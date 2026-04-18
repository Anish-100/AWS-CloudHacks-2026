import json
import os
import boto3
from boto3.dynamodb.conditions import Key
from decimal import Decimal

dynamodb = boto3.resource('dynamodb', region_name='us-west-2')
table = dynamodb.Table('Suggestions')
DATASET_ID = os.environ.get('DATASET_ID', 'demo')


def lambda_handler(event, context):
    body = json.loads(event.get('body') or '{}')
    dataset_id = body.get('dataset_id', DATASET_ID)
    suggestion_id = body.get('suggestion_id')
    accepted = body.get('accepted', False)
    category = body.get('category', '')
    action = body.get('action', '')
    monthly_saving = float(body.get('monthly_saving', 0))

    if not suggestion_id:
        return {'statusCode': 400, 'body': json.dumps({'error': 'suggestion_id required'})}

    pk = f'DATASET#{dataset_id}'
    sk = f'SUGGESTION#{suggestion_id}'

    if accepted:
        table.put_item(Item={
            'PK':             pk,
            'SK':             sk,
            'category':       category,
            'action':         action,
            'monthly_saving': Decimal(str(monthly_saving)),
            'taken':          True,
        })
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'message': 'Suggestion accepted and stored', 'suggestion_id': suggestion_id}),
        }
    else:
        # Delete all non-taken suggestions for this dataset
        response = table.query(
            KeyConditionExpression=Key('PK').eq(pk) & Key('SK').begins_with('SUGGESTION#')
        )
        deleted = 0
        with table.batch_writer() as batch:
            for item in response['Items']:
                if not item.get('taken', False):
                    batch.delete_item(Key={'PK': item['PK'], 'SK': item['SK']})
                    deleted += 1

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'message': f'Rejected — deleted {deleted} non-taken suggestions'}),
        }
