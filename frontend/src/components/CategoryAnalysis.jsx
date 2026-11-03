import React, { useState } from 'react'
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'

const CATEGORY_COLORS = {
  Food:          '#f97316',
  Travel:        '#3b82f6',
  Shopping:      '#8b5cf6',
  Bills:         '#06b6d4',
  EMI:           '#ef4444',
  Subscriptions: '#ec4899',
  Salary:        '#22c55e',
  Rent:          '#f59e0b',
  Investments:   '#10b981',
  Healthcare:    '#14b8a6',
  Education:     '#6366f1',
  Income:        '#84cc16',
  Other:         '#64748b',
}

function colorFor(cat) {
  return CATEGORY_COLORS[cat] ?? '#64748b'
}

function fmtInr(n) {
  if (n === null || n === undefined) return '—'
  return '₹' + Math.abs(n).toLocaleString('en-IN', { maximumFractionDigits: 0 })
}

export default function CategoryAnalysis({
  topCategories = [],
  incomeCategories = [],
  _totalSpend = 0,
  _totalIncome = 0,
  transactions = [],
  selectedCategory = null,
  onSelectCategory,
}) {
  const [activeTab, setActiveTab] = useState('expense') // 'expense' | 'income'

  // Pre-calculate count, avg, largest for each category from raw transactions
  const catStats = {}
  transactions.forEach((t) => {
    const cat = t.category || 'Other'
    if (!catStats[cat]) {
      catStats[cat] = { count: 0, total: 0, largest: 0 }
    }
    const amt = Math.abs(t.amount)
    catStats[cat].count += 1
    catStats[cat].total += amt
    if (amt > catStats[cat].largest) {
      catStats[cat].largest = amt
    }
  })

  const expenseData = topCategories.map((c) => ({
    name: c.category,
    value: c.amount,
    percentage: c.percentage,
    count: catStats[c.category]?.count || 0,
    avg: catStats[c.category]?.count ? Math.round(c.amount / catStats[c.category].count) : 0,
    largest: catStats[c.category]?.largest || 0,
  }))

  const incomeData = incomeCategories.map((c) => ({
    name: c.category,
    value: c.amount,
    percentage: c.percentage,
    count: catStats[c.category]?.count || 0,
    avg: catStats[c.category]?.count ? Math.round(c.amount / catStats[c.category].count) : 0,
    largest: catStats[c.category]?.largest || 0,
  }))

  const activeData = activeTab === 'expense' ? expenseData : incomeData

  return (
    <section className="bg-white dark:bg-slate-900 rounded-2xl border border-gray-200 dark:border-slate-800 shadow-xs p-6 space-y-6" id="category-analysis">
      {/* Title & Category Tab Switcher */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-gray-100 dark:border-slate-800 pb-4">
        <div>
          <h2 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <span>🏷️</span> Category Analysis & Contribution
          </h2>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
            Spending & revenue distributions across categories. Click any category row or chart slice to cross-filter.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {selectedCategory && (
            <span className="text-xs font-bold text-emerald-700 dark:text-emerald-300 bg-emerald-100 dark:bg-emerald-950/60 px-2.5 py-1 rounded-full border border-emerald-300">
              Active: {selectedCategory}
            </span>
          )}

          <div className="flex bg-gray-100 dark:bg-slate-800 p-1 rounded-xl text-xs font-semibold">
            <button
              onClick={() => setActiveTab('expense')}
              className={`px-3 py-1.5 rounded-lg transition-all ${
                activeTab === 'expense'
                  ? 'bg-white dark:bg-slate-700 text-gray-900 dark:text-white shadow-2xs'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
              }`}
            >
              Expense Categories ({expenseData.length})
            </button>
            <button
              onClick={() => setActiveTab('income')}
              className={`px-3 py-1.5 rounded-lg transition-all ${
                activeTab === 'income'
                  ? 'bg-white dark:bg-slate-700 text-gray-900 dark:text-white shadow-2xs'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
              }`}
            >
              Income Sources ({incomeData.length})
            </button>
          </div>
        </div>
      </div>

      {/* Main Content Grid: Chart + Ranked Table */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
        {/* Donut / Pie Chart (5 Cols) */}
        <div className="lg:col-span-5 h-64 w-full flex items-center justify-center">
          {activeData.length === 0 ? (
            <p className="text-xs text-gray-400">No category data recorded for this view.</p>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={activeData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={95}
                  paddingAngle={2}
                  cursor="pointer"
                  onClick={(entry) => onSelectCategory && onSelectCategory(entry.name)}
                >
                  {activeData.map((entry) => (
                    <Cell
                      key={entry.name}
                      fill={colorFor(entry.name)}
                      stroke={selectedCategory === entry.name ? '#000' : 'none'}
                      strokeWidth={selectedCategory === entry.name ? 2 : 0}
                    />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(val, name, item) => [
                    `${fmtInr(val)} (${item?.payload?.percentage?.toFixed(1) || 0}%)`,
                    name,
                  ]}
                  contentStyle={{ borderRadius: '12px', fontSize: '12px' }}
                />
                <Legend iconType="circle" wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Category Contribution Table (7 Cols) */}
        <div className="lg:col-span-7 overflow-x-auto">
          <table className="w-full text-xs text-left border-collapse">
            <thead>
              <tr className="border-b border-gray-200 dark:border-slate-800 text-gray-500 dark:text-gray-400 text-[11px] font-bold uppercase">
                <th className="py-2.5 px-3">Category</th>
                <th className="py-2.5 px-3 text-right">Amount</th>
                <th className="py-2.5 px-3 text-right">Share</th>
                <th className="py-2.5 px-3 text-right">Count</th>
                <th className="py-2.5 px-3 text-right">Avg Size</th>
                <th className="py-2.5 px-3 text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-slate-800">
              {activeData.map((c) => {
                const isSelected = selectedCategory === c.name
                return (
                  <tr
                    key={c.name}
                    onClick={() => onSelectCategory && onSelectCategory(c.name)}
                    className={`cursor-pointer transition-colors ${
                      isSelected
                        ? 'bg-emerald-50 dark:bg-emerald-950/40 font-bold'
                        : 'hover:bg-gray-50 dark:hover:bg-slate-800/60'
                    }`}
                  >
                    <td className="py-2.5 px-3 flex items-center gap-2 whitespace-nowrap">
                      <span
                        className="w-2.5 h-2.5 rounded-full shrink-0"
                        style={{ backgroundColor: colorFor(c.name) }}
                      />
                      <span className="font-semibold text-gray-900 dark:text-white">{c.name}</span>
                    </td>
                    <td className="py-2.5 px-3 text-right font-bold text-gray-900 dark:text-white whitespace-nowrap">
                      {fmtInr(c.value)}
                    </td>
                    <td className="py-2.5 px-3 text-right text-gray-500 dark:text-gray-400 whitespace-nowrap">
                      <div className="flex items-center justify-end gap-1.5">
                        <span>{c.percentage?.toFixed(1)}%</span>
                        <div className="w-12 bg-gray-200 dark:bg-slate-700 h-1.5 rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full"
                            style={{
                              width: `${Math.min(c.percentage || 0, 100)}%`,
                              backgroundColor: colorFor(c.name),
                            }}
                          />
                        </div>
                      </div>
                    </td>
                    <td className="py-2.5 px-3 text-right text-gray-600 dark:text-gray-300 whitespace-nowrap">
                      {c.count} txns
                    </td>
                    <td className="py-2.5 px-3 text-right text-gray-600 dark:text-gray-300 whitespace-nowrap">
                      {fmtInr(c.avg)}
                    </td>
                    <td className="py-2.5 px-3 text-center">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation()
                          if (onSelectCategory) {
                            onSelectCategory(isSelected ? null : c.name)
                          }
                        }}
                        className={`text-[11px] px-2 py-0.5 rounded font-semibold transition-all ${
                          isSelected
                            ? 'bg-emerald-600 text-white'
                            : 'bg-gray-100 dark:bg-slate-800 text-gray-600 dark:text-gray-400 hover:bg-emerald-100 hover:text-emerald-800'
                        }`}
                      >
                        {isSelected ? 'Clear' : 'Filter'}
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}
