# AI-Data-Analysis — Phase-wise Implementation Plan

## Overview

The implementation is split into 5 phases. Each phase produces a runnable, testable increment — no phase leaves the project in a broken state. Phases build strictly on top of each other.

```
Phase 1 → Project scaffold + environment setup
Phase 2 → Backend pipeline (ingestion → metrics)
Phase 3 → AI layer (categorization + insights)
Phase 4 → Frontend dashboard
Phase 5 → Export, polish, and deployment
```

Estimated total effort for a solo developer: **8–12 days**

---

## Phase 1 — Project Scaffold & Environment Setup
**Goal:** Get the skeleton running end-to-end with no real logic yet. Both servers start, CORS works, and a health-check API call succeeds from the browser.

**Duration:** 0.5–1 day

### Tasks

#### 1.1 Create directory structure
```
AI-Data-Analysis/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── routers/
│   │   ├── services/
│   │   ├── models/
│   │   └── session/
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   └── (Vite scaffold)
└── DOCS/
```

#### 1.2 Backend setup
- Initialize Python virtual environment (`python -m venv venv`)
- Create `requirements.txt` with pinned versions:
  ```
  fastapi==0.111.0
  uvicorn==0.29.0
  python-multipart==0.0.9
  pdfplumber==0.11.0
  pandas==2.2.2
  openpyxl==3.1.2
  pydantic==2.7.1
  python-dotenv==1.0.1
  google-generativeai==0.5.4
  reportlab==4.2.0
  ```
- Write `app/main.py` with FastAPI app instance, CORS middleware (allow `localhost:5173`), and a `GET /health` route
- Write `app/config.py` to load `.env` variables (`GEMINI_API_KEY`, `SESSION_TTL_MINUTES`)
- Write `session/store.py` — a simple dict-backed in-memory store with TTL expiry

#### 1.3 Frontend setup
- Scaffold with Vite: `npm create vite@latest frontend -- --template react-ts`
- Install dependencies:
  ```
  npm install axios react-router-dom recharts
  npm install -D tailwindcss postcss autoprefixer
  npx tailwindcss init -p
  ```
- Configure Tailwind in `index.css` and `tailwind.config.ts`
- Add Vite proxy in `vite.config.ts` to forward `/api/*` to `http://localhost:8000`
- Create placeholder `Home.tsx` and `Results.tsx` pages with React Router

#### 1.4 Verify
- `uvicorn app.main:app --reload` starts with no errors
- `npm run dev` starts with no errors
- `GET http://localhost:8000/health` returns `{ "status": "ok" }` from the browser

**Exit criteria:** Both servers start cleanly. Proxy works. No import errors.

---

## Phase 2 — Backend Data Pipeline
**Goal:** Build all 7 pipeline stages (ingestion → report builder stub) so that uploading a real CSV or PDF returns a fully structured `AnalysisResult` JSON with accurate metrics. No AI calls yet — categorization uses rules only.

**Duration:** 3–4 days

### Tasks

#### 2.1 Data models (`app/models/`)

Create `transaction.py`:
```python
# Transaction, RecurringItem, CategoryStat Pydantic models
# as defined in architecture.md
```

Create `result.py`:
```python
# Metrics, AnalysisResult Pydantic models
```

#### 2.2 Ingestion service (`services/ingestion.py`)
- Detect file type from extension + MIME type (`pdf`, `csv`, `xlsx`)
- **PDF path:** Use `pdfplumber` to extract text page by page, then apply regex patterns to detect table rows (date, description, debit, credit, balance columns)
- **CSV path:** Use `pandas.read_csv()` with flexible column name mapping (handle common bank CSV headers: `Narration`, `Description`, `Txn Remarks`, `Debit`, `Credit`, `Withdrawal`, `Deposit`)
- **XLSX path:** Use `pandas.read_excel()` with same column mapping
- Output: `List[dict]` of raw rows — always `{date_str, description, amount_str, balance_str}`
- Delete the uploaded file immediately after extraction

