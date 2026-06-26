import axios from 'axios'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: Number(import.meta.env.VITE_API_TIMEOUT || 60000)
})

export async function getData(path, params = {}) {
  const response = await api.get(path, { params })
  return response.data.data
}

export async function postData(path, payload = {}) {
  const response = await api.post(path, payload)
  return response.data.data
}

