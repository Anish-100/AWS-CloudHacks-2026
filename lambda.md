# Lambda Functions — Puran

This doc tracks (1) the Lambdas we've committed to build, (2) additional Lambdas we probably need for a working MVP, and (3) optional ones for stretch features.

---

## Core Lambdas (in [cloudformation.yaml](cloudformation.yaml))

| Lambda | Method | Path | Owner | Status |
|---|---|---|---|---|
| `UploadFunction` | POST | `/upload` | TBD | placeholder |
| `UploadGoalFunction` | POST | `/goals` | TBD | placeholder |
| `CategorizeGoalFunction` | POST | `/goals/categorize` | TBD | placeholder |
| `GetGoalsFunction` | GET | `/goals` | TBD | placeholder |
| `GetUserDataFunction` | GET | `/user-data` | TBD | placeholder |
| `GetSuggestionsFunction` | GET | `/suggestions` | TBD | placeholder |
| `PostSuggestionFunction` | POST | `/suggestions` | TBD | placeholder |
| `GenerateSuggestionsFunction` | GET | `/suggestions/generate` | TBD | placeholder |

---

## Additional Lambdas we should add

These aren't in the CF template yet but will be needed for a real demo. In priority order:

### 1. `UpdateGoalFunction` — PUT `/goals/{goalId}` **[HIGH]**
User needs to mark progress (`currentAmount`) and flip status to `achieved`/`failed`. Without this, the forest simulation stays frozen at "all pending."
- **Input:** `{ goalId, currentAmount?, status?, title?, deadline? }`
- **Writes:** `UserGoals` table

### 2. `DeleteGoalFunction` — DELETE `/goals/{goalId}` **[HIGH]**
Needed so the goals dashboard has a working delete button.
- **Input:** `{ goalId }`
- **Writes:** `UserGoals` table

### 3. `CsvProcessorFunction` — S3-triggered, no API Gateway **[MED]**
If `UploadFunction` gets too slow (CSV parse + Bedrock categorization + DynamoDB writes all synchronous), offload the heavy work:
- `UploadFunction` only writes raw CSV to S3 and returns a `batchId` immediately
- S3 `ObjectCreated` event fires `CsvProcessorFunction` which does Bedrock + DynamoDB async
- Requires a `/status/{batchId}` endpoint so the frontend can poll

### 4. `GetStatusFunction` — GET `/status/{batchId}` **[MED]**
Pairs with (3). Frontend polls to show "Processing…" then flips to "Done!" when DynamoDB has rows for that batch.
- **Input:** `batchId` (path param)
- **Reads:** `FinancialTransactions` (checks if any rows exist for this batch)

### 5. `GetQuickSightEmbedFunction` — GET `/quicksight/embed` **[MED]**
The QuickSight dashboard iframe URL has to be generated per-session — can't hardcode.
- **Input:** `dashboardId` (query param)
- **Calls:** `quicksight.generate_embed_url_for_registered_user`

### 6. `GetTransactionsFunction` — GET `/transactions` **[LOW]**
`GetUserDataFunction` returns aggregates; this one returns raw transaction rows with filtering. Only needed if the frontend builds a transaction list view.
- **Input:** `{ startDate?, endDate?, category? }`
- **Reads:** `FinancialTransactions` via `userId-date-index` GSI

---

## Stretch Lambdas (Level 3 only)

### 7. `DailyGoalStatusFunction` — EventBridge scheduled, no API Gateway
Runs daily at midnight. Scans `UserGoals`, flips goals past their deadline to `failed` (or `achieved` if `currentAmount >= targetAmount`). Keeps the forest simulation honest without user action.

### 8. `SendDeadlineEmailFunction` — EventBridge scheduled, no API Gateway
For very-short-term goals within 24h of deadline, send SES email. Pairs with (7).

### 9. `ForecastSpendingFunction` — GET `/forecast`
Pulls last 30 days of transactions, does linear regression per category, returns projected spend for next 4 weeks. Pure math, no ML/Bedrock.

### 10. `ExportForestFunction` — GET `/forest/export`
Generates a shareable image of the forest state. Probably easier client-side (`canvas.toDataURL`).

---

## Event payload convention

To keep Lambda handlers consistent, every function reads from the API Gateway proxy event shape:

```json
{
  "httpMethod": "POST",
  "pathParameters": { "goalId": "abc-123" },
  "queryStringParameters": { "startDate": "2026-04-01" },
  "body": "{\"title\":\"Save for laptop\",\"targetAmount\":1200}"
}
```

And every handler returns:
```json
{
  "statusCode": 200,
  "headers": { "Access-Control-Allow-Origin": "*" },
  "body": "{\"goals\":[...]}"
}
```

---

## Deployment pattern

All Lambdas share one IAM role (`puran-lambda-role-{env}`) and one S3 bucket. To deploy code for any function:

```bash
cd backend/lambda
zip deploy.zip upload.py  # or whichever handler
aws lambda update-function-code \
  --function-name puran-upload-dev \
  --zip-file fileb://deploy.zip
```

For functions with external dependencies (boto3 is pre-installed in Lambda; most others need bundling):
```bash
pip install -r requirements.txt -t package/
cp upload.py package/
cd package && zip -r ../deploy.zip . && cd ..
```
