<template>
  <section class="screen-page statistics-page">
    <div class="screen-board statistics-board">
      <header class="screen-titlebar">
        <div>
          <p class="screen-kicker">多维离线指标统计与效能评估</p>
          <h2>数据统计分析端</h2>
        </div>
        <div class="screen-tools">
          <a-button type="primary" size="large" :loading="loading" :disabled="loading" @click="loadAll({ force: true })">刷新</a-button>
        </div>
      </header>

      <!-- Unified States overlay/container -->
      <div v-if="loading && !hasLoaded" class="state-wrapper">
        <LoadingState message="正在加载数据统计与分析指标..." />
      </div>
      <div v-else-if="error && !hasLoaded" class="state-wrapper">
        <ErrorState :reason="error" @retry="loadAll" />
      </div>
      <div v-else-if="isEmpty && !hasLoaded" class="state-wrapper">
        <EmptyState />
      </div>

      <template v-if="hasLoaded || (!loading && !error && !isEmpty)">
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
      </template>
    </div>
  </section>
</template>

<script setup>
/**
 * StatisticsView.vue —— 数据统计分析端的多维离线指标统计与效能评估页面
 * 
 * 主要职责：
 *   - 并发加载历史 30 天运行数据、Token/成本消耗、异常分类分布以及分位数时延。
 *   - 通过 ECharts 提供四类离线深度分析图表：
 *     1. 任务量与运行成功率双轴图 (TrendChart)
 *     2. Agent Token 消耗占比环形饼图 (TokenChart)
 *     3. 系统异常类型与分布水平柱状图 (ErrorChart)
 *     4. Agent 平均与 P95 延迟折线对比图 (LatencyChart)
 *   - 支持从 KeepAlive 激活时 (onActivated) 重新布局重置大小 (resizeCharts)，保证图表尺寸自适应。
 */

import { computed, nextTick, onActivated, onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { Message } from '@arco-design/web-vue'
import ChartPanel from '../components/ChartPanel.vue'
import LoadingState from '../components/LoadingState.vue'
import EmptyState from '../components/EmptyState.vue'
import ErrorState from '../components/ErrorState.vue'
import { fetchDailyMetrics, fetchAgentRankings } from '../api/dashboard'
import {
  fetchAnalyticsAgentStats,
  fetchAnalyticsErrors,
  fetchAnalyticsTrend
} from '../api/statistics'
import { barOption, lineOption } from '../charts/options'

// === 1. 状态管理与数据源 ===
const loading = ref(true)          // 页面首次整体载入遮罩
const error = ref('')              // 异常抛错信息
const isEmpty = ref(false)          // 是否没有可读指标
const hasLoaded = ref(false)        // 标记是否已经完成首轮拉取
let loadPromise = null              // 单例 Promise 缓存，防并发重入

const trend = ref([])               // 近 30 天每日总执行次数与成功率
const errors = ref([])              // 各种运行时异常的发生频度
const agentStats = ref([])          // 各智能体近期的流量、时延、消耗成本汇总
const dailyMetrics = ref([])        // 大盘折线用：每日吞吐量指标
const historyRankings = ref([])     // 历史排行榜排行条目

// === 2. ECharts 实例及容器 ref ===
const trendChartRef = ref(null)
const tokenChartRef = ref(null)
const errorChartRef = ref(null)
const latencyChartRef = ref(null)

let trendChart
let tokenChart
let errorChart
let latencyChart

// 计算今日汇总顶部的数值指标卡片数据
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

// 时间滑窗天数标签说明
const trendPeriodLabel = computed(() => `近 ${trend.value.length || 0} 天`)

// Agent 执行次数排行榜 ECharts 配置
const historyRankingOption = computed(() => {
  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(2, 8, 16, 0.92)',
      borderColor: 'rgba(103, 232, 249, 0.25)',
      textStyle: { color: '#dbe7f3' }
    },
    grid: { top: 38, right: 18, bottom: 42, left: 48, containLabel: true },
    xAxis: {
      type: 'category',
      data: historyRankings.value.map((item) => item.agent_role),
      axisLabel: { color: '#9bc7d9', rotate: 18, fontSize: 11 },
      axisLine: { lineStyle: { color: 'rgba(103, 232, 249, 0.22)' } }
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#9bc7d9' },
      axisLine: { lineStyle: { color: 'rgba(103, 232, 249, 0.22)' } },
      splitLine: { lineStyle: { color: 'rgba(103, 232, 249, 0.08)' } }
    },
    series: [{
      name: '执行次数',
      type: 'bar',
      barWidth: 16,
      data: historyRankings.value.map((item) => item.execution_count),
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: '#22d3ee' },
          { offset: 1, color: '#0891b2' }
        ]),
        borderRadius: [4, 4, 0, 0]
      }
    }]
  }
})

