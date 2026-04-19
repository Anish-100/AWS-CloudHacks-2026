import json
import os
from datetime import datetime
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('SUGGESTIONS_TABLE', 'Suggestions'))
goals_table = dynamodb.Table(os.environ.get('GOALS_TABLE', 'UserGoals'))

DATASET_ID = os.environ.get('DATASET_ID', 'demo')


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
        message = 'Suggestion accepted and stored'
    else:
        table.delete_item(Key={'PK': pk, 'SK': sk})
        message = 'Suggestion rejected'

    return api_response(200, {
        'message': message,
        'suggestion_id': normalized_id,
        'updatedGoal': updated_goal,
    })
