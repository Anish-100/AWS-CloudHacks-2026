import boto3
import json
import os

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('GOALS_TABLE', 'UserGoals'))
DATASET_ID = os.environ.get('DATASET_ID', 'demo')


def lambda_handler(event, context):
    goal_id = (event.get('pathParameters') or {}).get('goalId')
    if not goal_id:
        return {'statusCode': 400, 'body': json.dumps({'error': 'goalId required'})}

    dataset_id = (event.get('queryStringParameters') or {}).get('dataset_id', DATASET_ID)

    table.delete_item(
        Key={'PK': f"DATASET#{dataset_id}", 'SK': f"GOAL#{goal_id}"},
    )

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
        'body': json.dumps({'message': 'Goal deleted', 'goalId': goal_id}),
    }
