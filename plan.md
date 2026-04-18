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
│  └──────┬──────┘   └──────────────────────┘   └───────────────────┘ │
│         │                                      ┌───────────────────┐ │
│         │                                      │ QuickSight Embed  │ │
│         │                                      │ (Spending graphs) │ │
│         │                                      └───────────────────┘ │
└─────────┼────────────────────────────────────────────────────────────┘
          │ HTTPS
          ▼
┌──────────────────────────────────────────────────────────────────────┐
│                        API Gateway (REST)                            │
│   Each route maps directly to its own Lambda function                │
└──────────┬───────────────────────────────────────────────────────────┘
           │
   ┌───────┴────────────────────────────────────────────────────────┐
   │                                                                │
   ▼                                                                ▼
┌──────────────────────┐    ┌──────────────────────┐   ┌──────────────────────┐
│ UploadFunction       │    │ UploadGoalFunction   │   │ GetGoalsFunction     │
│ POST /upload         │    │ POST /goals          │   │ GET  /goals          │
└──────────┬───────────┘    └──────────┬───────────┘   └──────────┬───────────┘
           │                           │                          │
┌──────────▼───────────┐    ┌──────────▼───────────┐   ┌──────────▼───────────┐
│ CategorizeGoal       │    │ GetUserDataFunction  │   │ GetSuggestions       │
│ POST /goals/         │    │ GET /user-data       │   │ GET /suggestions     │
│   categorize         │    │                      │   │                      │
└──────────┬───────────┘    └──────────┬───────────┘   └──────────┬───────────┘
           │                           │                          │
┌──────────▼───────────┐    ┌──────────▼───────────┐
│ PostSuggestion       │    │ GenerateSuggestions  │
│ POST /suggestions    │    │ GET /suggestions/    │
│                      │    │   generate           │
└──────────┬───────────┘    └──────────┬───────────┘
           │                           │
   ┌───────┴───────────┬───────────────┴──────────────┐
   ▼                   ▼                              ▼
┌─────────────┐  ┌──────────────┐               ┌─────────────┐
│  S3 Bucket  │  │   DynamoDB   │               │   Bedrock   │
│  raw/       │  │ FinancialTx  │               │ Claude Haiku│
│  processed/ │  │ UserGoals    │               └─────────────┘
└─────────────┘  │ Suggestions  │
                 └──────────────┘
```

---

## AWS Services

| Service | Purpose |
|---|---|
| **AWS Amplify** | Host React frontend, CI/CD from GitHub |
| **Amazon S3** | Store raw CSV uploads + enriched CSV for QuickSight |
| **AWS Lambda** | One function per API endpoint (see Lambda Map below) |
| **Amazon API Gateway** | REST API — routes each URL to its own Lambda |
| **Amazon DynamoDB** | `FinancialTransactions` + `UserGoals` + `Suggestions` tables |
| **Amazon Bedrock** | Claude 3 Haiku — goal subcategorization + spending suggestions |
| **Amazon QuickSight** | Embedded spending graphs (reads from S3 via SPICE) |
| **AWS IAM** | Shared Lambda execution role |

---

## Lambda Map

Each Lambda is deployed as an independent function wired to one API Gateway route.

| Lambda | Method | Path | Purpose |
|---|---|---|---|
| `UploadFunction` | POST | `/upload` | Receive CSV → upload to S3 `raw/` → parse → write rows to `FinancialTransactions` |
| `UploadGoalFunction` | POST | `/goals` | Create a new goal (title, target, saved, deadline, type) in `UserGoals` |
| `CategorizeGoalFunction` | POST | `/goals/categorize` | Call Bedrock → add `specs` subcategory to a goal |
| `GetGoalsFunction` | GET | `/goals` | List all goals for the user |
| `GetUserDataFunction` | GET | `/user-data` | Aggregate spending patterns from `FinancialTransactions` for graphing |
| `GetSuggestionsFunction` | GET | `/suggestions` | Read existing suggestions + compute total savings from accepted ones |
| `PostSuggestionFunction` | POST | `/suggestions` | Accept/reject a suggestion. Accepted → store. Rejected → delete all non-taken |
| `GenerateSuggestionsFunction` | GET | `/suggestions/generate` | Call Bedrock with DynamoDB data → produce fresh suggestions → store in `Suggestions` |

See [lambda.md](lambda.md) for extra Lambdas we should add (update/delete goal, status, QuickSight embed, CSV processor).

---

## Data Models

### DynamoDB — `FinancialTransactions`

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

### DynamoDB — `UserGoals`

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
| `specs` | String | Bedrock subcategory (set by `CategorizeGoalFunction`) |

### DynamoDB — `Suggestions` (new)

| Field | Type | Notes |
|---|---|---|
| `userId` | String (PK) | `"demo-user"` |
| `suggestionId` | String (SK) | UUID |
| `text` | String | The suggestion string from Bedrock |
| `category` | String | Which spending category it targets |
| `estimatedSavings` | Number | Estimated $ saved if accepted |
| `status` | String | `pending` / `accepted` / `rejected` |
| `createdAt` | String | ISO timestamp |

---

## Bedrock Prompt Design

### 1. Goal Categorization (called by `CategorizeGoalFunction`)

```
You are a financial goal categorizer.
Given a user's savings goal, return a concise subcategory string (max 5 words).

Goal: {goal_json}

