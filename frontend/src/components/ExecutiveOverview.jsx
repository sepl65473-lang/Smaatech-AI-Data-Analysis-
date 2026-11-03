import React, { useState } from 'react'

function fmt(n) {
  if (n === null || n === undefined) return '—'
  return '₹' + Math.abs(n).toLocaleString('en-IN', { maximumFractionDigits: 0 })
}

function KpiCard({ title, value, sub, accent, icon, tooltip, badge, onClick, onExplain }) {
  const [showTooltip, setShowTooltip] = useState(false)

  return (
    <div
      className="relative bg-white dark:bg-slate-900 rounded-2xl border border-gray-200 dark:border-slate-800 shadow-xs hover:shadow-md transition-all p-5 flex flex-col justify-between group"
    >
      <div className="flex items-center justify-between gap-2">
        <div
          onClick={onClick}
          className={`flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 ${
            onClick ? 'cursor-pointer hover:text-emerald-600 dark:hover:text-emerald-400' : ''
          }`}
        >
          <span className="text-base">{icon}</span>
          <span>{title}</span>
        </div>
        <div className="flex items-center gap-1.5">
          {badge && (
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-gray-100 dark:bg-slate-800 text-gray-600 dark:text-gray-300">
              {badge}
            </span>
          )}
          {onExplain && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation()
                onExplain()
              }}
              title="Click for Metric Diagnosis & Investigation Guide"
              className="w-5 h-5 rounded-full flex items-center justify-center text-gray-400 hover:text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-950/40 text-xs font-bold transition-colors"
            >
              ℹ
            </button>
          )}
          {tooltip && !onExplain && (
            <div
              className="relative inline-block cursor-help"
              onMouseEnter={() => setShowTooltip(true)}
              onMouseLeave={() => setShowTooltip(false)}
            >
              <span className="text-gray-400 hover:text-gray-600 text-xs">ℹ</span>
              {showTooltip && (
                <div className="absolute right-0 top-6 z-40 w-52 p-2 bg-slate-900 text-white text-[11px] rounded-lg shadow-xl border border-slate-700 leading-tight">
                  {tooltip}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <div
        onClick={onClick || onExplain}
        className={`my-2.5 ${onClick || onExplain ? 'cursor-pointer' : ''}`}
      >
        <span className={`text-2xl font-black tracking-tight ${accent}`}>{value}</span>
      </div>

      <div className="flex items-center justify-between text-xs text-gray-400 dark:text-gray-500 font-medium">
        <span>{sub || ''}</span>
        {onExplain && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation()
              onExplain()
            }}
            className="text-[10px] text-emerald-600 dark:text-emerald-400 hover:underline font-bold"
          >
            Guide →
          </button>
        )}
      </div>
    </div>
  )
}

