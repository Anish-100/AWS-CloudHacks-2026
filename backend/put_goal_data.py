import boto3
import json
import os
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('GOALS_TABLE', 'UserGoals'))
DATASET_ID = os.environ.get('DATASET_ID', 'demo')


def lambda_handler(event, context):
    goal_id = (event.get('pathParameters') or {}).get('goalId')
    if not goal_id:
        return {'statusCode': 400, 'body': json.dumps({'error': 'goalId required'})}

    body = json.loads(event.get('body') or '{}')
    dataset_id = body.get('dataset_id', DATASET_ID)

    update_fields = {}
    if 'currentAmount' in body:
        update_fields['AmountSaved'] = Decimal(str(body['currentAmount']))
    if 'title' in body:
        update_fields['Description'] = body['title']
    if 'deadline' in body:
        update_fields['EndDate'] = body['deadline']
    if 'status' in body:
        update_fields['Result'] = body['status'] == 'achieved'

    if not update_fields:
        return {'statusCode': 400, 'body': json.dumps({'error': 'no fields to update'})}

    expr = 'SET ' + ', '.join(f'#f_{k} = :v_{k}' for k in update_fields)
    names = {f'#f_{k}': k for k in update_fields}
    values = {f':v_{k}': v for k, v in update_fields.items()}

    table.update_item(
        Key={'PK': f"DATASET#{dataset_id}", 'SK': f"GOAL#{goal_id}"},
        UpdateExpression=expr,
        ExpressionAttributeNames=names,
        ExpressionAttributeValues=values,
    )

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
        'body': json.dumps({'message': 'Goal updated', 'goalId': goal_id}),
    }
