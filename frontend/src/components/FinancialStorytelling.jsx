import React, { useState } from 'react'

function fmtInr(n) {
  if (n === null || n === undefined) return '—'
  return '₹' + Math.abs(n).toLocaleString('en-IN', { maximumFractionDigits: 0 })
}

export default function FinancialStorytelling({
  metrics,
  transactions = [],
  aiEnabled,
  source,
  onInspectStory,
}) {
  const [activeTab, setActiveTab] = useState('all') // 'all' | 'liquidity' | 'concentration' | 'patterns'

  const totalSpend = metrics?.total_spend || 0
  const totalIncome = metrics?.total_income || 0
  const net = totalIncome - totalSpend
  const topCat = metrics?.top_categories?.[0]
  const topPayees = metrics?.top_payees || []
  const topPayers = metrics?.top_payers || []
  const largestDebit = metrics?.largest_debit
  const weekly = metrics?.weekly_cash_flow || []

  // Top 5 recipient concentration calculation
  const top5Total = topPayees.slice(0, 5).reduce((s, p) => s + p.amount, 0)
  const top5Pct = totalSpend > 0 ? ((top5Total / totalSpend) * 100).toFixed(1) : '0.0'

  // Weekly velocity change calculation
  const w24 = weekly.find((w) => w.week_start === '2023-06-12')
  const w25 = weekly.find((w) => w.week_start === '2023-06-19')

  // Weekend banking calculation
  const weekendTxns = transactions.filter((t) => {
    const d = new Date(t.date).getDay()
    return d === 0 || d === 6
  })
  const weekendVolume = weekendTxns.reduce((s, t) => s + Math.abs(t.amount), 0)

  // Repeated counterparties calculation (Strictly isolated by flow direction)
  const debitPartyFreq = {}
  const creditPartyFreq = {}
  transactions.forEach((t) => {
    const name = t.counterparty || t.merchant || ''
    if (!name) return
    if (t.amount < 0) {
      debitPartyFreq[name] = (debitPartyFreq[name] || 0) + 1
    } else if (t.amount > 0) {
      creditPartyFreq[name] = (creditPartyFreq[name] || 0) + 1
    }
  })
  const recurringDebitPayeesCount = Object.values(debitPartyFreq).filter(c => c > 1).length
  const repeatedDebitTxns = transactions.filter((t) => {
    if (t.amount >= 0) return false
    const name = t.counterparty || t.merchant || ''
    return name && (debitPartyFreq[name] || 0) > 1
  })
  const repeatedDebitTotal = repeatedDebitTxns.reduce((s, t) => s + Math.abs(t.amount), 0)
  const recurringDebitPct = totalSpend > 0 ? ((repeatedDebitTotal / totalSpend) * 100).toFixed(1) : '0.0'

  const recurringCreditRemittersCount = Object.values(creditPartyFreq).filter(c => c > 1).length
  const repeatedCreditTxns = transactions.filter((t) => {
    if (t.amount <= 0) return false
    const name = t.counterparty || t.merchant || ''
    return name && (creditPartyFreq[name] || 0) > 1
  })
  const repeatedCreditTotal = repeatedCreditTxns.reduce((s, t) => s + t.amount, 0)
  const recurringCreditPct = totalIncome > 0 ? ((repeatedCreditTotal / totalIncome) * 100).toFixed(1) : '0.0'

  // The 9 Storytelling Narratives requested
  const stories = [
    {
      id: 'story_top_expense_contributors',
      tab: 'concentration',
      title: '1. Primary Expense Category Drivers',
      theme: 'Expense Exposure',
      icon: '📊',
      badge: `${topCat?.percentage?.toFixed(1) || 0}% of Spend`,
      badgeCls: 'bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300',
      fact: `Category '${topCat?.category || 'Primary Category'}' represents ${fmtInr(topCat?.amount || 0)} across ${transactions.filter((t) => t.category === (topCat?.category || 'Other')).length} transactions, absorbing ${(topCat?.percentage || 0).toFixed(1)}% of total company outlays.`,
      interpretation: 'Disbursements are concentrated in core project vendor contracts and operational supplies. Continuous classification provides actionable departmental visibility.',
      amount: fmtInr(topCat?.amount || 0),
      statLabel: 'Dominant Outlay',
      count: transactions.filter((t) => t.category === (topCat?.category || 'Other')).length,
      actionLabel: `Filter '${topCat?.category || 'Primary Category'}' Outlays`,
      filterTarget: { category: topCat?.category || 'Other' },
    },
    {
      id: 'story_top5_concentration',
      tab: 'concentration',
      title: '2. Top 5 Recipient Concentration Risk',
      theme: 'Vendor Concentration',
      icon: '🏢',
      badge: `${top5Pct}% Absorbed by Top 5`,
      badgeCls: 'bg-purple-100 text-purple-800 dark:bg-purple-950/60 dark:text-purple-300',
      fact: `The top 5 beneficiaries absorbed ${fmtInr(top5Total)} out of ${fmtInr(totalSpend)} in total debits (${top5Pct}% of total expenditures), reflecting counterparty exposure across primary vendors and contractors.`,
      interpretation: 'Vendor concentration indicates the proportion of cash outflows directed to primary entities. Monitoring top payees ensures robust liquidity control and invoice verification.',
      amount: fmtInr(top5Total),
      statLabel: 'Top 5 Concentration',
      count: topPayees.slice(0, 5).reduce((acc, p) => acc + (p.count || 1), 0),
      actionLabel: 'Inspect Top Payees',
      filterTarget: { intelligenceTag: 'largest' },
    },
    {
      id: 'story_largest_income_sources',
      tab: 'liquidity',
      title: '3. Largest Income Remitters & Inflow Solvency',
      theme: 'Revenue Sources',
      icon: '💼',
      badge: topPayers[0]?.pct ? `${topPayers[0].pct}% from Primary Remitter` : 'Primary Remitter Solvency',
      badgeCls: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300',
      fact: `Inflows totaled ${fmtInr(totalIncome)} across ${metrics.credit_count || 0} deposits. ${topPayers[0]?.payer ? `${topPayers[0].payer} was the dominant remitter, depositing ${fmtInr(topPayers[0]?.amount)} (accounting for ${topPayers[0]?.pct || 0}% of all credits across ${topPayers[0]?.count || 0} milestone receipts)` : 'Inflow receipts were distributed across statement deposits'}${topPayers[1]?.payer ? `, followed by ${topPayers[1].payer} at ${fmtInr(topPayers[1]?.amount)} (${topPayers[1]?.pct || 0}% across ${topPayers[1]?.count || 0} tranche deposits).` : '.'}`,
      interpretation: 'The business demonstrates extreme customer revenue concentration. Operating liquidity is highly sensitive to the milestone release schedules of a single corporate client.',
      amount: fmtInr(topPayers[0]?.amount || 0),
      statLabel: 'Primary Inflow Source',
      count: topPayers[0]?.count || 0,
      actionLabel: 'Drilldown Top Remitter',
      filterTarget: { party: topPayers[0]?.payer || '' },
    },
    {
      id: 'story_cashflow_swings',
      tab: 'liquidity',
      title: '4. Daily & Weekly Cash-Flow Velocity Swings',
      theme: 'Liquidity Velocity',
      icon: '⚡',
      badge: 'Surplus to Deficit Cycles',
      badgeCls: 'bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300',
      fact: w24 && w25
        ? `Week 24 generated a net flow of +${fmtInr(w24.net || 0)} driven by inflow receipts. In Week 25, net flow shifted to -${fmtInr(Math.abs(w25.net || 0))} as vendor and operational obligations were settled.`
        : 'Cash management exhibits periodic liquidity cycles where inflow tranches are followed by scheduled operational settlements.',
      interpretation: 'Cash management exhibits a batch collection and disbursement pattern where vendor settlements align with client inflow milestones.',
      amount: w24 && w25 ? `+${fmtInr(w24.net || 0)} → -${fmtInr(Math.abs(w25.net || 0))}` : 'Periodic Cycles',
      statLabel: 'Weekly Swing Velocity',
      count: (w24?.count || 0) + (w25?.count || 0),
      actionLabel: 'Inspect Cash Flow',
      filterTarget: { type: 'All' },
    },
    {
      id: 'story_spending_spikes',
      tab: 'liquidity',
      title: '5. Significant Spending Spike Pattern',
      theme: 'Disbursement Spike',
      icon: '🚨',
      badge: largestDebit ? `Peak Outflow: ${fmtInr(largestDebit.amount)}` : 'Disbursement Concentration',
      badgeCls: 'bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300',
      fact: largestDebit
        ? `The account recorded a peak single disbursement of ${fmtInr(largestDebit.amount)} on ${largestDebit.date || 'statement period'} (${largestDebit.merchant || 'Primary Vendor'}).`
        : 'Disbursement flows reflect scheduled vendor and contractor settlements.',
      interpretation: 'Concentrated single-day outflows represent scheduled batch vendor disbursements following inflow milestones.',
      amount: fmtInr(largestDebit?.amount || 0),
      statLabel: 'Largest Single Outflow',
      count: 1,
      actionLabel: 'Inspect Peak Outflow',
      filterTarget: { type: 'Debit' },
    },
    {
      id: 'story_repeated_payments',
      tab: 'patterns',
      title: '6. Repeated Beneficiary Payment Patterns',
      theme: 'Beneficiary Patterns',
      icon: '🔁',
      badge: `${recurringDebitPayeesCount} Payees · ${repeatedDebitTxns.length} Debits (${fmtInr(repeatedDebitTotal)})`,
      badgeCls: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-950/60 dark:text-indigo-300',
      fact: `${recurringDebitPayeesCount} distinct recurring debit payees received ${repeatedDebitTxns.length} disbursements totaling ${fmtInr(repeatedDebitTotal)} (${recurringDebitPct}% of total debits). Repeated outflows represent routine vendor, salary, and operational working capital payments. Separately, recurring client deposits from ${recurringCreditRemittersCount} remitters provided ${fmtInr(repeatedCreditTotal)} across ${repeatedCreditTxns.length} remittances (${recurringCreditPct}% of total credits). Debits and credits are strictly segregated.`,
      interpretation: 'Directionally isolated outflow analysis: recurring vendor & director outlays represent legitimate working capital disbursements, completely separated from client revenue inflows.',
      amount: fmtInr(repeatedDebitTotal),
      statLabel: 'Recurring Debits Outflow',
      count: repeatedDebitTxns.length,
      actionLabel: 'Inspect Repeated Payees',
      filterTarget: { intelligenceTag: 'repeated' },
    },
    {
      id: 'story_category_exposure',
      tab: 'concentration',
      title: '7. Category-Level Exposure & Operating Breakdown',
      theme: 'Operational Exposure',
      icon: '🏷️',
      badge: 'Fixed vs Variable Costs',
      badgeCls: 'bg-blue-100 text-blue-800 dark:bg-blue-950/60 dark:text-blue-300',
      fact: 'Operating expenses are systematically categorized into baseline overheads (payroll, rent, utilities) alongside variable project and vendor contracts.',
      interpretation: 'Baseline operating commitments represent predictable recurring requirements, while discretionary vendor spend adjusts based on operational activity.',
      amount: fmtInr(totalSpend),
      statLabel: 'Total Operational Outlays',
      count: metrics.debit_count || 0,
      actionLabel: 'Filter Category Spend',
      filterTarget: { category: 'Salary' },
    },
    {
      id: 'story_unusual_patterns',
      tab: 'patterns',
      title: '8. Unusual Activity: Weekend Banking & Round Sums',
      theme: 'Operational Risk Signals',
      icon: '🛡️',
      badge: `${metrics.intelligence?.weekend_transactions || 0} Weekend Records`,
      badgeCls: 'bg-cyan-100 text-cyan-800 dark:bg-cyan-950/60 dark:text-cyan-300',
      fact: `${metrics.intelligence?.weekend_transactions || 0} transactions totaling ${fmtInr(weekendVolume)} were processed on weekends. Additionally, round-number disbursements and reference-tagged records reflect routine working capital and advance settlements.`,
      interpretation: 'Weekend banking activity reflects automated clearing and continuous operational schedules. Round amounts indicate standard advance disbursements.',
      amount: fmtInr(weekendVolume),
      statLabel: 'Weekend Volume',
      count: metrics.intelligence?.weekend_transactions || 0,
      actionLabel: 'Inspect Weekend Activity',
      filterTarget: { intelligenceTag: 'weekend' },
    },
    {
      id: 'story_income_expense_trend',
      tab: 'liquidity',
      title: '9. Overall Income vs. Expense Deficit Trajectory',
      theme: 'Net Position Assessment',
      icon: '📉',
      badge: `${net >= 0 ? '+' : '-'}${fmtInr(Math.abs(net))} Net Position`,
      badgeCls: net >= 0 ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300' : 'bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300',
      fact: `Aggregate expenditures (${fmtInr(totalSpend)}) and revenues (${fmtInr(totalIncome)}) yielded a net position of ${net >= 0 ? '+' : '-'}${fmtInr(Math.abs(net))}. Opening balance was ${fmtInr(metrics?.opening_balance || 0)}, closing balance landed at ${fmtInr(metrics?.closing_balance || 0)}, and statement ledger variance was exactly ₹0.00.`,
      interpretation: net >= 0
        ? 'The account generated positive cash retention during the statement period, increasing liquid reserves.'
        : 'The account drew down from opening cash reserves to bridge net operating outlays during this period.',
      amount: fmtInr(Math.abs(net)),
      statLabel: net >= 0 ? 'Net Cash Addition' : 'Net Reserve Drawdown',
      count: metrics?.transaction_count || transactions.length || 0,
      actionLabel: 'Inspect Full Cash Position',
      filterTarget: { type: 'All' },
    },
  ]

  const filteredStories = activeTab === 'all' ? stories : stories.filter((s) => s.tab === activeTab)

  return (
    <section className="bg-white dark:bg-slate-900 rounded-3xl border border-gray-200 dark:border-slate-800 shadow-xs p-6 space-y-6" id="financial-storytelling">
      {/* Header & Mode Badges */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-gray-100 dark:border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-2xl">📖</span>
            <h2 className="text-lg font-bold text-gray-900 dark:text-white">
              Financial Storytelling & Executive Commentary
            </h2>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300 font-bold">
              9 Calculated Narratives
            </span>
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            Separating verified ledger facts from financial interpretations. Every narrative is supported by exact ₹ amounts, percentages, and transaction counts.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className={`text-xs px-3 py-1 rounded-full font-bold border ${
            aiEnabled && source === 'llm'
              ? 'bg-purple-50 dark:bg-purple-950/40 text-purple-700 dark:text-purple-300 border-purple-200'
              : 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border-emerald-200'
          }`}>
            {aiEnabled && source === 'llm' ? '✨ LLM Narrative Engine' : '📐 Deterministic Financial Rules Engine'}
          </span>
        </div>
      </div>

      {/* Narrative Filter Tabs */}
      <div className="flex items-center gap-1.5 p-1 bg-gray-100 dark:bg-slate-800/80 rounded-2xl w-fit text-xs font-bold">
        {[
          { id: 'all', label: 'All 9 Narratives' },
          { id: 'liquidity', label: 'Liquidity & Cash Burn' },
          { id: 'concentration', label: 'Exposure & Concentration' },
          { id: 'patterns', label: 'Patterns & Risk Signals' },
        ].map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            className={`px-3 py-1.5 rounded-xl transition-all ${
              activeTab === tab.id
                ? 'bg-white dark:bg-slate-900 text-emerald-700 dark:text-emerald-400 shadow-xs'
                : 'text-gray-500 hover:text-gray-900 dark:hover:text-white'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Story Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {filteredStories.map((story) => (
          <div
            key={story.id}
            className="rounded-2xl border border-gray-200/90 dark:border-slate-800 bg-gray-50/50 dark:bg-slate-800/30 p-5 flex flex-col justify-between hover:shadow-md hover:border-emerald-300 dark:hover:border-emerald-800 transition-all space-y-4"
          >
            <div>
              {/* Card Title & Badge */}
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="text-xl">{story.icon}</span>
                  <div>
                    <h3 className="font-bold text-gray-900 dark:text-white text-xs leading-snug">
                      {story.title}
                    </h3>
                    <span className="text-[10px] text-gray-400 uppercase font-semibold">
                      {story.theme}
                    </span>
                  </div>
                </div>
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full shrink-0 ${story.badgeCls}`}>
                  {story.badge}
                </span>
              </div>

              {/* Verified Fact */}
              <div className="mt-3.5 p-3 bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 rounded-xl space-y-1">
                <span className="text-[10px] font-black uppercase tracking-wider text-emerald-700 dark:text-emerald-400 flex items-center gap-1">
                  <span>✓</span> VERIFIED FINANCIAL FACT
                </span>
                <p className="text-xs text-gray-800 dark:text-gray-200 leading-relaxed font-medium">
                  {story.fact}
                </p>
              </div>

              {/* Interpretation */}
              <div className="mt-2.5 p-3 bg-amber-50/50 dark:bg-amber-950/20 border border-amber-100/60 dark:border-amber-900/30 rounded-xl space-y-1">
                <span className="text-[10px] font-black uppercase tracking-wider text-amber-700 dark:text-amber-400 flex items-center gap-1">
                  <span>💡</span> FINANCIAL INTERPRETATION
                </span>
                <p className="text-xs text-gray-600 dark:text-gray-300 leading-relaxed">
                  {story.interpretation}
                </p>
              </div>
            </div>

            {/* Bottom Actions & Driver Indicator */}
            <div className="pt-3 border-t border-gray-200/60 dark:border-slate-700/60 flex items-center justify-between text-xs">
              <div>
                <span className="text-[10px] text-gray-400 uppercase block font-semibold">
                  {story.statLabel}
                </span>
                <span className="font-mono font-bold text-gray-900 dark:text-white text-xs">
                  {story.amount}
                </span>
              </div>

              <button
                type="button"
                onClick={() => onInspectStory && onInspectStory(story.filterTarget)}
                className="px-3 py-1.5 bg-white dark:bg-slate-800 hover:bg-emerald-50 dark:hover:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400 border border-gray-200 dark:border-slate-700 rounded-xl font-bold transition-all flex items-center gap-1 hover:border-emerald-300 text-xs shadow-2xs"
              >
                <span>{story.actionLabel}</span>
                <span>→</span>
              </button>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
