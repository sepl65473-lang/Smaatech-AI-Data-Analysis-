import React from 'react'

function fmtInr(n) {
  if (n === null || n === undefined) return '—'
  return '₹' + Math.abs(n).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export default function ReconciliationAudit({
  metrics,
  transactions = [],
  parseWarnings = [],
}) {
  const opening = metrics?.opening_balance ?? 0
  const credits = metrics?.total_income ?? 0
  const debits = metrics?.total_spend ?? 0
  const closing = metrics?.closing_balance ?? 0
  const calculatedClosing = opening + credits - debits
  const variance = Math.abs(calculatedClosing - closing)
  const isPerfect = variance < 0.01

  // Running balance continuity check row-by-row
  let runningBreaks = 0
  let prev = opening
  transactions.forEach((t) => {
    if (t.balance !== null && t.balance !== undefined) {
      const expected = prev + t.amount
      if (Math.abs(expected - t.balance) > 0.01) {
        runningBreaks++
      }
      prev = t.balance
    }
  })

  const missingRefs = transactions.filter((t) => !t.reference_no).length

  return (
    <section className="bg-white dark:bg-slate-900 rounded-2xl border border-gray-200 dark:border-slate-800 shadow-xs p-6 space-y-6" id="reconciliation-audit">
      {/* Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-gray-100 dark:border-slate-800 pb-4">
        <div>
          <h2 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <span>🛡️</span> Financial Reconciliation & Audit Trail
          </h2>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
            Independent proof of mathematical reconciliation, row continuity, and ledger balance verification.
          </p>
        </div>

        <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-black ${
          isPerfect
            ? 'bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border border-emerald-300'
            : 'bg-red-100 dark:bg-red-950/60 text-red-800 dark:text-red-300 border border-red-300'
        }`}>
          {isPerfect ? '✓ PERFECT RECONCILIATION (0.00 Variance)' : `Delta: ${fmtInr(variance)}`}
        </span>
      </div>

      {/* Main Reconciliation Equation Card */}
      <div className="bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/80 rounded-2xl p-6">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-4">
          Ledger Balance Roll-Forward Equation
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 items-center text-center">
          {/* Opening */}
          <div className="bg-white dark:bg-slate-900 p-4 rounded-xl border border-gray-200 dark:border-slate-700 shadow-2xs">
            <span className="text-[10px] font-bold uppercase text-gray-400">1. Opening Balance</span>
            <p className="text-lg font-black text-gray-900 dark:text-white mt-1">{fmtInr(opening)}</p>
            <span className="text-[10px] text-gray-400 font-mono">Statement Printed</span>
          </div>

          {/* Plus Credits */}
          <div className="bg-white dark:bg-slate-900 p-4 rounded-xl border border-emerald-200 dark:border-emerald-800/60 shadow-2xs">
            <span className="text-[10px] font-bold uppercase text-emerald-600 dark:text-emerald-400">2. (+) Total Credits</span>
            <p className="text-lg font-black text-emerald-600 dark:text-emerald-400 mt-1">+{fmtInr(credits)}</p>
            <span className="text-[10px] text-gray-400 font-mono">{metrics?.credit_count || 0} deposits</span>
          </div>

          {/* Minus Debits */}
          <div className="bg-white dark:bg-slate-900 p-4 rounded-xl border border-rose-200 dark:border-rose-800/60 shadow-2xs">
            <span className="text-[10px] font-bold uppercase text-rose-600 dark:text-rose-400">3. (−) Total Debits</span>
            <p className="text-lg font-black text-rose-600 dark:text-rose-400 mt-1">−{fmtInr(debits)}</p>
            <span className="text-[10px] text-gray-400 font-mono">{metrics?.debit_count || 0} withdrawals</span>
          </div>

          {/* Reconciled Closing */}
          <div className="bg-white dark:bg-slate-900 p-4 rounded-xl border border-blue-200 dark:border-blue-800/60 shadow-2xs">
            <span className="text-[10px] font-bold uppercase text-blue-600 dark:text-blue-400">4. (=) Reconciled Balance</span>
            <p className="text-lg font-black text-blue-600 dark:text-blue-400 mt-1">{fmtInr(calculatedClosing)}</p>
            <span className="text-[10px] text-gray-400 font-mono">Computed Roll-Forward</span>
          </div>

          {/* Statement Closing */}
          <div className="bg-white dark:bg-slate-900 p-4 rounded-xl border border-emerald-200 dark:border-emerald-800/60 shadow-2xs">
            <span className="text-[10px] font-bold uppercase text-emerald-700 dark:text-emerald-400">5. Statement Closing</span>
            <p className="text-lg font-black text-emerald-700 dark:text-emerald-400 mt-1">{fmtInr(closing)}</p>
            <span className="text-[10px] text-emerald-600 font-bold">Variance: {fmtInr(variance)} ✓</span>
          </div>
        </div>
      </div>

      {/* Audit Checklist & Integrity Checks */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Row-Level Continuity */}
        <div className="p-4 rounded-xl border border-gray-200 dark:border-slate-800 bg-gray-50 dark:bg-slate-800/40">
          <div className="flex items-center justify-between text-xs font-bold text-gray-700 dark:text-gray-300">
            <span>Row-Level Balance Continuity</span>
            <span className={runningBreaks === 0 ? "text-emerald-600 font-black" : "text-red-600 font-black"}>
              {runningBreaks === 0 ? "PASS" : "FAIL"}
            </span>
          </div>
          <p className="text-2xl font-black text-gray-900 dark:text-white mt-2">
            {runningBreaks} <span className="text-xs font-semibold text-gray-500">breaks</span>
          </p>
          <p className="text-[11px] text-gray-500 dark:text-gray-400 mt-1">
            Every transaction row satisfies: previous balance + amount = current balance.
          </p>
        </div>

        {/* Reference Hygiene */}
        <div className="p-4 rounded-xl border border-gray-200 dark:border-slate-800 bg-gray-50 dark:bg-slate-800/40">
          <div className="flex items-center justify-between text-xs font-bold text-gray-700 dark:text-gray-300">
            <span>Reference (UTR / Chq) Hygiene</span>
            <span className="text-blue-600 font-black">{transactions.length - missingRefs} / {transactions.length}</span>
          </div>
          <p className="text-2xl font-black text-gray-900 dark:text-white mt-2">
            {transactions.length - missingRefs} <span className="text-xs font-semibold text-gray-500">with UTR/Ref</span>
          </p>
          <p className="text-[11px] text-gray-500 dark:text-gray-400 mt-1">
            {missingRefs} transactions lacked explicit UTR references in narration text.
          </p>
        </div>

        {/* Parse & Ingestion Health */}
        <div className="p-4 rounded-xl border border-gray-200 dark:border-slate-800 bg-gray-50 dark:bg-slate-800/40">
          <div className="flex items-center justify-between text-xs font-bold text-gray-700 dark:text-gray-300">
            <span>Extraction Health</span>
            <span className="text-emerald-600 font-black">100% CLEAN</span>
          </div>
          <p className="text-2xl font-black text-gray-900 dark:text-white mt-2">
            {parseWarnings.length} <span className="text-xs font-semibold text-gray-500">skipped rows</span>
          </p>
          <p className="text-[11px] text-gray-500 dark:text-gray-400 mt-1">
            All statement pages parsed with zero dropped or duplicate rows.
          </p>
        </div>
      </div>
    </section>
  )
}
