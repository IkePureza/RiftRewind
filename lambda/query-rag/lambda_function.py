import json
import boto3
import os
import csv
from io import StringIO

def lambda_handler(event, context):
    """
    Query match data using Amazon Bedrock (RAG approach)
    Expected input: {"puuid": "user-puuid", "question": "What's my best champion?"}
    """
    try:
        # Parse request
        body = json.loads(event['body'])
        puuid = body.get('puuid', '').strip()
        question = body.get('question', '').strip()

        if not puuid or not question:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'PUUID and question are required'})
            }

        # Get bucket name from environment
        bucket_name = os.environ.get('MATCH_DATA_BUCKET')

        print(f"🔍 Question: {question}")
        print(f"👤 PUUID: {puuid[:20]}...")

        # Initialize clients
        s3 = boto3.client('s3')
        bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')

        # Check if processed data exists
        csv_key = f"users/{puuid}/processed/match_stats.csv"

        try:
            # Read the processed CSV
            csv_obj = s3.get_object(Bucket=bucket_name, Key=csv_key)
            csv_content = csv_obj['Body'].read().decode('utf-8')

            print(f"📊 Found processed data at {csv_key}")

        except s3.exceptions.NoSuchKey:
            return {
                'statusCode': 404,
                'body': json.dumps({
                    'error': 'No processed data found. Please click "Process Stats" first!',
                    'hint': 'Search for a summoner and process their stats before asking questions.'
                })
            }

        # Build the prompt for Claude
        prompt = f"""You are a League of Legends gameplay analyst. You have access to a player's match history data in CSV format.

Here is the player's match data:

{csv_content}

The player is asking: {question}

Please analyze the data and provide a helpful, insightful answer. Be specific and reference actual statistics from the data. Keep your response concise but informative (2-3 paragraphs max).

If the question cannot be answered with the available data, explain what additional information would be needed."""

        # Call Bedrock Claude
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }

        print("🤖 Calling Bedrock Claude...")

        response = bedrock.invoke_model(
            modelId='anthropic.claude-3-haiku-20240307-v1:0',  # Claude 3 Haiku - Best price/performance
            body=json.dumps(request_body)
        )

        # Parse Bedrock response
        response_body = json.loads(response['body'].read())
        answer = response_body['content'][0]['text']

        print(f"✅ Got answer from Claude ({len(answer)} chars)")

        return {
            'statusCode': 200,
            'body': json.dumps({
                'question': question,
                'answer': answer,
                'dataSource': csv_key
            })
        }

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

        # More specific error messages
        error_msg = str(e)
        if 'AccessDeniedException' in error_msg:
            error_msg = 'Bedrock access denied. Please enable Claude 3 Haiku model in AWS Bedrock console.'
        elif 'ModelNotFound' in error_msg:
            error_msg = 'Claude 3 Haiku model not found. Please enable it in the Bedrock console.'

        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error', 'detail': error_msg})
        }
