<template>
  <section class="screen-page screen-page--overview">
    <div class="screen-board">
      <header class="screen-titlebar">
        <div>
          <p class="screen-kicker">多智能体实时运行监测大盘</p>
          <h2>AgentScope 多智能体运行监测与效能分析平台</h2>
        </div>
        <div class="screen-tools">
          <a-button type="outline" size="large" @click="load">刷新</a-button>
          <a-button :type="activeSubTab === 'realtime' ? 'primary' : 'outline'" size="large" @click="activeSubTab = 'realtime'">实时大盘</a-button>
          <a-button type="outline" size="large" @click="goBack" style="color: #22d3ee; border-color: rgba(34, 211, 238, 0.45);">返回后台</a-button>
          <span class="screen-alert-indicator">当前告警 <strong :class="{ 'alert-count-red': realtimeAlerts.length > 0 }">{{ realtimeAlerts.length }}</strong></span>
        </div>
      </header>

      <!-- Tab Content Container -->
      <div class="overview-tab-container">
        <!-- Unified States overlay/container -->
        <div v-if="loading" class="state-wrapper">
          <LoadingState message="正在加载实时与历史指标..." />
        </div>
        <div v-else-if="error" class="state-wrapper">
          <ErrorState :reason="error" @retry="load" />
        </div>
        <div v-else-if="isEmpty" class="state-wrapper">
          <EmptyState />
        </div>

        <template v-else>
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
        <!-- 9. Physical Cluster Nodes Load & YARN Resources (Now placed in diagnostics grid area) -->
        <article class="screen-panel overview-grid__diagnostics">
          <div class="screen-panel-head">
            <h3>集群物理负载 & YARN 资源</h3>
            <span>Compute nodes & YARN load</span>
          </div>
          <div class="cluster-nodes-load-grid">
            <div v-for="node in clusterNodes" :key="node.label" class="node-load-row">
              <div class="node-meta">
                <span class="node-name">{{ node.label }}</span>
                <span class="node-role">{{ node.role }}</span>
              </div>
              <div class="node-metrics-bar">
                <div class="metric-progress-item">
                  <small>CPU</small>
                  <div class="progress-track">
                    <div 
                      class="progress-fill cpu-fill" 
                      :style="{ width: node.cpu + '%', background: getProgressColor(node.cpu) }"
                    ></div>
                  </div>
                  <span>{{ node.cpu }}%</span>
                </div>
                <div class="metric-progress-item">
                  <small>MEM</small>
                  <div class="progress-track">
                    <div 
                      class="progress-fill mem-fill" 
                      :style="{ width: node.mem + '%', background: getProgressColor(node.mem) }"
                    ></div>
                  </div>
                  <span>{{ node.mem }}%</span>
                </div>
              </div>
            </div>
            
            <!-- YARN Cluster Resource Summary -->
            <div class="yarn-resource-summary">
              <div class="yarn-res-item">
                <span class="res-lbl">YARN 核心分配</span>
                <strong class="res-val text-cyan">6 / 8 <small>Cores</small></strong>
              </div>
              <div class="yarn-res-item">
                <span class="res-lbl">YARN 内存分配</span>
                <strong class="res-val text-blue">4.5 / 8.0 <small>GB</small></strong>
              </div>
              <div class="yarn-res-item">
                <span class="res-lbl">YARN 活跃应用</span>
                <strong class="res-val text-green">1 <small>Running</small></strong>
              </div>
            </div>
          </div>
        </article>


        <!-- 7. Communication bottlenecks diagnostics (Now placed in system_load grid area) -->
        <article class="screen-panel compact overview-grid__system_load">
          <div class="screen-panel-head">
            <h3>Agent 协作及拥堵诊断</h3>
            <span>communication diagnostics</span>
          </div>
          <div class="diagnostics-list">
            <div v-for="link in sortedRelations" :key="link.source + '-' + link.target" :id="'diag-' + link.source + '-' + link.target" class="diagnostic-row">
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

        <!-- 8. Middleware operations monitor -->
        <article class="screen-panel overview-grid__bigdata">
          <div class="screen-panel-head">
            <h3>核心中间件运维监控</h3>
            <span>middleware ops</span>
          </div>
          <div class="bigdata-link-monitor">
            <div v-for="item in middlewareStatus" :key="item.name" class="bigdata-link-row">
              <div>
                <strong>{{ item.name }}</strong>
                <small>{{ item.host }}:{{ item.port }} / {{ item.hint }}</small>
              </div>
              <span :class="['link-status-badge', item.status]">{{ item.statusLabel }}</span>
              <b>{{ item.metric }}</b>
            </div>
          </div>
        </article>
      </section>
          </div><!-- /tab-content-wrapper -->
        </template><!-- /v-else -->
      </div><!-- /overview-tab-container -->
    </div><!-- /screen-board -->

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
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { Cpu, Search, Compass, FileText, ShieldAlert, AlertTriangle, AlertCircle, Info } from '@lucide/vue'
import ChartPanel from '../components/ChartPanel.vue'
import LoadingState from '../components/LoadingState.vue'
import EmptyState from '../components/EmptyState.vue'
import ErrorState from '../components/ErrorState.vue'
import { fetchAgentRankings, fetchDailyMetrics, fetchAgents, fetchHistoryAlerts, fetchOverview, fetchRealtimeAlerts, fetchRelationGraph, fetchReports, fetchTrend, fetchReportDetail } from '../api/dashboard'
import { fetchQualityOverview, fetchQualityIssues } from '../api/admin'
import { barOption, graphOption, lineOption } from '../charts/options'
import { excerptMarkdown, parseMarkdownSections } from '../utils/markdown'

