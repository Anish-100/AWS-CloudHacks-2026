import json
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

import boto3
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/goals", tags=["goals"])

GOALS_LAMBDA = os.environ.get("GOALS_LAMBDA", "UserGoals-handler")
USER_ID = os.environ.get("USER_ID", "demo-user")

_lambda = boto3.client("lambda")


# ── Lambda invocation helper ──────────────────────────────────────────────────
# Assumption: Goals Lambda accepts { "action": "...", "data": { ... } }
# and returns { "items": [...] } or { "item": {...} }
# Update action names / payload shape to match teammate's actual implementation.

def _invoke(action: str, data: dict) -> dict:
    resp = _lambda.invoke(
        FunctionName=GOALS_LAMBDA,
        InvocationType="RequestResponse",
        Payload=json.dumps({"action": action, "data": data}),
    )
    result = json.loads(resp["Payload"].read())
    if resp.get("FunctionError"):
        raise HTTPException(status_code=500, detail=result)
    return result


# ── Models ────────────────────────────────────────────────────────────────────

class GoalCreate(BaseModel):
    title: str
    targetAmount: float
    deadline: str
    type: str  # "short" | "veryShort"


class GoalUpdate(BaseModel):
    currentAmount: Optional[float] = None
    status: Optional[str] = None  # pending | achieved | failed
    title: Optional[str] = None
    targetAmount: Optional[float] = None
    deadline: Optional[str] = None


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("")
def list_goals():
    result = _invoke("getAll", {"userId": USER_ID})
    return {"goals": result.get("items", [])}


@router.post("", status_code=201)
def create_goal(goal: GoalCreate):
    item = {
        "userId": USER_ID,
        "goalId": str(uuid.uuid4()),
        "title": goal.title,
        "targetAmount": str(goal.targetAmount),
        "currentAmount": "0",
        "deadline": goal.deadline,
        "type": goal.type,
        "status": "pending",
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    result = _invoke("create", item)
    return result.get("item", item)


@router.put("/{goal_id}")
def update_goal(goal_id: str, update: GoalUpdate):
    updates = {k: v for k, v in update.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = _invoke("update", {"userId": USER_ID, "goalId": goal_id, **updates})
    return result.get("item", {})


@router.delete("/{goal_id}", status_code=204)
def delete_goal(goal_id: str):
    _invoke("delete", {"userId": USER_ID, "goalId": goal_id})
