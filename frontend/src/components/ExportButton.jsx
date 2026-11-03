import { getExportUrl } from '../api/client'

export default function ExportButton({ sessionId }) {
  function download(format) {
    const url = getExportUrl(sessionId, format)
    const a = document.createElement('a')
    a.href = url
    a.download = `data_analysis_report.${format}`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }

  return (
    <div className="flex gap-3">
      <button
        onClick={() => download('csv')}
        className="flex items-center gap-2 px-4 py-2 text-sm font-semibold border border-gray-300 rounded-xl text-gray-700 hover:bg-gray-50 transition-colors"
      >
        <span>📥</span> Download CSV
      </button>
      <button
        onClick={() => download('pdf')}
        className="flex items-center gap-2 px-4 py-2 text-sm font-semibold border border-gray-300 rounded-xl text-gray-700 hover:bg-gray-50 transition-colors"
      >
        <span>📄</span> Download PDF
      </button>
    </div>
  )
}
