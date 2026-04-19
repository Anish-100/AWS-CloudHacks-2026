import boto3
import base64
import csv
import io
import json
import os
import time
from decimal import Decimal, InvalidOperation
from datetime import datetime

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TRANSACTIONS_TABLE'])
USER_ID = os.environ['USER_ID']


def parse_date(raw: str) -> str:
    return datetime.strptime(raw.strip(), '%m/%d/%Y').strftime('%Y-%m-%d')


def response(status_code: int, payload: dict) -> dict:
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
        },
        'body': json.dumps(payload),
    }


def financial_items_from_csv(content: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(content))

    items = []
    for row_num, row in enumerate(reader):
        transaction_date = parse_date(row['Transaction Date'])
        post_date = parse_date(row['Post Date']) if row.get('Post Date', '').strip() else transaction_date

        raw_amount = row['Amount'].strip().lstrip('$').replace(',', '')
        try:
            amount = Decimal(raw_amount)
        except InvalidOperation:
            print(f"Skipping row {row_num}: invalid amount '{raw_amount}'")
            continue

        items.append({
            'DATASET': f"USER#{USER_ID}",
            'TXN': f"TXN#{transaction_date}#{row_num:06d}",
            'entityType': 'TRANSACTION',
            'UserId': USER_ID,
            'TransactionDate': transaction_date,
            'PostDate': post_date,
            'Description': row['Description'].strip(),
            'Category': row.get('Category', '').strip(),
            'Type': row['Type'].strip(),
            'Amount': amount,
            'Specs': row.get('Specs', '').strip(),
            'MonthBucket': transaction_date[:7],
        })

    return items


def write_items(items: list[dict]) -> dict:
    success, failed = 0, 0
    for i in range(0, len(items), 25):
        batch = items[i:i + 25]
        batch_size = len(batch)
        retries = 3
        while batch and retries > 0:
            resp = table.meta.client.batch_write_item(
                RequestItems={
                    table.name: [{'PutRequest': {'Item': item}} for item in batch]
                }
            )
            unprocessed = resp.get('UnprocessedItems', {}).get(table.name, [])
            batch = [r['PutRequest']['Item'] for r in unprocessed]
            if batch:
                time.sleep(0.5)
                retries -= 1
        success += batch_size - len(batch)
        failed += len(batch)

    print(f"Done. Success: {success}, Failed: {failed}")
    return {'success': success, 'failed': failed}


def csv_content_from_api_event(event: dict) -> str:
    body = event.get('body') or ''
    if event.get('isBase64Encoded'):
        return base64.b64decode(body).decode('utf-8-sig')
    return body


def csv_content_from_s3_event(event: dict) -> str:
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    s3_response = s3.get_object(Bucket=bucket, Key=key)
    return s3_response['Body'].read().decode('utf-8-sig')


def lambda_handler(event, context):
    if event.get('httpMethod') == 'OPTIONS' or event.get('requestContext', {}).get('http', {}).get('method') == 'OPTIONS':
        return response(204, {})

    if event.get('Records'):
        content = csv_content_from_s3_event(event)
    else:
        content = csv_content_from_api_event(event)

    if not content.strip():
        return response(400, {'error': 'CSV body is required'})

    result = write_items(financial_items_from_csv(content))
    return response(200, result)
