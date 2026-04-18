import csv
import json
import os
import sys
import boto3
from boto3.dynamodb.conditions import Key
from datetime import datetime, timezone
from decimal import Decimal

UTC = timezone.utc
ANOMALY_THRESHOLD = 50.0
CSV_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def _transactions_from_csv() -> list[dict]:
    transactions = []
    with open(os.path.join(CSV_DIR, "uci_student_finance.csv"), newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if row["Type"].strip() != "Sale":
                continue
            amt = abs(float(row["Amount"].strip()))
            tx_date = datetime.strptime(row["Transaction Date"].strip(), "%m/%d/%Y").strftime("%Y-%m-%d")
            transactions.append({
                "tx_date":      tx_date,
                "amount":       amt,
                "category":     row["Category"].strip(),
                "specs":        row["Specs"].strip() or row["Description"].strip(),
                "anomaly_flag": amt > ANOMALY_THRESHOLD,
            })
    return transactions


def _goal_from_csv() -> dict:
    with open(os.path.join(CSV_DIR, "uci_student_goals.csv"), newline="", encoding="utf-8-sig") as f:
        row = next(csv.DictReader(f, skipinitialspace=True))
    end_date = datetime.strptime(row["EndDate"].strip(), "%m/%d/%Y").strftime("%Y-%m-%d")
    target = float(row["AmountSaved"].strip())
    return {
        "description":     row["Description"].strip(),
        "target_amount":   Decimal(str(target)),
        "current_savings": Decimal("0"),
        "deadline":        end_date,
    }


def fetch_transactions(user_id: str) -> list[dict]:
    try:
        dynamodb = boto3.resource("dynamodb", region_name="us-west-2")
        table = dynamodb.Table("FinancialTransactions")
        response = table.query(
            KeyConditionExpression=Key("PK").eq(f"DATASET#{user_id}") & Key("SK").begins_with("TXN#")
        )
        transactions = []
        for item in response["Items"]:
            amt = abs(float(item["Amount"]))
            transactions.append({
                "tx_date":      item["TransactionDate"],
                "amount":       amt,
                "category":     item["Category"],
                "specs":        item.get("Specs") or item.get("Description", ""),
                "anomaly_flag": item["Type"] == "Sale" and amt > ANOMALY_THRESHOLD,
            })
        return transactions
    except Exception as e:
        code = getattr(getattr(e, 'response', {}), 'get', lambda *a: '')('Error', {}).get('Code', '') if hasattr(e, 'response') else ''
        if 'ResourceNotFoundException' in str(e) or 'AccessDeniedException' in str(e):
            print("[pipeline] DynamoDB not available — falling back to CSV")
            return _transactions_from_csv()
        raise


def fetch_goal(user_id: str) -> dict:
    try:
        dynamodb = boto3.resource("dynamodb", region_name="us-west-2")
        table = dynamodb.Table("UserGoals")
        response = table.query(
            KeyConditionExpression=Key("PK").eq(f"DATASET#{user_id}") & Key("SK").begins_with("GOAL#")
        )
        item = response["Items"][0]
        return {
            "description":     item["Description"],
            "target_amount":   item["TotalAmount"],
            "current_savings": item["AmountSaved"],
            "deadline":        item["EndDate"],
        }
    except Exception as e:
        if 'ResourceNotFoundException' in str(e) or 'AccessDeniedException' in str(e):
            print("[pipeline] DynamoDB not available — falling back to CSV")
            return _goal_from_csv()
        raise


def aggregate_transactions(transactions: list[dict]) -> dict:
    category_totals = {}
    anomalies = []

    for tx in transactions:
        cat = tx["category"]
        amt = float(tx["amount"])
        category_totals[cat] = category_totals.get(cat, 0) + amt
        if tx["anomaly_flag"]:
            anomalies.append({
                "specs":  tx["specs"],
                "amount": amt,
                "date":   tx["tx_date"],
            })

    total_spent = sum(category_totals.values())
    sorted_cats = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)

    category_breakdown = [
        {
            "category":     cat,
            "total":        round(amt, 2),
            "pct_of_spend": round((amt / total_spent) * 100, 1),
        }
        for cat, amt in sorted_cats
    ]

    return {
        "total_spent":        round(total_spent, 2),
        "category_breakdown": category_breakdown,
        "anomalies":          anomalies,
        "num_transactions":   len(transactions),
    }


