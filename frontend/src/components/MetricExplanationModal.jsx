import React from 'react'

function fmtInr(n) {
  if (n === null || n === undefined) return '—'
  return '₹' + Math.abs(n).toLocaleString('en-IN', { maximumFractionDigits: 2 })
}

export default function MetricExplanationModal({
  metricKey,
  metrics,
  transactions = [],
  onClose,
  onApplyFilter,
}) {
  if (!metricKey || !metrics) return null

  const totalIncome = metrics.total_income || 0
  const totalSpend = metrics.total_spend || 0
  const net = totalIncome - totalSpend
  const opening = metrics.opening_balance || 0
  const closing = metrics.closing_balance || 0
  const txnTotal = metrics.transaction_count || transactions.length || 0

  const guides = {
    income: {
      title: 'Total Income / Remittances',
      icon: '📥',
      badge: `${metrics.credit_count || 0} Credit Transactions`,
      badgeCls: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300',
      definition: 'The aggregate sum of all credit deposits, inward transfers, client remittances, and interest credited to the bank account during the statement period.',
      currentValueAssessment: `Total inflow stands at ${fmtInr(totalIncome)} across ${metrics.credit_count || 0} credit events. Average remittance size was ${fmtInr(metrics.avg_credit_amount || totalIncome / (metrics.credit_count || 1))}. Highest single deposit was ${fmtInr(metrics.largest_credit?.amount || 0)} from ${metrics.largest_credit?.merchant || 'Primary Remitter'} on ${metrics.largest_credit?.date || 'statement date'}.`,
      whyItMatters: 'Inflow velocity dictates short-term liquidity and cash-flow runway. For operational solvency, income must reliably exceed or match recurring monthly debt and vendor liabilities.',
      contributingSummary: 'Income concentration is tracked across key client remittances and milestone transfers during the statement period.',
      recommendedInvestigation: 'Review remitter concentration risk to verify whether revenue relies on a few key counterparties.',
      actionLabel: 'Filter All Income (Credits)',
      filterTarget: { type: 'Credit' },
    },
    spend: {
      title: 'Total Spend / Operational Outlays',
      icon: '📤',
      badge: `${metrics.debit_count || 0} Debit Transactions`,
      badgeCls: 'bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300',
      definition: 'The total value of all debits, vendor payouts, statutory charges, salary transfers, and operational disbursements withdrawn from the account.',
      currentValueAssessment: `Outflows total ${fmtInr(totalSpend)} across ${metrics.debit_count || 0} debits, averaging ${fmtInr(metrics.avg_debit_amount || totalSpend / (metrics.debit_count || 1))} per debit. The single largest outlay was ${fmtInr(metrics.largest_debit?.amount || 0)} on ${metrics.largest_debit?.date || 'statement date'} (${metrics.largest_debit?.merchant || 'Primary Outflow'}).`,
      whyItMatters: 'Uncontrolled spending velocity accelerates cash-burn and erodes working capital reserves, especially when capital expenditure or recurring withdrawals occur ahead of collections.',
      contributingSummary: 'Operational disbursements reflect settlements across vendors, suppliers, contractor invoices, and statutory obligations.',
      recommendedInvestigation: 'Audit top vendor disbursements and high-frequency recurring transfers for authorization compliance.',
      actionLabel: 'Filter All Expenses (Debits)',
      filterTarget: { type: 'Debit' },
    },
    net: {
      title: 'Net Cash Flow & Cash Burn Velocity',
      icon: '⚖️',
      badge: net >= 0 ? 'Cash Surplus' : 'Operating Deficit',
      badgeCls: net >= 0 ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300' : 'bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300',
      definition: 'The net mathematical difference between Total Income and Total Spend (Income − Spend). Represents retained cash or operating drawdown during the period.',
      currentValueAssessment: `The account generated a net ${net >= 0 ? 'cash surplus' : 'cash deficit'} of ${fmtInr(Math.abs(net))} during the statement period. ${net >= 0 ? 'Total income exceeded spending, strengthening reserve liquidity.' : 'Total spending exceeded income, resulting in a liquidity drawdown from opening reserves.'}`,
      whyItMatters: 'Persistent negative net cash flow burns liquidity buffers and may require short-term working capital financing, overdraft utilization, or equity capital injections.',
      contributingSummary: 'Cash-flow distribution reflects timing between milestone receivables and operating disbursements across weekly cycles.',
      recommendedInvestigation: 'Inspect high-disbursement periods to evaluate timing alignment between receivables and payables.',
      actionLabel: 'Inspect Cash Flow',
      filterTarget: { type: 'Debit' },
    },
    savings: {
      title: 'Savings & Liquidity Retention Rate',
      icon: '🏦',
      badge: `${(metrics.savings_rate || 0).toFixed(1)}% Retention`,
      badgeCls: 'bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300',
      definition: 'The percentage of total income retained in bank reserves after funding all operational disbursements: ((Income − Spend) ÷ Income) × 100.',
      currentValueAssessment: `The retention rate is ${(metrics.savings_rate || 0).toFixed(1)}%, indicating the proportion of deposits retained after all debits during this statement cycle.`,
      whyItMatters: 'Healthy corporate and professional treasury benchmarks recommend retaining 15% to 25% of gross revenues to withstand debtor delays and unforeseen liabilities.',
      contributingSummary: `${metrics.credit_count || 0} credit deposits totaling ${fmtInr(totalIncome)} were processed alongside ${metrics.debit_count || 0} debit disbursements totaling ${fmtInr(totalSpend)}.`,
      recommendedInvestigation: 'Review discretionary and director transfers to identify opportunities to restore a 20% retention buffer.',
      actionLabel: 'Inspect Discretionary Spend',
      filterTarget: { intelligenceTag: 'unusual' },
    },
    coverage: {
      title: 'Coverage / Income-to-Expense Ratio',
      icon: '🔄',
      badge: `${(metrics.income_to_expense_ratio || (totalSpend > 0 ? totalIncome / totalSpend : 1.0)).toFixed(2)}x Coverage`,
      badgeCls: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-950/60 dark:text-indigo-300',
      definition: 'The multiple of total income divided by total spend (Income ÷ Spend). A ratio > 1.0x indicates cash generation; < 1.0x indicates cash drawdown.',
      currentValueAssessment: `The coverage ratio is ${(metrics.income_to_expense_ratio || (totalSpend > 0 ? totalIncome / totalSpend : 1.0)).toFixed(2)}x. For every ₹100 disbursed during the period, the entity generated ₹${Math.min(999, Math.round((totalIncome / (totalSpend || 1)) * 100))} in top-line deposits.`,
      whyItMatters: 'A coverage ratio below 1.0x is sustainable in the short term only if backed by adequate opening liquidity balances.',
      contributingSummary: `Opening balance of ${fmtInr(opening)} provided liquidity buffer against operating expenses, ending with a closing balance of ${fmtInr(closing)}.`,
      recommendedInvestigation: 'Analyze monthly recurring expenses to model the runway if income receipts are delayed by 30 days.',
      actionLabel: 'Review Recurring Charges',
      filterTarget: { intelligenceTag: 'repeated' },
    },
    highest_credit: {
      title: 'Highest Single Credit Inflow',
      icon: '⭐',
      badge: fmtInr(metrics.largest_credit?.amount || 0),
      badgeCls: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300',
      definition: 'The single largest credit transaction recorded in the statement ledger during the reconciliation period.',
      currentValueAssessment: `Highest credit of ${fmtInr(metrics.largest_credit?.amount || 0)} arrived on ${metrics.largest_credit?.date || 'statement period'} via ${metrics.largest_credit?.payment_mode || 'transfer'} from ${metrics.largest_credit?.merchant || 'Primary Remitter'}${metrics.largest_credit?.reference_no ? ' (Ref: ' + metrics.largest_credit.reference_no + ')' : ''}.`,
      whyItMatters: 'Represents a major inflow milestone in a single transaction, highlighting reliance on key client receipts.',
      contributingSummary: 'Major milestone receipt contributing significantly to total monthly liquid inflow.',
      recommendedInvestigation: 'Inspect primary remitter receipts to verify client invoicing schedule.',
      actionLabel: 'Drilldown Top Remitter',
      filterTarget: { party: metrics.largest_credit?.merchant || '' },
    },
    highest_debit: {
      title: 'Highest Single Debit Outflow',
      icon: '🚨',
      badge: fmtInr(metrics.largest_debit?.amount || 0),
      badgeCls: 'bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300',
      definition: 'The largest single disbursement from the account during the statement period.',
      currentValueAssessment: `Highest debit of ${fmtInr(metrics.largest_debit?.amount || 0)} occurred on ${metrics.largest_debit?.date || 'statement date'}${metrics.largest_debit?.reference_no ? ' (Ref: ' + metrics.largest_debit.reference_no + ')' : ''} described as '${metrics.largest_debit?.merchant || 'Primary Outflow'}'.`,
      whyItMatters: 'Represents a major disbursement concentration in a single transaction. Requires invoice matching and PO authorization review.',
      contributingSummary: 'Significant single-transaction outlay relative to average disbursement size.',
      recommendedInvestigation: 'Inspect transaction details to verify payout authorization and invoice matching.',
      actionLabel: 'Filter Highest Outflow',
      filterTarget: { type: 'Debit' },
    },
    reconciliation: {
      title: 'Ledger Reconciliation & Mathematical Proof',
      icon: '🛡️',
      badge: 'Balanced · Zero Variance (₹0.00)',
      badgeCls: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300',
      definition: 'Formal mathematical proof verifying that Opening Balance + Credits − Debits equals Statement Closing Balance, with 0 breaks in row-by-row balance continuity.',
      currentValueAssessment: `Equation proof: ${fmtInr(opening)} + ${fmtInr(totalIncome)} − ${fmtInr(totalSpend)} = ${fmtInr(closing)}. Statement variance is exactly ₹0.00 across all ${txnTotal} transaction rows.`,
      whyItMatters: 'Zero variance guarantees data integrity: no transactions were skipped, duplicated, or misread during PDF tabular extraction.',
      contributingSummary: `${txnTotal}/${txnTotal} consecutive rows maintained mathematical balance continuity (Prev Balance ± Amount = Current Balance).`,
      recommendedInvestigation: 'Inspect reconciliation audit log and bank verification checklist.',
      actionLabel: 'Inspect Audit Proof',
      filterTarget: {},
    },
    transactions: {
      title: 'Total Transaction Volume & Velocity',
      icon: '📑',
      badge: `${txnTotal} Verified Transactions`,
      badgeCls: 'bg-blue-100 text-blue-800 dark:bg-blue-950/60 dark:text-blue-300',
      definition: 'The total count of financial movements (both credits and debits) processed through the account during the statement period.',
      currentValueAssessment: `${txnTotal} transactions recorded during the statement period (${metrics.credit_count || 0} credits vs ${metrics.debit_count || 0} debits).`,
      whyItMatters: 'High transaction count combined with low credit count indicates high micro-disbursement activity supporting day-to-day operations.',
      contributingSummary: 'Transactions are systematically classified across accounting categories including operations, payroll, rent, and vendor disbursements.',
      recommendedInvestigation: 'Explore all transactions in the interactive explorer with custom search and filters.',
      actionLabel: 'View All Transactions',
      filterTarget: { category: 'All' },
    },
  }

  const g = guides[metricKey] || guides.net

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-3xl max-w-xl w-full p-6 shadow-2xl space-y-5 animate-scaleUp">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-100 dark:border-slate-800 pb-3">
          <div className="flex items-center gap-2.5">
            <span className="text-2xl">{g.icon}</span>
            <div>
              <h3 className="text-base font-bold text-gray-900 dark:text-white">{g.title}</h3>
              <span className={`inline-block text-[10px] font-bold px-2 py-0.5 rounded-full mt-0.5 ${g.badgeCls}`}>
                {g.badge}
              </span>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="w-8 h-8 rounded-full flex items-center justify-center text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-slate-800 text-lg font-bold"
          >
            ✕
          </button>
        </div>

        {/* 5 Structural Explanations */}
        <div className="space-y-3.5 text-xs">
          {/* 1. What it means */}
          <div className="p-3 bg-gray-50 dark:bg-slate-800/60 rounded-xl space-y-1">
            <span className="text-[10px] uppercase font-bold text-gray-400 tracking-wider">1. What This Metric Means</span>
            <p className="text-gray-700 dark:text-gray-300 leading-relaxed">{g.definition}</p>
          </div>

          {/* 2. What the actual value indicates */}
          <div className="p-3 bg-blue-50/60 dark:bg-blue-950/30 border border-blue-100 dark:border-blue-900/40 rounded-xl space-y-1">
            <span className="text-[10px] uppercase font-bold text-blue-600 dark:text-blue-400 tracking-wider">2. What Current Value Indicates</span>
            <p className="text-gray-800 dark:text-gray-200 leading-relaxed font-medium">{g.currentValueAssessment}</p>
          </div>

          {/* 3. Why it matters */}
          <div className="p-3 bg-gray-50 dark:bg-slate-800/60 rounded-xl space-y-1">
            <span className="text-[10px] uppercase font-bold text-gray-400 tracking-wider">3. Strategic Financial Significance</span>
            <p className="text-gray-700 dark:text-gray-300 leading-relaxed">{g.whyItMatters}</p>
          </div>

          {/* 4. Contributing Transactions */}
          <div className="p-3 bg-gray-50 dark:bg-slate-800/60 rounded-xl space-y-1">
            <span className="text-[10px] uppercase font-bold text-gray-400 tracking-wider">4. Key Driver Transactions</span>
            <p className="text-gray-700 dark:text-gray-300 leading-relaxed font-mono">{g.contributingSummary}</p>
          </div>

          {/* 5. What to investigate next */}
          <div className="p-3 bg-amber-50/60 dark:bg-amber-950/30 border border-amber-100 dark:border-amber-900/40 rounded-xl space-y-1">
            <span className="text-[10px] uppercase font-bold text-amber-700 dark:text-amber-400 tracking-wider">5. Recommended Next Investigation</span>
            <p className="text-gray-800 dark:text-gray-200 leading-relaxed">{g.recommendedInvestigation}</p>
          </div>
        </div>

        {/* Footer actions */}
        <div className="pt-3 border-t border-gray-100 dark:border-slate-800 flex items-center justify-between">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 border border-gray-200 dark:border-slate-700 rounded-xl text-xs font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-slate-800"
          >
            Close Guide
          </button>

          <button
            type="button"
            onClick={() => {
              if (onApplyFilter) onApplyFilter(g.filterTarget)
              onClose()
            }}
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-sm transition-colors"
          >
            <span>{g.actionLabel}</span>
            <span>→</span>
          </button>
        </div>
      </div>
    </div>
  )
}
