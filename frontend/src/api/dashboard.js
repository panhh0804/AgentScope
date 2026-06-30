import { getData, postData } from './client'

const REPORT_TIMEOUT_MS = Number(import.meta.env.VITE_REPORT_TIMEOUT || 180000)

export const fetchOverview = () => getData('/realtime/overview')
export const fetchTrend = (minutes = 60) => getData('/realtime/trend', { minutes })
export const fetchAgents = () => getData('/realtime/agents')
export const fetchRealtimeAlerts = () => getData('/realtime/alerts')

export const fetchDailyMetrics = (start_date, end_date) => getData('/metrics/daily', { start_date, end_date })
export const fetchHourlyMetrics = (date) => getData('/metrics/hourly', { date })
export const fetchAgentRankings = (date) => getData('/rankings/agents', { date })
export const fetchRelationGraph = (date) => getData('/graph/agent-relations', { date })
export const fetchHistoryAlerts = (date) => getData('/alerts/history', { date })

export const generateReport = (payload) => postData('/reports/generate', payload, { timeout: REPORT_TIMEOUT_MS })
export const fetchReports = () => getData('/reports')
export const fetchReportDetail = (reportId) => getData(`/reports/${reportId}`)

