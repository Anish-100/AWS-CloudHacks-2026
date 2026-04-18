# Puran — Short-Term Financial Goal Tracker
### AWS CloudHacks 2026 @ UCI

**Team:** Anish Bhandarkar, Ethan Nguyen, Robert Ledoux, Vineel Bhattiprolu

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                     AWS Amplify  (React Frontend)                    │
│                                                                      │
│  ┌─────────────┐   ┌──────────────────────┐   ┌───────────────────┐ │
│  │  CSV Upload │   │  Forest Simulation   │   │  Goals Dashboard  │ │
│  │  (drag-drop)│   │  (React canvas)      │   │  Progress bars    │ │
│  └──────┬──────┘   └──────────────────────┘   └──────────────────-┘ │
│         │                                      ┌───────────────────┐ │
│         │                                      │ QuickSight Embed  │ │
│         │                                      │ (Spending graphs) │ │
│         │                                      └───────────────────┘ │
└─────────┼────────────────────────────────────────────────────────────┘
          │ HTTPS
          ▼
┌─────────────────────┐
│  API Gateway (REST) │
│  /upload  /goals    │
│  /recs  /status     │
└──────────┬──────────┘
           │
    ┌──────▼──────────────────────────────────────────────┐
    │               FastAPI on Lambda (Mangum)            │
    │                                                     │
    │  POST /upload   →  generate pre-signed S3 URL       │
    │  GET  /goals    →  read Goals table                 │
    │  POST /goals    →  write Goals table                │
    │  GET  /recs     →  aggregate patterns → Bedrock     │
    │  GET  /status   →  CSV processing job status        │
    └──────────────────────────────────────────────────────┘

S3 Upload Flow:
  Browser ──PUT──► S3 Bucket (raw/)
                       │ S3 Event (ObjectCreated)
                       ▼
              ┌────────────────────────────────────────────┐
              │         csv-processor Lambda               │
              │  1. Parse CSV                              │
              │  2. Bedrock (Haiku): add `specs` column    │
              │     (fine-grained subcategory per row)     │
              │  3. Write rows → DynamoDB Transactions     │
              │  4. Write enriched CSV → S3 (processed/)  │
              │     (QuickSight data source)               │
              └────────────────────────────────────────────┘
                       │
          ┌────────────┴──────────────┐
          ▼                           ▼
  DynamoDB Transactions        S3 processed/
  (API queries, goals           (QuickSight SPICE
   progress tracking)            ingestion)
          │
          ▼
  DynamoDB Goals Table
  (short + very-short goals)
```

---

## AWS Services

| Service | Purpose |
|---|---|
| **AWS Amplify** | Host React frontend, CI/CD from GitHub |
| **Amazon S3** | Store raw CSV uploads + enriched CSV for QuickSight |
| **AWS Lambda** | FastAPI app (Mangum) + csv-processor |
| **Amazon API Gateway** | REST API between React and FastAPI |
| **Amazon DynamoDB** | Transactions table + Goals table |
| **Amazon Bedrock** | Claude 3 Haiku — transaction categorization + spending recommendations |
| **Amazon QuickSight** | Embedded spending graphs (reads from S3 via SPICE) |
| **AWS IAM** | Lambda execution roles |

---

## Data Models

### DynamoDB — `puran-transactions`

| Field | Type | Notes |
|---|---|---|
| `userId` | String (PK) | Hardcoded `"demo-user"` for now |
| `transactionId` | String (SK) | UUID on ingest |
| `transactionDate` | String | ISO 8601, GSI sort key |
| `amount` | Number | Positive = income, negative = expense |
| `category` | String | Top-level: Food, Transport, Rent, etc. |
| `specs` | String | Bedrock subcategory (e.g. "Fast Food – Lunch") |
| `merchant` | String | From CSV |
| `uploadBatch` | String | S3 key of source CSV |

### DynamoDB — `puran-goals`

| Field | Type | Notes |
|---|---|---|
| `userId` | String (PK) | `"demo-user"` |
| `goalId` | String (SK) | UUID |
| `title` | String | User-entered description |
| `targetAmount` | Number | Savings target in $ |
| `currentAmount` | Number | Running progress |
| `deadline` | String | ISO date |
| `type` | String | `"short"` (≤3 months) or `"veryShort"` (≤7 days) |
| `status` | String | `pending` / `achieved` / `failed` |

---

## Bedrock Prompt Design

### 1. Transaction Categorization (batch, called during CSV ingest)

```
You are a financial transaction categorizer.
Given transactions with merchant names and amounts, return a JSON array
adding a "specs" field — a concise subcategory string (max 5 words).

Transactions: {transactions_json}

Return ONLY valid JSON. No explanation.
```

### 2. Spending Recommendations (called with aggregated patterns only — NOT raw data)

```
You are a personal finance advisor.
Spending pattern summary for the past 30 days: {spending_patterns}
Monthly income: ${income}. Fixed costs (rent + utilities): ${fixed_costs}.
Active goals: {goals_summary}

