const agents = ['planner', 'search', 'analysis', 'writer', 'reviewer']

function isoMinutes(offset = 0) {
  const date = new Date(Date.now() + offset * 60 * 1000)
  date.setSeconds(0, 0)
  return date.toISOString().slice(0, 16)
}

export function mockOverview() {
  return {
    running_tasks: 18,
    active_agents: 5,
    events_per_minute: 126,
    success_rate: 0.934,
    error_rate: 0.066,
    avg_latency_ms: 1840,
    token_total_5m: 48230,
    estimated_cost_5m: 0.0832,
    retry_tasks: 3,
    open_alerts: 4,
    updated_at: new Date().toISOString().slice(0, 19)
  }
}

export function mockTrend(minutes = 60) {
  return Array.from({ length: Math.min(minutes, 60) }, (_, index) => ({
    time: isoMinutes(index - Math.min(minutes, 60) + 1),
    events: 80 + (index * 7) % 55,
    success: 70 + (index * 5) % 45,
    failed: 3 + index % 8,
    avg_latency_ms: 1200 + (index * 113) % 2200
  }))
}

export function mockAgents() {
  return agents.map((role, index) => ({
    agent_id: `${role}_agent`,
    agent_role: role,
    status: ['running', 'running', 'idle', 'running', 'retry'][index],
    current_task: `trace_demo_${String(index + 1).padStart(3, '0')}`,
    success_rate: Number((0.94 - index * 0.013).toFixed(3)),
    avg_latency_ms: 900 + index * 430,
    token_total: 12000 + index * 6800,
    retry_count: index % 3,
    last_event_time: new Date().toISOString().slice(0, 19)
  }))
}

export function mockRealtimeAlerts() {
  const now = new Date()
  return [
    {
      alert_id: 'alert_demo_latency',
      alert_type: 'high_latency',
      level: 'warning',
      agent_id: 'writer_agent',
      current_value: 12800,
      threshold: 10000,
      source: 'streaming',
      status: 'open',
      created_at: new Date(now.getTime() - 3 * 60 * 1000).toISOString().slice(0, 19)
    },
    {
      alert_id: 'alert_demo_retry',
      alert_type: 'frequent_retry',
      level: 'critical',
      agent_id: 'reviewer_agent',
      current_value: 4,
      threshold: 3,
      source: 'streaming',
      status: 'open',
      created_at: new Date(now.getTime() - 6 * 60 * 1000).toISOString().slice(0, 19)
    },
    {
      alert_id: 'alert_demo_recovery',
      alert_type: 'stream_recovery',
      level: 'info',
      agent_id: 'spark_streaming',
      current_value: 1,
      threshold: 1,
      source: 'streaming',
      status: 'open',
      created_at: new Date(now.getTime() - 9 * 60 * 1000).toISOString().slice(0, 19)
    }
  ]
}

export function mockDailyMetrics(startDate = '2026-06-01', endDate = '2026-06-24') {
  const start = new Date(`${startDate}T00:00:00`)
  const end = new Date(`${endDate}T00:00:00`)
  const days = Math.max(1, Math.round((end - start) / 86400000) + 1)
  return Array.from({ length: days }, (_, index) => {
    const date = new Date(start.getTime() + index * 86400000).toISOString().slice(0, 10)
    return {
      metric_date: date,
      task_count: 1000 + index * 82,
      success_count: 920 + index * 75,
      failed_count: 80 + index * 7,
      success_rate: Number((0.91 + (index % 5) * 0.008).toFixed(3)),
      avg_latency_ms: 1600 + index * 60,
      p95_latency_ms: 4100 + index * 90,
      total_tokens: 1200000 + index * 95000,
      estimated_cost_usd: Number((2.4 + index * 0.18).toFixed(4))
    }
  })
}

export function mockHourlyMetrics() {
  return Array.from({ length: 24 }, (_, hour) => ({
    hour,
    task_count: 36 + hour * 2,
    success_rate: Number((0.9 + (hour % 6) * 0.01).toFixed(3)),
    avg_latency_ms: 1100 + (hour * 137) % 1800,
    total_tokens: 30000 + hour * 4200
  }))
}

export function mockRankings(date = '2026-06-24') {
  return agents.map((role, index) => ({
    metric_date: date,
    agent_id: `${role}_agent`,
    agent_role: role,
    execution_count: 1200 - index * 95,
    success_rate: Number((0.94 - index * 0.015).toFixed(3)),
    avg_latency_ms: 980 + index * 520,
    p95_latency_ms: 2600 + index * 900,
    total_tokens: 210000 + index * 78000,
    estimated_cost_usd: Number((0.48 + index * 0.17).toFixed(4))
  }))
}

export function mockRelationGraph(date = '2026-06-24') {
  return {
    metric_date: date,
    nodes: agents.map((role, index) => ({ id: `${role}_agent`, name: role[0].toUpperCase() + role.slice(1), value: 100 - index * 9 })),
    links: agents.slice(0, -1).map((role, index) => ({
      source: `${role}_agent`,
      target: `${agents[index + 1]}_agent`,
      call_count: 900 - index * 70,
      avg_latency_ms: 1200 + index * 330,
      failed_count: index * 8,
      total_tokens: 80000 + index * 32000
    }))
  }
}

export function mockHistoryAlerts(date = '2026-06-24') {
  return [
    ['high_error_rate', 'warning', 'search_agent', 0.24, 0.2],
    ['high_p95_latency', 'warning', 'writer_agent', 12400, 10000],
    ['high_cost_task', 'info', 'analysis_agent', 0.72, 0.5]
  ].map(([alertType, level, agentId, currentValue, threshold], index) => ({
    alert_id: `hist_${date}_${index}`,
    metric_date: date,
    alert_type: alertType,
    level,
    agent_id: agentId,
    current_value: currentValue,
    threshold,
    source: 'batch',
    status: 'open'
  }))
}

export function mockReport(payload = {}) {
  const date = payload.report_date || '2026-06-24'
  return {
    report_id: `report_${date}`,
    report_date: date,
    report_type: payload.report_type || 'daily',
    created_at: new Date().toISOString().slice(0, 19),
    content: `# AgentScope ${date} 运行分析报告

## 总体结论

系统实时链路和离线分析链路均处于可观测状态。Planner、Search、Analysis、Writer、Reviewer 五类 Agent 均产生有效事件，整体成功率保持在 93% 左右。

## 主要异常

- Writer Agent 出现高延迟告警，P95 时延超过阈值。
- Reviewer Agent 存在频繁重试现象，需要关注任务回退逻辑。
- Search Agent 错误率略高，建议检查外部检索工具稳定性。

## 优化建议

1. 对 Writer Agent 增加超时保护和降级策略。
2. 对 Reviewer 重试次数设置硬阈值，避免疑似循环调用。
3. 将实时告警和历史告警统一纳入 AI 报告摘要。`
  }
}

export function mockReports() {
  return [mockReport({ report_date: '2026-06-24', report_type: 'daily' })]
}
