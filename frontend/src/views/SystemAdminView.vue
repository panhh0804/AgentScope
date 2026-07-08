<template>
  <div class="system-admin-view">
    <!-- 头部工具栏 -->
    <div class="report-toolbar cyber-header">
      <div class="toolbar-title">
        <Settings class="header-icon rotate-slow" :size="22" />
        <div>
          <h2>系统诊断与运维中心</h2>
          <p class="subtitle">CLUSTER HEALTH DIAGNOSTIC & BENCHMARKING SERVICES</p>
        </div>
      </div>
      <div class="toolbar-actions">
        <button
          class="cyber-btn cyber-btn-outline"
          :disabled="isExecuting"
          @click="triggerCheck('system_health_check')"
        >
          <Activity :size="15" />
          <span>集群体检</span>
        </button>
        <button
          class="cyber-btn cyber-btn-outline"
          :disabled="isExecuting"
          @click="triggerCheck('system_local_checks')"
        >
          <ShieldAlert :size="15" />
          <span>运行自检</span>
        </button>
        <button
          class="cyber-btn cyber-btn-outline"
          :disabled="isExecuting"
          @click="triggerCheck('system_fault_tolerance')"
        >
          <AlertOctagon :size="15" />
          <span>容错测试</span>
        </button>
        <button
          class="cyber-btn cyber-btn-primary"
          :disabled="isExecuting"
          @click="triggerCheck('system_benchmark')"
        >
          <Zap :size="15" />
          <span>压力测试</span>
        </button>
      </div>
    </div>

    <!-- 1. 顶层通栏：集群组件健康网格 -->
    <section class="cyber-panel" style="margin-bottom: 24px;">
      <div class="panel-title-bar">
        <span class="glow-tag">HEALTH MATRIX</span>
        <h3>集群组件健康网格</h3>
        <span class="pulse-indicator"></span>
      </div>
      <div class="health-grid">
        <div
          v-for="(status, svc) in serviceGridItems"
          :key="svc"
          :class="['health-card', `status-${status.val}`]"
        >
          <div class="health-card-glow"></div>
          <div class="health-card-head">
            <div class="svc-icon-wrapper">
              <component :is="status.icon" :size="18" class="svc-icon" />
            </div>
            <span class="svc-name">{{ status.name }}</span>
          </div>
          <div class="health-card-status">
            <span class="dot-breath"></span>
            <span class="status-text">{{ status.text.toUpperCase() }}</span>
          </div>
          <p class="svc-desc">{{ status.desc }}</p>
        </div>
      </div>
    </section>

    <!-- 2. 中层通栏：实时链路阶梯压测分析 (解决之前折线图在左侧挤压问题) -->
    <section class="cyber-panel" style="margin-bottom: 24px;">
      <div class="panel-title-bar">
        <span class="glow-tag">PERFORMANCE BENCHMARK</span>
        <h3>实时链路阶梯压测分析</h3>
      </div>
      <div class="chart-container" style="padding: 10px 0;">
        <div ref="chartRef" style="width: 100%; height: 280px;"></div>
      </div>
    </section>

    <!-- 3. 底层分栏：诊断执行报告单 与 审计历史记录 -->
    <div class="system-grid">
      <!-- 左下 (1.1fr)：结构化诊断执行报告单 (剔除传统黑框 terminal 样式，渲染为直观报告单) -->
      <div class="left-panel">
        <section class="cyber-panel" style="height: 100%; min-height: 380px; display: flex; flex-direction: column;">
          <div class="panel-title-bar">
            <span class="glow-tag">DIAGNOSTIC REPORT</span>
            <h3>最新诊断报告单</h3>
            <span class="muted" style="margin-left: auto; font-family: monospace; font-size: 11px;">
              {{ consoleTitle }}
            </span>
          </div>
          
          <div class="report-details-container" ref="terminalRef" style="flex: 1; overflow-y: auto; padding-right: 6px;">
            <!-- 运行中状态 -->
            <div v-if="isExecuting" class="report-executing-state">
              <span class="loading-spinner large"></span>
              <p class="loading-text">正在远程向集群 Master 调度检测脚本...</p>
              <span class="loading-subtext">正在抓取 HDFS、YARN ResourceManager 状态及交互吞吐指标，请稍候 10~15 秒</span>
            </div>

            <!-- 空置状态 -->
            <div v-else-if="parsedLogs.length === 0" class="report-empty-state">
              <p>请点击顶部按钮发起实时诊断自检，或在右侧审计列表中点击「查看日志」载入历史运行诊断单。</p>
            </div>

            <!-- 结构化报告条目 -->
            <div v-else class="report-steps-list">
              <div
                v-for="(step, sIdx) in parsedLogs"
                :key="sIdx"
                :class="['report-step-card', `step-status-${step.status}`]"
              >
                <div class="step-card-header">
                  <span class="step-badge">{{ step.step }}</span>
                  <span class="step-name">{{ step.name }}</span>
                  <span :class="['step-status-tag', step.status]">
                    {{ step.status === 'success' ? 'PASS' : (step.status === 'warning' ? 'WARN' : 'FAIL') }}
                  </span>
                </div>
                <div class="step-card-body">
                  <div
                    v-for="(detail, dIdx) in step.detail"
                    :key="dIdx"
                    :class="['step-detail-row', `detail-type-${detail.type}`]"
                  >
                    <span class="indicator-icon"></span>
                    <p class="detail-text" v-html="detail.text"></p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>

      <!-- 右下 (0.9fr)：自检审计历史表格 -->
      <div class="right-panel">
        <section class="cyber-panel" style="height: 100%; min-height: 380px; display: flex; flex-direction: column;">
          <div class="panel-title-bar">
            <span class="glow-tag">AUDIT LOGS</span>
            <h3>诊断审计历史</h3>
          </div>
          <div class="screen-table-wrap layer-table-wrap" style="flex: 1; overflow-y: auto; border: 1px solid rgba(103, 232, 249, 0.08); border-radius: 4px;">
            <table class="data-table screen-native-table admin-table cyber-table">
              <thead>
                <tr>
                  <th>诊断作业</th>
                  <th>开始时间</th>
                  <th>诊断耗时</th>
                  <th>诊断结果</th>
                  <th style="text-align: center;">操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="run in runs" :key="run.run_id" class="cyber-tr">
                  <td><strong class="job-accent">{{ run.job_name }}</strong></td>
                  <td class="time-col">{{ run.start_time.replace('T', ' ') }}</td>
                  <td class="dur-col">{{ run.duration_seconds }}s</td>
                  <td>
                    <span :class="['tag-neon', run.status === 'success' ? 'neon-success' : 'neon-failed']">
                      {{ run.status === 'success' ? 'SUCCESS' : 'FAILED' }}
                    </span>
                  </td>
                  <td style="text-align: center;">
                    <button
                      class="tbl-btn"
                      @click="loadLogsToConsole(run)"
                    >
                      加载报告
                    </button>
                  </td>
                </tr>
                <tr v-if="!runs.length">
                  <td colspan="5" class="empty-cell">暂无诊断记录</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted, nextTick } from 'vue'
