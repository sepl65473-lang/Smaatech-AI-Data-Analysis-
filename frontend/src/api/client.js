import axios from 'axios'

export const API_BASE_URL = (typeof window !== 'undefined' && (window.location.hostname.endsWith('vercel.app') || window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'))
  ? '/api'
  : (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '')
let csrfToken = ''
let csrfPromise = null

export function getCookieCsrf() {
  if (typeof document === 'undefined') return ''
  const cookiePart = document.cookie.split('; ').find((part) => part.startsWith('sepl_csrf='))
  return cookiePart ? decodeURIComponent(cookiePart.split('=').slice(1).join('=')) : ''
}

export async function ensureCsrf(force = false) {
  const cookieVal = getCookieCsrf()
  if (!force && csrfToken && cookieVal && csrfToken === cookieVal) {
    return csrfToken
  }

  if (!csrfPromise) {
    csrfPromise = axios
      .get(`${API_BASE_URL}/auth/csrf`, { withCredentials: true })
      .then((res) => {
        if (res.data?.csrf_token) {
          csrfToken = res.data.csrf_token
        }
        return csrfToken || getCookieCsrf()
      })
      .catch(() => csrfToken || getCookieCsrf())
      .finally(() => {
        csrfPromise = null
      })
  }
  return csrfPromise
}

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000, // 60s — LLM calls can be slow
  withCredentials: true,
})

api.interceptors.request.use(async (config) => {
  const method = (config.method || 'get').toUpperCase()
  if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(method)) {
    if (!config.url?.endsWith('/auth/csrf')) {
      let csrf = csrfToken || getCookieCsrf()
      if (!csrf) {
        csrf = await ensureCsrf(true)
      }
      const cookieVal = getCookieCsrf()
      const token = cookieVal || csrf || csrfToken
      if (token) {
        config.headers['X-CSRF-Token'] = token
      }
    }
  }
  return config
})

api.interceptors.response.use(
  (response) => {
    if (response.config.url?.endsWith('/auth/csrf') && response.data?.csrf_token) {
      csrfToken = response.data.csrf_token
    }
    return response
  },
  async (error) => {
    const config = error.config
    if (!config) return Promise.reject(error)

    const status = error.response?.status
    const detail = error.response?.data?.detail
    const isCsrfError = status === 403 && typeof detail === 'string' && (
      detail.toLowerCase().includes('refresh the page') ||
      detail.toLowerCase().includes('csrf')
    )

    // Controlled single-retry for expired/mismatched CSRF tokens
    if (isCsrfError) {
      config.__csrfRetryCount = config.__csrfRetryCount || 0
      if (config.__csrfRetryCount < 1) {
        config.__csrfRetryCount += 1
        try {
          const freshToken = await ensureCsrf(true)
          if (freshToken) {
            config.headers['X-CSRF-Token'] = freshToken
          }
          return api(config)
        } catch (retryErr) {
          return Promise.reject(retryErr)
        }
      }
    }

    const isGet = (config.method || 'get').toUpperCase() === 'GET'
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
  return getCookieCsrf() || csrfToken
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