Give 3-5 specific, actionable recommendations.
Return JSON: { "recommendations": [...], "riskCategories": [...] }
```

---

## API Routes (FastAPI)

| Method | Path | Description |
|---|---|---|
| POST | `/upload` | Returns pre-signed S3 PUT URL for CSV upload |
| GET | `/status/{batch_id}` | Check if CSV processing is complete |
| GET | `/transactions` | List categorized transactions (query by date range) |
| GET | `/recommendations` | Aggregate patterns → Bedrock → return recs |
| GET | `/goals` | List all goals |
| POST | `/goals` | Create a goal |
| PUT | `/goals/{goal_id}` | Update goal progress or status |
| DELETE | `/goals/{goal_id}` | Delete a goal |
| GET | `/quicksight/embed` | Return QuickSight embedded dashboard URL |

---

## QuickSight Integration

**Data flow:** `csv-processor` Lambda writes enriched CSV to `s3://puran-data/processed/{userId}/{batch}.csv`

**QuickSight setup (one-time, manual for hackathon):**
1. Create S3 manifest file pointing to `processed/` prefix
2. Create QuickSight DataSource → S3
3. Create QuickSight DataSet with SPICE ingestion
4. Build analyses: spending by category (bar), spending over time (line), category breakdown (pie)
5. Publish Dashboard
6. Enable embedded URL generation (domain whitelist = Amplify URL)

**React integration:**
```
GET /quicksight/embed
  → FastAPI calls quicksight.generate_embed_url_for_anonymous_user()
  → returns { embedUrl: "https://..." }
  → React renders <iframe src={embedUrl} />
```

> Note: QuickSight embedding requires either Q (paid tier) or the free 1-session-per-account for anonymous embedding. For the demo, use a named user embedded URL via `generate_embed_url_for_registered_user` with a test QuickSight user.

---

## Forest Simulation Logic

```
trees_alive  = count(goals where status == "achieved")
trees_burned = count(goals where status == "failed")
trees_active = count(goals where status == "pending")

Display:
  - Green trees = achieved goals
  - Burning/dead trees = failed goals
  - Saplings = pending goals
```

Implement as a React component using HTML Canvas or an SVG sprite sheet. No external library needed.

---

## Implementation Spectrum

### Level 1 — MVP / Demo (must ship)

- [ ] S3 bucket + pre-signed URL upload working
- [ ] `csv-processor` Lambda: parse CSV → Bedrock specs → DynamoDB write + S3 processed write
- [ ] FastAPI app with `/upload`, `/goals` CRUD, `/transactions`
- [ ] API Gateway wired to FastAPI Lambda (Mangum)
- [ ] Amplify hosting for React app
- [ ] Upload screen: drag-drop CSV, show "Processing…" status
- [ ] Goals dashboard: create goal (title, amount, deadline, type), progress bars
- [ ] Short-term vs very-short-term goals split view
- [ ] Forest: static sprite display (trees count = achieved goals, dead trees = failed)
- [ ] QuickSight dashboard manually set up, embedded in React via iframe

### Level 2 — Full Feature

- [ ] `/recommendations` endpoint: aggregate patterns → Bedrock → display in React panel
- [ ] Monthly budget input stored per user (income, rent, utilities)
- [ ] `/status/{batch_id}` polling so frontend shows real-time upload → processing state
- [ ] Auto-update goal status: EventBridge daily rule → Lambda checks deadline vs progress
- [ ] Forest animation: CSS/canvas transition when goal achieved (grow) or failed (burn)
- [ ] QuickSight SPICE refresh triggered by Lambda after each CSV ingest
- [ ] Transaction filter/search UI (by category, date range, specs)

### Level 3 — Stretch

- [ ] WebSocket API Gateway for real-time CSV processing notifications
- [ ] Multi-CSV upload history with batch selector
- [ ] Spending forecast: extrapolate category trends 4 weeks forward (math only, no ML)
- [ ] Amazon SES email when a very-short-term goal is 1 day from deadline
- [ ] Forest screenshot export (`canvas.toDataURL`)

---

## Development Phases

| Phase | Tasks | When |
|---|---|---|
| **1. Infra** | Deploy CloudFormation, verify S3→Lambda trigger, DynamoDB writes | Day 1 AM |
| **2. Backend** | `csv-processor`, FastAPI routes, Bedrock calls, API Gateway | Day 1 AM–PM |
| **3. QuickSight** | Create datasource, dataset, dashboard, embed URL | Day 1 PM |
| **4. Frontend** | Upload flow, goals dashboard, forest component, QuickSight iframe | Day 1 PM – Day 2 AM |
| **5. Polish** | Recommendations panel, animations, end-to-end test with UCI dataset | Day 2 AM |

---

## Budget Estimate (Demo Scale)

| Service | Est. Cost |
|---|---|
| Lambda (500 invocations) | < $0.01 |
| DynamoDB (10K R/W units) | < $0.01 |
| S3 (500MB) | < $0.02 |
| Bedrock Haiku (~300 calls) | ~$0.05 |
| API Gateway (1K requests) | < $0.01 |
| QuickSight (1 author session) | $0 (free trial) or ~$9/mo |
| **Total** | **< $0.15 + QuickSight** |

---

## Open Questions

| # | Question | Status |
|---|---|---|
| 1 | FastAPI on Lambda (Mangum) or separate server (ECS/App Runner)? | Assuming Lambda + Mangum |
| 2 | QuickSight tier — standard or Enterprise for anonymous embedding? | TBD — use named user for demo |
| 3 | Forest simulation: canvas or CSS sprites? | TBD — frontend decision |
| 4 | CSV column names from UCI dataset — confirm headers match ingest parser | Check `uci_student_finance.csv` |