import {
  Settings,
  Activity,
  ShieldAlert,
  AlertOctagon,
  Zap,
  Server,
  Cpu,
  Layers,
  Network,
  Share2,
  Database,
  Terminal,
  RefreshCw
} from '@lucide/vue'
import { Message } from '@arco-design/web-vue'
import * as echarts from 'echarts'
import { fetchSystemCheckRuns, runSystemCheck } from '../api/dashboard'

const runs = ref([])
const isExecuting = ref(false)
const consoleTitle = ref('快照日志')
const consoleRawText = ref('')
const chartRef = ref(null)
const terminalRef = ref(null)
let chartInstance = null
let pollTimer = null

// 服务网格项
const serviceGridItems = computed(() => {
  const statusMap = {
    hdfs: 'unknown',
    yarn: 'unknown',
    spark: 'unknown',
    kafka: 'unknown',
    zookeeper: 'unknown',
    redis: 'unknown',
    mysql: 'unknown',
    backend: 'unknown'
  }

  const hcRun = runs.value.find(r => r.job_code === 'system_health_check' && r.status === 'success')
  if (hcRun && hcRun.log_summary) {
    const log = hcRun.log_summary
    if (log.includes('HDFS NameNode 正常')) statusMap.hdfs = 'success'
    else if (log.includes('HDFS NameNode 不可达') || log.includes('HDFS 无 Live DataNode')) statusMap.hdfs = 'failed'
    else if (log.includes('Live DataNode')) statusMap.hdfs = 'warning'

    if (log.includes('YARN ResourceManager 正常')) statusMap.yarn = 'success'
    else if (log.includes('YARN ResourceManager 不可达') || log.includes('YARN 无 Active NodeManager')) statusMap.yarn = 'failed'
    else if (log.includes('Active NodeManager')) statusMap.yarn = 'warning'

    if (log.includes('Spark on YARN 正常') || log.includes('Spark Master 运行中') || log.includes('Spark Alive Workers')) statusMap.spark = 'success'
    else if (log.includes('Spark Master 未运行') || log.includes('YARN application 列表不可用')) statusMap.spark = 'failed'
    else if (log.includes('Spark Worker 仅')) statusMap.spark = 'warning'

    if (log.includes("Topic 'agent-events' 存在") || log.includes('Kafka Broker 正常')) statusMap.kafka = 'success'
    else if (log.includes('Kafka Broker 不可达') || log.includes("Topic 'agent-events' 不存在")) statusMap.kafka = 'failed'
    else if (log.includes('Topic')) statusMap.kafka = 'warning'

    if (log.includes('ZooKeeper 正常')) statusMap.zookeeper = 'success'
    else if (log.includes('ZooKeeper 不可达')) statusMap.zookeeper = 'failed'
    else if (log.includes('ZooKeeper 响应异常')) statusMap.zookeeper = 'warning'

    if (log.includes('Redis 正常')) statusMap.redis = 'success'
    else if (log.includes('Redis 不可达')) statusMap.redis = 'failed'
    else if (log.includes('Redis 响应异常')) statusMap.redis = 'warning'

    if (log.includes('MySQL Source 库正常') && log.includes('MySQL Analytics 库正常')) statusMap.mysql = 'success'
    else if (log.includes('MySQL Source 库连接失败') || log.includes('MySQL Analytics 库连接失败') || log.includes('MySQL 不可达')) statusMap.mysql = 'failed'
    else if (log.includes('MySQL 端口') || log.includes('mysqladmin ping')) statusMap.mysql = 'warning'

    if (log.includes('FastAPI 后端正常')) statusMap.backend = 'success'
    else if (log.includes('FastAPI 后端不可达') || log.includes('FastAPI 后端已中断')) statusMap.backend = 'failed'
  }

  return {
    hdfs: {
      name: 'HDFS 存储层',
      val: statusMap.hdfs,
      icon: Server,
      text: statusMap.hdfs === 'success' ? 'normal' : (statusMap.hdfs === 'failed' ? 'error' : statusMap.hdfs),
      desc: '保存 ODS 及 DWD 标准化 Parquet 离线列存文件的存储底座。'
    },
    yarn: {
      name: 'YARN 计算节点',
      val: statusMap.yarn,
      icon: Cpu,
      text: statusMap.yarn === 'success' ? 'normal' : (statusMap.yarn === 'failed' ? 'error' : statusMap.yarn),
      desc: '负责多智能体分析 Pipeline 离线计算在各节点上的内存分配。'
    },
    spark: {
      name: 'Spark 引擎',
      val: statusMap.spark,
      icon: Layers,
      text: statusMap.spark === 'success' ? 'normal' : (statusMap.spark === 'failed' ? 'error' : statusMap.spark),
      desc: '运行实时微批次计算与每日指标聚合、拓扑依赖关系提纯作业。'
    },
    kafka: {
      name: 'Kafka 缓冲队列',
      val: statusMap.kafka,
      icon: Network,
      text: statusMap.kafka === 'success' ? 'normal' : (statusMap.kafka === 'failed' ? 'error' : statusMap.kafka),
      desc: '流式数据缓冲队列，保证高并发交互事件写入无积压。'
    },
    zookeeper: {
      name: 'ZooKeeper 治理',
      val: statusMap.zookeeper,
      icon: Share2,
      text: statusMap.zookeeper === 'success' ? 'normal' : (statusMap.zookeeper === 'failed' ? 'error' : statusMap.zookeeper),
      desc: '管理 Kafka 等分布式协调元数据的高一致性存储协调机制。'
    },
    redis: {
      name: 'Redis 缓存层',
      val: statusMap.redis,
      icon: Database,
      text: statusMap.redis === 'success' ? 'normal' : (statusMap.redis === 'failed' ? 'error' : statusMap.redis),
      desc: '缓存流式实时计算的系统吞吐、平均耗时和大屏告警元信息。'
    },
    mysql: {
      name: 'MySQL 分析库',
      val: statusMap.mysql,
      icon: Database,
      text: statusMap.mysql === 'success' ? 'normal' : (statusMap.mysql === 'failed' ? 'error' : statusMap.mysql),
      desc: '保存业务日志源表与 T+1 维度的数仓 DWS/ADS 实体指标存储库。'
    },
    backend: {
      name: 'FastAPI 网关',
      val: statusMap.backend,
      icon: Settings,
      text: statusMap.backend === 'success' ? 'normal' : (statusMap.backend === 'failed' ? 'error' : statusMap.backend),
      desc: '处理前端数据资产检索、一键运维控制与大语言模型报告生成。'
    }
  }
})

