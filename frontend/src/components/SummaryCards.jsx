function fmt(n) {
  if (n === null || n === undefined) return '—'
  return '₹' + Math.abs(n).toLocaleString('en-IN', { maximumFractionDigits: 0 })
}

function Card({ label, value, sub, accent, badge }) {
  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5 flex flex-col justify-between">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">{label}</span>
        {badge && <span>{badge}</span>}
      </div>
      <div className="my-2">
        <span className={`text-2xl font-black tracking-tight ${accent}`}>{value}</span>
      </div>
      {sub && <span className="text-xs text-gray-400 font-medium">{sub}</span>}
    </div>
  )
}

export default function SummaryCards({ metrics }) {
  const isNetPositive = metrics.savings >= 0
  const savingsColor = isNetPositive ? 'text-blue-600' : 'text-rose-600'
  const rateColor =
    metrics.savings_rate >= 20
      ? 'text-emerald-600'
      : metrics.savings_rate >= 10
      ? 'text-amber-600'
      : 'text-rose-600'

  return (
    <div className="space-y-4">
      {/* Primary KPI Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card
          label="Total Income (Credits)"
          value={fmt(metrics.total_income)}
          sub={`${metrics.credit_count || 0} credits · Avg: ${fmt(metrics.avg_credit_amount)}`}
          accent="text-emerald-600"
        />
        <Card
          label="Total Spend (Debits)"
          value={fmt(metrics.total_spend)}
          sub={`${metrics.debit_count || 0} debits · Avg: ${fmt(metrics.avg_debit_amount)}`}
          accent="text-rose-600"
        />
        <Card
          label="Net Cash Flow"
          value={(metrics.savings < 0 ? '-' : '+') + fmt(metrics.savings)}
          sub={isNetPositive ? 'Net surplus for period' : 'Deficit / overspent'}
          accent={savingsColor}
        />
        <Card
          label="Savings Rate"
          value={`${(metrics.savings_rate || 0).toFixed(1)}%`}
          sub={metrics.savings_rate >= 20 ? 'Above 20% benchmark ✓' : 'Below 20% target'}
          accent={rateColor}
        />
      </div>

      {/* Ledger & Reconciliation Row */}
      {(metrics.opening_balance !== null || metrics.closing_balance !== null) && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-slate-50 border border-slate-200/80 rounded-xl px-5 py-3 flex items-center justify-between">
            <div>
              <p className="text-[11px] font-semibold uppercase text-slate-500">Opening Balance</p>
              <p className="text-lg font-bold text-slate-800">{fmt(metrics.opening_balance)}</p>
            </div>
            <span className="text-xl">🏦</span>
          </div>

          <div className="bg-slate-50 border border-slate-200/80 rounded-xl px-5 py-3 flex items-center justify-between">
            <div>
              <p className="text-[11px] font-semibold uppercase text-slate-500">Closing Balance</p>
              <p className="text-lg font-bold text-slate-800">{fmt(metrics.closing_balance)}</p>
            </div>
            <span className="text-xl">🏁</span>
          </div>

          <div className="bg-slate-50 border border-slate-200/80 rounded-xl px-5 py-3 flex items-center justify-between">
            <div>
              <p className="text-[11px] font-semibold uppercase text-slate-500">Ledger Reconciliation</p>
              <div className="flex items-center gap-2 mt-0.5">
                <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-bold ${
                  metrics.is_reconciled
                    ? 'bg-emerald-100 text-emerald-800'
                    : 'bg-amber-100 text-amber-800'
                }`}>
                  {metrics.is_reconciled ? '✓ Fully Balanced' : `Delta: ${fmt(metrics.reconciliation_delta)}`}
                </span>
              </div>
            </div>
            <span className="text-xs text-slate-400 font-mono">
              Op + In - Sp = Cl
            </span>
          </div>
        </div>
      )}
    </div>
  )
}