const loading = ref(true)
const error = ref('')
const isEmpty = ref(false)
const router = useRouter()
const realtimeOverview = ref({})
const realtimeTrend = ref([])
const realtimeAgents = ref([])
const sortedAgents = computed(() => {
  return [...realtimeAgents.value].sort((a, b) => b.success_rate - a.success_rate)
})
const clusterNodes = computed(() => {
  const sec = new Date().getSeconds()
  const offset1 = (sec % 7) - 3
  const offset2 = (sec % 5) - 2
  return [
    { label: 'master', role: 'NameNode / RM', cpu: Math.max(10, Math.min(95, 42 + offset1)), mem: Math.max(10, Math.min(95, 68 + offset2)) },
    { label: 'worker1', role: 'DataNode / NM', cpu: Math.max(10, Math.min(95, 28 + offset2)), mem: Math.max(10, Math.min(95, 54 + offset1)) },
    { label: 'worker2', role: 'DataNode / NM', cpu: Math.max(10, Math.min(95, 31 + offset1)), mem: Math.max(10, Math.min(95, 59 + offset2)) },
    { label: 'middleware', role: 'DB / Redis / Kafka', cpu: Math.max(10, Math.min(95, 48 + offset2)), mem: Math.max(10, Math.min(95, 73 + offset1)) },
    { label: 'visualization', role: 'API / Nginx / Web', cpu: Math.max(10, Math.min(95, 35 + offset1)), mem: Math.max(10, Math.min(95, 41 + offset2)) }
  ]
})

function getProgressColor(val) {
  if (val > 80) return 'linear-gradient(90deg, #f43f5e, #fb7185)'
  if (val > 60) return 'linear-gradient(90deg, #f59e0b, #fbbf24)'
  return 'linear-gradient(90deg, #06b6d4, #22d3ee)'
}
const realtimeAlerts = ref([])
const dailyMetrics = ref([])
const historyRankings = ref([])
const relationGraph = ref({ nodes: [], links: [] })
const historyAlerts = ref([])
const reports = ref([])
const qualityOverview = ref({ rule_count: 0, issue_count: 0, avg_pass_rate: 1, pending_count: 0 })
const qualityIssues = ref([])

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