Supported banks to target first:
| Bank | Format |
|------|--------|
| SBI | CSV / PDF |
| HDFC | CSV / PDF |
| ICICI | CSV |
| Axis | CSV |
| Any generic | CSV with standard headers |

#### 2.3 Cleaner service (`services/cleaner.py`)
- Parse `date_str` → `datetime.date` (try multiple formats: `DD/MM/YYYY`, `DD-MM-YYYY`, `YYYY-MM-DD`, `DD MMM YYYY`)
- Parse `amount_str` → `float` (strip `₹`, commas, handle Dr/Cr suffix)
- Determine sign: credit transactions → positive, debit → negative
- Strip noise from description: remove UPI ref numbers, NEFT/IMPS prefixes, trailing IDs
- Extract merchant name: first meaningful token after prefix removal
- Assign UUID to each transaction
- Output: `List[Transaction]` (category and recurrence fields left as defaults)

#### 2.4 Categorizer service (`services/categorizer.py`)
- Build a rule map of regex patterns → category:
  ```python
  RULES = {
    "Food":          r"swiggy|zomato|uber.?eats|blinkit|dunzo|bigbasket|grofer|fresh",
    "Travel":        r"irctc|makemytrip|goibibo|ola|uber|rapido|redbus|cleartrip|yatra",
    "Shopping":      r"amazon|flipkart|myntra|ajio|nykaa|meesho|snapdeal",
    "Bills":         r"electricity|bescom|tata.?power|airtel|jio|bsnl|broadband|water.?bill",
    "Subscriptions": r"netflix|hotstar|spotify|prime|youtube|zee5|sonyliv|apple",
    "EMI":           r"\bemi\b|loan.?repay|equated.?monthly",
    "Salary":        r"salary|sal credit|neft.?credit.*salary",
    "Rent":          r"\brent\b|house.?rent|pg.?rent",
    "Investments":   r"zerodha|groww|kuvera|coin|sip|mutual.?fund|nps|ppf|fd.?open",
    "Other":         r".*",  # catch-all, always last
  }
  ```
- Apply rules in order; first match wins
- Track which transactions were unmatched (category = "Other") for LLM fallback in Phase 3
- Return updated `List[Transaction]`

#### 2.5 Recurring detector (`services/recurring_detector.py`)
- Normalize merchant: lowercase, strip non-alphanumeric except spaces, strip common suffixes (`@okaxis`, `@ybl`, `@paytm`, `upi`, `neft`, `imps`)
- Group transactions by `(normalized_merchant, round(abs(amount) / 10) * 10)` (amount bucketed to nearest ₹10)
- Flag as recurring if group size ≥ 2 and date range spans ≥ 25 days
- Assign `recurrence_tag`:
  - Matches `emi|loan` → `EMI`
  - Matches `sip|mutual fund|nps|ppf` → `SIP`
  - Matches `rent` → `RENT`
  - Matches `insurance|lic|policy` → `INSURANCE`
  - Default → `SUBSCRIPTION`
- Build `RecurringItem` list for the result

#### 2.6 Metrics engine (`services/metrics.py`)
- `total_income`: sum of all positive amounts
- `total_spend`: sum of absolute values of all negative amounts
- `savings`: `total_income - total_spend`
- `savings_rate`: `(savings / total_income) * 100` if income > 0 else 0
- `top_categories`: group debits by category, sort descending, compute percentage of total spend
- `biggest_transactions`: top 5 by `abs(amount)`
- `transaction_count`: len of transaction list
- `date_range`: (min date, max date)

#### 2.7 Placeholder insight generator (`services/insight_generator.py`)
- For Phase 2, generate rule-based insights (no LLM yet):
  ```
  "Your top spending category is {top_category} at ₹{amount}."
  "You made {count} transactions between {start} and {end}."
  "Your biggest single transaction was ₹{amount} at {merchant}."
  ```
- This placeholder will be replaced in Phase 3

