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
bedrock = boto3.client('bedrock-runtime', region_name=os.environ.get('AWS_REGION', 'us-west-2'))

DATASET_ID = os.environ.get('DATASET_ID', 'demo')
BEDROCK_MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'us.amazon.nova-micro-v1:0')


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
    return payload['output']['message']['content'][0]['text'].strip()


def parse_suggestion_json(text):
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


def generate_replacement_suggestion(dataset_id, previous_action, category, accepted):
    decision = 'accepted' if accepted else 'rejected'
    prompt = (
        'Create one new student-budgeting suggestion after the user '
        f'{decision} this advice: "{previous_action}".\n'
        f'Previous category: {category or "unknown"}.\n'
        f'Active goals:\n{build_goal_context(dataset_id)}\n\n'
        'Return ONLY compact JSON with keys: category, action, monthly_saving. '
        'The action must be specific, friendly, and one sentence. '
        'monthly_saving must be a realistic integer between 5 and 75.'
    )

    response = bedrock.invoke_model(
        modelId=BEDROCK_MODEL_ID,
        contentType='application/json',
        accept='application/json',
        body=json.dumps({'messages': [{'role': 'user', 'content': [{'text': prompt}]}]}),
    )
    suggestion = parse_suggestion_json(extract_bedrock_text(response))

    suggestion_id = str(uuid.uuid4())
    item = {
        'PK': f'DATASET#{dataset_id}',
        'SK': f'SUGGESTION#{suggestion_id}',
        'category': str(suggestion.get('category') or category or 'Savings'),
        'action': str(suggestion.get('action') or 'Move one small purchase toward your nearest goal.'),
        'monthly_saving': Decimal(str(suggestion.get('monthly_saving') or 10)),
        'taken': False,
    }
    table.put_item(Item=item)

    return {
        'suggestion_id': suggestion_id,
        'category': item['category'],
        'action': item['action'],
        'monthly_saving': float(item['monthly_saving']),
        'taken': False,
    }


def lambda_handler(event, context):
    body = json.loads(event.get('body') or '{}')
    dataset_id = body.get('dataset_id', DATASET_ID)
    suggestion_id = body.get('suggestion_id')
    accepted = body.get('accepted', False)
    category = body.get('category', '')
    action = body.get('action', '')
    monthly_saving = float(body.get('monthly_saving', 0))
    apply_to_nearest_goal = body.get('apply_to_nearest_goal', False)
    generate_replacement = body.get('generate_replacement', True)

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
        message = 'Suggestion accepted and stored'
    else:
        table.delete_item(Key={'PK': pk, 'SK': sk})
        message = 'Suggestion rejected'

    new_suggestion = (
        generate_replacement_suggestion(dataset_id, action, category, accepted)
        if generate_replacement
        else None
    )

    return api_response(200, {
        'message': message,
        'suggestion_id': normalized_id,
        'updatedGoal': updated_goal,
        'newSuggestion': new_suggestion,
    })
