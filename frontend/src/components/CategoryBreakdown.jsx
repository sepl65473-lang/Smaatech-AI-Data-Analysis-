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
  Other:         '#9ca3af',
}

function colorFor(cat) {
  return CATEGORY_COLORS[cat] ?? '#9ca3af'
}

function fmtInr(n) {
  return '₹' + n.toLocaleString('en-IN', { maximumFractionDigits: 0 })
}

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const d = payload[0]
  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-lg px-4 py-2 text-sm">
      <p className="font-semibold text-gray-800">{d.name}</p>
      <p className="text-gray-600">{fmtInr(d.value)}</p>
      <p className="text-gray-400">{d.payload.percentage.toFixed(1)}% of spend</p>
    </div>
  )
}

export default function CategoryBreakdown({ topCategories, totalSpend }) {
  if (!topCategories.length) return null

  const data = topCategories.map((c) => ({ name: c.category, value: c.amount, ...c }))

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
      <h2 className="text-lg font-semibold text-gray-800 mb-5">Spending by Category</h2>

      <div className="flex flex-col lg:flex-row gap-6 items-start">
        {/* Pie chart */}
        <div className="w-full lg:w-64 h-56 shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                innerRadius={52}
                outerRadius={90}
                paddingAngle={2}
              >
                {data.map((entry) => (
                  <Cell key={entry.name} fill={colorFor(entry.name)} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
              <Legend
                iconType="circle"
                iconSize={8}
                wrapperStyle={{ fontSize: '12px' }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Ranked bar list */}
        <div className="flex-1 w-full space-y-3">
          {topCategories.map((cat) => {
            const pct = totalSpend > 0 ? (cat.amount / totalSpend) * 100 : 0
            return (
              <div key={cat.category}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-gray-700 flex items-center gap-2">
                    <span
                      className="inline-block w-2.5 h-2.5 rounded-full shrink-0"
                      style={{ backgroundColor: colorFor(cat.category) }}
                    />
                    {cat.category}
                  </span>
                  <span className="text-sm text-gray-500">
                    {fmtInr(cat.amount)}
                    <span className="text-gray-400 ml-1 text-xs">({pct.toFixed(1)}%)</span>
                  </span>
                </div>
                <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{
                      width: `${Math.min(pct, 100)}%`,
                      backgroundColor: colorFor(cat.category),
                    }}
                  />
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
