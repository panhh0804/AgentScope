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
        <article class="screen-panel compact overview-grid__rank">
          <div class="screen-panel-head">
            <h3>实时 Agent 排行</h3>
            <span>success / latency</span>
          </div>
          <div class="agent-rank-list">
            <div v-for="agent in realtimeAgents" :key="agent.agent_id" class="agent-rank-item">
              <div>
                <strong>{{ agent.agent_role }}</strong>
                <span>{{ agent.agent_id }}</span>
              </div>
              <b>{{ percent(agent.success_rate) }}</b>
              <small>{{ Math.round(agent.avg_latency_ms || 0) }}ms</small>
            </div>
          </div>
        </article>

        <article class="screen-panel hero-panel overview-grid__throughput">
          <div class="screen-panel-head">
            <h3>实时吞吐 / 失败趋势</h3>
            <span>last 60 minutes</span>
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

        <article class="screen-panel compact overview-grid__relation">
          <div class="screen-panel-head">
            <h3>协作关系图</h3>
            <span>{{ relationGraph.nodes?.length || 0 }} nodes</span>
          </div>
          <div ref="relationChart" class="screen-chart small"></div>
        </article>

        <article class="screen-panel overview-grid__stream terminal-log-panel">
          <div class="screen-panel-head">
            <h3>实时数据流</h3>
            <span class="pulse-badge">LIVE STREAMING</span>
          </div>
          <div ref="terminalRef" class="terminal-log-container">
            <div v-for="(log, idx) in realtimeLogs" :key="idx" class="terminal-log-row">
              <span class="terminal-log-time">[{{ log.time }}]</span>
              <span class="terminal-log-agent"> [{{ log.agent }}]</span>
              <span :class="['terminal-log-message', `terminal-log-level-${log.level}`]"> {{ log.message }}</span>
            </div>
          </div>
        </article>
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

      <section ref="agentTableRef" class="screen-panel agent-monitor-panel">
        <div class="screen-panel-head">
          <h3>Agent 监控</h3>
          <span>{{ realtimeAgents.length }} agents</span>
        </div>
        <div class="screen-table-wrap">
          <table class="data-table screen-native-table">
            <thead>
              <tr>
                <th>Agent</th>
                <th>角色</th>
                <th>状态</th>
                <th>当前任务</th>
                <th>成功率</th>
                <th>平均时延</th>
                <th>Token</th>
                <th>重试</th>
                <th>最近事件</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="agent in realtimeAgents" :key="agent.agent_id">
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
            </tbody>
          </table>
        </div>
      </section>

      <section class="screen-bottom">
        <article class="screen-panel report-table-panel">
          <div class="screen-panel-head">
            <h3>历史告警</h3>
            <span>{{ historyAlerts.length }} records</span>
          </div>
          <div class="screen-table-wrap">
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
import * as echarts from 'echarts'
import ChartPanel from '../components/ChartPanel.vue'
import { fetchAgentRankings, fetchDailyMetrics, fetchAgents, fetchHistoryAlerts, fetchOverview, fetchRealtimeAlerts, fetchRelationGraph, fetchReports, fetchTrend } from '../api/dashboard'
import { barOption, graphOption, lineOption } from '../charts/options'
import { excerptMarkdown, parseMarkdownSections } from '../utils/markdown'

const realtimeOverview = ref({})
const realtimeTrend = ref([])
const realtimeAgents = ref([])
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

const realtimeLogs = ref([])
const terminalRef = ref(null)

const logTemplates = [
  { agent: 'planner_agent', level: 'info', message: '收到用户请求，开始任务规划与子任务拆解。' },
  { agent: 'planner_agent', level: 'info', message: '成功生成子任务链: [search -> analysis -> writer -> reviewer]。' },
  { agent: 'search_agent', level: 'info', message: '正在启动网络检索，查询关键词: "agentscope multi-agent framework"。' },
  { agent: 'search_agent', level: 'info', message: '检索完成，获取到 8 条相关网页结果 (latency: 120ms)。' },
  { agent: 'analysis_agent', level: 'info', message: '开始读取检索网页内容，进行深度摘要与信息提取。' },
  { agent: 'analysis_agent', level: 'info', message: '信息提取完毕，生成格式化分析数据 (tokens: 1250)。' },
  { agent: 'writer_agent', level: 'info', message: '开始调用 LLM 撰写报告首段：系统整体架构与优势。' },
  { agent: 'writer_agent', level: 'info', message: '报告内容生成中，当前使用 token 数: 2400。' },
  { agent: 'writer_agent', level: 'info', message: '草稿生成成功，正移交给 Reviewer 角色审核。' },
  { agent: 'reviewer_agent', level: 'info', message: '开始对生成的报告草稿进行合规性、事实准确性及逻辑链校对。' },
  { agent: 'reviewer_agent', level: 'info', message: '校对通过，内容无敏感信息且事实无误。' },
  { agent: 'planner_agent', level: 'info', message: '任务链 trace_demo_101 执行完毕，结果已成功保存。' },
  { agent: 'search_agent', level: 'warn', message: '网络检索 API 响应延迟较高 (3400ms)，正在自动优化连接池。' },
  { agent: 'writer_agent', level: 'warn', message: 'LLM API 返回结果出现截断，正在尝试重试以确保报告完整性。' },
  { agent: 'search_agent', level: 'error', message: '网络连接超时 (timeout 5s000ms)，将自动发起第 1 次重试。' },
  { agent: 'search_agent', level: 'info', message: '重试成功，已恢复数据拉取。' }
]

