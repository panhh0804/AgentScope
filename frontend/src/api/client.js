/**
 * client.js —— Axios 网络请求客户端封装模块
 * 
 * 职责：
 *   - 初始化并配置 Axios 实例 (baseURL, timeout)。
 *   - 拦截器注入 (interceptors)：
 *     - Request Interceptor: 为每次请求打上开始时间戳，以便统计接口执行时延。
 *     - Response Interceptor: 接口成功或失败时，根据环境变量决定是否在 Console 输出接口时延耗时性能日志。
 *   - 导出高层业务封装函数: getData, postData, putData 自动解包透出 `.data.data` 部分。
 */

import axios from 'axios'

// 实例化并配置全局 API 路由网关及超时时间
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: Number(import.meta.env.VITE_API_TIMEOUT || 180000) // 默认 3 分钟超时限制
})

// 判断是否需要在浏览器的 Console 中打印 API 性能时延日志
const shouldLogApiTiming = () => import.meta.env.DEV || import.meta.env.VITE_API_TIMING_LOG === 'true'

// 跨浏览器获取微秒级/毫秒级物理精度时间戳
const now = () => {
  if (typeof performance !== 'undefined' && typeof performance.now === 'function') {
    return performance.now()
  }
  return Date.now()
}

// 格式化输出接口请求标签说明，形如 "GET /api/v1/realtime/overview"
const requestLabel = (config = {}) => {
  const method = (config.method || 'get').toUpperCase()
  const baseURL = config.baseURL || ''
  const url = config.url || ''
  return `${method} ${url.startsWith('http') ? url : `${baseURL}${url}`}`
}

// 计算当前请求从下发到收到响应响应经历的总时延耗时（ms）
const requestDuration = (config = {}) => {
  const startTime = config.metadata?.startTime
  return typeof startTime === 'number' ? Math.round(now() - startTime) : null
}

// 辅助判定当前请求拦截错误是否是由网络连接超时所触发
const isTimeoutError = (error) => {
  const message = String(error?.message || '').toLowerCase()
  return error?.code === 'ECONNABORTED' || message.includes('timeout') || error?.name === 'AbortError'
}

// 1. 请求拦截器：开始前挂载毫秒级时间戳
api.interceptors.request.use((config) => {
  config.metadata = {
    ...(config.metadata || {}),
    startTime: now()
  }
  return config
})

// 2. 响应拦截器：计算时延耗时，开发环境下打印接口运行指标
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

/**
 * 封装统一的 GET 请求
 */
export async function getData(path, params = {}, config = {}) {
  const response = await api.get(path, { params, ...config })
  return response.data.data
}

/**
 * 封装统一的 POST 请求
 */
export async function postData(path, payload = {}, config = {}) {
  const response = await api.post(path, payload, config)
  return response.data.data
}

/**
 * 封装统一的 PUT 请求
 */
export async function putData(path, payload = {}, config = {}) {
  const response = await api.put(path, payload, config)
  return response.data.data
}
