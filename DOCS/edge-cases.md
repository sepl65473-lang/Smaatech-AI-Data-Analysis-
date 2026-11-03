# RupeeRadar — Edge Cases & Corner Cases

## How to Use This Document

Each edge case is tagged with:
- **Layer** — which part of the pipeline it affects
- **Severity** — `Critical` (breaks the app), `High` (wrong output), `Medium` (degraded UX), `Low` (minor annoyance)
- **Handling** — what the correct behavior should be

---

## 1. File Ingestion

### 1.1 Empty file uploaded
**Layer:** Ingestion  
**Severity:** Critical  
**Input:** A 0-byte PDF, CSV, or XLSX  
**Expected:** Return HTTP 400 — `"Uploaded file is empty."`  
**Risk if unhandled:** pdfplumber or pandas will throw an unhandled exception

---

### 1.2 Unsupported file type
**Layer:** Ingestion  
**Severity:** Critical  
**Input:** `.jpg`, `.txt`, `.docx`, `.json`, etc.  
**Expected:** Return HTTP 415 — `"Unsupported file type. Please upload a PDF, CSV, or XLSX."`  
**Risk if unhandled:** Silent failure or crash during parsing

---

### 1.3 File too large
**Layer:** Ingestion  
**Severity:** High  
**Input:** A file over a defined size limit (e.g., >10 MB)  
**Expected:** Return HTTP 413 with a clear message before parsing begins  
**Notes:** Large PDFs with many pages can exhaust memory. Set a hard limit at the FastAPI middleware level.

---

### 1.4 Password-protected PDF
**Layer:** Ingestion  
**Severity:** High  
**Input:** An encrypted/password-locked bank statement PDF  
**Expected:** Detect the encryption and return HTTP 422 — `"This PDF is password-protected. Please upload an unlocked version."`  
**Notes:** pdfplumber raises `pdfminer.pdfdocument.PDFPasswordIncorrect`. Catch this explicitly.

---

### 1.5 Scanned / image-only PDF
**Layer:** Ingestion  
**Severity:** High  
**Input:** A PDF where pages are scanned images with no selectable text  
**Expected:** Detect zero extracted text after pdfplumber parsing, return HTTP 422 — `"Could not extract text from this PDF. It may be a scanned image. Please upload a text-based PDF or CSV."`  
**Notes:** pdfplumber returns empty strings for image pages. Check `len(text.strip()) == 0` across all pages.

---

### 1.6 CSV with wrong delimiter
**Layer:** Ingestion  
**Severity:** High  
**Input:** A CSV using `;` or `|` as delimiter instead of `,`  
**Expected:** Auto-detect delimiter using `pandas.read_csv(sep=None, engine='python')`  
**Fallback:** If detection fails, return 422 with message asking user to re-export as standard CSV

---

### 1.7 CSV with BOM (Byte Order Mark)
**Layer:** Ingestion  
**Severity:** Medium  
**Input:** A CSV saved with UTF-8 BOM (common in Excel exports on Windows)  
**Expected:** Read with `encoding='utf-8-sig'` to strip the BOM automatically  
**Risk if unhandled:** First column header appears as `\ufeffDate` breaking column detection

---

### 1.8 Multi-sheet XLSX — wrong sheet
**Layer:** Ingestion  
**Severity:** Medium  
**Input:** An XLSX with multiple sheets (e.g., "Summary", "Transactions", "Charts")  
**Expected:** Try to detect the correct sheet by looking for date/amount column headers. Default to first sheet if ambiguous.  
**Fallback:** If no valid sheet found, return 422

---

### 1.9 PDF with multi-column layout
**Layer:** Ingestion  
**Severity:** Medium  
**Input:** A bank PDF where the statement is laid out in two columns side by side  
**Expected:** pdfplumber's `extract_table()` may jumble columns. Log a warning; attempt best-effort parsing.  
**Fallback:** Return partial results with a `parse_warning` flag in the response

---

### 1.10 File upload interrupted mid-stream
**Layer:** Ingestion  
**Severity:** Medium  
**Input:** Network drops during multipart upload  
**Expected:** FastAPI will raise a connection error. Ensure partially written temp files are cleaned up.  
**Notes:** Wrap file write in try/finally to guarantee cleanup

---

## 2. Transaction Cleaning

