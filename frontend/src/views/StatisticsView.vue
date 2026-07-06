<template>
  <section class="screen-page statistics-page">
    <div class="screen-board statistics-board">
      <header class="screen-titlebar">
        <div>
          <p class="screen-kicker">多维离线指标统计与效能评估</p>
          <h2>数据统计分析端</h2>
        </div>
        <div class="screen-tools">
          <a-button type="primary" size="large" :loading="loading" @click="loadAll">刷新</a-button>
        </div>
      </header>

      <section class="screen-metrics statistics-metrics">
        <article v-for="metric in summaryMetrics" :key="metric.label" class="screen-metric">
          <span>{{ metric.label }}</span>
          <strong>{{ metric.value }}</strong>
          <small>{{ metric.hint }}</small>
        </article>
      </section>

      <section class="history-chart-grid">
        <article class="screen-panel">
          <div class="screen-panel-head">
            <h3>智能体离线调用排行 (Top Roles)</h3>
            <span>agent execution rank</span>
          </div>
          <ChartPanel :option="historyRankingOption" class="history-chart-panel" />
        </article>
        <article class="screen-panel">
          <div class="screen-panel-head">
            <h3>每日 Token 与成本趋势</h3>
            <span>token / cost trend</span>
          </div>
          <ChartPanel :option="historyCostOption" class="history-chart-panel" />
        </article>
      </section>

      <section class="stats-chart-grid">
        <article class="screen-panel">
          <div class="screen-panel-head">
            <h3>任务量与运行成功率 {{ trendPeriodLabel }}走势</h3>
            <span>daily_metrics</span>
          </div>
          <div ref="trendChartRef" class="statistics-chart"></div>
        </article>

        <article class="screen-panel">
          <div class="screen-panel-head">
            <h3>Agent Token 消耗与成本分布</h3>
            <span>agent_rankings</span>
          </div>
          <div ref="tokenChartRef" class="statistics-chart"></div>
        </article>

        <article class="screen-panel">
          <div class="screen-panel-head">
            <h3>系统异常类型与错误分布</h3>
            <span>error_distribution</span>
          </div>
          <div ref="errorChartRef" class="statistics-chart"></div>
        </article>

        <article class="screen-panel">
          <div class="screen-panel-head">
            <h3>Agent 平均时延与 P95 时延对比</h3>
            <span>latency percentiles</span>
          </div>
          <div ref="latencyChartRef" class="statistics-chart"></div>
        </article>
      </section>
    </div>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { Message } from '@arco-design/web-vue'
import ChartPanel from '../components/ChartPanel.vue'
import { fetchDailyMetrics, fetchAgentRankings } from '../api/dashboard'
import {
  fetchAnalyticsAgentStats,
  fetchAnalyticsErrors,
  fetchAnalyticsTrend
} from '../api/statistics'
import { barOption, lineOption } from '../charts/options'

const loading = ref(false)
const trend = ref([])
const errors = ref([])
const agentStats = ref([])
const dailyMetrics = ref([])
const historyRankings = ref([])

const trendChartRef = ref(null)
const tokenChartRef = ref(null)
const errorChartRef = ref(null)
const latencyChartRef = ref(null)
let trendChart
let tokenChart
let errorChart
let latencyChart

const summaryMetrics = computed(() => {
  const totalTasks = trend.value.reduce((sum, item) => sum + Number(item.task_count || 0), 0)
  const totalSuccess = trend.value.reduce((sum, item) => sum + Number(item.success_count || 0), 0)
  const totalTokens = agentStats.value.reduce((sum, item) => sum + Number(item.total_tokens || 0), 0)
  const totalCost = agentStats.value.reduce((sum, item) => sum + Number(item.estimated_cost_usd || 0), 0)
  const p95Values = agentStats.value.map((item) => Number(item.p95_latency_ms || 0)).filter(Boolean)
  const maxP95 = p95Values.length ? Math.max(...p95Values) : 0
  return [
    { label: `${trendPeriodLabel.value}任务总量`, value: formatNumber(totalTasks), hint: `${trend.value.length} 个业务日期` },
    { label: '综合成功率', value: percent(totalTasks ? totalSuccess / totalTasks : 0), hint: 'success / task' },
    { label: 'Agent Token 总量', value: compactNumber(totalTokens), hint: `${agentStats.value.length} 个 Agent` },
    { label: '累计估算成本', value: `$${totalCost.toFixed(2)}`, hint: `最高 P95 ${formatNumber(maxP95)} ms` }
  ]
})

const trendPeriodLabel = computed(() => `近 ${trend.value.length || 0} 天`)

const historyRankingOption = computed(() => barOption(
  'Agent 执行次数排行',
  historyRankings.value.map((item) => item.agent_role),
  historyRankings.value.map((item) => item.execution_count),
  '执行次数'
))

