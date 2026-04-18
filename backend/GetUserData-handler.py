import boto3
import json
import os
from decimal import Decimal
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["financial_transactions"])
DEFAULT_DATASET_ID = os.environ.get("DATASET_ID", "demo")

def decimal_to_float(value):
    if isinstance(value, Decimal):
        return float(value)
    return value

def parse_transaction_date(item):
    if "TransactionDate" in item and item["TransactionDate"]:
        return item["TransactionDate"]
    sk = item.get("SK", "")
    parts = sk.split("#")
    if len(parts) >= 2:
        return parts[1]
    return None

def get_user_data_handler(event, context):
    params = event.get("queryStringParameters") or {}
    dataset_id = params.get("datasetId", DEFAULT_DATASET_ID)

    pk = f"DATASET#{dataset_id}"

    response = table.query(
        KeyConditionExpression=Key("PK").eq(pk)
    )

    items = response.get("Items", [])

    transactions = [
        {
            "date": parse_transaction_date(item),
            "description": item.get("Description", ""),
            "category": item.get("Category", ""),
            "type": item.get("Type", ""),
            "amount": decimal_to_float(item.get("Amount", Decimal("0"))),
            "specs": item.get("Specs", "")
        }
        for item in items
        if item.get("entityType") == "TRANSACTION"
    ]

    transactions.sort(key=lambda x: x["date"] or "", reverse=True)

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps({"datasetId": dataset_id, "transactions": transactions})
    }