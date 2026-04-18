import json
import boto3
from datetime import datetime, UTC
from mock_data import MOCK_TRANSACTIONS, MOCK_GOAL


# ─────────────────────────────────────────────
# STEP 5a — Fetch data
# When teammates finish DynamoDB, delete the
# mock return lines and uncomment the real code
# ─────────────────────────────────────────────

def fetch_transactions(user_id: str) -> list[dict]:
    # ── MOCK (delete when DynamoDB is ready) ──
    return MOCK_TRANSACTIONS
    # ── REAL (uncomment when DynamoDB is ready) ──
    # from boto3.dynamodb.conditions import Key, Attr
    # dynamodb = boto3.resource("dynamodb", region_name="us-west-2")
    # table = dynamodb.Table("transactions")
    # response = table.query(
    #     KeyConditionExpression=Key("user_id").eq(user_id),
    #     FilterExpression=Attr("tx_date").gte("2025-01-01")
    # )
    # return response["Items"]


def fetch_goal(user_id: str) -> dict:
    # ── MOCK (delete when DynamoDB is ready) ──
    return MOCK_GOAL
    # ── REAL (uncomment when DynamoDB is ready) ──
    # from boto3.dynamodb.conditions import Key, Attr
    # dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    # table = dynamodb.Table("goals")
    # response = table.query(
    #     KeyConditionExpression=Key("user_id").eq(user_id),
    #     FilterExpression=Attr("status").eq("active")
    # )
    # return response["Items"][0]


# ─────────────────────────────────────────────
# STEP 5b — Aggregate transactions
# No changes needed here ever
# ─────────────────────────────────────────────

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


# ─────────────────────────────────────────────
# STEP 5c — Build prompt + call Bedrock
# No changes needed here ever
# ─────────────────────────────────────────────

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

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": prompt}],
    })

    response = client.invoke_model(
        modelId="anthropic.claude-3-haiku-20240307-v1:0",
        contentType="application/json",
        accept="application/json",
        body=body,
    )

    text = json.loads(response["body"].read())["content"][0]["text"].strip()

    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]

    return json.loads(text)


# ─────────────────────────────────────────────
# STEP 5d — Main entry point for teammates
# This is the only function main.py calls
# ─────────────────────────────────────────────

def get_recommendations(user_id: str, monthly_income: int) -> dict:
    transactions = fetch_transactions(user_id)
    goal         = fetch_goal(user_id)
    summary      = aggregate_transactions(transactions)
    prompt       = build_prompt(summary, goal, monthly_income)

    # ── MOCK (delete when AWS creds are ready) ──
    
    # ── REAL (uncomment when AWS creds are ready) ──
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
    import json
    result = get_recommendations("test_user", 4500)
    print(json.dumps(result, indent=2, default=str))