# API Contracts

All requests go through API Gateway. Base URL set via `VITE_API_URL` env var in the frontend.

---

## 1. GET /goals
**Lambda:** `get_goal_data.py`  
**Trigger:** API Gateway GET

### Request
```
GET /goals?dataset_id={datasetId}
Content-Type: application/json
```
| Header | Value |
|--------|-------|
| Content-Type | application/json |

| Query Param | Type | Required | Default |
|-------------|------|----------|---------|
| dataset_id | string | No | `DATASET_ID` env var |

### Response
```json
{
  "dataset_id": "demo",
  "goals": [
    {
      "description": "string",
      "category": "string",
      "specs": "string",
      "start_date": "YYYY-MM-DD",
      "end_date": "YYYY-MM-DD",
      "duration_days": 10,
      "target_amount": 150.00,
      "amount_saved": 0.00,
      "result": false
    }
  ]
}
```

> **Frontend field mapping:** `description` → `title`, `target_amount` → `targetAmount`, `amount_saved` → `currentAmount`, `end_date` → `deadline`

---

## 2. POST /goals
**Lambda:** ❌ NOT IMPLEMENTED  
**Frontend sends:**
```
POST /goals
Content-Type: application/json
```
| Header | Value |
|--------|-------|
| Content-Type | application/json |

### Request Body
```json
{
  "title": "string",
  "targetAmount": 150.00,
  "currentAmount": 0.00,
  "deadline": "YYYY-MM-DD",
  "type": "short | veryShort",
  "status": "pending"
}
```

### Expected Response
```json
{
  "goalId": "uuid",
  "title": "string",
  "targetAmount": 150.00,
  "currentAmount": 0.00,
  "deadline": "YYYY-MM-DD",
  "status": "pending"
}
```

---

## 3. PUT /goals/{goalId}
**Lambda:** ❌ NOT IMPLEMENTED  
**Frontend sends:**
```
PUT /goals/{goalId}
Content-Type: application/json
```
| Header | Value |
|--------|-------|
| Content-Type | application/json |

### Request Body
```json
{
  "currentAmount": 75.00,
  "status": "pending | achieved | failed"
}
```

---

## 4. DELETE /goals/{goalId}
**Lambda:** ❌ NOT IMPLEMENTED  
**Frontend sends:**
```
DELETE /goals/{goalId}
```

---

## 5. GET /suggestions
**Lambda:** `get_suggestions_data.py`  
**Trigger:** API Gateway GET

### Request
```
GET /suggestions?dataset_id={datasetId}
```
| Query Param | Type | Required | Default |
|-------------|------|----------|---------|
| dataset_id | string | No | `DATASET_ID` env var |

### Response
```json
{
  "dataset_id": "demo",
  "suggestions": [
    {
      "suggestion_id": "SUGGESTION#uuid",
      "category": "string",
      "action": "string",
      "monthly_saving": 15.00,
      "taken": false
    }
  ],
  "total_savings": 0.00
}
```

---

## 6. POST /suggestions
**Lambda:** `post_suggestion_input.py`  
**Trigger:** API Gateway POST

### Request
```
POST /suggestions
Content-Type: application/json
```
| Header | Value |
|--------|-------|
| Content-Type | application/json |

### Request Body
```json
{
  "dataset_id": "string",
  "suggestion_id": "string",
  "accepted": true,
  "category": "string",
  "action": "string",
  "monthly_saving": 15.00
}
```
`suggestion_id` is required. All other fields except `accepted` are only needed when `accepted: true`.

### Response (accepted)
```json
{ "message": "Suggestion accepted and stored", "suggestion_id": "string" }
```

### Response (rejected)
```json
{ "message": "Rejected — deleted N non-taken suggestions" }
```

### Error
```json
{ "error": "suggestion_id required" }
```

---

## 7. GET /upload
**Lambda:** ❌ NOT IMPLEMENTED — needs a presigned-URL generator Lambda  
**Frontend sends:**
```
GET /upload?fileName={name}&contentType={type}
```
| Query Param | Type | Required |
|-------------|------|----------|
| fileName | string | Yes |
| contentType | string | Yes |

### Expected Response
```json
{
  "uploadUrl": "https://s3.amazonaws.com/...",
  "batchId": "uuid"
}
```

---

## 8. PUT {S3 presigned URL}
**Not through API Gateway — direct S3 upload**

### Request
```
PUT {uploadUrl}
Content-Type: text/csv
Body: <raw CSV file bytes>
```
| Header | Value |
|--------|-------|
| Content-Type | text/csv |

CSV format (`uci_student_finance.csv`):
```
Transaction Date,Post Date,Description,Category,Type,Amount,Specs
04/01/2025,04/02/2025,SPOTIFY USA,Entertainment,Sale,-5.99,
```

This PUT triggers `update_financial_data.py` via S3 event notification.

