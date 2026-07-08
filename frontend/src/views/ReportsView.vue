<template>
  <div class="page-stack">
    <section class="toolbar report-toolbar">
      <label>
        报告业务日期
        <a-date-picker v-model="date" value-format="YYYY-MM-DD" style="width: 160px;" />
      </label>

      <button class="primary-button" :disabled="isGenerating" @click="createReport">
        <FilePlus2 :size="16" />
        <span>{{ isGenerating ? '生成中...' : '生成报告' }}</span>
      </button>
      <button 
        v-if="report && report.content" 
        class="outline-button" 
        @click="downloadMarkdown"
        style="margin-left: 10px; display: inline-flex; align-items: center; gap: 6px; height: 38px; padding: 0 16px; background: rgba(14, 42, 68, 0.3); border: 1px solid rgba(34, 211, 238, 0.35); border-radius: 4px; color: #67e8f9; cursor: pointer; transition: all 0.2s;"
      >
        <Download :size="16" />
        <span>导出 Markdown</span>
      </button>
    </section>

    <section v-if="reportError" class="panel report-message report-message--error">
      <p>{{ reportError }}</p>
    </section>

    <section v-if="isGenerating" class="panel report-message">
      <p>正在生成报告，请稍候。</p>
    </section>

    <!-- Unified States -->
    <div v-if="isLoadingReport" class="state-wrapper">
      <LoadingState message="正在加载分析报告..." />
    </div>
    <div v-else-if="error" class="state-wrapper">
      <ErrorState :reason="error" @retry="loadLatestReport" />
    </div>
    <div v-else-if="isEmpty" class="state-wrapper">
      <EmptyState message="暂无分析报告，请在上方选择日期并点击「生成报告」。" />
    </div>

    <template v-else>
      <section class="report-hero panel">
        <div class="panel-header">
          <h2>报告概览</h2>
          <span v-if="report.create_time" class="muted">生成时间：{{ report.create_time }}</span>
        </div>

        <div class="report-meta-grid" style="grid-template-columns: 3fr 1fr;">
          <article class="report-meta-card">
            <span>总体结论</span>
            <strong v-html="reportTitleHtml" style="font-size: 16px; display: block; margin-bottom: 8px;"></strong>
            <div v-if="conclusionSection" class="conclusion-content" style="font-size: 13px; line-height: 1.6; color: #aee0f5;">
              <template v-for="(block, bIdx) in conclusionSection.blocks" :key="bIdx">
                <div v-if="block.type === 'paragraph'" v-html="block.html"></div>
                <div v-else-if="block.type === 'list'">
                  <ul style="margin: 4px 0; padding-left: 18px;">
                    <li v-for="(item, iIdx) in block.items" :key="iIdx" v-html="item"></li>
                  </ul>
                </div>
              </template>
            </div>
            <p v-else>{{ reportIntro }}</p>
          </article>
          <article class="report-meta-card">
            <span>内容块</span>
            <strong>{{ displaySections.length }}</strong>
            <p>结构化渲染后的章节数</p>
          </article>
        </div>
      </section>

      <section v-if="displaySections.length" class="report-section-grid">
        <article v-for="(section, sectionIndex) in displaySections" :key="`${section.title}-${sectionIndex}`" class="panel report-section-card">
          <div class="panel-header">
            <h2 v-html="section.titleHtml"></h2>
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
    </template>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { FilePlus2, Download } from '@lucide/vue'
import { Message } from '@arco-design/web-vue'
import { generateReport, fetchReports, fetchReportDetail } from '../api/dashboard'
import { excerptMarkdown, parseMarkdownSections } from '../utils/markdown'
import LoadingState from '../components/LoadingState.vue'
import EmptyState from '../components/EmptyState.vue'
import ErrorState from '../components/ErrorState.vue'

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
const isLoadingReport = ref(true)
const error = ref('')
const isEmpty = ref(false)

async function loadLatestReport() {
  isLoadingReport.value = true
  error.value = ''
  isEmpty.value = false
  try {
    const list = await fetchReports()
    if (list && list.length > 0) {
      const detail = await fetchReportDetail(list[0].report_id)
      report.value = detail
      if (detail.report_date) {
        reportType.value = detail.report_type || 'daily'
      }
      if (!detail.content || detail.content.trim() === '') {
        isEmpty.value = true
      }
    } else {
      isEmpty.value = true
    }
  } catch (e) {
    console.error('Failed to load latest report', e)
    error.value = e.message || '网络连接或后端服务异常'
  } finally {
    isLoadingReport.value = false
  }
}

onMounted(async () => {
  await loadLatestReport()
})

const sections = computed(() => parseMarkdownSections(report.value.content || ''))
const conclusionSection = computed(() => {
  return sections.value.find(s => s.title === '总体结论')
})
const displaySections = computed(() => {
  return sections.value.filter(s => {
    const isTitle = s.title.includes('多智能体系统运行分析报告') || s.title === '内容'
    const isConclusion = s.title === '总体结论'
    return !isTitle && !isConclusion
  })
})
const reportDisplayDate = computed(() => report.value.report_date || date.value)
const reportDisplayType = computed(() => report.value.report_type || reportType.value)
const reportTitle = computed(() => sections.value[0]?.title || 'AI 报告')
const reportTitleHtml = computed(() => sections.value[0]?.titleHtml || 'AI 报告')
const reportIntro = computed(() => {
  const content = String(report.value.content || '')
  return content ? excerptMarkdown(content, 160) : '生成结果会分成多个卡片区块，方便快速阅读和定位。'
})

async function createReport() {
  if (isGenerating.value) return

  isGenerating.value = true
  reportError.value = ''

  try {
    const detail = await generateReport({
      report_date: date.value,
      report_type: reportType.value
    })
    report.value = detail
    if (detail.report_date) {
      date.value = detail.report_date
      reportType.value = detail.report_type || 'daily'
    }
  } catch (error) {
    reportError.value = error?.response?.data?.detail || error?.message || '报告生成失败，请稍后重试。'
  } finally {
    isGenerating.value = false
  }
}

function downloadMarkdown() {
  if (!report.value || !report.value.content) {
    Message.error('没有可导出的报告内容')
    return
  }
  try {
    const blob = new Blob([report.value.content], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    const fileName = `AI_Report_${report.value.report_date || date.value || 'export'}.md`
    link.download = fileName
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
    Message.success('报告已成功导出为 Markdown 文件')
  } catch (err) {
    Message.error('导出失败: ' + err.message)
  }
}
</script>
