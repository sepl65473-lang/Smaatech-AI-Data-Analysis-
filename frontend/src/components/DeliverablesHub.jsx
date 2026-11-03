import { useState, useEffect } from 'react'
import { getExportStatus, getExportUrl } from '../api/client'
import PdfPreviewModal from './PdfPreviewModal'
import ExcelPreviewModal from './ExcelPreviewModal'
import HtmlPreviewModal from './HtmlPreviewModal'

export default function DeliverablesHub({ sessionId, onScrollToDashboard }) {
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Preview modals state
  const [activePreview, setActivePreview] = useState(null) // 'pdf' | 'excel' | 'html' | null

  useEffect(() => {
    if (!sessionId) return
    getExportStatus(sessionId)
      .then(setStatus)
      .catch((err) => {
        console.error('Failed to verify deliverables status:', err)
        setError(err.message || 'Deliverables validation pending')
      })
      .finally(() => setLoading(false))
  }, [sessionId])

  function triggerDownload(format) {
    const url = getExportUrl(sessionId, format, false)
    const a = document.createElement('a')
    a.href = url
    if (status?.filenames?.[format]) {
      a.download = status.filenames[format]
    }
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }

  const isReady = status?.status === 'ready'
  const filenames = status?.filenames || {}

  return (
    <section id="deliverables-hub" className="bg-gradient-to-br from-slate-900 via-slate-800 to-indigo-950 text-white rounded-3xl p-7 shadow-xl border border-slate-700/60 relative overflow-hidden">
      {/* Background glow */}
      <div className="absolute top-0 right-0 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />

      {/* Header & Validation badge */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-700/60">
        <div>
          <div className="flex items-center gap-2.5">
            <span className="text-2xl">📦</span>
            <h2 className="text-xl font-bold tracking-tight text-white">
              Deliverables Hub
            </h2>
            <span className={`text-xs px-2.5 py-1 rounded-full font-semibold border ${
              isReady
                ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
                : 'bg-amber-500/20 text-amber-300 border-amber-500/30'
            }`}>
              {loading ? 'Validating…' : isReady ? '✓ Verified & Ready' : 'Pending'}
            </span>
          </div>
          {error && (
            <div className="mt-2 text-xs text-rose-300 bg-rose-950/40 border border-rose-800/60 rounded-lg px-3 py-1.5 inline-block">
              ⚠️ {error}
            </div>
          )}
          <p className="text-xs text-slate-400 mt-1">
            {status?.period_label ? `Period: ${status.period_label} · ` : ''}
            Three independent deliverables generated from one canonical, verified dataset.
          </p>
        </div>

        {/* Quick action: ZIP Bundle download */}
        <button
          onClick={() => triggerDownload('zip')}
          disabled={!isReady}
          className="px-5 py-2.5 bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-semibold rounded-xl shadow-lg shadow-emerald-900/30 transition-all flex items-center justify-center gap-2"
        >
          <span>📦</span>
          <span>Download Complete Package (ZIP)</span>
        </button>
      </div>

      {/* 5 Actions Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mt-6">
        
        {/* Action 1: View Interactive Dashboard */}
        <div className="bg-slate-800/80 hover:bg-slate-800 border border-slate-700/80 rounded-2xl p-4 flex flex-col justify-between transition-all">
          <div>
            <div className="text-2xl mb-2">📊</div>
            <h3 className="text-sm font-bold text-white">1. Interactive Dashboard</h3>
            <p className="text-xs text-slate-400 mt-1 leading-relaxed">
              Explore dynamic KPI cards, cash flow, category breakdown, and live transaction filters.
            </p>
          </div>
          <button
            onClick={onScrollToDashboard}
            className="mt-4 w-full py-2 bg-slate-700 hover:bg-slate-600 text-slate-200 text-xs font-semibold rounded-lg transition-colors flex items-center justify-center gap-1.5"
          >
            <span>👁️</span> View Dashboard
          </button>
        </div>

        {/* Action 2: PDF Report */}
        <div className="bg-slate-800/80 hover:bg-slate-800 border border-slate-700/80 rounded-2xl p-4 flex flex-col justify-between transition-all">
          <div>
            <div className="text-2xl mb-2">📄</div>
            <h3 className="text-sm font-bold text-white">2. PDF Report</h3>
            <p className="text-xs text-slate-400 mt-1 leading-relaxed truncate" title={filenames.pdf}>
              {filenames.pdf || 'Multi-page financial audit with separate Dr/Cr columns & page numbers.'}
            </p>
          </div>
          <div className="mt-4 flex flex-col gap-1.5">
            <button
              onClick={() => setActivePreview('pdf')}
              disabled={!isReady}
              className="w-full py-1.5 bg-slate-700/90 hover:bg-slate-700 disabled:opacity-50 text-slate-300 text-xs font-medium rounded-lg transition-colors flex items-center justify-center gap-1"
            >
              <span>👁️</span> Preview PDF
            </button>
            <button
              onClick={() => triggerDownload('pdf')}
              disabled={!isReady}
              className="w-full py-2 bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white text-xs font-semibold rounded-lg transition-colors flex items-center justify-center gap-1.5 shadow-sm"
            >
              <span>📥</span> Download PDF
            </button>
          </div>
        </div>

        {/* Action 3: Excel Workbook */}
        <div className="bg-slate-800/80 hover:bg-slate-800 border border-slate-700/80 rounded-2xl p-4 flex flex-col justify-between transition-all">
          <div>
            <div className="text-2xl mb-2">📗</div>
            <h3 className="text-sm font-bold text-white">3. Excel Workbook</h3>
            <p className="text-xs text-slate-400 mt-1 leading-relaxed truncate" title={filenames.xlsx}>
              {filenames.xlsx || '7 sheets with native formulas, frozen headers, and reconciliation audit.'}
            </p>
          </div>
          <div className="mt-4 flex flex-col gap-1.5">
            <button
              onClick={() => setActivePreview('excel')}
              disabled={!isReady}
              className="w-full py-1.5 bg-slate-700/90 hover:bg-slate-700 disabled:opacity-50 text-slate-300 text-xs font-medium rounded-lg transition-colors flex items-center justify-center gap-1"
            >
              <span>👁️</span> Preview 7 Sheets
            </button>
            <button
              onClick={() => triggerDownload('xlsx')}
              disabled={!isReady}
              className="w-full py-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white text-xs font-semibold rounded-lg transition-colors flex items-center justify-center gap-1.5 shadow-sm"
            >
              <span>📥</span> Download .xlsx
            </button>
          </div>
        </div>

        {/* Action 4: Standalone HTML Dashboard */}
        <div className="bg-slate-800/80 hover:bg-slate-800 border border-slate-700/80 rounded-2xl p-4 flex flex-col justify-between transition-all">
          <div>
            <div className="text-2xl mb-2">🌐</div>
            <h3 className="text-sm font-bold text-white">4. HTML Dashboard</h3>
            <p className="text-xs text-slate-400 mt-1 leading-relaxed truncate" title={filenames.html}>
              {filenames.html || 'Standalone offline file with embedded charts & real-time filtering.'}
            </p>
          </div>
          <div className="mt-4 flex flex-col gap-1.5">
            <button
              onClick={() => setActivePreview('html')}
              disabled={!isReady}
              className="w-full py-1.5 bg-slate-700/90 hover:bg-slate-700 disabled:opacity-50 text-slate-300 text-xs font-medium rounded-lg transition-colors flex items-center justify-center gap-1"
            >
              <span>👁️</span> Preview HTML
            </button>
            <button
              onClick={() => triggerDownload('html')}
              disabled={!isReady}
              className="w-full py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-semibold rounded-lg transition-colors flex items-center justify-center gap-1.5 shadow-sm"
            >
              <span>📥</span> Download HTML
            </button>
          </div>
        </div>

        {/* Action 5: Complete Package (ZIP) */}
        <div className="bg-gradient-to-b from-indigo-900/60 to-slate-800 border border-indigo-500/40 rounded-2xl p-4 flex flex-col justify-between transition-all">
          <div>
            <div className="text-2xl mb-2">🗜️</div>
            <h3 className="text-sm font-bold text-white">5. Report Package</h3>
            <p className="text-xs text-indigo-200/80 mt-1 leading-relaxed truncate" title={filenames.zip}>
              {filenames.zip || 'All 3 deliverables bundled into a single ZIP archive.'}
            </p>
          </div>
          <div className="mt-4">
            <button
              onClick={() => triggerDownload('zip')}
              disabled={!isReady}
              className="w-full py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-xs font-semibold rounded-lg transition-colors flex items-center justify-center gap-1.5 shadow-md shadow-indigo-950/50"
            >
              <span>📥</span> Download .zip
            </button>
          </div>
        </div>

      </div>

      {/* Modals */}
      {activePreview === 'pdf' && (
        <PdfPreviewModal
          sessionId={sessionId}
          onClose={() => setActivePreview(null)}
          onDownload={() => triggerDownload('pdf')}
        />
      )}
      {activePreview === 'excel' && (
        <ExcelPreviewModal
          sessionId={sessionId}
          onClose={() => setActivePreview(null)}
          onDownload={() => triggerDownload('xlsx')}
        />
      )}
      {activePreview === 'html' && (
        <HtmlPreviewModal
          sessionId={sessionId}
          onClose={() => setActivePreview(null)}
          onDownload={() => triggerDownload('html')}
        />
      )}
    </section>
  )
}
