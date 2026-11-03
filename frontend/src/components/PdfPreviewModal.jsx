import { getExportUrl } from '../api/client'

export default function PdfPreviewModal({ sessionId, onClose, onDownload }) {
  if (!sessionId) return null

  const previewUrl = getExportUrl(sessionId, 'pdf', true)

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl border border-gray-200 w-full max-w-5xl h-[90vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between bg-gray-50">
          <div className="flex items-center gap-3">
            <span className="text-2xl">📄</span>
            <div>
              <h3 className="text-lg font-bold text-gray-900">
                PDF Report Preview
              </h3>
              <p className="text-xs text-gray-500">
                Multi-page executive report · Charts, separate Dr/Cr columns & page numbers
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={onDownload}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-xl text-sm font-semibold transition-colors flex items-center gap-2"
            >
              <span>📥</span> Download PDF
            </button>
            <button
              onClick={onClose}
              className="w-8 h-8 rounded-full bg-gray-200 hover:bg-gray-300 text-gray-600 flex items-center justify-center text-sm font-bold transition-colors"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Embedded PDF iframe */}
        <div className="flex-1 bg-gray-100 p-2">
          <iframe
            src={previewUrl}
            title="PDF Report Preview"
            className="w-full h-full rounded-xl border border-gray-300 bg-white"
          />
        </div>

      </div>
    </div>
  )
}
