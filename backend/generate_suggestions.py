import boto3
import json
import os
import uuid
from decimal import Decimal
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb')
transactions_table = dynamodb.Table(os.environ.get('TRANSACTIONS_TABLE', 'FinancialTransactions'))
goals_table = dynamodb.Table(os.environ.get('GOALS_TABLE', 'UserGoals'))
suggestions_table = dynamodb.Table(os.environ.get('SUGGESTIONS_TABLE', 'Suggestions'))
DATASET_ID = os.environ.get('DATASET_ID', 'demo')

bedrock = boto3.client('bedrock-runtime', region_name=os.environ.get('AWS_REGION', 'us-east-1'))
MODEL_ID = 'anthropic.claude-3-haiku-20240307-v1:0'

CORS_HEADERS = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'OPTIONS,GET',
}


def lambda_handler(event, context):
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': CORS_HEADERS, 'body': '{}'}

    dataset_id = (event.get('queryStringParameters') or {}).get('datasetId', DATASET_ID)

    # 1. Get transactions — pass raw rows to Bedrock
    txn_resp = transactions_table.query(
        KeyConditionExpression=Key('PK').eq(f'DATASET#{dataset_id}')
    )
    rows = [
        f"{item.get('TransactionDate')} | {item.get('Category', 'Other')} | {item.get('Description', '')} | ${float(item.get('Amount', 0)):.2f}"
        for item in txn_resp.get('Items', [])
        if item.get('entityType') == 'TRANSACTION'
    ]
    spending_summary = '\n'.join(rows) if rows else 'No transactions found'

    # 2. Get active goals
    goals_resp = goals_table.query(
        KeyConditionExpression=Key('PK').eq(f'DATASET#{dataset_id}')
    )
    active_goals = [
        f"{item.get('Description')} (target: ${float(item.get('TotalAmount', 0)):.2f}, saved: ${float(item.get('AmountSaved', 0)):.2f})"
        for item in goals_resp.get('Items', [])
        if item.get('entityType') == 'GOAL' and not item.get('Result', False)
    ]
    goals_summary = '; '.join(active_goals) if active_goals else 'No active goals'

    # 3. Call Bedrock
    prompt = (
        f"You are a personal finance advisor analyzing real transaction data.\n\n"
        f"Transactions (date | category | description | amount):\n{spending_summary}\n\n"
        f"Active savings goals: {goals_summary}\n\n"
        f"Based on the transaction patterns above, give 3-5 specific, actionable recommendations to help reach these goals.\n"
        f"Return ONLY valid JSON: {{\"recommendations\": [{{\"action\": \"...\", \"category\": \"...\", \"monthly_saving\": 0}}]}}"
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
    raw = json.loads(br_response['body'].read())
    text = raw['content'][0]['text']

    # Extract JSON from response
    start = text.find('{')
    end = text.rfind('}') + 1
    recommendations = json.loads(text[start:end]).get('recommendations', [])

    # 4. Store suggestions (clear old non-taken ones first)
    existing = suggestions_table.query(
        KeyConditionExpression=Key('PK').eq(f'DATASET#{dataset_id}')
    )
    with suggestions_table.batch_writer() as batch:
        for item in existing.get('Items', []):
            if not item.get('taken', False):
                batch.delete_item(Key={'PK': item['PK'], 'SK': item['SK']})

    new_suggestions = []
    with suggestions_table.batch_writer() as batch:
        for rec in recommendations:
            sid = str(uuid.uuid4())
            batch.put_item(Item={
                'PK': f'DATASET#{dataset_id}',
                'SK': f'SUGGESTION#{sid}',
                'category': rec.get('category', 'General'),
                'action': rec.get('action', ''),
                'monthly_saving': Decimal(str(rec.get('monthly_saving', 0))),
                'taken': False,
            })
            new_suggestions.append({
                'suggestion_id': f'SUGGESTION#{sid}',
                'category': rec.get('category', 'General'),
                'action': rec.get('action', ''),
                'monthly_saving': float(rec.get('monthly_saving', 0)),
                'taken': False,
            })

    return {
        'statusCode': 200,
        'headers': CORS_HEADERS,
        'body': json.dumps({'dataset_id': dataset_id, 'suggestions': new_suggestions}),
    }
