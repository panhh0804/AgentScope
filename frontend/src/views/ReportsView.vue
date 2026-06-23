<template>
  <div class="page-stack">
    <section class="toolbar">
      <label>
        报告日期
        <input v-model="date" type="date" />
      </label>
      <label>
        报告类型
        <select v-model="reportType">
          <option value="daily">daily</option>
          <option value="weekly">weekly</option>
        </select>
      </label>
      <button class="primary-button" @click="createReport">
        <FilePlus2 :size="16" />
        <span>生成报告</span>
      </button>
    </section>

    <section class="panel report-panel">
      <div class="panel-header">
        <h2>报告内容</h2>
        <span v-if="report.created_at" class="muted">{{ report.created_at }}</span>
      </div>
      <pre>{{ report.content || '暂无报告' }}</pre>
    </section>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { FilePlus2 } from 'lucide-vue-next'
import { generateReport } from '../api/dashboard'

const date = ref('2026-06-23')
const reportType = ref('daily')
const report = ref({})

async function createReport() {
  report.value = await generateReport({
    report_date: date.value,
    report_type: reportType.value
  })
}
</script>

