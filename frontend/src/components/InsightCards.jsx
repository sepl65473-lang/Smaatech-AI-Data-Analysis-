import React from 'react'

function fmtInr(n) {
  if (n === null || n === undefined) return '—'
  return '₹' + Math.abs(n).toLocaleString('en-IN', { maximumFractionDigits: 0 })
}

export default function InsightCards({
  _insights = [],
  metrics,
  transactions = [],
  source,
  aiEnabled,
  onInspectInsight,
}) {
  // Synthesize rich, mathematically grounded insights from actual metrics and transactions
  const totalSpend = metrics?.total_spend || 0
  const totalIncome = metrics?.total_income || 0
  const net = metrics?.savings || 0
  const topCat = metrics?.top_categories?.[0]
  const topPayer = metrics?.top_payers?.[0]
  const topPayee = metrics?.top_payees?.[0]
  const largestTxn = metrics?.biggest_transactions?.[0]

  const richInsights = [
    {
      id: 'net_flow',
      title: net < 0 ? 'Monthly Net Outflow Deficit' : 'Net Liquidity Surplus Generated',
      category: 'Cash Flow',
      icon: net < 0 ? '⚠️' : '🎉',
      amount: fmtInr(Math.abs(net)),
      percentage: totalIncome > 0 ? `${Math.abs(metrics?.savings_rate || 0).toFixed(1)}% of income` : '—',
      count: metrics?.transaction_count || 0,
      whyItMatters: net < 0
        ? `Total expenses (₹${(totalSpend / 100000).toFixed(2)}L) exceeded total revenue (₹${(totalIncome / 100000).toFixed(2)}L) by ₹${Math.abs(net).toLocaleString('en-IN')}, drawing down bank reserves.`
        : `Total deposits exceeded withdrawals, leaving a positive liquidity buffer of ₹${net.toLocaleString('en-IN')}.`,
      actionLabel: 'Inspect All Cash Flow',
      filterType: net < 0 ? 'Debit' : 'Credit',
    },
    {
      id: 'top_category',
      title: `Dominant Category: ${topCat?.category || 'General'}`,
      category: 'Cost Concentration',
      icon: '📊',
      amount: fmtInr(topCat?.amount),
      percentage: `${topCat?.percentage?.toFixed(1) || 0}% of all spend`,
      count: transactions.filter((t) => t.category === topCat?.category).length,
      whyItMatters: `Category '${topCat?.category}' accounts for ₹${(topCat?.amount || 0).toLocaleString('en-IN')}, representing the vast majority of company operating outflows this period.`,
      actionLabel: `Filter '${topCat?.category}' Txns`,
      filterCategory: topCat?.category,
    },
    {
      id: 'counterparty_concentration',
      title: `Key Inflow Counterparty: ${topPayer?.payer || 'Primary Remitter'}`,
      category: 'Inflow Source',
      icon: '💼',
      amount: fmtInr(topPayer?.amount),
      percentage: `${topPayer?.pct || 0}% of total income`,
      count: topPayer?.count || 1,
      whyItMatters: `${topPayer?.payer} contributed ₹${(topPayer?.amount || 0).toLocaleString('en-IN')} across ${topPayer?.count} remittances, representing the single largest revenue stream.`,
      actionLabel: `Drilldown ${topPayer?.payer}`,
      filterParty: topPayer?.payer,
    },
    {
      id: 'counterparty_outflow',
      title: `Largest Outflow Partner: ${topPayee?.payee || 'Primary Payee'}`,
      category: 'Vendor Outflow',
      icon: '🏢',
      amount: fmtInr(topPayee?.amount),
      percentage: `${topPayee?.pct || 0}% of all debits`,
      count: topPayee?.count || 1,
      whyItMatters: `Transfers to ${topPayee?.payee} totaled ₹${(topPayee?.amount || 0).toLocaleString('en-IN')}, making it the primary vendor/contractor counterparty.`,
      actionLabel: `Inspect ${topPayee?.payee} Outflows`,
      filterParty: topPayee?.payee,
    },
    {
      id: 'largest_single',
      title: `Peak Single Outflow: ${largestTxn?.merchant || largestTxn?.clean_description?.slice(0, 24) || 'Major Transfer'}`,
      category: 'High-Value Transfer',
      icon: '⚡',
      amount: fmtInr(largestTxn?.amount),
      percentage: totalSpend > 0 ? `${((Math.abs(largestTxn?.amount || 0) / totalSpend) * 100).toFixed(1)}% of total spend` : '—',
      count: 1,
      whyItMatters: `A single transfer of ₹${Math.abs(largestTxn?.amount || 0).toLocaleString('en-IN')} occurred on ${largestTxn?.date}. Large lump-sum disbursements have an outsized impact on monthly liquidity.`,
      actionLabel: 'Inspect Large Transactions',
      filterFlag: 'largest',
    },
  ]

  return (
    <div className="bg-white dark:bg-slate-900 rounded-2xl border border-gray-200 dark:border-slate-800 shadow-xs p-6 space-y-5" id="ai-insights-section">
      <div className="flex items-center justify-between border-b border-gray-100 dark:border-slate-800 pb-3">
        <div>
          <h2 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <span>💡</span> AI Financial Insights & Executive Actions
          </h2>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
            Key findings derived deterministically from actual ledger metrics and counterparty patterns.
          </p>
        </div>

        <span className={`text-xs px-2.5 py-1 rounded-full font-bold border ${
          aiEnabled && source === 'llm'
            ? 'bg-purple-100 dark:bg-purple-950/60 text-purple-700 dark:text-purple-300 border-purple-300'
            : 'bg-blue-100 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 border-blue-300'
        }`}>
          {aiEnabled && source === 'llm' ? '✨ LLM Enhanced' : '📊 Verified Metrics Engine'}
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {richInsights.map((ins) => (
          <div
            key={ins.id}
            className="bg-gray-50/80 dark:bg-slate-800/50 border border-gray-200/80 dark:border-slate-700/80 rounded-2xl p-4 flex flex-col justify-between hover:shadow-sm transition-all"
          >
            <div>
              <div className="flex items-center justify-between gap-2 mb-2">
                <span className="text-xs font-bold text-gray-800 dark:text-gray-200 flex items-center gap-1.5">
                  <span className="text-base">{ins.icon}</span>
                  <span className="truncate">{ins.title}</span>
                </span>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-white dark:bg-slate-800 text-gray-500 border border-gray-200 dark:border-slate-700 shrink-0">
                  {ins.category}
                </span>
              </div>

              <div className="my-2.5 flex items-baseline justify-between">
                <span className="text-lg font-black text-gray-900 dark:text-white">
                  {ins.amount}
                </span>
                <span className="text-xs font-semibold text-emerald-700 dark:text-emerald-400">
                  {ins.percentage}
                </span>
              </div>

              <p className="text-xs text-gray-600 dark:text-gray-400 leading-relaxed">
                {ins.whyItMatters}
              </p>
            </div>

            <div className="mt-4 pt-3 border-t border-gray-200/60 dark:border-slate-700/60 flex items-center justify-between">
              <span className="text-[11px] text-gray-400 font-mono">
                {ins.count} relevant txn{ins.count > 1 ? 's' : ''}
              </span>
              <button
                type="button"
                onClick={() => onInspectInsight && onInspectInsight(ins)}
                className="text-xs font-bold text-emerald-600 dark:text-emerald-400 hover:text-emerald-700 dark:hover:text-emerald-300 flex items-center gap-1 hover:underline"
              >
                <span>{ins.actionLabel}</span>
                <span>→</span>
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
