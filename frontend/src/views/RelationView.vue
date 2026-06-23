<template>
  <div class="page-stack">
    <section class="toolbar">
      <label>
        业务日期
        <input v-model="date" type="date" />
      </label>
      <button class="primary-button" @click="load">
        <Network :size="16" />
        <span>分析</span>
      </button>
    </section>
    <ChartPanel :option="option" />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { Network } from '@lucide/vue'
import ChartPanel from '../components/ChartPanel.vue'
import { fetchRelationGraph } from '../api/dashboard'
import { graphOption } from '../charts/options'

const date = ref('2026-06-23')
const graph = ref({ nodes: [], links: [] })
const option = computed(() => graphOption(graph.value))

async function load() {
  graph.value = await fetchRelationGraph(date.value)
}

onMounted(load)
</script>
