/**
 * admin.js —— 后端系统管理端 API 请求模块
 * 
 * 包含：
 *   - 运维大盘与血缘 API: fetchAdminOverview, fetchDataVolumeTrend, fetchPipelineStatus, fetchDatasets, fetchDataLineage
 *   - 任务调度流水与执行 API: fetchAdminJobs, fetchAdminJobRuns, executeAdminJob, retryAdminJobRun, fetchAdminJobLogs
 *   - 明细数据查询 API: fetchDwdEvents, fetchDwsMetrics, fetchAdminEvents
 *   - 数据质量与校验规则 API: fetchQualityOverview, fetchQualityIssues, fetchQualityRules, createQualityRule, updateQualityRule
 *   - 操作审计 API: fetchAuditLogs
 */

import { getData, postData, putData } from './client'

// AI 诊断报告生成大模型请求超时（3 分钟）
const REPORT_TIMEOUT_MS = Number(import.meta.env.VITE_REPORT_TIMEOUT || 180000)

// === 1. 运维总体卡片与血缘依赖 ===
// 获取运维端卡片数据中心概览
export const fetchAdminOverview = () => getData('/admin/data-overview')
// 获取 Raw 与 Clean 数据存储量历史占比对比趋势
export const fetchDataVolumeTrend = () => getData('/admin/data-volume-trend')
// 获取计算链路各环节的状态与吞吐量拓扑结构
export const fetchPipelineStatus = () => getData('/admin/pipeline-status')
// 获取系统管理的所有物理/逻辑数据集清单
export const fetchDatasets = () => getData('/admin/datasets')
// 获取系统的数据流向依赖血缘拓扑结构
export const fetchDataLineage = () => getData('/admin/data-lineage')

// === 2. 明细及聚合日志查询 ===
// 搜索拉取常规系统日志明细
export const fetchAdminEvents = (params = {}) => getData('/admin/events', params)
// 搜索拉取 DWD 清洗后的事件大表记录明细
export const fetchDwdEvents = (params = {}) => getData('/admin/dwd-events', params)
// 搜索拉取 DWS 离线汇总指标日分区大表明细
export const fetchDwsMetrics = (params = {}) => getData('/admin/dws-metrics', params)

// === 3. 调度作业管理 ===
// 获取系统中支持的全部任务调度项目列表
export const fetchAdminJobs = () => getData('/admin/jobs')
// 获取历史所有调度的任务运行流水历史
export const fetchAdminJobRuns = () => getData('/admin/job-runs')
// 手动下发执行特定的数据同步、Spark 计算、AI 诊断报告任务
export const executeAdminJob = (jobCode, bizDate, payload = {}) => {
  const config = {}
  if (jobCode === 'report_generate') {
    // 报告生成作业可能需要等待较长的时间
    config.timeout = REPORT_TIMEOUT_MS
  }
  return postData(`/admin/jobs/${jobCode}/execute`, { biz_date: bizDate, ...payload }, config)
}
// 重试失败的任务
export const retryAdminJobRun = (runId) => postData(`/admin/job-runs/${runId}/retry`)
// 查看特定作业流水的详细控制台 stdout 输出日志
export const fetchAdminJobLogs = (runId) => getData(`/admin/job-runs/${runId}/logs`)

// === 4. 数据质量管理 ===
// 获取今日全局质量校验规则与合格率概况
export const fetchQualityOverview = () => getData('/admin/quality/overview')
// 获取特定的数据校验异常样本合规拦截明细
export const fetchQualityIssues = () => getData('/admin/quality/issues')
// 获取当前系统中注册注册生效的校验规则 SQL 清单
export const fetchQualityRules = () => getData('/admin/quality/rules')
// 注册并新增一条数据质量校验 SQL 规则
export const createQualityRule = (rule) => postData('/admin/quality/rules', rule)
// 开启/禁用指定的质量校验 SQL 规则
export const updateQualityRule = (ruleId, payload) => putData(`/admin/quality/rules/${ruleId}`, payload)

// === 5. 平台审计日志 ===
// 获取操作审计追踪历史
export const fetchAuditLogs = () => getData('/admin/audit-logs')
