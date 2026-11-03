# RupeeRadar — Architecture

## Overview

RupeeRadar is a web-based, AI-powered personal finance assistant. The architecture follows a layered pipeline model: raw bank statement data enters at one end, and structured insights exit at the other. The system is designed to run fully locally or be deployed as a lightweight web app, with no mandatory cloud dependency for the prototype.

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Browser                             │
│                                                                 │
│   ┌──────────────┐   ┌──────────────┐   ┌───────────────────┐  │
│   │  Upload UI   │──▶│  Dashboard   │   │  Report / Export  │  │
│   └──────────────┘   └──────────────┘   └───────────────────┘  │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP (REST / multipart)
┌───────────────────────────▼─────────────────────────────────────┐
│                        Backend Server                           │
│                                                                 │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐    │
│  │  Ingestion  │─▶│  Processing  │─▶│   Insight Engine    │    │
│  │   Module    │  │   Pipeline   │  │   (AI / LLM layer)  │    │
│  └─────────────┘  └──────────────┘  └─────────────────────┘    │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                  In-Memory Session Store                  │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Frontend | React + Vite | Fast dev experience, component-based dashboard |
| Styling | Tailwind CSS | Utility-first, no design system overhead |
| Charts | Recharts | Lightweight, React-native charting |
| Backend | Python + FastAPI | Async, easy PDF/CSV parsing, rich AI library ecosystem |
| AI / NLP | Google Gemini API (or OpenAI) | LLM for categorization and insight generation |
| Parsing | pdfplumber, pandas | PDF and CSV bank statement parsing |
| Session store | In-memory (dict) / Redis (optional) | Ephemeral; data is not persisted to disk by default |
| Export | ReportLab / WeasyPrint | PDF report generation |
| Deployment | Uvicorn + static serve, or Docker | Single-container local-first deployment |

---

## System Layers

### 1. Frontend (React)

Responsible for all user interaction. Communicates with the backend via REST API calls.

```
src/
├── components/
│   ├── UploadZone.tsx          # Drag-and-drop file upload
│   ├── Dashboard.tsx           # Main insights view
│   ├── CategoryBreakdown.tsx   # Pie / bar chart for categories
│   ├── RecurringList.tsx       # Detected recurring payments table
│   ├── TransactionTable.tsx    # Cleaned transactions with filters
│   ├── InsightCards.tsx        # 3+ AI-generated insight cards
│   └── ExportButton.tsx        # Trigger PDF/CSV download
├── pages/
│   ├── Home.tsx                # Upload landing page
│   └── Results.tsx             # Dashboard after processing
├── api/
│   └── client.ts               # Axios wrapper for backend calls
└── main.tsx
```

**Key flows:**
- User drops a PDF/CSV → `UploadZone` sends multipart POST to `/api/upload`
- Backend responds with a `session_id`
- Results page polls/calls `/api/results/{session_id}` and renders the dashboard

---

### 2. Backend (FastAPI)

Handles file ingestion, orchestrates the processing pipeline, calls the AI layer, and returns structured JSON to the frontend.

```
app/
├── main.py                     # FastAPI app, route registration
├── routers/
│   ├── upload.py               # POST /api/upload
│   └── results.py              # GET /api/results/{session_id}
│   └── export.py               # GET /api/export/{session_id}
├── services/
│   ├── ingestion.py            # File type detection, raw text extraction
│   ├── cleaner.py              # Transaction normalization
│   ├── categorizer.py          # Rule-based + AI categorization
│   ├── recurring_detector.py   # Recurring payment identification
│   ├── metrics.py              # Financial metrics computation
│   ├── insight_generator.py    # LLM-powered insight generation
│   └── report_builder.py       # PDF report assembly
├── models/
│   ├── transaction.py          # Transaction dataclass / Pydantic model
│   └── result.py               # Full result schema
├── session/
│   └── store.py                # In-memory session management
└── config.py                   # Env vars, API keys
```

---

## Data Pipeline (End-to-End)

