import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from 'recharts'
import { getDownloadCleanedUrl } from '../api/client'

function humanize(key) {
  return key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

function fmtValue(v) {
  if (typeof v === 'number') return v.toLocaleString('en-IN', { maximumFractionDigits: 2 })
  if (v === null || v === undefined || v === '') return '—'
  return String(v)
}

function Card({ title, children }) {
  return (
    <section className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
      {title && <h2 className="text-base font-semibold text-gray-900 mb-4">{title}</h2>}
      {children}
    </section>
  )
}

function ChartCard({ chart }) {
  if (!chart.data?.length) return null
  return (
    <Card title={chart.title}>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chart.data} margin={{ top: 4, right: 8, left: 0, bottom: 4 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
            <XAxis dataKey="name" tick={{ fontSize: 11 }} interval="preserveStartEnd" />
            <YAxis tick={{ fontSize: 11 }} width={48} />
            <Tooltip formatter={(v) => fmtValue(v)} />
            <Bar dataKey="value" fill="#16a34a" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  )
}

function DataTable({ columns, rows }) {
  return (
    <div className="overflow-x-auto max-h-[28rem] border border-gray-100 rounded-lg">
      <table className="min-w-full text-sm">
        <thead className="bg-gray-50 sticky top-0">
          <tr>
            {columns.map((c) => (
              <th key={c} className="px-3 py-2 text-left font-medium text-gray-600 whitespace-nowrap">{c}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {rows.map((row, i) => (
            <tr key={i} className="hover:bg-gray-50">
              {row.map((cell, j) => (
                <td key={j} className="px-3 py-2 text-gray-700 whitespace-nowrap max-w-xs truncate">{fmtValue(cell)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function DatasetResults({ result, sessionId, onNew }) {
  const analysis = result.business_analysis ?? {}
  const quality = result.data_quality ?? {}
  const kpis = Object.entries(analysis.kpis ?? {})
  const insights = analysis.insights ?? []
  const charts = analysis.charts ?? []
  const tables = analysis.tables ?? []
  const issues = quality.issues ?? []
  const columns = result.columns ?? []
  const preview = result.preview_data ?? []

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3 min-w-0">
            <span className="text-xl font-bold text-gray-900">📊 AI Data Analysis Platform</span>
            {result.filename && (
              <span className="hidden sm:inline text-xs text-gray-400 bg-gray-100 px-2.5 py-1 rounded-full truncate">
                {result.filename} · {humanize(result.dataset_type ?? 'general')} dataset
              </span>
            )}
          </div>
          <div className="flex items-center gap-3">
            <a
              href={getDownloadCleanedUrl(sessionId, 'csv')}
              className="text-sm px-4 py-2 bg-green-600 text-white rounded-xl hover:bg-green-700 transition-colors font-medium"
            >
              Download CSV
            </a>
            <button
              onClick={onNew}
              className="text-sm px-4 py-2 border border-gray-300 rounded-xl text-gray-600 hover:bg-gray-50 transition-colors font-medium"
            >
              New Analysis
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-8 space-y-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5">
            <p className="text-xs text-gray-500">Data Quality Score</p>
            <p className="text-2xl font-bold text-gray-900 mt-1">{quality.quality_score ?? '—'}/100</p>
          </div>
          {kpis.map(([k, v]) => (
            <div key={k} className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5">
              <p className="text-xs text-gray-500">{humanize(k)}</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">{fmtValue(v)}</p>
            </div>
          ))}
        </div>

        {insights.length > 0 && (
          <Card title="Insights">
            <ul className="space-y-2 text-sm text-gray-700 list-disc pl-5">
              {insights.map((ins, i) => <li key={i}>{ins}</li>)}
            </ul>
          </Card>
        )}

        {charts.length > 0 && (
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            {charts.map((c, i) => <ChartCard key={i} chart={c} />)}
          </div>
        )}

        {tables.map((t, i) => (
          <Card key={i} title={t.title}>
            <DataTable columns={t.columns} rows={t.rows} />
          </Card>
        ))}

        {issues.length > 0 && (
          <Card title="Data Quality Issues">
            <ul className="space-y-2 text-sm">
              {issues.map((iss, i) => (
                <li key={i} className={iss.type === 'error' ? 'text-red-600' : iss.severity === 'warning' ? 'text-yellow-700' : 'text-gray-600'}>
                  {iss.message}
                </li>
              ))}
            </ul>
          </Card>
        )}

        {preview.length > 0 && (
          <Card title={`Data Preview (first ${preview.length} of ${result.row_count} rows)`}>
            <DataTable columns={columns} rows={preview.map((r) => columns.map((c) => r[c]))} />
          </Card>
        )}

        <p className="text-center text-xs text-gray-400 pb-4">
          🔒 Data processed in memory only · Session expires after 60 min
        </p>
      </main>
    </div>
  )
}
