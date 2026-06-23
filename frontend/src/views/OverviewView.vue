<template>
  <div class="page-stack">
    <section class="metric-grid">
      <MetricCard label="运行任务" :value="overview.running_tasks ?? '-'" :icon="PlayCircle" />
      <MetricCard label="活跃 Agent" :value="overview.active_agents ?? '-'" :icon="Bot" />
      <MetricCard label="事件吞吐 / 分钟" :value="overview.events_per_minute ?? '-'" :icon="RadioTower" />
      <MetricCard label="实时错误率" :value="percent(overview.error_rate)" :icon="AlertTriangle" />
      <MetricCard label="平均时延" :value="`${Math.round(overview.avg_latency_ms || 0)} ms`" :icon="Clock3" />
      <MetricCard label="近 5 分钟 Token" :value="formatNumber(overview.token_total_5m)" :icon="Coins" />
      <MetricCard label="未处理告警" :value="overview.open_alerts ?? '-'" :icon="Siren" />
      <MetricCard label="预估成本" :value="`$${Number(overview.estimated_cost_5m || 0).toFixed(4)}`" :icon="BadgeDollarSign" />
    </section>

    <div class="grid-two">
      <ChartPanel :option="throughputOption" />
      <ChartPanel :option="latencyOption" />
    </div>

    <section class="panel">
      <div class="panel-header">
        <h2>最近告警</h2>
      </div>
      <table class="data-table">
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
          <tr v-for="alert in alerts" :key="alert.alert_id">
            <td><span :class="['tag', alert.level]">{{ alert.level }}</span></td>
            <td>{{ alert.alert_type }}</td>
            <td>{{ alert.agent_id }}</td>
            <td>{{ alert.current_value }}</td>
            <td>{{ alert.threshold }}</td>
            <td>{{ alert.created_at }}</td>
          </tr>
        </tbody>
      </table>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { AlertTriangle, BadgeDollarSign, Bot, Clock3, Coins, PlayCircle, RadioTower, Siren } from '@lucide/vue'
import ChartPanel from '../components/ChartPanel.vue'
import MetricCard from '../components/MetricCard.vue'
import { fetchOverview, fetchRealtimeAlerts, fetchTrend } from '../api/dashboard'
import { lineOption } from '../charts/options'

const overview = ref({})
const trend = ref([])
const alerts = ref([])

const throughputOption = computed(() => {
  const xData = trend.value.map((item) => item.time?.slice(11, 16))
  return lineOption('最近 60 分钟吞吐', xData, [
    { name: '事件数', type: 'line', smooth: true, data: trend.value.map((item) => item.events), areaStyle: {}, lineStyle: { color: '#2563eb' } },
    { name: '失败数', type: 'line', smooth: true, data: trend.value.map((item) => item.failed), lineStyle: { color: '#dc2626' } }
  ])
})

const latencyOption = computed(() => {
  const xData = trend.value.map((item) => item.time?.slice(11, 16))
  return lineOption('平均时延趋势', xData, [
    { name: '平均时延 ms', type: 'line', smooth: true, data: trend.value.map((item) => item.avg_latency_ms), lineStyle: { color: '#0891b2' } }
  ])
})

function percent(value) {
  return `${Number((value || 0) * 100).toFixed(1)}%`
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString()
}

async function load() {
  const [overviewData, trendData, alertData] = await Promise.all([
    fetchOverview(),
    fetchTrend(60),
    fetchRealtimeAlerts()
  ])
  overview.value = overviewData
  trend.value = trendData
  alerts.value = alertData
}

onMounted(load)
</script>
