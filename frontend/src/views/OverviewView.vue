<template>
  <section class="screen-page screen-page--overview">
    <div class="screen-board">
      <header class="screen-titlebar">
        <div>
          <p class="screen-kicker">实时链路与离线链路双总览</p>
          <h2>AgentScope 多智能体运行监测与效能分析平台</h2>
        </div>
        <div class="screen-tools">
          <a-range-picker v-model="dateRange" value-format="YYYY-MM-DD" size="large" class="screen-date" />
          <a-button type="outline" size="large" @click="load">刷新</a-button>
          <a-button type="outline" size="large" @click="scrollToAgents">Agent 监控</a-button>
          <a-button type="outline" size="large" @click="scrollToHistory">历史图表</a-button>
          <a-button type="outline" size="large" @click="router.push('/data-admin')" style="color: #22d3ee; border-color: rgba(34, 211, 238, 0.45);">返回数据后台</a-button>
          <a-button type="primary" size="large" @click="alertOpen = true">告警 {{ realtimeAlerts.length + historyAlerts.length }}</a-button>
        </div>
      </header>

      <section class="link-summary-grid">
        <article class="link-summary-card realtime">
          <span>实时链路</span>
          <strong>实时调度与处理态势</strong>
          <p>当前运行任务 {{ realtimeOverview.running_tasks ?? '-' }} 个，活跃 Agent {{ realtimeOverview.active_agents ?? '-' }} 个，实时吞吐 {{ realtimeOverview.events_per_minute ?? '-' }}/min，告警 {{ realtimeAlerts.length }} 条。</p>
        </article>
        <article class="link-summary-card offline">
          <span>离线链路</span>
          <strong>离线分析与报告产出</strong>
          <p>选区内历史任务 {{ formatNumber(dailySummary.taskCount) }} 条，离线成功率 {{ percent(dailySummary.successRate) }}，报告 {{ reports.length }} 份，关系图 {{ relationGraph.links?.length || 0 }} 条边。</p>
        </article>
      </section>

      <section class="screen-metrics">
        <article v-for="metric in metrics" :key="metric.label" class="screen-metric">
          <span>{{ metric.label }}</span>
          <strong>{{ metric.value }}</strong>
          <small>{{ metric.hint }}</small>
        </article>
      </section>

      <section class="screen-layout overview-grid">
        <article class="screen-panel overview-grid__stream terminal-log-panel">
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

        <article class="screen-panel hero-panel overview-grid__throughput">
          <div class="screen-panel-head">
            <h3>实时吞吐 / 失败趋势</h3>
            <span>last 60 seconds</span>
          </div>
          <div ref="throughputChart" class="screen-chart large"></div>
        </article>

        <article class="screen-panel compact overview-grid__daily">
          <div class="screen-panel-head">
            <h3>离线每日指标</h3>
            <span>history trend</span>
          </div>
          <div ref="dailyChart" class="screen-chart small"></div>
        </article>

        <article class="screen-panel compact overview-grid__alerts">
          <div class="screen-panel-head">
            <h3>实时告警</h3>
            <span>{{ realtimeAlerts.length }} open</span>
          </div>
          <div class="alert-ticker">
            <div v-for="alert in realtimeAlerts" :key="alert.alert_id" class="ticker-item">
              <span :class="['level-dot', alert.level]">{{ alert.level }}</span>
              <strong>{{ alert.alert_type }}</strong>
              <small>{{ alert.agent_id }} / {{ alert.create_time }}</small>
            </div>
          </div>
        </article>

        <article class="screen-panel hero-panel overview-grid__latency">
          <div class="screen-panel-head">
            <h3>平均时延趋势</h3>
            <span>avg latency ms</span>
          </div>
          <div ref="latencyChart" class="screen-chart large"></div>
        </article>

        <article class="screen-panel overview-grid__relation">
          <div class="screen-panel-head">
            <h3>协作关系图</h3>
            <span>{{ relationGraph.nodes?.length || 0 }} nodes</span>
          </div>
          <div ref="relationChart" class="screen-chart" style="height: 260px;"></div>
        </article>

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

        <article class="screen-panel overview-grid__cost">
          <div class="screen-panel-head">
            <h3>LLM 资源与成本监控</h3>
            <span>real-time & history</span>
          </div>
          <div class="cost-summary-cards">
            <div class="cost-card token">
              <span>实时 (5m) Token 消耗</span>
              <strong>{{ formatNumber(realtimeOverview.token_total_5m) }}</strong>
              <small>tokens</small>
            </div>
            <div class="cost-card price">
              <span>实时 (5m) 估算成本</span>
              <strong>${{ Number(realtimeOverview.estimated_cost_5m || 0).toFixed(4) }}</strong>
              <small>USD</small>
            </div>
          </div>
          <div ref="costChart" class="screen-chart" style="height: 200px; margin-top: 14px;"></div>
        </article>
      </section>

      <section ref="agentTableRef" class="screen-panel agent-monitor-panel">
        <div class="screen-panel-head">
          <h3>Agent 监控与实时排行</h3>
          <span>{{ realtimeAgents.length }} agents</span>
        </div>
        <div class="screen-table-wrap">
          <table class="data-table screen-native-table">
            <thead>
              <tr>
                <th style="width: 70px;">排名</th>
                <th>Agent ID</th>
                <th>角色</th>
                <th>状态</th>
                <th>当前任务</th>
                <th>成功率</th>
                <th>平均时延</th>
                <th>Token</th>
                <th>重试次数</th>
                <th>最近事件时间</th>
              </tr>
            </thead>
            <TransitionGroup name="flip-list" tag="tbody">
              <tr v-for="(agent, index) in sortedAgents" :key="agent.agent_id">
                <td><span class="rank-badge">#{{ index + 1 }}</span></td>
                <td>{{ agent.agent_id }}</td>
                <td>{{ agent.agent_role }}</td>
                <td><span :class="['tag', agent.status]">{{ agent.status }}</span></td>
                <td>{{ agent.current_task }}</td>
                <td>{{ percent(agent.success_rate) }}</td>
                <td>{{ Math.round(agent.avg_latency_ms || 0) }} ms</td>
                <td>{{ Number(agent.token_total || 0).toLocaleString() }}</td>
                <td>{{ agent.retry_count }}</td>
                <td>{{ agent.last_event_time }}</td>
              </tr>
            </TransitionGroup>
          </table>
        </div>
      </section>

      <section ref="historyChartsRef" class="screen-history">
        <div class="screen-panel-head screen-history-head">
          <div>
            <p class="screen-kicker">历史分析汇总</p>
            <h3>历史分析图表</h3>
          </div>
          <span>daily / ranking</span>
        </div>
        <div class="history-grid">
          <ChartPanel :option="historyTaskOption" />
          <ChartPanel :option="historySuccessOption" />
          <ChartPanel :option="historyLatencyOption" />
          <ChartPanel :option="historyRankingOption" />
        </div>
      </section>

      <section class="screen-bottom">
        <article class="screen-panel report-table-panel">
          <div class="screen-panel-head">
            <h3>历史告警</h3>
            <span>{{ historyAlerts.length }} records</span>
          </div>
          <div class="screen-table-wrap scrollable-table-wrap">
            <table class="data-table screen-native-table">
              <thead>
                <tr>
                  <th>等级</th>
                  <th>类型</th>
                  <th>Agent</th>
                  <th>当前值</th>
                  <th>阈值</th>
                  <th>来源</th>
                  <th>状态</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="alert in historyAlerts" :key="alert.alert_id">
                  <td><span :class="['tag', alert.level]">{{ alert.level }}</span></td>
                  <td>{{ alert.alert_type }}</td>
                  <td>{{ alert.agent_id }}</td>
                  <td>{{ alert.current_value }}</td>
                  <td>{{ alert.threshold ?? alert.threshold_value }}</td>
                  <td>{{ alert.source }}</td>
                  <td>{{ alert.status }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </article>

        <article class="screen-panel report-summary-panel">
          <div class="screen-panel-head">
            <h3>AI 报告摘要</h3>
            <span>{{ latestReport.create_time || '未生成' }}</span>
          </div>
          <p class="report-summary-intro">
            {{ latestReport.content ? reportIntro : '暂无报告内容，点击右上角进入报告页或先生成一份日报。' }}
          </p>
          <div v-if="reportPreviewSections.length" class="report-preview-grid">
            <article v-for="(section, sectionIndex) in reportPreviewSections" :key="`${section.title}-${sectionIndex}`" class="report-preview-card">
              <div class="report-preview-head">
                <h4>{{ section.title }}</h4>
                <span>{{ section.blocks.length }} 段</span>
              </div>
              <div class="report-markdown">
                <template v-for="(block, blockIndex) in section.blocks" :key="`${sectionIndex}-${blockIndex}`">
                  <div v-if="block.type === 'paragraph'" class="report-block report-block--paragraph" v-html="block.html"></div>
                  <div v-else-if="block.type === 'list'" class="report-block report-block--list">
                    <ul>
                      <li v-for="(item, itemIndex) in block.items" :key="itemIndex" v-html="item"></li>
                    </ul>
                  </div>
                  <div v-else-if="block.type === 'code'" class="report-block report-block--code">
                    <span v-if="block.language" class="code-lang">{{ block.language }}</span>
                    <pre v-text="block.text"></pre>
                  </div>
                  <div v-else-if="block.type === 'table'" class="report-block report-block--table table-responsive">
                    <table class="data-table screen-native-table markdown-table">
                      <thead>
                        <tr>
                          <th v-for="(h, hIdx) in block.headers" :key="hIdx" v-html="h"></th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="(row, rIdx) in block.rows" :key="rIdx">
                          <td v-for="(cell, cIdx) in row" :key="cIdx" v-html="cell"></td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </template>
              </div>
            </article>
          </div>
          <a-space wrap>
            <a-button type="primary" @click="$router.push('/reports')">进入报告页</a-button>
            <a-button @click="scrollToHistory">查看历史图表</a-button>
          </a-space>
        </article>
      </section>
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
              <td>{{ alert.alert_type }}</td>
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
const agentTableRef = ref(null)
const historyChartsRef = ref(null)

const throughputChart = ref(null)
const latencyChart = ref(null)
const dailyChart = ref(null)
const relationChart = ref(null)
const costChart = ref(null)

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
let dailyInstance
let relationInstance
let costInstance

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
  const content = String(latestReport.value.content || '')
  return content ? excerptMarkdown(content, 160) : '生成结果会以卡片方式展示，方便快速阅读和定位重点。'
})

