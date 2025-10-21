import json
import boto3
import urllib3
from urllib.parse import quote
from datetime import datetime
import os

def lambda_handler(event, context):
    """
    Fetches League of Legends match history for a summoner using Riot ID.
    Stores data in S3 with organized folder structure.
    Expected input: {"summonerName": "GameName#TAG", "region": "oc1", "count": 5}
    """
    try:
        # Get configuration from environment variables
        bucket_name = os.environ.get('MATCH_DATA_BUCKET')
        api_key_param = os.environ.get('RIOT_API_KEY_PARAM', '/rift-rewind/riot-api-key')

        # Parse the request
        body = json.loads(event['body'])
        summoner_name = body.get('summonerName', '').strip()
        region = body.get('region', 'oc1')
        match_count = body.get('count', 5)
        
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
        try:
            parameter = ssm.get_parameter(
                Name=api_key_param,
                WithDecryption=True
            )
            api_key = parameter['Parameter']['Value']
            print(f"✅ Retrieved API key from Parameter Store")
        except Exception as e:
            print(f"❌ Failed to get API key: {str(e)}")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Failed to retrieve API key'})
            }

        # Debug logging
        print(f"🎮 Looking up: {summoner_name} in region {region}")
        print(f"📊 Fetching {match_count} matches")
        
        # Initialize HTTP client and S3
        http = urllib3.PoolManager()
        s3 = boto3.client('s3')
        headers = {'X-Riot-Token': api_key}

        # Step 1: Get account PUUID using Riot ID
        game_name, tag_line = summoner_name.split('#', 1)
        game_name = quote(game_name)
        tag_line = quote(tag_line)

        # Get routing values for this region
        account_routing = get_account_routing(region)
        match_routing = get_match_routing(region)

        account_url = f"https://{account_routing}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
        
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
        full_summoner_name = f"{account_data['gameName']}#{account_data['tagLine']}"

        print(f"✅ Got summoner level: {summoner_data['summonerLevel']}")

        # Save profile data to S3
        profile_data = {
            'puuid': puuid,
            'gameName': account_data['gameName'],
            'tagLine': account_data['tagLine'],
            'summonerLevel': summoner_data['summonerLevel'],
            'region': region,
            'lastUpdated': datetime.now().isoformat()
        }

        profile_key = f"users/{puuid}/profile.json"
        s3.put_object(
            Bucket=bucket_name,
            Key=profile_key,
            Body=json.dumps(profile_data, indent=2),
            ContentType='application/json'
        )
        print(f"💾 Saved profile to S3: {profile_key}")

        # Step 3: Get match list
        match_list_url = f"https://{match_routing}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count={match_count}"

        print(f"🔗 Match list URL: {match_list_url}")
        match_list_response = http.request('GET', match_list_url, headers=headers)

        if match_list_response.status != 200:
            print(f"⚠️  Failed to fetch match list: {match_list_response.status}")
            return {
                'statusCode': match_list_response.status,
                'body': json.dumps({
                    'error': f'Failed to fetch match list: {match_list_response.status}'
                })
            }

        match_ids = json.loads(match_list_response.data.decode('utf-8'))

        if not match_ids:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'No matches found for this summoner'})
            }

        print(f"✅ Found {len(match_ids)} matches")

        # Step 4: Fetch and process each match
        processed_matches = []

        for i, match_id in enumerate(match_ids):
            print(f"🎮 Processing match {i+1}/{len(match_ids)}: {match_id}")

            # Get full match data
            match_url = f"https://{match_routing}.api.riotgames.com/lol/match/v5/matches/{match_id}"
            match_response = http.request('GET', match_url, headers=headers)

            if match_response.status != 200:
                print(f"⚠️  Failed to fetch match {match_id}: {match_response.status}")
                continue

            match_data = json.loads(match_response.data.decode('utf-8'))

            # Save full match data to S3
            match_key = f"users/{puuid}/matches/{match_id}.json"
            s3.put_object(
                Bucket=bucket_name,
                Key=match_key,
                Body=json.dumps(match_data, indent=2),
                ContentType='application/json'
            )

            # Extract player stats
            player_stats = extract_player_stats(match_data, puuid)
            if player_stats:
                processed_matches.append({
                    'matchId': match_id,
                    'champion': player_stats.get('championName'),
                    'championId': player_stats.get('championId'),
                    'role': player_stats.get('teamPosition', 'UNKNOWN'),
                    'kills': player_stats.get('kills', 0),
                    'deaths': player_stats.get('deaths', 0),
                    'assists': player_stats.get('assists', 0),
                    'kda': f"{player_stats.get('kills', 0)}/{player_stats.get('deaths', 0)}/{player_stats.get('assists', 0)}",
                    'win': player_stats.get('win'),
                    'gameMode': player_stats.get('gameMode'),
                    'gameDuration': player_stats.get('gameDuration'),
                    'cs': player_stats.get('totalMinionsKilled', 0) + player_stats.get('neutralMinionsKilled', 0),
                    's3Key': match_key
                })
                print(f"  ✅ {player_stats.get('championName')} - {'Win' if player_stats.get('win') else 'Loss'}")

        # Format response
        response_data = {
            'summoner': {
                'name': full_summoner_name,
                'level': summoner_data['summonerLevel'],
                'puuid': puuid,
                'profileS3Key': profile_key
            },
            'matchesProcessed': len(processed_matches),
            'matches': processed_matches,
            'region': region
        }

        print(f"🎉 Success! Processed {len(processed_matches)} matches for {full_summoner_name}")

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