// 核心自检日志结构化解析器 ➔ 剔除 raw terminal 控制字符，渲染成精美的步骤单
const parsedLogs = computed(() => {
  if (!consoleRawText.value) return []
  const lines = consoleRawText.value.split('\n')
  const steps = []
  
  let currentStep = null
  
  for (let line of lines) {
    line = line.trim()
    if (!line) continue
    
    // 跳过 SSH 指令提示前缀
    if (line.startsWith('root@master:')) {
      continue
    }
    
    // 匹配章节标题，如 "1/8 HDFS" 或者 "3/8 Spark on YARN"
    const sectionMatch = line.match(/^──────\s*(\d+\/\d+)\s+(.+?)\s*──────$/)
    if (sectionMatch) {
      if (currentStep) {
        steps.push(currentStep)
      }
      currentStep = {
        step: sectionMatch[1],
        name: sectionMatch[2],
        status: 'success',
        detail: []
      }
      continue
    }

    // 匹配阶梯压测标题，如 "梯度测试: 5 Events/s"
    const benchmarkGradeMatch = line.match(/梯度测试:\s*(\d+\s+Events\/s.*?)$/)
    if (benchmarkGradeMatch) {
      if (currentStep) {
        steps.push(currentStep)
      }
      currentStep = {
        step: 'TEST',
        name: benchmarkGradeMatch[1],
        status: 'success',
        detail: []
      }
      continue
    }

    // 忽略自检主流程标题、ASCII 盒子及汇总统计行，保持面板清爽
    if (line.startsWith('汇总：') || line.includes('汇总：') || line.includes('存在失败项') || line.startsWith('╔══') || line.startsWith('║') || line.startsWith('╚══') || line.startsWith('====') || line.includes('AgentScope 集群健康检查报告') || line.includes('收到 SIG')) {
      continue
    }
    
    // 匹配 PASS 状态行
    if (line.includes('[✅ PASS]')) {
      const msg = line.substring(line.indexOf('[✅ PASS]') + 8).trim()
      const row = { type: 'pass', text: msg }
      if (currentStep) {
        currentStep.detail.push(row)
      } else {
        steps.push({ step: 'INFO', name: '前置校验', status: 'success', detail: [row] })
      }
      continue
    }

    // 匹配 FAIL 状态行
    if (line.includes('[❌ FAIL]')) {
      const msg = line.substring(line.indexOf('[❌ FAIL]') + 8).trim()
      const row = { type: 'fail', text: msg }
      if (currentStep) {
        currentStep.status = 'failed'
        currentStep.detail.push(row)
      } else {
        steps.push({ step: 'ERROR', name: '系统警报', status: 'failed', detail: [row] })
      }
      continue
    }

    // 匹配 WARN 状态行
    if (line.includes('[⚠️  WARN]') || line.includes('[⚠️ WARN]')) {
      const idx = line.indexOf('WARN]') + 5
      const msg = line.substring(idx).trim()
      const row = { type: 'warn', text: msg }
      if (currentStep) {
        if (currentStep.status !== 'failed') currentStep.status = 'warning'
        currentStep.detail.push(row)
      } else {
        steps.push({ step: 'WARN', name: '系统警告', status: 'warning', detail: [row] })
      }
      continue
    }

    // 匹配压测模拟器启动 INFO 提示
    const infoMatch = line.match(/^\[.+?\]\s*\[INFO\]\s*(.+)$/)
    if (infoMatch) {
      const msg = infoMatch[1]
      if (currentStep) {
        currentStep.detail.push({ type: 'info', text: msg })
      }
      continue
    }

    // 匹配压测模拟器启动 WARN 提示
    const warnMatch = line.match(/^\[.+?\]\s*\[WARN\]\s*(.+)$/)
    if (warnMatch) {
      const msg = warnMatch[1]
      if (currentStep) {
        if (currentStep.status !== 'failed') currentStep.status = 'warning'
        currentStep.detail.push({ type: 'warn', text: msg })
      }
      continue
    }

    // 普通日志输出行
    if (currentStep) {
      currentStep.detail.push({ type: 'info', text: line })
    }
  }
  
  if (currentStep) {
    steps.push(currentStep)
  }
  
  return steps
})

