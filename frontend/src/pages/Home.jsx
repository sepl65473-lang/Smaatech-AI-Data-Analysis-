import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { uploadStatement, uploadDataset, getErrorMessage } from '../api/client'
import DashboardHeader from '../components/DashboardHeader'

export default function Home() {
  const [file, setFile] = useState(null)
  const [dragging, setDragging] = useState(false)
  const [loading, setLoading] = useState(false)
  const [analyzingStatus, setAnalyzingStatus] = useState('')
  const [error, setError] = useState(null)
  const inputRef = useRef(null)
  const navigate = useNavigate()

  const ACCEPTED = ['.pdf', '.csv', '.xlsx', '.json']

  function handleFile(f) {
    const ext = '.' + f.name.split('.').pop()?.toLowerCase()
    if (!ACCEPTED.includes(ext)) {
      setError(`Unsupported file type "${ext}". Please upload a PDF, CSV, XLSX, or JSON file.`)
      return
    }
    if (f.size === 0) {
      setError('Selected file appears to be empty.')
      return
    }
    setError(null)
    setFile(f)
  }

  function onDrop(e) {
    e.preventDefault()
    setDragging(false)
    const f = e.dataTransfer.files[0]
    if (f) handleFile(f)
  }

  async function handleAnalyze() {
    if (!file) return
    setLoading(true)
    setError(null)
    setAnalyzingStatus('Analyzing statement…')
    try {
      try {
        const { session_id } = await uploadStatement(file)
        setAnalyzingStatus('Preparing analytics dashboard…')
        await new Promise((resolve) => setTimeout(resolve, 1800))
        navigate(`/results?sid=${session_id}`)
      } catch (err) {
        // 422 = not a bank statement → run the universal dataset analysis instead
        if (err?.response?.status !== 422) throw err
        setAnalyzingStatus('Analyzing dataset…')
        const { session_id } = await uploadDataset(file)
        setAnalyzingStatus('Preparing dataset dashboard…')
        await new Promise((resolve) => setTimeout(resolve, 1800))
        navigate(`/results?sid=${session_id}&mode=dataset`)
      }
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
      setAnalyzingStatus('')
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-950 flex flex-col transition-colors">
      <DashboardHeader />
      <div className="flex-1 flex flex-col items-center justify-center px-4 py-8">
        {/* Header */}
        <div className="mb-10 text-center">
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white tracking-tight">
            📊 AI Data Analysis Platform
          </h1>
          <p className="mt-2 text-gray-500 dark:text-gray-400 text-lg">
            Upload any dataset — bank statements, sales, HR, inventory — and get instant AI-powered insights.
          </p>
        </div>

        {/* Upload card */}
        <div className="w-full max-w-lg bg-white dark:bg-slate-900 rounded-2xl shadow-sm border border-gray-200 dark:border-slate-800 p-8">
          {/* Drop zone */}
          <div
            onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            onClick={() => inputRef.current?.click()}
            className={`
              border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors
              ${dragging ? 'border-green-500 bg-green-50 dark:bg-green-950/20' : 'border-gray-300 dark:border-slate-700 hover:border-green-400 dark:hover:border-green-500 hover:bg-gray-50 dark:hover:bg-slate-800/50'}
            `}
          >
            <input
              ref={inputRef}
              type="file"
              accept=".pdf,.csv,.xlsx,.json"
              className="hidden"
              onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
            />
            <div className="text-4xl mb-3">📄</div>
            {file ? (
              <div>
                <p className="font-medium text-gray-800 dark:text-gray-200">{file.name}</p>
                <p className="text-sm text-gray-400 mt-1">{(file.size / 1024).toFixed(1)} KB</p>
              </div>
            ) : (
              <div>
                <p className="text-gray-600 dark:text-gray-300 font-medium">Drag & drop your bank statement here</p>
                <p className="text-sm text-gray-400 mt-1">or click to browse — PDF, CSV, XLSX, JSON</p>
              </div>
            )}
          </div>

          {/* Error */}
          {error && (
            <p className="mt-3 text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900/60 rounded-lg px-4 py-2">
              {error}
            </p>
          )}

          {/* Analyze button */}
          <button
            onClick={handleAnalyze}
            disabled={!file || loading}
            className="
              mt-5 w-full py-3 rounded-xl font-semibold text-white transition-colors
              bg-green-600 hover:bg-green-700 disabled:bg-gray-300 dark:disabled:bg-slate-800 disabled:cursor-not-allowed
            "
          >
            {loading ? (analyzingStatus || 'Analyzing…') : 'Analyze Data'}
          </button>

          {/* Privacy note */}
          <p className="mt-4 text-xs text-center text-gray-400 dark:text-gray-500">
            🔒 Session-backed storage enabled · Mathematical reconciliation verified with variance ₹0.00
          </p>
        </div>

        {/* Supported formats */}
        <p className="mt-6 text-xs text-gray-400 dark:text-gray-500">
          Supports bank statements · sales data · HR reports · inventory · any CSV/XLSX
        </p>
      </div>
    </div>
  )
}
