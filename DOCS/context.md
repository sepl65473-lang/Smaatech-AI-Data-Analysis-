# RupeeRadar — Project Context

## What Is This?

RupeeRadar is an AI-powered personal finance assistant built for working professionals in India. It takes raw bank statement data as input and converts it into actionable spending insights through an end-to-end pipeline: ingestion → cleaning → categorization → analysis → dashboard.

---

## Problem Being Solved

Indian professionals transact across UPI, cards, bank transfers, subscriptions, EMIs, rent, food delivery, travel, and investments. While bank statements contain all this data, the transaction descriptions are messy, inconsistent, and hard to parse — making it nearly impossible for a person to manually understand their spending behavior.

RupeeRadar bridges this gap by automating the full analysis pipeline and presenting the results in a simple, human-readable format.

---

## Core User Questions the App Answers

- What are my biggest spending categories?
- How much did I spend this month?
- Which transactions are recurring subscriptions or EMIs?
- What was my biggest single transaction?
- What are the top insights from my spending behavior?

---

## Functional Requirements

| # | Requirement |
|---|-------------|
| 1 | Accept bank statement data as input (file upload or structured data) |
| 2 | Extract and clean transactions into a structured format |
| 3 | Categorize transactions into: Food, Travel, Shopping, Bills, EMI, Subscriptions, Salary, Rent, Investments, Other |
| 4 | Identify recurring transactions: subscriptions, EMIs, rent, SIPs, insurance |
| 5 | Calculate key metrics: total income, total spend, savings, top categories, biggest transactions |
| 6 | Generate clear, human-readable insights using actual rupee amounts |
| 7 | Present output via a UI dashboard or downloadable report |

---

## Expected Deliverables

- Cleaned and structured transaction data
- Categorized expense breakdown
- Recurring payment detection results
- Spend summary dashboard
- At least 3 personalized financial insights
- A shareable final report or visual summary

---

## Evaluation Criteria

- Accuracy of transaction cleaning and categorization
- Quality and specificity of financial insights (amounts, not just percentages)
- Handling of real-world messy transaction descriptions
- Simplicity and usefulness of the UX
- Completeness of the end-to-end workflow
- Privacy-conscious handling of sensitive financial data

---

## Key Constraints

- Prioritize a working end-to-end prototype over supporting every bank format
- Technology stack is open — no prescribed language or framework
- Final output must be deployed or locally runnable

---

## Data Sensitivity Notes

- Bank statement data is highly sensitive (PII + financial data)
- No raw transaction data should be stored beyond the session unless explicitly opted in
- User data should not be sent to third-party services without consent
- Prefer client-side or local processing where feasible

---

## Scope Boundaries

**In scope:**
- Single user, single bank statement per session
- Indian banks and UPI transaction formats
- Web-based or local UI
- AI-assisted categorization and insight generation

**Out of scope (for prototype):**
- Multi-user accounts and authentication
- Real-time bank API integration
- Support for every bank format from day one
- Mobile app

---

## Glossary

| Term | Meaning |
|------|---------|
| UPI | Unified Payments Interface — India's real-time payment system |
| EMI | Equated Monthly Installment — loan repayment amount |
| SIP | Systematic Investment Plan — recurring mutual fund investment |
| Recurring transaction | A payment that repeats at a regular interval (monthly, weekly) |
| Insight | A human-readable sentence derived from transaction data, e.g., "You spent ₹4,200 on food delivery this month" |
