<template>
  <div class="page-stack">
    <section class="toolbar">
      <label>
        业务日期
        <input v-model="date" type="date" />
      </label>
      <button class="primary-button" @click="load">
        <RefreshCw :size="16" />
        <span>刷新</span>
      </button>
    </section>
    <section class="panel">
      <div class="panel-header">
        <h2>历史告警</h2>
      </div>
      <table class="data-table">
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
          <tr v-for="alert in alerts" :key="alert.alert_id">
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
    </section>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { RefreshCw } from 'lucide-vue-next'
import { fetchHistoryAlerts } from '../api/dashboard'

const date = ref('2026-06-23')
const alerts = ref([])

async function load() {
  alerts.value = await fetchHistoryAlerts(date.value)
}

onMounted(load)
</script>

