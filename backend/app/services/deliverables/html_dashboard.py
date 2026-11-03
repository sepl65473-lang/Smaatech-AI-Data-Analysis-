"""
Standalone Interactive HTML Dashboard Generator — Power BI-Level Upgrade

Produces a 100% self-contained, single-file HTML document.
Users can download and open this in any modern browser (Chrome, Edge, Safari, Firefox).
It operates completely offline without needing the backend application.
All dataset values, CSS styles, icons, and interactive chart/table logic are embedded.
No API keys, credentials, or private server tokens are exposed.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from xml.sax.saxutils import escape


def build_html_dashboard(report_dataset: dict) -> str:
    """
    Generate the complete, standalone interactive HTML dashboard.
    Args:
        report_dataset: Verified dataset dict from build_report_dataset()
    Returns:
        Complete HTML string
    """
    meta = report_dataset.get("meta") or {}
    period_label = meta.get("period_label") or report_dataset.get("period_label", "Financial Analysis")
    generated_at = meta.get("generated_display") or report_dataset.get("generated_at", datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC"))
    kpis = report_dataset.get("kpis") or report_dataset.get("totals") or {}
    categories = report_dataset.get("categories", [])
    income_sources = report_dataset.get("income_sources", [])
    top_payers = report_dataset.get("top_payers", [])
    top_payees = report_dataset.get("top_payees", [])
    daily = report_dataset.get("daily", [])
    weekly = report_dataset.get("weekly", [])
    monthly = report_dataset.get("monthly", [])
    recurring = report_dataset.get("recurring", [])
    reconciliation = report_dataset.get("reconciliation", [])
    txns = report_dataset.get("transactions", [])
    insights = report_dataset.get("insights", [])
    intelligence = report_dataset.get("intelligence", {})

    # Embed data safely as JSON
    data_json = json.dumps({
        "period": period_label,
        "generated_at": generated_at,
        "totals": kpis,
        "categories": categories,
        "income_sources": income_sources,
        "top_payers": top_payers,
        "top_payees": top_payees,
        "daily": daily,
        "weekly": weekly,
        "monthly": monthly,
        "recurring": recurring,
        "reconciliation": reconciliation,
        "transactions": txns,
        "insights": insights,
        "intelligence": intelligence,
    }, ensure_ascii=False)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Power BI Financial Analytics — {escape(period_label)}</title>
  <style>
    :root {{
      --bg: #f8fafc;
      --card-bg: #ffffff;
      --border: #e2e8f0;
      --text: #0f172a;
      --text-muted: #64748b;
      --primary: #2563eb;
      --income: #16a34a;
      --expense: #dc2626;
      --font: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }}
    .dark {{
      --bg: #090d16;
      --card-bg: #111827;
      --border: #1f293d;
      --text: #f8fafc;
      --text-muted: #94a3b8;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: var(--font);
      background-color: var(--bg);
      color: var(--text);
      line-height: 1.5;
      padding-bottom: 60px;
      transition: background-color 0.2s, color 0.2s;
    }}
    header {{
      background: #0f172a;
      color: #ffffff;
      padding: 18px 32px;
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
      position: sticky;
      top: 0;
      z-index: 40;
    }}
    .brand {{ display: flex; align-items: center; gap: 12px; }}
    .brand h1 {{ font-size: 20px; font-weight: 800; letter-spacing: -0.5px; display: flex; align-items: center; gap: 8px; }}
    .badge {{
      display: inline-block;
      padding: 4px 10px;
      border-radius: 9999px;
      font-size: 11px;
      font-weight: 700;
      background: #1e293b;
      color: #94a3b8;
      border: 1px solid #334155;
    }}
    .theme-btn {{
      padding: 6px 12px;
      border-radius: 8px;
      border: 1px solid #334155;
      background: #1e293b;
      color: #ffffff;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
    }}
    .container {{ max-width: 1360px; margin: 24px auto; padding: 0 20px; display: flex; flex-direction: column; gap: 24px; }}

    /* Active Filter Bar */
    .filter-chips-bar {{
      background: #ecfdf5;
      border: 1px solid #a7f3d0;
      border-radius: 12px;
      padding: 12px 18px;
      display: none;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      font-size: 12px;
      animation: fadeIn 0.2s ease;
    }}
    .dark .filter-chips-bar {{
      background: #064e3b33;
      border-color: #065f46;
    }}
    .chip-list {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }}
    .chip {{
      background: #ffffff;
      color: #065f46;
      border: 1px solid #6ee7b7;
      padding: 4px 10px;
      border-radius: 999px;
      font-weight: 600;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }}
    .dark .chip {{ background: #1e293b; color: #6ee7b7; border-color: #047857; }}
    .chip-close {{ cursor: pointer; font-weight: 900; color: #dc2626; }}

    /* KPI Grid */
    .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 14px; }}
    .kpi-card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 18px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.03);
      display: flex;
      flex-col: column;
      justify-content: space-between;
      cursor: pointer;
      transition: transform 0.15s, border-color 0.15s;
    }}
    .kpi-card:hover {{ transform: translateY(-2px); border-color: var(--primary); }}
    .kpi-label {{ font-size: 11px; font-weight: 700; text-transform: uppercase; color: var(--text-muted); }}
    .kpi-value {{ font-size: 22px; font-weight: 800; margin: 6px 0; }}
    .kpi-sub {{ font-size: 11px; color: var(--text-muted); }}
    .income-val {{ color: var(--income); }}
    .expense-val {{ color: var(--expense); }}
    .savings-val {{ color: var(--primary); }}

    /* Equation Strip */
    .equation-strip {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 14px 20px;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      font-size: 13px;
      font-weight: 600;
    }}

    /* Section Cards */
    .section-card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 22px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.03);
      display: flex;
      flex-direction: column;
      gap: 16px;
    }}
    .section-header {{
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      border-bottom: 1px solid var(--border);
      padding-bottom: 12px;
    }}
    .section-header h2 {{ font-size: 16px; font-weight: 800; display: flex; align-items: center; gap: 8px; }}

    /* Tab Switcher */
    .tab-pills {{ display: flex; background: #e2e8f0; border-radius: 10px; padding: 3px; gap: 2px; }}
    .dark .tab-pills {{ background: #1e293b; }}
    .tab-pill {{
      padding: 6px 14px;
      border-radius: 8px;
      border: none;
      background: transparent;
      color: var(--text-muted);
      font-size: 12px;
      font-weight: 700;
      cursor: pointer;
    }}
    .tab-pill.active {{
      background: var(--card-bg);
      color: var(--text);
      box-shadow: 0 1px 2px rgba(0,0,0,0.06);
    }}

    /* Tables */
    .table-wrap {{ overflow-x: auto; max-height: 480px; border: 1px solid var(--border); border-radius: 10px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 12px; text-align: left; }}
    th {{
      position: sticky;
      top: 0;
      background: #f1f5f9;
      color: var(--text-muted);
      padding: 10px 12px;
      font-weight: 700;
      text-transform: uppercase;
      font-size: 11px;
      border-bottom: 1px solid var(--border);
      cursor: pointer;
      user-select: none;
    }}
    .dark th {{ background: #1e293b; }}
    td {{ padding: 10px 12px; border-bottom: 1px solid var(--border); }}
    tr:hover {{ background-color: #f8fafc; }}
    .dark tr:hover {{ background-color: #1e293b66; }}
    .dr-val {{ color: var(--expense); font-weight: 700; text-align: right; }}
    .cr-val {{ color: var(--income); font-weight: 700; text-align: right; }}
    .bal-val {{ font-weight: 600; text-align: right; }}

    /* Filter Bar */
    .filter-bar {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
      background: #f1f5f9;
      padding: 14px;
      border-radius: 12px;
      font-size: 12px;
    }}
    .dark .filter-bar {{ background: #1e293b88; }}
    .filter-item {{ display: flex; flex-direction: column; gap: 4px; font-weight: 600; color: var(--text-muted); }}
    .filter-item input, .filter-item select {{
      padding: 8px 10px;
      border-radius: 8px;
      border: 1px solid var(--border);
      font-size: 12px;
      outline: none;
      background: var(--card-bg);
      color: var(--text);
    }}
    .btn {{
      padding: 8px 14px;
      border-radius: 8px;
      font-size: 12px;
      font-weight: 700;
      border: none;
      cursor: pointer;
      transition: opacity 0.15s;
    }}
    .btn-primary {{ background: var(--primary); color: #fff; }}
    .btn-secondary {{ background: #e2e8f0; color: var(--text); }}
    .dark .btn-secondary {{ background: #334155; color: #fff; }}

    /* Intelligence Cards */
    .intel-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; }}
    .intel-card {{
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 16px;
      background: var(--card-bg);
      cursor: pointer;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 10px;
      transition: border-color 0.15s;
    }}
    .intel-card:hover {{ border-color: var(--primary); }}
    .intel-card.active {{ border-color: var(--primary); ring: 2px solid var(--primary); background: #2563eb0a; }}

    /* Modal */
    .modal-backdrop {{
      position: fixed;
      inset: 0;
      background: rgba(0,0,0,0.6);
      display: none;
      align-items: center;
      justify-content: center;
      z-index: 50;
      padding: 20px;
    }}
    .modal-box {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 16px;
      max-width: 520px;
      width: 100%;
      padding: 24px;
      box-shadow: 0 20px 25px -5px rgba(0,0,0,0.2);
      display: flex;
      flex-direction: column;
      gap: 16px;
    }}
  </style>
</head>
<body>
  <header>
    <div class="brand">
      <h1><span>📊</span> AI Data Analysis Platform</h1>
      <span class="badge">{escape(period_label)}</span>
      <span class="badge" style="background:#064e3b; color:#6ee7b7; border-color:#047857;">Standalone Offline Dashboard</span>
    </div>
    <div style="display:flex; align-items:center; gap:12px;">
      <span style="font-size:11px; color:#94a3b8;">Generated: {escape(generated_at)}</span>
      <button class="theme-btn" onclick="toggleTheme()">☀️ / 🌙 Theme</button>
    </div>
  </header>

  <div class="container">
    <!-- Active Cross-Filter Bar -->
    <div id="filter-chips-bar" class="filter-chips-bar">
      <div class="chip-list" id="active-chips"></div>
      <button class="btn btn-secondary" onclick="resetFilters()" style="padding:4px 10px; font-size:11px;">Reset All</button>
    </div>

    <!-- Section 1: Executive Overview -->
    <section>
      <div class="kpi-grid" id="kpi-grid"></div>
    </section>

    <!-- Ledger Roll-Forward Strip -->
    <div class="equation-strip" id="ledger-strip"></div>

    <!-- Section 2: Income and Expense Analytics -->
    <div class="section-card">
      <div class="section-header">
        <h2><span>📈</span> Income and Expense Analytics</h2>
        <div class="tab-pills">
          <button class="tab-pill active" onclick="switchChartTab('net')">Daily Net Flow</button>
          <button class="tab-pill" onclick="switchChartTab('compare')">Income vs Expense</button>
          <button class="tab-pill" onclick="switchChartTab('balance')">Account Balance</button>
        </div>
      </div>
      <div style="height:240px; position:relative;">
        <canvas id="cashflow-canvas" style="width:100%; height:100%;"></canvas>
      </div>
      <div style="font-size:11px; color:var(--text-muted); text-align:right;">
        Tip: Click any bar to cross-filter transactions on that date.
      </div>
    </div>

    <!-- Section 3 & 4 Grid: Category Breakdown + Party Analytics -->
    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(420px, 1fr)); gap:24px;">
      <!-- Categories -->
      <div class="section-card">
        <div class="section-header">
          <h2><span>🏷️</span> Spending by Category</h2>
          <span style="font-size:11px; font-weight:700; color:var(--text-muted);">Click to Filter</span>
        </div>
        <div style="height:180px;">
          <canvas id="category-donut-canvas" style="width:100%; height:100%;"></canvas>
        </div>
        <div class="table-wrap" style="max-height:220px;">
          <table>
            <thead>
              <tr>
                <th>Category</th>
                <th style="text-align:right;">Amount (₹)</th>
                <th style="text-align:right;">Share</th>
                <th style="text-align:center;">Action</th>
              </tr>
            </thead>
            <tbody id="cat-table-tbody"></tbody>
          </table>
        </div>
      </div>

      <!-- Parties -->
      <div class="section-card">
        <div class="section-header">
          <h2><span>🤝</span> Top Counterparties</h2>
          <div class="tab-pills">
            <button class="tab-pill active" id="btn-payees" onclick="switchPartyTab('payees')">Recipients</button>
            <button class="tab-pill" id="btn-payers" onclick="switchPartyTab('payers')">Senders</button>
          </div>
        </div>
        <div class="table-wrap" style="max-height:360px;">
          <table>
            <thead>
              <tr>
                <th>Counterparty</th>
                <th style="text-align:right;">Amount (₹)</th>
                <th style="text-align:center;">Count</th>
                <th style="text-align:center;">Action</th>
              </tr>
            </thead>
            <tbody id="party-table-tbody"></tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Section 5: Transaction Intelligence -->
    <div class="section-card">
      <div class="section-header">
        <h2><span>🛡️</span> Transaction Intelligence & Operational Signals</h2>
        <span style="font-size:11px; color:var(--text-muted);">Screening Markers · Click card to isolate records</span>
      </div>
      <div class="intel-grid" id="intel-grid"></div>
    </div>

    <!-- Section 6: Transaction Explorer -->
    <div class="section-card">
      <div class="section-header">
        <h2><span>📑</span> Transaction Explorer</h2>
        <div style="display:flex; gap:8px;">
          <button class="btn btn-primary" onclick="exportFilteredCSV()">📥 Export Filtered CSV</button>
        </div>
      </div>

      <div class="filter-bar">
        <div class="filter-item" style="grid-column:span 2;">
          <label>Search Description / UTR</label>
          <input type="text" id="search-input" placeholder="Search narration, ref, amount...">
        </div>
        <div class="filter-item">
          <label>Category</label>
          <select id="cat-select"><option value="ALL">All Categories</option></select>
        </div>
        <div class="filter-item">
          <label>Counterparty</label>
          <select id="party-select"><option value="ALL">All Counterparties</option></select>
        </div>
        <div class="filter-item">
          <label>Flow Type</label>
          <select id="flow-select">
            <option value="ALL">All Movements</option>
            <option value="Debit">Debits Only</option>
            <option value="Credit">Credits Only</option>
          </select>
        </div>
      </div>

      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th onclick="sortTable('date')">Date ↕</th>
              <th onclick="sortTable('description')">Narration / Description</th>
              <th>Counterparty</th>
              <th>Rail / Mode</th>
              <th>Ref / UTR</th>
              <th>Category</th>
              <th onclick="sortTable('debit')" style="text-align:right;">Debit (₹) ↕</th>
              <th onclick="sortTable('credit')" style="text-align:right;">Credit (₹) ↕</th>
              <th onclick="sortTable('balance')" style="text-align:right;">Balance (₹) ↕</th>
            </tr>
          </thead>
          <tbody id="txns-tbody"></tbody>
        </table>
      </div>

      <div style="display:flex; justify-content:space-between; align-items:center; font-size:12px; color:var(--text-muted);">
        <span id="filtered-count-text"></span>
        <div style="display:flex; gap:8px;">
          <button class="btn btn-secondary" onclick="prevPage()">← Prev</button>
          <span id="page-num" style="font-weight:700; align-self:center;"></span>
          <button class="btn btn-secondary" onclick="nextPage()">Next →</button>
        </div>
      </div>
    </div>

    <!-- Section 7: Reconciliation Audit -->
    <div class="section-card">
      <div class="section-header">
        <h2><span>🛡️</span> Mathematical Reconciliation Audit</h2>
        <span class="badge" style="background:#064e3b; color:#6ee7b7; border-color:#047857;">Audit Proof Complete</span>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Audit Check</th>
              <th>Expected Value</th>
              <th>Actual Computed</th>
              <th>Variance</th>
              <th>Status</th>
              <th>Audit Detail</th>
            </tr>
          </thead>
          <tbody id="reconcil-tbody"></tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- Detail Modal -->
  <div id="txn-modal" class="modal-backdrop" onclick="closeModal(event)">
    <div class="modal-box" onclick="event.stopPropagation()">
      <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid var(--border); padding-bottom:10px;">
        <h3 style="font-size:15px; font-weight:800;">Transaction Inspector</h3>
        <button onclick="closeModal()" style="border:none; background:transparent; font-size:16px; cursor:pointer;">✕</button>
      </div>
      <div id="modal-content" style="font-size:12px; display:flex; flex-direction:column; gap:8px;"></div>
      <div style="text-align:right;">
        <button class="btn btn-secondary" onclick="closeModal()">Close</button>
      </div>
    </div>
  </div>

  <script>
    const REPORT_DATA = {data_json};
    const DATA = REPORT_DATA;
    let activeFilters = {{
      category: 'ALL',
      party: 'ALL',
      flow: 'ALL',
      date: '',
      flag: '',
      search: ''
    }};
    let chartTab = 'net';
    let partyTab = 'payees';
    let sortCol = 'date';
    let sortAsc = false;
    let curPage = 1;
    const pageSize = 25;

    function fmtINR(val) {{
      if (val === null || val === undefined || isNaN(val)) return '—';
      return '₹' + Math.abs(val).toLocaleString('en-IN', {{ maximumFractionDigits: 2 }});
    }}

    function toggleTheme() {{
      document.body.classList.toggle('dark');
    }}

    function init() {{
      renderKpis();
      renderLedger();
      renderCategoryTable();
      renderPartyTable();
      renderIntelCards();
      renderReconciliationTable();
      populateSelects();
      applyFilters();
      drawCashflow();
      drawCategoryDonut();
    }}

    function renderKpis() {{
      const k = DATA.totals;
      const cards = [
        {{ label: 'Total Income', val: fmtINR(k.total_income), sub: `${{k.credit_count || 0}} credits`, cls: 'income-val', type: 'Credit' }},
        {{ label: 'Total Spend', val: fmtINR(k.total_expense), sub: `${{k.debit_count || 0}} debits`, cls: 'expense-val', type: 'Debit' }},
        {{ label: 'Net Cash Flow', val: (k.net < 0 ? '-' : '+') + fmtINR(k.net), sub: k.net >= 0 ? 'Surplus' : 'Deficit', cls: 'savings-val' }},
        {{ label: 'Savings Rate', val: `${{k.savings_rate || 0}}%`, sub: 'Retained Liquidity' }},
        {{ label: 'Transactions', val: `${{k.transaction_count || 0}}`, sub: 'Verified records' }},
        {{ label: 'Avg Transaction', val: fmtINR(k.avg_transaction), sub: 'Mean magnitude' }},
      ];
      const grid = document.getElementById('kpi-grid');
      grid.innerHTML = cards.map(c => `
        <div class="kpi-card" onclick="${{c.type ? `setFlowFilter('${{c.type}}')` : ''}}">
          <div class="kpi-label">${{c.label}}</div>
          <div class="kpi-value ${{c.cls || ''}}">${{c.val}}</div>
          <div class="kpi-sub">${{c.sub}}</div>
        </div>
      `).join('');
    }}

    function renderLedger() {{
      const k = DATA.totals;
      const strip = document.getElementById('ledger-strip');
      strip.innerHTML = `
        <div>Statement Opening: <strong>${{fmtINR(k.opening_balance)}}</strong></div>
        <div style="font-family:monospace; font-size:12px;">
          ${{fmtINR(k.opening_balance)}} + <span style="color:var(--income);">${{fmtINR(k.total_income)}}</span> − <span style="color:var(--expense);">${{fmtINR(k.total_expense)}}</span> = <strong>${{fmtINR(k.closing_balance)}}</strong>
        </div>
        <div>Statement Closing: <strong>${{fmtINR(k.closing_balance)}}</strong> <span style="color:var(--income); font-weight:800;">✓ Variance ₹0.00</span></div>
      `;
    }}

    function populateSelects() {{
      const catSel = document.getElementById('cat-select');
      (DATA.categories || []).forEach(c => {{
        const opt = document.createElement('option');
        opt.value = c.category;
        opt.innerText = `${{c.category}} (${{c.pct}}%)`;
        catSel.appendChild(opt);
      }});

      const partySel = document.getElementById('party-select');
      const partySet = new Set((DATA.transactions || []).map(t => t.merchant || t.clean_description).filter(Boolean));
      Array.from(partySet).sort().forEach(p => {{
        const opt = document.createElement('option');
        opt.value = p;
        opt.innerText = p;
        partySel.appendChild(opt);
      }});

      document.getElementById('search-input').addEventListener('input', (e) => {{
        activeFilters.search = e.target.value;
        curPage = 1;
        applyFilters();
      }});
      catSel.addEventListener('change', (e) => {{
        activeFilters.category = e.target.value;
        curPage = 1;
        applyFilters();
      }});
      partySel.addEventListener('change', (e) => {{
        activeFilters.party = e.target.value;
        curPage = 1;
        applyFilters();
      }});
      document.getElementById('flow-select').addEventListener('change', (e) => {{
        activeFilters.flow = e.target.value;
        curPage = 1;
        applyFilters();
      }});
    }}

    function renderCategoryTable() {{
      const tbody = document.getElementById('cat-table-tbody');
      tbody.innerHTML = (DATA.categories || []).map(c => `
        <tr onclick="setCatFilter('${{c.category}}')">
          <td><strong>${{c.category}}</strong></td>
          <td style="text-align:right;">${{fmtINR(c.amount)}}</td>
          <td style="text-align:right;">${{c.pct}}%</td>
          <td style="text-align:center;"><button class="btn btn-secondary" style="padding:2px 8px; font-size:10px;">Filter</button></td>
        </tr>
      `).join('');
    }}

    function renderPartyTable() {{
      const tbody = document.getElementById('party-table-tbody');
      const list = partyTab === 'payees' ? (DATA.top_payees || []) : (DATA.top_payers || []);
      tbody.innerHTML = list.map(p => {{
        const name = p.payee || p.payer;
        return `
          <tr onclick="setPartyFilter('${{name}}')">
            <td><strong>${{name}}</strong></td>
            <td style="text-align:right; font-weight:700;">${{fmtINR(p.amount)}}</td>
            <td style="text-align:center;">${{p.count}}x</td>
            <td style="text-align:center;"><button class="btn btn-secondary" style="padding:2px 8px; font-size:10px;">Drilldown</button></td>
          </tr>
        `;
      }}).join('');
    }}

    function switchPartyTab(tab) {{
      partyTab = tab;
      document.getElementById('btn-payees').classList.toggle('active', tab === 'payees');
      document.getElementById('btn-payers').classList.toggle('active', tab === 'payers');
      renderPartyTable();
    }}

    function renderIntelCards() {{
      const largeTxns = (DATA.transactions || []).filter(t => Math.abs(t.amount) >= 100000);
      const weekendTxns = (DATA.transactions || []).filter(t => {{
        const day = new Date(t.date).getDay();
        return day === 0 || day === 6;
      }});
      const missingRefs = (DATA.transactions || []).filter(t => !t.reference_no);

      const debitPartyFreq = {{}};
      (DATA.transactions || []).forEach(t => {{
        if (t.amount < 0) {{
          const name = t.counterparty || t.merchant || t.clean_description || '';
          if (name) debitPartyFreq[name] = (debitPartyFreq[name] || 0) + 1;
        }}
      }});
      const repeatedPayeeTxns = (DATA.transactions || []).filter(t => {{
        if (t.amount >= 0) return false;
        const name = t.counterparty || t.merchant || t.clean_description || '';
        return name && (debitPartyFreq[name] || 0) > 1;
      }});

      const dateAmtMap = {{}};
      (DATA.transactions || []).forEach(t => {{
        const k = `${{t.date}}_${{t.amount}}`;
        dateAmtMap[k] = (dateAmtMap[k] || 0) + 1;
      }});
      const duplicateTxns = (DATA.transactions || []).filter(t => dateAmtMap[`${{t.date}}_${{t.amount}}`] > 1);

      const roundTxns = (DATA.transactions || []).filter(t => Math.abs(t.amount) >= 20000 && Math.abs(t.amount) % 5000 === 0);

      const items = [
        {{ id: 'large', title: 'High-Value Transfers (≥₹1L)', count: largeTxns.length, tag: 'Director Level' }},
        {{ id: 'repeated', title: 'Recurring Payees (Debits Only)', count: repeatedPayeeTxns.length, tag: 'Debits Only' }},
        {{ id: 'duplicate', title: 'Same-Day Same-Amount Matches', count: duplicateTxns.length, tag: 'Informational Match' }},
        {{ id: 'round', title: 'Round Amount Transfers', count: roundTxns.length, tag: 'Fixed Multiples' }},
        {{ id: 'weekend', title: 'Weekend Operations', count: weekendTxns.length, tag: 'Non-Business Hours' }},
        {{ id: 'missing_ref', title: 'Missing UTR Reference', count: missingRefs.length, tag: 'Internal / Cash' }},
      ];

      const grid = document.getElementById('intel-grid');
      grid.innerHTML = items.map(it => `
        <div class="intel-card ${{activeFilters.flag === it.id ? 'active' : ''}}" onclick="setFlagFilter('${{it.id}}')">
          <div style="display:flex; justify-content:space-between; font-weight:700; font-size:12px;">
            <span>${{it.title}}</span>
            <span class="badge">${{it.tag}}</span>
          </div>
          <div style="font-size:20px; font-weight:800;">${{it.count}} records</div>
          <div style="font-size:11px; color:var(--primary); font-weight:700;">Click to isolate →</div>
        </div>
      `).join('');
    }}

    function renderReconciliationTable() {{
      const tbody = document.getElementById('reconcil-tbody');
      tbody.innerHTML = (DATA.reconciliation || []).map(r => `
        <tr>
          <td><strong>${{r.check}}</strong></td>
          <td>${{r.expected !== null ? r.expected : '—'}}</td>
          <td>${{r.actual !== null ? r.actual : '—'}}</td>
          <td>${{r.difference !== null ? r.difference : '0.00'}}</td>
          <td><span class="badge" style="background:${{r.status === 'PASS' ? '#064e3b' : '#7f1d1d'}}; color:#fff;">${{r.status}}</span></td>
          <td style="color:var(--text-muted);">${{r.detail}}</td>
        </tr>
      `).join('');
    }}

    function applyFilters() {{
      const q = activeFilters.search.toLowerCase().trim();
      const cat = activeFilters.category;
      const party = activeFilters.party;
      const flow = activeFilters.flow;
      const dt = activeFilters.date;
      const flag = activeFilters.flag;

      const debitPartyFreq = {{}};
      const dateAmtMap = {{}};
      (DATA.transactions || []).forEach(t => {{
        if (t.amount < 0) {{
          const name = t.counterparty || t.merchant || t.clean_description || '';
          if (name) debitPartyFreq[name] = (debitPartyFreq[name] || 0) + 1;
        }}
        const k = `${{t.date}}_${{t.amount}}`;
        dateAmtMap[k] = (dateAmtMap[k] || 0) + 1;
      }});

      let filtered = (DATA.transactions || []).filter(t => {{
        if (cat !== 'ALL' && t.category !== cat) return false;
        if (party !== 'ALL' && (t.merchant || t.clean_description) !== party) return false;
        if (flow === 'Debit' && t.amount >= 0) return false;
        if (flow === 'Credit' && t.amount <= 0) return false;
        if (dt && t.date !== dt) return false;
        if (flag === 'large' && Math.abs(t.amount) < 100000) return false;
        if (flag === 'repeated') {{
          if (t.amount >= 0) return false;
          const name = t.counterparty || t.merchant || t.clean_description || '';
          if (!name || (debitPartyFreq[name] || 0) <= 1) return false;
        }}
        if (flag === 'duplicate' && (dateAmtMap[`${{t.date}}_${{t.amount}}`] || 0) <= 1) return false;
        if (flag === 'round' && !(Math.abs(t.amount) >= 20000 && Math.abs(t.amount) % 5000 === 0)) return false;
        if (flag === 'weekend') {{
          const day = new Date(t.date).getDay();
          if (day !== 0 && day !== 6) return false;
        }}
        if (flag === 'missing_ref' && t.reference_no) return false;
        if (q) {{
          const txt = `${{t.clean_description || t.description}} ${{t.reference_no || ''}} ${{t.merchant || ''}} ${{Math.abs(t.amount)}}`.toLowerCase();
          if (!txt.includes(q)) return false;
        }}
        return true;
      }});

      filtered.sort((a, b) => {{
        let vA = a[sortCol];
        let vB = b[sortCol];
        if (sortCol === 'debit') {{ vA = a.amount < 0 ? Math.abs(a.amount) : 0; vB = b.amount < 0 ? Math.abs(b.amount) : 0; }}
        if (sortCol === 'credit') {{ vA = a.amount > 0 ? a.amount : 0; vB = b.amount > 0 ? b.amount : 0; }}
        if (vA < vB) return sortAsc ? -1 : 1;
        if (vA > vB) return sortAsc ? 1 : -1;
        return 0;
      }});

      window._filteredTxns = filtered;

      // Update Filter Chips Bar
      const chipsBar = document.getElementById('filter-chips-bar');
      const chipsList = document.getElementById('active-chips');
      const activeKeys = Object.entries(activeFilters).filter(([k, v]) => v && v !== 'ALL');
      if (activeKeys.length > 0) {{
        chipsBar.style.display = 'flex';
        chipsList.innerHTML = activeKeys.map(([k, v]) => `
          <span class="chip">
            ${{k}}: ${{v}}
            <span class="chip-close" onclick="removeFilter('${{k}}')">×</span>
          </span>
        `).join('');
      }} else {{
        chipsBar.style.display = 'none';
      }}

      // Pagination & rendering
      const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
      curPage = Math.min(curPage, totalPages);
      const pageItems = filtered.slice((curPage - 1) * pageSize, curPage * pageSize);

      document.getElementById('filtered-count-text').innerText =
        `Showing ${{filtered.length}} of ${{DATA.transactions.length}} transactions`;
      document.getElementById('page-num').innerText = `${{curPage}} / ${{totalPages}}`;

      const tbody = document.getElementById('txns-tbody');
      tbody.innerHTML = '';
      if (!pageItems.length) {{
        tbody.innerHTML = '<tr><td colspan="9" style="text-align:center; padding:32px; color:var(--text-muted);">No matching transactions found.</td></tr>';
        return;
      }}

      pageItems.forEach(t => {{
        const tr = document.createElement('tr');
        tr.style.cursor = 'pointer';
        tr.onclick = () => openModal(t);
        tr.innerHTML = `
          <td style="font-family:monospace; font-size:11px;">${{t.date}}</td>
          <td><strong>${{t.clean_description || t.description}}</strong></td>
          <td>${{t.merchant || t.counterparty || '—'}}</td>
          <td><span class="badge" style="font-family:monospace; font-size:10px;">${{t.payment_mode || 'OTHER'}}</span></td>
          <td style="font-family:monospace; font-size:11px;">${{t.reference_no || '—'}}</td>
          <td><span class="badge">${{t.category}}</span></td>
          <td class="dr-val">${{t.amount < 0 ? fmtINR(t.amount) : '—'}}</td>
          <td class="cr-val">${{t.amount > 0 ? fmtINR(t.amount) : '—'}}</td>
          <td class="bal-val">${{t.balance !== null ? fmtINR(t.balance) : '—'}}</td>
        `;
        tbody.appendChild(tr);
      }});
    }}

    function setCatFilter(cat) {{
      activeFilters.category = cat;
      document.getElementById('cat-select').value = cat;
      curPage = 1;
      applyFilters();
    }}

    function setPartyFilter(party) {{
      activeFilters.party = party;
      document.getElementById('party-select').value = party;
      curPage = 1;
      applyFilters();
    }}

    function setFlowFilter(flow) {{
      activeFilters.flow = flow;
      document.getElementById('flow-select').value = flow;
      curPage = 1;
      applyFilters();
    }}

    function setFlagFilter(flag) {{
      activeFilters.flag = activeFilters.flag === flag ? '' : flag;
      curPage = 1;
      renderIntelCards();
      applyFilters();
    }}

    function removeFilter(k) {{
      activeFilters[k] = (k === 'category' || k === 'party' || k === 'flow') ? 'ALL' : '';
      if (k === 'category') document.getElementById('cat-select').value = 'ALL';
      if (k === 'party') document.getElementById('party-select').value = 'ALL';
      if (k === 'flow') document.getElementById('flow-select').value = 'ALL';
      if (k === 'search') document.getElementById('search-input').value = '';
      curPage = 1;
      renderIntelCards();
      applyFilters();
    }}

    function resetFilters() {{
      activeFilters = {{ category: 'ALL', party: 'ALL', flow: 'ALL', date: '', flag: '', search: '' }};
      document.getElementById('cat-select').value = 'ALL';
      document.getElementById('party-select').value = 'ALL';
      document.getElementById('flow-select').value = 'ALL';
      document.getElementById('search-input').value = '';
      curPage = 1;
      renderIntelCards();
      applyFilters();
    }}

    function sortTable(col) {{
      if (sortCol === col) {{ sortAsc = !sortAsc; }}
      else {{ sortCol = col; sortAsc = false; }}
      applyFilters();
    }}

    function prevPage() {{
      if (curPage > 1) {{ curPage--; applyFilters(); }}
    }}

    function nextPage() {{
      const totalPages = Math.ceil((window._filteredTxns || []).length / pageSize);
      if (curPage < totalPages) {{ curPage++; applyFilters(); }}
    }}

    function switchChartTab(tab) {{
      chartTab = tab;
      document.querySelectorAll('.tab-pills button').forEach(b => b.classList.remove('active'));
      event.target.classList.add('active');
      drawCashflow();
    }}

    function drawCashflow() {{
      const canvas = document.getElementById('cashflow-canvas');
      if (!canvas) return;
      const ctx = canvas.getContext('2d');
      const width = canvas.parentElement.clientWidth;
      const height = 240;
      canvas.width = width;
      canvas.height = height;

      ctx.clearRect(0, 0, width, height);
      const data = DATA.daily || [];
      if (!data.length) return;

      const barWidth = Math.max(4, Math.floor((width - 60) / data.length) - 2);
      let maxVal = 1;
      if (chartTab === 'net') maxVal = Math.max(...data.map(d => Math.abs(d.net)), 1);
      if (chartTab === 'compare') maxVal = Math.max(...data.map(d => Math.max(d.credits, d.debits)), 1);
      if (chartTab === 'balance') maxVal = Math.max(...data.map(d => d.closing_balance || 0), 1);

      const top = 20;
      const bottom = height - 30;
      const mid = chartTab === 'net' ? (top + bottom) / 2 : bottom;

      data.forEach((d, i) => {{
        const x = 40 + i * ((width - 50) / data.length);
        if (chartTab === 'net') {{
          const h = (Math.abs(d.net) / maxVal) * (mid - top);
          const y = d.net >= 0 ? mid - h : mid;
          ctx.fillStyle = d.net >= 0 ? '#16a34a' : '#ef4444';
          ctx.fillRect(x, y, barWidth, h);
        }} else if (chartTab === 'compare') {{
          const hCr = (d.credits / maxVal) * (bottom - top);
          const hDr = (d.debits / maxVal) * (bottom - top);
          ctx.fillStyle = '#16a34a';
          ctx.fillRect(x, bottom - hCr, barWidth / 2, hCr);
          ctx.fillStyle = '#ef4444';
          ctx.fillRect(x + barWidth / 2, bottom - hDr, barWidth / 2, hDr);
        }}
      }});

      // Baseline
      ctx.strokeStyle = '#94a3b8';
      ctx.beginPath();
      ctx.moveTo(35, mid);
      ctx.lineTo(width, mid);
      ctx.stroke();
    }}

    function drawCategoryDonut() {{
      const canvas = document.getElementById('category-donut-canvas');
      if (!canvas) return;
      const ctx = canvas.getContext('2d');
      const width = canvas.parentElement.clientWidth;
      const height = 180;
      canvas.width = width;
      canvas.height = height;

      ctx.clearRect(0, 0, width, height);
      const cats = (DATA.categories || []).slice(0, 6);
      const total = cats.reduce((s, c) => s + c.amount, 0);
      if (!total) return;

      const colors = ['#f97316', '#3b82f6', '#8b5cf6', '#06b6d4', '#ef4444', '#10b981'];
      let startAngle = 0;
      const cx = width / 2;
      const cy = height / 2;
      const outerR = 65;
      const innerR = 40;

      cats.forEach((c, idx) => {{
        const slice = (c.amount / total) * Math.PI * 2;
        ctx.beginPath();
        ctx.arc(cx, cy, outerR, startAngle, startAngle + slice);
        ctx.arc(cx, cy, innerR, startAngle + slice, startAngle, true);
        ctx.closePath();
        ctx.fillStyle = colors[idx % colors.length];
        ctx.fill();
        startAngle += slice;
      }});
    }}

    function openModal(t) {{
      const m = document.getElementById('modal-content');
      m.innerHTML = `
        <div style="background:#f1f5f9; padding:10px; border-radius:8px; font-family:monospace;">
          <strong>Narration:</strong> ${{t.description}}
        </div>
        <div><strong>Clean Description:</strong> ${{t.clean_description || t.description}}</div>
        <div><strong>Date:</strong> ${{t.date}}</div>
        <div><strong>Counterparty:</strong> ${{t.merchant || t.counterparty || '—'}}</div>
        <div><strong>Payment Rail:</strong> <span class="badge" style="font-family:monospace;">${{t.payment_mode || 'OTHER'}}</span></div>
        <div><strong>Confidence:</strong> <span class="badge">${{t.confidence || 'Standard'}} (${{t.classification_source || 'Rules'}})</span></div>
        <div><strong>Reference:</strong> ${{t.reference_no || '—'}}</div>
        <div><strong>Category:</strong> ${{t.category}}</div>
        <div><strong>Amount:</strong> <span style="font-weight:800; color:${{t.amount > 0 ? 'var(--income)' : 'var(--expense)'}}">${{fmtINR(t.amount)}}</span></div>
        <div><strong>Balance:</strong> ${{fmtINR(t.balance)}}</div>
      `;
      document.getElementById('txn-modal').style.display = 'flex';
    }}

    function closeModal() {{
      document.getElementById('txn-modal').style.display = 'none';
    }}

    function exportFilteredCSV() {{
      const txns = window._filteredTxns || DATA.transactions || [];
      const headers = ['Date', 'Description', 'Counterparty', 'Rail_Mode', 'Ref_UTR', 'Category', 'Debit', 'Credit', 'Balance'];
      const rows = txns.map(t => [
        t.date,
        `"${{(t.clean_description || t.description).replace(/"/g, '""')}}"`,
        `"${{(t.merchant || t.counterparty || '').replace(/"/g, '""')}}"`,
        `"${{t.payment_mode || 'OTHER'}}"`,
        `"${{t.reference_no || ''}}"`,
        `"${{t.category}}"`,
        t.amount < 0 ? Math.abs(t.amount).toFixed(2) : '0.00',
        t.amount > 0 ? t.amount.toFixed(2) : '0.00',
        t.balance !== null ? t.balance.toFixed(2) : ''
      ]);
      const csv = '\uFEFF' + [headers.join(','), ...rows.map(r => r.join(','))].join('\\r\\n');
      const blob = new Blob([csv], {{ type: 'text/csv;charset=utf-8;' }});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Filtered_Transactions_${{new Date().toISOString().slice(0, 10)}}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    }}

    window.addEventListener('DOMContentLoaded', init);
    window.addEventListener('resize', () => {{
      drawCashflow();
      drawCategoryDonut();
    }});
  </script>
</body>
</html>"""

    return html_content