// 每日 Token 与成本消耗双 Y 轴折线图 ECharts 配置
const historyCostOption = computed(() => {
  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(2, 8, 16, 0.92)',
      borderColor: 'rgba(103, 232, 249, 0.25)',
      textStyle: { color: '#dbe7f3' },
      formatter: historyTooltipFormatter
    },
    legend: {
      top: 0,
      right: 8,
      textStyle: { color: '#9bc7d9' }
    },
    grid: { top: 38, right: 48, bottom: 32, left: 48, containLabel: true },
    xAxis: {
      type: 'category',
      data: dailyMetrics.value.map((item) => formatShortDate(item.metric_date)),
      boundaryGap: ['4%', '8%'],
      axisLabel: { color: '#9bc7d9' },
      axisLine: { lineStyle: { color: 'rgba(103, 232, 249, 0.22)' } }
    },
    yAxis: [
      {
        type: 'value',
        name: 'Tokens',
        nameTextStyle: { color: '#9bc7d9', fontSize: 10 },
        axisLabel: {
          color: '#9bc7d9',
          formatter: (value) => value >= 1000000 ? `${(value / 1000000).toFixed(1)}M` : `${Math.round(value / 1000)}k`
        },
        axisLine: { lineStyle: { color: 'rgba(103, 232, 249, 0.22)' } },
        splitLine: { lineStyle: { color: 'rgba(103, 232, 249, 0.08)' } }
      },
      {
        type: 'value',
        name: '成本 ($)',
        nameTextStyle: { color: '#9bc7d9', fontSize: 10 },
        axisLabel: { color: '#9bc7d9', formatter: '${value}' },
        axisLine: { lineStyle: { color: 'rgba(103, 232, 249, 0.22)' } },
        splitLine: { show: false }
      }
    ],
    series: [
      {
        name: '每日 Token',
        type: 'line',
        smooth: true,
        symbol: 'none',
        yAxisIndex: 0,
        data: dailyMetrics.value.map((item) => item.total_tokens),
        itemStyle: { color: '#06b6d4' },
        lineStyle: { width: 3 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(6, 182, 212, 0.16)' },
            { offset: 1, color: 'rgba(6, 182, 212, 0.01)' }
          ])
        }
      },
      {
        name: '每日成本 ($)',
        type: 'line',
        smooth: true,
        symbol: 'none',
        yAxisIndex: 1,
        data: dailyMetrics.value.map((item) => item.estimated_cost_usd),
        itemStyle: { color: '#10b981' },
        lineStyle: { width: 3 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(16, 185, 129, 0.12)' },
            { offset: 1, color: 'rgba(16, 185, 129, 0.01)' }
          ])
        }
      }
    ]
  }
})

// 错误分类词典
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

// 统一的基础 ECharts 全局排版背景样式配置项
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

// 无指标时的图形文字占位
function emptyGraphic(text = '暂无数据') {
  return {
    type: 'text',
    left: 'center',
    top: 'middle',
    style: {
      text,
      fill: '#9bc7d9',
      fontSize: 14,
      fontWeight: 500
    }
  }
}

function waitForFrame() {
  return new Promise((resolve) => requestAnimationFrame(() => resolve()))
}

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