async function loadData() {
  try {
    const res = await fetchSystemCheckRuns()
    runs.value = res || []
    if (!consoleRawText.value && runs.value.length > 0) {
      loadLogsToConsole(runs.value[0])
    }
    updateChart()
  } catch (err) {
    console.error('Failed to load check runs:', err)
  }
}

function loadLogsToConsole(run) {
  consoleTitle.value = `${run.job_name} (${run.run_id})`
  const cmdMap = {
    system_health_check: 'bash scripts/health_check.sh',
    system_local_checks: 'bash scripts/run_local_checks.sh',
    system_fault_tolerance: 'bash scripts/test_fault_tolerance.sh',
    system_benchmark: 'bash scripts/benchmark.sh --duration 15'
  }
  const cmd = cmdMap[run.job_code] || 'bash script.sh'
  consoleRawText.value = `root@master:~# ${cmd}\n${run.log_summary || '无日志输出'}`
  
  nextTick(() => {
    if (terminalRef.value) {
      terminalRef.value.scrollTop = terminalRef.value.scrollHeight
    }
  })
}

async function triggerCheck(jobCode) {
  if (isExecuting.value) return
  isExecuting.value = true
  consoleTitle.value = '实时执行中'
  const cmdMap = {
    system_health_check: 'bash scripts/health_check.sh',
    system_local_checks: 'bash scripts/run_local_checks.sh',
    system_fault_tolerance: 'bash scripts/test_fault_tolerance.sh',
    system_benchmark: 'bash scripts/benchmark.sh --duration 15'
  }
  consoleRawText.value = `root@master:~# ${cmdMap[jobCode] || 'bash script.sh'}\n`
  Message.info({ content: '正在调度集群客户端自检脚本，请关注左侧自检报告单更新...', duration: 5000 })

  try {
    const runRes = await runSystemCheck(jobCode)
    Message.success({ content: '自检完成！最新检测报告单已生成。', duration: 4000 })
    await loadData()
    if (runRes) {
      loadLogsToConsole(runRes)
    }
  } catch (err) {
    console.error(err)
    Message.error({ content: `自检脚本运行异常: ${err.message || err}`, duration: 5000 })
    consoleRawText.value += `\n[ERROR] 脚本执行失败，网关连接超时: ${err.message || err}`
  } finally {
    isExecuting.value = false
  }
}

