<template>
  <section class="panel">
    <div ref="el" class="chart"></div>
  </section>
</template>

<script setup>
import * as echarts from 'echarts'
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  option: { type: Object, required: true },
  refreshKey: { type: [String, Number], default: 0 }
})

const el = ref(null)
let chart = null

function waitForFrame() {
  return new Promise((resolve) => requestAnimationFrame(() => resolve()))
}

async function ensureContainer(attempts = 8) {
  for (let i = 0; i < attempts; i += 1) {
    if (el.value && el.value.clientWidth > 0 && el.value.clientHeight > 0) return true
    await new Promise((resolve) => setTimeout(resolve, 60))
    await waitForFrame()
  }
  return Boolean(el.value)
}

async function render(options = {}) {
  await nextTick()
  const ready = await ensureContainer()
  if (!ready || !el.value) return
  if (!chart) chart = echarts.init(el.value)
  if (options.replay) chart.clear()
  chart.setOption(props.option, true)
  await waitForFrame()
  chart.resize()
}

function resize() {
  if (chart) chart.resize()
}

onMounted(() => {
  render()
  window.addEventListener('resize', resize)
})

watch(() => props.option, () => render(), { deep: true })

watch(() => props.refreshKey, () => render({ replay: true }))

onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  if (chart) chart.dispose()
})
</script>