// 防 clientWidth / clientHeight == 0 时的图形加载空白自愈
async function ensureChartContainer(elRef, attempts = 8) {
  for (let i = 0; i < attempts; i += 1) {
    const el = elRef.value
    if (el && el.clientWidth > 0 && el.clientHeight > 0) return el
    await wait(60)
    await waitForFrame()
  }
  return elRef.value
}

function ensureChart(elRef, currentChart) {
  const el = elRef.value
  if (!el || el.clientWidth === 0 || el.clientHeight === 0) return currentChart
  return currentChart || echarts.init(el)
}

/**
 * 绘制 1. 任务量与运行成功率双轴折线+柱状图
 */
function renderTrend() {
  if (!trendChartRef.value) return
  trendChart = ensureChart(trendChartRef, trendChart)
  if (!trendChart) return
  const dates = trend.value.map((item) => item.metric_date)
  trendChart.setOption({
    ...baseChartOption(),
    graphic: trend.value.length ? [] : emptyGraphic('暂无每日指标数据'),
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
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#22d3ee' },
            { offset: 1, color: '#0891b2' }
          ]),
          borderRadius: [4, 4, 0, 0]
        }
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
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(74, 222, 128, 0.2)' },
            { offset: 1, color: 'rgba(74, 222, 128, 0.01)' }
          ])
        }
      }
    ]
  }, true)
  trendChart.resize()
}

/**
 * 绘制 2. Agent Token 消耗分布饼图
 */
function renderToken() {
  if (!tokenChartRef.value) return
  tokenChart = ensureChart(tokenChartRef, tokenChart)
  if (!tokenChart) return
  tokenChart.setOption({
    backgroundColor: 'transparent',
    graphic: agentStats.value.length ? [] : emptyGraphic('暂无 Agent 消耗数据'),
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
        color: [
          new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: '#22d3ee' }, { offset: 1, color: '#0891b2' }]),
          new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: '#38bdf8' }, { offset: 1, color: '#0284c7' }]),
          new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: '#60a5fa' }, { offset: 1, color: '#1d4ed8' }]),
          new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: '#06b6d4' }, { offset: 1, color: '#0e7490' }]),
          new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: '#a5f3fc' }, { offset: 1, color: '#0891b2' }]),
          new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: '#818cf8' }, { offset: 1, color: '#4f46e5' }])
        ],
        data: agentStats.value.map((item) => ({
          name: item.agent_role || item.agent_id,
          value: Number(item.total_tokens || 0),
          tokens: Number(item.total_tokens || 0),
          cost: Number(item.estimated_cost_usd || 0)
        }))
      }
    ]
  }, true)
  tokenChart.resize()
}

/**
 * 绘制 3. 系统异常类型与错误分布条形图
 */
function renderErrors() {
  if (!errorChartRef.value) return
  errorChart = ensureChart(errorChartRef, errorChart)
  if (!errorChart) return
  const sorted = [...errors.value].sort((a, b) => Number(a.total_count || 0) - Number(b.total_count || 0))
  errorChart.setOption({
    ...baseChartOption(),
    graphic: sorted.length ? [] : emptyGraphic('暂无异常数据'),
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
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: '#0e7490' },
            { offset: 1, color: '#22d3ee' }
          ]),
          borderRadius: [0, 4, 4, 0]
        },
        label: { show: true, position: 'right', color: '#dbe7f3' }
      }
    ]
  }, true)
  errorChart.resize()
}

/**
 * 绘制 4. 时延及百分时延分位数延迟折线图
 */
