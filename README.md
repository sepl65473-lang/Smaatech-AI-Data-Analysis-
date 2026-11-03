<div align="center">

# AI-Data-Analysis

### AI-Powered Personal Finance Assistant for Indian Professionals

Upload your bank statement. Understand where your money is going — in seconds.

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![Groq](https://img.shields.io/badge/Groq-LLaMA_3.3_70B-orange?logo=groq&logoColor=white)](https://console.groq.com)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)](https://docker.com)


</div>

---

## Table of Contents

- [What is AI-Data-Analysis?](#what-is-ai-data-analysis)
- [Problem Statement](#problem-statement)
- [Live Demo](#live-demo)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [AI / LLM Integration](#ai--llm-integration)
- [Data Pipeline](#data-pipeline)
- [Security & Privacy](#security--privacy)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Local Development](#local-development)
  - [Docker (Single Container)](#docker-single-container)
- [Environment Variables](#environment-variables)
- [API Reference](#api-reference)
- [Project Structure](#project-structure)
- [Supported Banks & Formats](#supported-banks--formats)
- [Roadmap](#roadmap)
- [Contributing](#contributing)

---

## What is AI-Data-Analysis?

AI-Data-Analysis is a **full-stack, AI-powered personal finance assistant** that transforms raw bank statement files into actionable spending insights. It is built for working professionals in India who make hundreds of transactions every month across UPI, cards, EMIs, subscriptions, and investments — but have no easy way to understand the full picture.

You upload a PDF, CSV, or XLSX bank statement. AI-Data-Analysis parses it, cleans the messy transaction descriptions, categorizes every entry, detects recurring payments, computes financial metrics, and generates **personalized AI insights** using the LLaMA 3.3 70B model via Groq — all within a single page-load.

---

## Problem Statement

Indian bank statements are hard to read.

Transaction descriptions look like this:

```
UPI/324981273849/NEFT-HDFC-SWI123@okaxis/PAYMENT/REF9827341
```

No human can manually parse hundreds of these per month to figure out:
- How much did I spend on food delivery?
- Which subscriptions am I still paying for?
- Am I saving enough?
- What was my biggest expense this month?

AI-Data-Analysis solves this by automating the entire analysis pipeline — from raw bytes to a polished dashboard — in a few seconds.

---

## Live Demo


[**AI-Data-Analysis**](https://rupeeradar-p1c4.onrender.com/)

---

## Features

| Feature | Details |
|---|---|
| **Multi-format ingestion** | PDF, CSV, XLSX from any Indian bank |
| **Smart cleaning** | Strips UPI ref IDs, NEFT prefixes, extracts & preserves reference/UTR numbers |
| **13-category classification** | Food, Travel, Shopping, Bills, EMI, Subscriptions, Salary, Rent, Investments, Healthcare, Education, Income, Other |
| **Two-pass categorization** | Rule-based regex (fast) + Groq LLM fallback (accurate) |
| **Recurring detection** | Auto-detects subscriptions, EMIs, SIPs, rent, insurance |
| **Financial metrics** | Income, spend, savings, savings rate, opening/closing balance, reconciliation delta, top counterparties, daily/weekly/monthly trends |
| **AI-generated insights** | 5 personalized, ₹-specific insights via LLaMA 3.3 70B |
| **Five-Action Deliverables Hub** | Interactive Dashboard, PDF Report, Excel Workbook, Standalone HTML, and ZIP Package with in-app previews |
| **Multi-Page PDF Report** | Professional ReportLab multi-page report with vector charts, running headers/footers, "Page X of Y", separate Debit/Credit/Balance columns |
| **Advanced Excel Workbook** | Real 7-sheet .xlsx workbook (Executive Summary, Complete Transactions, Income & Expenses, Categories, Daily & Weekly, Monthly, Reconciliation & Audit) with native formulas and auto-filters |
| **Standalone HTML Dashboard** | 100% portable, offline-capable single-file dashboard with embedded dataset, search, filters, and canvas charts (no backend required) |
| **Graceful degradation** | Works without a Groq API key using rule-based fallback insights |
| **Privacy by design** | All data processed in memory, never written to disk, auto-expires in 60 min |
| **Docker deployment** | Single-container build serves both API and React SPA |

---

## Tech Stack

### Backend
| Technology | Version | Purpose |
|---|---|---|
| Python | 3.11 | Runtime |
| FastAPI | 0.111 | Async REST API framework |
| Uvicorn | 0.29 | ASGI server |
| pdfplumber | 0.11 | PDF table + text extraction |
| pandas | 2.2 | CSV/XLSX parsing, column mapping |
| openpyxl | 3.1 | Excel file backend for pandas |
| Pydantic | 2.7 | Data validation and serialization |
| Groq SDK | 0.28 | LLaMA 3.3 70B API client |
| ReportLab | 4.2 | PDF report generation |
| python-dotenv | 1.0 | Environment variable management |

### Frontend
| Technology | Version | Purpose |
|---|---|---|
| React | 19 | UI framework |
| Vite | 8 | Build tool and dev server |
| React Router | 7 | Client-side routing |
| Recharts | 3 | Category pie chart |
| Axios | 1.18 | HTTP client (60s timeout for LLM calls) |
| Tailwind CSS | 3.4 | Utility-first styling |

### Infrastructure
| Technology | Purpose |
|---|---|
| Docker (multi-stage) | Single-container production build |
| Docker Compose | Local orchestration |
| FastAPI StaticFiles | Serves React SPA from the same process |

---

## Architecture

AI-Data-Analysis follows a **layered pipeline model**. Data enters as a raw file and exits as structured JSON delivered to the React dashboard.

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Browser                            │
│                                                                 │
│   ┌──────────────┐   ┌──────────────┐   ┌───────────────────┐  │
│   │  Upload UI   │──▶│  Dashboard   │   │  Report / Export  │  │
│   └──────────────┘   └──────────────┘   └───────────────────┘  │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP REST (multipart + JSON)
┌───────────────────────────▼─────────────────────────────────────┐
│                        FastAPI Backend                          │
│                                                                 │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐    │
│  │  Ingestion  │─▶│   Pipeline   │─▶│   Groq LLM Layer    │    │
│  │   Module    │  │  (6 stages)  │  │  (categorize+insight)│    │
│  └─────────────┘  └──────────────┘  └─────────────────────┘    │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              In-Memory Session Store (TTL: 60 min)        │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

**Why FastAPI?**
Async I/O handles file parsing and LLM API calls concurrently without blocking. Auto-generated OpenAPI docs (`/docs`) make the API self-documenting.

**Why in-memory sessions?**
Financial data is sensitive PII. Storing it in memory with a 60-minute TTL means it never touches disk and is automatically purged. There is no database to breach.

**Why a single Docker container?**
Minimal deployment friction. FastAPI mounts the React build as static files, so one `docker compose up` serves the entire app on port 8000 with no reverse proxy needed.

**Why two-pass categorization?**
Rule-based regex handles ~80% of Indian bank transactions instantly at zero cost. The Groq LLM is invoked only for the remainder, keeping inference latency and API usage low.

---

## AI / LLM Integration

AI-Data-Analysis uses **Groq's LLaMA 3.3 70B Versatile** model for two tasks:

### 1. LLM Categorization Fallback

After the rule-based pass, any debit transaction still tagged `"Other"` is sent to the LLM in batches of 10.

```
Prompt (tight — every token counts):
"Categorize Indian bank transactions.
 Categories: Food,Travel,Shopping,Bills,EMI,Subscriptions,
             Salary,Rent,Investments,Healthcare,Education,Other
 Return ONLY a JSON array: [{"id":"…","category":"…"},…]

 Transactions: [{"id":"x1","desc":"NEFT-RAHUL-RENT MARCH"},…]"
```

**Rate-limit awareness** (free tier: 1,000 tokens/min, 30 req/min):
- Batch size capped at 10 transactions ≈ 240 tokens/call
- 1-second sleep between batches
- Automatic 1-retry with 2-second back-off on HTTP 429
- Graceful fallback to `"Other"` if all retries fail

### 2. Personalized Insight Generation

After metrics are computed, a compact, **PII-free** summary is sent to the LLM:

```json
{
  "period": "01 Aug 2024 – 31 Aug 2024",
  "income": 85000,
  "spend": 62000,
  "savings": 23000,
  "savings_pct": 27.1,
  "top_cats": { "Food": 12400, "Travel": 8200, "Subscriptions": 2300 },
  "recurring": [{"name": "Netflix", "amt": 649, "tag": "SUBSCRIPTION"}],
  "biggest_txn": {"desc": "Hdfc Home Loan Emi", "amt": 18500}
}
```

The LLM returns exactly 5 actionable, ₹-specific insight strings. Up to 3 retries with 10-second back-off on rate limits.

**If no Groq API key is set**, both passes fall back to deterministic rule-based logic — the app is fully usable without AI.

---

## Data Pipeline

```
Raw File (PDF / CSV / Excel)
         │
         ▼
┌─────────────────────┐
│  1. Ingestion        │  pdfplumber (table extract → text heuristic fallback)
│                      │  pandas.read_csv / read_excel with fuzzy column mapping
└──────────┬──────────┘
           │  raw rows: {date_str, description, amount_str, balance_str}
           ▼
┌─────────────────────┐
│  2. Cleaner          │  13 date formats · Indian lakh number format
│                      │  Dr/Cr suffix · UPI ref strip · merchant extraction
└──────────┬──────────┘
           │  List[Transaction]
           ▼
┌─────────────────────┐
│  3. Categorizer      │  Pass 1: regex rules (13 categories, 100+ merchants)
│                      │  Pass 2: Groq LLM for unmatched debits (batched)
└──────────┬──────────┘
           │  categories applied
           ▼
┌─────────────────────┐
│  4. Recurring        │  Normalize merchant → group by (merchant, amount±₹10)
│     Detector         │  Flag if count ≥ 2 AND date span ≥ 25 days
│                      │  Tags: SUBSCRIPTION · EMI · RENT · SIP · INSURANCE
└──────────┬──────────┘
           │  is_recurring + recurrence_tag set
           ▼
┌─────────────────────┐
│  5. Metrics Engine   │  income · spend · savings · savings_rate
│                      │  top_categories · biggest_transactions · date_range
└──────────┬──────────┘
           │  Metrics object
           ▼
┌─────────────────────┐
│  6. Insight          │  PII-free summary → Groq LLM → 5 insight strings
│     Generator        │  Rule-based fallback always available
└──────────┬──────────┘
           │  AnalysisResult JSON
           ▼
      Session Store
   (JSON files + in-memory cache; TTL 60 min)
           │
           ▼
    React Dashboard
```

---

## Security & Privacy

| Concern | Implementation |
|---|---|
| **Session persistence** | Parsed session data, category mappings, and audit history are stored as JSON files with atomic replacement and per-session thread/process locks. Docker Compose mounts the `session-data` named volume at the session data directory. |
| **Session expiry** | Expired sessions are rejected and removed when accessed; inactive expired files may remain until accessed or the volume is cleaned. |
| **Persistence limits** | This is a single-host local file store, not a distributed database. It is not encrypted at rest and does not provide multi-host locking, backup, or MongoDB compatibility. Keep the Docker volume and host storage protected; `docker compose down -v` removes the named volume. |
| **Uploaded file retention** | Original upload bytes are parsed in memory and are not saved as uploaded files; extracted transaction/session data is persisted as described above. |
| **API key protection** | `GROQ_API_KEY` loaded from `.env` (gitignored); never exposed to frontend or logs |
| **PII-free AI prompts** | LLM receives only aggregated amounts and category labels — zero raw descriptions, zero account numbers, zero names |
| **Safe temp filenames** | UUID-based filenames prevent path traversal attacks |
| **File size limit** | Configurable `MAX_UPLOAD_SIZE_MB` (default 10 MB) enforced before parsing |
| **Input validation** | File type checked by extension; empty files rejected before processing |
| **CORS** | Origin whitelist driven entirely by environment variables — no hardcoded localhost in production |
| **Error sanitization** | Raw SDK exception messages are never forwarded to the client |

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 20+
- A free [Groq API key](https://console.groq.com) *(optional — app works without it)*

---

### Local Development

**Step 1 — Clone the repository**

```bash
git clone https://github.com/sepl65473-lang/Smaatech-AI-Data-Analysis-.git
cd Smaatech-AI-Data-Analysis-
```

**Step 2 — Set up the backend**

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

# Install dependencies
pip install -r requirements.txt

# Copy env template and add your Groq key
cp .env.example .env
# Edit .env and set GROQ_API_KEY=your_key_here
```

**Step 3 — Start the backend**

```bash
# From the backend/ directory, with venv active
uvicorn app.main:app --reload --port 8000
```

Backend is live at → **http://localhost:8000**
Interactive API docs → **http://localhost:8000/docs**

**Step 4 — Set up the frontend** *(new terminal)*

```bash
cd frontend
npm install
npm run dev
```

Frontend is live at → **http://localhost:5173**

> The Vite dev server proxies all `/api` calls to `http://localhost:8000`, so start the backend first.

---

### Docker (Single Container)

The Docker build compiles the React frontend and serves it from the same FastAPI process — one container, one port.

```bash
# Build and start
docker compose up --build

# Run in background
docker compose up --build -d

# View logs
docker compose logs -f

# Stop
docker compose down
```

App is live at → **http://localhost:8000**

> Make sure `backend/.env` exists with your `GROQ_API_KEY` before building. The Docker build reads it at runtime via `env_file`.

---

## Environment Variables

Copy `backend/.env.example` to `backend/.env` and fill in your values.

| Variable | Required | Default | Description |
|---|---|---|---|
| `GROQ_API_KEY` | No* | `""` | Groq API key for AI features. App works without it. |
| `GROQ_MODEL` | No | `llama-3.3-70b-versatile` | Groq model to use |
| `SESSION_TTL_MINUTES` | No | `60` | Minutes before session data is auto-purged |
| `MAX_UPLOAD_SIZE_MB` | No | `10` | Max file upload size in MB |
| `FRONTEND_ORIGIN` | No | `http://localhost:5173` | Primary CORS allowed origin |
| `EXTRA_CORS_ORIGINS` | No | `""` | Comma-separated extra CORS origins (staging, preview) |
| `PORT` | No | `8000` | Server port (auto-set by Render/Railway/Fly.io) |

> *Without `GROQ_API_KEY`, categorization uses regex rules only and insights are generated by rule-based logic. All other features work normally.

---

## API Reference

### `POST /api/upload`

Upload a bank statement for analysis.

**Request:** `multipart/form-data` with field `file` (PDF, CSV, or XLSX)

**Response:**
```json
{
  "session_id": "3f7a1c2e-...",
  "status": "complete",
  "transaction_count": 147,
  "parse_warnings": [],
  "ai_enabled": true,
  "insights_source": "llm",
  "message": "Analysis complete. 147 transactions processed."
}
```

---

### `GET /api/results/{session_id}`

Retrieve the full analysis result.

**Response:**
```json
{
  "session_id": "3f7a1c2e-...",
  "metrics": {
    "total_income": 85000.00,
    "total_spend": 62000.00,
    "savings": 23000.00,
    "savings_rate": 27.1,
    "top_categories": [
      { "category": "Food", "amount": 12400.00, "percentage": 20.0 }
    ],
    "biggest_transactions": [ "..." ],
    "transaction_count": 147,
    "date_range": ["2024-08-01", "2024-08-31"]
  },
  "category_summary": { "Food": 12400.00, "Travel": 8200.00 },
  "recurring_summary": [
    { "merchant": "Netflix", "amount": 649.00, "tag": "SUBSCRIPTION", "frequency": "monthly", "occurrences": 2 }
  ],
  "insights": [
    "You spent ₹12,400 on Food this month — your single largest expense category.",
    "Your savings rate of 27.1% is above the recommended 20% benchmark."
  ],
  "transactions": [ "..." ],
  "ai_enabled": true,
  "insights_source": "llm"
}
```

---

### `GET /api/export/{session_id}?format=pdf|csv`

Download a report.

| Format | Content-Type | Filename |
|---|---|---|
| `csv` | `text/csv` | `data_analysis_export.csv` |
| `pdf` | `application/pdf` | `data_analysis_report.pdf` |

---

### `GET /health`

Liveness probe.

```json
{ "status": "ok", "ai_enabled": true, "model": "llama-3.3-70b-versatile" }
```

---

## Project Structure

```
AI-Data-Analysis/
│
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app, CORS, static file serving
│   │   ├── config.py                # Settings loaded from env vars
│   │   ├── models/
│   │   │   ├── transaction.py       # Transaction, RecurringItem, CategoryStat
│   │   │   └── result.py            # Metrics, AnalysisResult
│   │   ├── routers/
│   │   │   ├── upload.py            # POST /api/upload — full pipeline orchestration
│   │   │   ├── results.py           # GET  /api/results/{session_id}
│   │   │   └── export.py            # GET  /api/export/{session_id}
│   │   ├── services/
│   │   │   ├── ingestion.py         # PDF / CSV / XLSX → raw rows
│   │   │   ├── cleaner.py           # raw rows → List[Transaction]
│   │   │   ├── categorizer.py       # Rule-based + Groq LLM categorization
│   │   │   ├── recurring_detector.py# Recurring payment detection
│   │   │   ├── metrics.py           # Financial metrics computation
│   │   │   ├── insight_generator.py # Groq LLM insights + rule-based fallback
│   │   │   └── report_builder.py    # PDF and CSV export generation
│   │   └── session/
│   │       └── store.py             # Atomic JSON session store, locking, recovery, and TTL
│   ├── requirements.txt
│   ├── .env                         # ← gitignored — your real secrets
│   └── .env.example                 # ← committed — template for others
│
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   └── client.js            # Axios wrapper (upload, results, export)
│   │   ├── components/
│   │   │   ├── SummaryCards.jsx     # Income / Spend / Savings / Rate cards
│   │   │   ├── CategoryBreakdown.jsx# Recharts pie chart + ranked bar list
│   │   │   ├── InsightCards.jsx     # AI insight cards with auto-icons
│   │   │   ├── RecurringList.jsx    # Recurring payments table
│   │   │   ├── TransactionTable.jsx # Paginated, filterable, sortable table
│   │   │   └── ExportButton.jsx     # PDF / CSV download buttons
│   │   ├── pages/
│   │   │   ├── Home.jsx             # Upload page with drag-and-drop
│   │   │   └── Results.jsx          # Dashboard page
│   │   ├── App.jsx                  # Router (/ and /results)
│   │   └── main.jsx                 # React entry point
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js               # Dev proxy: /api → localhost:8000
│   └── tailwind.config.js
│
├── DOCS/
│   ├── architecture.md              # Full system design document
│   ├── context.md                   # Problem context and requirements
│   ├── implementation-plan.md       # 5-phase build plan
│   ├── edge-cases.md                # 45+ edge cases with handling strategies
│   └── problemStatement.txt         # Original challenge brief
│
├── Dockerfile                       # Multi-stage: Node builder → Python final
├── docker-compose.yml               # Single-service local/prod orchestration
├── .dockerignore                    # Excludes venv, node_modules, .env
├── .gitignore
└── README.md
```

---

## Supported Banks & Formats

| Bank | CSV | PDF |
|---|---|---|
| SBI (State Bank of India) | ✅ | ✅ |
| HDFC Bank | ✅ | ✅ |
| ICICI Bank | ✅ | ✅ |
| Axis Bank | ✅ | ✅ |
| Kotak Mahindra Bank | ✅ | ✅ |
| Any generic CSV with standard headers | ✅ | — |

> **PDF note:** Text-based PDFs work well. Scanned / image-only PDFs are not supported and will return a clear error message.

The ingestion layer uses **fuzzy column name matching**, so slight header variations across banks (`Narration` vs `Description` vs `Txn Remarks`) are handled automatically.

---



## Contributing

Contributions are welcome. Here's how to get started:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Make your changes and test them locally
4. Ensure the backend starts cleanly: `uvicorn app.main:app --reload`
5. Ensure the frontend builds: `npm run build`
6. Commit with a clear message: `git commit -m "feat: add monthly trend chart"`
7. Push and open a Pull Request

**Areas that benefit most from contributions:**
- More bank PDF format support
- Additional categorization rules for niche merchants
- Improving the recurring detection algorithm for irregular payments
- Frontend accessibility improvements
- Unit tests for the services layer

---


<div align="center">

Built with ❤️ for Indian professionals who want to understand their money.

**[⬆ Back to top](#ai-data-analysis)**

</div>
