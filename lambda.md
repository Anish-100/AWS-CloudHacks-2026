# Lambda Functions — Puran

## When → Which Lambda

| When this happens | Lambda(s) called (in order) |
|-------------------|------------------------------|
| User opens the app | `get_goal_data` → `get_suggestions_data` |
| User uploads a CSV | `get_presigned_url` → *(S3 trigger)* `update_financial_data` → `get_financial_data` |
| User creates a goal | `post_goal_data` |
| User updates goal progress | `put_goal_data` |
| User deletes a goal | `delete_goal_data` |
| App generates AI suggestions | `ask_bedrock_to_categorize` |
| User accepts a suggestion | `post_suggestion_input` |
| User rejects a suggestion | `post_suggestion_input` (deletes non-taken suggestions) |

---

## All Lambdas

| Lambda | File | Method | Path / Trigger | AWS Trigger |
|--------|------|--------|----------------|-------------|
| `get_presigned_url` | `get_presigned_url.py` | GET | `/upload` | API Gateway |
| `upload_financial_data` | `post_financial_data.py` | S3 event | S3 PutObject | S3 notification |
| `update_financial_data` | `update_financial_data.py` | S3 event | S3 PutObject | S3 notification |
| `post_goal_data` | `post_goal_data.py` | POST | `/goals` | API Gateway |
| `get_goal_data` | `get_goal_data.py` | GET | `/goals` | API Gateway |
| `put_goal_data` | `put_goal_data.py` | PUT | `/goals/{goalId}` | API Gateway |
| `delete_goal_data` | `delete_goal_data.py` | DELETE | `/goals/{goalId}` | API Gateway |
| `ask_bedrock_to_categorize` | `ask_bedrock_to_categorize.py` | POST | `/bedrock-categorize` | API Gateway |
| `get_financial_data` | `get_financial_data.py` | GET | `/user-data` | API Gateway |
| `get_suggestions_data` | `get_suggestions_data.py` | GET | `/suggestions` | API Gateway |
| `post_suggestion_input` | `post_suggestion_input.py` | POST | `/suggestions` | API Gateway |

---

## Full Call Flow

### 1. App Loads (user opens the site)

```
Browser
  → GET /goals?dataset_id={id}          → get_goal_data        → DynamoDB UserGoals
  → GET /suggestions?dataset_id={id}    → get_suggestions_data → DynamoDB Suggestions
```

Both run in parallel on mount. Goals populate the forest canvas and goals dashboard. Suggestions populate the recommendations panel.

---

### 2. User Uploads a CSV File

```
Browser
  │
  ├─ 1. GET /upload?fileName=finance.csv&contentType=text/csv
  │       → get_presigned_url
  │       → s3.generate_presigned_url()
  │       ← { uploadUrl, batchId, key }          key = "{datasetId}/{batchId}/finance.csv"
  │
  ├─ 2. PUT {uploadUrl}                           direct to S3, no Lambda
  │       Content-Type: text/csv
  │       Body: <raw CSV bytes>
  │
  │    S3 receives the file
  │       → fires S3 ObjectCreated event
  │       → update_financial_data               parses CSV → writes to DynamoDB FinancialTransactions
  │
  ├─ 3. POST /upload-data                        (frontend also calls this — no backend yet,
  │                                               can be skipped since S3 trigger handles it)
  │
  ├─ 4. GET /user-data?datasetId={id}
  │       → get_financial_data
  │       → DynamoDB FinancialTransactions query
  │       ← { datasetId, transactions: [...] }
  │
  └─ 5. (optional) GET /status/{batchId}         not implemented — frontend polls up to 12x
```

---

### 3. User Creates a Goal (GoalForm)

```
Browser
  → POST /goals
      Body: { title, targetAmount, currentAmount, deadline, type }
      → post_goal_data
      → DynamoDB UserGoals  PK=DATASET#{id}  SK=GOAL#{uuid}
      ← { goalId, title, targetAmount, currentAmount, deadline, status }

Browser stores returned goalId for future PUT/DELETE calls
```

---

### 4. User Updates Goal Progress

```
Browser
  → PUT /goals/{goalId}
      Body: { currentAmount, status? }
      → put_goal_data
      → DynamoDB UserGoals  update_item on PK+SK
      ← { message: "Goal updated", goalId }
```

