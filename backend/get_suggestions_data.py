import json
import os

import boto3
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('SUGGESTIONS_TABLE', 'Suggestions'))
DATASET_ID = os.environ.get('DATASET_ID', 'demo')


def lambda_handler(event, context):
    params = event.get('queryStringParameters') or {}
    dataset_id = params.get('dataset_id') or params.get('datasetId') or DATASET_ID

    response = table.query(
        KeyConditionExpression=Key('PK').eq(f'DATASET#{dataset_id}') & Key('SK').begins_with('SUGGESTION#')
    )

    suggestions = []
    total_savings = 0.0
    for item in response.get('Items', []):
        taken = item.get('taken', False)
        monthly_saving = float(item.get('monthly_saving', 0))
        if taken:
            total_savings += monthly_saving
            continue

        suggestions.append({
            'suggestion_id':  item['SK'],
            'category':       item.get('category', 'Savings'),
            'action':         item.get('action', ''),
            'monthly_saving': monthly_saving,
            'taken':          taken,
        })

    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'OPTIONS,GET',
        },
        'body': json.dumps({
            'dataset_id':    dataset_id,
            'suggestions':   suggestions[:3],
            'total_savings': round(total_savings, 2),
        }),
    }