function renderLatency() {
  if (!latencyChartRef.value) return
  latencyChart = ensureChart(latencyChartRef, latencyChart)
  if (!latencyChart) return
  const names = agentStats.value.map((item) => item.agent_role || item.agent_id)
  latencyChart.setOption({
    ...baseChartOption(),
    graphic: agentStats.value.length ? [] : emptyGraphic('暂无时延数据'),
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
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(34, 211, 238, 0.2)' },
            { offset: 1, color: 'rgba(34, 211, 238, 0.01)' }
          ])
        }
      },
      {
        name: 'P95 时延',
        type: 'line',
        smooth: true,
        data: agentStats.value.map((item) => Number(item.p95_latency_ms || 0)),
        itemStyle: { color: '#fbbf24' },
        lineStyle: { width: 3 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(251, 191, 36, 0.2)' },
            { offset: 1, color: 'rgba(251, 191, 36, 0.01)' }
          ])
        }
      }
    ]
  }, true)
  latencyChart.resize()
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
  try {
    renderTrend()
  } catch (err) {
    console.error('Failed to render statistics trend chart', err)
  }
  try {
    renderToken()
  } catch (err) {
    console.error('Failed to render statistics token chart', err)
  }
  try {
    renderErrors()
  } catch (err) {
    console.error('Failed to render statistics error chart', err)
  }
  try {
    renderLatency()
  } catch (err) {
    console.error('Failed to render statistics latency chart', err)
  }
}

function resizeCharts() {
  trendChart?.resize()
  tokenChart?.resize()
  errorChart?.resize()
  latencyChart?.resize()
}

async function scheduleChartRender() {
  await nextTick()
  await Promise.all([
    ensureChartContainer(trendChartRef),
    ensureChartContainer(tokenChartRef),
    ensureChartContainer(errorChartRef),
    ensureChartContainer(latencyChartRef)
  ])
  await waitForFrame()
  renderCharts()
  resizeCharts()
}

function updateArrayIfUseful(result, target, label) {
  if (result.status !== 'fulfilled') {
    console.warn(`Failed to load ${label}`, result.reason)
    return false
  }
  if (!Array.isArray(result.value)) {
    console.warn(`Unexpected ${label} payload`, result.value)
    return false
  }
  if (result.value.length === 0 && target.value.length > 0) {
    console.info(`${label} returned empty data, keeping previous chart data`)
    return false
  }
  target.value = result.value
  return true
}

/**
 * 离线拉取核心：拉取趋势数据、异常类型分布、Agent 消耗等指标
 */
async function loadAll(options = {}) {
  if (loadPromise) return loadPromise
  loading.value = true
  error.value = ''
  isEmpty.value = false
  showLoading()
  loadPromise = (async () => {
    const endDate = getTodayString()
    const results = await Promise.allSettled([
      fetchAnalyticsTrend(),
      fetchAnalyticsErrors(),
      fetchAnalyticsAgentStats(),
      fetchDailyMetrics('2026-06-01', endDate),
      fetchAgentRankings(endDate)
    ])

    const changed = [
      updateArrayIfUseful(results[0], trend, 'analytics trend'),
      updateArrayIfUseful(results[1], errors, 'error distribution'),
      updateArrayIfUseful(results[2], agentStats, 'agent statistics'),
      updateArrayIfUseful(results[3], dailyMetrics, 'daily metrics'),
      updateArrayIfUseful(results[4], historyRankings, 'agent rankings')
    ].some(Boolean)

    if (!trend.value.length && !agentStats.value.length && !hasLoaded.value) {
      isEmpty.value = true
    }

    hasLoaded.value = true
    if (!changed && hasLoaded.value && !isEmpty.value && options.force) {
      Message.info({ content: '统计数据暂无更新，已保留当前图表', duration: 2500 })
    }
  })().catch((err) => {
    console.error('Failed to load statistics', err)
    if (!hasLoaded.value) {
      error.value = err.message || '网络连接或后端服务异常'
    } else {
      Message.warning({ content: '刷新失败，已保留当前统计图表', duration: 3000 })
    }
  }).finally(async () => {
    hideLoading()
    loading.value = false
    loadPromise = null
    if (!error.value && (!isEmpty.value || hasLoaded.value)) {
      await scheduleChartRender()
    }
  })
  return loadPromise
}

onMounted(async () => {
  await nextTick()
  await loadAll()
  window.addEventListener('resize', resizeCharts)
})

onActivated(async () => {
  await nextTick()
  await waitForFrame()
  resizeCharts()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCharts)
  trendChart?.dispose()
  tokenChart?.dispose()
  errorChart?.dispose()
  latencyChart?.dispose()
})
</script>