const historyCostOption = computed(() => {
  const option = historyLineOption('Token / 成本趋势', [
    {
      name: '每日 Token',
      type: 'line',
      smooth: true,
      yAxisIndex: 0,
      data: dailyMetrics.value.map((item) => item.total_tokens),
      itemStyle: { color: '#06b6d4' },
      lineStyle: { width: 3 },
      areaStyle: { color: 'rgba(6, 182, 212, 0.08)' }
    },
    {
      name: '每日成本 ($)',
      type: 'line',
      smooth: true,
      yAxisIndex: 1,
      data: dailyMetrics.value.map((item) => item.estimated_cost_usd),
      itemStyle: { color: '#10b981' },
      lineStyle: { width: 3 }
    }
  ])
  option.yAxis = [
    {
      type: 'value',
      name: 'Tokens',
      axisLabel: {
        color: '#9bc7d9',
        formatter: (value) => value >= 1000000 ? `${(value / 1000000).toFixed(1)}M` : `${Math.round(value / 1000)}k`
      },
      splitLine: { lineStyle: { color: 'rgba(103, 232, 249, 0.1)' } }
    },
    {
      type: 'value',
      name: '成本 ($)',
      axisLabel: { color: '#9bc7d9', formatter: '${value}' },
      splitLine: { show: false }
    }
  ]
  return option
})

const errorTypeLabels = {
  validation_error: '数据校验错误',
  tool_error: '工具调用错误',
  timeout: '请求超时',
  model_error: '模型响应错误',
  tool_timeout: '工具超时'
}

function formatErrorType(value) {
  return errorTypeLabels[value] || value
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString()
}

function compactNumber(value) {
  return Intl.NumberFormat('en', { notation: 'compact', maximumFractionDigits: 1 }).format(Number(value || 0))
}

function percent(value) {
  return `${(Number(value || 0) * 100).toFixed(1)}%`
}

function getTodayString() {
  const d = new Date()
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function formatShortDate(dateStr) {
  if (!dateStr) return ''
  const parts = String(dateStr).split('-')
  if (parts.length === 3) return `${parts[1]}-${parts[2]}`
  return dateStr
}

function historyTooltipFormatter(params) {
  if (!params || !params.length) return ''
  const date = params[0].axisValueLabel
  const rows = Array.isArray(params) ? params : [params]
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

function baseChartOption() {
  return {
    backgroundColor: 'transparent',
    textStyle: { color: '#dbe7f3' },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(2, 8, 16, 0.92)',
      borderColor: 'rgba(103, 232, 249, 0.25)',
      textStyle: { color: '#dbe7f3' }
    },
    legend: {
      top: 0,
      right: 8,
      textStyle: { color: '#9bc7d9' }
    },
    grid: { left: 48, right: 48, top: 52, bottom: 36 },
    xAxis: {
      type: 'category',
      axisLine: { lineStyle: { color: 'rgba(103, 232, 249, 0.28)' } },
      axisLabel: { color: '#9bc7d9' }
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: 'rgba(103, 232, 249, 0.1)' } },
      axisLabel: { color: '#9bc7d9' }
    }
  }
}

function renderTrend() {
  if (!trendChartRef.value) return
  trendChart ||= echarts.init(trendChartRef.value)
  const dates = trend.value.map((item) => item.metric_date)
  trendChart.setOption({
    ...baseChartOption(),
    tooltip: { ...baseChartOption().tooltip, trigger: 'axis' },
    xAxis: { ...baseChartOption().xAxis, data: dates },
    yAxis: [
      { ...baseChartOption().yAxis, name: '任务数' },
      {
        ...baseChartOption().yAxis,
        name: '成功率',
        min: 0,
        max: 100,
        axisLabel: { color: '#9bc7d9', formatter: '{value}%' }
      }
    ],
    series: [
      {
        name: '任务总数',
        type: 'bar',
        barWidth: 14,
        data: trend.value.map((item) => Number(item.task_count || 0)),
        itemStyle: { color: '#06b6d4', borderRadius: [4, 4, 0, 0] }
      },
      {
        name: '成功率',
        type: 'line',
        yAxisIndex: 1,
        smooth: true,
        symbolSize: 7,
        data: trend.value.map((item) => Number((Number(item.success_rate || 0) * 100).toFixed(2))),
        itemStyle: { color: '#4ade80' },
        lineStyle: { width: 3, color: '#4ade80' },
        areaStyle: { color: 'rgba(74, 222, 128, 0.08)' }
      }
    ]
  }, true)
}

function renderToken() {
  if (!tokenChartRef.value) return
  tokenChart ||= echarts.init(tokenChartRef.value)
  tokenChart.setOption({
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(2, 8, 16, 0.92)',
      borderColor: 'rgba(103, 232, 249, 0.25)',
      textStyle: { color: '#dbe7f3' },
      formatter: (params) => `${params.marker}${params.name}<br/>Token: ${formatNumber(params.data.tokens)}<br/>成本: $${Number(params.data.cost || 0).toFixed(2)}`
    },
    legend: { bottom: 0, textStyle: { color: '#9bc7d9' } },
    series: [
      {
        name: 'Token 消耗',
        type: 'pie',
        radius: ['46%', '72%'],
        center: ['50%', '45%'],
        label: { color: '#dbe7f3', formatter: '{b}\n{d}%' },
        labelLine: { lineStyle: { color: 'rgba(103, 232, 249, 0.35)' } },
        itemStyle: {
          borderColor: 'rgba(6, 18, 31, 0.95)',
          borderWidth: 2,
          shadowBlur: 12,
          shadowColor: 'rgba(34, 211, 238, 0.18)'
        },
        color: ['#22d3ee', '#06b6d4', '#0891b2', '#38bdf8', '#4ade80', '#fbbf24'],
        data: agentStats.value.map((item) => ({
          name: item.agent_role || item.agent_id,
          value: Number(item.total_tokens || 0),
          tokens: Number(item.total_tokens || 0),
          cost: Number(item.estimated_cost_usd || 0)
        }))
      }
    ]
  }, true)
}

