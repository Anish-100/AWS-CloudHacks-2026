import boto3
import csv
import io
import os
import time
from decimal import Decimal
from datetime import datetime

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['DYNAMO_TABLE_NAME'])
DATASET_ID = os.environ['DATASET_ID']

def lambda_handler(event, context):
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']

    response = s3.get_object(Bucket=bucket, Key=key)
    content = response['Body'].read().decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(content))

    items = []
    for row_num, row in enumerate(reader):
        raw_date = row['Transaction Date'].strip()
        parsed_date = datetime.strptime(raw_date, '%m/%d/%Y').strftime('%Y-%m-%d')

        item = {
            'PK': f"DATASET#{DATASET_ID}",
            'SK': f"TXN#{parsed_date}#{row_num:04d}",
            'entityType': 'TRANSACTION',
            'TransactionDate': parsed_date,
            'Description': row['Description'].strip(),
            'Category': row['Category'].strip(),
            'Type': row['Type'].strip(),
            'Amount': Decimal(row['Amount'].strip()),
            'Specs': row['Specs'].strip(),
            'MonthBucket': parsed_date[:7]
        }
        items.append(item)

    # Batch write in groups of 25
    success, failed = 0, 0
    for i in range(0, len(items), 25):
        batch = items[i:i+25]
        retries = 3
        while batch and retries > 0:
            response = table.meta.client.batch_write_item(
                RequestItems={
                    table.name: [{'PutRequest': {'Item': item}} for item in batch]
                }
            )
            unprocessed = response.get('UnprocessedItems', {}).get(table.name, [])
            batch = [r['PutRequest']['Item'] for r in unprocessed]
            if batch:
                time.sleep(0.5)
                retries -= 1
        success += 25 - len(batch)
        failed += len(batch)

    print(f"Done. Success: {success}, Failed: {failed}")
    return {'success': success, 'failed': failed}