```
Raw File (PDF / CSV / Excel)
        │
        ▼
┌───────────────────┐
│  1. Ingestion     │  Extract raw text / rows from the file
│     Module        │  Supports: PDF (pdfplumber), CSV (pandas), XLSX (openpyxl)
└────────┬──────────┘
         │  Raw rows: [date_str, description, amount_str, balance_str]
         ▼
┌───────────────────┐
│  2. Cleaner       │  Normalize dates, parse amounts, strip noise from descriptions
│                   │  Output: List[Transaction]
└────────┬──────────┘
         │  Structured transactions
         ▼
┌───────────────────┐
│  3. Categorizer   │  Rule-based pass first (regex keyword matching)
│                   │  LLM pass for unmatched / ambiguous transactions
│                   │  Categories: Food, Travel, Shopping, Bills, EMI,
│                   │  Subscriptions, Salary, Rent, Investments, Other
└────────┬──────────┘
         │  Categorized transactions
         ▼
┌───────────────────┐
│  4. Recurring     │  Group by normalized merchant name + amount
│     Detector      │  Flag if same merchant+amount appears ≥2 times/month
│                   │  Tags: SUBSCRIPTION, EMI, RENT, SIP, INSURANCE
└────────┬──────────┘
         │  Transactions with recurrence flags
         ▼
┌───────────────────┐
│  5. Metrics       │  Total income, total spend, savings rate
│     Engine        │  Top categories by spend, biggest transactions
│                   │  Monthly trend if multi-month data present
└────────┬──────────┘
         │  Metrics object
         ▼
┌───────────────────┐
│  6. Insight       │  Sends metrics + category summary to LLM
│     Generator     │  Receives 3–5 human-readable insight strings
│                   │  Example: "You spent ₹6,400 on food delivery — 22% of total spend"
└────────┬──────────┘
         │  Final result object
         ▼
┌───────────────────┐
│  7. Report        │  Assembles PDF with charts + insights (optional download)
│     Builder       │
└───────────────────┘
```

---

## Data Models

### Transaction
```python
class Transaction(BaseModel):
    id: str                         # UUID
    date: date
    description: str                # Raw description
    clean_description: str          # Normalized description
    amount: float                   # Positive = credit, Negative = debit
    balance: float | None
    category: str                   # Assigned category
    is_recurring: bool
    recurrence_tag: str | None      # SUBSCRIPTION | EMI | RENT | SIP | INSURANCE
    merchant: str | None            # Extracted merchant name
```

### AnalysisResult
```python
class AnalysisResult(BaseModel):
    session_id: str
    transactions: List[Transaction]
    metrics: Metrics
    insights: List[str]             # 3–5 LLM-generated insight strings
    category_summary: Dict[str, float]   # category → total spend
    recurring_summary: List[RecurringItem]
    generated_at: datetime
```

### Metrics
```python
class Metrics(BaseModel):
    total_income: float
    total_spend: float
    savings: float
    savings_rate: float             # percentage
    top_categories: List[CategoryStat]
    biggest_transactions: List[Transaction]  # top 5 by amount
    transaction_count: int
    date_range: tuple[date, date]
```

---

## API Contracts

### POST `/api/upload`
Accepts a bank statement file.

**Request:** `multipart/form-data` with field `file`

**Response:**
```json
{
  "session_id": "abc-123",
  "status": "processing",
  "message": "File received. Processing started."
}
```

---

### GET `/api/results/{session_id}`
Returns the full analysis for a session.

**Response:**
```json
{
  "session_id": "abc-123",
  "metrics": {
    "total_income": 85000.00,
    "total_spend": 62000.00,
    "savings": 23000.00,
    "savings_rate": 27.1,
    "top_categories": [
      { "category": "Food", "amount": 12400.00, "percentage": 20.0 }
    ],
    "biggest_transactions": [ ... ]
  },
  "category_summary": {
    "Food": 12400.00,
    "Travel": 8200.00,
    "Subscriptions": 2300.00
  },
  "recurring_summary": [
    { "merchant": "Netflix", "amount": 649.00, "tag": "SUBSCRIPTION", "frequency": "monthly" }
  ],
  "insights": [
    "You spent ₹12,400 on Food this month — your single largest expense category.",
    "Netflix, Hotstar, and Spotify together cost you ₹1,847/month in subscriptions.",
    "Your savings rate of 27.1% is above the recommended 20% benchmark."
  ],
  "transactions": [ ... ]
}
```

