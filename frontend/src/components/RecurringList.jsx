const TAG_STYLES = {
  EMI:          'bg-orange-100 text-orange-700',
  SUBSCRIPTION: 'bg-purple-100 text-purple-700',
  RENT:         'bg-blue-100 text-blue-700',
  SIP:          'bg-green-100 text-green-700',
  INSURANCE:    'bg-yellow-100 text-yellow-700',
}

function tagStyle(tag) {
  return TAG_STYLES[tag.toUpperCase()] ?? 'bg-gray-100 text-gray-600'
}

function fmtInr(n) {
  return '₹' + n.toLocaleString('en-IN', { maximumFractionDigits: 0 })
}

function fmtFreq(freq, occ) {
  const label = freq.charAt(0).toUpperCase() + freq.slice(1)
  return `${label} · ${occ}×`
}

export default function RecurringList({ items }) {
  if (!items.length) {
    return (
      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-2">Recurring Payments</h2>
        <p className="text-sm text-gray-400">No recurring payments detected.</p>
      </div>
    )
  }

  const sorted = [...items].sort((a, b) => b.amount - a.amount)

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-800">Recurring Payments</h2>
        <span className="text-sm text-gray-400">{items.length} detected</span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100">
              <th className="text-left py-2 pr-4 font-medium text-gray-500">Merchant</th>
              <th className="text-right py-2 pr-4 font-medium text-gray-500">Amount</th>
              <th className="text-left py-2 pr-4 font-medium text-gray-500">Tag</th>
              <th className="text-left py-2 font-medium text-gray-500">Frequency</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((item, i) => (
              <tr
                key={i}
                className="border-b border-gray-50 hover:bg-gray-50 transition-colors"
              >
                <td className="py-3 pr-4 font-medium text-gray-800">{item.merchant}</td>
                <td className="py-3 pr-4 text-right font-semibold text-gray-800">
                  {fmtInr(item.amount)}
                </td>
                <td className="py-3 pr-4">
                  <span className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold ${tagStyle(item.tag)}`}>
                    {item.tag}
                  </span>
                </td>
                <td className="py-3 text-gray-500">{fmtFreq(item.frequency, item.occurrences)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
