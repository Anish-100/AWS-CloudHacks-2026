import json
import os
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ.get("TRANSACTIONS_TABLE", "FinancialTransactions"))
DEFAULT_DATASET_ID = os.environ.get("DATASET_ID", "demo")


def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


def parse_transaction_date(item):
    if item.get("TransactionDate"):
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
    dataset_id = params.get("datasetId") or params.get("dataset_id") or DEFAULT_DATASET_ID

    pk = f"DATASET#{dataset_id}"

    items = []
    last_key = None
    while True:
        kwargs = {
            "KeyConditionExpression": Key("PK").eq(pk) & Key("SK").begins_with("TXN#"),
        }
        if last_key:
            kwargs["ExclusiveStartKey"] = last_key
        response = table.query(**kwargs)
        items.extend(response.get("Items", []))
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break

    transactions = [
        {
            "date": parse_transaction_date(item),
            "description": item.get("Description", ""),
            "category": item.get("Category", ""),
            "type": item.get("Type", ""),
            "amount": float(item.get("Amount", 0)),
            "specs": item.get("Specs", ""),
        }
        for item in items
    ]

    transactions.sort(key=lambda x: x["date"] or "", reverse=True)

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "OPTIONS,GET",
        },
        "body": json.dumps(
            {"datasetId": dataset_id, "transactions": transactions},
            default=decimal_default,
        ),
    }

