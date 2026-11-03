import React, { useState } from 'react'
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Cell,
  Legend,
  PieChart,
  Pie,
} from 'recharts'

function fmtInr(n) {
  if (n === null || n === undefined) return '—'
  return '₹' + Math.abs(n).toLocaleString('en-IN', { maximumFractionDigits: 0 })
}

export default function IncomeExpenseAnalysis({ metrics, onSelectDate }) {
  const [activeTab, setActiveTab] = useState('daily') // 'daily' | 'compare' | 'balance' | 'weekly'

  const dailyData = (metrics?.daily_cash_flow || []).map((d) => ({
    date: d.date.slice(5), // MM-DD
    fullDate: d.date,
    net: d.net,
    cumulative: d.cumulative,
    credits: d.credits,
    debits: d.debits,
    balance: d.balance !== null && d.balance !== undefined ? d.balance : null,
    count: d.count,
  }))

  const weeklyData = (metrics?.weekly_cash_flow || []).map((w) => ({
    week: w.week_start.slice(5),
    fullWeek: w.week_start,
    credits: w.credits,
    debits: w.debits,
    net: w.net,
    count: w.count,
  }))

  // Highs and distribution
  const peakIncomeDay = dailyData.reduce(
    (max, d) => (d.credits > (max?.credits || 0) ? d : max),
    null
  )
  const peakExpenseDay = dailyData.reduce(
    (max, d) => (d.debits > (max?.debits || 0) ? d : max),
    null
  )

  const distributionData = [
    { name: 'Income (Credits)', value: metrics?.total_income || 0, color: '#16a34a' },
    { name: 'Expenses (Debits)', value: metrics?.total_spend || 0, color: '#ef4444' },
  ]

  const totalVolume = (metrics?.total_income || 0) + (metrics?.total_spend || 0)
  const incomePct = totalVolume > 0 ? (((metrics?.total_income || 0) / totalVolume) * 100).toFixed(1) : 0
  const expensePct = totalVolume > 0 ? (((metrics?.total_spend || 0) / totalVolume) * 100).toFixed(1) : 0

  if (!dailyData.length) return null

  return (
    <section className="bg-white dark:bg-slate-900 rounded-2xl border border-gray-200 dark:border-slate-800 shadow-xs p-6 space-y-6" id="income-expense-analysis">
      {/* Header & Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-gray-100 dark:border-slate-800 pb-4">
        <div>
          <h2 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <span>📊</span> Income and Expense Analytics
          </h2>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
            Cross-sectional analysis of liquidity, timing patterns, and ledger trajectory. Click any date to cross-filter.
          </p>
        </div>

        {/* View Switcher Tabs */}
        <div className="flex bg-gray-100 dark:bg-slate-800 p-1 rounded-xl text-xs font-semibold">
          {[
            { id: 'daily', label: 'Daily Net Flow' },
            { id: 'compare', label: 'Income vs Expense' },
            { id: 'balance', label: 'Account Balance' },
            { id: 'weekly', label: 'Weekly Aggregates' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-3 py-1.5 rounded-lg transition-all ${
                activeTab === tab.id
                  ? 'bg-white dark:bg-slate-700 text-gray-900 dark:text-white shadow-2xs'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Main Chart Section */}
      <div className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          {activeTab === 'daily' ? (
            <BarChart
              data={dailyData}
              margin={{ top: 12, right: 12, left: -10, bottom: 0 }}
              onClick={(e) => {
                if (e?.activePayload?.[0]?.payload?.fullDate && onSelectDate) {
                  onSelectDate(e.activePayload[0].payload.fullDate)
                }
              }}
            >
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" opacity={0.6} />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `₹${Math.round(v / 1000)}k`} />
              <Tooltip
                formatter={(value, name) => [
                  (value < 0 ? '-' : '+') + fmtInr(value),
                  name === 'net' ? 'Net Cash Movement' : name,
                ]}
                labelFormatter={(l, p) => `Date: ${p?.[0]?.payload?.fullDate || l} (Click to Filter)`}
                contentStyle={{ borderRadius: '12px', fontSize: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
              />
              <Bar dataKey="net" radius={[3, 3, 0, 0]} cursor="pointer">
                {dailyData.map((entry, index) => (
                  <Cell key={index} fill={entry.net >= 0 ? '#16a34a' : '#ef4444'} />
                ))}
              </Bar>
            </BarChart>
          ) : activeTab === 'compare' ? (
            <BarChart
              data={dailyData}
              margin={{ top: 12, right: 12, left: -10, bottom: 0 }}
              onClick={(e) => {
                if (e?.activePayload?.[0]?.payload?.fullDate && onSelectDate) {
                  onSelectDate(e.activePayload[0].payload.fullDate)
                }
              }}
            >
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" opacity={0.6} />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `₹${Math.round(v / 1000)}k`} />
              <Tooltip
                formatter={(value, name) => [
                  fmtInr(value),
                  name === 'credits' ? 'Income (Credits)' : 'Spend (Debits)',
                ]}
                labelFormatter={(l, p) => `Date: ${p?.[0]?.payload?.fullDate || l}`}
                contentStyle={{ borderRadius: '12px', fontSize: '12px' }}
              />
              <Legend wrapperStyle={{ fontSize: '12px' }} />
              <Bar dataKey="credits" fill="#16a34a" name="Income (Credits)" radius={[3, 3, 0, 0]} cursor="pointer" />
              <Bar dataKey="debits" fill="#ef4444" name="Expenses (Debits)" radius={[3, 3, 0, 0]} cursor="pointer" />
            </BarChart>
          ) : activeTab === 'balance' ? (
            <LineChart
              data={dailyData.filter((d) => d.balance !== null)}
              margin={{ top: 12, right: 12, left: 10, bottom: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" opacity={0.6} />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `₹${Math.round(v / 1000)}k`} domain={['auto', 'auto']} />
              <Tooltip
                formatter={(value) => [fmtInr(value), 'Running Account Balance']}
                labelFormatter={(l, p) => `Date: ${p?.[0]?.payload?.fullDate || l}`}
                contentStyle={{ borderRadius: '12px', fontSize: '12px' }}
              />
              <Line
                type="monotone"
                dataKey="balance"
                stroke="#2563eb"
                strokeWidth={3}
                dot={{ r: 3, fill: '#2563eb' }}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          ) : (
            <BarChart data={weeklyData} margin={{ top: 12, right: 12, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" opacity={0.6} />
              <XAxis dataKey="week" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `₹${Math.round(v / 1000)}k`} />
              <Tooltip
                formatter={(value, name) => [
                  fmtInr(value),
                  name === 'credits' ? 'Credits' : name === 'debits' ? 'Debits' : 'Net',
                ]}
                labelFormatter={(l, p) => `Week Starting: ${p?.[0]?.payload?.fullWeek || l}`}
                contentStyle={{ borderRadius: '12px', fontSize: '12px' }}
              />
              <Legend wrapperStyle={{ fontSize: '12px' }} />
              <Bar dataKey="credits" fill="#16a34a" name="Credits" radius={[3, 3, 0, 0]} />
              <Bar dataKey="debits" fill="#ef4444" name="Debits" radius={[3, 3, 0, 0]} />
            </BarChart>
          )}
        </ResponsiveContainer>
      </div>

      {/* Analytics Sub-Grid: Peak Days & Debit/Credit Volume Distribution */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
        {/* Peak Income Day Card */}
        <div
          onClick={() => peakIncomeDay && onSelectDate && onSelectDate(peakIncomeDay.fullDate)}
          className="bg-emerald-50/70 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800/60 rounded-xl p-4 cursor-pointer hover:border-emerald-500 transition-all"
        >
          <div className="flex items-center justify-between text-xs font-semibold text-emerald-800 dark:text-emerald-300">
            <span>⭐ Peak Inflow Day</span>
            <span className="font-mono text-[11px] bg-white dark:bg-slate-800 px-2 py-0.5 rounded border border-emerald-200">
              {peakIncomeDay?.fullDate || '—'}
            </span>
          </div>
          <p className="text-xl font-black text-emerald-700 dark:text-emerald-400 mt-2">
            +{fmtInr(peakIncomeDay?.credits)}
          </p>
          <p className="text-[11px] text-emerald-800/80 dark:text-emerald-400 mt-1">
            {peakIncomeDay?.count} transaction(s) · Click to filter this day
          </p>
        </div>

        {/* Peak Expense Day Card */}
        <div
          onClick={() => peakExpenseDay && onSelectDate && onSelectDate(peakExpenseDay.fullDate)}
          className="bg-rose-50/70 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-800/60 rounded-xl p-4 cursor-pointer hover:border-rose-500 transition-all"
        >
          <div className="flex items-center justify-between text-xs font-semibold text-rose-800 dark:text-rose-300">
            <span>🚨 Peak Outflow Day</span>
            <span className="font-mono text-[11px] bg-white dark:bg-slate-800 px-2 py-0.5 rounded border border-rose-200">
              {peakExpenseDay?.fullDate || '—'}
            </span>
          </div>
          <p className="text-xl font-black text-rose-700 dark:text-rose-400 mt-2">
            -{fmtInr(peakExpenseDay?.debits)}
          </p>
          <p className="text-[11px] text-rose-800/80 dark:text-rose-400 mt-1">
            {peakExpenseDay?.count} transaction(s) · Click to filter this day
          </p>
        </div>

        {/* Volume Distribution Mini-Chart */}
        <div className="bg-gray-50 dark:bg-slate-800/60 border border-gray-200 dark:border-slate-700 rounded-xl p-4 flex items-center justify-between">
          <div>
            <p className="text-xs font-bold text-gray-700 dark:text-gray-300">Volume Distribution</p>
            <div className="mt-2 space-y-1 text-xs">
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 shrink-0"></span>
                <span className="text-gray-600 dark:text-gray-400">Income: <strong>{incomePct}%</strong></span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-500 shrink-0"></span>
                <span className="text-gray-600 dark:text-gray-400">Expense: <strong>{expensePct}%</strong></span>
              </div>
            </div>
          </div>
          <div className="w-20 h-20 shrink-0">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={distributionData}
                  dataKey="value"
                  innerRadius={22}
                  outerRadius={36}
                  paddingAngle={3}
                >
                  {distributionData.map((d, i) => (
                    <Cell key={i} fill={d.color} />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </section>
  )
}
