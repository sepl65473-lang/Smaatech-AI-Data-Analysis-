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
} from 'recharts'

function fmtInr(n) {
  if (n === null || n === undefined) return '—'
  return '₹' + Math.abs(n).toLocaleString('en-IN', { maximumFractionDigits: 0 })
}

export default function CashFlowCharts({ metrics }) {
  const dailyData = (metrics?.daily_cash_flow || []).map((d) => ({
    date: d.date.slice(5), // MM-DD
    fullDate: d.date,
    net: d.net,
    cumulative: d.cumulative,
    credits: d.credits,
    debits: d.debits,
  }))

  const topPayers = metrics?.top_payers || []
  const topPayees = metrics?.top_payees || []

  if (!dailyData.length && !topPayers.length) return null

  return (
    <div className="space-y-6">
      {/* Cash Flow Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Daily Net Cash Flow */}
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-base font-bold text-gray-900">Daily Net Cash Flow</h3>
              <p className="text-xs text-gray-500">Net movement (Credits − Debits) by transaction date</p>
            </div>
            <span className="text-xs font-semibold px-2 py-0.5 rounded bg-gray-100 text-gray-600">
              {dailyData.length} Days
            </span>
          </div>

          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={dailyData} margin={{ top: 8, right: 8, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="date" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} tickFormatter={(v) => `₹${Math.round(v / 1000)}k`} />
                <Tooltip
                  formatter={(value, name) => [
                    (value < 0 ? '-' : '+') + fmtInr(value),
                    name === 'net' ? 'Net Flow' : name,
                  ]}
                  labelFormatter={(l, p) => p?.[0]?.payload?.fullDate || l}
                />
                <Bar dataKey="net" radius={[2, 2, 0, 0]}>
                  {dailyData.map((entry, index) => (
                    <Cell key={index} fill={entry.net >= 0 ? '#16a34a' : '#ef4444'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Cumulative Cash Flow Trend */}
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-base font-bold text-gray-900">Cumulative Cash Flow</h3>
              <p className="text-xs text-gray-500">Running net balance trajectory over the statement period</p>
            </div>
            <span className="text-xs font-semibold px-2 py-0.5 rounded bg-blue-50 text-blue-700">
              Trajectory
            </span>
          </div>

          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={dailyData} margin={{ top: 8, right: 8, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="date" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} tickFormatter={(v) => `₹${Math.round(v / 1000)}k`} />
                <Tooltip
                  formatter={(value) => [(value < 0 ? '-' : '+') + fmtInr(value), 'Cumulative Net']}
                  labelFormatter={(l, p) => p?.[0]?.payload?.fullDate || l}
                />
                <Line
                  type="monotone"
                  dataKey="cumulative"
                  stroke="#2563eb"
                  strokeWidth={2.5}
                  dot={false}
                  activeDot={{ r: 5 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

      </div>

      {/* Counterparties: Top Payers vs Top Payees */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* Top Payers */}
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2">
              <span className="text-emerald-600">📥</span> Top Payers (Income Sources)
            </h3>
            <span className="text-xs text-gray-400 font-medium">{topPayers.length} entities</span>
          </div>
          <div className="divide-y divide-gray-100 max-h-56 overflow-y-auto">
            {topPayers.length === 0 ? (
              <p className="py-4 text-xs text-gray-400 text-center">No credit counterparties recorded.</p>
            ) : (
              topPayers.map((p, i) => (
                <div key={i} className="py-2.5 flex items-center justify-between text-xs">
                  <div className="truncate max-w-[200px]">
                    <p className="font-semibold text-gray-800 truncate">{p.payer}</p>
                    <p className="text-[10px] text-gray-400">{p.count} transaction{p.count > 1 ? 's' : ''}</p>
                  </div>
                  <div className="text-right whitespace-nowrap">
                    <p className="font-bold text-emerald-600">+{fmtInr(p.amount)}</p>
                    <p className="text-[10px] text-gray-400">{p.pct}% of income</p>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Top Payees */}
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2">
              <span className="text-rose-600">📤</span> Top Payees (Outflow Entities)
            </h3>
            <span className="text-xs text-gray-400 font-medium">{topPayees.length} entities</span>
          </div>
          <div className="divide-y divide-gray-100 max-h-56 overflow-y-auto">
            {topPayees.length === 0 ? (
              <p className="py-4 text-xs text-gray-400 text-center">No debit counterparties recorded.</p>
            ) : (
              topPayees.map((p, i) => (
                <div key={i} className="py-2.5 flex items-center justify-between text-xs">
                  <div className="truncate max-w-[200px]">
                    <p className="font-semibold text-gray-800 truncate">{p.payee}</p>
                    <p className="text-[10px] text-gray-400">{p.count} transaction{p.count > 1 ? 's' : ''}</p>
                  </div>
                  <div className="text-right whitespace-nowrap">
                    <p className="font-bold text-rose-600">-{fmtInr(p.amount)}</p>
                    <p className="text-[10px] text-gray-400">{p.pct}% of spend</p>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

      </div>
    </div>
  )
}
