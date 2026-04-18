import boto3
import csv
import io
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


def lambda_handler(event, context):
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']

    response = s3.get_object(Bucket=bucket, Key=key)
    content = response['Body'].read().decode('utf-8-sig')
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