function renderErrors() {
  if (!errorChartRef.value) return
  errorChart ||= echarts.init(errorChartRef.value)
  const sorted = [...errors.value].sort((a, b) => Number(a.total_count || 0) - Number(b.total_count || 0))
  errorChart.setOption({
    ...baseChartOption(),
    tooltip: {
      ...baseChartOption().tooltip,
      trigger: 'axis',
      formatter: (params) => {
        const item = params[0]
        return `${item.marker}${item.name}<br/>次数: ${formatNumber(item.value)}<br/>占比: ${percent(sorted[item.dataIndex]?.percentage)}`
      }
    },
    grid: { left: 132, right: 28, top: 34, bottom: 28 },
    xAxis: { ...baseChartOption().xAxis, type: 'value' },
    yAxis: {
      ...baseChartOption().yAxis,
      type: 'category',
      data: sorted.map((item) => formatErrorType(item.error_type)),
      axisLabel: { color: '#9bc7d9', width: 112, overflow: 'truncate' }
    },
    series: [
      {
        name: '错误次数',
        type: 'bar',
        data: sorted.map((item) => Number(item.total_count || 0)),
        itemStyle: { color: '#22d3ee', borderRadius: [0, 4, 4, 0] },
        label: { show: true, position: 'right', color: '#dbe7f3' }
      }
    ]
  }, true)
}

function renderLatency() {
  if (!latencyChartRef.value) return
  latencyChart ||= echarts.init(latencyChartRef.value)
  const names = agentStats.value.map((item) => item.agent_role || item.agent_id)
  latencyChart.setOption({
    ...baseChartOption(),
    xAxis: { ...baseChartOption().xAxis, data: names },
    yAxis: { ...baseChartOption().yAxis, name: 'ms' },
    series: [
      {
        name: '平均时延',
        type: 'line',
        smooth: true,
        data: agentStats.value.map((item) => Number(item.avg_latency_ms || 0)),
        itemStyle: { color: '#22d3ee' },
        lineStyle: { width: 3 },
        areaStyle: { color: 'rgba(34, 211, 238, 0.08)' }
      },
      {
        name: 'P95 时延',
        type: 'line',
        smooth: true,
        data: agentStats.value.map((item) => Number(item.p95_latency_ms || 0)),
        itemStyle: { color: '#fbbf24' },
        lineStyle: { width: 3 },
        areaStyle: { color: 'rgba(251, 191, 36, 0.08)' }
      }
    ]
  }, true)
}

function showLoading() {
  ;[trendChart, tokenChart, errorChart, latencyChart].forEach((chart) => {
    chart?.showLoading('default', {
      text: '加载中',
      color: '#22d3ee',
      textColor: '#dbe7f3',
      maskColor: 'rgba(2, 8, 16, 0.35)'
    })
  })
}

function hideLoading() {
  ;[trendChart, tokenChart, errorChart, latencyChart].forEach((chart) => chart?.hideLoading())
}

function renderCharts() {
  renderTrend()
  renderToken()
  renderErrors()
  renderLatency()
}

function resizeCharts() {
  trendChart?.resize()
  tokenChart?.resize()
  errorChart?.resize()
  latencyChart?.resize()
}

async function loadAll() {
  loading.value = true
  showLoading()
  try {
    const endDate = getTodayString()
    const [trendData, errorData, agentData, dailyData, rankingData] = await Promise.all([
      fetchAnalyticsTrend(),
      fetchAnalyticsErrors(),
      fetchAnalyticsAgentStats(),
      fetchDailyMetrics('2026-06-01', endDate),
      fetchAgentRankings(endDate)
    ])
    trend.value = trendData
    errors.value = errorData
    agentStats.value = agentData
    dailyMetrics.value = dailyData || []
    historyRankings.value = rankingData || []
    await nextTick()
    renderCharts()
  } catch (err) {
    Message.error({ content: `数据统计加载失败: ${err.message || err}`, duration: 5000 })
  } finally {
    hideLoading()
    loading.value = false
  }
}

onMounted(async () => {
  await nextTick()
  renderCharts()
  await loadAll()
  window.addEventListener('resize', resizeCharts)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCharts)
  trendChart?.dispose()
  tokenChart?.dispose()
  errorChart?.dispose()
  latencyChart?.dispose()
})
</script>