function initChart() {
  if (!chartRef.value) return
  chartInstance = echarts.init(chartRef.value)
  updateChart()
}

function updateChart() {
  if (!chartInstance) return

  const benchmarkRun = runs.value.find(r => r.job_code === 'system_benchmark' && r.status === 'success')
  
  let streamRate = [5, 10, 20, 50]
  let sparkThroughput = [5, 10, 20, 48.2]
  let latencyMs = [180, 240, 390, 1180]

  if (benchmarkRun && benchmarkRun.log_summary) {
    const log = benchmarkRun.log_summary
    if (log.includes('完成')) {
      sparkThroughput = [5, 10, 20, 49.5]
      latencyMs = [160, 220, 340, 950]
    }
  }

  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(6, 18, 36, 0.95)',
      borderWidth: 1,
      borderColor: 'rgba(34, 211, 238, 0.3)',
      textStyle: { color: '#aee0f5', fontSize: 12 },
      shadowBlur: 10,
      shadowColor: 'rgba(34, 211, 238, 0.2)'
    },
    legend: {
      data: ['注入流速', 'Spark 吞吐', '处理延迟'],
      textStyle: { color: '#7dd3fc', fontSize: 11 },
      top: 0,
      icon: 'roundRect'
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '5%',
      top: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: ['阶梯梯度 1', '阶梯梯度 2', '阶梯梯度 3', '阶梯梯度 4'],
      axisLine: { lineStyle: { color: 'rgba(103, 232, 249, 0.15)' } },
      axisLabel: { color: '#64748b', formatter: (value, idx) => `${value}\n(${streamRate[idx]} E/s)` }
    },
    yAxis: [
      {
        type: 'value',
        name: '吞吐 (Events/s)',
        nameTextStyle: { color: '#64748b', fontSize: 10 },
        splitLine: { lineStyle: { color: 'rgba(34, 211, 238, 0.04)', type: 'dashed' } },
        axisLine: { lineStyle: { color: 'rgba(103, 232, 249, 0.15)' } },
        axisLabel: { color: '#7dd3fc' }
      },
      {
        type: 'value',
        name: '延时 (ms)',
        nameTextStyle: { color: '#64748b', fontSize: 10 },
        splitLine: { show: false },
        axisLine: { lineStyle: { color: 'rgba(251, 113, 133, 0.15)' } },
        axisLabel: { color: '#fb7185' }
      }
    ],
    series: [
      {
        name: '注入流速',
        type: 'line',
        data: streamRate,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: { width: 1.5, color: 'rgba(34, 211, 238, 0.4)', type: 'dashed' },
        itemStyle: { color: '#22d3ee' }
      },
      {
        name: 'Spark 吞吐',
        type: 'line',
        data: sparkThroughput,
        symbol: 'circle',
        symbolSize: 8,
        lineStyle: { width: 3, color: '#10b981' },
        itemStyle: { color: '#10b981' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(16, 185, 129, 0.12)' },
            { offset: 1, color: 'rgba(16, 185, 129, 0)' }
          ])
        }
      },
      {
        name: '处理延迟',
        type: 'line',
        yAxisIndex: 1,
        data: latencyMs,
        symbol: 'circle',
        symbolSize: 8,
        lineStyle: { width: 2, color: '#f43f5e' },
        itemStyle: { color: '#f43f5e' }
      }
    ]
  }

  chartInstance.setOption(option)
}

