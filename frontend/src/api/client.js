import axios from 'axios'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: Number(import.meta.env.VITE_API_TIMEOUT || 180000)
})

const shouldLogApiTiming = () => import.meta.env.DEV || import.meta.env.VITE_API_TIMING_LOG === 'true'

const now = () => {
  if (typeof performance !== 'undefined' && typeof performance.now === 'function') {
    return performance.now()
  }
  return Date.now()
}

const requestLabel = (config = {}) => {
  const method = (config.method || 'get').toUpperCase()
  const baseURL = config.baseURL || ''
  const url = config.url || ''
  return `${method} ${url.startsWith('http') ? url : `${baseURL}${url}`}`
}

const requestDuration = (config = {}) => {
  const startTime = config.metadata?.startTime
  return typeof startTime === 'number' ? Math.round(now() - startTime) : null
}

const isTimeoutError = (error) => {
  const message = String(error?.message || '').toLowerCase()
  return error?.code === 'ECONNABORTED' || message.includes('timeout') || error?.name === 'AbortError'
}

api.interceptors.request.use((config) => {
  config.metadata = {
    ...(config.metadata || {}),
    startTime: now()
  }
  return config
})

api.interceptors.response.use(
  (response) => {
    if (shouldLogApiTiming()) {
      const duration = requestDuration(response.config)
      console.debug('[api]', requestLabel(response.config), {
        duration_ms: duration,
        status: response.status,
        success: true,
        timeout: false
      })
    }
    return response
  },
  (error) => {
    if (shouldLogApiTiming()) {
      const config = error.config || {}
      const duration = requestDuration(config)
      console.warn('[api]', requestLabel(config), {
        duration_ms: duration,
        status: error.response?.status || null,
        success: false,
        timeout: isTimeoutError(error),
        message: error.message
      })
    }
    return Promise.reject(error)
  }
)

export async function getData(path, params = {}, config = {}) {
  const response = await api.get(path, { params, ...config })
  return response.data.data
}

export async function postData(path, payload = {}, config = {}) {
  const response = await api.post(path, payload, config)
  return response.data.data
}

export async function putData(path, payload = {}, config = {}) {
  const response = await api.put(path, payload, config)
  return response.data.data
}


