import json
import os
import re
import uuid
from datetime import datetime
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('SUGGESTIONS_TABLE', 'Suggestions'))
goals_table = dynamodb.Table(os.environ.get('GOALS_TABLE', 'UserGoals'))
transactions_table = dynamodb.Table(os.environ.get('TRANSACTIONS_TABLE', 'FinancialTransactions'))
bedrock = boto3.client('bedrock-runtime', region_name=os.environ.get('AWS_REGION', 'us-west-2'))

DATASET_ID = os.environ.get('DATASET_ID', 'demo')
BEDROCK_MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-3-haiku-20240307-v1:0')


def api_response(status_code, body):
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'OPTIONS,POST',
        },
        'body': json.dumps(body),
    }


def normalize_suggestion_id(suggestion_id):
    return str(suggestion_id).replace('SUGGESTION#', '', 1)


def parse_date(value):
    try:
        return datetime.strptime(value, '%Y-%m-%d')
    except (TypeError, ValueError):
        return datetime.max


def query_open_goals(dataset_id):
    pk = f'DATASET#{dataset_id}'
    goal_response = goals_table.query(
        KeyConditionExpression=Key('PK').eq(pk) & Key('SK').begins_with('GOAL#')
    )

    return [
        item
        for item in goal_response.get('Items', [])
        if not item.get('Result', False)
        and Decimal(str(item.get('AmountSaved', 0))) < Decimal(str(item.get('TotalAmount', 0)))
    ]


def apply_saving_to_nearest_goal(dataset_id, monthly_saving):
    if monthly_saving <= 0:
        return None

    goals = query_open_goals(dataset_id)
    if not goals:
        return None

    nearest_goal = sorted(goals, key=lambda item: parse_date(item.get('EndDate')))[0]
    current = Decimal(str(nearest_goal.get('AmountSaved', 0)))
    target = Decimal(str(nearest_goal.get('TotalAmount', 0)))
    next_amount = min(current + Decimal(str(monthly_saving)), target)
    achieved = next_amount >= target

    goals_table.update_item(
        Key={'PK': nearest_goal['PK'], 'SK': nearest_goal['SK']},
        UpdateExpression='SET AmountSaved = :amount, #result = :result',
        ExpressionAttributeNames={'#result': 'Result'},
        ExpressionAttributeValues={
            ':amount': next_amount,
            ':result': achieved,
        },
    )

    goal_id = nearest_goal.get('goalId', nearest_goal['SK'].replace('GOAL#', '', 1))
    return {
        'goalId': goal_id,
        'title': nearest_goal.get('Description', ''),
        'currentAmount': float(next_amount),
        'targetAmount': float(target),
        'deadline': nearest_goal.get('EndDate', ''),
        'status': 'achieved' if achieved else 'pending',
    }


def extract_bedrock_text(response):
    payload = json.loads(response['body'].read())
    return payload['content'][0]['text'].strip()


def parse_suggestions_json(text):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def build_goal_context(dataset_id):
    goals = sorted(query_open_goals(dataset_id), key=lambda item: parse_date(item.get('EndDate')))[:3]
    if not goals:
        return 'No active savings goals.'
    lines = []
    for goal in goals:
        lines.append(
            f"- {goal.get('Description', 'Goal')}: "
            f"${float(goal.get('AmountSaved', 0)):.0f} saved of "
            f"${float(goal.get('TotalAmount', 0)):.0f}, due {goal.get('EndDate', 'unknown')}"
        )
    return '\n'.join(lines)


def build_spending_context(dataset_id):
    resp = transactions_table.query(
        KeyConditionExpression=Key('PK').eq(f'DATASET#{dataset_id}')
    )
    rows = [
        f"{item.get('TransactionDate')} | {item.get('Category', 'Other')} | {item.get('Description', '')} | ${float(item.get('Amount', 0)):.2f}"
        for item in resp.get('Items', [])
        if item.get('entityType') == 'TRANSACTION'
    ]
    return '\n'.join(rows) if rows else 'No transaction history available.'