### 2.1 Unparseable date formats
**Layer:** Cleaner  
**Severity:** High  
**Input:** Dates like `29-Jul-2024`, `Jul 29 '24`, `20240729`  
**Expected:** Try a list of known date format strings. If all fail, skip the row and log it to a `parse_errors` list returned in the response.  
**Risk if unhandled:** `datetime.strptime` raises ValueError, crashing the cleaner

---

### 2.2 Amount with Dr/Cr suffix
**Layer:** Cleaner  
**Severity:** High  
**Input:** `"5,400.00 Dr"` or `"12,000.00 Cr"` (common in SBI statements)  
**Expected:** Strip suffix, parse amount, use `Dr` → negative, `Cr` → positive  
**Risk if unhandled:** Amount parsed as NaN or wrong sign

---

### 2.3 Amount in Indian number format
**Layer:** Cleaner  
**Severity:** High  
**Input:** `"1,25,000.00"` (Indian comma grouping: lakh separator)  
**Expected:** Strip all commas before parsing as float  
**Risk if unhandled:** `float("1,25,000.00")` raises ValueError

---

### 2.4 Negative amount represented as `(5400.00)`
**Layer:** Cleaner  
**Severity:** Medium  
**Input:** Parenthetical notation for debits: `(5,400.00)`  
**Expected:** Strip parentheses and parse as negative float

---

### 2.5 Zero-amount transactions
**Layer:** Cleaner  
**Severity:** Medium  
**Input:** Rows where debit and credit are both 0 (e.g., balance enquiry, standing instruction failed)  
**Expected:** Include in transaction list but exclude from spend/income calculations  
**Notes:** Do not divide by zero in savings rate if both income and spend are 0

---

### 2.6 Missing balance column
**Layer:** Cleaner  
**Severity:** Low  
**Input:** CSV with no balance column  
**Expected:** Set `balance = None` on all transactions. Balance column is optional in the data model.  
**Risk if unhandled:** KeyError crash during column mapping

---

### 2.7 Duplicate transaction rows
**Layer:** Cleaner  
**Severity:** Medium  
**Input:** The same transaction appears twice in the statement (e.g., copy-paste error by user, or bank export bug)  
**Expected:** Deduplicate on `(date, description, amount)` before processing. Log count of duplicates removed.

---

### 2.8 Transactions with only whitespace descriptions
**Layer:** Cleaner  
**Severity:** Low  
**Input:** Description field is empty or just spaces  
**Expected:** Set `clean_description = "Unknown"` and `merchant = "Unknown"`. Assign category `Other`.

---

### 2.9 Very long description strings
**Layer:** Cleaner  
**Severity:** Low  
**Input:** Description of 500+ characters (base64-encoded data sometimes appears in UPI remarks)  
**Expected:** Truncate `clean_description` to 120 characters before storing and sending to LLM

---

## 3. Categorization

### 3.1 Ambiguous merchant matches multiple categories
**Layer:** Categorizer  
**Severity:** High  
**Input:** `"AMAZON PAY WALLET"` — matches both Shopping (amazon) and Bills (wallet top-up / utility payments)  
**Expected:** Rule specificity order matters. More specific rules (e.g., `amazon.*pay` → Bills) should come before generic ones (`amazon` → Shopping).  
**Notes:** Document rule priority in `categorizer.py`

---

### 3.2 UPI ID as description with no merchant name
**Layer:** Categorizer  
**Severity:** High  
**Input:** `"UPI/8987654321@ybl/PAYMENT"` — UPI transfer to a mobile number, merchant unknown  
**Expected:** Rule-based pass fails. Route to LLM. If LLM also can't determine, assign `Other`.

---

### 3.3 Same merchant in multiple categories depending on context
**Layer:** Categorizer  
**Severity:** Medium  
**Input:** `"UBER"` — could be Uber Cab (Travel) or Uber Eats (Food)  
**Expected:** Use longer pattern: `uber.*eats → Food`, `uber(?!.*eats) → Travel`

---

### 3.4 LLM returns malformed JSON
**Layer:** Categorizer (LLM pass)  
**Severity:** High  
**Input:** Gemini response is truncated or contains markdown code fences around the JSON  
**Expected:** Strip markdown fences before parsing. On `json.JSONDecodeError`, fall back to `Other` for the entire batch. Log the raw response.

---