Return ONLY the subcategory string. No explanation.
```

### 2. Suggestion Generation (called by `GenerateSuggestionsFunction` on login)

```
You are a personal finance advisor.
Spending pattern summary for the past 30 days: {spending_patterns}
Monthly income: ${income}. Fixed costs (rent + utilities): ${fixed_costs}.
Active goals: {goals_summary}

Give 3-5 specific, actionable recommendations.
Return JSON: { "recommendations": [{ "text": "...", "category": "...", "estimatedSavings": 0 }] }
```

---

## API Routes (API Gateway → Lambda)

| Method | Path | Lambda | Description |
|---|---|---|---|
| POST | `/upload` | `UploadFunction` | CSV upload → S3 + DynamoDB |
| POST | `/goals` | `UploadGoalFunction` | Create goal |
| POST | `/goals/categorize` | `CategorizeGoalFunction` | Add Bedrock-generated specs |
| GET | `/goals` | `GetGoalsFunction` | List goals |
| GET | `/user-data` | `GetUserDataFunction` | Aggregated spending data |
| GET | `/suggestions` | `GetSuggestionsFunction` | List suggestions + totals |
| POST | `/suggestions` | `PostSuggestionFunction` | Accept/reject suggestion |
| GET | `/suggestions/generate` | `GenerateSuggestionsFunction` | Fresh Bedrock suggestions |

See [lambda.md](lambda.md) for additional routes under consideration.

---

## QuickSight Integration

**Data flow:** `UploadFunction` writes enriched rows to `s3://puran-data/processed/{userId}/{batch}.csv` so QuickSight can ingest them.

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
  → Lambda calls quicksight.generate_embed_url_for_registered_user()
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

- [ ] S3 bucket + `UploadFunction` parses CSV and writes to DynamoDB
- [ ] `UploadGoalFunction`, `GetGoalsFunction` working against `UserGoals`
- [ ] `GetUserDataFunction` returns aggregated spending for graphs
- [ ] API Gateway wired to all 8 Lambdas
- [ ] Amplify hosting for React app
- [ ] Upload screen: drag-drop CSV, show "Processing…" status
- [ ] Goals dashboard: create goal (title, amount, deadline, type), progress bars
- [ ] Short-term vs very-short-term goals split view
- [ ] Forest: static sprite display (trees count = achieved goals, dead trees = failed)
- [ ] QuickSight dashboard manually set up, embedded in React via iframe

### Level 2 — Full Feature

- [ ] `GenerateSuggestionsFunction` running on login → `Suggestions` table populated
- [ ] `GetSuggestionsFunction` + `PostSuggestionFunction` wired to React panel
- [ ] `CategorizeGoalFunction` auto-tagging goals with Bedrock specs
- [ ] Monthly budget input stored per user (income, rent, utilities)
- [ ] Goal status auto-update: EventBridge daily rule checks deadline vs progress
- [ ] Forest animation: CSS/canvas transition when goal achieved (grow) or failed (burn)
- [ ] QuickSight SPICE refresh triggered after each upload
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
| **1. Infra** | Deploy CloudFormation, verify API Gateway → Lambda → DynamoDB writes | Day 1 AM |
| **2. Core Lambdas** | `UploadFunction`, `UploadGoalFunction`, `GetGoalsFunction`, `GetUserDataFunction` | Day 1 AM–PM |
| **3. Bedrock Lambdas** | `GenerateSuggestionsFunction`, `CategorizeGoalFunction` | Day 1 PM |
| **4. Suggestions Flow** | `GetSuggestionsFunction`, `PostSuggestionFunction` + `Suggestions` table | Day 1 PM |
| **5. QuickSight** | Create datasource, dataset, dashboard, embed URL | Day 1 PM |
| **6. Frontend** | Upload flow, goals dashboard, forest, QuickSight iframe, suggestions panel | Day 1 PM – Day 2 AM |
| **7. Polish** | Animations, end-to-end test with UCI dataset | Day 2 AM |

---

## Team Responsibilities

| Person | Owns |
|---|---|
| Anish | API Gateway, Lambda wiring, CloudFormation deploy, glue code |
| Ethan | React frontend + Amplify hosting |
| Robert | DynamoDB schema + table-handler Lambdas (`FinancialTransactions-handler`, `UserGoals-handler`) |
| Vineel | Bedrock integration — prompts + response parsing |

---

## Budget Estimate (Demo Scale)

| Service | Est. Cost |
|---|---|
| Lambda (2K invocations across 8+ functions) | < $0.02 |
| DynamoDB (10K R/W units) | < $0.01 |
| S3 (500MB) | < $0.02 |
| Bedrock Haiku (~500 calls) | ~$0.08 |
| API Gateway (2K requests) | < $0.02 |
| QuickSight (1 author session) | $0 (free trial) or ~$9/mo |
| **Total** | **< $0.20 + QuickSight** |

---

## Open Questions

| # | Question | Status |
|---|---|---|
| 1 | CSV upload — does `UploadFunction` receive the file directly, or issue a pre-signed URL? | Going with direct upload for simplicity — switch to pre-signed if file size > 5MB |
| 2 | QuickSight tier — standard or Enterprise for anonymous embedding? | TBD — use named user for demo |
| 3 | Forest simulation: canvas or CSS sprites? | TBD — frontend decision |
| 4 | CSV column names from UCI dataset — confirm headers match ingest parser | Check `uci_student_finance.csv` |
| 5 | Auth — do we need Cognito for the demo, or hardcode `userId`? | Hardcoded for now |
