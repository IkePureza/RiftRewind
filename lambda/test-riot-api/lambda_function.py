import json
import boto3
import urllib3
from urllib.parse import quote

def lambda_handler(event, context):
    """
    Fetches champion mastery data for a summoner using Riot ID.
    Expected input: {"summonerName": "GameName#TAG", "region": "oc1"}
    """
    try:
        # Parse the request
        body = json.loads(event['body'])
        summoner_name = body.get('summonerName', '').strip()
        region = body.get('region', 'oc1')
        
        # Validate input
        if not summoner_name:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Summoner name is required'})
            }
        
        # Validate Riot ID format
        if '#' not in summoner_name:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Please use Riot ID format: GameName#TAG (e.g., Iceraze#OC)'})
            }
        
        # Get API key from Parameter Store
        ssm = boto3.client('ssm', region_name='us-east-1')
        parameter = ssm.get_parameter(
            Name='/rift-rewind/riot-api-key',
            WithDecryption=True
        )
        api_key = parameter['Parameter']['Value']
        
        # Debug logging
        print(f"✅ Retrieved API key from Parameter Store")
        print(f"🎮 Looking up: {summoner_name} in region {region}")
        
        # Initialize HTTP client
        http = urllib3.PoolManager()
        headers = {'X-Riot-Token': api_key}
        
        # Step 1: Get account PUUID using Riot ID
        game_name, tag_line = summoner_name.split('#', 1)
        game_name = quote(game_name)
        tag_line = quote(tag_line)
        
        # Use americas routing for now (most reliable)
        routing_value = 'americas'
        account_url = f"https://{routing_value}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
        
        print(f"🔗 Account API URL: {account_url}")
        
        account_response = http.request('GET', account_url, headers=headers)
        
        print(f"📊 Account API Response Status: {account_response.status}")
        
        if account_response.status == 404:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'Riot ID not found. Check spelling and region.'})
            }
        elif account_response.status == 403:
            print(f"❌ 403 Error - API key likely expired")
            return {
                'statusCode': 403,
                'body': json.dumps({
                    'error': 'API key is invalid or expired',
                    'hint': 'Regenerate your Riot API key at https://developer.riotgames.com/'
                })
            }
        elif account_response.status != 200:
            error_detail = account_response.data.decode('utf-8')
            print(f"❌ Error: {error_detail}")
            return {
                'statusCode': account_response.status,
                'body': json.dumps({
                    'error': f'Failed to fetch account: {account_response.status}',
                    'detail': error_detail
                })
            }
        
        account_data = json.loads(account_response.data.decode('utf-8'))
        puuid = account_data['puuid']
        
        print(f"✅ Got PUUID: {puuid[:20]}...")
        
        # Step 2: Get summoner data by PUUID
        summoner_url = f"https://{region}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
        
        print(f"🔗 Summoner API URL: {summoner_url}")
        
        summoner_response = http.request('GET', summoner_url, headers=headers)
        
        print(f"📊 Summoner API Response Status: {summoner_response.status}")
        
        if summoner_response.status != 200:
            error_detail = summoner_response.data.decode('utf-8')
            print(f"❌ Summoner Error: {error_detail}")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Failed to fetch summoner data',
                    'detail': error_detail
                })
            }
        
        summoner_data = json.loads(summoner_response.data.decode('utf-8'))
        
        print(f"✅ Got summoner level: {summoner_data['summonerLevel']}")
        
        # Step 3: Get champion mastery data
        mastery_url = f"https://{region}.api.riotgames.com/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}/top?count=3"
        mastery_response = http.request('GET', mastery_url, headers=headers)
        
        mastery_data = []
        if mastery_response.status == 200:
            mastery_data = json.loads(mastery_response.data.decode('utf-8'))
            print(f"✅ Got {len(mastery_data)} champion masteries")
        else:
            print(f"⚠️  No mastery data (status {mastery_response.status})")
        
        # Format response
        response_data = {
            'summoner': {
                'name': account_data['gameName'] + '#' + account_data['tagLine'],
                'level': summoner_data['summonerLevel'],
                'puuid': puuid
            },
            'topChampions': mastery_data[:3]
        }
        
        print(f"🎉 Success! Returning data for {response_data['summoner']['name']}")
        
        return {
            'statusCode': 200,
            'body': json.dumps(response_data)
        }
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error', 'detail': str(e)})
        }