### 3.5 LLM returns unexpected category names
**Layer:** Categorizer (LLM pass)  
**Severity:** Medium  
**Input:** LLM returns `"Groceries"` instead of `"Food"`, or `"Loan"` instead of `"EMI"`  
**Expected:** Maintain a normalization map: `{"Groceries": "Food", "Loan": "EMI", "Entertainment": "Subscriptions", ...}`. Apply after parsing LLM response.

---

### 3.6 LLM API key not set
**Layer:** Categorizer, Insight Generator  
**Severity:** Medium  
**Input:** `GEMINI_API_KEY` is missing from `.env`  
**Expected:** Skip LLM passes entirely. Use rule-based categories and rule-based insights. Flag `ai_enabled: false` in the response metadata.  
**Risk if unhandled:** Crash on API client initialization

---

### 3.7 LLM API rate limit hit
**Layer:** Categorizer, Insight Generator  
**Severity:** Medium  
**Input:** Too many requests in a short window  
**Expected:** Catch `429` / rate limit exception. Wait and retry once with exponential backoff. If retry fails, fall back to rule-based.

---

### 3.8 All transactions fall into "Other"
**Layer:** Categorizer  
**Severity:** Low  
**Input:** A statement from a very new or uncommon bank with non-standard description formats  
**Expected:** App still functions. Dashboard shows "Other" as the top category. Insights acknowledge limited categorization.

---

## 4. Recurring Detection

### 4.1 Single transaction that looks recurring
**Layer:** Recurring Detector  
**Severity:** Medium  
**Input:** Only one month of data — every transaction appears exactly once  
**Expected:** Nothing is flagged as recurring. Recurring list is empty. UI shows "No recurring payments detected."

---

### 4.2 Irregular amount for the same merchant
**Layer:** Recurring Detector  
**Severity:** Medium  
**Input:** Electricity bill from BESCOM — ₹1,200 one month, ₹1,850 next month (variable bill)  
**Expected:** Amount bucketing (±10%) should still catch this as recurring if merchant matches and dates span > 25 days. Tag as `SUBSCRIPTION` or `BILLS`.

---

### 4.3 Merchant name changes slightly across months
**Layer:** Recurring Detector  
**Severity:** Medium  
**Input:** `"NETFLIX INDIA"` one month, `"NETFLIX.COM"` the next  
**Expected:** Normalization strips domain suffixes and stops at the brand name. Both should normalize to `"netflix"` and be grouped together.

---

### 4.4 EMI amount decreases over time (floating-rate loan)
**Layer:** Recurring Detector  
**Severity:** Low  
**Input:** EMI of ₹12,450 one month, ₹12,380 the next due to rate adjustment  
**Expected:** Amount bucket (rounded to nearest ₹100 for EMIs) should still group them. Tag as `EMI`.

---

### 4.5 Two different subscriptions at the same price
**Layer:** Recurring Detector  
**Severity:** Medium  
**Input:** Netflix ₹649 and Hotstar ₹649 — same amount, different merchants  
**Expected:** Grouping is by `(normalized_merchant, amount)` not just amount alone, so these are treated as two separate recurring items.

---

## 5. Metrics Calculation

### 5.1 No income transactions
**Layer:** Metrics  
**Severity:** High  
**Input:** Statement contains only debit transactions (e.g., a credit card statement or a spending-only account)  
**Expected:** `total_income = 0`, `savings = -total_spend`, `savings_rate = 0`. Do not divide by zero.

---

### 5.2 No debit transactions
**Layer:** Metrics  
**Severity:** Medium  
**Input:** Statement is a salary credit-only view  
**Expected:** `total_spend = 0`, `savings = total_income`, `savings_rate = 100`. Category breakdown is empty. Show a message: "No expense transactions found."

---

### 5.3 Single transaction in the entire file
**Layer:** Metrics  
**Severity:** Low  
**Input:** File with exactly one row  
**Expected:** App processes it without crash. `biggest_transactions` returns a list of 1. `top_categories` has one entry.

---

### 5.4 Multi-year statement
**Layer:** Metrics  
**Severity:** Medium  
**Input:** A statement spanning 18 months  
**Expected:** `date_range` reflects the full span. Metrics are computed over all transactions. Monthly trend view (if implemented) breaks down by month correctly.

---

### 5.5 All transactions on the same date
**Layer:** Metrics  
**Severity:** Low  
**Input:** Statement exported for a single day  
**Expected:** `date_range` is `(same_date, same_date)`. Recurring detection finds nothing. App works without crash.