#### 2.8 Upload and results routers
- `routers/upload.py`:
  - `POST /api/upload` — accept `UploadFile`, run full pipeline, store `AnalysisResult` in session store, return `session_id`
  - Pipeline call order: `ingestion → cleaner → categorizer → recurring_detector → metrics → insight_generator`
- `routers/results.py`:
  - `GET /api/results/{session_id}` — retrieve from session store, return JSON

#### 2.9 Verify
- Upload a real SBI/HDFC CSV and get back a valid `AnalysisResult` JSON
- Metrics are numerically correct (manually verify against the statement)
- Recurring transactions are correctly flagged (e.g., Netflix, salary)
- Session store returns the same result on second call

**Exit criteria:** Full pipeline runs on real data. `/api/results` returns correct structured JSON. No AI dependency yet.

---

## Phase 3 — AI Layer (Categorization + Insights)
**Goal:** Replace the placeholder categorizer fallback and insight generator with real LLM calls. The pipeline now produces human-quality category assignments and personalized insight strings.

**Duration:** 1.5–2 days

### Tasks

#### 3.1 Gemini API integration (`config.py`)
- Load `GEMINI_API_KEY` from `.env`
- Initialize `google.generativeai` client once at startup
- Model: `gemini-1.5-flash` (fast and cheap for structured output tasks)

#### 3.2 LLM categorizer fallback (`services/categorizer.py`)
- After rule-based pass, collect all transactions still tagged `Other`
- Batch them into groups of 50 (to stay within token limits)
- Build prompt:
  ```
  You are a financial transaction categorizer for Indian bank statements.
  Categorize each transaction into exactly one of:
  Food, Travel, Shopping, Bills, EMI, Subscriptions, Salary, Rent, Investments, Other

  Return ONLY a JSON array: [{"id": "<id>", "category": "<category>"}, ...]

  Transactions:
  [{"id": "x1", "description": "NEFT CR-HDFC-JOHN DOE-SALARY"}, ...]
  ```
- Parse JSON response, update transaction categories
- On API error: leave category as `Other` (graceful degradation)

#### 3.3 LLM insight generator (`services/insight_generator.py`)
- Build a compact summary payload (no raw descriptions, no account numbers — only amounts and categories):
  ```python
  summary = {
      "total_income": metrics.total_income,
      "total_spend": metrics.total_spend,
      "savings_rate": metrics.savings_rate,
      "category_breakdown": category_summary,     # {category: amount}
      "top_recurring": [r.merchant for r in recurring[:5]],
      "biggest_transaction": {"merchant": ..., "amount": ...},
      "date_range": str(metrics.date_range),
  }
  ```
- Prompt:
  ```
  You are a personal finance advisor analyzing an Indian professional's bank statement.
  Based on the summary below, generate exactly 5 short, specific, friendly insights.
  - Use actual ₹ amounts (not percentages alone)
  - Be specific, not generic
  - Each insight should be 1–2 sentences max
  - Return ONLY a JSON array of strings

  Summary:
  {summary_json}
  ```
- Parse response, store as `List[str]` in `AnalysisResult.insights`
- Fallback: if API fails, use rule-based insights from Phase 2

#### 3.4 Verify
- Upload a statement with ambiguous descriptions (e.g., "NEFT-RAHUL-RENT MARCH")
- Confirm LLM correctly categorizes it as `Rent`
- Confirm insights contain actual rupee amounts and are specific to the uploaded data
- Confirm graceful fallback when `GEMINI_API_KEY` is unset

**Exit criteria:** Categorization accuracy visibly improves for edge cases. Insights are specific and data-driven, not generic.

---

## Phase 4 — Frontend Dashboard
**Goal:** Build the full React UI — upload flow, dashboard with charts, transaction table, recurring payments list, and insight cards. The app is fully usable end-to-end in the browser.

**Duration:** 2–3 days

### Tasks

#### 4.1 API client (`src/api/client.ts`)
- Axios instance with `baseURL: /api`
- `uploadStatement(file: File): Promise<{ session_id: string }>`
- `getResults(sessionId: string): Promise<AnalysisResult>`
- `getExportUrl(sessionId: string, format: 'pdf' | 'csv'): string`