---

### 5. User Deletes a Goal

```
Browser
  → DELETE /goals/{goalId}?dataset_id={id}
      → delete_goal_data
      → DynamoDB UserGoals  delete_item on PK+SK
      ← { message: "Goal deleted", goalId }
```

---

### 6. Bedrock Generates Suggestions (called on login or manually)

```
Browser
  → POST /bedrock-categorize
      Body: { user_id, monthly_income }
      → ask_bedrock_to_categorize
          → DynamoDB FinancialTransactions  (fetch all transactions for user)
          → DynamoDB UserGoals              (fetch first goal)
          → Bedrock nova-micro-v1:0         (send spending summary prompt)
          ← AI JSON: { patterns, suggestions, projections, sim_params }
      ← { goal, spending_summary, patterns, suggestions, projections, sim_params }
```

---

### 7. User Accepts or Rejects a Suggestion

```
Browser
  → POST /suggestions
      Body: { dataset_id, suggestion_id, accepted, category, action, monthly_saving }
      → post_suggestion_input
      │
      ├─ if accepted=true  → DynamoDB Suggestions  put_item  (stores suggestion, taken=true)
      └─ if accepted=false → DynamoDB Suggestions  batch delete all non-taken suggestions
      
      ← { message }
```

---

## DynamoDB Tables

| Table | PK | SK | Used By |
|-------|----|----|---------|
| `FinancialTransactions` | `DATASET#{userId}` | `TXN#{date}#{num}` | upload_financial_data, update_financial_data, get_financial_data, ask_bedrock_to_categorize |
| `UserGoals` | `DATASET#{userId}` | `GOAL#{goalId}` | post_goal_data, get_goal_data, put_goal_data, delete_goal_data, ask_bedrock_to_categorize |
| `Suggestions` | `DATASET#{userId}` | `SUGGESTION#{id}` | get_suggestions_data, post_suggestion_input |

---

## Environment Variables per Lambda

| Lambda | Env Vars |
|--------|----------|
| `get_presigned_url` | `UPLOAD_BUCKET`, `USER_ID`, `PRESIGN_EXPIRY` (default 300) |
| `upload_financial_data` | `TRANSACTIONS_TABLE`, `USER_ID` |
| `update_financial_data` | `TRANSACTIONS_TABLE`, `USER_ID` |
| `post_goal_data` | `GOALS_TABLE`, `DATASET_ID` |
| `get_goal_data` | `GOALS_TABLE`, `DATASET_ID` |
| `put_goal_data` | `GOALS_TABLE`, `DATASET_ID` |
| `delete_goal_data` | `GOALS_TABLE`, `DATASET_ID` |
| `get_financial_data` | `financial_transactions`, `DATASET_ID` |
| `get_suggestions_data` | `SUGGESTIONS_TABLE`, `DATASET_ID` |
| `post_suggestion_input` | `SUGGESTIONS_TABLE`, `DATASET_ID` |
| `ask_bedrock_to_categorize` | (uses hardcoded table names + us-west-2 region) |

---

## IAM Permissions per Lambda

| Lambda | Needs |
|--------|-------|
| `get_presigned_url` | `s3:PutObject` on upload bucket |
| `upload_financial_data` | `s3:GetObject`, `dynamodb:BatchWriteItem` |
| `update_financial_data` | `s3:GetObject`, `dynamodb:BatchWriteItem` |
| `post_goal_data` | `dynamodb:PutItem` on UserGoals |
| `get_goal_data` | `dynamodb:Query` on UserGoals |
| `put_goal_data` | `dynamodb:UpdateItem` on UserGoals |
| `delete_goal_data` | `dynamodb:DeleteItem` on UserGoals |
| `get_financial_data` | `dynamodb:Query` on FinancialTransactions |
| `get_suggestions_data` | `dynamodb:Query` on Suggestions |
| `post_suggestion_input` | `dynamodb:PutItem`, `dynamodb:Query`, `dynamodb:BatchWriteItem` on Suggestions |
| `ask_bedrock_to_categorize` | `dynamodb:Query` on both tables, `bedrock:InvokeModel` |

---

## S3 Bucket CORS (required for direct browser upload)

```json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["PUT"],
    "AllowedOrigins": ["*"],
    "ExposeHeaders": []
  }
]
```
