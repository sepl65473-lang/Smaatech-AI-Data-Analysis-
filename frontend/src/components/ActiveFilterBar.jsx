import React from 'react'

function fmt(n) {
  if (n === null || n === undefined) return '—'
  return '₹' + Math.abs(n).toLocaleString('en-IN', { maximumFractionDigits: 0 })
}

export default function ActiveFilterBar({
  filters,
  onRemoveFilter,
  onResetFilters,
  totalCount,
  filteredCount,
  filteredIncome,
  filteredSpend,
  filteredNet,
}) {
  const activeChips = []

  if (filters.category && filters.category !== 'All') {
    activeChips.push({
      key: 'category',
      label: `Category: ${filters.category}`,
      onRemove: () => onRemoveFilter('category'),
    })
  }

  if (filters.party) {
    activeChips.push({
      key: 'party',
      label: `Party: ${filters.party}`,
      onRemove: () => onRemoveFilter('party'),
    })
  }

  if (filters.type && filters.type !== 'All') {
    activeChips.push({
      key: 'type',
      label: `Type: ${filters.type}s Only`,
      onRemove: () => onRemoveFilter('type'),
    })
  }

  if (filters.date) {
    activeChips.push({
      key: 'date',
      label: `Date: ${filters.date}`,
      onRemove: () => onRemoveFilter('date'),
    })
  }

  if (filters.search) {
    activeChips.push({
      key: 'search',
      label: `Search: "${filters.search}"`,
      onRemove: () => onRemoveFilter('search'),
    })
  }

  if (filters.intelligenceTag) {
    const tagLabels = {
      missing_ref: 'Missing Reference No.',
      weekend: 'Weekend Activity',
      largest: 'Large Transactions (≥₹1L)',
      unusual: 'Unusual / Round Amount',
      repeated: 'Repeated Counterparty',
      uncategorized: 'Uncategorized / Other',
    }
    activeChips.push({
      key: 'intelligenceTag',
      label: `Flag: ${tagLabels[filters.intelligenceTag] || filters.intelligenceTag}`,
      onRemove: () => onRemoveFilter('intelligenceTag'),
    })
  }

  if (filters.startDate || filters.endDate) {
    activeChips.push({
      key: 'dateRange',
      label: `Range: ${filters.startDate || 'Start'} to ${filters.endDate || 'End'}`,
      onRemove: () => {
        onRemoveFilter('startDate')
        onRemoveFilter('endDate')
      },
    })
  }

  if (filters.minAmount || filters.maxAmount) {
    activeChips.push({
      key: 'amountRange',
      label: `Amount: ₹${filters.minAmount || 0} – ₹${filters.maxAmount || '∞'}`,
      onRemove: () => {
        onRemoveFilter('minAmount')
        onRemoveFilter('maxAmount')
      },
    })
  }

  if (activeChips.length === 0) return null

  return (
    <div className="bg-emerald-50/90 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800/60 rounded-2xl p-4 shadow-xs transition-all animate-fadeIn">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-bold text-emerald-900 dark:text-emerald-300 flex items-center gap-1.5 uppercase tracking-wider">
            <span>⚡</span> Active Cross-Filters ({activeChips.length}):
          </span>

          {activeChips.map((chip) => (
            <span
              key={chip.key}
              className="inline-flex items-center gap-1.5 px-3 py-1 bg-white dark:bg-slate-800 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700/60 text-xs font-semibold rounded-full shadow-2xs hover:bg-emerald-50 dark:hover:bg-slate-700 transition-colors"
            >
              <span>{chip.label}</span>
              <button
                type="button"
                onClick={chip.onRemove}
                title="Remove filter"
                className="text-emerald-600 dark:text-emerald-400 hover:text-red-600 dark:hover:text-red-400 text-sm font-black leading-none ml-0.5 focus:outline-hidden"
              >
                ×
              </button>
            </span>
          ))}

          <button
            type="button"
            onClick={onResetFilters}
            className="text-xs px-2.5 py-1 text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 font-bold underline transition-colors"
          >
            Reset All
          </button>
        </div>

        {/* Filtered dataset telemetry */}
        <div className="text-xs text-emerald-950 dark:text-emerald-200 font-medium whitespace-nowrap bg-emerald-100/70 dark:bg-emerald-900/40 px-3 py-1 rounded-xl border border-emerald-300/60 dark:border-emerald-700/40">
          Showing <strong>{filteredCount}</strong> of <strong>{totalCount}</strong> txns · In: <span className="text-emerald-700 dark:text-emerald-400 font-bold">{fmt(filteredIncome)}</span> · Out: <span className="text-rose-700 dark:text-rose-400 font-bold">{fmt(filteredSpend)}</span> · Net: <span className="font-bold">{fmt(filteredNet)}</span>
        </div>
      </div>
    </div>
  )
}
