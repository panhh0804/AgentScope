import { getData } from './client'

export const fetchAnalyticsTrend = () => getData('/analytics/trend')
export const fetchAnalyticsErrors = (params) => getData('/analytics/errors', params)
export const fetchAnalyticsAgentStats = () => getData('/analytics/agent-stats')