export default function ExecutiveOverview({
  metrics,
  filteredMetrics,
  isFiltered,
  onSelectType,
  onExplainMetric,
}) {
  const activeMetrics = isFiltered ? filteredMetrics : metrics

  const isNetPositive = (activeMetrics.savings ?? 0) >= 0
  const savingsColor = isNetPositive ? 'text-blue-600 dark:text-blue-400' : 'text-rose-600 dark:text-rose-400'
  const savingsRate = activeMetrics.savings_rate ?? 0
  const rateColor =
    savingsRate >= 20
      ? 'text-emerald-600 dark:text-emerald-400'
      : savingsRate >= 10
      ? 'text-amber-600 dark:text-amber-400'
      : 'text-rose-600 dark:text-rose-400'

  const incomeToExpense =
    (activeMetrics.total_spend || 0) > 0
      ? ((activeMetrics.total_income || 0) / (activeMetrics.total_spend || 1)).toFixed(2)
      : '—'

  return (
    <section className="space-y-4" id="executive-overview">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <span>📈</span> Executive Financial Overview
          </h2>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {isFiltered
              ? 'Computed dynamically for active filtered transactions'
              : 'Holistic KPI summary across the entire statement period with instant accounting diagnostic guides'}
          </p>
        </div>
        {isFiltered && (
          <span className="text-xs bg-amber-100 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 font-bold px-3 py-1 rounded-full border border-amber-300 dark:border-amber-800">
            ⚡ Filtered View Active
          </span>
        )}
      </div>

      {/* 9 Executive KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
        {/* 1. Total Income */}
        <KpiCard
          title="Total Income"
          value={fmt(activeMetrics.total_income)}
          sub={`${activeMetrics.credit_count || 0} credits · Avg: ${fmt(activeMetrics.avg_credit_amount)}`}
          accent="text-emerald-600 dark:text-emerald-400"
          icon="📥"
          tooltip="Sum of all incoming funds (credits) deposited into the account."
          onClick={() => onSelectType && onSelectType('Credit')}
          onExplain={() => onExplainMetric && onExplainMetric('income')}
        />

        {/* 2. Total Spend */}
        <KpiCard
          title="Total Spend"
          value={fmt(activeMetrics.total_spend)}
          sub={`${activeMetrics.debit_count || 0} debits · Avg: ${fmt(activeMetrics.avg_debit_amount)}`}
          accent="text-rose-600 dark:text-rose-400"
          icon="📤"
          tooltip="Sum of all outgoing funds (withdrawals/debits) paid out from the account."
          onClick={() => onSelectType && onSelectType('Debit')}
          onExplain={() => onExplainMetric && onExplainMetric('spend')}
        />

        {/* 3. Net Cash Flow */}
        <KpiCard
          title="Net Cash Flow"
          value={(activeMetrics.savings < 0 ? '-' : '+') + fmt(activeMetrics.savings)}
          sub={isNetPositive ? 'Net surplus accumulated' : 'Net deficit / outflow exceeded income'}
          accent={savingsColor}
          icon="⚖️"
          tooltip="Net cash movement: Total Credits minus Total Debits over the period."
          onExplain={() => onExplainMetric && onExplainMetric('net')}
        />

        {/* 4. Savings Rate */}
        <KpiCard
          title="Savings Rate"
          value={`${savingsRate.toFixed(1)}%`}
          sub={savingsRate >= 20 ? 'Above 20% benchmark ✓' : 'Below 20% target rate'}
          accent={rateColor}
          icon="🏦"
          tooltip="Percentage of incoming revenue retained after meeting all expenses: (Net / Income) × 100."
          onExplain={() => onExplainMetric && onExplainMetric('savings')}
        />

        {/* 5. Income-to-Expense Ratio */}
        <KpiCard
          title="Coverage Ratio"
          value={incomeToExpense !== '—' ? `${incomeToExpense}x` : '—'}
          sub={Number(incomeToExpense) >= 1.0 ? 'Expenses fully covered' : 'Expenses exceed income'}
          accent={Number(incomeToExpense) >= 1.0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-amber-600 dark:text-amber-400'}
          icon="🔄"
          tooltip="Income-to-Expense Coverage Ratio (Income ÷ Spend). 1.0x indicates break-even."
          onExplain={() => onExplainMetric && onExplainMetric('coverage')}
        />

        {/* 6. Transaction Count */}
        <KpiCard
          title="Transactions"
          value={`${activeMetrics.transaction_count || 0}`}
          sub={`${activeMetrics.credit_count || 0} Cr / ${activeMetrics.debit_count || 0} Dr`}
          accent="text-blue-600 dark:text-blue-400"
          icon="📋"
          tooltip="Total number of transaction records identified and verified from statement."
          onExplain={() => onExplainMetric && onExplainMetric('transactions')}
        />

        {/* 7. Average Transaction Amount */}
        <KpiCard
          title="Avg Transaction"
          value={fmt(activeMetrics.avg_transaction_amount)}
          sub="Overall transaction volume mean"
          accent="text-purple-600 dark:text-purple-400"
          icon="📊"
          tooltip="Average monetary magnitude of all movements: (Credits + Debits) ÷ Total Transactions."
          onExplain={() => onExplainMetric && onExplainMetric('transactions')}
        />

        {/* 8. Highest Credit */}
        <KpiCard
          title="Highest Credit"
          value={fmt(activeMetrics.largest_credit?.amount)}
          sub={activeMetrics.largest_credit?.merchant || activeMetrics.largest_credit?.clean_description?.slice(0, 24) || '—'}
          accent="text-emerald-600 dark:text-emerald-400"
          icon="⭐"
          badge={activeMetrics.largest_credit?.date ? String(activeMetrics.largest_credit.date).slice(5) : ''}
          tooltip="Largest single incoming deposit recorded during the statement period."
          onExplain={() => onExplainMetric && onExplainMetric('highest_credit')}
        />

        {/* 9. Highest Debit */}
        <KpiCard
          title="Highest Debit"
          value={fmt(activeMetrics.largest_debit?.amount)}
          sub={activeMetrics.largest_debit?.merchant || activeMetrics.largest_debit?.clean_description?.slice(0, 24) || '—'}
          accent="text-rose-600 dark:text-rose-400"
          icon="🚨"
          badge={activeMetrics.largest_debit?.date ? String(activeMetrics.largest_debit.date).slice(5) : ''}
          tooltip="Largest single withdrawal/transfer outflow recorded during the statement period."
          onExplain={() => onExplainMetric && onExplainMetric('highest_debit')}
        />

        {/* 10. Reconciliation Status Card */}
        <KpiCard
          title="Reconciliation"
          value={metrics.is_reconciled ? 'Balanced ✓' : 'Delta Alert'}
          sub={`Variance: ${fmt(metrics.reconciliation_delta)}`}
          accent={metrics.is_reconciled ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}
          icon="🛡️"
          badge="Audit Proof"
          tooltip="Statement ledger reconciliation: Opening Balance + Credits - Debits = Closing Balance."
          onExplain={() => onExplainMetric && onExplainMetric('reconciliation')}
        />
      </div>

      {/* Ledger Balances & Dynamic Reconciliation Equation Strip */}
      {(metrics.opening_balance !== null || metrics.closing_balance !== null) && (
        <div className="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-2xl p-4 shadow-2xs">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-center">
            {/* Opening Balance */}
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-blue-50 dark:bg-blue-950/60 border border-blue-200 dark:border-blue-800 flex items-center justify-center text-lg shrink-0">
                🏦
              </div>
              <div>
                <p className="text-[11px] font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400">Statement Opening Balance</p>
                <p className="text-base font-black text-gray-900 dark:text-white">{fmt(metrics.opening_balance)}</p>
              </div>
            </div>

            {/* Inflow / Outflow Net Equation */}
            <div className="flex items-center gap-3 md:col-span-2 bg-gray-50 dark:bg-slate-800/60 px-4 py-2.5 rounded-xl border border-gray-200 dark:border-slate-700">
              <div className="text-xs leading-relaxed text-gray-700 dark:text-gray-300 font-mono w-full">
                <div className="flex items-center justify-between font-bold text-[11px] mb-1 text-gray-500 dark:text-gray-400">
                  <span>AUDIT RECONCILIATION FORMULA</span>
                  <span className={metrics.is_reconciled ? 'text-emerald-600 dark:text-emerald-400 font-black' : 'text-red-600'}>
                    {metrics.is_reconciled ? '✓ EXACT MATCH (Variance: ₹0.00)' : 'VARIANCE DETECTED'}
                  </span>
                </div>
                <div className="flex flex-wrap items-center gap-1.5 text-xs font-semibold">
                  <span>{fmt(metrics.opening_balance)} (Op)</span>
                  <span className="text-emerald-600 font-bold">+</span>
                  <span className="text-emerald-600">{fmt(metrics.total_income)} (Cr)</span>
                  <span className="text-rose-600 font-bold">−</span>
                  <span className="text-rose-600">{fmt(metrics.total_spend)} (Dr)</span>
                  <span>=</span>
                  <span className="font-black text-gray-900 dark:text-white">{fmt(metrics.closing_balance)} (Cl)</span>
                </div>
              </div>
            </div>

            {/* Closing Balance */}
            <div className="flex items-center gap-3 justify-start md:justify-end">
              <div className="w-10 h-10 rounded-xl bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-800 flex items-center justify-center text-lg shrink-0">
                🏁
              </div>
              <div>
                <p className="text-[11px] font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400">Statement Closing Balance</p>
                <p className="text-base font-black text-gray-900 dark:text-white">{fmt(metrics.closing_balance)}</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
