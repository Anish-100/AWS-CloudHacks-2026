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
    reader = csv.DictReader(io.StringIO(content), skipinitialspace=True)


    items = []
    for row_num, row in enumerate(reader):
        raw_start = row['StartDate'].strip()
        raw_end = row['EndDate'].strip()
        parsed_start = datetime.strptime(raw_start, '%m/%d/%Y').strftime('%Y-%m-%d')
        parsed_end = datetime.strptime(raw_end, '%m/%d/%Y').strftime('%Y-%m-%d')

        item = {
            'PK': f"DATASET#{DATASET_ID}",
            'SK': f"GOAL#{parsed_start}#{row_num:04d}",
            'entityType': 'GOAL',
            'StartDate': parsed_start,
            'EndDate': parsed_end,
            'Duration': int(row['Duration'].strip()),
            'Description': row['Description'].strip(),
            'Category': row['Category'].strip(),
            'Specs': row['Specs'].strip(),
            'TotalAmount': Decimal(row['AmountSaved'].strip()),
            'AmountSaved': Decimal('0'),
            'Result': row['Result'].strip().lower() == 'true'
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