---

## 9. POST /upload-data
**Lambda:** ❌ NOT IMPLEMENTED as HTTP endpoint  
(`post_financial_data.py` is an S3 trigger, not an HTTP handler)

**Frontend sends:**
```
POST /upload-data
Content-Type: text/csv
Body: <raw CSV file bytes>
```
| Header | Value |
|--------|-------|
| Content-Type | text/csv |

---

## 10. GET /user-data
**Lambda:** `get_financial_data.py` (maps here)  
**Trigger:** API Gateway GET

### Request
```
GET /user-data?datasetId={datasetId}
```
| Query Param | Type | Required | Default |
|-------------|------|----------|---------|
| datasetId | string | No | `DATASET_ID` env var |

### Response
```json
{
  "datasetId": "demo",
  "transactions": [
    {
      "date": "YYYY-MM-DD",
      "description": "string",
      "category": "string",
      "type": "Sale",
      "amount": -5.99,
      "specs": "string"
    }
  ]
}
```

> **Note:** `getUserData()` result is not currently stored in App.jsx state — this endpoint is called but its response is discarded.

---

## 11. GET /status/{batchId}
**Lambda:** ❌ NOT IMPLEMENTED  
**Frontend polls this every 3s (up to 12 attempts) after upload**

### Expected Response
```json
{
  "status": "processing | complete | failed"
}
```

---

## 12. POST /bedrock-categorize
**Lambda:** `ask_bedrock_to_categorize.py`  
**Trigger:** API Gateway POST

### Request
```
POST /bedrock-categorize
Content-Type: application/json
```
| Header | Value |
|--------|-------|
| Content-Type | application/json |

### Request Body
```json
{
  "user_id": "string",
  "monthly_income": 4500
}
```

### Response
```json
{
  "user_id": "string",
  "generated_at": "ISO-8601",
  "goal": {
    "description": "string",
    "target": 150.00,
    "saved": 0.00,
    "remaining": 150.00,
    "deadline": "YYYY-MM-DD"
  },
  "spending_summary": {
    "total_spent": 500.00,
    "num_transactions": 30,
    "category_breakdown": [
      { "category": "Food & Drink", "total": 120.00, "pct_of_spend": 24.0 }
    ],
    "anomalies": [
      { "specs": "string", "amount": 75.00, "date": "YYYY-MM-DD" }
    ]
  },
  "patterns": ["observation 1", "observation 2"],
  "suggestions": [
    { "category": "string", "action": "string", "monthly_saving": 15 }
  ],
  "projections": {
    "eta_current_pace": "YYYY-MM-DD",
    "eta_if_improved": "YYYY-MM-DD",
    "days_saved": 10
  },
  "sim_params": {
    "on_track": false,
    "severity": "green | amber | red"
  }
}
```

---

## 13. S3 Event → update_financial_data.py
**Not an HTTP endpoint — fires automatically on S3 PutObject**

S3 key must follow format: `{datasetId}/filename.csv`  
Lambda env vars required: `TRANSACTIONS_TABLE`

---

## 14. S3 Event → post_goals_data.py
**Not an HTTP endpoint — fires automatically on S3 PutObject**

Lambda env vars required: `DYNAMO_TABLE_NAME`, `DATASET_ID`

CSV format (`uci_student_goals.csv`):
```
StartDate,EndDate,Duration,Description,Category,Specs,AmountSaved,Result
04/01/2025,04/11/2025,10,ROLLING LOUD TICKETS,Entertainment,Concert,150,true
```

---

## Missing Lambda Implementations

| Frontend Call | Status | What's Needed |
|---------------|--------|---------------|
| `GET /upload` | ❌ Missing | Lambda that calls `s3.generate_presigned_url('put_object')` and returns `{uploadUrl, batchId}` |
| `POST /goals` | ❌ Missing | Lambda that writes goal to DynamoDB with frontend field names |
| `PUT /goals/{id}` | ❌ Missing | Lambda that updates `AmountSaved` and `Result` in DynamoDB |
| `DELETE /goals/{id}` | ❌ Missing | Lambda that deletes goal item from DynamoDB |
| `GET /status/{batchId}` | ❌ Missing | Lambda that checks processing state (or simplify: remove polling) |
| `POST /upload-data` | ❌ Missing | Wrap `post_financial_data.py` with HTTP POST handler |

## Frontend ↔ Backend Field Name Mismatches

| Frontend field | Backend field |
|----------------|---------------|
| `title` | `Description` |
| `targetAmount` | `TotalAmount` / `target_amount` |
| `currentAmount` | `AmountSaved` / `amount_saved` |
| `deadline` | `EndDate` / `end_date` |
| `goalId` | `SK` (e.g. `GOAL#2025-04-01#0000`) |
| `datasetId` (camelCase) | `dataset_id` (snake_case) in goals/suggestions |
