import json
import os
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional

import boto3
from boto3.dynamodb.conditions import Key
from fastapi import APIRouter

router = APIRouter(tags=["transactions"])

TRANSACTIONS_TABLE = os.environ.get("TRANSACTIONS_TABLE", "puran-transactions-dev")
GOALS_TABLE = os.environ.get("GOALS_TABLE", "puran-goals-dev")
DATA_BUCKET = os.environ.get("DATA_BUCKET", "")
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
QUICKSIGHT_ACCOUNT_ID = os.environ.get("QUICKSIGHT_ACCOUNT_ID", "")
QUICKSIGHT_NAMESPACE = os.environ.get("QUICKSIGHT_NAMESPACE", "default")
USER_ID = os.environ.get("USER_ID", "demo-user")

_dynamodb = boto3.resource("dynamodb")
_s3 = boto3.client("s3")
_bedrock = boto3.client("bedrock-runtime")
_quicksight = boto3.client("quicksight")

transactions_table = _dynamodb.Table(TRANSACTIONS_TABLE)
goals_table = _dynamodb.Table(GOALS_TABLE)


@router.post("/upload")
def get_upload_url():
    batch_id = str(uuid.uuid4())
    key = f"raw/{USER_ID}/{batch_id}.csv"
    url = _s3.generate_presigned_url(
        "put_object",
        Params={"Bucket": DATA_BUCKET, "Key": key, "ContentType": "text/csv"},
        ExpiresIn=300,
    )
    return {"uploadUrl": url, "batchId": batch_id, "key": key}


@router.get("/status/{batch_id}")
def get_status(batch_id: str):
    key = f"processed/{USER_ID}/{batch_id}.csv"
    try:
        _s3.head_object(Bucket=DATA_BUCKET, Key=key)
        return {"batchId": batch_id, "status": "complete"}
    except Exception:
        return {"batchId": batch_id, "status": "processing"}


@router.get("/transactions")
def list_transactions(startDate: Optional[str] = None, endDate: Optional[str] = None):
    key_expr = Key("userId").eq(USER_ID)
    if startDate and endDate:
        key_expr = key_expr & Key("transactionDate").between(startDate, endDate)
    elif startDate:
        key_expr = key_expr & Key("transactionDate").gte(startDate)

    resp = transactions_table.query(
        IndexName="userId-date-index",
        KeyConditionExpression=key_expr,
    )
    return {"transactions": resp.get("Items", [])}


@router.get("/recommendations")
def get_recommendations():
    month_start = datetime.now(timezone.utc).strftime("%Y-%m-01")
    resp = transactions_table.query(
        IndexName="userId-date-index",
        KeyConditionExpression=Key("userId").eq(USER_ID) & Key("transactionDate").gte(month_start),
    )

    category_totals: dict[str, float] = defaultdict(float)
    income = 0.0
    for item in resp.get("Items", []):
        amt = float(item.get("amount", 0))
        if amt > 0:
            income += amt
        else:
            category_totals[item.get("category", "Other")] += abs(amt)

    goals_resp = goals_table.query(KeyConditionExpression=Key("userId").eq(USER_ID))
    active_goals = [
        {"title": g["title"], "target": g["targetAmount"], "current": g["currentAmount"], "deadline": g["deadline"]}
        for g in goals_resp.get("Items", [])
        if g.get("status") == "pending"
    ]

    prompt = (
        "You are a personal finance advisor.\n"
        f"Spending pattern summary for the past 30 days: {dict(category_totals)}\n"
        f"Monthly income: ${income:.2f}.\n"
        f"Active goals: {active_goals}\n\n"
        "Give 3-5 specific, actionable recommendations.\n"
        'Return JSON: { "recommendations": [...], "riskCategories": [...] }'
    )
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": prompt}],
    })
    result = _bedrock.invoke_model(modelId=BEDROCK_MODEL_ID, body=body)
    text = json.loads(result["body"].read())["content"][0]["text"]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw": text}


@router.get("/quicksight/embed")
def get_embed_url(dashboard_id: str):
    region = boto3.session.Session().region_name
    resp = _quicksight.generate_embed_url_for_registered_user(
        AwsAccountId=QUICKSIGHT_ACCOUNT_ID,
        SessionLifetimeInMinutes=60,
        UserArn=f"arn:aws:quicksight:{region}:{QUICKSIGHT_ACCOUNT_ID}:user/{QUICKSIGHT_NAMESPACE}/demo-user",
        ExperienceConfiguration={"Dashboard": {"InitialDashboardId": dashboard_id}},
    )
    return {"embedUrl": resp["EmbedUrl"]}