const addLog = (logObj = null) => {
  const d = new Date()
  const timeStr = `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`
  
  let entry
  if (logObj) {
    entry = { time: timeStr, ...logObj }
  } else {
    const template = logTemplates[Math.floor(Math.random() * logTemplates.length)]
    entry = {
      time: timeStr,
      agent: template.agent,
      level: template.level,
      message: template.message
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

const dailySummary = computed(() => {
  const rows = dailyMetrics.value
  const taskCount = rows.reduce((sum, row) => sum + Number(row.task_count || 0), 0)
  const successRate = rows.length ? rows.reduce((sum, row) => sum + Number(row.success_rate || 0), 0) / rows.length : 0
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
  { name: '任务数', type: 'line', smooth: true, data: dailyMetrics.value.map((item) => item.task_count), lineStyle: { color: '#5f79ad' } }
]))

const historySuccessOption = computed(() => lineOption('每日成功率', dailyMetrics.value.map((item) => item.metric_date), [
  { name: '成功率', type: 'line', smooth: true, data: dailyMetrics.value.map((item) => Number(item.success_rate) * 100), lineStyle: { color: '#7aa06f' } }
]))

const historyLatencyOption = computed(() => lineOption('平均 / P95 时延', dailyMetrics.value.map((item) => item.metric_date), [
  { name: '平均时延', type: 'line', smooth: true, data: dailyMetrics.value.map((item) => item.avg_latency_ms), lineStyle: { color: '#6d90a8' } },
  { name: 'P95 时延', type: 'line', smooth: true, data: dailyMetrics.value.map((item) => item.p95_latency_ms), lineStyle: { color: '#8f6c6c' } }
]))

const historyRankingOption = computed(() => barOption(
  'Agent 执行次数排行',
  historyRankings.value.map((item) => item.agent_role),
  historyRankings.value.map((item) => item.execution_count),
  '执行次数'
))

const allAlerts = computed(() => [...realtimeAlerts.value, ...historyAlerts.value])

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

function renderCharts() {
  if (!throughputChart.value || !latencyChart.value || !dailyChart.value || !relationChart.value) return
  throughputInstance ||= echarts.init(throughputChart.value)
  latencyInstance ||= echarts.init(latencyChart.value)
  dailyInstance ||= echarts.init(dailyChart.value)
  relationInstance ||= echarts.init(relationChart.value)

  const xRealtime = realtimeTrend.value.map((item) => String(item.time || '').slice(11, 16))
  setLineOption(throughputInstance, '最近 60 分钟吞吐', xRealtime, [
    {
      name: '事件数',
      type: 'line',
      smooth: true,
      data: realtimeTrend.value.map((item) => item.events),
      areaStyle: { color: 'rgba(34, 211, 238, 0.12)' },
      lineStyle: { color: '#22d3ee', width: 2 }
    },
    { name: '失败数', type: 'line', smooth: true, data: realtimeTrend.value.map((item) => item.failed), lineStyle: { color: '#fb7185', width: 2 } }
  ])

  setLineOption(latencyInstance, '平均时延趋势', xRealtime, [
    { name: '平均时延 ms', type: 'line', smooth: true, data: realtimeTrend.value.map((item) => item.avg_latency_ms), lineStyle: { color: '#4ade80', width: 2 } }
  ])

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
        yAxisIndex: 0,
        data: dailyMetrics.value.map((item) => item.task_count),
        areaStyle: { color: 'rgba(34, 211, 238, 0.12)' },
        lineStyle: { color: '#22d3ee' }
      },
      {
        name: '成功率 %',
        type: 'line',
        smooth: true,
        yAxisIndex: 1,
        data: dailyMetrics.value.map((item) => Math.round(Number(item.success_rate) * 100)),
        lineStyle: { color: '#4ade80' }
      }
    ]
  }, true)

  relationInstance.setOption(graphOption(relationGraph.value), true)
}

function resizeCharts() {
  throughputInstance?.resize()
  latencyInstance?.resize()
  dailyInstance?.resize()
  relationInstance?.resize()
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
  reports.value = reportsData
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
    realtimeLogs.value.push({
      time: timeStr,
      agent: template.agent,
      level: template.level,
      message: template.message
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
      renderCharts()
    } catch (e) {
      console.error('Failed to poll realtime data', e)
    }
  }, 5000)
  
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
})
</script>
