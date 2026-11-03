import { useState, useMemo } from 'react'

const PAGE_SIZE = 25

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
  if (sortKey !== currentKey) return <span className="text-gray-300 ml-1">↕</span>
  return <span className="text-emerald-600 ml-1">{sortDir === 'asc' ? '↑' : '↓'}</span>
}

export default function TransactionTable({ transactions }) {
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('All')
  const [type, setType] = useState('All') // 'All' | 'Debit' | 'Credit'
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [minAmount, setMinAmount] = useState('')
  const [maxAmount, setMaxAmount] = useState('')
  const [sortKey, setSortKey] = useState('date')
  const [sortDir, setSortDir] = useState('desc')
  const [page, setPage] = useState(1)

  const categories = useMemo(() => {
    const cats = Array.from(new Set(transactions.map((t) => t.category))).filter(Boolean).sort()
    return ['All', ...cats]
  }, [transactions])

  const filtered = useMemo(() => {
    const q = search.toLowerCase().trim()
    const minA = minAmount ? parseFloat(minAmount) : null
    const maxA = maxAmount ? parseFloat(maxAmount) : null

    return transactions
      .filter((t) => {
        // Category
        if (category !== 'All' && t.category !== category) return false
        // Type
        if (type === 'Debit' && t.amount >= 0) return false
        if (type === 'Credit' && t.amount <= 0) return false
        // Dates
        const tDate = typeof t.date === 'string' ? t.date.slice(0, 10) : new Date(t.date).toISOString().slice(0, 10)
        if (startDate && tDate < startDate) return false
        if (endDate && tDate > endDate) return false
        // Amount range
        const absAmt = Math.abs(t.amount)
        if (minA !== null && absAmt < minA) return false
        if (maxA !== null && absAmt > maxA) return false
        // Search
        if (q) {
          const desc = (t.description || '').toLowerCase()
          const cleanDesc = (t.clean_description || '').toLowerCase()
          const merch = (t.merchant || '').toLowerCase()
          const ref = (t.reference_no || '').toLowerCase()
          if (!desc.includes(q) && !cleanDesc.includes(q) && !merch.includes(q) && !ref.includes(q)) {
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
  }, [transactions, search, category, type, startDate, endDate, minAmount, maxAmount, sortKey, sortDir])

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const pageItems = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  function toggleSort(key) {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir('desc')
    }
    setPage(1)
  }

  function resetFilters() {
    setSearch('')
    setCategory('All')
    setType('All')
    setStartDate('')
    setEndDate('')
    setMinAmount('')
    setMaxAmount('')
    setPage(1)
  }

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6" id="transactions-section">
      {/* Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-5">
        <div>
          <h2 className="text-lg font-bold text-gray-900">
            Statement Transactions
          </h2>
          <p className="text-xs text-gray-500 mt-0.5">
            Showing {filtered.length} of {transactions.length} verified transactions with complete debit, credit & balance ledger.
          </p>
        </div>
        <button
          onClick={resetFilters}
          className="text-xs px-3 py-1.5 border border-gray-200 rounded-lg text-gray-600 hover:bg-gray-50 transition-colors font-medium self-start sm:self-auto"
        >
          Reset Filters
        </button>
      </div>

      {/* Filter toolbar */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 p-4 bg-gray-50 border border-gray-200 rounded-xl mb-5 text-xs">
        <div>
          <label className="block font-semibold text-gray-600 mb-1">Search Description / UTR</label>
          <input
            type="text"
            placeholder="Search narration, ref..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1) }}
            className="w-full bg-white border border-gray-200 rounded-lg px-3 py-2 text-xs focus:ring-2 focus:ring-emerald-500 outline-none"
          />
        </div>

        <div>
          <label className="block font-semibold text-gray-600 mb-1">Category</label>
          <select
            value={category}
            onChange={(e) => { setCategory(e.target.value); setPage(1) }}
            className="w-full bg-white border border-gray-200 rounded-lg px-3 py-2 text-xs focus:ring-2 focus:ring-emerald-500 outline-none"
          >
            {categories.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block font-semibold text-gray-600 mb-1">Type</label>
          <select
            value={type}
            onChange={(e) => { setType(e.target.value); setPage(1) }}
            className="w-full bg-white border border-gray-200 rounded-lg px-3 py-2 text-xs focus:ring-2 focus:ring-emerald-500 outline-none"
          >
            <option value="All">All Transactions</option>
            <option value="Debit">Debits Only</option>
            <option value="Credit">Credits Only</option>
          </select>
        </div>

        <div>
          <label className="block font-semibold text-gray-600 mb-1">Date Range</label>
          <div className="flex gap-1.5">
            <input
              type="date"
              value={startDate}
              onChange={(e) => { setStartDate(e.target.value); setPage(1) }}
              className="w-1/2 bg-white border border-gray-200 rounded-lg px-2 py-1.5 text-[11px] outline-none"
            />
            <input
              type="date"
              value={endDate}
              onChange={(e) => { setEndDate(e.target.value); setPage(1) }}
              className="w-1/2 bg-white border border-gray-200 rounded-lg px-2 py-1.5 text-[11px] outline-none"
            />
          </div>
        </div>

        <div>
          <label className="block font-semibold text-gray-600 mb-1">Amount Range (₹)</label>
          <div className="flex gap-1.5">
            <input
              type="number"
              placeholder="Min"
              value={minAmount}
              onChange={(e) => { setMinAmount(e.target.value); setPage(1) }}
              className="w-1/2 bg-white border border-gray-200 rounded-lg px-2 py-1.5 text-xs outline-none"
            />
            <input
              type="number"
              placeholder="Max"
              value={maxAmount}
              onChange={(e) => { setMaxAmount(e.target.value); setPage(1) }}
              className="w-1/2 bg-white border border-gray-200 rounded-lg px-2 py-1.5 text-xs outline-none"
            />
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto border border-gray-200 rounded-xl">
        <table className="w-full text-xs text-left border-collapse">
          <thead>
            <tr className="bg-gray-100/80 text-gray-600 border-b border-gray-200">
              <th
                className="py-3 px-3.5 font-semibold cursor-pointer select-none whitespace-nowrap"
                onClick={() => toggleSort('date')}
              >
                Date <SortIcon sortKey={sortKey} currentKey="date" sortDir={sortDir} />
              </th>
              <th className="py-3 px-3.5 font-semibold">Description</th>
              <th className="py-3 px-3.5 font-semibold">Ref / UTR</th>
              <th className="py-3 px-3.5 font-semibold">Category</th>
              <th
                className="py-3 px-3.5 font-semibold text-right cursor-pointer select-none whitespace-nowrap"
                onClick={() => toggleSort('debit')}
              >
                Debit (₹) <SortIcon sortKey={sortKey} currentKey="debit" sortDir={sortDir} />
              </th>
              <th
                className="py-3 px-3.5 font-semibold text-right cursor-pointer select-none whitespace-nowrap"
                onClick={() => toggleSort('credit')}
              >
                Credit (₹) <SortIcon sortKey={sortKey} currentKey="credit" sortDir={sortDir} />
              </th>
              <th
                className="py-3 px-3.5 font-semibold text-right cursor-pointer select-none whitespace-nowrap"
                onClick={() => toggleSort('balance')}
              >
                Balance (₹) <SortIcon sortKey={sortKey} currentKey="balance" sortDir={sortDir} />
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {pageItems.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-10 text-center text-gray-400">
                  No transactions match your active filters.
                </td>
              </tr>
            ) : (
              pageItems.map((t) => (
                <tr key={t.id} className="hover:bg-slate-50 transition-colors">
                  <td className="py-3 px-3.5 text-gray-500 whitespace-nowrap">{fmtDate(t.date)}</td>
                  <td className="py-3 px-3.5 max-w-sm">
                    <p className="font-semibold text-gray-900 truncate" title={t.clean_description || t.description}>
                      {t.clean_description || t.description}
                    </p>
                    {t.is_recurring && (
                      <span className="inline-block mt-0.5 text-[10px] text-purple-700 bg-purple-50 font-bold px-1.5 py-0.5 rounded border border-purple-200">
                        ↻ Recurring ({t.recurrence_tag || 'SUB'})
                      </span>
                    )}
                  </td>
                  <td className="py-3 px-3.5 font-mono text-gray-500 text-[11px] whitespace-nowrap">
                    {t.reference_no || '—'}
                  </td>
                  <td className="py-3 px-3.5">
                    <span className="inline-block bg-gray-100 text-gray-700 text-[11px] font-semibold px-2 py-0.5 rounded-full">
                      {t.category}
                    </span>
                  </td>
                  <td className="py-3 px-3.5 text-right font-semibold text-red-600 whitespace-nowrap">
                    {t.amount < 0 ? fmtCurrency(t.amount) : '—'}
                  </td>
                  <td className="py-3 px-3.5 text-right font-semibold text-emerald-600 whitespace-nowrap">
                    {t.amount > 0 ? fmtCurrency(t.amount) : '—'}
                  </td>
                  <td className="py-3 px-3.5 text-right font-medium text-gray-700 whitespace-nowrap">
                    {t.balance !== null && t.balance !== undefined ? fmtCurrency(t.balance) : '—'}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-between text-xs text-gray-500">
          <span>
            Page <strong className="text-gray-800">{page}</strong> of <strong className="text-gray-800">{totalPages}</strong> ({filtered.length} rows)
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-3 py-1.5 border border-gray-200 rounded-lg disabled:opacity-40 hover:bg-gray-50 font-medium"
            >
              ← Prev
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="px-3 py-1.5 border border-gray-200 rounded-lg disabled:opacity-40 hover:bg-gray-50 font-medium"
            >
              Next →
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
