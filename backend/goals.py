import os
import uuid
from datetime import datetime, timezone
from typing import Optional

import boto3
from boto3.dynamodb.conditions import Key
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/goals", tags=["goals"])

GOALS_TABLE = os.environ.get("GOALS_TABLE", "puran-goals-dev")
USER_ID = os.environ.get("USER_ID", "demo-user")

_dynamodb = boto3.resource("dynamodb")
table = _dynamodb.Table(GOALS_TABLE)


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


@router.get("")
def list_goals():
    resp = table.query(KeyConditionExpression=Key("userId").eq(USER_ID))
    return {"goals": resp.get("Items", [])}


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
    table.put_item(Item=item)
    return item


@router.put("/{goal_id}")
def update_goal(goal_id: str, update: GoalUpdate):
    field_map = {
        "currentAmount": ("#ca", ":ca", str),
        "status":        ("#st", ":st", str),
        "title":         ("#ti", ":ti", str),
        "targetAmount":  ("#ta", ":ta", str),
        "deadline":      ("#dl", ":dl", str),
    }
    expr_parts, names, values = [], {}, {}
    for field, (name_key, val_key, transform) in field_map.items():
        val = getattr(update, field)
        if val is not None:
            expr_parts.append(f"{name_key} = {val_key}")
            names[name_key] = field
            values[val_key] = transform(val)

    if not expr_parts:
        raise HTTPException(status_code=400, detail="No fields to update")

    resp = table.update_item(
        Key={"userId": USER_ID, "goalId": goal_id},
        UpdateExpression="SET " + ", ".join(expr_parts),
        ExpressionAttributeNames=names,
        ExpressionAttributeValues=values,
        ReturnValues="ALL_NEW",
    )
    return resp.get("Attributes", {})


@router.delete("/{goal_id}", status_code=204)
def delete_goal(goal_id: str):
    table.delete_item(Key={"userId": USER_ID, "goalId": goal_id})