def generate_replacement_suggestions(dataset_id, accepted_action, category):
    prompt = (
        'You are a practical personal finance advisor for a student.\n'
        f'The user just accepted this advice: "{accepted_action}" (category: {category or "General"}).\n\n'
        f'Past spending from their CSV (date | category | description | amount):\n{build_spending_context(dataset_id)}\n\n'
        f'Their active goals:\n{build_goal_context(dataset_id)}\n\n'
        'Generate exactly 3 new specific, actionable suggestions that tell the user how to save money '
        'by avoiding, reducing, replacing, or delaying a spending habit shown in the CSV. '
        'Each action must be behavior-based and tied to a past category, merchant, or transaction pattern. '
        'Write actions like "Save $10 this week by packing lunch instead of buying Chipotle or Panda Express", '
        'not like "Save $20 toward a new suit". '
        'Do not suggest saving toward a goal item, buying cheaper versions of goal items, investing, budgeting apps, '
        'or generic advice. '
        'Do not repeat the accepted advice. '
        'Each monthly_saving must be a positive exact integer in dollars, estimated from the past spending amounts. '
        'Return ONLY valid JSON: {"recommendations": [{"action": "...", "category": "...", "monthly_saving": 25}]}'
    )

    response = bedrock.invoke_model(
        modelId=BEDROCK_MODEL_ID,
        contentType='application/json',
        accept='application/json',
        body=json.dumps({
            'anthropic_version': 'bedrock-2023-05-31',
            'max_tokens': 1024,
            'messages': [{'role': 'user', 'content': prompt}],
        }),
    )
    parsed = parse_suggestions_json(extract_bedrock_text(response))
    recommendations = parsed.get('recommendations', [])

    new_suggestions = []
    for rec in recommendations[:3]:
        sid = str(uuid.uuid4())
        item = {
            'PK': f'DATASET#{dataset_id}',
            'SK': f'SUGGESTION#{sid}',
            'category': str(rec.get('category') or category or 'Savings'),
            'action': str(rec.get('action') or 'Review your spending for opportunities to save.'),
            'monthly_saving': Decimal(str(rec.get('monthly_saving') or 10)),
            'taken': None,
        }
        table.put_item(Item=item)
        new_suggestions.append({
            'suggestion_id': f'SUGGESTION#{sid}',
            'category': item['category'],
            'action': item['action'],
            'monthly_saving': float(item['monthly_saving']),
            'taken': None,
        })

    return new_suggestions


def lambda_handler(event, context):
    body = json.loads(event.get('body') or '{}')
    dataset_id = body.get('dataset_id', DATASET_ID)
    suggestion_id = body.get('suggestion_id')
    accepted = body.get('accepted', False)
    category = body.get('category', '')
    action = body.get('action', '')
    monthly_saving = float(body.get('monthly_saving', 0))
    apply_to_nearest_goal = body.get('apply_to_nearest_goal', False)

    if not suggestion_id:
        return api_response(400, {'error': 'suggestion_id required'})

    pk = f'DATASET#{dataset_id}'
    normalized_id = normalize_suggestion_id(suggestion_id)
    sk = f'SUGGESTION#{normalized_id}'
    updated_goal = None

    if accepted:
        table.put_item(Item={
            'PK': pk,
            'SK': sk,
            'category': category,
            'action': action,
            'monthly_saving': Decimal(str(monthly_saving)),
            'taken': True,
        })

        if apply_to_nearest_goal:
            updated_goal = apply_saving_to_nearest_goal(dataset_id, monthly_saving)

        new_suggestions = generate_replacement_suggestions(dataset_id, action, category)
        return api_response(200, {
            'message': 'Suggestion accepted',
            'suggestion_id': normalized_id,
            'updatedGoal': updated_goal,
            'newSuggestions': new_suggestions,
        })
    else:
        table.delete_item(Key={'PK': pk, 'SK': sk})
        return api_response(200, {
            'message': 'Suggestion rejected',
            'suggestion_id': normalized_id,
        })
