import json
import os
import boto3
from boto3.dynamodb.conditions import Key
from decimal import Decimal

dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
table = dynamodb.Table('Suggestions')
DATASET_ID = os.environ.get('DATASET_ID', 'demo')


def lambda_handler(event, context):
    dataset_id = (event.get('queryStringParameters') or {}).get('dataset_id', DATASET_ID)

    response = table.query(
        KeyConditionExpression=Key('PK').eq(f'DATASET#{dataset_id}') & Key('SK').begins_with('SUGGESTION#')
    )

    suggestions = []
    total_savings = 0.0
    for item in response['Items']:
        taken = item.get('taken', False)
        monthly_saving = float(item.get('monthly_saving', 0))
        if taken:
            total_savings += monthly_saving
        suggestions.append({
            'suggestion_id':  item['SK'],
            'category':       item['category'],
            'action':         item['action'],
            'monthly_saving': monthly_saving,
            'taken':          taken,
        })

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({
            'dataset_id':    dataset_id,
            'suggestions':   suggestions,
            'total_savings': round(total_savings, 2),
        }),
    }
