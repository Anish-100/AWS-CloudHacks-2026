import json
import os
import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TRANSACTIONS_TABLE'])
bedrock = boto3.client('bedrock-runtime', region_name=os.environ.get('AWS_REGION', 'us-west-2'))


def generate_specs(description: str, category: str, amount: float) -> str:
    prompt = (
        f"Given this bank transaction, write a single concise sentence describing what the purchase likely was.\n\n"
        f"Description: {description}\n"
        f"Category: {category}\n"
        f"Amount: ${amount:.2f}\n\n"
        f"Return ONLY the sentence, no extra text."
    )
    response = bedrock.invoke_model(
        modelId='us.amazon.nova-micro-v1:0',
        contentType='application/json',
        accept='application/json',
        body=json.dumps({'messages': [{'role': 'user', 'content': [{'text': prompt}]}]}),
    )
    return json.loads(response['body'].read())['output']['message']['content'][0]['text'].strip()


def lambda_handler(event, _context):
    updated = 0
    skipped = 0

    for record in event['Records']:
        if record['eventName'] != 'INSERT':
            continue

        new_image = record['dynamodb'].get('NewImage', {})

        if new_image.get('entityType', {}).get('S') != 'TRANSACTION':
            continue

        if new_image.get('Specs', {}).get('S', '').strip():
            skipped += 1
            continue

        pk          = new_image['PK']['S']
        sk          = new_image['SK']['S']
        description = new_image.get('Description', {}).get('S', '')
        category    = new_image.get('Category', {}).get('S', '')
        amount      = float(new_image.get('Amount', {}).get('N', '0'))

        specs = generate_specs(description, category, amount)

        table.update_item(
            Key={'PK': pk, 'SK': sk},
            UpdateExpression='SET Specs = :s',
            ExpressionAttributeValues={':s': specs},
        )
        updated += 1

    print(f"Specs enriched — updated: {updated}, skipped: {skipped}")
    return {'updated': updated, 'skipped': skipped}
