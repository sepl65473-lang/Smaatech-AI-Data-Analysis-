import axios from 'axios'

export const API_BASE_URL = (typeof window !== 'undefined' && window.location.hostname.endsWith('vercel.app'))
  ? '/api'
  : (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '')
let csrfToken = ''

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000, // 60s — LLM calls can be slow
  withCredentials: true,
})

api.interceptors.request.use((config) => {
  const method = (config.method || 'get').toUpperCase()
  if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(method)) {
    const csrf = csrfToken || document.cookie.split('; ').find((part) => part.startsWith('sepl_csrf='))?.split('=').slice(1).join('=')
    if (csrf) config.headers['X-CSRF-Token'] = decodeURIComponent(csrf)
  }
  return config
})

api.interceptors.response.use(
  (response) => {
    if (response.config.url?.endsWith('/auth/csrf') && response.data?.csrf_token) csrfToken = response.data.csrf_token
    return response
  },
  async (error) => {
    const config = error.config
    if (!config) return Promise.reject(error)

    const isGet = (config.method || 'get').toUpperCase() === 'GET'
    const status = error.response?.status
    const isTransient = [502, 503, 504].includes(status) || error.code === 'ECONNABORTED'

    config.__retryCount = config.__retryCount || 0
    if (isGet && isTransient && config.__retryCount < 2) {
      config.__retryCount += 1
      await new Promise((res) => setTimeout(res, 3000))
      return api(config)
    }

    return Promise.reject(error)
  }
)

export function getCsrfToken() {
  return csrfToken || decodeURIComponent(document.cookie.split('; ').find((part) => part.startsWith('sepl_csrf='))?.split('=').slice(1).join('=') || '')
}

export function apiUrl(path) {
  return `${API_BASE_URL}/${path.replace(/^\//, '')}`
}

/** Turn an axios error into the backend's human-readable message */
export function getErrorMessage(err) {
  const detail = err?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map((d) => d.msg).join('; ')
  if (err?.code === 'ECONNABORTED') return 'The server took too long to respond. Please try again.'
  if (!err?.response) return 'Could not connect to the server. Is the backend running?'
  return err.message || 'Something went wrong. Please try again.'
}

/** Upload a bank statement file and get back a session_id */
export async function uploadStatement(file) {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await api.post('/upload', formData)
  return data
}

/** Fetch analysis results for a session */
export async function getResults(sessionId) {
  const { data } = await api.get(`/results/${sessionId}`)
  return data
}

/** Get deliverable validation status and filenames */
export async function getExportStatus(sessionId) {
  const { data } = await api.get(`/export/${sessionId}/status`)
  return data
}

/** Get export download or inline preview URL */
export function getExportUrl(sessionId, format, preview = false) {
  return `${apiUrl(`/export/${sessionId}`)}?format=${format}${preview ? '&preview=true' : ''}`
}

/** Fetch interactive workbook sheet preview for in-app Excel modal */
export async function getWorkbookPreview(sessionId) {
  const { data } = await api.get(`/export/${sessionId}?format=xlsx&preview=true`)
  return data
}

/** Universal Analysis: Upload any dataset (Sales, HR, Inventory, CSV, XLSX, JSON) */
export async function uploadDataset(file) {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await api.post('/analyze', formData)
  return data
}

/** Universal Analysis: Get analysis details */
export async function getAnalysis(analysisId) {
  const { data } = await api.get(`/analysis/${analysisId}`)
  return data
}

/** Universal Analysis: Ask a question about data */
export async function askQuestion(analysisId, question) {
  const { data } = await api.post(`/analysis/${analysisId}/qa`, { question })
  return data
}

/** Universal Analysis: Preview or apply data cleaning */
export async function cleanData(analysisId, operations, apply = false) {
  const { data } = await api.post(`/analysis/${analysisId}/clean`, { operations, apply })
  return data
}

/** Universal Analysis: Download cleaned dataset */
export function getDownloadCleanedUrl(analysisId, format = 'csv') {
  return `${apiUrl(`/analysis/${analysisId}/download`)}?format=${format}`
}

export default api
