import json
import os
import boto3
from boto3.dynamodb.conditions import Key
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('GOALS_TABLE', 'UserGoals'))
DATASET_ID = os.environ.get('DATASET_ID', 'demo')


def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


def lambda_handler(event, context):
    dataset_id = event.get('queryStringParameters', {}) or {}
    dataset_id = dataset_id.get('dataset_id', DATASET_ID)

    response = table.query(
        KeyConditionExpression=Key('PK').eq(f'DATASET#{dataset_id}') & Key('SK').begins_with('GOAL#')
    )

    goals = [
        {
            'goalId':         item.get('goalId', item['SK'].split('#')[-1]),
            'description':    item.get('Description', ''),
            'category':       item.get('Category', 'short'),
            'specs':          item.get('Specs', ''),
            'start_date':     item.get('StartDate', ''),
            'end_date':       item.get('EndDate', ''),
            'duration_days':  int(item.get('Duration', 0)),
            'target_amount':  float(item.get('TotalAmount', 0)),
            'amount_saved':   float(item.get('AmountSaved', 0)),
            'result':         item.get('Result', False),
        }
        for item in response['Items']
        if item.get('entityType') == 'GOAL'
    ]

    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'OPTIONS,GET',
        },
        'body': json.dumps({'dataset_id': dataset_id, 'goals': goals}, default=decimal_default),
    }