const metrics = computed(() => [
  { label: '运行任务', value: realtimeOverview.value.running_tasks ?? '-', hint: '实时处理中的任务' },
  { label: '活跃 Agent', value: realtimeOverview.value.active_agents ?? '-', hint: '当前在线角色数' },
  { label: '事件吞吐 / 分钟', value: realtimeOverview.value.events_per_minute ?? '-', hint: '实时事件输入速率' },
  { label: '实时成功率', value: percent(realtimeOverview.value.success_rate), hint: `错误率 ${percent(realtimeOverview.value.error_rate)}` },
  { label: '平均时延', value: `${Math.round(realtimeOverview.value.avg_latency_ms || 0)} ms`, hint: '实时窗口统计' },
  { label: '离线任务总量', value: formatNumber(dailySummary.value.taskCount), hint: '选定区间离线任务' },
  { label: '离线成功率', value: percent(dailySummary.value.successRate), hint: `P95 ${Math.round(dailySummary.value.p95Latency || 0)} ms` },
  { label: '离线 Top Agent', value: historyRankings.value[0] ? `${historyRankings.value[0].agent_role} / ${formatNumber(historyRankings.value[0].execution_count)}` : '-', hint: '离线执行次数排行' },
])

const historyTaskOption = computed(() => lineOption('每日任务量', dailyMetrics.value.map((item) => item.metric_date), [
  { name: '任务数', type: 'line', smooth: true, data: dailyMetrics.value.map((item) => item.task_count), itemStyle: { color: '#3b82f6' }, lineStyle: { width: 3 }, areaStyle: { color: 'rgba(59, 130, 246, 0.08)' } }
]))

