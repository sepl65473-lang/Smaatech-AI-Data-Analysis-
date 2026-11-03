import React, { useState } from 'react'
import { apiUrl, getCsrfToken } from '../api/client'

const VALID_CATEGORIES = [
  'Salary',
  'Rent',
  'Bills',
  'EMI',
  'Investments',
  'Food',
  'Travel',
  'Shopping',
  'Healthcare',
  'Education',
  'Income',
  'Other',
]

function fmtInr(n) {
  if (n === null || n === undefined) return '—'
  return '₹' + Math.abs(n).toLocaleString('en-IN', { maximumFractionDigits: 0 })
}

export default function CategoryIntelligenceModal({
  isOpen = false,
  sessionId,
  transactions = [],
  onClose,
  onUpdateMapping,
  onCategoryUpdated,
}) {
  if (!isOpen) return null

  const [selectedTxnId, setSelectedTxnId] = useState(null)
  const [targetCategory, setTargetCategory] = useState('Rent')
  const [applyToAllParty, setApplyToAllParty] = useState(true)
  const [filterMode, setFilterMode] = useState('review') // 'review' | 'all'
  const [loading, setLoading] = useState(false)
  const [statusMsg, setStatusMsg] = useState('')

  const isUserConfirmed = (t) => ['user', 'user_override'].includes(t.classification_source)
  const isNeedsReview = (t) => !isUserConfirmed(t) && (
    ['rules_unclassified', 'llm_inferred'].includes(t.classification_source) ||
    t.confidence === 'Review' ||
    ['other', 'uncategorized'].includes((t.category || '').toLowerCase())
  )
  const reviewTxns = transactions.filter(isNeedsReview)
  const displayTxns = filterMode === 'review' ? reviewTxns : transactions

  const debitTxns = transactions.filter((t) => t.amount < 0)
  const totalDebits = debitTxns.reduce((sum, t) => sum + Math.abs(t.amount), 0)
  const classifiedDebits = debitTxns.filter((t) => (t.category || '').toLowerCase() !== 'other' && (t.category || '').toLowerCase() !== 'uncategorized')
  const classifiedSpend = classifiedDebits.reduce((sum, t) => sum + Math.abs(t.amount), 0)
  const classifiedPct = totalDebits > 0 ? ((classifiedSpend / totalDebits) * 100).toFixed(1) : '0.0'

  const unclassifiedDebits = reviewTxns.filter((t) => t.amount < 0)
  const unclassifiedSpend = unclassifiedDebits.reduce((sum, t) => sum + Math.abs(t.amount), 0)
  const unclassifiedPct = totalDebits > 0 ? ((unclassifiedSpend / totalDebits) * 100).toFixed(1) : '0.0'

  const activeTxn = transactions.find((t) => t.id === selectedTxnId) || displayTxns[0]

  async function handleApplyMapping() {
    if (!activeTxn) return
    setLoading(true)
    setStatusMsg('')

    const payload = applyToAllParty && (activeTxn.merchant || activeTxn.counterparty)
      ? { counterparty: activeTxn.merchant || activeTxn.counterparty, new_category: targetCategory }
      : { transaction_id: activeTxn.id, new_category: targetCategory }

    try {
      const csrfToken = getCsrfToken()
      const resp = await fetch(apiUrl(`/results/${sessionId}/category-mapping`), {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json', ...(csrfToken ? { 'X-CSRF-Token': decodeURIComponent(csrfToken) } : {}) },
        body: JSON.stringify(payload),
      })
      const data = await resp.json()
      if (data.status === 'success') {
        setStatusMsg(`✓ Successfully mapped ${data.modified_count} transaction(s) to '${data.new_category}'!`)
        const cb = onCategoryUpdated || onUpdateMapping
        if (cb) {
          cb(payload, data.metrics, data.category_summary)
        }
      } else {
        setStatusMsg('Failed to update mapping.')
      }
    } catch {
      setStatusMsg('Error updating category mapping.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-3xl max-w-4xl w-full p-6 shadow-2xl space-y-5 animate-scaleUp max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-100 dark:border-slate-800 pb-3">
          <div className="flex items-center gap-3">
            <span className="text-2xl">🏷️</span>
            <div>
              <h3 className="text-base font-bold text-gray-900 dark:text-white flex items-center gap-2">
                Category Intelligence & Classification Review
                <span className="text-xs px-2.5 py-0.5 rounded-full bg-blue-100 text-blue-800 dark:bg-blue-950/60 dark:text-blue-300 font-semibold">
                  {reviewTxns.length} to review
                </span>
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                Review automated payment-rail classifications (NEFT, UPI, RTGS, IMPS) and confirm custom categorization mappings.
              </p>
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

        {/* View Mode Filter Tabs */}
        <div className="flex items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-1.5 p-1 bg-gray-100 dark:bg-slate-800 rounded-xl">
            <button
              type="button"
              onClick={() => setFilterMode('review')}
              className={`px-3 py-1 rounded-lg font-semibold transition-all ${
                filterMode === 'review'
                  ? 'bg-white dark:bg-slate-900 text-emerald-700 dark:text-emerald-400 shadow-xs'
                  : 'text-gray-500 hover:text-gray-900 dark:hover:text-white'
              }`}
            >
              Needs Review / Other ({reviewTxns.length})
            </button>
            <button
              type="button"
              onClick={() => setFilterMode('all')}
              className={`px-3 py-1 rounded-lg font-semibold transition-all ${
                filterMode === 'all'
                  ? 'bg-white dark:bg-slate-900 text-emerald-700 dark:text-emerald-400 shadow-xs'
                  : 'text-gray-500 hover:text-gray-900 dark:hover:text-white'
              }`}
            >
              All Transactions ({transactions.length})
            </button>
          </div>

          <span className="text-gray-400 text-[11px]">
            Payment Rail Classification · Rules + Pattern Engine
          </span>
        </div>

        {/* Classification Queue Summary */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 p-3 bg-gray-50 dark:bg-slate-800/50 rounded-2xl border border-gray-200 dark:border-slate-800 text-xs">
          <div className="flex items-center justify-between px-3 py-2 bg-emerald-50/70 dark:bg-emerald-950/30 border border-emerald-200/60 dark:border-emerald-800/60 rounded-xl">
            <div>
              <span className="text-[10px] uppercase font-bold text-emerald-800 dark:text-emerald-300">Classified Outlays</span>
              <p className="text-sm font-black text-emerald-900 dark:text-emerald-200">{fmtInr(classifiedSpend)} <span className="text-xs font-semibold">({classifiedPct}%)</span></p>
            </div>
            <span className="text-xs font-bold text-emerald-700 dark:text-emerald-400">{classifiedDebits.length} txns</span>
          </div>
          <div className="flex items-center justify-between px-3 py-2 bg-amber-50/70 dark:bg-amber-950/30 border border-amber-200/60 dark:border-amber-800/60 rounded-xl">
            <div>
              <span className="text-[10px] uppercase font-bold text-amber-800 dark:text-amber-300">Review Queue (Unclassified)</span>
              <p className="text-sm font-black text-amber-900 dark:text-amber-200">{fmtInr(unclassifiedSpend)} <span className="text-xs font-semibold">({unclassifiedPct}%)</span></p>
            </div>
            <span className="text-xs font-bold text-amber-700 dark:text-amber-400">{unclassifiedDebits.length} txns</span>
          </div>
        </div>

        {/* Main 2-column layout */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-5 flex-1 min-h-0 overflow-hidden">
          {/* Left Table of Review Transactions (7 cols) */}
          <div className="md:col-span-7 border border-gray-200 dark:border-slate-800 rounded-2xl overflow-y-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-gray-50 dark:bg-slate-800/80 sticky top-0 text-[11px] font-bold text-gray-500 uppercase tracking-wider">
                <tr>
                  <th className="py-2.5 px-3">Date</th>
                  <th className="py-2.5 px-3">Counterparty / Description</th>
                  <th className="py-2.5 px-3">Rail</th>
                  <th className="py-2.5 px-3 text-right">Amount</th>
                  <th className="py-2.5 px-3">Confidence</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-slate-800">
                {displayTxns.map((t) => {
                  const isSelected = activeTxn?.id === t.id
                  return (
                    <tr
                      key={t.id}
                      onClick={() => setSelectedTxnId(t.id)}
                      className={`cursor-pointer transition-colors ${
                        isSelected
                          ? 'bg-emerald-50/80 dark:bg-emerald-950/30'
                          : 'hover:bg-gray-50/60 dark:hover:bg-slate-800/40'
                      }`}
                    >
                      <td className="py-2.5 px-3 font-mono text-[11px] text-gray-500 whitespace-nowrap">
                        {t.date}
                      </td>
                      <td className="py-2.5 px-3 max-w-[180px]">
                        <p className="font-semibold text-gray-900 dark:text-white truncate" title={t.description}>
                          {t.counterparty || t.merchant || t.clean_description}
                        </p>
                        <span className="text-[10px] text-gray-400">Current: {t.category}</span>
                        <p className="text-[10px] text-gray-500 dark:text-gray-400 italic truncate" title={t.classification_reason}>
                          {t.classification_reason || (t.category === 'Other' ? 'Preserved in Review Queue' : 'Rule match')}
                        </p>
                      </td>
                      <td className="py-2.5 px-3">
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-gray-100 dark:bg-slate-800 text-gray-700 dark:text-gray-300">
                          {t.payment_mode || 'OTHER'}
                        </span>
                      </td>
                      <td className={`py-2.5 px-3 text-right font-black whitespace-nowrap ${
                        t.amount > 0 ? 'text-emerald-600' : 'text-rose-600'
                      }`}>
                        {fmtInr(t.amount)}
                      </td>
                      <td className="py-2.5 px-3">
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                          t.confidence === 'High'
                            ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300'
                            : 'bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300'
                        }`}>
                          {t.confidence || 'Review'}
                        </span>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          {/* Right Reclassification Action Panel (5 cols) */}
          <div className="md:col-span-5 bg-gray-50/80 dark:bg-slate-800/40 border border-gray-200 dark:border-slate-800 rounded-2xl p-4 flex flex-col justify-between space-y-4">
            {activeTxn ? (
              <div className="space-y-4">
                <div className="border-b border-gray-200 dark:border-slate-700 pb-3">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400">Selected Transaction</span>
                  <h4 className="font-bold text-gray-900 dark:text-white text-sm mt-0.5 truncate">
                    {activeTxn.counterparty || activeTxn.merchant || activeTxn.clean_description}
                  </h4>
                  <div className="flex items-center gap-2 mt-1 text-xs">
                    <span className="font-mono text-gray-500">{activeTxn.date}</span>
                    <span className="font-bold text-gray-900 dark:text-white">{fmtInr(activeTxn.amount)}</span>
                    <span className="px-2 py-0.2 rounded text-[10px] bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700">
                      Rail: {activeTxn.payment_mode || 'OTHER'}
                    </span>
                  </div>
                  <div className="mt-2 text-[11px] text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-slate-800/60 p-2 rounded-lg">
                    <span className="font-bold">Reason:</span> {activeTxn.classification_reason || (activeTxn.category === 'Other' ? 'Unsupported narration preserved in Review Queue' : 'Rule keyword match')}
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-gray-700 dark:text-gray-300">
                    Assign Confirmed Category:
                  </label>
                  <select
                    value={targetCategory}
                    onChange={(e) => setTargetCategory(e.target.value)}
                    className="w-full text-xs p-2.5 rounded-xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-gray-800 dark:text-gray-200 font-semibold"
                  >
                    {VALID_CATEGORIES.map((cat) => (
                      <option key={cat} value={cat}>
                        {cat}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="p-3 bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-700 rounded-xl space-y-2">
                  <label className="flex items-center gap-2 text-xs text-gray-700 dark:text-gray-300 font-semibold cursor-pointer">
                    <input
                      type="checkbox"
                      checked={applyToAllParty}
                      onChange={(e) => setApplyToAllParty(e.target.checked)}
                      className="rounded text-emerald-600 focus:ring-0"
                    />
                    <span>
                      Apply to all transactions for{' '}
                      <strong>{activeTxn.counterparty || activeTxn.merchant || 'this entity'}</strong>
                    </span>
                  </label>
                  <p className="text-[11px] text-gray-400 leading-relaxed">
                    Automatically reclassifies all matching records, updating category analytics, donor charts, and the ledger in real time.
                  </p>
                </div>

                {statusMsg && (
                  <div className="p-2.5 rounded-xl text-xs font-bold bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                    {statusMsg}
                  </div>
                )}
              </div>
            ) : (
              <p className="text-xs text-gray-400">Select a transaction to review.</p>
            )}

            <div className="pt-3 border-t border-gray-200 dark:border-slate-700 flex items-center justify-between">
              <span className="text-[11px] text-gray-400 font-mono">
                {activeTxn ? `ID: ${activeTxn.id.slice(0, 8)}...` : ''}
              </span>

              <button
                type="button"
                onClick={handleApplyMapping}
                disabled={loading || !activeTxn}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white rounded-xl text-xs font-bold shadow-sm transition-colors flex items-center gap-1.5"
              >
                {loading ? 'Saving...' : 'Confirm Category Mapping'}
              </button>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="pt-2 border-t border-gray-100 dark:border-slate-800 flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 bg-gray-900 text-white dark:bg-white dark:text-gray-900 rounded-xl text-xs font-bold"
          >
            Done Reviewing
          </button>
        </div>
      </div>
    </div>
  )
}
