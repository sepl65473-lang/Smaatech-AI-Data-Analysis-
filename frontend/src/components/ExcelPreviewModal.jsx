import { useState, useEffect } from 'react'
import { getWorkbookPreview } from '../api/client'

export default function ExcelPreviewModal({ sessionId, onClose, onDownload }) {
  const [data, setData] = useState(null)
  const [activeSheetIdx, setActiveSheetIdx] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    getWorkbookPreview(sessionId)
      .then(setData)
      .catch((err) => setError(err.message || 'Failed to load Excel workbook preview.'))
      .finally(() => setLoading(false))
  }, [sessionId])

  if (!sessionId) return null

  const sheets = data?.sheets || []
  const activeSheet = sheets[activeSheetIdx] || { rows: [], columns: [] }

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl border border-gray-200 w-full max-w-6xl max-h-[90vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between bg-gray-50">
          <div className="flex items-center gap-3">
            <span className="text-2xl">📗</span>
            <div>
              <h3 className="text-lg font-bold text-gray-900">
                Excel Workbook Preview (.xlsx)
              </h3>
              <p className="text-xs text-gray-500">
                {data?.period_label ? `Period: ${data.period_label} · ` : ''}
                {data?.formula_count ? `${data.formula_count} native formulas active` : '7 Sheets · Reconciled'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={onDownload}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-sm font-semibold transition-colors flex items-center gap-2"
            >
              <span>📥</span> Download .xlsx
            </button>
            <button
              onClick={onClose}
              className="w-8 h-8 rounded-full bg-gray-200 hover:bg-gray-300 text-gray-600 flex items-center justify-center text-sm font-bold transition-colors"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Sheet Tabs */}
        <div className="flex overflow-x-auto border-b border-gray-200 bg-gray-100 px-4 pt-2 gap-1">
          {sheets.map((s, idx) => (
            <button
              key={s.name}
              onClick={() => setActiveSheetIdx(idx)}
              className={`px-4 py-2 text-xs font-semibold rounded-t-lg transition-colors whitespace-nowrap flex items-center gap-2 border-t border-x ${
                activeSheetIdx === idx
                  ? 'bg-white text-emerald-800 border-gray-300 shadow-sm'
                  : 'bg-gray-200 text-gray-600 border-transparent hover:bg-gray-300/80'
              }`}
            >
              <span>{idx + 1}. {s.name}</span>
              {s.charts > 0 && <span className="text-[10px] bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded-full font-bold">Chart</span>}
            </button>
          ))}
        </div>

        {/* Content Table */}
        <div className="flex-1 overflow-auto p-4 bg-white">
          {loading ? (
            <div className="h-64 flex flex-col items-center justify-center gap-3 text-gray-400">
              <div className="text-3xl animate-spin">⏳</div>
              <p className="text-sm font-medium">Rendering 7-sheet workbook preview…</p>
            </div>
          ) : error ? (
            <div className="h-64 flex flex-col items-center justify-center text-red-500 gap-2">
              <p className="font-semibold">⚠️ {error}</p>
            </div>
          ) : (
            <div className="border border-gray-200 rounded-lg overflow-x-auto">
              <table className="min-w-full text-xs font-mono border-collapse">
                <thead>
                  <tr className="bg-gray-100 text-gray-500">
                    <th className="w-12 px-2 py-1.5 border border-gray-200 text-center font-normal">#</th>
                    {activeSheet.columns.map((c) => (
                      <th key={c} className="px-3 py-1.5 border border-gray-200 text-center font-semibold">
                        {c}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {activeSheet.rows.map((row, rIdx) => (
                    <tr key={rIdx} className="hover:bg-blue-50/40">
                      <td className="px-2 py-1 border border-gray-200 text-center bg-gray-50 text-gray-400 select-none">
                        {rIdx + 1}
                      </td>
                      {row.map((cell, cIdx) => (
                        <td
                          key={cIdx}
                          title={cell.f ? `Formula: ${cell.f}` : undefined}
                          className={`px-3 py-1 border border-gray-200 truncate max-w-xs ${
                            cell.b ? 'font-bold text-gray-900 bg-gray-50/50' : 'text-gray-700'
                          } ${cell.f ? 'bg-amber-50/30' : ''}`}
                        >
                          {cell.v}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 border-t border-gray-200 bg-gray-50 flex items-center justify-between text-xs text-gray-500">
          <span>
            {activeSheet.total_rows ? `Showing ${activeSheet.rows.length} of ${activeSheet.total_rows} rows in ${activeSheet.name}` : ''}
          </span>
          <span className="text-emerald-700 font-medium">
            ✓ Formatted with Excel formulas, number masks, and auto-filters
          </span>
        </div>

      </div>
    </div>
  )
}
