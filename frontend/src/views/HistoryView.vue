<template>
  <div class="page-stack">
    <section class="toolbar">
      <label>
        开始日期
        <input v-model="startDate" type="date" />
      </label>
      <label>
        结束日期
        <input v-model="endDate" type="date" />
      </label>
      <button class="primary-button" @click="load">
        <Search :size="16" />
        <span>查询</span>
      </button>
    </section>

    <div class="grid-two">
      <ChartPanel :option="taskOption" />
      <ChartPanel :option="successOption" />
    </div>
    <div class="grid-two">
      <ChartPanel :option="latencyOption" />
      <ChartPanel :option="rankingOption" />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { Search } from 'lucide-vue-next'
import ChartPanel from '../components/ChartPanel.vue'
import { fetchAgentRankings, fetchDailyMetrics } from '../api/dashboard'
import { barOption, lineOption } from '../charts/options'

const today = '2026-06-23'
const startDate = ref('2026-06-01')
const endDate = ref(today)
const daily = ref([])
const rankings = ref([])

const taskOption = computed(() => lineOption('每日任务量', daily.value.map((item) => item.metric_date), [
  { name: '任务数', type: 'line', smooth: true, data: daily.value.map((item) => item.task_count), lineStyle: { color: '#2563eb' } }
]))

const successOption = computed(() => lineOption('每日成功率', daily.value.map((item) => item.metric_date), [
  { name: '成功率', type: 'line', smooth: true, data: daily.value.map((item) => Number(item.success_rate) * 100), lineStyle: { color: '#16a34a' } }
]))

const latencyOption = computed(() => lineOption('平均 / P95 时延', daily.value.map((item) => item.metric_date), [
  { name: '平均时延', type: 'line', smooth: true, data: daily.value.map((item) => item.avg_latency_ms), lineStyle: { color: '#0891b2' } },
  { name: 'P95 时延', type: 'line', smooth: true, data: daily.value.map((item) => item.p95_latency_ms), lineStyle: { color: '#dc2626' } }
]))

const rankingOption = computed(() => barOption(
  'Agent 执行次数排行',
  rankings.value.map((item) => item.agent_role),
  rankings.value.map((item) => item.execution_count),
  '执行次数'
))

async function load() {
  const [dailyData, rankingData] = await Promise.all([
    fetchDailyMetrics(startDate.value, endDate.value),
    fetchAgentRankings(endDate.value)
  ])
  daily.value = dailyData
  rankings.value = rankingData
}

onMounted(load)
</script>