---

### 5.6 Extremely large transaction amounts
**Layer:** Metrics  
**Severity:** Low  
**Input:** A crore-level transaction (₹1,00,00,000+) mixed with everyday ₹500 transactions  
**Expected:** Float precision is sufficient for Indian rupee amounts at this scale. Verify no overflow or display truncation in the UI.

---

## 6. Insight Generation

### 6.1 LLM generates fewer than 3 insights
**Layer:** Insight Generator  
**Severity:** Medium  
**Input:** LLM returns only 1–2 strings in the array  
**Expected:** Pad with rule-based insights to always return at least 3. Never show an empty insights section.

---

### 6.2 LLM insight contains hallucinated merchant names
**Layer:** Insight Generator  
**Severity:** High  
**Input:** LLM invents a merchant not present in the data  
**Expected:** The prompt must instruct the LLM to use only merchants and amounts from the provided summary JSON. Add a post-processing check: if a merchant in an insight string doesn't appear in `recurring_summary` or `top_categories`, replace the insight with a rule-based one.

---

### 6.3 LLM insight leaks account number or personal name
**Layer:** Insight Generator  
**Severity:** Critical  
**Input:** The LLM somehow echoes back PII from its context  
**Expected:** The prompt payload sent to the LLM must contain zero raw descriptions, zero account numbers, and zero personal names — only aggregated amounts and category labels. Enforce this at the prompt-building layer, not post-hoc.

---

### 6.4 Insights repeat the same point
**Layer:** Insight Generator  
**Severity:** Low  
**Input:** LLM generates 5 insights but 3 of them all say "you spent a lot on food"  
**Expected:** Prompt instruction: "Each insight must cover a different aspect of the spending data." Accept duplicates gracefully; do not crash, just display them.

---

## 7. Session Management

### 7.1 Session ID not found
**Layer:** Session Store / Results Router  
**Severity:** High  
**Input:** `GET /api/results/nonexistent-id`  
**Expected:** Return HTTP 404 — `"Session not found or expired."`

---

### 7.2 Session expires mid-analysis
**Layer:** Session Store  
**Severity:** Medium  
**Input:** TTL set to 60 minutes; user leaves the page open for 61 minutes then tries to download  
**Expected:** Return HTTP 404 on results/export call. Frontend shows: "Your session has expired. Please upload your statement again."

---

### 7.3 Concurrent uploads from the same user
**Layer:** Session Store  
**Severity:** Low  
**Input:** User uploads two files quickly in two browser tabs  
**Expected:** Each upload gets a distinct `session_id`. No cross-contamination between sessions. The in-memory store is keyed by UUID, so this is safe by default.

---

### 7.4 Very high number of concurrent sessions
**Layer:** Session Store  
**Severity:** Low (prototype scope)  
**Input:** 100+ simultaneous sessions  
**Expected:** For the prototype, document the memory ceiling. Each session holding ~1000 transactions ≈ ~2 MB. 100 sessions ≈ 200 MB. Acceptable for a demo server; flag as a scaling concern.

---

## 8. Frontend / API

### 8.1 Backend unreachable at upload time
**Layer:** Frontend  
**Severity:** High  
**Input:** User clicks "Analyze" but backend is down  
**Expected:** Show a user-friendly error: "Could not connect to the server. Please try again." Do not show raw network error stack traces.

---

### 8.2 User navigates directly to `/results` with no session
**Layer:** Frontend  
**Severity:** Medium  
**Input:** User types `/results` in the URL bar directly  
**Expected:** Results page checks for a valid `session_id` in navigation state or URL params. If missing, redirect to Home with a message: "Please upload a statement to get started."

---

### 8.3 Results page refreshed (session_id lost from state)
**Layer:** Frontend  
**Severity:** Medium  
**Input:** User refreshes the browser on the Results page  
**Expected:** If `session_id` is passed as a URL query param (e.g., `/results?sid=abc-123`), it survives a refresh. If stored only in React state, it is lost on refresh — redirect to Home.  
**Recommendation:** Pass `session_id` as a URL query param, not only in navigation state.

---

### 8.4 File selected but empty (0 bytes) on the frontend
**Layer:** Frontend  
**Severity:** Medium  
**Input:** User selects an empty file via the file picker  
**Expected:** Validate `file.size > 0` before sending. Show inline error: "Selected file appears to be empty."