const historySuccessOption = computed(() => lineOption('每日成功率', dailyMetrics.value.map((item) => item.metric_date), [
  { name: '成功率', type: 'line', smooth: true, data: dailyMetrics.value.map((item) => Number(item.success_rate) * 100), itemStyle: { color: '#10b981' }, lineStyle: { width: 3 }, areaStyle: { color: 'rgba(16, 185, 129, 0.08)' } }
]))

const historyLatencyOption = computed(() => lineOption('平均 / P95 时延', dailyMetrics.value.map((item) => item.metric_date), [
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

function getDateValue(value, fallback) {
  if (!value) return fallback
  if (typeof value === 'string') return value
  if (typeof value?.format === 'function') return value.format('YYYY-MM-DD')
  return fallback
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
  if (!dailyChart.value || !relationChart.value || !costChart.value) return
  dailyInstance ||= echarts.init(dailyChart.value)
  relationInstance ||= echarts.init(relationChart.value)
  costInstance ||= echarts.init(costChart.value)

  const xDaily = dailyMetrics.value.map((item) => item.metric_date)
  dailyInstance.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    legend: { top: 0, textStyle: { color: '#bdefff' } },
    grid: { top: 42, right: 50, bottom: 24, left: 50 },
    xAxis: { type: 'category', data: xDaily, ...baseAxis() },
    yAxis: [
      {
        type: 'value',
        name: '任务量',
        position: 'left',
        ...baseAxis()
      },
      {
        type: 'value',
        name: '成功率',
        position: 'right',
        min: 0,
        max: 100,
        ...baseAxis(),
        splitLine: { show: false },
        axisLabel: {
          formatter: '{value}%',
          color: '#9bc7d9'
        }
      }
    ],
    series: [
      {
        name: '任务量',
        type: 'line',
        smooth: true,
        symbol: 'none',
        showSymbol: false,
        yAxisIndex: 0,
        data: dailyMetrics.value.map((item) => item.task_count),
        areaStyle: { color: 'rgba(34, 211, 238, 0.08)' },
        itemStyle: { color: '#22d3ee' },
        lineStyle: { width: 3 }
      },
      {
        name: '成功率 %',
        type: 'line',
        smooth: true,
        symbol: 'none',
        showSymbol: false,
        yAxisIndex: 1,
        data: dailyMetrics.value.map((item) => Math.round(Number(item.success_rate) * 100)),
        itemStyle: { color: '#4ade80' },
        lineStyle: { width: 3 }
      }
    ]
  }, true)

  relationInstance.setOption(graphOption(relationGraph.value), true)

  costInstance.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    legend: { top: 0, textStyle: { color: '#bdefff' } },
    grid: { top: 38, right: 48, bottom: 24, left: 48 },
    xAxis: { type: 'category', data: xDaily, ...baseAxis() },
    yAxis: [
      {
        type: 'value',
        name: 'Tokens',
        position: 'left',
        ...baseAxis(),
        axisLabel: {
          formatter: (val) => val >= 1000000 ? `${(val/1000000).toFixed(1)}M` : `${val/1000}k`,
          color: '#9bc7d9'
        }
      },
      {
        type: 'value',
        name: '成本 (USD)',
        position: 'right',
        ...baseAxis(),
        splitLine: { show: false },
        axisLabel: {
          formatter: '${value}',
          color: '#9bc7d9'
        }
      }
    ],
    series: [
      {
        name: '每日 Token',
        type: 'line',
        smooth: true,
        symbol: 'none',
        showSymbol: false,
        yAxisIndex: 0,
        data: dailyMetrics.value.map((item) => item.total_tokens),
        itemStyle: { color: '#06b6d4' },
        lineStyle: { width: 3 }
      },
      {
        name: '每日成本 ($)',
        type: 'line',
        smooth: true,
        symbol: 'none',
        showSymbol: false,
        yAxisIndex: 1,
        data: dailyMetrics.value.map((item) => item.estimated_cost_usd),
        itemStyle: { color: '#10b981' },
        lineStyle: { width: 3 }
      }
    ]
  }, true)
}

function resizeCharts() {
  throughputInstance?.resize()
  latencyInstance?.resize()
  dailyInstance?.resize()
  relationInstance?.resize()
  costInstance?.resize()
}

function scrollToHistory() {
  historyChartsRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function scrollToAgents() {
  agentTableRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
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
  dailyInstance?.dispose()
  relationInstance?.dispose()
  costInstance?.dispose()
})
</script>