def build_prompt(summary: dict, goal: dict, monthly_income: int) -> str:
    remaining = float(goal["target_amount"]) - float(goal["current_savings"])

    cats = "\n".join(
        f"  - {c['category']}: ${c['total']} ({c['pct_of_spend']}% of spend)"
        for c in summary["category_breakdown"]
    )
    anomaly_lines = "\n".join(
        f"  - {a['specs']}: ${a['amount']} on {a['date']}"
        for a in summary["anomalies"]
    ) or "  None"

    return f"""
You are a personal finance advisor. Analyze this user's spending and return ONLY a JSON object — no markdown, no preamble.

USER FINANCIAL SNAPSHOT:
- Monthly income (after tax): ${monthly_income}
- Total spent this month: ${summary["total_spent"]}
- Number of transactions: {summary["num_transactions"]}

SPENDING BY CATEGORY:
{cats}

ANOMALOUS SPIKES FLAGGED:
{anomaly_lines}

CURRENT GOAL:
- Goal: {goal["description"]}
- Target: ${float(goal["target_amount"]):.2f}
- Already saved: ${float(goal["current_savings"]):.2f}
- Still needed: ${remaining:.2f}
- Deadline: {goal["deadline"]}

Return ONLY this JSON structure:
{{
  "patterns": ["<observation 1>", "<observation 2>", "<observation 3>"],
  "suggestions": [
    {{"category": "<category>", "action": "<what to do>", "monthly_saving": <number>}},
    ...
  ],
  "goal_eta_current_pace": "<date as YYYY-MM-DD>",
  "goal_eta_if_suggestions_followed": "<date as YYYY-MM-DD>",
  "days_saved": <number>,
  "sim_params": {{
    "on_track": <true or false>,
    "severity": "<green | amber | red>"
  }}
}}
""".strip()


def call_bedrock(prompt: str) -> dict:
    client = boto3.client("bedrock-runtime", region_name="us-west-2")
    response = client.invoke_model(
        modelId="us.amazon.nova-micro-v1:0",
        contentType="application/json",
        accept="application/json",
        body=json.dumps({"messages": [{"role": "user", "content": [{"text": prompt}]}]}),
    )
    text = json.loads(response["body"].read())["output"]["message"]["content"][0]["text"].strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text)


def get_recommendations(user_id: str, monthly_income: int) -> dict:
    transactions = fetch_transactions(user_id)
    goal = fetch_goal(user_id)
    summary = aggregate_transactions(transactions)
    prompt = build_prompt(summary, goal, monthly_income)
    ai_output = call_bedrock(prompt)

    return {
        "user_id":      user_id,
        "generated_at": datetime.now(UTC).isoformat(),
        "goal": {
            "description": goal["description"],
            "target":      float(goal["target_amount"]),
            "saved":       float(goal["current_savings"]),
            "remaining":   float(goal["target_amount"]) - float(goal["current_savings"]),
            "deadline":    goal["deadline"],
        },
        "spending_summary": summary,
        "patterns":    ai_output["patterns"],
        "suggestions": ai_output["suggestions"],
        "projections": {
            "eta_current_pace": ai_output["goal_eta_current_pace"],
            "eta_if_improved":  ai_output["goal_eta_if_suggestions_followed"],
            "days_saved":       ai_output["days_saved"],
        },
        "sim_params": ai_output["sim_params"],
    }


if __name__ == "__main__":
    result = get_recommendations("demo", 4500)
    print(json.dumps(result, indent=2, default=str))


def lambda_handler(event, context):
    body = json.loads(event.get("body") or "{}")
    user_id = body.get("user_id", "demo")
    monthly_income = int(body.get("monthly_income", 4500))
    result = get_recommendations(user_id, monthly_income)
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(result, default=str),
    }