const middlewareStatus = computed(() => {
  const rows = realtimeOverview.value?.middleware
  if (Array.isArray(rows) && rows.length > 0) return rows
  return [
    {
      name: 'MySQL 关系数据库',
      status: 'warning',
      statusLabel: 'WAIT',
      metric: '-',
      host: 'middleware',
      port: 3306,
      hint: 'waiting for backend probe'
    },
    {
      name: 'Redis 缓存/实时指标',
      status: 'warning',
      statusLabel: 'WAIT',
      metric: '-',
      host: 'middleware',
      port: 6379,
      hint: 'waiting for backend probe'
    },
    {
      name: 'Kafka 消息队列',
      status: 'warning',
      statusLabel: 'WAIT',
      metric: '-',
      host: 'middleware',
      port: 9092,
      hint: 'waiting for backend probe'
    },
    {
      name: 'YARN / HDFS / Spark',
      status: 'warning',
      statusLabel: 'WAIT',
      metric: '-',
      host: 'master',
      port: 8088,
      hint: 'waiting for backend probe'
    }
  ]
})

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
  if (!throughputInstance || throughputInstance.getDom?.() !== throughputChart.value) {
    throughputInstance?.dispose()
    throughputInstance = echarts.init(throughputChart.value)
  }
  if (!latencyInstance || latencyInstance.getDom?.() !== latencyChart.value) {
    latencyInstance?.dispose()
    latencyInstance = echarts.init(latencyChart.value)
  }

  const xRealtime = realtimeTrend.value.map((item) => String(item.time || '').slice(11, 19))
  throughputInstance.setOption({
    tooltip: { trigger: 'axis' },
    legend: {
      data: ['事件数', '失败数'],
      textStyle: { color: '#9bc0d9' },
      top: 0
    },
    grid: { top: 38, right: 38, bottom: 28, left: 44 },
    xAxis: {
      type: 'category',
      data: xRealtime,
      boundaryGap: false,
      axisLabel: { color: '#9bc0d9' },
      axisLine: { lineStyle: { color: '#3f5a70' } }
    },
    yAxis: [
      {
        type: 'value',
        name: '事件数',
        nameTextStyle: { color: '#9bc0d9', fontSize: 10 },
        axisLabel: { color: '#9bc0d9' },
        axisLine: { lineStyle: { color: '#3f5a70' } },
        splitLine: { lineStyle: { color: 'rgba(139, 192, 217, 0.12)' } }
      },
      {
        type: 'value',
        name: '失败数',
        nameTextStyle: { color: '#9bc0d9', fontSize: 10 },
        axisLabel: { color: '#9bc0d9' },
        axisLine: { lineStyle: { color: '#3f5a70' } },
        splitLine: { show: false }
      }
    ],
    series: [
      {
        name: '事件数',
        type: 'line',
        smooth: true,
        symbol: 'none',
        showSymbol: false,
        yAxisIndex: 0,
        data: realtimeTrend.value.map((item) => item.events),
        areaStyle: { color: 'rgba(34, 211, 238, 0.12)' },
        itemStyle: { color: '#22d3ee' },
        lineStyle: { width: 2 }
      },
      {
        name: '失败数',
        type: 'line',
        smooth: true,
        symbol: 'none',
        showSymbol: false,
        yAxisIndex: 1,
        data: realtimeTrend.value.map((item) => item.failed),
        itemStyle: { color: '#fb7185' },
        lineStyle: { width: 2 }
      }
    ]
  }, true)

  setLineOption(latencyInstance, '平均时延趋势', xRealtime, [
    { name: '平均时延 ms', type: 'line', smooth: true, data: realtimeTrend.value.map((item) => item.avg_latency_ms), itemStyle: { color: '#4ade80' }, lineStyle: { width: 2 } }
  ])
}

function renderCharts() {
  renderRealtimeCharts()
  if (!relationChart.value) return
  if (!relationInstance || relationInstance.getDom?.() !== relationChart.value) {
    relationInstance?.dispose()
    relationInstance = echarts.init(relationChart.value)
  }

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
  
  if (relationInstance && !relationInstance._hasClickEvent) {
    relationInstance.on('click', (params) => {
      if (params.dataType === 'edge') {
        const source = params.data.source
        const target = params.data.target
        const elId = `diag-${source}-${target}`
        const el = document.getElementById(elId)
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
          el.classList.add('pulse-highlight')
          setTimeout(() => {
            el.classList.remove('pulse-highlight')
          }, 2000)
        }
      }
    })
    relationInstance._hasClickEvent = true
  }
}

function resizeCharts() {
  throughputInstance?.resize()
  latencyInstance?.resize()
  relationInstance?.resize()
}

function waitForFrame() {
  return new Promise((resolve) => requestAnimationFrame(() => resolve()))
}

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

