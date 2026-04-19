## Is an AWS sub-function
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

def parse_date(raw: str) -> str:
    # Clean whitespace and handle common formats
    return datetime.strptime(raw.strip(), '%m/%d/%Y').strftime('%Y-%m-%d')

def extract_dataset_id(key: str) -> str:
    """
    Based on the image path: demo/2981645c-e18b-4ce4-a03d-829e145abfad/uci_student_finance.csv
    The ID is the second folder segment (index 1).
    """
    parts = key.split('/')
    # If the path is demo/UUID/file.csv, parts[1] is the UUID
    if len(parts) >= 3:
        return parts[1]
    # Fallback to the first part if the structure is shorter
    if len(parts) >= 2:
        return parts[0]
    return os.environ.get('USER_ID', 'demo')

def lambda_handler(event, context):
    # 1. Parse S3 Event details
    record = event['Records'][0]['s3']
    bucket = record['bucket']['name']
    key = record['object']['key']
    
    # 2. Extract ID from the specific path provided in image
    dataset_id = extract_dataset_id(key)
    print(f"Processing dataset: {dataset_id} from key: {key}")

    # 3. Fetch and Parse CSV
    response = s3.get_object(Bucket=bucket, Key=key)
    # utf-8-sig handles BOM if exported from Excel
    content = response['Body'].read().decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(content))

    items = []
    for row_num, row in enumerate(reader):
        try:
            transaction_date = parse_date(row['Transaction Date'])
            post_date = parse_date(row['Post Date']) if row.get('Post Date', '').strip() else transaction_date

            # Clean currency symbols and commas
            raw_amount = row['Amount'].strip().replace('$', '').replace(',', '')
            amount = Decimal(raw_amount)

            items.append({
                'PK': f"DATASET#{dataset_id}",
                'SK': f"TXN#{transaction_date}#{row_num:06d}",
                'entityType': 'TRANSACTION',
                'UserId': dataset_id,
                'TransactionDate': transaction_date,
                'PostDate': post_date,
                'Description': row['Description'].strip(),
                'Category': row.get('Category', '').strip(),
                'Type': row['Type'].strip(),
                'Amount': amount,
                'Specs': row.get('Specs', '').strip(),
                'MonthBucket': transaction_date[:7], # Useful for GSI filtering by month
            })
        except (InvalidOperation, KeyError, ValueError) as e:
            print(f"Skipping row {row_num} due to error: {e}")
            continue

    # 4. Batch Write to DynamoDB (25 items at a time)
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
            # Handle Throttling / Unprocessed Items
            unprocessed = resp.get('UnprocessedItems', {}).get(table.name, [])
            batch = [r['PutRequest']['Item'] for r in unprocessed]
            if batch:
                time.sleep(0.5)
                retries -= 1
                
        success += (batch_size - len(batch))
        failed += len(batch)

    print(f"Final Report | Dataset: {dataset_id} | Success: {success}, Failed: {failed}")
    return {'datasetId': dataset_id, 'success': success, 'failed': failed}