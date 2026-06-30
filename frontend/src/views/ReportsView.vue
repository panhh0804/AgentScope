<template>
  <div class="page-stack">
    <section class="toolbar report-toolbar">
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
      <button class="primary-button" :disabled="isGenerating" @click="createReport">
        <FilePlus2 :size="16" />
        <span>{{ isGenerating ? '生成中...' : '生成报告' }}</span>
      </button>
    </section>

    <section v-if="reportError" class="panel report-message report-message--error">
      <p>{{ reportError }}</p>
    </section>

    <section v-if="isGenerating" class="panel report-message">
      <p>正在生成报告，请稍候。</p>
    </section>

    <section class="report-hero panel">
      <div class="panel-header">
        <h2>报告概览</h2>
        <span v-if="report.create_time" class="muted">{{ report.create_time }}</span>
      </div>

      <div class="report-meta-grid">
        <article class="report-meta-card">
          <span>报告主题</span>
          <strong>{{ reportTitle }}</strong>
          <p>{{ reportIntro }}</p>
        </article>
        <article class="report-meta-card">
          <span>生成参数</span>
          <strong>{{ reportType.toUpperCase() }}</strong>
          <p>{{ date }}</p>
        </article>
        <article class="report-meta-card">
          <span>内容块</span>
          <strong>{{ sections.length }}</strong>
          <p>结构化渲染后的章节数</p>
        </article>
      </div>
    </section>

    <section v-if="sections.length" class="report-section-grid">
      <article v-for="(section, sectionIndex) in sections" :key="`${section.title}-${sectionIndex}`" class="panel report-section-card">
        <div class="panel-header">
          <h2>{{ section.title }}</h2>
          <span>{{ section.blocks.length }} 段</span>
        </div>

        <div class="report-blocks">
          <template v-for="(block, blockIndex) in section.blocks" :key="`${sectionIndex}-${blockIndex}`">
            <div v-if="block.type === 'paragraph'" class="report-block report-block--paragraph" v-html="block.html"></div>
            <div v-else-if="block.type === 'hr'" class="report-block report-block--hr">
              <hr style="border: 0; border-top: 1px dashed rgba(34, 211, 238, 0.25); margin: 15px 0;" />
            </div>
            <div v-else-if="block.type === 'list'" class="report-block report-block--list">
              <ul>
                <li v-for="(item, itemIndex) in block.items" :key="itemIndex" v-html="item"></li>
              </ul>
            </div>
            <div v-else-if="block.type === 'code'" class="report-block report-block--code">
              <span v-if="block.language" class="code-lang">{{ block.language }}</span>
              <pre v-text="block.text"></pre>
            </div>
            <div v-else-if="block.type === 'table'" class="report-block report-block--table table-responsive">
              <table class="data-table screen-native-table markdown-table">
                <thead>
                  <tr>
                    <th v-for="(h, hIdx) in block.headers" :key="hIdx" v-html="h"></th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, rIdx) in block.rows" :key="rIdx">
                    <td v-for="(cell, cIdx) in row" :key="cIdx" v-html="cell"></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </template>
        </div>
      </article>
    </section>

    <section v-else class="panel report-empty">
      <div class="panel-header">
        <h2>报告内容</h2>
      </div>
      <p class="report-empty-text">暂无报告，点击“生成报告”后会以卡片化方式展示结构化内容。</p>
    </section>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { FilePlus2 } from '@lucide/vue'
import { generateReport } from '../api/dashboard'
import { excerptMarkdown, parseMarkdownSections } from '../utils/markdown'

const getTodayString = () => {
  const d = new Date()
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}
const date = ref(getTodayString())
const reportType = ref('daily')
const report = ref({})
const isGenerating = ref(false)
const reportError = ref('')

const sections = computed(() => parseMarkdownSections(report.value.content || ''))
const reportTitle = computed(() => sections.value[0]?.title || 'AI 报告')
const reportIntro = computed(() => {
  const content = String(report.value.content || '')
  return content ? excerptMarkdown(content, 160) : '生成结果会分成多个卡片区块，方便快速阅读和定位。'
})

async function createReport() {
  if (isGenerating.value) return

  isGenerating.value = true
  reportError.value = ''

  try {
    report.value = await generateReport({
      report_date: date.value,
      report_type: reportType.value
    })
  } catch (error) {
    reportError.value = error?.response?.data?.detail || error?.message || '报告生成失败，请稍后重试。'
  } finally {
    isGenerating.value = false
  }
}
</script>
