import axios from 'axios'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: Number(import.meta.env.VITE_API_TIMEOUT || 180000)
})

export async function getData(path, params = {}, config = {}) {
  const response = await api.get(path, { params, ...config })
  return response.data.data
}

export async function postData(path, payload = {}, config = {}) {
  const response = await api.post(path, payload, config)
  return response.data.data
}

