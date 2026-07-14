/**
 * dashboard.js —— 监控面板/实时大屏与系统运行自检数据 API 请求模块
 * 
 * 包含：
 *   - 实时流大屏 API: Overview, Trend, Agents, Alerts
 *   - 离线大盘报表 API: Daily, Hourly, Rankings, Graph, HistoryAlerts
 *   - AI 报告生成 API: generateReport, fetchReports, fetchReportDetail
 *   - 系统巡检自检 API: fetchSystemCheckRuns, runSystemCheck, fetchSystemRunningLog
 */

import { getData, postData } from './client'

// AI 诊断报告大模型调用的超时限制（默认 3 分钟）
const REPORT_TIMEOUT_MS = Number(import.meta.env.VITE_REPORT_TIMEOUT || 180000)

// === 1. 实时流大屏数据 ===
// 获取大盘全局概览与中间件健康状态矩阵
export const fetchOverview = () => getData('/realtime/overview')
// 获取实时吞吐与平均时延折线数据（默认过去 60 分钟）
export const fetchTrend = (minutes = 60) => getData('/realtime/trend', { minutes })
// 获取实时在线智能体实例的活动状态
export const fetchAgents = () => getData('/realtime/agents')
// 获取实时大屏积压告警
export const fetchRealtimeAlerts = () => getData('/realtime/alerts')

// === 2. 离线数仓多维指标 ===
// 获取起止日期之间的每日运行汇总
export const fetchDailyMetrics = (start_date, end_date) => getData('/metrics/daily', { start_date, end_date })
// 获取单日每小时流量分布
export const fetchHourlyMetrics = (date) => getData('/metrics/hourly', { date })
// 获取单日 Agent 效能排行
export const fetchAgentRankings = (date) => getData('/rankings/agents', { date })
// 获取单日 Agent 协作依赖网络关系拓扑图
export const fetchRelationGraph = (date) => getData('/graph/agent-relations', { date })
// 获取单日历史已归档告警记录
export const fetchHistoryAlerts = (date) => getData('/alerts/history', { date })

// === 3. AI 运维报告 ===
// 触发大模型或备用规则引擎生成系统运维分析报告，配置较长超时阈值
export const generateReport = (payload) => postData('/reports/generate', payload, { timeout: REPORT_TIMEOUT_MS })
// 获取已归档的诊断报告列表（摘要）
export const fetchReports = () => getData('/reports')
// 获取单个诊断报告的详细正文与指标快照
export const fetchReportDetail = (reportId) => getData(`/reports/${reportId}`)

// === 4. 系统诊断与自检 ===
// 获取历史完成的系统检查与benchmark流水
export const fetchSystemCheckRuns = () => getData('/admin/system/check-runs')
// 下发自检命令触发后台异步 SSH 诊断任务
export const runSystemCheck = (jobCode) => postData(`/admin/system/run-check?job_code=${jobCode}`, {})
// 获取自检巡检任务执行时的实时控制台标准 stdout 输出
export const fetchSystemRunningLog = () => getData('/admin/system/running-log')
