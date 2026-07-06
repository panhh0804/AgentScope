<template>
  <section class="screen-page screen-page--overview">
    <div class="screen-board">
      <header class="screen-titlebar">
        <div>
          <p class="screen-kicker">实时链路与离线链路双总览</p>
          <h2>AgentScope 多智能体运行监测与效能分析平台</h2>
        </div>
        <div class="screen-tools">
          <a-button type="outline" size="large" @click="load">刷新</a-button>
          <a-button :type="activeSubTab === 'realtime' ? 'primary' : 'outline'" size="large" @click="activeSubTab = 'realtime'">实时大盘</a-button>
          <a-button type="outline" size="large" @click="goBack" style="color: #22d3ee; border-color: rgba(34, 211, 238, 0.45);">返回后台</a-button>
          <a-button type="primary" size="large" @click="alertOpen = true">当前告警 {{ realtimeAlerts.length }}</a-button>
        </div>
      </header>

      <!-- Tab Content Container -->
      <div class="overview-tab-container">
        <!-- Tab 1: Realtime Board -->
        <div v-if="activeSubTab === 'realtime'" class="tab-content-wrapper">

      <!-- Compact realtime stats bar -->
      <div class="rt-stats-bar">
        <div v-for="metric in realtimeMetrics" :key="metric.label" class="rt-stat-item">
          <span class="rt-stat-label">{{ metric.label }}</span>
          <strong class="rt-stat-value">{{ metric.value }}</strong>
          <small class="rt-stat-hint">{{ metric.hint }}</small>
        </div>
      </div>

      <section class="screen-layout overview-grid">
        <!-- 1. Real-time Event Stream (Takes full height of stream area) -->
        <article class="screen-panel terminal-log-panel overview-grid__stream">
          <div class="screen-panel-head">
            <h3>实时数据流</h3>
            <span class="pulse-badge">LIVE STREAMING</span>
          </div>
          <div ref="terminalRef" class="terminal-log-container stream-cards-container">
            <TransitionGroup name="list" tag="div">
              <div v-for="log in realtimeLogs" :key="log.id" class="stream-event-card">
                <div :class="['event-icon-wrapper', log.level]">
                  <component :is="getEventIcon(log.agent, log.level)" :size="14" />
                </div>
                <div class="event-card-body">
                  <div class="event-card-meta">
                    <span class="event-agent-tag">{{ log.agent }}</span>
                    <span :class="['event-level-badge', log.level]">{{ log.level.toUpperCase() }}</span>
                    <span class="event-time-stamp">{{ log.time }}</span>
                  </div>
                  <p class="event-message-text">{{ log.message }}</p>
                </div>
                <div v-if="log.metric" class="event-card-metric">
                  <span v-if="log.metric.latency">{{ log.metric.latency }}ms</span>
                  <span v-if="log.metric.tokens">{{ log.metric.tokens }} tk</span>
                </div>
              </div>
            </TransitionGroup>
          </div>
        </article>

        <!-- 2. Throughput Chart -->
        <article class="screen-panel hero-panel overview-grid__throughput">
          <div class="screen-panel-head">
            <h3>实时吞吐 / 失败趋势</h3>
            <span>last 60 seconds</span>
          </div>
          <div ref="throughputChart" class="screen-chart large"></div>
        </article>

        <!-- 3. Realtime Alerts Ticker -->
        <article class="screen-panel compact overview-grid__alerts">
          <div class="screen-panel-head">
            <h3>实时告警</h3>
            <span>{{ realtimeAlerts.length }} open</span>
          </div>
          <div class="alert-ticker">
            <div v-for="alert in realtimeAlerts" :key="alert.alert_id" class="ticker-item">
              <span :class="['level-dot', alert.level]">{{ alert.level }}</span>
              <strong>{{ formatAlertType(alert.alert_type) }}</strong>
              <small>{{ alert.agent_id }} / {{ alert.create_time }}</small>
            </div>
          </div>
        </article>

        <!-- 4. Latency Trend Chart -->
        <article class="screen-panel hero-panel overview-grid__latency">
          <div class="screen-panel-head">
            <h3>平均时延趋势</h3>
            <span>avg latency ms</span>
          </div>
          <div ref="latencyChart" class="screen-chart large"></div>
        </article>

        <!-- 5. Agent Communication Topology -->
        <article class="screen-panel overview-grid__relation">
          <div class="screen-panel-head">
            <h3>协作关系图</h3>
            <span>{{ relationGraph.nodes?.length || 0 }} nodes</span>
          </div>
          <div ref="relationChart" class="screen-chart" style="height: 260px;"></div>
        </article>

        <!-- 6. Agent live rankings (Dedicated Flat Card) -->
        <article class="screen-panel agent-rank-panel overview-grid__agent_rank">
          <div class="screen-panel-head">
            <h3>Agent 监控与实时排行</h3>
            <span>{{ realtimeAgents.length }} agents</span>
          </div>
          <div class="agent-rank-compact">
            <div v-for="(agent, index) in sortedAgents" :key="agent.agent_id" class="agent-rank-row">
              <span class="rank-badge">#{{ index + 1 }}</span>
              <div class="agent-rank-main">
                <strong>{{ agent.agent_id }}</strong>
                <small>{{ agent.current_task }}</small>
              </div>
              <span :class="['tag', agent.status]">{{ agent.status }}</span>
              
              <div class="agent-rank-metrics">
                <div class="metric-mini">
                  <span class="m-val">{{ percent(agent.success_rate) }}</span>
                  <span class="m-lbl">成功率</span>
                </div>
                <div class="metric-mini">
                  <span class="m-val">{{ Math.round(agent.avg_latency_ms || 0) }}ms</span>
                  <span class="m-lbl">时延</span>
                </div>
                <div class="metric-mini">
                  <span class="m-val">{{ formatCompact(agent.token_total) }}</span>
                  <span class="m-lbl">Tokens</span>
                </div>
                <div class="metric-mini" :class="{ 'has-retries': agent.retry_count > 0 }">
                  <span class="m-val">{{ agent.retry_count }}</span>
                  <span class="m-lbl">重试</span>
                </div>
              </div>
            </div>
          </div>
        </article>

        <!-- 7. Communication bottlenecks diagnostics -->
        <article class="screen-panel overview-grid__diagnostics">
          <div class="screen-panel-head">
            <h3>Agent 协作及拥堵诊断</h3>
            <span>communication diagnostics</span>
          </div>
          <div class="diagnostics-list">
            <div v-for="link in sortedRelations" :key="link.source + '-' + link.target" class="diagnostic-row">
              <div class="route-info">
                <span class="agent-name">{{ formatAgentName(link.source) }}</span>
                <span class="arrow">➔</span>
                <span class="agent-name">{{ formatAgentName(link.target) }}</span>
                <span :class="['latency-badge', getLatencyLevel(link.avg_latency_ms)]">
                  {{ link.avg_latency_ms }} ms
                </span>
              </div>
              <div class="progress-bar-wrap">
                <div 
                  class="progress-bar-fill" 
                  :class="getLatencyLevel(link.avg_latency_ms)"
                  :style="{ width: Math.min(100, (link.avg_latency_ms / 3000) * 100) + '%' }"
                ></div>
              </div>
              <div class="route-stats">
                <span>交互次数: <b>{{ link.call_count }}</b> 次</span>
                <span>失败次数: <b :class="{ 'has-failed': link.failed_count > 0 }">{{ link.failed_count }}</b> 次</span>
              </div>
            </div>
          </div>
        </article>

        <!-- 8. Pipeline Ingress monitor -->
        <article class="screen-panel overview-grid__bigdata">
          <div class="screen-panel-head">
            <h3>大数据链路监控</h3>
            <span>pipeline monitor</span>
          </div>
          <div class="bigdata-link-monitor">
            <div v-for="item in bigDataLinkStatus" :key="item.name" class="bigdata-link-row">
              <div>
                <strong>{{ item.name }}</strong>
                <small>{{ item.hint }}</small>
              </div>
              <span :class="['link-status-badge', item.status]">{{ item.statusLabel }}</span>
              <b>{{ item.metric }}</b>
            </div>
          </div>
        </article>
      </section>
        </div>

      </div>
    </div>

    <a-modal v-model:visible="alertOpen" title="告警详情" width="920px" :footer="false">
      <div class="screen-table-wrap modal-table-wrap">
        <table class="data-table screen-native-table">
          <thead>
            <tr>
              <th>等级</th>
              <th>类型</th>
              <th>Agent</th>
              <th>当前值</th>
              <th>阈值</th>
              <th>时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="alert in allAlerts" :key="alert.alert_id">
              <td><span :class="['tag', alert.level]">{{ alert.level }}</span></td>
              <td>{{ formatAlertType(alert.alert_type) }}</td>
              <td>{{ alert.agent_id }}</td>
              <td>{{ alert.current_value }}</td>
              <td>{{ alert.threshold ?? alert.threshold_value }}</td>
              <td>{{ alert.create_time }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </a-modal>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { Cpu, Search, Compass, FileText, ShieldAlert, AlertTriangle, AlertCircle, Info } from '@lucide/vue'
import ChartPanel from '../components/ChartPanel.vue'
import { fetchAgentRankings, fetchDailyMetrics, fetchAgents, fetchHistoryAlerts, fetchOverview, fetchRealtimeAlerts, fetchRelationGraph, fetchReports, fetchTrend, fetchReportDetail } from '../api/dashboard'
import { barOption, graphOption, lineOption } from '../charts/options'
import { excerptMarkdown, parseMarkdownSections } from '../utils/markdown'
const router = useRouter()
const realtimeOverview = ref({})
const realtimeTrend = ref([])
const realtimeAgents = ref([])
const sortedAgents = computed(() => {
  return [...realtimeAgents.value].sort((a, b) => b.success_rate - a.success_rate)
})
const realtimeAlerts = ref([])
const dailyMetrics = ref([])
const historyRankings = ref([])
const relationGraph = ref({ nodes: [], links: [] })
const historyAlerts = ref([])
const reports = ref([])

const getTodayString = () => {
  const d = new Date()
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const dateRange = ref(['2026-06-01', getTodayString()])
const alertOpen = ref(false)
const activeSubTab = ref('realtime')
const agentTableRef = ref(null)
const historyChartsRef = ref(null)

const throughputChart = ref(null)
const latencyChart = ref(null)
const relationChart = ref(null)

const realtimeLogs = ref([])
const terminalRef = ref(null)

const logTemplates = [
  { agent: 'planner_agent', level: 'info', message: '收到用户请求，开始进行全局任务规划与子任务链拆解。', metric: null },
  { agent: 'planner_agent', level: 'info', message: '成功生成子任务规划，生成任务执行拓扑链: [search -> analysis -> writer -> reviewer]。', metric: null },
  { agent: 'search_agent', level: 'info', message: '启动搜索引擎检索，分析关键词: "agentscope multi-agent framework"。', metric: null },
  { agent: 'search_agent', level: 'info', message: '检索查询响应成功，共拉取到 8 条最相关的网页数据。', metric: { latency: 120 } },
  { agent: 'analysis_agent', level: 'info', message: '开始对检索拉取的文档内容进行分析摘要与核心信息抽取。', metric: null },
  { agent: 'analysis_agent', level: 'info', message: '核心知识和文本片段提取成功，已生成清洗后的结构化 JSON 数据。', metric: { tokens: 1250 } },
  { agent: 'writer_agent', level: 'info', message: '开始根据提取的上下文材料，调用 LLM 撰写报告首章。', metric: null },
  { agent: 'writer_agent', level: 'info', message: '报告首章草稿撰写成功，已渲染 Markdown 节点。', metric: { tokens: 2400 } },
  { agent: 'writer_agent', level: 'info', message: '所有报告章节撰写完毕，提交给 Reviewer 角色执行审核流程。', metric: null },
  { agent: 'reviewer_agent', level: 'info', message: '开始对提交的报告内容进行深度校验（包含敏感性校验、事实准确性校验和逻辑完备度校验）。', metric: null },
  { agent: 'reviewer_agent', level: 'info', message: '审核完毕，所有安全及格式校验点全部通过，可以安全发布。', metric: null },
  { agent: 'planner_agent', level: 'info', message: '任务链 trace_demo_101 整体执行完毕，数据已持久化并提交至 Hive 归档。', metric: { latency: 5400 } },
  { agent: 'search_agent', level: 'warn', message: '检测到外部网络检索 API 响应延迟偏高，将自动开启连接池扩容。', metric: { latency: 3400 } },
  { agent: 'writer_agent', level: 'warn', message: 'LLM 生成响应出现潜在截断风险，将自动进行单次请求重试以恢复生成。', metric: null },
  { agent: 'search_agent', level: 'error', message: '连接检索服务超时，连接失败。将自动触发第 1 次故障自愈重试。', metric: { latency: 5000 } },
  { agent: 'search_agent', level: 'info', message: '故障重试成功，搜索引擎服务连接已自动恢复。', metric: null }
]

const getEventIcon = (agent, level) => {
  if (level === 'error') return AlertCircle
  if (level === 'warn') return AlertTriangle
  
  switch (agent) {
    case 'planner_agent': return Compass
    case 'search_agent': return Search
    case 'analysis_agent': return Cpu
    case 'writer_agent': return FileText
    case 'reviewer_agent': return ShieldAlert
    default: return Info
  }
}

const addLog = (logObj = null) => {
  const d = new Date()
  const timeStr = `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`
  const idStr = Math.random().toString(36).substring(2, 9)
  
  let entry
  if (logObj) {
    entry = { id: idStr, time: timeStr, ...logObj }
  } else {
    const template = logTemplates[Math.floor(Math.random() * logTemplates.length)]
    entry = {
      id: idStr,
      time: timeStr,
      agent: template.agent,
      level: template.level,
      message: template.message,
      metric: template.metric
    }
  }
  
  realtimeLogs.value.push(entry)
  if (realtimeLogs.value.length > 50) {
    realtimeLogs.value.shift()
  }
  
  nextTick(() => {
    if (terminalRef.value) {
      terminalRef.value.scrollTop = terminalRef.value.scrollHeight
    }
  })
}

let logTimer
let pollTimer

let throughputInstance
let latencyInstance
let relationInstance

const dailySummary = computed(() => {
  const rows = dailyMetrics.value
  const taskCount = rows.reduce((sum, row) => sum + Number(row.task_count || 0), 0)
  const successCount = rows.reduce((sum, row) => sum + Number(row.success_count || 0), 0)
  const successRate = taskCount > 0 ? successCount / taskCount : 0
  const avgLatency = rows.length ? rows.reduce((sum, row) => sum + Number(row.avg_latency_ms || 0), 0) / rows.length : 0
  const p95Latency = rows.length ? rows.reduce((sum, row) => sum + Number(row.p95_latency_ms || 0), 0) / rows.length : 0
  const tokens = rows.reduce((sum, row) => sum + Number(row.total_tokens || 0), 0)
  return { taskCount, successRate, avgLatency, p95Latency, tokens }
})

const latestReport = computed(() => reports.value[0] || {})

const reportSections = computed(() => parseMarkdownSections(latestReport.value.content || ''))

const reportPreviewSections = computed(() => reportSections.value.slice(0, 2))

const reportIntro = computed(() => {
  const content = cleanReportIntroSource(latestReport.value.content)
  return content ? excerptMarkdown(content, 150) : '生成结果会以卡片方式展示，方便快速阅读和定位重点。'
})

const alertTypeLabels = {
  high_latency: '高时延',
  frequent_retry: '频繁重试',
  token_limit: 'Token 限制',
  token_overuse: 'Token 超量'
}

// Kept for backward compatibility (not used in template anymore)
const metrics = computed(() => [
  { label: '运行任务', value: realtimeOverview.value.running_tasks ?? '-', hint: '实时处理中的任务' },
  { label: '活跃 Agent', value: realtimeOverview.value.active_agents ?? '-', hint: '当前在线角色数' },
  { label: '事件吞吐 / 分钟', value: realtimeOverview.value.events_per_minute ?? '-', hint: '实时事件输入速率' },
  { label: '实时成功率', value: percent(realtimeOverview.value.success_rate), hint: `错误率 ${percent(realtimeOverview.value.error_rate)}` },
  { label: '平均时延', value: `${Math.round(realtimeOverview.value.avg_latency_ms || 0)} ms`, hint: '实时窗口统计' },
])

// Compact horizontal stats bar — realtime only
const realtimeMetrics = computed(() => [
  { label: '运行任务', value: realtimeOverview.value.running_tasks ?? '-', hint: '运行任务数' },
  { label: '活跃 Agent', value: realtimeOverview.value.active_agents ?? '-', hint: '在线角色' },
  { label: '事件吞吐', value: `${realtimeOverview.value.events_per_minute ?? '-'} /min`, hint: '实时输入' },
  { label: '实时成功率', value: percent(realtimeOverview.value.success_rate), hint: `错误率 ${percent(realtimeOverview.value.error_rate)}` },
  { label: '平均时延', value: `${Math.round(realtimeOverview.value.avg_latency_ms || 0)} ms`, hint: '时延窗口' },
  { label: '5m Token 消耗', value: formatNumber(realtimeOverview.value.token_total_5m), hint: '近 5 分钟' },
  { label: '5m 估算成本', value: `$${Number(realtimeOverview.value.estimated_cost_5m || 0).toFixed(4)}`, hint: '近 5 分钟' },
  { label: '告警数', value: realtimeAlerts.value.length, hint: '未处理告警' }
])

const historyTaskOption = computed(() => historyLineOption('每日任务量', [
  { name: '任务数', type: 'line', smooth: true, data: dailyMetrics.value.map((item) => item.task_count), itemStyle: { color: '#3b82f6' }, lineStyle: { width: 3 }, areaStyle: { color: 'rgba(59, 130, 246, 0.08)' } }
]))

const historySuccessOption = computed(() => historyLineOption('每日成功率', [
  { name: '成功率', type: 'line', smooth: true, data: dailyMetrics.value.map((item) => Number(item.success_rate) * 100), itemStyle: { color: '#10b981' }, lineStyle: { width: 3 }, areaStyle: { color: 'rgba(16, 185, 129, 0.08)' } }
]))

const historyLatencyOption = computed(() => historyLineOption('平均 / P95 时延', [
  { name: '平均时延', type: 'line', smooth: true, data: dailyMetrics.value.map((item) => item.avg_latency_ms), itemStyle: { color: '#06b6d4' }, lineStyle: { width: 3 } },
  { name: 'P95 时延', type: 'line', smooth: true, data: dailyMetrics.value.map((item) => item.p95_latency_ms), itemStyle: { color: '#f97316' }, lineStyle: { width: 3 } }
]))

const historyRankingOption = computed(() => barOption(
  'Agent 执行次数排行',
  historyRankings.value.map((item) => item.agent_role),
  historyRankings.value.map((item) => item.execution_count),
  '执行次数'
))

const allAlerts = computed(() => [...realtimeAlerts.value, ...historyAlerts.value])

const sortedRelations = computed(() => {
  return [...(relationGraph.value.links || [])].sort((a, b) => b.avg_latency_ms - a.avg_latency_ms)
})

const bigDataLinkStatus = computed(() => [
  {
    name: '实时采集',
    status: Number(realtimeOverview.value.events_per_minute || 0) > 0 ? 'normal' : 'warning',
    statusLabel: Number(realtimeOverview.value.events_per_minute || 0) > 0 ? 'RUNNING' : 'IDLE',
    metric: `${realtimeOverview.value.events_per_minute ?? '-'} /min`,
    hint: 'Kafka / event ingress'
  },
  {
    name: '流式计算',
    status: Number(realtimeOverview.value.error_rate || 0) > 0.08 ? 'warning' : 'normal',
    statusLabel: Number(realtimeOverview.value.error_rate || 0) > 0.08 ? 'CHECK' : 'OK',
    metric: percent(1 - Number(realtimeOverview.value.error_rate || 0)),
    hint: 'Spark Streaming window'
  },
  {
    name: '离线指标',
    status: dailyMetrics.value.length > 0 ? 'normal' : 'warning',
    statusLabel: dailyMetrics.value.length > 0 ? 'READY' : 'WAIT',
    metric: formatNumber(dailySummary.value.taskCount),
    hint: 'DWS daily metrics'
  },
  {
    name: '告警链路',
    status: realtimeAlerts.value.length > 0 ? 'warning' : 'normal',
    statusLabel: realtimeAlerts.value.length > 0 ? 'OPEN' : 'CLEAR',
    metric: `${realtimeAlerts.value.length} open`,
    hint: 'rules / notification'
  }
])

function formatAgentName(name) {
  return String(name || '').replace('_agent', '').toUpperCase()
}

function getLatencyLevel(ms) {
  if (ms < 1000) return 'normal'
  if (ms < 2000) return 'warning'
  return 'critical'
}

function percent(value) {
  return `${Number((value || 0) * 100).toFixed(1)}%`
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString()
}

function formatCompact(value) {
  return Intl.NumberFormat('en', { notation: 'compact', maximumFractionDigits: 1 }).format(Number(value || 0))
}

function getDateValue(value, fallback) {
  if (!value) return fallback
  if (typeof value === 'string') return value
  if (typeof value?.format === 'function') return value.format('YYYY-MM-DD')
  return fallback
}

function formatShortDate(value) {
  return String(value || '').slice(5, 10) || value
}

function formatAlertType(value) {
  return alertTypeLabels[value] || value
}

function cleanReportIntroSource(value) {
  return String(value || '')
    .replace(/%[（(]\s*\/\s*[）)]/g, '')
    .replace(/[（(]\s*\/\s*[）)]/g, '')
    .replace(/\s+/g, ' ')
    .trim()
}

function historyTooltipFormatter(params) {
  const rows = Array.isArray(params) ? params : [params]
  const date = dailyMetrics.value[rows[0]?.dataIndex]?.metric_date || rows[0]?.axisValue || ''
  const lines = rows.map((item) => `${item.marker}${item.seriesName}: ${item.value}`)
  return [date, ...lines].join('<br/>')
}

function historyLineOption(title, series) {
  const option = lineOption(title, dailyMetrics.value.map((item) => formatShortDate(item.metric_date)), series)
  option.tooltip = { ...option.tooltip, trigger: 'axis', formatter: historyTooltipFormatter }
  option.grid = { ...option.grid, right: 34, bottom: 32, containLabel: true }
  option.xAxis = { ...option.xAxis, boundaryGap: ['4%', '8%'] }
  return option
}

function baseAxis() {
  return {
    axisLabel: { color: '#9bc7d9' },
    axisLine: { lineStyle: { color: '#46627d' } },
    splitLine: { lineStyle: { color: 'rgba(139, 205, 235, 0.14)' } }
  }
}

function setLineOption(chart, title, xData, series) {
  chart.setOption(lineOption(title, xData, series), true)
}

function renderRealtimeCharts() {
  if (!throughputChart.value || !latencyChart.value) return
  throughputInstance ||= echarts.init(throughputChart.value)
  latencyInstance ||= echarts.init(latencyChart.value)

  const xRealtime = realtimeTrend.value.map((item) => String(item.time || '').slice(11, 19))
  setLineOption(throughputInstance, '最近 60 秒吞吐', xRealtime, [
    {
      name: '事件数',
      type: 'line',
      smooth: true,
      data: realtimeTrend.value.map((item) => item.events),
      areaStyle: { color: 'rgba(34, 211, 238, 0.12)' },
      itemStyle: { color: '#22d3ee' },
      lineStyle: { width: 2 }
    },
    { name: '失败数', type: 'line', smooth: true, data: realtimeTrend.value.map((item) => item.failed), itemStyle: { color: '#fb7185' }, lineStyle: { width: 2 } }
  ])

  setLineOption(latencyInstance, '平均时延趋势', xRealtime, [
    { name: '平均时延 ms', type: 'line', smooth: true, data: realtimeTrend.value.map((item) => item.avg_latency_ms), itemStyle: { color: '#4ade80' }, lineStyle: { width: 2 } }
  ])
}

function renderCharts() {
  renderRealtimeCharts()
  if (!relationChart.value) return
  relationInstance ||= echarts.init(relationChart.value)

  const relationOption = graphOption(relationGraph.value)
  const relationSeries = relationOption.series?.[0]
  if (relationSeries) {
    relationSeries.label = { ...relationSeries.label, fontSize: 10, color: '#f8fafc' }
    relationSeries.force = { ...relationSeries.force, repulsion: 260, edgeLength: 145 }
    relationSeries.data = (relationSeries.data || []).map((node) => ({
      ...node,
      symbolSize: Math.max(28, Math.min(64, Number(node.symbolSize || node.value || 32) * 0.82))
    }))
    relationSeries.links = (relationSeries.links || []).map((link) => ({
      ...link,
      lineStyle: {
        ...(link.lineStyle || {}),
        color: 'rgba(56, 189, 248, 0.72)',
        opacity: 0.85,
        width: Math.max(1.5, link.lineStyle?.width || 1.5)
      }
    }))
  }
  relationInstance.setOption(relationOption, true)
}

function resizeCharts() {
  throughputInstance?.resize()
  latencyInstance?.resize()
  relationInstance?.resize()
}

function scrollToHistory() {
  historyChartsRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function scrollToAgents() {
  agentTableRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function goBack() {
  if (window.opener || window.history.length <= 1) {
    window.close()
  } else {
    router.push('/data-overview')
  }
}

async function load() {
  const [startDate, endDate] = [getDateValue(dateRange.value?.[0], '2026-06-01'), getDateValue(dateRange.value?.[1], getTodayString())]
  const [realtimeOverviewData, realtimeTrendData, agentsData, realtimeAlertData, dailyData, rankingData, relationData, historyAlertData, reportsData] = await Promise.all([
    fetchOverview(),
    fetchTrend(60),
    fetchAgents(),
    fetchRealtimeAlerts(),
    fetchDailyMetrics(startDate, endDate),
    fetchAgentRankings(endDate),
    fetchRelationGraph(endDate),
    fetchHistoryAlerts(endDate),
    fetchReports()
  ])
  realtimeOverview.value = realtimeOverviewData
  realtimeTrend.value = realtimeTrendData
  realtimeAgents.value = agentsData
  realtimeAlerts.value = realtimeAlertData
  dailyMetrics.value = dailyData
  historyRankings.value = rankingData
  relationGraph.value = relationData
  historyAlerts.value = historyAlertData
  
  if (reportsData && reportsData.length > 0) {
    try {
      const detail = await fetchReportDetail(reportsData[0].report_id)
      reports.value = [detail, ...reportsData.slice(1)]
    } catch (err) {
      console.error('Failed to load latest report detail', err)
      reports.value = reportsData
    }
  } else {
    reports.value = []
  }

  await nextTick()
  renderCharts()
}

onMounted(async () => {
  await load()
  
  // Seed initial logs
  for (let i = 0; i < 8; i++) {
    const d = new Date(Date.now() - (8 - i) * 5000)
    const timeStr = `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`
    const template = logTemplates[i % logTemplates.length]
    addLog({
      time: timeStr,
      agent: template.agent,
      level: template.level,
      message: template.message,
      metric: template.metric
    })
  }
  
  logTimer = setInterval(() => {
    addLog()
  }, 3000)
  
  pollTimer = setInterval(async () => {
    try {
      const [realtimeOverviewData, realtimeTrendData, agentsData, realtimeAlertData] = await Promise.all([
        fetchOverview(),
        fetchTrend(60),
        fetchAgents(),
        fetchRealtimeAlerts()
      ])
      realtimeOverview.value = realtimeOverviewData
      realtimeTrend.value = realtimeTrendData
      realtimeAgents.value = agentsData
      realtimeAlerts.value = realtimeAlertData
      await nextTick()
      renderRealtimeCharts()
    } catch (e) {
      console.error('Failed to poll realtime data', e)
    }
  }, 1000)
  
  window.addEventListener('resize', resizeCharts)
})

onBeforeUnmount(() => {
  clearInterval(logTimer)
  clearInterval(pollTimer)
  window.removeEventListener('resize', resizeCharts)
  throughputInstance?.dispose()
  latencyInstance?.dispose()
  relationInstance?.dispose()
})
</script>
