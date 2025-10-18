# Test Riot API Lambda

Simple Lambda function to test Riot API connectivity and Parameter Store access.

## What it does
- Retrieves Riot API key from AWS Systems Manager Parameter Store
- Makes a test API call to fetch summoner data
- Returns success/failure status

## Environment
- Runtime: Python 3.12
- Required IAM permissions: SSM Parameter access