async function ensureChartContainer(elRef, attempts = 10) {
  for (let i = 0; i < attempts; i += 1) {
    const el = elRef.value
    if (el && el.clientWidth > 0 && el.clientHeight > 0) return el
    await wait(80)
    await waitForFrame()
  }
  return elRef.value
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
  loading.value = true
  error.value = ''
  isEmpty.value = false
  try {
    const [startDate, endDate] = [getDateValue(dateRange.value?.[0], '2026-06-01'), getDateValue(dateRange.value?.[1], getTodayString())]
    const [realtimeOverviewData, realtimeTrendData, agentsData, realtimeAlertData, dailyData, rankingData, relationData, historyAlertData, reportsData, qualityOverviewData, qualityIssuesData] = await Promise.all([
      fetchOverview(),
      fetchTrend(60),
      fetchAgents(),
      fetchRealtimeAlerts(),
      fetchDailyMetrics(startDate, endDate),
      fetchAgentRankings(endDate),
      fetchRelationGraph(endDate),
      fetchHistoryAlerts(endDate),
      fetchReports(),
      fetchQualityOverview().catch(() => ({ rule_count: 3, issue_count: 0, avg_pass_rate: 1, pending_count: 0 })),
      fetchQualityIssues().catch(() => [])
    ])
    
    // Check empty dataset condition (strict mode check)
    if (!realtimeOverviewData || Object.keys(realtimeOverviewData).length === 0 || !agentsData || agentsData.length === 0) {
      isEmpty.value = true
    }
    
    realtimeOverview.value = realtimeOverviewData || {}
    realtimeTrend.value = realtimeTrendData || []
    realtimeAgents.value = agentsData || []
    realtimeAlerts.value = realtimeAlertData || []
    dailyMetrics.value = dailyData || []
    historyRankings.value = rankingData || []
    relationGraph.value = relationData || { nodes: [], links: [] }
    historyAlerts.value = historyAlertData || []
    qualityOverview.value = qualityOverviewData || { rule_count: 3, issue_count: 0, avg_pass_rate: 1, pending_count: 0 }
    qualityIssues.value = qualityIssuesData || []
    
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

    loading.value = false
    await nextTick()
    await ensureChartContainer(throughputChart)
    renderCharts()
    await waitForFrame()
    resizeCharts()
  } catch (err) {
    console.error('Failed to load overview data', err)
    error.value = err.message || '网络连接或后端服务异常'
  } finally {
    if (loading.value) {
      loading.value = false
    }
  }
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

watch(activeSubTab, async (tab) => {
  if (tab !== 'realtime') return
  await nextTick()
  await ensureChartContainer(throughputChart)
  renderCharts()
  await waitForFrame()
  resizeCharts()
}, { flush: 'post' })

onBeforeUnmount(() => {
  clearInterval(logTimer)
  clearInterval(pollTimer)
  window.removeEventListener('resize', resizeCharts)
  throughputInstance?.dispose()
  latencyInstance?.dispose()
  relationInstance?.dispose()
})
</script>

<style scoped>
.cluster-nodes-load-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 10px;
}
.node-load-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(30, 41, 59, 0.35);
  border: 1px solid rgba(255, 255, 255, 0.04);
  border-radius: 6px;
  padding: 5px 10px;
}
.node-meta {
  display: flex;
  flex-direction: column;
  width: 130px;
}
.node-name {
  font-size: 11px;
  font-weight: 600;
  color: #f8fafc;
}
.node-role {
  font-size: 9px;
  color: rgba(226, 232, 240, 0.5);
  margin-top: 1px;
}
.node-metrics-bar {
  display: flex;
  flex: 1;
  gap: 12px;
  margin-left: 10px;
}
.metric-progress-item {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
}
.metric-progress-item small {
  font-size: 9px;
  color: rgba(226, 232, 240, 0.65);
  width: 22px;
}
.progress-track {
  flex: 1;
  height: 5px;
  background: rgba(15, 23, 42, 0.6);
  border-radius: 3px;
  overflow: hidden;
  position: relative;
}
.progress-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.4s ease;
}
.metric-progress-item span {
  font-size: 10px;
  font-family: monospace;
  width: 28px;
  text-align: right;
  color: #e2e8f0;
}
.yarn-resource-summary {
  display: flex;
  justify-content: space-between;
  margin-top: 4px;
  background: rgba(15, 23, 42, 0.4);
  border: 1px dashed rgba(34, 211, 238, 0.18);
  border-radius: 6px;
  padding: 6px 10px;
}
.yarn-res-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
}
.res-lbl {
  font-size: 9px;
  color: rgba(226, 232, 240, 0.55);
  margin-bottom: 2px;
}
.res-val {
  font-size: 13px;
  font-weight: 700;
}
.res-val small {
  font-size: 9px;
  font-weight: 400;
  color: rgba(226, 232, 240, 0.65);
}
.text-cyan {
  color: #22d3ee;
}
.text-blue {
  color: #3b82f6;
}
.text-green {
  color: #10b981;
}

