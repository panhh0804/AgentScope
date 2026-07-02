import { getData } from './client'

export const fetchAnalyticsTrend = () => getData('/analytics/trend')
export const fetchAnalyticsErrors = () => getData('/analytics/errors')
export const fetchAnalyticsAgentStats = () => getData('/analytics/agent-stats')
