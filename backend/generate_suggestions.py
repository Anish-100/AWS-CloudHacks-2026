import json
import boto3
import os
import uuid
from datetime import datetime

bedrock = boto3.client('bedrock-runtime')
dynamodb = boto3.resource('dynamodb')

TRANSACTIONS_TABLE = os.environ.get('TRANSACTIONS_TABLE', 'FinancialTransactions')
GOALS_TABLE = os.environ.get('GOALS_TABLE', 'UserGoals')
SUGGESTIONS_TABLE = os.environ.get('SUGGESTIONS_TABLE', 'Suggestions')
BEDROCK_MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-3-haiku-20240307-v1:0')


def get_user_id(event):
    # Cognito User Pools authorizer via API Gateway
    try:
        return event['requestContext']['authorizer']['claims']['sub']
    except (KeyError, TypeError):
        pass
    # Lambda authorizer
    try:
        return event['requestContext']['authorizer']['principalId']
    except (KeyError, TypeError):
        pass
    return None


def handler(event, context):
    try:
        user_id = get_user_id(event)
        if not user_id:
            return {
                "statusCode": 401,
                "headers": {"Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"error": "Unauthorized"})
            }

        tx_table = dynamodb.Table(TRANSACTIONS_TABLE)
        goals_table = dynamodb.Table(GOALS_TABLE)

        try:
            tx_response = tx_table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key('PK').eq(f"USER#{user_id}")
            )
            transactions = tx_response.get('Items', [])
        except Exception as e:
            print(f"Transactions query error: {e}")
            transactions = []

        try:
            goals_response = goals_table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key('PK').eq(f"USER#{user_id}")
            )
            goals = goals_response.get('Items', [])
        except Exception as e:
            print(f"Goals query error: {e}")
            goals = []

        tx_summary = json.dumps(transactions[:50], default=str)
        goals_summary = json.dumps(goals[:10], default=str)

        prompt = f"""
        You are an expert financial advisor. Here is a user's recent financial history (transactions):
        {tx_summary}

        And here are their current short-term financial goals:
        {goals_summary}

        Based on these spending patterns and goals, please identify any significant trends or spikes in spending.
        Then, generate 3 specific, actionable suggestions for how the user can cut back on spending or improve their habits to achieve their goals faster.

        Respond ONLY in the following JSON format:
        {{
            "suggestions": [
                {{
                    "title": "<suggestion title>",
                    "description": "<detailed suggestion>",
                    "impact": "<High/Medium/Low>"
                }}
            ]
        }}
        """

        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1024,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }

        response = bedrock.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            body=json.dumps(request_body)
        )

        response_body = json.loads(response.get('body').read())
        content_list = response_body.get('content', [])
        if not content_list:
            raise ValueError("Empty response from Bedrock")
        content = content_list[0].get('text', '')

        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            result = {"suggestions": [{"title": "Review Spending", "description": content, "impact": "Medium"}]}

        try:
            sugg_table = dynamodb.Table(SUGGESTIONS_TABLE)
            suggestion_id = str(uuid.uuid4())  # uuid avoids SK collisions on concurrent calls
            created_at = datetime.utcnow().isoformat() + 'Z'

            sugg_table.put_item(
                Item={
                    'PK': f"USER#{user_id}",
                    'SK': f"SUGG#{suggestion_id}",
                    'CreatedAt': created_at,
                    'Suggestions': result.get('suggestions', [])
                }
            )
        except Exception as e:
            print(f"DynamoDB Put Error: {e}")

        return {
            "statusCode": 200,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps(result)
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": str(e)})
        }
