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
            'description':    item['Description'],
            'category':       item['Category'],
            'specs':          item.get('Specs', ''),
            'start_date':     item['StartDate'],
            'end_date':       item['EndDate'],
            'duration_days':  int(item['Duration']),
            'target_amount':  float(item['TotalAmount']),
            'amount_saved':   float(item['AmountSaved']),
            'result':         item['Result'],
        }
        for item in response['Items']
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
