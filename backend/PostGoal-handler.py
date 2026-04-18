import json
import os
import boto3
from boto3.dynamodb.conditions import Key
from decimal import Decimal
from datetime import datetime

dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
table = dynamodb.Table('UserGoals')
DATASET_ID = os.environ.get('DATASET_ID', 'demo')


def lambda_handler(event, context):
    body = json.loads(event.get('body') or '{}')
    dataset_id = body.get('dataset_id', DATASET_ID)

    description   = body.get('description')
    target_amount = body.get('target_amount')
    amount_saved  = float(body.get('amount_saved', 0))
    deadline      = body.get('deadline')
    category      = body.get('category', 'General')
    specs         = body.get('specs', '')

    if not description or not target_amount or not deadline:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'description, target_amount, and deadline are required'}),
        }

    try:
        datetime.strptime(deadline, '%Y-%m-%d')
    except ValueError:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'deadline must be YYYY-MM-DD'}),
        }

    start_date = datetime.utcnow().strftime('%Y-%m-%d')
    existing = table.query(
        KeyConditionExpression=Key('PK').eq(f'DATASET#{dataset_id}') & Key('SK').begins_with('GOAL#')
    )
    index = len(existing['Items'])
    sk = f'GOAL#{start_date}#{index:04d}'

    table.put_item(Item={
        'PK':          f'DATASET#{dataset_id}',
        'SK':          sk,
        'entityType':  'GOAL',
        'Description': description,
        'Category':    category,
        'Specs':       specs,
        'StartDate':   start_date,
        'EndDate':     deadline,
        'TotalAmount': Decimal(str(target_amount)),
        'AmountSaved': Decimal(str(amount_saved)),
        'Result':      False,
    })

    return {
        'statusCode': 201,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({
            'message':    'Goal created',
            'dataset_id': dataset_id,
            'sk':         sk,
        }),
    }
