<template>
  <section class="screen-page data-admin-page">
    <div class="screen-board data-admin-board">
      <header class="screen-titlebar">
        <div>
          <p class="screen-kicker">离线数据链路与数据治理</p>
          <h2>数据管理端</h2>
        </div>
        <div class="screen-tools">
          <a-date-picker v-model="bizDate" value-format="YYYY-MM-DD" size="large" />
          <a-button type="primary" size="large" @click="loadAll">刷新</a-button>
        </div>
      </header>

      <a-tabs v-model:active-key="activeTab" class="admin-tabs">
        <a-tab-pane key="overview" title="数据总览">
          <section class="screen-metrics admin-metrics">
            <article v-for="metric in overviewMetrics" :key="metric.label" class="screen-metric">
              <span>{{ metric.label }}</span>
              <strong>{{ metric.value }}</strong>
              <small>{{ metric.hint }}</small>
            </article>
          </section>

          <section class="admin-overview-grid">
            <article class="screen-panel">
              <div class="screen-panel-head">
                <h3>Source -> Raw -> Clean -> Metric 漏斗</h3>
                <span>{{ overview.recent_failed_task ? `最近失败 ${overview.recent_failed_task}` : 'pipeline' }}</span>
              </div>
              <div ref="funnelChartRef" class="screen-chart" style="height: 240px; margin-top: 10px;"></div>
            </article>

            <article class="screen-panel">
              <div class="screen-panel-head">
                <h3>最近 7 天数据量趋势</h3>
                <span>Raw / Clean</span>
              </div>
              <div ref="trendChartRef" class="screen-chart"></div>
            </article>

            <article class="screen-panel">
              <div class="screen-panel-head">
                <h3>各数据层最新更新时间</h3>
                <span>{{ overview.quality_issue_pending_count || 0 }} quality issues</span>
              </div>
              <div class="admin-list">
                <div v-for="item in overview.layer_update_times || []" :key="item.layer" class="admin-list-row">
                  <span>{{ item.layer }}</span>
                  <strong>{{ item.latest_update_time }}</strong>
                </div>
              </div>
            </article>

            <article class="screen-panel">
              <div class="screen-panel-head">
                <h3>离线链路状态</h3>
                <span>{{ pipeline.nodes?.length || 0 }} nodes</span>
              </div>
              <div class="pipeline-strip">
                <template v-for="(node, index) in pipeline.nodes || []" :key="node.code">
                  <div class="pipeline-node">
                    <span>{{ node.name }}</span>
                    <strong>{{ formatNumber(node.count) }}</strong>
                    <small :class="['tag', node.status]">{{ node.status }}</small>
                  </div>
                  <i v-if="index < (pipeline.nodes || []).length - 1"></i>
                </template>
              </div>
            </article>
          </section>
        </a-tab-pane>

        <a-tab-pane key="events" title="原始数据管理">
          <section class="toolbar admin-filter">
            <label>trace_id<input v-model="eventFilters.trace_id" /></label>
            <label>run_id<input v-model="eventFilters.run_id" /></label>
            <label>agent_id<input v-model="eventFilters.agent_id" /></label>
            <label>event_type<input v-model="eventFilters.event_type" /></label>
            <label>status<select v-model="eventFilters.status"><option value="">全部</option><option>success</option><option>failed</option></select></label>
            <a-button type="primary" @click="loadEvents">筛选</a-button>
          </section>
          <section class="screen-panel">
            <div class="screen-panel-head">
              <h3>Agent 原始事件</h3>
              <span>{{ events.length }} records</span>
            </div>
            <div class="screen-table-wrap">
              <table class="data-table screen-native-table admin-table">
                <thead>
                  <tr>
                    <th>event_id</th>
                    <th>trace_id</th>
                    <th>run_id</th>
                    <th>agent_id</th>
                    <th>event_type</th>
                    <th>status</th>
                    <th>event_time</th>
                    <th>latency_ms</th>
                    <th>JSON</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="event in events" :key="event.event_id">
                    <td>{{ event.event_id }}</td>
                    <td>{{ event.trace_id }}</td>
                    <td>{{ event.run_id }}</td>
                    <td>{{ event.agent_id }}</td>
                    <td>{{ event.event_type }}</td>
                    <td><span :class="['tag', event.status]">{{ event.status }}</span></td>
                    <td>{{ event.event_time }}</td>
                    <td>{{ event.latency_ms }}</td>
                    <td><a-button size="mini" @click="showJson(event.raw_json)">查看</a-button></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        </a-tab-pane>

        <a-tab-pane key="assets" title="数据资产管理">
          <section class="admin-assets-grid">
            <article class="screen-panel">
              <div class="screen-panel-head">
                <h3>数据集目录</h3>
                <span>{{ datasets.length }} datasets</span>
              </div>
              <div class="screen-table-wrap">
                <table class="data-table screen-native-table">
                  <thead>
                    <tr><th>数据集</th><th>存储</th><th>层级</th><th>数据量</th><th>最新业务日期</th></tr>
                  </thead>
                  <tbody>
                    <tr v-for="dataset in datasets" :key="dataset.dataset_code">
                      <td>{{ dataset.dataset_name }}</td>
                      <td>{{ dataset.storage }}</td>
                      <td><span class="tag">{{ dataset.layer }}</span></td>
                      <td>{{ formatNumber(dataset.row_count) }}</td>
                      <td>{{ dataset.latest_biz_date }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </article>
            <article class="screen-panel">
              <div class="screen-panel-head">
                <h3>简化数据血缘</h3>
                <span>Source to Analytics</span>
              </div>
              <div ref="lineageChartRef" class="screen-chart" style="height: 280px; margin-top: 10px;"></div>
            </article>
          </section>
        </a-tab-pane>

        <a-tab-pane key="jobs" title="数据任务管理">
          <!-- Scheduling and Pipeline Banner -->
          <div class="scheduler-banner">
            <div class="banner-icon">⏰</div>
            <div class="banner-content">
              <h4>自动调度与数据补数说明</h4>
              <p>离线计算流水线在生产环境中由 <strong>Crontab 定时任务（每天凌晨 02:00）</strong> 自动触发运行。此控制台主要用于开发与运维进行历史日期补数（Backfill）或失败作业的手动重试。运行前请确认源数据库（MySQL Source）在所选业务日期是否有数据。</p>
            </div>
          </div>

          <section class="screen-panel">
            <div class="screen-panel-head">
              <h3>白名单任务流水线</h3>
              <a-button 
                type="primary" 
                :loading="pipelineRunning" 
                :disabled="anyJobRunning" 
                @click="runFullPipeline"
              >
                {{ pipelineRunning ? '整条链路执行中...' : '一键执行完整离线链路' }}
              </a-button>
            </div>

            <!-- Horizontal Pipeline Workflow Layout -->
            <div class="pipeline-flow-layout">
              <!-- Stage 1 -->
              <div class="pipeline-stage-box">
                <div class="stage-badge">01</div>
                <div class="stage-info">
                  <h4>数据接入</h4>
                  <small>Source ➔ Raw (DataX)</small>
                </div>
                <div class="stage-body">
                  <div v-for="job in getJobsByStage(1)" :key="job.job_code" class="pipeline-job-item">
                    <div class="job-meta">
                      <h5>{{ job.job_name }}</h5>
                      <code>{{ job.job_code }}</code>
                    </div>
                    <a-button 
                      size="small" 
                      type="outline" 
                      :loading="runningJobs[job.job_code]" 
                      :disabled="anyJobRunning" 
                      @click="runJob(job.job_code)"
                    >
                      {{ runningJobs[job.job_code] ? '运行中' : '执行' }}
                    </a-button>
                  </div>
                </div>
              </div>

              <div class="pipeline-flow-arrow">➔</div>

              <!-- Stage 2 -->
              <div class="pipeline-stage-box">
                <div class="stage-badge">02</div>
                <div class="stage-info">
                  <h4>数据清洗</h4>
                  <small>Raw ➔ Clean (Spark)</small>
                </div>
                <div class="stage-body">
                  <div v-for="job in getJobsByStage(2)" :key="job.job_code" class="pipeline-job-item">
                    <div class="job-meta">
                      <h5>{{ job.job_name }}</h5>
                      <code>{{ job.job_code }}</code>
                    </div>
                    <a-button 
                      size="small" 
                      type="outline" 
                      :loading="runningJobs[job.job_code]" 
                      :disabled="anyJobRunning" 
                      @click="runJob(job.job_code)"
                    >
                      {{ runningJobs[job.job_code] ? '运行中' : '执行' }}
                    </a-button>
                  </div>
                </div>
              </div>

              <div class="pipeline-flow-arrow">➔</div>

              <!-- Stage 3 -->
              <div class="pipeline-stage-box stage-box-wide">
                <div class="stage-badge">03</div>
                <div class="stage-info">
                  <h4>多维离线计算</h4>
                  <small>Clean ➔ Metrics (Spark Batch)</small>
                </div>
                <div class="stage-body stage-body-grid">
                  <div v-for="job in getJobsByStage(3)" :key="job.job_code" class="pipeline-job-item">
                    <div class="job-meta">
                      <h5>{{ job.job_name }}</h5>
                      <code>{{ job.job_code }}</code>
                    </div>
                    <a-button 
                      size="small" 
                      type="outline" 
                      :loading="runningJobs[job.job_code]" 
                      :disabled="anyJobRunning" 
                      @click="runJob(job.job_code)"
                    >
                      {{ runningJobs[job.job_code] ? '运行中' : '执行' }}
                    </a-button>
                  </div>
                </div>
              </div>

              <div class="pipeline-flow-arrow">➔</div>

              <!-- Stage 4 -->
              <div class="pipeline-stage-box">
                <div class="stage-badge">04</div>
                <div class="stage-info">
                  <h4>报告生成</h4>
                  <small>Decision Support (LLM)</small>
                </div>
                <div class="stage-body">
                  <div v-for="job in getJobsByStage(4)" :key="job.job_code" class="pipeline-job-item">
                    <div class="job-meta">
                      <h5>{{ job.job_name }}</h5>
                      <code>{{ job.job_code }}</code>
                    </div>
                    <a-button 
                      size="small" 
                      type="outline" 
                      :loading="runningJobs[job.job_code]" 
                      :disabled="anyJobRunning" 
                      @click="runJob(job.job_code)"
                    >
                      {{ runningJobs[job.job_code] ? '运行中' : '执行' }}
                    </a-button>
                  </div>
                </div>
              </div>
            </div>
          </section>
          <section class="screen-panel">
            <div class="screen-panel-head">
              <h3>任务运行记录</h3>
              <span>{{ jobRuns.length }} runs</span>
            </div>
            <div class="screen-table-wrap">
              <table class="data-table screen-native-table admin-table">
                <thead>
                  <tr><th>run_id</th><th>job_code</th><th>biz_date</th><th>状态</th><th>输入</th><th>输出</th><th>异常</th><th>开始</th><th>结束</th><th>耗时</th><th>日志</th><th>操作</th></tr>
                </thead>
                <tbody>
                  <tr v-for="run in jobRuns" :key="run.run_id">
                    <td>{{ run.run_id }}</td>
                    <td>{{ run.job_code }}</td>
                    <td>{{ run.biz_date }}</td>
                    <td><span :class="['tag', run.status]">{{ run.status }}</span></td>
                    <td>{{ formatNumber(run.input_count) }}</td>
                    <td>{{ formatNumber(run.output_count) }}</td>
                    <td>{{ run.error_count }}</td>
                    <td>{{ run.start_time }}</td>
                    <td>{{ run.end_time || '-' }}</td>
                    <td>{{ run.duration_seconds ?? '-' }}s</td>
                    <td><a-button size="mini" @click="showLogs(run.run_id)">查看</a-button></td>
                    <td><a-button size="mini" :disabled="run.status !== 'failed'" @click="retryRun(run.run_id)">重试</a-button></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        </a-tab-pane>

        <a-tab-pane key="quality" title="数据质量管理">
          <section class="screen-metrics admin-metrics">
            <article class="screen-metric">
              <span>质量规则</span><strong>{{ qualityOverview.rule_count || 0 }}</strong><small>enabled rules</small>
            </article>
            <article class="screen-metric">
              <span>问题总数</span><strong>{{ qualityOverview.issue_count || 0 }}</strong><small>failed rows</small>
            </article>
            <article class="screen-metric">
              <span>平均通过率</span><strong>{{ percent(qualityOverview.avg_pass_rate) }}</strong><small>all rules</small>
            </article>
            <article class="screen-metric">
              <span>待处理问题</span><strong>{{ qualityOverview.pending_count || 0 }}</strong><small>pending</small>
            </article>
          </section>
          <section class="screen-panel">
            <div class="screen-panel-head">
              <h3>质量问题明细</h3>
              <span>{{ qualityIssues.length }} rules</span>
            </div>
            <div class="screen-table-wrap">
              <table class="data-table screen-native-table">
                <thead>
                  <tr><th>rule_code</th><th>rule_name</th><th>dataset_code</th><th>biz_date</th><th>total</th><th>failed</th><th>pass_rate</th><th>sample_data_json</th></tr>
                </thead>
                <tbody>
                  <tr v-for="issue in qualityIssues" :key="issue.rule_code">
                    <td>{{ issue.rule_code }}</td>
                    <td>{{ issue.rule_name }}</td>
                    <td>{{ issue.dataset_code }}</td>
                    <td>{{ issue.biz_date }}</td>
                    <td>{{ formatNumber(issue.total_count) }}</td>
                    <td>{{ issue.failed_count }}</td>
                    <td>{{ percent(issue.pass_rate) }}</td>
                    <td><a-button size="mini" @click="showJson(issue.sample_data_json)">查看样本</a-button></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        </a-tab-pane>

        <a-tab-pane key="audit" title="操作审计">
          <section class="screen-panel">
            <div class="screen-panel-head">
              <h3>操作审计</h3>
              <span>{{ auditLogs.length }} records</span>
            </div>
            <div class="screen-table-wrap">
              <table class="data-table screen-native-table">
                <thead>
                  <tr><th>operator</th><th>operation_type</th><th>resource_type</th><th>resource_id</th><th>operation_result</th><th>created_at</th></tr>
                </thead>
                <tbody>
                  <tr v-for="log in auditLogs" :key="log.audit_id">
                    <td>{{ log.operator }}</td>
                    <td>{{ log.operation_type }}</td>
                    <td>{{ log.resource_type }}</td>
                    <td>{{ log.resource_id }}</td>
                    <td><span :class="['tag', log.operation_result]">{{ log.operation_result }}</span></td>
                    <td>{{ log.created_at }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        </a-tab-pane>
      </a-tabs>
    </div>

    <a-modal v-model:visible="jsonModalOpen" title="JSON 详情" width="760px" :footer="false">
      <pre class="json-pre">{{ jsonPreview }}</pre>
    </a-modal>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { Message } from '@arco-design/web-vue'
import {
  executeAdminJob,
  fetchAdminEvents,
  fetchAdminJobLogs,
  fetchAdminJobRuns,
  fetchAdminJobs,
  fetchAdminOverview,
  fetchAuditLogs,
  fetchDataLineage,
  fetchDataVolumeTrend,
  fetchDatasets,
  fetchPipelineStatus,
  fetchQualityIssues,
  fetchQualityOverview,
  retryAdminJobRun
} from '../api/admin'
import { lineOption } from '../charts/options'

const activeTab = ref('overview')
const bizDate = ref(todayString())
const overview = ref({})
const trend = ref([])
const pipeline = ref({})
const datasets = ref([])
const lineage = ref({})
const events = ref([])
const jobs = ref([])
const jobRuns = ref([])
const qualityOverview = ref({})
const qualityIssues = ref([])
const auditLogs = ref([])
const eventFilters = ref({ trace_id: '', run_id: '', agent_id: '', event_type: '', status: '' })

// Pipeline running states
const runningJobs = ref({})
const pipelineRunning = ref(false)
const anyJobRunning = computed(() => {
  return Object.values(runningJobs.value).some(Boolean) || pipelineRunning.value
})

function getJobsByStage(stage) {
  if (stage === 1) return jobs.value.filter(j => j.job_code === 'datax_import')
  if (stage === 2) return jobs.value.filter(j => j.job_code === 'spark_clean')
  if (stage === 3) return jobs.value.filter(j => ['daily_metric', 'agent_ranking', 'error_analysis', 'relation_analysis', 'historical_alert'].includes(j.job_code))
  if (stage === 4) return jobs.value.filter(j => j.job_code === 'report_generate')
  return []
}
const jsonModalOpen = ref(false)
const jsonPreview = ref('')
const trendChartRef = ref(null)
const funnelChartRef = ref(null)
const lineageChartRef = ref(null)
let trendChart
let funnelChart
let lineageChart

const overviewMetrics = computed(() => [
  { label: 'MySQL Source 总量', value: formatNumber(overview.value.source_total_count), hint: `今日新增 ${formatNumber(overview.value.today_new_count)}` },
  { label: 'HDFS Raw 分区', value: overview.value.raw_partition_count ?? '-', hint: latestHint(overview.value.raw_latest_biz_date) },
  { label: 'HDFS Clean 分区', value: overview.value.clean_partition_count ?? '-', hint: latestHint(overview.value.clean_latest_biz_date) },
  { label: 'HDFS Metric 分区', value: overview.value.metric_partition_count ?? '-', hint: latestHint(overview.value.metric_latest_biz_date) },
  { label: 'Raw 到 Clean 有效率', value: percent(overview.value.raw_to_clean_valid_rate), hint: 'clean / raw' },
  { label: '今日任务成功率', value: percent(overview.value.today_task_success_rate), hint: 'offline jobs' },
  { label: '最近失败任务', value: overview.value.recent_failed_task || '-', hint: 'failed job' },
  { label: '待处理质量问题', value: overview.value.quality_issue_pending_count ?? 0, hint: 'quality backlog' }
])

function todayString() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function latestHint(value) {
  return value ? `最新业务日期 ${value}` : '暂无分区'
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString()
}

function percent(value) {
  return `${(Number(value || 0) * 100).toFixed(1)}%`
}

function nodeName(id) {
  return lineage.value.nodes?.find((node) => node.id === id)?.name || id
}

function showJson(value) {
  jsonPreview.value = JSON.stringify(value, null, 2)
  jsonModalOpen.value = true
}

async function showLogs(runId) {
  const data = await fetchAdminJobLogs(runId)
  showJson(data)
}

function compactParams(params) {
  return Object.fromEntries(Object.entries(params).filter(([, value]) => value !== ''))
}

async function loadEvents() {
  events.value = await fetchAdminEvents(compactParams(eventFilters.value))
}

async function loadJobs() {
  const [jobData, runData] = await Promise.all([fetchAdminJobs(), fetchAdminJobRuns()])
  jobs.value = jobData
  jobRuns.value = runData
}

async function runJob(jobCode) {
  runningJobs.value[jobCode] = true
  Message.info({ content: `正在调度执行作业: ${jobCode}...`, duration: 3000 })
  try {
    const res = await executeAdminJob(jobCode, bizDate.value)
    if (res.status === 'failed') {
      Message.error({ content: `作业 ${jobCode} 运行失败，请在下方列表查看详细日志！`, duration: 6000 })
    } else {
      Message.success({ content: `作业 ${jobCode} 执行成功！`, duration: 4000 })
    }
  } catch (err) {
    Message.error({ content: `作业调度系统异常: ${err.message || err}`, duration: 5000 })
  } finally {
    runningJobs.value[jobCode] = false
    await loadJobs()
    auditLogs.value = await fetchAuditLogs()
  }
}

async function runFullPipeline() {
  pipelineRunning.value = true
  Message.info({ content: '离线流水线已启动，各阶段任务正按顺序流式调度...', duration: 4000 })
  try {
    let failed = false
    for (const job of jobs.value) {
      runningJobs.value[job.job_code] = true
      Message.info({ content: `正在执行：${job.job_name}...`, duration: 2500 })
      try {
        const res = await executeAdminJob(job.job_code, bizDate.value)
        if (res.status === 'failed') {
          failed = true
          Message.error({ content: `流水线在 [${job.job_name}] 阶段运行失败，已中止后续任务！`, duration: 6000 })
          break
        }
      } catch (e) {
        failed = true
        Message.error({ content: `流水线在 [${job.job_name}] 运行异常，已强制中止！`, duration: 6000 })
        break
      } finally {
        runningJobs.value[job.job_code] = false
        await loadJobs()
      }
    }
    if (!failed) {
      Message.success({ content: '一键离线计算流水线全段运行成功！', duration: 5000 })
    }
  } catch (err) {
    Message.error({ content: `流水线运行系统异常: ${err.message || err}` })
  } finally {
    pipelineRunning.value = false
    auditLogs.value = await fetchAuditLogs()
  }
}

async function retryRun(runId) {
  Message.info({ content: `正在重新提交运行记录 ${runId}...`, duration: 3000 })
  try {
    const res = await retryAdminJobRun(runId)
    if (res.status === 'failed') {
      Message.error({ content: `运行重试失败，请点查看日志分析！`, duration: 5000 })
    } else {
      Message.success({ content: `重试作业提交并运行成功！`, duration: 4000 })
    }
  } catch (err) {
    Message.error({ content: `重试失败: ${err.message || err}` })
  } finally {
    await loadJobs()
    auditLogs.value = await fetchAuditLogs()
  }
}

function renderFunnel() {
  if (!funnelChartRef.value) return
  funnelChart ||= echarts.init(funnelChartRef.value)
  
  const rawFunnel = overview.value.funnel || []
  // Use a beautifully-proportioned visual scale to prevent the 120 count from collapsing the funnel shape
  const visualScales = [100, 80, 60, 40]
  const funnelData = rawFunnel.map((item, idx) => ({
    name: item.name,
    value: visualScales[idx] || 30,
    realValue: item.count
  }))
  
  funnelChart.setOption({
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      formatter: (params) => {
        const valStr = Number(params.data.realValue || 0).toLocaleString()
        return `${params.marker}${params.name} : <b>${valStr}</b> 条`
      }
    },
    grid: { top: 10, bottom: 10 },
    series: [
      {
        name: '数据生命周期漏斗',
        type: 'funnel',
        left: '20%',
        width: '60%',
        top: 20,
        bottom: 10,
        min: 0,
        max: 100,
        minSize: '30%',
        maxSize: '100%',
        sort: 'descending',
        gap: 6,
        label: {
          show: true,
          position: 'inside',
          formatter: (params) => {
            const valStr = Number(params.data.realValue || 0).toLocaleString()
            return `${params.name}: ${valStr} 条`
          },
          color: '#ffffff',
          fontWeight: 'bold',
          fontSize: 12
        },
        labelLine: {
          show: false
        },
        itemStyle: {
          borderColor: 'rgba(103, 232, 249, 0.3)',
          borderWidth: 1.5,
          shadowBlur: 12,
          shadowColor: 'rgba(34, 211, 238, 0.25)',
          borderRadius: 4
        },
        color: ['#0891b2', '#06b6d4', '#22d3ee', '#67e8f9'],
        data: funnelData
      }
    ]
  }, true)
}

function renderLineage() {
  if (!lineageChartRef.value) return
  lineageChart ||= echarts.init(lineageChartRef.value)
  
  const nodes = (lineage.value.nodes || []).map(n => ({
    id: n.id,
    name: n.name,
    value: n.name,
    symbolSize: 22,
    itemStyle: { 
      color: n.id.includes('mysql') ? '#3b82f6' : '#22d3ee',
      shadowBlur: 10,
      shadowColor: 'rgba(34, 211, 238, 0.4)'
    }
  }))
  
  const links = (lineage.value.edges || []).map(e => ({
    source: e.from,
    target: e.to,
    label: { 
      show: true, 
      formatter: e.label, 
      fontSize: 10, 
      color: '#9bc7d9',
      backgroundColor: 'rgba(8, 22, 34, 0.75)',
      padding: [2, 4],
      borderRadius: 2
    },
    lineStyle: { 
      color: 'rgba(103, 232, 249, 0.35)', 
      curveness: 0.15,
      width: 1.5
    }
  }))
  
  lineageChart.setOption({
    backgroundColor: 'transparent',
    tooltip: { 
      trigger: 'item',
      formatter: (params) => {
        if (params.dataType === 'node') {
          return `数据层: <b>${params.name}</b>`
        } else {
          return `血缘流动: <b>${params.data.source} ➔ ${params.data.target}</b> (${params.data.label.formatter})`
        }
      }
    },
    series: [
      {
        type: 'graph',
        layout: 'force',
        force: {
          repulsion: 150,
          edgeLength: 110,
          gravity: 0.08
        },
        roam: true,
        draggable: true,
        symbol: 'circle',
        edgeSymbol: ['none', 'arrow'],
        edgeSymbolSize: [4, 8],
        label: {
          show: true,
          position: 'bottom',
          color: '#bdefff',
          fontSize: 10,
          fontWeight: 'bold'
        },
        data: nodes,
        links: links
      }
    ]
  }, true)
}

function renderTrend() {
  if (!trendChartRef.value) return
  trendChart ||= echarts.init(trendChartRef.value)
  trendChart.setOption(lineOption('Raw / Clean 数据量趋势', trend.value.map((item) => item.biz_date), [
    { name: 'Raw', type: 'line', smooth: true, data: trend.value.map((item) => item.raw_count), itemStyle: { color: '#22d3ee' }, areaStyle: { color: 'rgba(34, 211, 238, 0.1)' } },
    { name: 'Clean', type: 'line', smooth: true, data: trend.value.map((item) => item.clean_count), itemStyle: { color: '#4ade80' }, areaStyle: { color: 'rgba(74, 222, 128, 0.08)' } }
  ]), true)
}

function resizeCharts() {
  trendChart?.resize()
  funnelChart?.resize()
  lineageChart?.resize()
}

async function loadAll() {
  const [overviewData, trendData, pipelineData, datasetData, lineageData, qualityOverviewData, qualityIssueData, auditData] = await Promise.all([
    fetchAdminOverview(),
    fetchDataVolumeTrend(),
    fetchPipelineStatus(),
    fetchDatasets(),
    fetchDataLineage(),
    fetchQualityOverview(),
    fetchQualityIssues(),
    fetchAuditLogs()
  ])
  overview.value = overviewData
  trend.value = trendData
  pipeline.value = pipelineData
  datasets.value = datasetData
  lineage.value = lineageData
  qualityOverview.value = qualityOverviewData
  qualityIssues.value = qualityIssueData
  auditLogs.value = auditData
  await Promise.all([loadEvents(), loadJobs()])
  await nextTick()
  renderTrend()
  renderFunnel()
  renderLineage()
}

onMounted(async () => {
  await loadAll()
  window.addEventListener('resize', resizeCharts)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCharts)
  trendChart?.dispose()
  funnelChart?.dispose()
  lineageChart?.dispose()
})
</script>
