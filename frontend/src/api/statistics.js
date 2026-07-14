/**
 * statistics.js —— 统计分析模块数据请求 API 定义
 * 
 * 包含：
 *   - fetchAnalyticsTrend: 获取近30天系统运行吞吐与成功率/耗时趋势。
 *   - fetchAnalyticsErrors: 获取异常分布率。
 *   - fetchAnalyticsAgentStats: 智能体时延占比和消耗统计。
 */

import { getData } from './client'

// 获取 30 天运行数据趋势
export const fetchAnalyticsTrend = () => getData('/analytics/trend')

// 获取系统错误分布统计，支持 params 过滤条件（如 limit, start_date, end_date）
export const fetchAnalyticsErrors = (params) => getData('/analytics/errors', params)

// 获取智能体历史总体耗时和效能指标
export const fetchAnalyticsAgentStats = () => getData('/analytics/agent-stats')