#### 4.2 Home page (`src/pages/Home.tsx`)
- Full-page centered layout with AI-Data-Analysis branding
- `UploadZone` component:
  - Drag-and-drop area using HTML5 drag events
  - Click-to-browse fallback
  - Accepts `.pdf`, `.csv`, `.xlsx`
  - Shows file name and size after selection
  - "Analyze" button triggers upload
  - Loading spinner during processing
  - Error message on failure

#### 4.3 Results page (`src/pages/Results.tsx`)
- Receives `session_id` from navigation state
- Calls `getResults` on mount
- Shows loading skeleton while fetching
- Renders all dashboard components once data arrives

#### 4.4 Summary cards (`src/components/SummaryCards.tsx`)
Four stat cards in a row:
- Total Income (green)
- Total Spend (red)
- Savings (blue)
- Savings Rate (percentage badge)

#### 4.5 Category breakdown (`src/components/CategoryBreakdown.tsx`)
- Recharts `PieChart` + `Legend` showing spend by category
- Color-coded segments (one color per category, consistent across the app)
- Below the chart: a ranked list of categories with bar indicators and ₹ amounts

#### 4.6 Insight cards (`src/components/InsightCards.tsx`)
- Grid of 3–5 cards, one per LLM insight string
- Light background, icon per insight type (💡 default)
- Insight text in readable font size

#### 4.7 Recurring payments list (`src/components/RecurringList.tsx`)
- Table with columns: Merchant, Amount, Tag (badge), Frequency
- Tags color-coded: EMI (orange), SUBSCRIPTION (purple), RENT (blue), SIP (green)
- Sort by amount descending by default

#### 4.8 Transaction table (`src/components/TransactionTable.tsx`)
- Paginated table (20 rows/page): Date, Description, Category, Amount
- Amount colored: green for credit, red for debit
- Filter by category (dropdown)
- Search by description (text input)
- Sort by date or amount

#### 4.9 Export button (`src/components/ExportButton.tsx`)
- Two buttons: "Download PDF" and "Download CSV"
- Triggers `GET /api/export/{session_id}?format=pdf|csv`
- Uses `<a href download>` pattern to trigger browser download

#### 4.10 Routing
```tsx
// main.tsx
<BrowserRouter>
  <Routes>
    <Route path="/" element={<Home />} />
    <Route path="/results" element={<Results />} />
  </Routes>
</BrowserRouter>
```

#### 4.11 Verify
- Upload a real statement CSV from the browser
- All dashboard sections populate with correct data
- Category pie chart renders and is readable
- Transaction table filters and pagination work
- Insights display the LLM-generated strings

**Exit criteria:** Full browser flow works end-to-end. No console errors. All sections render real data.

---

## Phase 5 — Export, Polish & Deployment
**Goal:** Add PDF/CSV export, harden edge cases, and produce a single-container deployable build.

**Duration:** 1.5–2 days

### Tasks

#### 5.1 CSV export (`routers/export.py`)
- `GET /api/export/{session_id}?format=csv`
- Build a pandas DataFrame from `AnalysisResult.transactions`
- Columns: `Date, Description, Clean Description, Category, Amount, Recurring, Tag`
- Return as `StreamingResponse` with `Content-Disposition: attachment; filename=data_analysis_export.csv`

#### 5.2 PDF report (`services/report_builder.py`)
- Use ReportLab to build a multi-page PDF:
  - **Page 1:** Title, date range, summary metrics (income / spend / savings)
  - **Page 2:** Category breakdown table + bar chart (drawn with ReportLab graphics)
  - **Page 3:** Recurring payments table
  - **Page 4:** Top 5 insights
  - **Page 5:** Full transaction list (paginated)
- Return as `StreamingResponse` with `Content-Disposition: attachment; filename=data_analysis_report.pdf`