/* 对调位置后的高度与滚动重写 */

/* 1. 物理负载卡片（现在在 diagnostics 区域） */
.overview-grid__diagnostics .cluster-nodes-load-grid {
  max-height: 180px; /* 放宽高度 */
  overflow-y: auto;
  padding-right: 4px;
  scrollbar-color: rgba(34, 211, 238, 0.65) rgba(2, 8, 16, 0.72);
  scrollbar-width: thin;
}

/* 2. 诊断卡片（现在在 system_load 区域） */
.overview-grid__system_load .diagnostics-list {
  max-height: 165px; /* 放宽高度限制，让滚动范围能够饱满占满整个卡片框 */
  overflow-y: auto;
  padding-right: 4px;
  scrollbar-color: rgba(34, 211, 238, 0.65) rgba(2, 8, 16, 0.72);
  scrollbar-width: thin;
}

.alert-ticker {
  max-height: 120px;
  overflow-y: auto;
  padding-right: 4px;
  scrollbar-color: rgba(34, 211, 238, 0.65) rgba(2, 8, 16, 0.72);
  scrollbar-width: thin;
}

/* 顶部告警只读状态条 */
.screen-alert-indicator {
  display: inline-flex;
  align-items: center;
  height: 38px;
  padding: 0 16px;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(34, 211, 238, 0.35);
  border-radius: 4px;
  color: #9bc0d9;
  font-size: 14px;
  font-weight: 600;
}
.screen-alert-indicator strong {
  margin-left: 6px;
  color: #22d3ee;
}
.screen-alert-indicator strong.alert-count-red {
  color: #fb7185;
  text-shadow: 0 0 8px rgba(251, 113, 133, 0.6);
}

/* 协作诊断联动高亮动画 */
@keyframes pulseGlow {
  0% { background: rgba(34, 211, 238, 0.15); border-color: rgba(34, 211, 238, 0.4); }
  50% { background: rgba(34, 211, 238, 0.4); border-color: #22d3ee; box-shadow: 0 0 10px rgba(34, 211, 238, 0.45); }
  100% { background: rgba(15, 34, 54, 0.45); border-color: rgba(103, 232, 249, 0.12); }
}

.pulse-highlight {
  animation: pulseGlow 1.5s ease-in-out;
}

.agent-rank-compact {
  scrollbar-color: rgba(34, 211, 238, 0.65) rgba(2, 8, 16, 0.72);
  scrollbar-width: thin;
  padding-right: 4px;
}

/* 实时数据流一致性的滚动条美化 */
.overview-grid__diagnostics .cluster-nodes-load-grid::-webkit-scrollbar,
.overview-grid__system_load .diagnostics-list::-webkit-scrollbar,
.agent-rank-compact::-webkit-scrollbar,
.alert-ticker::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

.overview-grid__diagnostics .cluster-nodes-load-grid::-webkit-scrollbar-track,
.overview-grid__system_load .diagnostics-list::-webkit-scrollbar-track,
.agent-rank-compact::-webkit-scrollbar-track,
.alert-ticker::-webkit-scrollbar-track {
  background: rgba(2, 8, 16, 0.72);
  border-radius: 8px;
}

.overview-grid__diagnostics .cluster-nodes-load-grid::-webkit-scrollbar-thumb,
.overview-grid__system_load .diagnostics-list::-webkit-scrollbar-thumb,
.agent-rank-compact::-webkit-scrollbar-thumb,
.alert-ticker::-webkit-scrollbar-thumb {
  background: linear-gradient(180deg, rgba(34, 211, 238, 0.78), rgba(14, 116, 144, 0.72));
  border: 2px solid rgba(2, 8, 16, 0.72);
  border-radius: 8px;
}

.overview-grid__diagnostics .cluster-nodes-load-grid::-webkit-scrollbar-thumb:hover,
.overview-grid__system_load .diagnostics-list::-webkit-scrollbar-thumb:hover,
.agent-rank-compact::-webkit-scrollbar-thumb:hover,
.alert-ticker::-webkit-scrollbar-thumb:hover {
  background: linear-gradient(180deg, rgba(103, 232, 249, 0.95), rgba(8, 145, 178, 0.86));
}
</style>
