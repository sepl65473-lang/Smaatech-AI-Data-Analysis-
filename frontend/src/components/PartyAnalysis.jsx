import React, { useState } from 'react'

function fmtInr(n) {
  if (n === null || n === undefined) return '—'
  return '₹' + Math.abs(n).toLocaleString('en-IN', { maximumFractionDigits: 0 })
}

function fmtDate(d) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })
}

export default function PartyAnalysis({
  topPayers = [],
  topPayees = [],
  selectedParty = null,
  onSelectParty,
}) {
  const [activeTab, setActiveTab] = useState('payees') // 'payees' | 'payers'

  const activeList = activeTab === 'payees' ? topPayees : topPayers
  const isPayees = activeTab === 'payees'

  return (
    <section className="bg-white dark:bg-slate-900 rounded-2xl border border-gray-200 dark:border-slate-800 shadow-xs p-6 space-y-6" id="party-analysis">
      {/* Title & Switcher */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-gray-100 dark:border-slate-800 pb-4">
        <div>
          <h2 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <span>🤝</span> Party and Counterparty Intelligence
          </h2>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
            Identify primary cash-flow partners, concentration risks, and recurring transfer counterparties.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {selectedParty && (
            <span className="text-xs font-bold text-blue-700 dark:text-blue-300 bg-blue-100 dark:bg-blue-950/60 px-2.5 py-1 rounded-full border border-blue-300">
              Active Party: {selectedParty}
            </span>
          )}

          <div className="flex bg-gray-100 dark:bg-slate-800 p-1 rounded-xl text-xs font-semibold">
            <button
              onClick={() => setActiveTab('payees')}
              className={`px-3 py-1.5 rounded-lg transition-all ${
                isPayees
                  ? 'bg-white dark:bg-slate-700 text-gray-900 dark:text-white shadow-2xs'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
              }`}
            >
              Top Recipients / Outflows ({topPayees.length})
            </button>
            <button
              onClick={() => setActiveTab('payers')}
              className={`px-3 py-1.5 rounded-lg transition-all ${
                !isPayees
                  ? 'bg-white dark:bg-slate-700 text-gray-900 dark:text-white shadow-2xs'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
              }`}
            >
              Top Senders / Inflows ({topPayers.length})
            </button>
          </div>
        </div>
      </div>

      {/* Counterparties Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-xs text-left border-collapse">
          <thead>
            <tr className="border-b border-gray-200 dark:border-slate-800 text-gray-500 dark:text-gray-400 text-[11px] font-bold uppercase">
              <th className="py-3 px-3">#</th>
              <th className="py-3 px-3">{isPayees ? 'Recipient / Beneficiary' : 'Sender / Remitter'}</th>
              <th className="py-3 px-3 text-right">Total Amount</th>
              <th className="py-3 px-3 text-right">Share of Flow</th>
              <th className="py-3 px-3 text-center">Txn Count</th>
              <th className="py-3 px-3 text-right">Avg Size</th>
              <th className="py-3 px-3 text-center">Date Range</th>
              <th className="py-3 px-3 text-center">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-slate-800">
            {activeList.length === 0 ? (
              <tr>
                <td colSpan={8} className="py-8 text-center text-gray-400 text-xs">
                  No counterparties recorded for this track.
                </td>
              </tr>
            ) : (
              activeList.map((p, idx) => {
                const name = p.payee || p.payer || 'Unknown'
                const isSelected = selectedParty === name
                const isFrequent = p.count >= 3

                return (
                  <tr
                    key={idx}
                    onClick={() => onSelectParty && onSelectParty(isSelected ? null : name)}
                    className={`cursor-pointer transition-colors ${
                      isSelected
                        ? 'bg-blue-50 dark:bg-blue-950/40 font-bold'
                        : 'hover:bg-gray-50 dark:hover:bg-slate-800/60'
                    }`}
                  >
                    <td className="py-3 px-3 text-gray-400 font-mono text-[11px]">{idx + 1}</td>
                    <td className="py-3 px-3">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-gray-900 dark:text-white truncate max-w-xs" title={name}>
                          {name}
                        </span>
                        {isFrequent && (
                          <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-purple-100 dark:bg-purple-950/60 text-purple-700 dark:text-purple-300 border border-purple-200">
                            🔁 {p.count}x
                          </span>
                        )}
                      </div>
                    </td>
                    <td className={`py-3 px-3 text-right font-black whitespace-nowrap ${
                      isPayees ? 'text-rose-600 dark:text-rose-400' : 'text-emerald-600 dark:text-emerald-400'
                    }`}>
                      {isPayees ? '-' : '+'}{fmtInr(p.amount)}
                    </td>
                    <td className="py-3 px-3 text-right whitespace-nowrap text-gray-600 dark:text-gray-300">
                      <div className="flex items-center justify-end gap-1.5">
                        <span>{p.pct || 0}%</span>
                        <div className="w-12 bg-gray-200 dark:bg-slate-700 h-1.5 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${isPayees ? 'bg-rose-500' : 'bg-emerald-500'}`}
                            style={{ width: `${Math.min(p.pct || 0, 100)}%` }}
                          />
                        </div>
                      </div>
                    </td>
                    <td className="py-3 px-3 text-center font-bold text-gray-800 dark:text-gray-200">
                      {p.count}
                    </td>
                    <td className="py-3 px-3 text-right text-gray-600 dark:text-gray-300 whitespace-nowrap">
                      {fmtInr(p.avg_amount || (p.count ? Math.round(p.amount / p.count) : 0))}
                    </td>
                    <td className="py-3 px-3 text-center text-gray-500 dark:text-gray-400 text-[11px] whitespace-nowrap font-mono">
                      {p.first_date ? `${fmtDate(p.first_date)} – ${fmtDate(p.last_date)}` : '—'}
                    </td>
                    <td className="py-3 px-3 text-center">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation()
                          if (onSelectParty) {
                            onSelectParty(isSelected ? null : name)
                          }
                        }}
                        className={`text-[11px] px-2.5 py-1 rounded font-semibold transition-all ${
                          isSelected
                            ? 'bg-blue-600 text-white'
                            : 'bg-gray-100 dark:bg-slate-800 text-gray-600 dark:text-gray-400 hover:bg-blue-100 hover:text-blue-800'
                        }`}
                      >
                        {isSelected ? 'Clear Filter' : 'Drilldown'}
                      </button>
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>
    </section>
  )
}