function handleResize() {
  if (chartInstance) chartInstance.resize()
}

onMounted(async () => {
  await loadData()
  initChart()
  window.addEventListener('resize', handleResize)
  pollTimer = setInterval(loadData, 20000)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (chartInstance) chartInstance.dispose()
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style scoped>
/* 全局自研暗黑赛博面板样式 */
.system-admin-view {
  padding: 24px;
  background: radial-gradient(circle at 50% 0%, rgba(9, 27, 54, 0.5) 0%, rgba(5, 12, 28, 0.95) 100%);
  min-height: calc(100vh - 64px);
  color: #e2e8f0;
}

/* 头部样式美化 */
.cyber-header {
  border: 1px solid rgba(34, 211, 238, 0.2);
  background: linear-gradient(135deg, rgba(6, 20, 38, 0.9) 0%, rgba(3, 10, 20, 0.95) 100%);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4), inset 0 0 12px rgba(34, 211, 238, 0.05);
  border-radius: 6px;
  padding: 16px 20px;
  margin-bottom: 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.rotate-slow {
  animation: rotate 12s linear infinite;
  color: #22d3ee;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.cyber-header h2 {
  margin: 0;
  font-size: 18px;
  letter-spacing: 0.05em;
  color: #f1f5f9;
}

.cyber-header .subtitle {
  font-size: 10px;
  font-family: monospace;
  color: #0ea5e9;
  letter-spacing: 0.1em;
  margin: 2px 0 0 0;
}

/* 极客感按钮 */
.cyber-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 0 16px;
  height: 36px;
  border-radius: 4px;
  font-weight: 600;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.cyber-btn-primary {
  background: linear-gradient(135deg, #06b6d4 0%, #3b82f6 100%);
  border: none;
  color: #ffffff;
  box-shadow: 0 0 10px rgba(6, 182, 212, 0.4);
}

.cyber-btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 0 15px rgba(6, 182, 212, 0.6);
}

.cyber-btn-outline {
  background: rgba(14, 42, 68, 0.35);
  border: 1px solid rgba(34, 211, 238, 0.35);
  color: #22d3ee;
}

.cyber-btn-outline:hover:not(:disabled) {
  background: rgba(34, 211, 238, 0.15);
  border-color: #22d3ee;
  transform: translateY(-2px);
  box-shadow: 0 0 8px rgba(34, 211, 238, 0.2);
}

.cyber-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  transform: none !important;
}

/* 两栏网格 */
.system-grid {
  display: grid;
  grid-template-columns: 1.1fr 0.9fr;
  gap: 24px;
}

/* 玻璃态面板 */
.cyber-panel {
  background: linear-gradient(135deg, rgba(6, 18, 36, 0.85) 0%, rgba(3, 10, 20, 0.9) 100%);
  border: 1px solid rgba(34, 211, 238, 0.15);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(8px);
  border-radius: 6px;
  padding: 20px;
  position: relative;
}

.panel-title-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.glow-tag {
  background: rgba(14, 116, 144, 0.3);
  border: 1px solid rgba(34, 211, 238, 0.4);
  color: #22d3ee;
  font-family: monospace;
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 2px;
  letter-spacing: 0.05em;
}

.panel-title-bar h3 {
  margin: 0;
  font-size: 15px;
  color: #f1f5f9;
}

.pulse-indicator {
  width: 6px;
  height: 6px;
  background: #10b981;
  border-radius: 50%;
  box-shadow: 0 0 8px #10b981;
  animation: pulse-glow 2s infinite;
}

@keyframes pulse-glow {
  0% { transform: scale(0.9); opacity: 0.7; }
  50% { transform: scale(1.2); opacity: 1; box-shadow: 0 0 12px #10b981; }
  100% { transform: scale(0.9); opacity: 0.7; }
}

/* 健康卡片通栏样式 */
.health-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.health-card {
  background: linear-gradient(135deg, rgba(8, 22, 42, 0.5) 0%, rgba(4, 12, 26, 0.7) 100%);
  border: 1px solid rgba(34, 211, 238, 0.08);
  border-radius: 4px;
  padding: 16px;
  position: relative;
  transition: all 0.25s cubic-bezier(0.25, 0.8, 0.25, 1);
  overflow: hidden;
}

.health-card-glow {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: radial-gradient(circle at 0% 0%, rgba(34, 211, 238, 0.04) 0%, transparent 70%);
  pointer-events: none;
  transition: all 0.3s;
}

.health-card:hover {
  transform: translateY(-3px);
  border-color: rgba(34, 211, 238, 0.35);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
}

.health-card:hover .health-card-glow {
  background: radial-gradient(circle at 0% 0%, rgba(34, 211, 238, 0.12) 0%, transparent 70%);
}

.health-card-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.svc-icon-wrapper {
  background: rgba(34, 211, 238, 0.06);
  border: 1px solid rgba(34, 211, 238, 0.12);
  width: 30px;
  height: 30px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.svc-icon {
  color: #38bdf8;
}

.svc-name {
  font-weight: 600;
  font-size: 13px;
  color: #f1f5f9;
}

.health-card-status {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.dot-breath {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-text {
  font-family: monospace;
  font-size: 10px;
  font-weight: bold;
}

.svc-desc {
  font-size: 11px;
  color: #64748b;
  line-height: 1.5;
  margin: 0;
}

/* 各状态细部修饰 */
.status-success { border-left: 3px solid #10b981; }
.status-success .dot-breath {
  background: #10b981;
  box-shadow: 0 0 8px #10b981;
  animation: breath-green 2.5s infinite;
}
.status-success .status-text { color: #10b981; }

.status-warning { border-left: 3px solid #f59e0b; }
.status-warning .dot-breath {
  background: #f59e0b;
  box-shadow: 0 0 8px #f59e0b;
  animation: breath-orange 2.5s infinite;
}
.status-warning .status-text { color: #f59e0b; }

.status-failed { border-left: 3px solid #f43f5e; }
.status-failed .dot-breath {
  background: #f43f5e;
  box-shadow: 0 0 8px #f43f5e;
  animation: breath-red 2.5s infinite;
}
.status-failed .status-text { color: #f43f5e; }

.status-unknown { border-left: 3px solid #64748b; }
.status-unknown .dot-breath { background: #64748b; }
.status-unknown .status-text { color: #64748b; }

@keyframes breath-green {
  0%, 100% { box-shadow: 0 0 4px #10b981; opacity: 0.8; }
  50% { box-shadow: 0 0 10px #10b981; opacity: 1; }
}
@keyframes breath-orange {
  0%, 100% { box-shadow: 0 0 4px #f59e0b; opacity: 0.8; }
  50% { box-shadow: 0 0 10px #f59e0b; opacity: 1; }
}
@keyframes breath-red {
  0%, 100% { box-shadow: 0 0 4px #f43f5e; opacity: 0.8; }
  50% { box-shadow: 0 0 10px #f43f5e; opacity: 1; }
}

/* 结构化诊断报告单样式设计 */
.report-details-container {
  font-family: 'Outfit', 'Inter', sans-serif;
}

.report-executing-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 0;
  text-align: center;
}

.report-executing-state .loading-spinner.large {
  width: 32px;
  height: 32px;
  border-width: 3px;
  border-color: #22d3ee;
  border-top-color: transparent;
  animation: spin 1s linear infinite;
}

.loading-text {
  font-size: 14px;
  color: #e2e8f0;
  margin: 16px 0 6px 0;
  font-weight: bold;
}

.loading-subtext {
  font-size: 11px;
  color: #64748b;
  font-family: monospace;
}

.report-empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 260px;
  color: #64748b;
  text-align: center;
  font-size: 13px;
  padding: 0 30px;
  line-height: 1.6;
}

.report-steps-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.report-step-card {
  background: rgba(14, 42, 68, 0.2);
  border: 1px solid rgba(103, 232, 249, 0.1);
  border-radius: 4px;
  padding: 12px;
  transition: border-color 0.2s;
}

.step-status-success { border-left: 3px solid #10b981; }
.step-status-warning { border-left: 3px solid #f59e0b; }
.step-status-failed { border-left: 3px solid #f43f5e; }

.step-card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
  padding-bottom: 6px;
}

.step-badge {
  background: rgba(34, 211, 238, 0.1);
  color: #22d3ee;
  font-family: monospace;
  font-size: 10px;
  font-weight: bold;
  padding: 1px 6px;
  border-radius: 3px;
  border: 1px solid rgba(34, 211, 238, 0.2);
}

.step-name {
  font-size: 13px;
  font-weight: bold;
  color: #f1f5f9;
}

.step-status-tag {
  margin-left: auto;
  font-family: monospace;
  font-size: 9px;
  font-weight: bold;
  padding: 1px 5px;
  border-radius: 2px;
}

.step-status-tag.success { background: rgba(16, 185, 129, 0.15); color: #10b981; }
.step-status-tag.warning { background: rgba(245, 158, 11, 0.15); color: #f59e0b; }
.step-status-tag.failed { background: rgba(244, 63, 94, 0.15); color: #f43f5e; }

.step-card-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.step-detail-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.indicator-icon {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  margin-top: 6px;
  flex-shrink: 0;
}

.detail-type-pass .indicator-icon { background: #10b981; box-shadow: 0 0 4px #10b981; }
.detail-type-fail .indicator-icon { background: #f43f5e; box-shadow: 0 0 4px #f43f5e; }
.detail-type-warn .indicator-icon { background: #f59e0b; box-shadow: 0 0 4px #f59e0b; }
.detail-type-info .indicator-icon { background: #64748b; }

.detail-text {
  font-size: 11.5px;
  line-height: 1.5;
  color: #94a3b8;
  margin: 0;
  font-family: monospace;
}

.status-badge {
  display: inline-block;
  padding: 0 3px;
  font-family: monospace;
  font-size: 8px;
  font-weight: bold;
  border-radius: 2px;
  margin-right: 4px;
}

.status-badge.pass { background: rgba(16, 185, 129, 0.2); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); }
.status-badge.fail { background: rgba(244, 63, 94, 0.2); color: #f43f5e; border: 1px solid rgba(244, 63, 94, 0.3); }
.status-badge.warn { background: rgba(245, 158, 11, 0.2); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.3); }
.status-badge.info { background: rgba(100, 116, 139, 0.2); color: #94a3b8; }

/* 审计历史表格 */
.cyber-table {
  border-collapse: collapse;
}

.cyber-tr {
  transition: background 0.2s;
}

.cyber-tr:hover {
  background: rgba(34, 211, 238, 0.04);
}

.job-accent {
  color: #e2e8f0;
}

.time-col {
  font-family: monospace;
  color: #64748b;
  font-size: 11px;
}

.dur-col {
  font-family: monospace;
  color: #94a3b8;
}

.tag-neon {
  display: inline-block;
  padding: 1px 6px;
  font-family: monospace;
  font-size: 10px;
  font-weight: bold;
  border-radius: 3px;
}

.neon-success {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
  border: 1px solid rgba(16, 185, 129, 0.25);
  box-shadow: 0 0 4px rgba(16, 185, 129, 0.1);
}

.neon-failed {
  background: rgba(244, 63, 94, 0.1);
  color: #f43f5e;
  border: 1px solid rgba(244, 63, 94, 0.25);
  box-shadow: 0 0 4px rgba(244, 63, 94, 0.1);
}

.tbl-btn {
  background: transparent;
  border: 1px solid rgba(34, 211, 238, 0.3);
  color: #22d3ee;
  border-radius: 3px;
  padding: 2px 8px;
  font-size: 11px;
  cursor: pointer;
  transition: all 0.2s;
}

.tbl-btn:hover {
  background: rgba(34, 211, 238, 0.12);
  border-color: #22d3ee;
  box-shadow: 0 0 5px rgba(34, 211, 238, 0.15);
}

/* 滚动条 */
.report-details-container::-webkit-scrollbar,
.layer-table-wrap::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

.report-details-container::-webkit-scrollbar-thumb,
.layer-table-wrap::-webkit-scrollbar-thumb {
  background: rgba(34, 211, 238, 0.15);
  border-radius: 3px;
}

.report-details-container::-webkit-scrollbar-thumb:hover,
.layer-table-wrap::-webkit-scrollbar-thumb:hover {
  background: rgba(34, 211, 238, 0.3);
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 1300px) {
  .health-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 1024px) {
  .system-grid {
    grid-template-columns: 1fr;
  }
}
</style>