---

### GET `/api/export/{session_id}?format=pdf|csv`
Downloads a report.

**Response:** Binary file stream (`application/pdf` or `text/csv`)

---

## Categorization Strategy

A two-pass approach balances speed and accuracy:

**Pass 1 — Rule-based (fast, free)**
Keyword regex matching against the cleaned description. Examples:
```
swiggy|zomato|uber eats → Food
irctc|makemytrip|ola|uber → Travel
netflix|hotstar|spotify|prime → Subscriptions
emi|loan → EMI
neft credit|salary → Salary
```

**Pass 2 — LLM fallback (accurate, used sparingly)**
Transactions that don't match any rule are batched and sent to the LLM with a structured prompt. This keeps API cost low while handling edge cases.

```
Prompt template:
"Categorize the following bank transactions into one of: 
Food, Travel, Shopping, Bills, EMI, Subscriptions, Salary, Rent, Investments, Other.
Return a JSON array of {id, category} only.

Transactions:
[{id: "x1", description: "NEFT-HDFC-RAMESH CHIT FUND 2024"}, ...]"
```

---

## Recurring Payment Detection

Algorithm:
1. Normalize merchant names (strip UPI suffixes, lowercase, remove special chars)
2. Group transactions by `(normalized_merchant, amount_bucket)`
3. Flag group as recurring if:
   - Count ≥ 2 within a 35-day rolling window, OR
   - Same amount appears on approximately the same date across multiple months
4. Classify tag based on merchant name keywords (EMI, SIP, rent) or default to SUBSCRIPTION

---

## Privacy & Security

| Concern | Approach |
|---------|----------|
| Data persistence | Transactions stored in-memory only; session expires after 1 hour |
| File handling | Uploaded files deleted from disk immediately after parsing |
| API keys | Stored in `.env`, never exposed to frontend |
| PII in insights | LLM prompt includes only amounts and categories, not names or account numbers |
| Export | Reports generated on-demand; not cached on server |
| HTTPS | Enforced in any deployed environment |

---

## Session Lifecycle

```
Upload → [session created, TTL = 60 min] → Processing → Results served
                                                              │
                                               User downloads report or
                                               navigates away
                                                              │
                                               Session auto-expires (TTL)
                                               All data purged from memory
```

---

## Deployment

### Local (Development)
```
# Backend
uvicorn app.main:app --reload --port 8000

# Frontend
npm run dev  (Vite dev server on port 5173)
```

### Production (Single Container)
```dockerfile
FROM python:3.11-slim
# Install backend deps
COPY backend/ /app/backend
# Copy built frontend static files
COPY frontend/dist/ /app/static
# FastAPI serves static files from /app/static
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Directory Structure (Full Project)

```
RupeeRadar/
├── DOCS/
│   ├── problemStatement.txt
│   ├── context.md
│   └── architecture.md
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── routers/
│   │   ├── services/
│   │   ├── models/
│   │   ├── session/
│   │   └── config.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── api/
│   ├── package.json
│   └── vite.config.ts
├── docker-compose.yml
└── README.md
```

---

## Key Design Decisions

**Why FastAPI over Django/Flask?**
FastAPI's async support handles file I/O and LLM API calls efficiently without blocking. Auto-generated OpenAPI docs also speed up frontend integration.

**Why in-memory session store?**
Financial data should not be persisted beyond the session. In-memory storage enforces this by default and eliminates any database setup for the prototype.

**Why two-pass categorization?**
Rule-based matching handles 70–80% of Indian bank transactions cheaply and instantly. The LLM is called only for the remainder, keeping inference costs low and latency acceptable.

**Why a single-container deployment?**
Minimizes setup friction for a prototype. FastAPI can serve the React build as static files, so the entire app runs with one command and no reverse proxy needed.