def extract_player_stats(match_data, puuid):
    """Extract relevant player statistics from match data"""
    try:
        # Find the participant data for our player
        participants = match_data['info']['participants']
        player_data = None

        for participant in participants:
            if participant['puuid'] == puuid:
                player_data = participant
                break

        if not player_data:
            return None

        # Extract key statistics
        stats = {
            'matchId': match_data['metadata']['matchId'],
            'gameCreation': match_data['info']['gameCreation'],
            'gameDuration': match_data['info']['gameDuration'],
            'gameMode': match_data['info']['gameMode'],
            'queueId': match_data['info']['queueId'],
            'championName': player_data['championName'],
            'championId': player_data['championId'],
            'teamPosition': player_data['teamPosition'],
            'individualPosition': player_data['individualPosition'],
            'kills': player_data['kills'],
            'deaths': player_data['deaths'],
            'assists': player_data['assists'],
            'totalMinionsKilled': player_data['totalMinionsKilled'],
            'neutralMinionsKilled': player_data['neutralMinionsKilled'],
            'goldEarned': player_data['goldEarned'],
            'totalDamageDealtToChampions': player_data['totalDamageDealtToChampions'],
            'totalDamageTaken': player_data['totalDamageTaken'],
            'visionScore': player_data['visionScore'],
            'win': player_data['win'],
            'items': [
                player_data['item0'],
                player_data['item1'],
                player_data['item2'],
                player_data['item3'],
                player_data['item4'],
                player_data['item5'],
                player_data['item6']  # trinket
            ],
            'summoner1Id': player_data['summoner1Id'],
            'summoner2Id': player_data['summoner2Id'],
            'perks': {
                'primaryStyle': player_data['perks']['styles'][0]['style'],
                'subStyle': player_data['perks']['styles'][1]['style'],
                'primaryPerk': player_data['perks']['styles'][0]['selections'][0]['perk']
            }
        }

        return stats

    except Exception as e:
        print(f"❌ Error extracting player stats: {str(e)}")
        return None

def get_account_routing(region):
    """Map platform region to routing value for Account API (Riot ID lookup)"""
    routing_map = {
        'na1': 'americas',
        'br1': 'americas',
        'la1': 'americas',
        'la2': 'americas',
        'oc1': 'americas',  # OC1 uses americas for account API
        'euw1': 'europe',
        'eun1': 'europe',
        'tr1': 'europe',
        'ru': 'europe',
        'kr': 'asia',
        'jp1': 'asia',
        'ph2': 'sea',
        'sg2': 'sea',
        'th2': 'sea',
        'tw2': 'sea',
        'vn2': 'sea'
    }
    return routing_map.get(region, 'americas')

def get_match_routing(region):
    """Map platform region to routing value for Match API (match history)"""
    routing_map = {
        'na1': 'americas',
        'br1': 'americas',
        'la1': 'americas',
        'la2': 'americas',
        'oc1': 'sea',  # OC1 uses sea for match API
        'euw1': 'europe',
        'eun1': 'europe',
        'tr1': 'europe',
        'ru': 'europe',
        'kr': 'asia',
        'jp1': 'asia',
        'ph2': 'sea',
        'sg2': 'sea',
        'th2': 'sea',
        'tw2': 'sea',
        'vn2': 'sea'
    }
    return routing_map.get(region, 'americas')