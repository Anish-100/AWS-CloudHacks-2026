import boto3
import json
import os
from decimal import Decimal
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TRANSACTIONS_TABLE"])
DEFAULT_DATASET_ID = os.environ.get("DATASET_ID", "demo")
CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "OPTIONS,GET"
}

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

def lambda_handler(event, context):
    if event.get("httpMethod") == "OPTIONS":
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": "{}"}

    params = event.get("queryStringParameters") or {}
    dataset_id = params.get("datasetId") or params.get("dataset_id") or DEFAULT_DATASET_ID

    pk = f"DATASET#{dataset_id}"

    items = []
    query_kwargs = {"KeyConditionExpression": Key("PK").eq(pk)}
    while True:
        response = table.query(**query_kwargs)
        items.extend(response.get("Items", []))

        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break

        query_kwargs["ExclusiveStartKey"] = last_key

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
        "headers": CORS_HEADERS,
        "body": json.dumps({"datasetId": dataset_id, "transactions": transactions})
    }
