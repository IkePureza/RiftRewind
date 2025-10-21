import json
import boto3
import csv
from io import StringIO
import os

def lambda_handler(event, context):
    """
    Process match data for a user and return clean stats
    Expected input: {"puuid": "user-puuid"}
    """
    try:
        # Parse request
        body = json.loads(event['body'])
        puuid = body.get('puuid', '').strip()

        if not puuid:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'PUUID is required'})
            }

        # Get bucket name from environment
        bucket_name = os.environ.get('MATCH_DATA_BUCKET')

        s3 = boto3.client('s3')

        # List all match files for this user
        prefix = f"users/{puuid}/matches/"

        print(f"🔍 Looking for matches at s3://{bucket_name}/{prefix}")

        try:
            response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
        except Exception as e:
            print(f"❌ Error listing S3 objects: {str(e)}")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Failed to access S3 bucket'})
            }

        if 'Contents' not in response:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'No matches found for this user. Search for a summoner first!'})
            }

        # Collect match stats
        match_stats = []

        for obj in response['Contents']:
            key = obj['Key']
            if not key.endswith('.json'):
                continue

            print(f"📊 Processing {key}")

            # Read match data
            match_obj = s3.get_object(Bucket=bucket_name, Key=key)
            match_json = json.loads(match_obj['Body'].read().decode('utf-8'))

            # Find the player's stats
            player_stats = None
            for participant in match_json['info']['participants']:
                if participant['puuid'] == puuid:
                    player_stats = participant
                    break

            if not player_stats:
                print(f"⚠️  Player not found in match {key}")
                continue

            # Extract clean stats
            stats = {
                'matchId': match_json['metadata']['matchId'],
                'gameCreation': match_json['info']['gameCreation'],
                'gameDuration': match_json['info']['gameDuration'],
                'gameMode': match_json['info']['gameMode'],
                'queueId': match_json['info']['queueId'],
                'championName': player_stats['championName'],
                'championId': player_stats['championId'],
                'position': player_stats.get('teamPosition', 'UNKNOWN'),
                'kills': player_stats['kills'],
                'deaths': player_stats['deaths'],
                'assists': player_stats['assists'],
                'kdaRatio': round((player_stats['kills'] + player_stats['assists']) / max(player_stats['deaths'], 1), 2),
                'cs': player_stats['totalMinionsKilled'] + player_stats['neutralMinionsKilled'],
                'goldEarned': player_stats['goldEarned'],
                'damageDealt': player_stats['totalDamageDealtToChampions'],
                'damageTaken': player_stats['totalDamageTaken'],
                'visionScore': player_stats['visionScore'],
                'win': player_stats['win'],
                'firstBlood': player_stats.get('firstBloodKill', False),
                'doubleKills': player_stats['doubleKills'],
                'tripleKills': player_stats['tripleKills'],
                'quadraKills': player_stats['quadraKills'],
                'pentaKills': player_stats['pentaKills'],
            }

            match_stats.append(stats)

        if not match_stats:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'No valid match data found'})
            }

        # Create CSV
        csv_buffer = StringIO()
        fieldnames = match_stats[0].keys()
        writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(match_stats)

        # Save to S3
        output_key = f"users/{puuid}/processed/match_stats.csv"
        s3.put_object(
            Bucket=bucket_name,
            Key=output_key,
            Body=csv_buffer.getvalue(),
            ContentType='text/csv'
        )

        print(f"✅ Processed {len(match_stats)} matches")
        print(f"📁 Saved to s3://{bucket_name}/{output_key}")

        # Return processed stats
        return {
            'statusCode': 200,
            'body': json.dumps({
                'matchesProcessed': len(match_stats),
                'stats': match_stats,
                's3Location': f"s3://{bucket_name}/{output_key}",
                'message': f'Successfully processed {len(match_stats)} matches'
            })
        }

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error', 'detail': str(e)})
        }