---

### 8.5 Very slow LLM response (>30 seconds)
**Layer:** Frontend + Backend  
**Severity:** Medium  
**Input:** Gemini API takes unusually long  
**Expected:** Show a progress indicator with step labels on the frontend. Backend should set a timeout on the LLM HTTP call (e.g., 30s). On timeout, fall back to rule-based insights and return the response rather than hanging.

---

### 8.6 Transaction table with 0 rows after filtering
**Layer:** Frontend  
**Severity:** Low  
**Input:** User filters by a category that has no transactions in the dataset  
**Expected:** Show an empty state: "No transactions found for this category." Do not show a blank table.

---

## 9. Export

### 9.1 Export called before analysis is complete
**Layer:** Export Router  
**Severity:** Medium  
**Input:** `GET /api/export/{session_id}` called immediately after upload before pipeline finishes  
**Expected:** Return HTTP 202 — `"Analysis still in progress. Please try again shortly."` (or implement a status endpoint to prevent premature export calls)

---

### 9.2 PDF generation fails (ReportLab error)
**Layer:** Report Builder  
**Severity:** Medium  
**Input:** Unusual unicode characters in merchant names cause ReportLab font errors  
**Expected:** Sanitize all strings before inserting into the PDF (replace or remove characters outside Latin-1/Windows-1252). Log the error and fall back to CSV export if PDF fails.

---

### 9.3 CSV export with special characters in descriptions
**Layer:** Export Router  
**Severity:** Low  
**Input:** Description contains commas or newlines (e.g., `"Transfer, personal"`)  
**Expected:** pandas `to_csv()` handles quoting automatically. Verify the output is valid CSV by testing with a known problematic description.

---

## 10. Privacy & Security

### 10.1 Temp file not deleted after parse error
**Layer:** Ingestion  
**Severity:** Critical  
**Input:** An exception is raised during PDF parsing after the file has been written to disk  
**Expected:** Use `try/finally` to guarantee `os.remove(temp_path)` runs regardless of whether parsing succeeds or fails.

---

### 10.2 Session data not purged on server restart
**Layer:** Session Store  
**Severity:** Low (in-memory store is wiped on restart by definition)  
**Input:** Server is restarted while sessions are active  
**Expected:** All in-memory data is lost on restart. This is acceptable and by design. Document it clearly.

---

### 10.3 API key exposed in error response
**Layer:** Backend  
**Severity:** Critical  
**Input:** Gemini API raises an exception that includes the API key in the error message (some SDKs do this)  
**Expected:** Catch all AI-layer exceptions at the service level. Return only a generic error message to the client. Never propagate raw exception messages from third-party SDK calls.

---

### 10.4 Malicious file upload (path traversal or zip bomb)
**Layer:** Ingestion  
**Severity:** High  
**Input:** A file named `../../../../etc/passwd` or an XLSX that expands to gigabytes  
**Expected:** Use a random UUID as the temp filename (never the user-provided filename). Enforce file size limit before writing to disk. These two measures mitigate both attacks.

---

## Edge Case Priority Matrix

| # | Edge Case | Severity | Phase to Handle |
|---|-----------|----------|----------------|
| 1.4 | Password-protected PDF | Critical | Phase 2 |
| 10.1 | Temp file not deleted on error | Critical | Phase 2 |
| 10.3 | API key in error response | Critical | Phase 3 |
| 6.3 | LLM leaks PII | Critical | Phase 3 |
| 1.5 | Scanned image PDF | High | Phase 2 |
| 2.2 | Dr/Cr amount suffix | High | Phase 2 |
| 2.3 | Indian number format (lakh) | High | Phase 2 |
| 3.4 | LLM returns malformed JSON | High | Phase 3 |
| 5.1 | No income transactions | High | Phase 2 |
| 6.2 | LLM hallucinates merchants | High | Phase 3 |
| 8.1 | Backend unreachable | High | Phase 4 |
| 10.4 | Malicious file upload | High | Phase 2 |
| 1.1 | Empty file | Critical | Phase 2 |
| 1.2 | Unsupported file type | Critical | Phase 2 |
| 3.6 | API key not set | Medium | Phase 3 |
| 7.1 | Session not found | High | Phase 2 |
| 8.3 | Results page refresh | Medium | Phase 4 |
| 9.1 | Export before analysis done | Medium | Phase 5 |
