import boto3
import json
import os
import uuid
from decimal import Decimal
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('GOALS_TABLE', 'UserGoals'))
DATASET_ID = os.environ.get('DATASET_ID', 'demo')


def lambda_handler(event, context):
    body = json.loads(event.get('body') or '{}')
    dataset_id = body.get('dataset_id', DATASET_ID)

    title = body.get('title', '').strip()
    if not title:
        return {'statusCode': 400, 'body': json.dumps({'error': 'title required'})}

    target = body.get('targetAmount', 0)
    current = body.get('currentAmount', 0)
    deadline = body.get('deadline', '')
    goal_type = body.get('type', '')

    goal_id = str(uuid.uuid4())
    today = datetime.utcnow().strftime('%Y-%m-%d')

    try:
        if deadline:
            end_dt = datetime.strptime(deadline, '%Y-%m-%d')
            duration = (end_dt - datetime.utcnow()).days
        else:
            duration = 0
    except ValueError:
        duration = 0

    table.put_item(Item={
        'PK': f"DATASET#{dataset_id}",
        'SK': f"GOAL#{goal_id}",
        'entityType': 'GOAL',
        'goalId': goal_id,
        'Description': title,
        'Category': goal_type,
        'Specs': '',
        'StartDate': today,
        'EndDate': deadline or today,
        'Duration': duration,
        'TotalAmount': Decimal(str(target)),
        'AmountSaved': Decimal(str(current)),
        'Result': current >= target,
    })

    return {
        'statusCode': 201,
        'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
        'body': json.dumps({
            'goalId': goal_id,
            'title': title,
            'targetAmount': float(target),
            'currentAmount': float(current),
            'deadline': deadline,
            'type': goal_type,
            'status': 'achieved' if current >= target else 'pending',
        }),
    }
