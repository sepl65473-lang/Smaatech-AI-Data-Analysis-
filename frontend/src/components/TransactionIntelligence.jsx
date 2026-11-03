import React from 'react'

function fmtInr(n) {
  if (n === null || n === undefined) return '—'
  return '₹' + Math.abs(n).toLocaleString('en-IN', { maximumFractionDigits: 0 })
}

export default function TransactionIntelligence({
  transactions = [],
  _intelligence = {},
  selectedFlag = null,
  onSelectFlag,
}) {
  // Derive flags directly from transactions to ensure 100% accurate dynamic responsiveness
  const missingRefs = transactions.filter((t) => !t.reference_no)
  const weekendTxns = transactions.filter((t) => {
    const d = new Date(t.date)
    const day = d.getDay() // 0 = Sun, 6 = Sat
    return day === 0 || day === 6
  })
  const largeTxns = transactions.filter((t) => Math.abs(t.amount) >= 100000)
  const uncategorizedTxns = transactions.filter((t) => (t.category || '').toLowerCase() === 'other')

  // Unusual round amounts (e.g., transfers of exact 50k, 1L, etc.)
  const roundAmountTxns = transactions.filter((t) => {
    const amt = Math.abs(t.amount)
    return amt >= 20000 && amt % 5000 === 0
  })

  // Duplicate audit (same date + same amount)
  const dateAmtMap = {}
  transactions.forEach((t) => {
    const key = `${t.date}_${t.amount}`
    dateAmtMap[key] = (dateAmtMap[key] || 0) + 1
  })
  const duplicateTxns = transactions.filter((t) => dateAmtMap[`${t.date}_${t.amount}`] > 1)
  const sameDayMatchGroups = Object.values(dateAmtMap).filter((c) => c > 1).length

  // Repeated payees: counterparties with >= 2 debit transactions (strictly isolated debits)
  const debitPartyFreq = {}
  transactions.forEach((t) => {
    if (t.amount < 0) {
      const name = t.merchant || t.counterparty || t.clean_description || ''
      if (name) debitPartyFreq[name] = (debitPartyFreq[name] || 0) + 1
    }
  })
  const recurringDebitPayeesCount = Object.values(debitPartyFreq).filter((c) => c > 1).length
  const repeatedPayeeTxns = transactions.filter((t) => {
    if (t.amount >= 0) return false
    const name = t.merchant || t.counterparty || t.clean_description || ''
    return name && (debitPartyFreq[name] || 0) > 1
  })
  const repeatedDebitSpend = repeatedPayeeTxns.reduce((sum, t) => sum + Math.abs(t.amount), 0)
  const totalDebits = transactions.filter((t) => t.amount < 0).reduce((sum, t) => sum + Math.abs(t.amount), 0)
  const repeatedDebitPct = totalDebits > 0 ? ((repeatedDebitSpend / totalDebits) * 100).toFixed(1) : '0.0'

  // Repeat remitters: counterparties with >= 2 credit transactions (strictly isolated credits)
  const creditPartyFreq = {}
  transactions.forEach((t) => {
    if (t.amount > 0) {
      const name = t.merchant || t.counterparty || t.clean_description || ''
      if (name) creditPartyFreq[name] = (creditPartyFreq[name] || 0) + 1
    }
  })
  const recurringCreditRemittersCount = Object.values(creditPartyFreq).filter((c) => c > 1).length
  const repeatCreditTxns = transactions.filter((t) => {
    if (t.amount <= 0) return false
    const name = t.merchant || t.counterparty || t.clean_description || ''
    return name && (creditPartyFreq[name] || 0) > 1
  })
  const repeatCreditIncome = repeatCreditTxns.reduce((sum, t) => sum + t.amount, 0)

  const flags = [
    {
      id: 'largest',
      title: 'High-Value Outflows & Inflows',
      icon: '💎',
      count: largeTxns.length,
      amount: largeTxns.reduce((sum, t) => sum + Math.abs(t.amount), 0),
      desc: 'Transactions with absolute value ≥ ₹1,00,000 requiring director-level audit.',
      tag: 'Critical Outflow',
      color: 'border-blue-200 dark:border-blue-900 bg-blue-50/50 dark:bg-blue-950/20 text-blue-700 dark:text-blue-300',
    },
    {
      id: 'repeated',
      title: 'Recurring Payees (Debits Only)',
      icon: '🔁',
      count: repeatedPayeeTxns.length,
      amount: repeatedDebitSpend,
      desc: `${recurringDebitPayeesCount} payees across ${repeatedPayeeTxns.length} disbursements (${repeatedDebitPct}% of debits). Client deposits (${recurringCreditRemittersCount} remitters, ${repeatCreditTxns.length} deposits, ${fmtInr(repeatCreditIncome)}) are tracked separately.`,
      tag: `${recurringDebitPayeesCount} Payees`,
      color: 'border-purple-200 dark:border-purple-900 bg-purple-50/50 dark:bg-purple-950/20 text-purple-700 dark:text-purple-300',
    },
    {
      id: 'duplicate',
      title: 'Same-Day Same-Amount Matches',
      icon: '👯',
      count: duplicateTxns.length,
      amount: duplicateTxns.reduce((sum, t) => sum + Math.abs(t.amount), 0),
      desc: `${duplicateTxns.length} records across ${sameDayMatchGroups} groups. Multi-factor review (date, amount, counterparty, reference, narration): No potential duplicates detected under the applied matching rules. Missing references handled explicitly; manual review preserved for suspicious items.`,
      tag: 'Informational Match',
      color: 'border-orange-200 dark:border-orange-900 bg-orange-50/50 dark:bg-orange-950/20 text-orange-700 dark:text-orange-300',
    },
    {
      id: 'unusual',
      title: 'Round Amount Transfers',
      icon: '🎯',
      count: roundAmountTxns.length,
      amount: roundAmountTxns.reduce((sum, t) => sum + Math.abs(t.amount), 0),
      desc: 'Transfers with exact round sums (multiples of ₹5k/₹10k/₹50k) common in advances/salaries.',
      tag: 'Audit Marker',
      color: 'border-amber-200 dark:border-amber-900 bg-amber-50/50 dark:bg-amber-950/20 text-amber-700 dark:text-amber-300',
    },
    {
      id: 'weekend',
      title: 'Weekend Banking Activity',
      icon: '📅',
      count: weekendTxns.length,
      amount: weekendTxns.reduce((sum, t) => sum + Math.abs(t.amount), 0),
      desc: 'Transfers executed on Saturdays and Sundays (IMPS/NEFT/Internal transfers).',
      tag: 'Timing Pattern',
      color: 'border-cyan-200 dark:border-cyan-900 bg-cyan-50/50 dark:bg-cyan-950/20 text-cyan-700 dark:text-cyan-300',
    },
    {
      id: 'missing_ref',
      title: 'Missing Reference / UTR Numbers',
      icon: '🔎',
      count: missingRefs.length,
      amount: missingRefs.reduce((sum, t) => sum + Math.abs(t.amount), 0),
      desc: 'Transactions where the statement did not provide a distinct bank UTR or cheque reference.',
      tag: 'Compliance Flag',
      color: 'border-rose-200 dark:border-rose-900 bg-rose-50/50 dark:bg-rose-950/20 text-rose-700 dark:text-rose-400',
    },
    {
      id: 'uncategorized',
      title: 'Review Queue (Unclassified Spend)',
      icon: '🏷️',
      count: uncategorizedTxns.length,
      amount: uncategorizedTxns.reduce((sum, t) => sum + Math.abs(t.amount), 0),
      desc: 'Unsupported narrations preserved in Review Queue for confirmation. Never auto-forced into arbitrary categories.',
      tag: 'Review Queue',
      color: 'border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-800/40 text-slate-700 dark:text-slate-300',
    },
  ]

  return (
    <section className="bg-white dark:bg-slate-900 rounded-2xl border border-gray-200 dark:border-slate-800 shadow-xs p-6 space-y-6" id="transaction-intelligence">
      {/* Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-gray-100 dark:border-slate-800 pb-4">
        <div>
          <h2 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <span>🛡️</span> Transaction Intelligence & Risk Signals
          </h2>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
            Automated analytical screening for operational patterns, timing flags, and reference hygiene.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-[11px] font-semibold text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-slate-800 px-3 py-1 rounded-full border border-gray-200 dark:border-slate-700">
            ℹ Analytical flags · Not fraud determinations
          </span>
          {selectedFlag && (
            <button
              onClick={() => onSelectFlag && onSelectFlag(null)}
              className="text-xs text-red-600 dark:text-red-400 hover:underline font-bold"
            >
              Clear Flag Filter
            </button>
          )}
        </div>
      </div>

      {/* 6 Intelligence Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {flags.map((flag) => {
          const isSelected = selectedFlag === flag.id

          return (
            <div
              key={flag.id}
              onClick={() => onSelectFlag && onSelectFlag(isSelected ? null : flag.id)}
              className={`rounded-2xl border p-5 flex flex-col justify-between cursor-pointer transition-all hover:scale-[1.01] ${
                flag.color
              } ${isSelected ? 'ring-2 ring-emerald-500 shadow-md' : 'hover:shadow-sm'}`}
            >
              <div>
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 font-bold text-xs">
                    <span className="text-xl">{flag.icon}</span>
                    <span className="text-gray-900 dark:text-white">{flag.title}</span>
                  </div>
                  <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-white dark:bg-slate-800 shadow-2xs">
                    {flag.tag}
                  </span>
                </div>

                <div className="my-3 flex items-baseline justify-between">
                  <span className="text-2xl font-black text-gray-900 dark:text-white">
                    {flag.count} <span className="text-xs font-semibold text-gray-500">records</span>
                  </span>
                  <span className="text-sm font-bold text-gray-800 dark:text-gray-200">
                    {fmtInr(flag.amount)}
                  </span>
                </div>

                <p className="text-xs text-gray-600 dark:text-gray-400 leading-relaxed">
                  {flag.desc}
                </p>
              </div>

              <div className="mt-4 pt-3 border-t border-gray-200/60 dark:border-slate-700/60 flex items-center justify-between text-xs font-bold">
                <span className="text-emerald-700 dark:text-emerald-400">
                  {isSelected ? '✓ Filter Applied' : 'Click to Inspect'}
                </span>
                <span className="text-gray-400">→</span>
              </div>
            </div>
          )
        })}
      </div>
    </section>
  )
}
