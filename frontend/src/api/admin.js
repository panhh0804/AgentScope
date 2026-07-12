import { getData, postData, putData } from './client'

const REPORT_TIMEOUT_MS = Number(import.meta.env.VITE_REPORT_TIMEOUT || 180000)

export const fetchAdminOverview = () => getData('/admin/data-overview')
export const fetchDataVolumeTrend = () => getData('/admin/data-volume-trend')
export const fetchPipelineStatus = () => getData('/admin/pipeline-status')
export const fetchDatasets = () => getData('/admin/datasets')
export const fetchDataLineage = () => getData('/admin/data-lineage')
export const fetchAdminEvents = (params = {}) => getData('/admin/events', params)
export const fetchDwdEvents = (params = {}) => getData('/admin/dwd-events', params)
export const fetchDwsMetrics = (params = {}) => getData('/admin/dws-metrics', params)
export const fetchAdminJobs = () => getData('/admin/jobs')
export const fetchAdminJobRuns = () => getData('/admin/job-runs')
export const executeAdminJob = (jobCode, bizDate, payload = {}) => {
  const config = {}
  if (jobCode === 'report_generate') {
    config.timeout = REPORT_TIMEOUT_MS
  }
  return postData(`/admin/jobs/${jobCode}/execute`, { biz_date: bizDate, ...payload }, config)
}
export const retryAdminJobRun = (runId) => postData(`/admin/job-runs/${runId}/retry`)
export const fetchAdminJobLogs = (runId) => getData(`/admin/job-runs/${runId}/logs`)
export const fetchQualityOverview = () => getData('/admin/quality/overview')
export const fetchQualityIssues = () => getData('/admin/quality/issues')
export const fetchAuditLogs = () => getData('/admin/audit-logs')
export const fetchQualityRules = () => getData('/admin/quality/rules')
export const createQualityRule = (rule) => postData('/admin/quality/rules', rule)
export const updateQualityRule = (ruleId, payload) => putData(`/admin/quality/rules/${ruleId}`, payload)
