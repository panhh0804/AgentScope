<template>
  <section class="panel">
    <div class="panel-header">
      <h2>Agent 当前状态</h2>
      <button class="icon-button" @click="load" title="刷新">
        <RefreshCw :size="16" />
      </button>
    </div>
    <table class="data-table">
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
        <tr v-for="agent in agents" :key="agent.agent_id">
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
  </section>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { RefreshCw } from 'lucide-vue-next'
import { fetchAgents } from '../api/dashboard'

const agents = ref([])

function percent(value) {
  return `${Number((value || 0) * 100).toFixed(1)}%`
}

async function load() {
  agents.value = await fetchAgents()
}

onMounted(load)
</script>

