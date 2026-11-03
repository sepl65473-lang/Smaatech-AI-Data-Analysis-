import { getExportUrl } from '../api/client'

export default function HtmlPreviewModal({ sessionId, onClose, onDownload }) {
  if (!sessionId) return null

  const previewUrl = getExportUrl(sessionId, 'html', true)

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl border border-gray-200 w-full max-w-6xl h-[92vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between bg-gray-50">
          <div className="flex items-center gap-3">
            <span className="text-2xl">🌐</span>
            <div>
              <h3 className="text-lg font-bold text-gray-900">
                Interactive Standalone Dashboard Preview (.html)
              </h3>
              <p className="text-xs text-gray-500">
                Self-contained, offline-capable dashboard · Runs in any browser without backend
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={onDownload}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-semibold transition-colors flex items-center gap-2"
            >
              <span>📥</span> Download HTML
            </button>
            <button
              onClick={onClose}
              className="w-8 h-8 rounded-full bg-gray-200 hover:bg-gray-300 text-gray-600 flex items-center justify-center text-sm font-bold transition-colors"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Embedded HTML Dashboard iframe */}
        <div className="flex-1 bg-gray-50 p-1">
          <iframe
            src={previewUrl}
            title="Interactive Dashboard Preview"
            className="w-full h-full rounded-xl border border-gray-200 bg-white"
          />
        </div>

      </div>
    </div>
  )
}
