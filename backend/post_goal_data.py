import boto3
import json
import os
import uuid
from decimal import Decimal
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('GOALS_TABLE', 'UserGoals'))
DATASET_ID = os.environ.get('DATASET_ID', 'demo')

CORS_HEADERS = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'OPTIONS,POST',
}


def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


def response(status_code, body):
    return {
        'statusCode': status_code,
        'headers': CORS_HEADERS,
        'body': json.dumps(body, default=decimal_default),
    }


def parse_decimal(value, default='0'):
    try:
        return Decimal(str(value if value not in (None, '') else default))
    except Exception:
        return None


def lambda_handler(event, context):
    if event.get('httpMethod') == 'OPTIONS' or event.get('requestContext', {}).get('http', {}).get('method') == 'OPTIONS':
        return response(200, {})

    body = json.loads(event.get('body') or '{}')
    dataset_id = body.get('dataset_id', DATASET_ID)

    title = body.get('title', '').strip()
    if not title:
        return response(400, {'error': 'title required'})

    target = parse_decimal(body.get('targetAmount'))
    current = parse_decimal(body.get('currentAmount'))
    if target is None or current is None:
        return response(400, {'error': 'targetAmount and currentAmount must be numbers'})

    deadline = body.get('deadline') or ''
    goal_type = body.get('type') or 'short'

    goal_id = str(uuid.uuid4())
    today = datetime.utcnow().strftime('%Y-%m-%d')

    try:
        end_dt = datetime.strptime(deadline, '%Y-%m-%d') if deadline else datetime.utcnow()
        duration = max((end_dt - datetime.utcnow()).days, 0)
        stored_deadline = deadline or today
    except ValueError:
        return response(400, {'error': 'deadline must use YYYY-MM-DD format'})

    status = 'achieved' if current >= target else 'pending'

    table.put_item(Item={
        'PK': f"DATASET#{dataset_id}",
        'SK': f"GOAL#{goal_id}",
        'entityType': 'GOAL',
        'goalId': goal_id,
        'Description': title,
        'Category': goal_type,
        'Specs': '',
        'StartDate': today,
        'EndDate': stored_deadline,
        'Duration': duration,
        'TotalAmount': target,
        'AmountSaved': current,
        'Result': status == 'achieved',
    })

    return response(201, {
        'goalId': goal_id,
        'title': title,
        'targetAmount': target,
        'currentAmount': current,
        'deadline': stored_deadline,
        'type': goal_type,
        'status': status,
    })
