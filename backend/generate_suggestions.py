import json
import os
import re
import uuid
from collections import Counter, defaultdict
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb')
transactions_table = dynamodb.Table(os.environ.get('TRANSACTIONS_TABLE', 'FinancialTransactions'))
goals_table = dynamodb.Table(os.environ.get('GOALS_TABLE', 'UserGoals'))
suggestions_table = dynamodb.Table(os.environ.get('SUGGESTIONS_TABLE', 'Suggestions'))
DATASET_ID = os.environ.get('DATASET_ID', 'demo')

bedrock = boto3.client('bedrock-runtime', region_name=os.environ.get('AWS_REGION', 'us-west-2'))
MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-3-haiku-20240307-v1:0')
SUGGESTION_COUNT = 3

CORS_HEADERS = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'OPTIONS,GET',
}


def extract_bedrock_text(response):
    payload = json.loads(response['body'].read())
    return payload['content'][0]['text'].strip()


def parse_recommendations(text):
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if not match:
            raise
        payload = json.loads(match.group(0))

    recommendations = payload.get('recommendations', [])
    if not isinstance(recommendations, list):
        return []
    return recommendations


def clean_description(description):
    return re.sub(r'\s+', ' ', str(description or '').strip()) or 'Unknown merchant'


def get_spending_trends(dataset_id):
    txn_resp = transactions_table.query(
        KeyConditionExpression=Key('PK').eq(f'DATASET#{dataset_id}')
    )

    spending_by_category = defaultdict(float)
    count_by_category = Counter()
    merchants_by_category = defaultdict(Counter)

    for item in txn_resp.get('Items', []):
        if item.get('entityType') == 'TRANSACTION' and item.get('Type', '').lower() == 'sale':
            category = item.get('Category', 'Other')
            amount = abs(float(item.get('Amount', 0)))
            spending_by_category[category] += amount
            count_by_category[category] += 1
            merchants_by_category[category][clean_description(item.get('Description'))] += 1

    if not spending_by_category:
        return 'No spending data'

    lines = []
    for category, amount in sorted(spending_by_category.items(), key=lambda pair: -pair[1])[:6]:
        count = count_by_category[category]
        average = amount / count if count else 0
        examples = ', '.join(
            merchant
            for merchant, _ in merchants_by_category[category].most_common(4)
        )
        lines.append(
            f'- {category}: ${amount:.2f} across {count} purchases '
            f'(avg ${average:.2f}); examples: {examples}'
        )

    return '\n'.join(lines)


def get_goals_summary(dataset_id):
    goals_resp = goals_table.query(
        KeyConditionExpression=Key('PK').eq(f'DATASET#{dataset_id}')
    )

    active_goals = []
    for item in goals_resp.get('Items', []):
        if not item.get('SK', '').startswith('GOAL#') or item.get('Result', False):
            continue

        active_goals.append(
            f"{item.get('Description', 'Goal')} "
            f"(target: ${float(item.get('TotalAmount', 0)):.2f}, "
            f"saved: ${float(item.get('AmountSaved', 0)):.2f})"
        )

    return '; '.join(active_goals) if active_goals else 'No active goals'


def delete_open_suggestions(dataset_id):
    existing = suggestions_table.query(
        KeyConditionExpression=Key('PK').eq(f'DATASET#{dataset_id}')
    )

    with suggestions_table.batch_writer() as batch:
        for item in existing.get('Items', []):
            if item.get('taken') is not True:
                batch.delete_item(Key={'PK': item['PK'], 'SK': item['SK']})


def store_recommendations(dataset_id, recommendations):
    new_suggestions = []

    with suggestions_table.batch_writer() as batch:
        for rec in recommendations[:SUGGESTION_COUNT]:
            monthly_saving = int(float(rec.get('monthly_saving') or 0))
            if monthly_saving <= 0:
                continue

            sid = str(uuid.uuid4())
            item = {
                'PK': f'DATASET#{dataset_id}',
                'SK': f'SUGGESTION#{sid}',
                'category': rec.get('category', 'General'),
                'action': rec.get('action', ''),
                'monthly_saving': Decimal(str(rec.get('monthly_saving', 0))),
                'taken': None,
            }
            batch.put_item(Item=item)
            new_suggestions.append({
                'suggestion_id': item['SK'],
                'category': item['category'],
                'action': item['action'],
                'monthly_saving': float(monthly_saving),
                'taken': None,
            })

    return new_suggestions


def lambda_handler(event, context):
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': CORS_HEADERS, 'body': '{}'}

    params = event.get('queryStringParameters') or {}
    dataset_id = params.get('dataset_id') or params.get('datasetId') or DATASET_ID

    prompt = (
        'You are a practical personal finance advisor for a student.\n'
        f"Past spending trends from the user's CSV:\n{get_spending_trends(dataset_id)}\n\n"
        f'Active savings goals: {get_goals_summary(dataset_id)}.\n\n'
        f'Give exactly {SUGGESTION_COUNT} specific recommendations that tell the user how to save money '
        'by avoiding, reducing, replacing, or delaying a spending habit shown in the CSV. '
        'Each action must be behavior-based and tied to a past category or merchant trend. '
        'Write actions like "Save $10 this week by packing lunch instead of buying Chipotle or Panda Express", '
        'not like "Save $20 toward a new suit". '
        'Do not suggest saving toward a goal item, buying cheaper versions of goal items, investing, budgeting apps, '
        'or generic advice. '
        'Each recommendation must be quantifiable with a positive exact monthly_saving integer in dollars, '
        'estimated from the past spending amounts. '
        'Return ONLY valid JSON: '
        '{"recommendations":[{"action":"...","category":"...","monthly_saving":25}]}'
    )

    br_response = bedrock.invoke_model(
        modelId=MODEL_ID,
        contentType='application/json',
        accept='application/json',
        body=json.dumps({
            'anthropic_version': 'bedrock-2023-05-31',
            'max_tokens': 1024,
            'messages': [{'role': 'user', 'content': prompt}],
        }),
    )

    recommendations = parse_recommendations(extract_bedrock_text(br_response))
    delete_open_suggestions(dataset_id)
    new_suggestions = store_recommendations(dataset_id, recommendations)

    return {
        'statusCode': 200,
        'headers': CORS_HEADERS,
        'body': json.dumps({'dataset_id': dataset_id, 'suggestions': new_suggestions}),
    }
