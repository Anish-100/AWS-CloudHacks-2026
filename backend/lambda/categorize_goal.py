import json
import boto3
import os

bedrock = boto3.client('bedrock-runtime')
dynamodb = boto3.resource('dynamodb')

GOALS_TABLE = os.environ.get('GOALS_TABLE', 'UserGoals')
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

        body = json.loads(event.get('body') or '{}')
        goal_description = body.get('description') or body.get('title', '')
        goal_id = body.get('goalId', 'new-goal')

        if not goal_description:
            return {
                "statusCode": 400,
                "headers": {"Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"error": "No goal description provided"})
            }

        # Truncate and sanitize to mitigate prompt injection
        safe_description = goal_description[:500].replace('"', "'")

        prompt = f"""
        You are a financial advisor assistant. A user has a short-term financial goal: "{safe_description}".
        Please categorize this goal into a single word or short phrase (e.g., 'Emergency Fund', 'Travel', 'Debt Payoff', 'Large Purchase').
        Also, provide specific, measurable specifications or sub-goals to achieve this.

        Respond ONLY in the following JSON format:
        {{
            "category": "<category>",
            "specs": ["<spec1>", "<spec2>"]
        }}
        """

        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 512,
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
            result = {"category": "Uncategorized", "specs": [content]}

        if goal_id != 'new-goal':
            try:
                table = dynamodb.Table(GOALS_TABLE)
                table.update_item(
                    Key={'PK': f"USER#{user_id}", 'SK': f"GOAL#{goal_id}"},
                    UpdateExpression="SET Category = :c, Specs = :s",
                    ExpressionAttributeValues={
                        ':c': result.get('category'),
                        ':s': result.get('specs', [])  # native DynamoDB List, not JSON string
                    }
                )
            except Exception as e:
                print(f"DynamoDB Update Error: {e}")

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
