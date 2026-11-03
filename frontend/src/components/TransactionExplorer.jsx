import React, { useState, useMemo } from 'react'

function fmtDate(d) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
  })
}

function fmtCurrency(n) {
  if (n === null || n === undefined) return '—'
  return '₹' + Math.abs(n).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function SortIcon({ sortKey, currentKey, sortDir }) {
  if (sortKey !== currentKey) return <span className="text-gray-300 dark:text-slate-600 ml-1">↕</span>
  return <span className="text-emerald-600 dark:text-emerald-400 font-bold ml-1">{sortDir === 'asc' ? '↑' : '↓'}</span>
}

export default function TransactionExplorer({
  transactions = [],
  externalFilters = {},
  onFilterChange,
  onResetFilters,
  onOpenCategoryReview,
}) {
  const [pageSize, setPageSize] = useState(25)
  const [page, setPage] = useState(1)
  const [sortKey, setSortKey] = useState('date')
  const [sortDir, setSortDir] = useState('desc')
  const [selectedTxn, setSelectedTxn] = useState(null)

  // Column visibility state
  const [colVisible, setColVisible] = useState({
    date: true,
    description: true,
    merchant: true,
    mode: true,
    reference: true,
    category: true,
    debit: true,
    credit: true,
    balance: true,
  })

  const [showColMenu, setShowColMenu] = useState(false)

  // Collect unique categories and counterparties for dropdowns
  const categories = useMemo(() => {
    const set = new Set(transactions.map((t) => t.category).filter(Boolean))
    return ['All', ...Array.from(set).sort()]
  }, [transactions])

  const parties = useMemo(() => {
    const set = new Set(
      transactions
        .map((t) => t.merchant || t.clean_description)
        .filter(Boolean)
    )
    return ['All', ...Array.from(set).sort()]
  }, [transactions])

  // Filter & sort logic
  const filtered = useMemo(() => {
    const q = (externalFilters.search || '').toLowerCase().trim()
    const cat = externalFilters.category || 'All'
    const party = externalFilters.party || 'All'
    const type = externalFilters.type || 'All'
    const sDate = externalFilters.startDate || ''
    const eDate = externalFilters.endDate || ''
    const minA = externalFilters.minAmount ? parseFloat(externalFilters.minAmount) : null
    const maxA = externalFilters.maxAmount ? parseFloat(externalFilters.maxAmount) : null
    const specificDate = externalFilters.date || ''
    const flag = externalFilters.intelligenceTag || ''

    return transactions
      .filter((t) => {
        // Specific date from chart click
        if (specificDate) {
          const tDate = typeof t.date === 'string' ? t.date.slice(0, 10) : new Date(t.date).toISOString().slice(0, 10)
          if (tDate !== specificDate) return false
        }

        // Category
        if (cat !== 'All' && t.category !== cat) return false

        // Party
        if (party !== 'All') {
          const name = t.merchant || t.clean_description || ''
          if (name !== party) return false
        }

        // Type
        if (type === 'Debit' && t.amount >= 0) return false
        if (type === 'Credit' && t.amount <= 0) return false

        // Date Range
        const tDate = typeof t.date === 'string' ? t.date.slice(0, 10) : new Date(t.date).toISOString().slice(0, 10)
        if (sDate && tDate < sDate) return false
        if (eDate && tDate > eDate) return false

        // Amount range
        const absAmt = Math.abs(t.amount)
        if (minA !== null && absAmt < minA) return false
        if (maxA !== null && absAmt > maxA) return false

        // Intelligence Flag Filters
        if (flag === 'missing_ref' && t.reference_no) return false
        if (flag === 'weekend') {
          const day = new Date(t.date).getDay()
          if (day !== 0 && day !== 6) return false
        }
        if (flag === 'largest' && absAmt < 100000) return false
        if (flag === 'unusual') {
          if (absAmt < 20000 || absAmt % 5000 !== 0) return false
        }
        if (flag === 'uncategorized' && (t.category || '').toLowerCase() !== 'other') return false

        // Search text
        if (q) {
          const desc = (t.description || '').toLowerCase()
          const clean = (t.clean_description || '').toLowerCase()
          const merch = (t.merchant || '').toLowerCase()
          const ref = (t.reference_no || '').toLowerCase()
          const catStr = (t.category || '').toLowerCase()
          const amtStr = String(absAmt)
          if (
            !desc.includes(q) &&
            !clean.includes(q) &&
            !merch.includes(q) &&
            !ref.includes(q) &&
            !catStr.includes(q) &&
            !amtStr.includes(q)
          ) {
            return false
          }
        }
        return true
      })
      .sort((a, b) => {
        let diff = 0
        if (sortKey === 'date') {
          diff = new Date(a.date).getTime() - new Date(b.date).getTime()
        } else if (sortKey === 'debit') {
          const dA = a.amount < 0 ? Math.abs(a.amount) : 0
          const dB = b.amount < 0 ? Math.abs(b.amount) : 0
          diff = dA - dB
        } else if (sortKey === 'credit') {
          const cA = a.amount > 0 ? a.amount : 0
          const cB = b.amount > 0 ? b.amount : 0
          diff = cA - cB
        } else if (sortKey === 'balance') {
          diff = (a.balance ?? 0) - (b.balance ?? 0)
        } else {
          diff = Math.abs(a.amount) - Math.abs(b.amount)
        }
        return sortDir === 'asc' ? diff : -diff
      })
  }, [transactions, externalFilters, sortKey, sortDir])

  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize))
  const pageItems = filtered.slice((page - 1) * pageSize, page * pageSize)

  function toggleSort(key) {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir('desc')
    }
    setPage(1)
  }

  // Client-side export of filtered transactions
  function exportFilteredCSV() {
    const headers = ['Date', 'Description', 'Counterparty', 'Ref_UTR', 'Category', 'Debit_INR', 'Credit_INR', 'Balance_INR']
    const rows = filtered.map((t) => [
      t.date,
      `"${(t.clean_description || t.description || '').replace(/"/g, '""')}"`,
      `"${(t.merchant || '').replace(/"/g, '""')}"`,
      `"${t.reference_no || ''}"`,
      `"${t.category || ''}"`,
      t.amount < 0 ? Math.abs(t.amount).toFixed(2) : '0.00',
      t.amount > 0 ? t.amount.toFixed(2) : '0.00',
      t.balance !== null && t.balance !== undefined ? t.balance.toFixed(2) : '',
    ])

    const csvContent = '\uFEFF' + [headers.join(','), ...rows.map((r) => r.join(','))].join('\r\n')
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `Filtered_Transactions_${new Date().toISOString().slice(0, 10)}.csv`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  return (
    <section className="bg-white dark:bg-slate-900 rounded-2xl border border-gray-200 dark:border-slate-800 shadow-xs p-6 space-y-5" id="transaction-explorer">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <span>📑</span> Transaction Explorer & Ledger
          </h2>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
            Showing {filtered.length} of {transactions.length} verified transactions with complete running balances.
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {/* Column Visibility Button */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setShowColMenu(!showColMenu)}
              className="text-xs px-3 py-1.5 border border-gray-200 dark:border-slate-700 rounded-xl text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-slate-800 font-semibold"
            >
              Columns ▾
            </button>
            {showColMenu && (
              <div className="absolute right-0 top-9 z-30 w-44 p-2 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-xl shadow-lg text-xs space-y-1">
                {Object.keys(colVisible).map((col) => (
                  <label key={col} className="flex items-center gap-2 px-2 py-1 hover:bg-gray-50 dark:hover:bg-slate-700 rounded cursor-pointer capitalize">
                    <input
                      type="checkbox"
                      checked={colVisible[col]}
                      onChange={(e) => setColVisible({ ...colVisible, [col]: e.target.checked })}
                      className="rounded text-emerald-600"
                    />
                    <span>{col}</span>
                  </label>
                ))}
              </div>
            )}
          </div>

          {/* Category Intelligence Review */}
          {onOpenCategoryReview && (
            <button
              type="button"
              onClick={onOpenCategoryReview}
              className="text-xs px-3.5 py-1.5 bg-amber-500 hover:bg-amber-600 text-white rounded-xl font-bold transition-colors flex items-center gap-1.5 shadow-2xs"
              title="Review unclassified transactions and manage counterparty category mappings"
            >
              <span>🏷️</span> Category Intelligence
            </button>
          )}

          {/* Export Filtered CSV */}
          <button
            type="button"
            onClick={exportFilteredCSV}
            className="text-xs px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold transition-colors flex items-center gap-1.5 shadow-2xs"
          >
            <span>📥</span> Export Filtered ({filtered.length})
          </button>

          {/* Reset Filters */}
          <button
            type="button"
            onClick={onResetFilters}
            className="text-xs px-3 py-1.5 border border-gray-200 dark:border-slate-700 rounded-xl text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-800 font-semibold"
          >
            Reset Filters
          </button>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-3 p-4 bg-gray-50 dark:bg-slate-800/60 border border-gray-200 dark:border-slate-800 rounded-xl text-xs">
        {/* Search */}
        <div className="sm:col-span-2">
          <label className="block font-semibold text-gray-600 dark:text-gray-400 mb-1">Search Fields (Text, Ref, ₹)</label>
          <input
            type="text"
            placeholder="Search naration, merchant, UTR, ₹ amount..."
            value={externalFilters.search || ''}
            onChange={(e) => {
              onFilterChange('search', e.target.value)
              setPage(1)
            }}
            className="w-full bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-700 rounded-lg px-3 py-2 text-xs focus:ring-2 focus:ring-emerald-500 outline-none text-gray-900 dark:text-white"
          />
        </div>

        {/* Category */}
        <div>
          <label className="block font-semibold text-gray-600 dark:text-gray-400 mb-1">Category</label>
          <select
            value={externalFilters.category || 'All'}
            onChange={(e) => {
              onFilterChange('category', e.target.value)
              setPage(1)
            }}
            className="w-full bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-700 rounded-lg px-2.5 py-2 text-xs focus:ring-2 focus:ring-emerald-500 outline-none text-gray-900 dark:text-white"
          >
            {categories.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>

        {/* Counterparty */}
        <div>
          <label className="block font-semibold text-gray-600 dark:text-gray-400 mb-1">Counterparty</label>
          <select
            value={externalFilters.party || 'All'}
            onChange={(e) => {
              onFilterChange('party', e.target.value)
              setPage(1)
            }}
            className="w-full bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-700 rounded-lg px-2.5 py-2 text-xs focus:ring-2 focus:ring-emerald-500 outline-none text-gray-900 dark:text-white"
          >
            {parties.map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
        </div>

        {/* Flow Type */}
        <div>
          <label className="block font-semibold text-gray-600 dark:text-gray-400 mb-1">Flow Type</label>
          <select
            value={externalFilters.type || 'All'}
            onChange={(e) => {
              onFilterChange('type', e.target.value)
              setPage(1)
            }}
            className="w-full bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-700 rounded-lg px-2.5 py-2 text-xs focus:ring-2 focus:ring-emerald-500 outline-none text-gray-900 dark:text-white"
          >
            <option value="All">All Movements</option>
            <option value="Debit">Debits / Outflows</option>
            <option value="Credit">Credits / Inflows</option>
          </select>
        </div>

        {/* Date Range */}
        <div>
          <label className="block font-semibold text-gray-600 dark:text-gray-400 mb-1">Start Date</label>
          <input
            type="date"
            value={externalFilters.startDate || ''}
            onChange={(e) => {
              onFilterChange('startDate', e.target.value)
              setPage(1)
            }}
            className="w-full bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-700 rounded-lg px-2 py-1.5 text-xs outline-none text-gray-900 dark:text-white"
          />
        </div>

        <div>
          <label className="block font-semibold text-gray-600 dark:text-gray-400 mb-1">End Date</label>
          <input
            type="date"
            value={externalFilters.endDate || ''}
            onChange={(e) => {
              onFilterChange('endDate', e.target.value)
              setPage(1)
            }}
            className="w-full bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-700 rounded-lg px-2 py-1.5 text-xs outline-none text-gray-900 dark:text-white"
          />
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto border border-gray-200 dark:border-slate-800 rounded-xl">
        <table className="w-full text-xs text-left border-collapse">
          <thead>
            <tr className="bg-gray-100/80 dark:bg-slate-800 text-gray-600 dark:text-gray-300 border-b border-gray-200 dark:border-slate-700">
              {colVisible.date && (
                <th
                  className="py-3 px-3.5 font-semibold cursor-pointer select-none whitespace-nowrap"
                  onClick={() => toggleSort('date')}
                >
                  Date <SortIcon sortKey={sortKey} currentKey="date" sortDir={sortDir} />
                </th>
              )}
              {colVisible.description && <th className="py-3 px-3.5 font-semibold">Description / Narration</th>}
              {colVisible.merchant && <th className="py-3 px-3.5 font-semibold">Counterparty</th>}
              {colVisible.mode && <th className="py-3 px-3.5 font-semibold">Rail / Mode</th>}
              {colVisible.reference && <th className="py-3 px-3.5 font-semibold">Ref / UTR</th>}
              {colVisible.category && <th className="py-3 px-3.5 font-semibold">Category</th>}
              {colVisible.debit && (
                <th
                  className="py-3 px-3.5 font-semibold text-right cursor-pointer select-none whitespace-nowrap"
                  onClick={() => toggleSort('debit')}
                >
                  Debit (₹) <SortIcon sortKey={sortKey} currentKey="debit" sortDir={sortDir} />
                </th>
              )}
              {colVisible.credit && (
                <th
                  className="py-3 px-3.5 font-semibold text-right cursor-pointer select-none whitespace-nowrap"
                  onClick={() => toggleSort('credit')}
                >
                  Credit (₹) <SortIcon sortKey={sortKey} currentKey="credit" sortDir={sortDir} />
                </th>
              )}
              {colVisible.balance && (
                <th
                  className="py-3 px-3.5 font-semibold text-right cursor-pointer select-none whitespace-nowrap"
                  onClick={() => toggleSort('balance')}
                >
                  Balance (₹) <SortIcon sortKey={sortKey} currentKey="balance" sortDir={sortDir} />
                </th>
              )}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-slate-800">
            {pageItems.length === 0 ? (
              <tr>
                <td colSpan={Object.values(colVisible).filter(Boolean).length} className="py-12 text-center text-gray-400">
                  No transactions match your active cross-filters.
                </td>
              </tr>
            ) : (
              pageItems.map((t) => (
                <tr
                  key={t.id}
                  onClick={() => setSelectedTxn(t)}
                  className="hover:bg-slate-50 dark:hover:bg-slate-800/60 transition-colors cursor-pointer"
                >
                  {colVisible.date && (
                    <td className="py-3 px-3.5 text-gray-500 dark:text-gray-400 whitespace-nowrap font-mono text-[11px]">
                      {fmtDate(t.date)}
                    </td>
                  )}
                  {colVisible.description && (
                    <td className="py-3 px-3.5 max-w-xs">
                      <p className="font-semibold text-gray-900 dark:text-white truncate" title={t.description}>
                        {t.clean_description || t.description}
                      </p>
                      {t.is_recurring && (
                        <span className="inline-block mt-0.5 text-[10px] text-purple-700 bg-purple-50 dark:bg-purple-950/60 font-bold px-1.5 py-0.2 rounded border border-purple-200">
                          ↻ Recurring
                        </span>
                      )}
                    </td>
                  )}
                  {colVisible.merchant && (
                    <td className="py-3 px-3.5 text-gray-600 dark:text-gray-300 truncate max-w-[140px]">
                      {t.merchant || '—'}
                    </td>
                  )}
                  {colVisible.mode && (
                    <td className="py-3 px-3.5">
                      <span className={`inline-block font-mono text-[10px] font-bold px-2 py-0.5 rounded ${
                        t.payment_mode === 'RTGS' ? 'bg-indigo-100 text-indigo-800 dark:bg-indigo-950/70 dark:text-indigo-300' :
                        t.payment_mode === 'NEFT' ? 'bg-blue-100 text-blue-800 dark:bg-blue-950/70 dark:text-blue-300' :
                        t.payment_mode === 'IMPS' ? 'bg-teal-100 text-teal-800 dark:bg-teal-950/70 dark:text-teal-300' :
                        t.payment_mode === 'UPI' ? 'bg-cyan-100 text-cyan-800 dark:bg-cyan-950/70 dark:text-cyan-300' :
                        t.payment_mode === 'IFT' ? 'bg-purple-100 text-purple-800 dark:bg-purple-950/70 dark:text-purple-300' :
                        t.payment_mode === 'CHEQUE' ? 'bg-amber-100 text-amber-800 dark:bg-amber-950/70 dark:text-amber-300' :
                        'bg-gray-100 text-gray-700 dark:bg-slate-800 dark:text-gray-300'
                      }`}>
                        {t.payment_mode || 'OTHER'}
                      </span>
                    </td>
                  )}
                  {colVisible.reference && (
                    <td className="py-3 px-3.5 font-mono text-gray-500 dark:text-gray-400 text-[11px] whitespace-nowrap">
                      {t.reference_no || '—'}
                    </td>
                  )}
                  {colVisible.category && (
                    <td className="py-3 px-3.5">
                      <span className="inline-block bg-gray-100 dark:bg-slate-800 text-gray-700 dark:text-gray-300 text-[11px] font-semibold px-2 py-0.5 rounded-full">
                        {t.category}
                      </span>
                    </td>
                  )}
                  {colVisible.debit && (
                    <td className="py-3 px-3.5 text-right font-black text-rose-600 dark:text-rose-400 whitespace-nowrap">
                      {t.amount < 0 ? fmtCurrency(t.amount) : '—'}
                    </td>
                  )}
                  {colVisible.credit && (
                    <td className="py-3 px-3.5 text-right font-black text-emerald-600 dark:text-emerald-400 whitespace-nowrap">
                      {t.amount > 0 ? fmtCurrency(t.amount) : '—'}
                    </td>
                  )}
                  {colVisible.balance && (
                    <td className="py-3 px-3.5 text-right font-medium text-gray-800 dark:text-gray-200 whitespace-nowrap">
                      {t.balance !== null && t.balance !== undefined ? fmtCurrency(t.balance) : '—'}
                    </td>
                  )}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination & Page Size */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-gray-500 dark:text-gray-400">
        <div className="flex items-center gap-3">
          <span>
            Page <strong className="text-gray-800 dark:text-white">{page}</strong> of <strong className="text-gray-800 dark:text-white">{totalPages}</strong> ({filtered.length} matching rows)
          </span>
          <div className="flex items-center gap-1.5">
            <span>Show:</span>
            <select
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value))
                setPage(1)
              }}
              className="bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded px-2 py-1 text-xs"
            >
              <option value={10}>10</option>
              <option value={25}>25</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
          </div>
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1.5 border border-gray-200 dark:border-slate-700 rounded-lg disabled:opacity-40 hover:bg-gray-50 dark:hover:bg-slate-800 font-semibold"
          >
            ← Prev
          </button>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-3 py-1.5 border border-gray-200 dark:border-slate-700 rounded-lg disabled:opacity-40 hover:bg-gray-50 dark:hover:bg-slate-800 font-semibold"
          >
            Next →
          </button>
        </div>
      </div>

      {/* Transaction Detail Slide-Out / Modal */}
      {selectedTxn && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4 animate-scaleUp">
            <div className="flex items-center justify-between border-b border-gray-100 dark:border-slate-800 pb-3">
              <h3 className="text-base font-bold text-gray-900 dark:text-white flex items-center gap-2">
                <span>🔍</span> Transaction Audit Detail
              </h3>
              <button
                onClick={() => setSelectedTxn(null)}
                className="text-gray-400 hover:text-gray-600 text-lg font-bold"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="bg-gray-50 dark:bg-slate-800 p-3 rounded-xl space-y-1">
                <span className="text-[10px] uppercase font-bold text-gray-400">Raw Bank Statement Narration</span>
                <p className="font-mono text-gray-800 dark:text-gray-200 break-words">{selectedTxn.description}</p>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 bg-gray-50 dark:bg-slate-800 rounded-xl">
                  <span className="text-[10px] uppercase font-bold text-gray-400">Transaction Date</span>
                  <p className="font-bold text-gray-900 dark:text-white mt-0.5">{fmtDate(selectedTxn.date)}</p>
                </div>
                <div className="p-3 bg-gray-50 dark:bg-slate-800 rounded-xl">
                  <span className="text-[10px] uppercase font-bold text-gray-400">Flow Amount</span>
                  <p className={`font-black mt-0.5 text-sm ${selectedTxn.amount > 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                    {selectedTxn.amount > 0 ? '+' : '-'}{fmtCurrency(selectedTxn.amount)}
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 bg-gray-50 dark:bg-slate-800 rounded-xl">
                  <span className="text-[10px] uppercase font-bold text-gray-400">Reference / UTR</span>
                  <p className="font-mono font-bold text-gray-800 dark:text-gray-200 mt-0.5">{selectedTxn.reference_no || 'Not Available'}</p>
                </div>
                <div className="p-3 bg-gray-50 dark:bg-slate-800 rounded-xl">
                  <span className="text-[10px] uppercase font-bold text-gray-400">Statement Running Balance</span>
                  <p className="font-bold text-gray-900 dark:text-white mt-0.5">{fmtCurrency(selectedTxn.balance)}</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 bg-gray-50 dark:bg-slate-800 rounded-xl">
                  <span className="text-[10px] uppercase font-bold text-gray-400">Identified Counterparty</span>
                  <p className="font-bold text-gray-900 dark:text-white mt-0.5">{selectedTxn.merchant || selectedTxn.clean_description || '—'}</p>
                </div>
                <div className="p-3 bg-gray-50 dark:bg-slate-800 rounded-xl">
                  <span className="text-[10px] uppercase font-bold text-gray-400">Category</span>
                  <p className="font-bold text-gray-900 dark:text-white mt-0.5">{selectedTxn.category}</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 bg-gray-50 dark:bg-slate-800 rounded-xl">
                  <span className="text-[10px] uppercase font-bold text-gray-400">Payment Rail</span>
                  <p className="font-bold text-gray-900 dark:text-white mt-0.5">{selectedTxn.payment_mode || 'OTHER'}</p>
                </div>
                <div className="p-3 bg-gray-50 dark:bg-slate-800 rounded-xl">
                  <span className="text-[10px] uppercase font-bold text-gray-400">Classification Confidence</span>
                  <p className="font-bold text-gray-900 dark:text-white mt-0.5">
                    <span className={`inline-block px-2 py-0.5 rounded text-[11px] ${
                      selectedTxn.confidence === 'High' ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300' : 'bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300'
                    }`}>
                      {selectedTxn.confidence || 'Standard'} ({selectedTxn.classification_source || 'Rules'})
                    </span>
                  </p>
                </div>
              </div>
            </div>

            <div className="pt-3 border-t border-gray-100 dark:border-slate-800 flex justify-between items-center">
              {onOpenCategoryReview && (
                <button
                  type="button"
                  onClick={() => {
                    setSelectedTxn(null)
                    onOpenCategoryReview()
                  }}
                  className="px-3 py-1.5 bg-amber-500 hover:bg-amber-600 text-white rounded-xl text-xs font-bold transition-colors"
                >
                  🏷️ Reclassify / Map Category
                </button>
              )}
              <button
                type="button"
                onClick={() => setSelectedTxn(null)}
                className="px-4 py-2 bg-gray-900 text-white dark:bg-white dark:text-gray-900 rounded-xl text-xs font-bold"
              >
                Close Inspector
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