#### 5.3 Edge case hardening
- Empty file → return 400 with clear message
- File with no parseable transactions → return 422 with message
- Unsupported file type → return 415
- Session not found → return 404
- LLM API timeout → use rule-based fallback, flag `insights_source: "fallback"` in response
- Statement with only credits (no debits) → handle zero spend gracefully
- Single-transaction file → works without crashing

#### 5.4 Frontend polish
- Add a `"New Analysis"` button on the Results page to go back to Home
- Add a simple loading progress indicator with step labels:
  ```
  Parsing file... → Cleaning transactions... → Categorizing... → Generating insights...
  ```
- Responsive layout: dashboard readable on 1280px+ screens
- Add a privacy notice below the upload zone:
  > "Your data is processed in memory only and is never stored on our servers."

#### 5.5 Docker build
- Write `Dockerfile`:
  ```dockerfile
  FROM python:3.11-slim
  WORKDIR /app
  COPY backend/requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt
  COPY backend/app ./app
  COPY frontend/dist ./static
  ENV PYTHONPATH=/app
  CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
  ```
- Write `docker-compose.yml`:
  ```yaml
  services:
    ai-data-analysis:
      build: .
      ports:
        - "8000:8000"
      env_file:
        - backend/.env
  ```
- Add `app/main.py` static file mounting:
  ```python
  app.mount("/", StaticFiles(directory="static", html=True), name="static")
  ```
- Build frontend: `npm run build` → `frontend/dist/`
- Verify: `docker compose up` → open `http://localhost:8000` → full app works

#### 5.6 Final verification checklist
- [ ] Upload SBI PDF → correct transactions extracted
- [ ] Upload HDFC CSV → correct transactions extracted
- [ ] Upload generic CSV → correct transactions extracted
- [ ] Categories match expected values for known transactions
- [ ] Recurring: Netflix, salary, EMI all detected
- [ ] Insights contain ₹ amounts specific to the uploaded data
- [ ] PDF download opens cleanly with all sections
- [ ] CSV download has correct columns and data
- [ ] Docker container starts and serves the full app on port 8000
- [ ] No raw transaction data logged to console or server logs

**Exit criteria:** Single `docker compose up` command starts the full app. All checklist items pass.

---

## Phase Summary

| Phase | What Gets Built | Duration | End State |
|-------|----------------|----------|-----------|
| 1 | Scaffold, env, health check | 0.5–1 day | Both servers start; CORS works |
| 2 | Full backend pipeline, rule-based only | 3–4 days | Upload → structured JSON with accurate metrics |
| 3 | LLM categorization + insights | 1.5–2 days | AI-quality categories and personalized insights |
| 4 | React dashboard | 2–3 days | Full browser flow works end-to-end |
| 5 | Export, polish, Docker | 1.5–2 days | Single-container deployable prototype |
| **Total** | | **8–12 days** | |

---

## Dependencies Between Phases

```
Phase 1 (scaffold)
    │
    ▼
Phase 2 (backend pipeline) ◄── no AI dependency; testable with curl
    │
    ▼
Phase 3 (AI layer) ◄── drops in on top of Phase 2 services
    │
    ▼
Phase 4 (frontend) ◄── consumes Phase 2+3 API; can be mocked before Phase 3
    │
    ▼
Phase 5 (export + deployment) ◄── wraps everything
```

Phase 4 frontend can begin in parallel with Phase 3 if the API response shape from Phase 2 is used as a mock fixture. This can save 1–2 days of calendar time.

---

## Risk Register

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Bank PDF format varies wildly | High | Target CSV first; PDF is a stretch goal for the prototype |
| LLM API rate limits or cost overrun | Medium | Batch LLM calls; rule-based fallback always available |
| pdfplumber fails on scanned PDFs | Medium | Detect image-only PDFs and return a clear error; out of scope for prototype |
| Vite proxy issues in production | Low | Build frontend and serve as static files from FastAPI |
| Session memory leak under load | Low | TTL + explicit cleanup; not a concern for prototype / single user |
