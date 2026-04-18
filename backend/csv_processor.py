import csv
import io
import json
import os
import uuid
from datetime import datetime, timezone

import boto3

TRANSACTIONS_TABLE = os.environ["TRANSACTIONS_TABLE"]
DATA_BUCKET = os.environ["DATA_BUCKET"]
BEDROCK_MODEL_ID = os.environ["BEDROCK_MODEL_ID"]
USER_ID = os.environ.get("USER_ID", "demo-user")

dynamodb = boto3.resource("dynamodb")
s3_client = boto3.client("s3")
bedrock = boto3.client("bedrock-runtime")

table = dynamodb.Table(TRANSACTIONS_TABLE)

BATCH_SIZE = 20


def handler(event, context):
    record = event["Records"][0]
    bucket = record["s3"]["bucket"]["name"]
    key = record["s3"]["object"]["key"]
    batch_id = key.split("/")[-1].replace(".csv", "")

    obj = s3_client.get_object(Bucket=bucket, Key=key)
    raw = obj["Body"].read().decode("utf-8")
    rows = list(csv.DictReader(io.StringIO(raw)))

    normalized = [_normalize_row(row) for row in rows]

    for i in range(0, len(normalized), BATCH_SIZE):
        batch = normalized[i : i + BATCH_SIZE]
        specs = _get_specs(batch)
        for j, spec in enumerate(specs):
            normalized[i + j]["specs"] = spec

    _write_to_dynamo(normalized, batch_id)
    _write_enriched_csv(normalized, batch_id)

    return {"statusCode": 200, "batchId": batch_id, "rowsProcessed": len(normalized)}


def _normalize_row(row: dict) -> dict:
    # Handle UCI dataset column names and common variants
    return {
        "merchant": row.get("Merchant") or row.get("merchant") or row.get("Description") or "Unknown",
        "amount": float(row.get("Amount") or row.get("amount") or 0),
        "category": row.get("Category") or row.get("category") or "Other",
        "transactionDate": (
            row.get("Date") or row.get("date") or row.get("TransactionDate")
            or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        ),
        "specs": "",
    }


def _get_specs(batch: list[dict]) -> list[str]:
    slim = [{"merchant": r["merchant"], "amount": r["amount"], "category": r["category"]} for r in batch]
    prompt = (
        "You are a financial transaction categorizer.\n"
        "Given transactions with merchant names and amounts, return a JSON array "
        "of concise subcategory strings (max 5 words each), one per transaction.\n\n"
        f"Transactions: {json.dumps(slim)}\n\n"
        "Return ONLY a JSON array of strings. No explanation."
    )
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 512,
        "messages": [{"role": "user", "content": prompt}],
    })
    try:
        resp = bedrock.invoke_model(modelId=BEDROCK_MODEL_ID, body=body)
        text = json.loads(resp["body"].read())["content"][0]["text"]
        specs = json.loads(text)
        if isinstance(specs, list) and len(specs) == len(batch):
            return [str(s) for s in specs]
    except Exception:
        pass
    return ["" for _ in batch]


def _write_to_dynamo(rows: list[dict], batch_id: str) -> None:
    with table.batch_writer() as writer:
        for row in rows:
            writer.put_item(Item={
                "userId": USER_ID,
                "transactionId": str(uuid.uuid4()),
                "transactionDate": row["transactionDate"],
                "amount": str(row["amount"]),
                "category": row["category"],
                "specs": row["specs"],
                "merchant": row["merchant"],
                "uploadBatch": batch_id,
            })


def _write_enriched_csv(rows: list[dict], batch_id: str) -> None:
    out = io.StringIO()
    fieldnames = ["userId", "transactionId", "transactionDate", "amount", "category", "specs", "merchant", "uploadBatch"]
    writer = csv.DictWriter(out, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow({
            "userId": USER_ID,
            "transactionId": str(uuid.uuid4()),
            "transactionDate": row["transactionDate"],
            "amount": row["amount"],
            "category": row["category"],
            "specs": row["specs"],
            "merchant": row["merchant"],
            "uploadBatch": batch_id,
        })
    s3_client.put_object(
        Bucket=DATA_BUCKET,
        Key=f"processed/{USER_ID}/{batch_id}.csv",
        Body=out.getvalue().encode("utf-8"),
        ContentType="text/csv",
    )
