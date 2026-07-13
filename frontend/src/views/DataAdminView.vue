<template>
  <section class="screen-page data-admin-page">
    <div class="screen-board data-admin-board">
      <header class="screen-titlebar">
        <div>
          <p class="screen-kicker">离线数仓治理与任务运维</p>
          <h2>{{ pageTitle }}</h2>
        </div>
        <div class="screen-tools">
          <a-button type="outline" size="large" @click="openScreen" style="color: #22d3ee; border-color: rgba(34, 211, 238, 0.45); margin-right: 8px;">进入实时大屏 ↗</a-button>
          <a-button type="primary" size="large" :loading="loading" :disabled="loading" @click="loadAll({ force: true })">刷新</a-button>
        </div>
      </header>

      <!-- Unified States overlay/container -->
      <div v-if="loading && !hasLoaded" class="state-wrapper">
        <LoadingState message="正在加载数仓治理与任务运维指标..." />
      </div>
      <div v-else-if="error && !hasLoaded" class="state-wrapper">
        <ErrorState :reason="error" @retry="loadAll" />
      </div>
      <div v-else-if="isEmpty && !hasLoaded" class="state-wrapper">
        <EmptyState />
      </div>

      <a-tabs v-show="hasLoaded || (!loading && !error && !isEmpty)" v-model:active-key="activeTab" class="admin-tabs">
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
                <h3>Source -> Raw -> Clean -> Metric 漏斗 (当日批处理新增)</h3>
                <span>{{ overview.recent_failed_task ? `最近失败 ${overview.recent_failed_task}` : 'pipeline' }}</span>
              </div>
              <div :key="`funnel-${overviewChartRenderKey}`" ref="funnelChartRef" class="screen-chart" style="height: 240px; margin-top: 10px;"></div>
            </article>

            <article class="screen-panel">
              <div class="screen-panel-head">
                <h3>最近 7 天数据量趋势</h3>
                <span>Raw / Clean</span>
              </div>
              <div :key="`trend-${overviewChartRenderKey}`" ref="trendChartRef" class="screen-chart"></div>
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
                <h3>离线链路状态 (历史全量累计)</h3>
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

            <!-- HDFS 存储资产配额环形图 -->
            <article class="screen-panel">
              <div class="screen-panel-head">
                <h3>HDFS 存储资产配额</h3>
                <span>Parquet 压缩节省 {{ percent(overview.parquet_saving_rate || 0.784) }}</span>
              </div>
              <div ref="storageChartRef" class="screen-chart" style="height: 240px; margin-top: 10px;"></div>
            </article>

            <!-- Spark 离线计算性能瓶颈条形图 -->
            <article class="screen-panel">
              <div class="screen-panel-head">
                <h3>Spark 离线计算性能瓶颈</h3>
                <span>Run duration (Seconds)</span>
              </div>
              <div ref="perfChartRef" class="screen-chart" style="height: 240px; margin-top: 10px;"></div>
            </article>
            <!-- 数据质量检测与合规明细表格（横跨整行） -->
            <article class="screen-panel" style="grid-column: span 2; margin-top: 16px;">
              <div class="screen-panel-head">
                <h3>数据质量检测与合规明细</h3>
                <span>待处理问题: {{ qualityOverview.pending_count || 0 }} | 平均通过率: {{ percent2(qualityOverview.avg_pass_rate) }}</span>
              </div>
              <div class="screen-table-wrap">
                <table class="data-table screen-native-table">
                  <thead>
                    <tr>
                      <th>规则代码</th>
                      <th>规则名称</th>
                      <th>物理数据集</th>
                      <th>业务日期</th>
                      <th>检测总行数</th>
                      <th>异常拦截行数</th>
                      <th>规则合规率</th>
                      <th>异常样本</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="issue in qualityIssues" :key="issue.rule_code">
                      <td><code>{{ issue.rule_code }}</code></td>
                      <td>{{ issue.rule_name }}</td>
                      <td>{{ issue.dataset_code }}</td>
                      <td>{{ issue.biz_date }}</td>
                      <td>{{ formatNumber(issue.total_count) }}</td>
                      <td><span :class="{ 'tag failed': issue.failed_count > 0 }">{{ issue.failed_count }}</span></td>
                      <td><strong>{{ percent2(issue.pass_rate) }}</strong></td>
                      <td><a-button type="text" size="mini" @click="showJson(issue.sample_data_json, issue.failed_count > 5 ? `异常样本预览 (总异常行数: ${issue.failed_count} 行，此处仅展示最新 5 条样本)` : `异常样本预览 (共 ${issue.failed_count} 行，已全部展示)`)" :disabled="!issue.sample_data_json">查看样本</a-button></td>
                    </tr>
                    <tr v-if="!qualityIssues.length">
                      <td colspan="8" class="empty-cell" style="text-align: center; color: #94a3b8; padding: 32px; font-style: italic;">
                        暂无数据质量异常（所有规则检测合规率 100%）
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </article>
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
                <h3>数据血缘</h3>
                <span>Source to Analytics</span>
              </div>
              <div ref="lineageChartRef" class="screen-chart" style="height: 280px; margin-top: 10px;"></div>
            </article>
          </section>


          <!-- Three-Layer Data Warehouse Responsibility Section with Integrated Data Viewer -->
          <section class="screen-panel warehouse-layers-panel" style="margin-top: 16px;">
            <div class="screen-panel-head">
              <h3>数仓分层职责架构与数据查看</h3>
              <span>ODS ➔ DWD ➔ DWS ➔ ADS (点击对应层级卡片可直接查看/查询物理数据)</span>
            </div>
            <div class="warehouse-layers-flow">
              <div :class="['layer-card', 'ods-card', { active: selectedLayer === 'ods' }]" @click="selectLayer('ods')">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                  <div class="layer-title">ODS 层</div>
                  <span class="tag success" style="font-size: 10px; padding: 2px 6px; border-radius: 4px;">正常</span>
                </div>
                <div class="layer-eng">Operational Data Store</div>
                <p class="layer-desc">原始数据落地，保持数据原貌，接入格式各异的原始事件（JSON）。</p>
                <div class="layer-mapping">
                  <div>链路：<strong>Source ➔ HDFS Raw</strong></div>
                  <div>载体：<code>/agentscope/raw/</code> (JSON)</div>
                </div>
              </div>
              <div class="layer-arrow">➔</div>
              <div :class="['layer-card', 'dwd-card', { active: selectedLayer === 'dwd' }]" @click="selectLayer('dwd')">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                  <div class="layer-title">DWD 层</div>
                  <span :class="['tag', qualityOverview.issue_count > 0 ? 'failed' : 'success']" style="font-size: 10px; padding: 2px 6px; border-radius: 4px;">
                    {{ qualityOverview.issue_count > 0 ? `已过滤掉 ${qualityOverview.issue_count} 个异常` : '正常' }}
                  </span>
                </div>
                <div class="layer-eng">Data Warehouse Detail</div>
                <p class="layer-desc">数据清洗与标准化，过滤坏账去重，提供干净、无重复、字段统一的存储。</p>
                <div class="layer-mapping">
                  <div>链路：<strong>HDFS Raw ➔ HDFS Clean</strong></div>
                  <div>载体：<code>/agentscope/clean/</code> (Parquet)</div>
                </div>
              </div>
              <div class="layer-arrow">➔</div>
              <div :class="['layer-card', 'dws-card', { active: selectedLayer === 'dws' }]" @click="selectLayer('dws')">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                  <div class="layer-title">DWS 层</div>
                  <span class="tag success" style="font-size: 10px; padding: 2px 6px; border-radius: 4px;">数据已更新</span>
                </div>
                <div class="layer-eng">Data Warehouse Summary</div>
                <p class="layer-desc">轻度汇总，按天/小时/Agent等多维主题聚合，提供下游可视化直接消费。</p>
                <div class="layer-mapping">
                  <div>链路：<strong>HDFS Clean ➔ MySQL Analytics</strong></div>
                  <div>载体：<code>daily_metrics</code> / <code>agent_rankings</code> 表</div>
                </div>
              </div>
              <div class="layer-arrow">➔</div>
              <div :class="['layer-card', 'ads-card', { active: selectedLayer === 'ads' }]" @click="selectLayer('ads')">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                  <div class="layer-title">ADS 层</div>
                  <span class="tag success" style="font-size: 10px; padding: 2px 6px; border-radius: 4px;">服务已就绪</span>
                </div>
                <div class="layer-eng">Application Data Service</div>
                <p class="layer-desc">面向特定图表与AI报告等直接定制的分析视图数据，与底层公共汇总解耦。</p>
                <div class="layer-mapping">
                  <div>链路：<strong>DWD / DWS ➔ MySQL ADS</strong></div>
                  <div>载体：<code>error_distribution</code> / <code>historical_alerts</code> 表</div>
                </div>
              </div>
            </div>

            <!-- Filters & Data Table for Selected Layer -->
            <div style="margin-top: 24px; border-top: 1px dashed rgba(34, 211, 238, 0.15); padding-top: 20px;">
              <section v-if="selectedLayer === 'ods'" class="toolbar admin-filter warehouse-filter" style="margin-top: 0;">
                <label>event_id<input v-model="eventFilters.event_id" /></label>
                <label>trace_id<input v-model="eventFilters.trace_id" /></label>
                <label>run_id<input v-model="eventFilters.run_id" /></label>
                <label>agent_id<select v-model="eventFilters.agent_id"><option value="">全部</option><option v-for="agent in agentOptions" :key="agent" :value="agent">{{ agent }}</option></select></label>
                <label>event_type<select v-model="eventFilters.event_type"><option value="">全部</option><option v-for="type in eventTypeOptions" :key="type" :value="type">{{ type }}</option></select></label>
                <label>status<select v-model="eventFilters.status"><option value="">全部</option><option v-for="status in statusOptions" :key="status" :value="status">{{ status }}</option></select></label>
                <a-button type="primary" @click="loadEvents">查询</a-button>
              </section>
              <section v-if="selectedLayer === 'dwd'" class="toolbar admin-filter warehouse-filter" style="margin-top: 0;">
                <label>event_id<input v-model="dwdFilters.event_id" /></label>
                <label>trace_id<input v-model="dwdFilters.trace_id" /></label>
                <label>agent_id<select v-model="dwdFilters.agent_id"><option value="">全部</option><option v-for="agent in agentOptions" :key="agent" :value="agent">{{ agent }}</option></select></label>
                <label>event_type<select v-model="dwdFilters.event_type"><option value="">全部</option><option v-for="type in eventTypeOptions" :key="type" :value="type">{{ type }}</option></select></label>
                <label>status<select v-model="dwdFilters.status"><option value="">全部</option><option v-for="status in statusOptions" :key="status" :value="status">{{ status }}</option></select></label>
                <a-button type="primary" @click="loadLayerData">查询</a-button>
              </section>
              <section v-if="selectedLayer === 'dws'" class="toolbar admin-filter warehouse-filter" style="margin-top: 0;">
                <label>
                  开始日期
                  <a-date-picker
                    v-model="dwsFilters.start_date"
                    value-format="YYYY-MM-DD"
                    format="YYYY/MM/DD"
                    allow-clear
                    @change="(value) => setDwsDate('start_date', value)"
                  />
                </label>
                <label>
                  结束日期
                  <a-date-picker
                    v-model="dwsFilters.end_date"
                    value-format="YYYY-MM-DD"
                    format="YYYY/MM/DD"
                    allow-clear
                    @change="(value) => setDwsDate('end_date', value)"
                  />
                </label>
                <a-button type="primary" @click="loadLayerData">查询</a-button>
              </section>

              <!-- Tables -->
              <div v-if="selectedLayer === 'ods'" class="screen-table-wrap layer-table-wrap" style="margin-top: 12px;">
                <div class="layer-table-title">
                  <strong>Agent 原始事件</strong>
                  <span>{{ events.length }} records</span>
                </div>
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
                    <tr v-if="!events.length">
                      <td colspan="9" class="empty-cell">暂无 ODS 原始事件数据</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <div v-if="selectedLayer === 'dwd'" class="screen-table-wrap layer-table-wrap" style="margin-top: 12px;">
                <div class="layer-table-title">
                  <strong>DWD 清洗明细事件</strong>
                  <span>{{ dwdEvents.length }} records</span>
                </div>
                <table class="data-table screen-native-table admin-table">
                  <thead>
                    <tr>
                      <th>event_id</th>
                      <th>trace_id</th>
                      <th>agent_id</th>
                      <th>event_type</th>
                      <th>status</th>
                      <th>latency_ms</th>
                      <th>event_time</th>
                      <th>JSON</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="event in dwdEvents" :key="event.event_id">
                      <td>{{ event.event_id }}</td>
                      <td>{{ event.trace_id }}</td>
                      <td>{{ event.agent_id }}</td>
                      <td>{{ event.event_type }}</td>
                      <td><span :class="['tag', event.status]">{{ event.status || '-' }}</span></td>
                      <td>{{ event.latency_ms }}</td>
                      <td>{{ event.event_time || event.create_time || '-' }}</td>
                      <td><a-button size="mini" @click="showJson(event.raw_json || event)">查看</a-button></td>
                    </tr>
                    <tr v-if="!dwdEvents.length">
                      <td colspan="8" class="empty-cell">暂无 DWD 明细数据</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <div v-if="selectedLayer === 'dws'" class="screen-table-wrap layer-table-wrap" style="margin-top: 12px;">
                <div class="layer-table-title">
                  <strong>DWS 每日汇总指标</strong>
                  <span>{{ dwsMetrics.length }} records</span>
                </div>
                <table class="data-table screen-native-table admin-table">
                  <thead>
                    <tr>
                      <th>metric_date</th>
                      <th>task_count</th>
                      <th>success_count</th>
                      <th>failed_count</th>
                      <th>success_rate</th>
                      <th>avg_latency_ms</th>
                      <th>p95_latency_ms</th>
                      <th>estimated_cost_usd</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="metric in dwsMetrics" :key="metric.metric_date">
                      <td>{{ metric.metric_date }}</td>
                      <td>{{ formatNumber(metric.task_count) }}</td>
                      <td>{{ formatNumber(metric.success_count) }}</td>
                      <td>{{ formatNumber(metric.failed_count) }}</td>
                      <td>{{ percent(metric.success_rate) }}</td>
                      <td>{{ formatNumber(metric.avg_latency_ms) }}</td>
                      <td>{{ formatNumber(metric.p95_latency_ms) }}</td>
                      <td>{{ Number(metric.estimated_cost_usd || 0).toFixed(4) }}</td>
                    </tr>
                    <tr v-if="!dwsMetrics.length">
                      <td colspan="8" class="empty-cell">暂无 DWS 指标数据</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <!-- ADS Filters -->
              <section v-if="selectedLayer === 'ads'" class="toolbar admin-filter warehouse-filter" style="margin-top: 0;">
                <label style="flex: 0 0 240px; min-width: 240px;">
                  选择应用数据表
                  <select v-model="adsSelectedTable" @change="loadLayerData" style="width: 200px;">
                    <option value="error_distribution">error_distribution (异常分布)</option>
                    <option value="historical_alerts">historical_alerts (历史告警)</option>
                  </select>
                </label>
                <label>
                  开始日期
                  <a-date-picker
                    v-model="adsFilters.start_date"
                    value-format="YYYY-MM-DD"
                    allow-clear
                  />
                </label>
                <label>
                  结束日期
                  <a-date-picker
                    v-model="adsFilters.end_date"
                    value-format="YYYY-MM-DD"
                    allow-clear
                  />
                </label>
                <a-button type="primary" @click="loadLayerData">查询</a-button>
              </section>

              <!-- ADS error_distribution Table -->
              <div v-if="selectedLayer === 'ads' && adsSelectedTable === 'error_distribution'" class="screen-table-wrap layer-table-wrap" style="margin-top: 12px;">
                <div class="layer-table-title">
                  <strong>ADS 异常错误分布表 (error_distribution)</strong>
                  <span>{{ adsDataList.length }} records</span>
                </div>
                <table class="data-table screen-native-table admin-table">
                  <thead>
                    <tr>
                      <th style="width: 250px;">错误类型 (error_type)</th>
                      <th style="width: 150px;">异常次数 (total_count)</th>
                      <th style="width: 150px;">占比 (percentage)</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(item, idx) in adsDataList" :key="idx">
                      <td><code>{{ item.error_type }}</code></td>
                      <td>{{ formatNumber(item.total_count) }}</td>
                      <td>{{ (Number(item.percentage || 0) * 100).toFixed(2) }}%</td>
                    </tr>
                    <tr v-if="!adsDataList.length">
                      <td colspan="3" class="empty-cell">暂无异常分布数据</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <!-- ADS historical_alerts Table -->
              <div v-if="selectedLayer === 'ads' && adsSelectedTable === 'historical_alerts'" class="screen-table-wrap layer-table-wrap" style="margin-top: 12px;">
                <div class="layer-table-title">
                  <strong>ADS 历史告警归档表 (historical_alerts)</strong>
                  <span>{{ adsDataList.length }} records</span>
                </div>
                <table class="data-table screen-native-table admin-table">
                  <thead>
                    <tr>
                      <th>告警 ID (alert_id)</th>
                      <th>业务日期 (metric_date)</th>
                      <th>告警类型 (alert_type)</th>
                      <th>级别 (level)</th>
                      <th>智能体 (agent_id)</th>
                      <th>当前值 (current_val)</th>
                      <th>阀值 (threshold)</th>
                      <th>状态 (status)</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="item in adsDataList" :key="item.alert_id">
                      <td><code>{{ item.alert_id }}</code></td>
                      <td>{{ item.metric_date }}</td>
                      <td>{{ item.alert_type }}</td>
                      <td>
                        <span :class="['tag', item.level === 'error' || item.level === 'critical' ? 'failed' : 'warning']">
                          {{ item.level }}
                        </span>
                      </td>
                      <td><code>{{ item.agent_id || 'system' }}</code></td>
                      <td>{{ item.current_value ?? item.current_val }}</td>
                      <td>{{ item.threshold_value ?? item.threshold }}</td>
                      <td>
                        <span :class="['tag', item.status === 'resolved' ? 'success' : 'failed']">
                          {{ item.status }}
                        </span>
                      </td>
                    </tr>
                    <tr v-if="!adsDataList.length">
                      <td colspan="8" class="empty-cell">暂无历史告警数据</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </section>

        </a-tab-pane>

        <a-tab-pane key="jobs" title="数据任务管理">
          <!-- Scheduling and Pipeline Banner -->
          <div class="scheduler-banner">
            <div class="banner-content">
              <h4>自动调度与数据补数说明</h4>
              <p>离线计算流水线提供 <strong>Crontab 定时任务（每天凌晨 02:00）</strong> 的脚本示例，但是否自动运行取决于生产环境是否已单独部署该调度。此控制台主要用于开发与运维进行历史日期补数（Backfill）或失败作业的手动重试。运行前请确认源数据库（MySQL Source）在所选业务日期是否有数据。</p>
            </div>
          </div>

          <!-- 清洗前置：数据质量规则配置 (Data Quality Rules Configuration) -->
          <section class="screen-panel" style="margin-top: 16px; margin-bottom: 16px;">
            <div class="screen-panel-head">
              <h3>清洗前置：质量规则配置</h3>
            </div>
            <div style="margin: 0 0 12px; color: rgba(226, 232, 240, 0.72); font-size: 12px; line-height: 1.6;">
              <span style="color: #22d3ee; font-weight: bold;">[说明]</span>
              Spark 离线清洗任务运行前，会加载此处已启用的质量规则，并在 <strong>Stage 2 (数据清洗)</strong> 中对 ODS 原始事件进行过滤，不符合规则的记录将进入脏数据归档。
            </div>
            <div class="screen-table-wrap">
              <table class="data-table screen-native-table admin-table">
                <thead>
                  <tr>
                    <th style="width: 150px;">规则代码 (rule_id)</th>
                    <th style="width: 250px;">规则名称 (rule_name)</th>
                    <th style="width: 120px;">启用状态 (is_active)</th>
                    <th style="width: 100px;">操作</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="rule in qualityRules" :key="rule.rule_id">
                    <td><code>{{ rule.rule_id }}</code></td>
                    <td>{{ rule.rule_name }}</td>
                    <td>
                      <span :class="['tag', rule.is_active ? 'success' : 'failed']">
                        {{ rule.is_active ? '已启用' : '已禁用' }}
                      </span>
                    </td>
                    <td>
                      <a-button size="mini" :type="rule.is_active ? 'outline' : 'primary'" @click="toggleRule(rule)">
                        {{ rule.is_active ? '禁用' : '启用' }}
                      </a-button>
                    </td>
                  </tr>
                  <tr v-if="!qualityRules.length">
                    <td colspan="4" class="empty-cell">暂无配置规则</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <section class="screen-panel">
            <div class="screen-panel-head">
              <h3>任务流水线</h3>
              <div class="header-actions" style="display: flex; gap: 10px;">
                <a-date-picker
                  v-model="bizDate"
                  value-format="YYYY-MM-DD"
                  size="large"
                  :disabled-date="disableFutureBizDate"
                />
                <a-tooltip content="控制模拟器生成的任务轨迹数量；每条轨迹会拆分出多条事件明细">
                  <div style="display: flex; align-items: center; gap: 6px;">
                    <span style="color: #cbd5e1; font-size: 13px; white-space: nowrap;">模拟轨迹数</span>
                    <a-input-number
                      v-model="generateCount"
                      :min="1"
                      :max="100000"
                      :step="50"
                      placeholder="轨迹条数"
                      size="large"
                      style="width: 130px;"
                    />
                  </div>
                </a-tooltip>
                <a-tooltip content="只影响一键完整链路；单独点击生成数据时始终会生成并追加">
                  <div style="display: flex; align-items: center; gap: 6px;">
                    <span style="color: #cbd5e1; font-size: 13px; white-space: nowrap;">一键生成策略</span>
                    <a-select
                      v-model="pipelineGenerateMode"
                      size="large"
                      style="width: 150px;"
                  >
                    <a-option value="append">重新生成并追加</a-option>
                    <a-option value="skip">跳过生成</a-option>
                  </a-select>
                </div>
                </a-tooltip>
                <a-button class="pipeline-toolbar-btn" type="outline" size="large" @click="diagramModalOpen = true" style="height: 40px; min-height: 40px; padding: 0 16px; box-sizing: border-box;">
                  层次示意
                </a-button>
                <a-button 
                  class="pipeline-toolbar-btn"
                  type="outline" 
                  :loading="runningJobs['offline_generate']" 
                  :disabled="anyJobRunning" 
                  @click="runJob('offline_generate')"
                  style="height: 40px; min-height: 40px; padding: 0 16px; box-sizing: border-box;"
                >
                  {{ runningJobs['offline_generate'] ? '数据生成中...' : '生成所选日期模拟数据' }}
                </a-button>
                <a-button 
                  type="primary" 
                  :loading="pipelineRunning" 
                  :disabled="anyJobRunning" 
                  @click="runFullPipeline"
                  style="height: 40px; min-height: 40px; padding: 0 16px; box-sizing: border-box;"
                >
                  {{ pipelineRunning ? '整条链路执行中...' : '一键执行完整离线链路' }}
                </a-button>
              </div>
            </div>

            <!-- Horizontal Pipeline Workflow Layout -->
            <div class="pipeline-flow-layout">
              <!-- Stage 1 -->
              <div class="pipeline-stage-box" :class="{ 'stage-running': isStageRunning(1) }">
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
                      :disabled="anyJobRunning && !runningJobs[job.job_code]" 
                      :class="{ 'btn-running': runningJobs[job.job_code] }"
                      @click="runJob(job.job_code)"
                    >
                      {{ runningJobs[job.job_code] ? '运行中' : '执行' }}
                    </a-button>
                  </div>
                </div>
              </div>

              <div class="pipeline-flow-arrow">➔</div>

              <!-- Stage 2 -->
              <div class="pipeline-stage-box" :class="{ 'stage-running': isStageRunning(2) }">
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
                      :disabled="anyJobRunning && !runningJobs[job.job_code]" 
                      :class="{ 'btn-running': runningJobs[job.job_code] }"
                      @click="runJob(job.job_code)"
                    >
                      {{ runningJobs[job.job_code] ? '运行中' : '执行' }}
                    </a-button>
                  </div>
                </div>
              </div>

              <div class="pipeline-flow-arrow">➔</div>

              <!-- Stage 3 -->
              <div class="pipeline-stage-box stage-box-wide" :class="{ 'stage-running': isStageRunning(3) }">
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
                      :disabled="anyJobRunning && !runningJobs[job.job_code]" 
                      :class="{ 'btn-running': runningJobs[job.job_code] }"
                      @click="runJob(job.job_code)"
                    >
                      {{ runningJobs[job.job_code] ? '运行中' : '执行' }}
                    </a-button>
                  </div>
                </div>
              </div>

              <div class="pipeline-flow-arrow">➔</div>

              <!-- Stage 4 -->
              <div class="pipeline-stage-box" :class="{ 'stage-running': isStageRunning(4) }">
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
                      :disabled="anyJobRunning && !runningJobs[job.job_code]" 
                      :class="{ 'btn-running': runningJobs[job.job_code] }"
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
                  <tr>
                    <th style="width: 140px;">run_id</th>
                    <th style="width: 120px;">job_code</th>
                    <th style="width: 95px;">biz_date</th>
                    <th style="width: 75px;">状态</th>
                    <th style="width: 75px;">输入</th>
                    <th style="width: 75px;">输出</th>
                    <th style="width: 65px;">异常</th>
                    <th style="width: 160px;">开始</th>
                    <th style="width: 160px;">结束</th>
                    <th style="width: 65px;">耗时</th>
                    <th style="width: 65px;">日志</th>
                    <th style="width: 70px;">操作</th>
                  </tr>
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
                    <td class="nowrap">{{ formatDateTime(run.start_time) }}</td>
                    <td class="nowrap">{{ formatDateTime(run.end_time) }}</td>
                    <td>{{ run.duration_seconds ?? '-' }}s</td>
                    <td><a-button size="mini" @click="showLogs(run.run_id)">查看</a-button></td>
                    <td><a-button size="mini" :disabled="run.status !== 'failed'" @click="retryRun(run.run_id)">重试</a-button></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

         </a-tab-pane>
      </a-tabs>
    </div>

    <a-modal v-model:visible="jsonModalOpen" class="deep-blue-modal" :title="jsonModalTitle" width="760px" :footer="false">
      <pre class="json-pre">{{ jsonPreview }}</pre>
    </a-modal>

    <a-modal v-model:visible="diagramModalOpen" class="deep-blue-modal" title="模拟轨迹层次示意" width="1040px" :footer="false">
      <div style="padding: 4px 2px 2px; max-height: 72vh; overflow: auto;">
        <div style="display: flex; justify-content: center; margin-bottom: 14px;">
          <div style="padding: 8px 18px; border-radius: 999px; background: rgba(12, 74, 110, 0.62); border: 1px solid rgba(56, 189, 248, 0.38); color: #e0f2fe; font-weight: 700;">
            trace / workflow
          </div>
        </div>

        <div style="position: relative; padding: 8px 0 4px; display: flex; flex-direction: column; align-items: center; gap: 14px;">
          <div style="width: 100%; overflow-x: auto; padding-bottom: 6px;">
            <div style="display: flex; flex-wrap: nowrap; gap: 14px; align-items: flex-start; min-width: max-content; padding: 4px 2px;">
              <div
                v-for="node in diagramTree"
                :key="node.agent"
                style="flex: 0 0 180px; width: 180px; padding: 14px 14px 12px; border-radius: 10px; background: rgba(8, 47, 73, 0.28); border: 1px solid rgba(56, 189, 248, 0.14);"
              >
                <div style="display: flex; justify-content: center; margin-bottom: 10px;">
                  <div style="padding: 7px 12px; border-radius: 999px; background: rgba(15, 23, 42, 0.72); border: 1px solid rgba(56, 189, 248, 0.22); color: #e0f2fe; font-size: 13px; font-weight: 700;">{{ node.agent }}</div>
                </div>
                <div style="display: flex; flex-direction: column; gap: 8px;">
                  <div v-for="event in node.events" :key="`${node.agent}-${event.label}`" style="display: inline-flex; align-items: center; gap: 8px; min-height: 22px;">
                    <span
                      :style="{
                        width: '8px',
                        height: '8px',
                        borderRadius: '999px',
                        background: event.solid ? '#38bdf8' : 'transparent',
                        border: event.solid ? 'none' : '1.2px solid #7dd3fc',
                        flex: '0 0 auto'
                      }"
                    ></span>
                    <span
                      :style="{
                        padding: '5px 10px',
                        borderRadius: '999px',
                        background: 'rgba(15, 23, 42, 0.66)',
                        border: event.solid ? '1px solid rgba(56, 189, 248, 0.18)' : '1px dashed rgba(125, 211, 252, 0.30)',
                        color: '#e0f2fe',
                        fontSize: '12px',
                        lineHeight: '1',
                        whiteSpace: 'nowrap'
                      }"
                    >{{ event.label }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </a-modal>


  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { Message } from '@arco-design/web-vue'
import LoadingState from '../components/LoadingState.vue'
import EmptyState from '../components/EmptyState.vue'
import ErrorState from '../components/ErrorState.vue'

const loading = ref(true)
const error = ref('')
const isEmpty = ref(false)
const hasLoaded = ref(false)
import {
  executeAdminJob,
  fetchAdminEvents,
  fetchAdminJobLogs,
  fetchAdminJobRuns,
  fetchAdminJobs,
  fetchAdminOverview,
  fetchDataLineage,
  fetchDataVolumeTrend,
  fetchDatasets,
  fetchDwdEvents,
  fetchDwsMetrics,
  fetchPipelineStatus,
  fetchQualityIssues,
  fetchQualityOverview,
  fetchQualityRules,
  createQualityRule,
  updateQualityRule,
  retryAdminJobRun
} from '../api/admin'
import { fetchHistoryAlerts } from '../api/dashboard'
import { fetchAnalyticsErrors } from '../api/statistics'
import { lineOption } from '../charts/options'
const route = useRoute()
const router = useRouter()
const openScreen = () => {
  window.open('/overview', '_blank')
}

const activeTab = ref('overview')
const overviewDirty = ref(false)
const overviewChartRenderKey = ref(0)
let activeLoadCount = 0
const moduleRequests = new Map()
const requestCache = new Map()
const CACHE_TTL_MS = 8000

const pageTitle = computed(() => {
  if (route.path === '/data-overview') return '数据总览'
  if (route.path === '/data-assets') return '数据资产'
  if (route.path === '/data-jobs') return '数据任务'
  return '数据管理端'
})

watch(
  () => route.path,
  (path) => {
    if (path === '/data-overview') {
      activeTab.value = 'overview'
    } else if (path === '/data-assets') {
      activeTab.value = 'assets'
    } else if (path === '/data-jobs') {
      activeTab.value = 'jobs'
    }
  },
  { immediate: true }
)
const bizDate = ref(todayString())
const generateCount = ref(50)
const pipelineGenerateMode = ref('append')
const diagramModalOpen = ref(false)
const diagramTree = [
  {
    agent: 'planner',
    events: [
      { label: 'agent_start', solid: true },
      { label: 'llm_request', solid: true },
      { label: 'llm_response', solid: true },
      { label: 'agent_complete', solid: true }
    ]
  },
  {
    agent: 'search',
    events: [
      { label: 'agent_start', solid: true },
      { label: 'llm_request', solid: true },
      { label: 'llm_response', solid: true },
      { label: 'tool_call', solid: false },
      { label: 'tool_result', solid: false },
      { label: 'agent_complete', solid: true }
    ]
  },
  {
    agent: 'analysis',
    events: [
      { label: 'agent_start', solid: true },
      { label: 'llm_request', solid: true },
      { label: 'llm_response', solid: true },
      { label: 'agent_complete', solid: true }
    ]
  },
  {
    agent: 'writer',
    events: [
      { label: 'agent_start', solid: true },
      { label: 'llm_request', solid: true },
      { label: 'llm_response', solid: true },
      { label: 'agent_complete', solid: true },
      { label: 'retry', solid: false },
      { label: 'agent_failed', solid: false }
    ]
  },
  {
    agent: 'reviewer',
    events: [
      { label: 'agent_start', solid: true },
      { label: 'llm_request', solid: true },
      { label: 'llm_response', solid: true },
      { label: 'agent_complete', solid: true },
      { label: 'retry', solid: false },
      { label: 'agent_failed', solid: false }
    ]
  }
]

const overview = ref({})
const trend = ref([])
const pipeline = ref({})
const datasets = ref([])
const lineage = ref({})
const events = ref([])
const selectedLayer = ref('ods')
const dwdEvents = ref([])
const dwsMetrics = ref([])
const dwdFilters = ref({ event_id: '', trace_id: '', agent_id: '', event_type: '', status: '' })
const dwsFilters = ref({ start_date: '', end_date: '' })
const adsSelectedTable = ref('error_distribution')
const adsFilters = ref({ start_date: todayString(), end_date: todayString() })
const adsDataList = ref([])
const jobs = ref([])
const jobRuns = ref([])
const qualityOverview = ref({})
const qualityIssues = ref([])
const qualityRules = ref([])
const recleaning = ref({})
const eventFilters = ref({ event_id: '', trace_id: '', run_id: '', agent_id: '', event_type: '', status: '' })
const agentOptions = ['planner_agent', 'search_agent', 'analysis_agent', 'writer_agent', 'reviewer_agent']
const eventTypeOptions = ['agent_start', 'agent_complete', 'agent_failed', 'llm_request', 'llm_response', 'tool_call', 'tool_result', 'retry']
const statusOptions = ['success', 'failed', 'running']

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

function isStageRunning(stage) {
  return getJobsByStage(stage).some(job => runningJobs.value[job.job_code])
}
const jsonModalOpen = ref(false)
const jsonModalTitle = ref('JSON 详情')
const jsonPreview = ref('')
const trendChartRef = ref(null)
const funnelChartRef = ref(null)
const lineageChartRef = ref(null)
const storageChartRef = ref(null)
const perfChartRef = ref(null)
let trendChart
let funnelChart
let lineageChart
let storageChart
let perfChart

const defaultComputePerf = [
  { job_name: 'DataX 业务同步', duration: 8 },
  { job_name: 'Spark 格式清洗', duration: 22 },
  { job_name: 'Spark 每日指标聚合', duration: 12 },
  { job_name: 'Spark 节点关系分析', duration: 18 },
  { job_name: 'Spark 错误分布聚合', duration: 45 }
]

const defaultLineage = {
  nodes: [
    { id: 'mysql_source', name: 'MySQL Source' },
    { id: 'hdfs_raw', name: 'HDFS Raw' },
    { id: 'hdfs_clean', name: 'HDFS Clean' },
    { id: 'daily_metric', name: 'Daily Metric' },
    { id: 'mysql_analytics', name: 'MySQL Analytics' }
  ],
  edges: [
    { from: 'mysql_source', to: 'hdfs_raw', label: 'DataX' },
    { from: 'hdfs_raw', to: 'hdfs_clean', label: 'Spark Clean' },
    { from: 'hdfs_clean', to: 'daily_metric', label: 'Spark Analysis' },
    { from: 'daily_metric', to: 'mysql_analytics', label: 'Write Back' }
  ]
}

const defaultHdfsStorage = {
  used_bytes: 1331589120,
  limit_bytes: 10737418240
}

const overviewMetrics = computed(() => [
  { label: 'MySQL Source 总量', value: formatNumber(overview.value.source_total_count), hint: `今日新增 ${formatNumber(overview.value.today_new_count)}` },
  { label: 'HDFS Raw 分区', value: overview.value.raw_partition_count ?? '-', hint: latestHint(overview.value.raw_latest_biz_date) },
  { label: 'HDFS Clean 分区', value: overview.value.clean_partition_count ?? '-', hint: latestHint(overview.value.clean_latest_biz_date) },
  { label: 'HDFS Metric 分区', value: overview.value.metric_partition_count ?? '-', hint: latestHint(overview.value.metric_latest_biz_date) },
  { label: 'Raw 到 Clean 有效率', value: percent(overview.value.raw_to_clean_valid_rate), hint: 'clean / raw' },
  { label: '今日任务成功率', value: percent(overview.value.today_task_success_rate), hint: 'offline jobs' },
  { label: '最近失败任务', value: overview.value.recent_failed_task || '-', hint: 'failed job' },
  { label: '质量合规率', value: percent(qualityOverview.value.avg_pass_rate), hint: 'average pass rate' }
])

function todayString() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function disableFutureBizDate(current) {
  if (!current) return false
  const value = current instanceof Date ? current : new Date(current)
  const selected = new Date(value.getFullYear(), value.getMonth(), value.getDate()).getTime()
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime()
  return selected > today
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

function percent2(value) {
  return `${(Number(value || 0) * 100).toFixed(2)}%`
}

function formatTrendDate(value) {
  return String(value || '').slice(5, 10) || value
}

function formatDateTime(value) {
  if (!value) return '-'
  return String(value).replace('T', ' ').slice(0, 19)
}

function nodeName(id) {
  return lineage.value.nodes?.find((node) => node.id === id)?.name || id
}

function showJson(value, title = 'JSON 详情') {
  jsonPreview.value = JSON.stringify(value, null, 2)
  jsonModalTitle.value = title
  jsonModalOpen.value = true
}

async function showLogs(runId) {
  const data = await fetchAdminJobLogs(runId)
  showJson(data)
}

function compactParams(params) {
  return Object.fromEntries(
    Object.entries(params)
      .map(([key, value]) => {
        if (typeof value !== 'string') return [key, value]
        const trimmed = value.trim()
        if (key.endsWith('_date')) return [key, trimmed.replace(/\//g, '-')]
        return [key, key === 'event_id' ? trimmed.replace(/\s+/g, '_') : trimmed]
      })
      .filter(([, value]) => value !== '')
  )
}

function normalizeDateValue(value) {
  if (!value) return ''
  if (typeof value === 'string') return value.trim().replace(/\//g, '-')
  if (value instanceof Date) {
    return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}-${String(value.getDate()).padStart(2, '0')}`
  }
  return String(value).trim().replace(/\//g, '-')
}

function setDwsDate(field, value) {
  dwsFilters.value[field] = normalizeDateValue(value)
}

function beginLoading() {
  activeLoadCount += 1
  loading.value = true
}

function endLoading() {
  activeLoadCount = Math.max(0, activeLoadCount - 1)
  loading.value = activeLoadCount > 0
}

function cachedRequest(key, fetcher, options = {}) {
  const force = options.force === true
  const ttl = options.ttl ?? CACHE_TTL_MS
  const entry = requestCache.get(key)
  const currentTime = Date.now()

  if (entry?.pending) return entry.pending
  if (!force && entry && currentTime - entry.time < ttl) {
    return Promise.resolve(entry.data)
  }

  const pending = Promise.resolve()
    .then(fetcher)
    .then((data) => {
      requestCache.set(key, { data, time: Date.now() })
      return data
    })
    .finally(() => {
      const latest = requestCache.get(key)
      if (latest?.pending === pending) {
        delete latest.pending
      }
    })

  requestCache.set(key, {
    data: entry?.data,
    time: entry?.time || 0,
    pending
  })
  return pending
}

function invalidateAdminCache(prefixes = []) {
  for (const key of requestCache.keys()) {
    if (prefixes.some((prefix) => key.startsWith(prefix))) {
      requestCache.delete(key)
    }
  }
}

function applySettled(result, apply, label) {
  if (result.status === 'fulfilled') {
    apply(result.value)
    return true
  }
  console.warn(`Failed to refresh ${label}`, result.reason)
  if (hasLoaded.value) {
    Message.warning({ content: `${label} 刷新失败，已保留旧数据`, duration: 3000 })
  }
  return false
}

async function runModuleLoad(moduleKey, loader, options = {}) {
  if (moduleRequests.has(moduleKey)) return moduleRequests.get(moduleKey)
  error.value = ''
  isEmpty.value = false
  let didSucceed = false
  beginLoading()

  const request = Promise.resolve()
    .then(loader)
    .then(() => {
      didSucceed = true
      hasLoaded.value = true
    })
    .catch((err) => {
      console.error(`Failed to load ${moduleKey}`, err)
      if (!hasLoaded.value) {
        error.value = err.message || '网络连接或后端服务异常'
      } else {
        Message.warning({ content: '刷新失败，已保留当前数据', duration: 3000 })
      }
    })
    .finally(async () => {
      moduleRequests.delete(moduleKey)
      endLoading()
      if (options.render !== false) {
        if (didSucceed && options.replayOverview === true) {
          await nextTick()
          overviewChartRenderKey.value += 1
          if (import.meta.env.DEV) {
            console.log('[data-overview] replay chart animation', overviewChartRenderKey.value)
          }
          await nextTick()
        }
        await scheduleVisibleChartRender({ replayOverview: didSucceed && options.replayOverview === true })
      }
    })

  moduleRequests.set(moduleKey, request)
  return request
}

async function loadEvents(options = {}) {
  const force = options.force !== false
  const params = compactParams(eventFilters.value)
  try {
    events.value = await cachedRequest(`admin:events:${JSON.stringify(params)}`, () => fetchAdminEvents(params), { force })
  } catch (err) {
    Message.error({ content: `ODS 查询失败: ${err.message || err}`, duration: 5000 })
  }
}

async function loadLayerData(options = {}) {
  const force = options.force !== false
  if (selectedLayer.value === 'ods') {
    await loadEvents({ force })
    return
  }
  if (selectedLayer.value === 'dwd') {
    const params = { limit: 50, ...compactParams(dwdFilters.value) }
    try {
      dwdEvents.value = await cachedRequest(`admin:dwd-events:${JSON.stringify(params)}`, () => fetchDwdEvents(params), { force })
    } catch (err) {
      Message.error({ content: `DWD 查询失败: ${err.message || err}`, duration: 5000 })
    }
    return
  }
  if (selectedLayer.value === 'dws') {
    const dwsParams = compactParams({
      start_date: normalizeDateValue(dwsFilters.value.start_date),
      end_date: normalizeDateValue(dwsFilters.value.end_date)
    })
    if (dwsParams.start_date && dwsParams.end_date && dwsParams.start_date > dwsParams.end_date) {
      Message.warning({ content: '开始日期不能晚于结束日期', duration: 3000 })
      return
    }
    const params = { limit: 50, ...dwsParams }
    try {
      dwsMetrics.value = await cachedRequest(`admin:dws-metrics:${JSON.stringify(params)}`, () => fetchDwsMetrics(params), { force })
    } catch (err) {
      Message.error({ content: `DWS 查询失败: ${err.message || err}`, duration: 5000 })
    }
    return
  }
  if (selectedLayer.value === 'ads') {
    if (adsSelectedTable.value === 'error_distribution') {
      const adsParams = compactParams({
        start_date: normalizeDateValue(adsFilters.value.start_date),
        end_date: normalizeDateValue(adsFilters.value.end_date)
      })
      if (adsParams.start_date && adsParams.end_date && adsParams.start_date > adsParams.end_date) {
        Message.warning({ content: '开始日期不能晚于结束日期', duration: 3000 })
        return
      }
      const params = { limit: 50, ...adsParams }
      try {
        const res = await cachedRequest(`analytics:errors:${JSON.stringify(params)}`, () => fetchAnalyticsErrors(params), { force })
        adsDataList.value = (res && Array.isArray(res.data) ? res.data : (Array.isArray(res) ? res : []))
      } catch (err) {
        Message.error({ content: `ADS 异常分布查询失败: ${err.message || err}`, duration: 5000 })
      }
    } else if (adsSelectedTable.value === 'historical_alerts') {
      const queryDate = adsFilters.value.end_date || adsFilters.value.start_date || todayString()
      try {
        const res = await cachedRequest(`alerts:history:${queryDate}`, () => fetchHistoryAlerts(queryDate), { force })
        adsDataList.value = (res && Array.isArray(res.data) ? res.data : (Array.isArray(res) ? res : []))
      } catch (err) {
        Message.error({ content: `ADS 历史告警查询失败: ${err.message || err}`, duration: 5000 })
      }
    }
  }
}

async function handleLayerChange() {
  await loadLayerData()
}

const warehouseDataPanelRef = ref(null)

function selectLayer(layer) {
  selectedLayer.value = layer
  loadLayerData({ force: false })
}

async function loadRules(options = {}) {
  const force = options.force === true
  try {
    qualityRules.value = await cachedRequest('admin:quality-rules', fetchQualityRules, { force, ttl: 10000 })
  } catch (e) {
    console.error('Failed to load quality rules', e)
  }
}



async function toggleRule(rule) {
  try {
    const newStatus = rule.is_active ? 0 : 1
    await updateQualityRule(rule.rule_id, { is_active: newStatus })
    Message.success(`${rule.rule_name}已${newStatus ? '启用' : '禁用'}`)
    invalidateAdminCache(['admin:quality-rules'])
    await loadRules({ force: true })
  } catch (e) {
    Message.error('修改规则状态失败')
  }
}

function invalidateOverviewCache() {
  invalidateAdminCache([
    'admin:data-overview',
    'admin:data-volume-trend',
    'admin:pipeline-status',
    'admin:quality-overview',
    'admin:quality-issues',
    'admin:datasets',
    'admin:data-lineage',
    'admin:dws-metrics',
    'analytics:'
  ])
  overviewDirty.value = true
}

async function refreshOverviewAfterJob() {
  invalidateOverviewCache()
  await wait(800)
  if (activeTab.value === 'overview') {
    overviewDirty.value = false
    await loadOverviewData({ force: true })
  }
}

async function recleanData(dateVal) {
  if (!dateVal) return
  recleaning.value[dateVal] = true
  Message.info({ content: `正在触发数据清洗自愈任务，业务日期: ${dateVal}...`, duration: 3000 })
  try {
    await executeAdminJob('spark_clean', dateVal)
    Message.success({ content: `业务日期 ${dateVal} 的清洗自愈执行成功！`, duration: 4000 })
    await refreshOverviewAfterJob()
    if (activeTab.value === 'assets') {
      await loadLayerData({ force: true })
    }
  } catch (e) {
    Message.error({ content: `重洗自愈执行失败: ${e.message || '未知错误'}`, duration: 4000 })
  } finally {
    recleaning.value[dateVal] = false
  }
}




async function loadJobs(options = {}) {
  const force = options.force === true
  const [jobData, runData] = await Promise.allSettled([
    cachedRequest('admin:jobs', fetchAdminJobs, { force, ttl: 10000 }),
    cachedRequest('admin:job-runs', fetchAdminJobRuns, { force, ttl: 5000 })
  ])
  applySettled(jobData, (data) => { jobs.value = data || [] }, 'jobs')
  applySettled(runData, (data) => { jobRuns.value = data || [] }, 'job-runs')
}

async function runJob(jobCode) {
  runningJobs.value[jobCode] = true
  Message.info({ content: `正在调度执行作业: ${jobCode}...`, duration: 3000 })

  try {
    const payload = jobCode === 'offline_generate'
      ? { count: Number(generateCount.value || 50) }
      : {}
    const res = await executeAdminJob(jobCode, bizDate.value, payload)
    if (res.status === 'failed') {
      Message.error({ content: `作业 ${jobCode} 运行失败，请在下方列表查看详细日志！`, duration: 6000 })
    } else {
      Message.success({ content: `作业 ${jobCode} 执行成功！`, duration: 4000 })
    }
  } catch (err) {
    Message.error({ content: `作业调度系统异常: ${err.message || err}`, duration: 5000 })
  } finally {
    runningJobs.value[jobCode] = false
    invalidateAdminCache(['admin:jobs', 'admin:job-runs'])
    await loadJobsData({ force: true })
    await refreshOverviewAfterJob()
  }
}

async function runFullPipeline() {
  pipelineRunning.value = true
  Message.info({ content: '离线流水线已启动，各阶段任务正按顺序流式调度...', duration: 4000 })
  try {
    let failed = false
    for (const job of jobs.value) {
      if (job.job_code === 'offline_generate' && pipelineGenerateMode.value === 'skip') {
        Message.info({ content: '一键链路已跳过模拟数据生成，直接处理当前 Source 数据。', duration: 3000 })
        continue
      }
      runningJobs.value[job.job_code] = true
      Message.info({ content: `正在执行：${job.job_name}...`, duration: 2500 })

      try {
        const payload = job.job_code === 'offline_generate'
          ? { count: Number(generateCount.value || 50) }
          : {}
        const res = await executeAdminJob(job.job_code, bizDate.value, payload)
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
        invalidateAdminCache(['admin:jobs', 'admin:job-runs'])
        await loadJobs({ force: true }) // refresh intermediate runs live
      }
    }
    if (!failed) {
      Message.success({ content: '一键离线计算流水线全段运行成功！', duration: 5000 })
    }
  } catch (err) {
    Message.error({ content: `流水线运行系统异常: ${err.message || err}` })
  } finally {
    pipelineRunning.value = false
    invalidateAdminCache(['admin:jobs', 'admin:job-runs'])
    await loadJobsData({ force: true })
    await refreshOverviewAfterJob()
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
    invalidateAdminCache(['admin:jobs', 'admin:job-runs'])
    await loadJobsData({ force: true })
    await refreshOverviewAfterJob()
  }
}

function renderFunnel(options = {}) {
  try {
    if (!funnelChartRef.value) return
    if (!funnelChart || funnelChart.getDom?.() !== funnelChartRef.value) {
      funnelChart?.dispose()
      funnelChart = echarts.init(funnelChartRef.value)
    }
    if (options.replay) funnelChart.clear()

    const rawFunnel = Array.isArray(overview.value.funnel) && overview.value.funnel.length
      ? overview.value.funnel
      : [
          { name: 'Source', count: overview.value.source_total_count || 0 },
          { name: 'Raw', count: overview.value.raw_count || overview.value.source_total_count || 0 },
          { name: 'Clean', count: overview.value.clean_count || 0 },
          { name: 'Metric', count: overview.value.metric_count || overview.value.metric_partition_count || 0 }
        ]
    const visualScales = [100, 80, 60, 40]
    const funnelData = rawFunnel.map((item, idx) => ({
      name: item.name,
      value: visualScales[idx] || 30,
      realValue: item.count
    }))

    funnelChart.setOption({
      backgroundColor: 'transparent',
      animation: true,
      animationDuration: 1200,
      animationDurationUpdate: 1200,
      animationEasing: 'cubicOut',
      animationEasingUpdate: 'cubicOut',
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
          animation: true,
          animationDuration: 1200,
          animationDurationUpdate: 1200,
          animationEasing: 'cubicOut',
          animationDelay: (idx) => idx * 80,
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
          labelLine: { show: false },
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
    funnelChart.resize()
  } catch (err) {
    console.error('Failed to render funnel chart', err)
  }
}

function renderLineage() {
  try {
    if (!lineageChartRef.value) return
    if (!lineageChart || lineageChart.getDom?.() !== lineageChartRef.value) {
      lineageChart?.dispose()
      lineageChart = echarts.init(lineageChartRef.value)
    }

    const sourceLineage = Array.isArray(lineage.value.nodes) && lineage.value.nodes.length
      ? lineage.value
      : defaultLineage
    const nodes = (sourceLineage.nodes || []).map(n => ({
      id: n.id,
      name: n.name,
      value: n.name,
      symbolSize: 22,
      itemStyle: {
        color: String(n.id || '').includes('mysql') ? '#3b82f6' : '#22d3ee',
        shadowBlur: 10,
        shadowColor: 'rgba(34, 211, 238, 0.4)'
      }
    }))

    const links = (sourceLineage.edges || []).map(e => ({
      source: e.from,
      target: e.to,
      value: e.label,
      label: {
        show: true,
        position: 'middle',
        color: '#c5f5ff',
        fontSize: 10,
        formatter: (params) => params.data?.value || ''
      },
      lineStyle: {
        color: 'rgba(103, 232, 249, 0.55)',
        curveness: 0.16,
        width: 1.8
      }
    }))

    lineageChart.setOption({
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'item',
        formatter: (params) => {
          if (params.dataType === 'node') {
            return `数据层: <b>${params.name}</b>`
          }
          return `血缘流动: <b>${params.data.source} ➔ ${params.data.target}</b>${params.data.value ? ` (${params.data.value})` : ''}`
        }
      },
      series: [
        {
          type: 'graph',
          layout: 'force',
          top: 24,
          right: 28,
          bottom: 30,
          left: 28,
          force: {
            repulsion: 360,
            edgeLength: [170, 240],
            gravity: 0.035
          },
          roam: true,
          draggable: true,
          symbol: 'circle',
          edgeSymbol: ['none', 'arrow'],
          edgeSymbolSize: [4, 9],
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
    lineageChart.resize()
  } catch (err) {
    console.error('Failed to render lineage chart', err)
  }
}

function renderTrend(options = {}) {
  try {
    if (!trendChartRef.value) return
    if (!trendChart || trendChart.getDom?.() !== trendChartRef.value) {
      trendChart?.dispose()
      trendChart = echarts.init(trendChartRef.value)
    }
    if (options.replay) trendChart.clear()
    const sourceTrend = Array.isArray(trend.value) && trend.value.length ? trend.value : getDefaultTrend()
    const option = lineOption('Raw / Clean 数据量趋势', sourceTrend.map((item) => formatTrendDate(item.biz_date)), [
      { name: 'Raw', type: 'line', smooth: true, showSymbol: false, animation: true, animationDuration: 1200, animationDurationUpdate: 1200, animationEasing: 'cubicOut', animationDelay: (idx) => idx * 80, data: sourceTrend.map((item) => Number(item.raw_count || 0)), itemStyle: { color: '#22d3ee' }, areaStyle: { color: 'rgba(34, 211, 238, 0.1)' } },
      { name: 'Clean', type: 'line', smooth: true, showSymbol: false, animation: true, animationDuration: 1200, animationDurationUpdate: 1200, animationEasing: 'cubicOut', animationDelay: (idx) => idx * 80, data: sourceTrend.map((item) => Number(item.clean_count || 0)), itemStyle: { color: '#4ade80' }, areaStyle: { color: 'rgba(74, 222, 128, 0.08)' } }
    ])
    option.animation = true
    option.animationDuration = 1200
    option.animationDurationUpdate = 1200
    option.animationEasing = 'cubicOut'
    option.animationEasingUpdate = 'cubicOut'
    option.grid = { ...option.grid, right: 42, bottom: 30, containLabel: true }
    option.xAxis = { ...option.xAxis, boundaryGap: true }
    trendChart.setOption(option, true)
    trendChart.resize()
  } catch (err) {
    console.error('Failed to render trend chart', err)
  }
}

function renderStorageChart() {
  try {
    if (!storageChartRef.value) return
    if (!storageChart || storageChart.getDom?.() !== storageChartRef.value) {
      storageChart?.dispose()
      storageChart = echarts.init(storageChartRef.value)
    }
    const hdfs = overview.value.hdfs_storage || defaultHdfsStorage
    const usedBytes = Number(hdfs.used_bytes || 0)
    const limitBytes = Number(hdfs.limit_bytes || defaultHdfsStorage.limit_bytes || 1)
    const percentVal = limitBytes > 0 ? ((usedBytes / limitBytes) * 100).toFixed(1) : 0
    storageChart.setOption({
      series: [{
        type: 'gauge',
        startAngle: 90,
        endAngle: -270,
        pointer: { show: false },
        progress: { show: true, roundCap: true, itemStyle: { color: '#22d3ee' } },
        axisLine: { lineStyle: { width: 10, color: [['1', 'rgba(34, 211, 238, 0.1)']] } },
        splitLine: { show: false },
        axisTick: { show: false },
        axisLabel: { show: false },
        data: [{ value: percentVal, name: '已用空间' }],
        detail: { fontSize: 18, color: '#f8fafc', formatter: '{value}%', offsetCenter: [0, 0] }
      }]
    }, true)
    storageChart.resize()
  } catch (err) {
    console.error('Failed to render storage chart', err)
  }
}

function renderPerfChart() {
  try {
    if (!perfChartRef.value) return
    if (!perfChart || perfChart.getDom?.() !== perfChartRef.value) {
      perfChart?.dispose()
      perfChart = echarts.init(perfChartRef.value)
    }
    const rawPerfData = Array.isArray(overview.value.compute_perf) && overview.value.compute_perf.length
      ? overview.value.compute_perf
      : defaultComputePerf
    const perfData = rawPerfData.map((item) => ({
      job_name: item.job_name || item.name || item.job_code || '-',
      duration: Number(item.duration ?? item.duration_seconds ?? item.value ?? 0)
    }))
    perfChart.setOption({
      grid: { left: '3%', right: '10%', bottom: '3%', top: '5%', containLabel: true },
      xAxis: { type: 'value', splitLine: { show: false }, axisLabel: { color: '#64748b' } },
      yAxis: { type: 'category', data: perfData.map(item => item.job_name), axisLabel: { color: '#cbd5e1', fontSize: 11 } },
      series: [{
        name: '运行时长',
        type: 'bar',
        data: perfData.map(item => item.duration),
        itemStyle: {
          borderRadius: 4,
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: '#0891b2' },
            { offset: 1, color: '#22d3ee' }
          ])
        },
        label: { show: true, position: 'right', color: '#67e8f9' }
      }]
    }, true)
    perfChart.resize()
  } catch (err) {
    console.error('Failed to render performance chart', err)
  }
}

function getDefaultTrend() {
  const days = []
  const now = new Date()
  for (let index = 6; index >= 0; index -= 1) {
    const day = new Date(now)
    day.setDate(now.getDate() - index)
    days.push({
      biz_date: `${day.getFullYear()}-${String(day.getMonth() + 1).padStart(2, '0')}-${String(day.getDate()).padStart(2, '0')}`,
      raw_count: 0,
      clean_count: 0
    })
  }
  return days
}

function resizeCharts() {
  trendChart?.resize()
  funnelChart?.resize()
  lineageChart?.resize()
  storageChart?.resize()
  perfChart?.resize()
}

function waitForFrame() {
  return new Promise((resolve) => requestAnimationFrame(() => resolve()))
}

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

async function ensureChartContainer(elRef, attempts = 8) {
  for (let i = 0; i < attempts; i += 1) {
    const el = elRef.value
    if (el && el.clientWidth > 0 && el.clientHeight > 0) return el
    await wait(80)
    await waitForFrame()
  }
  return elRef.value
}

function renderAllVisibleCharts(options = {}) {
  if (activeTab.value === 'overview') {
    renderTrend({ replay: options.replayOverview })
    renderFunnel({ replay: options.replayOverview })
    renderStorageChart()
    renderPerfChart()
  }
  if (activeTab.value === 'assets') {
    renderLineage()
  }
}

async function scheduleVisibleChartRender(options = {}) {
  await nextTick()
  await ensureChartContainer(activeTab.value === 'overview' ? trendChartRef : lineageChartRef)
  renderAllVisibleCharts(options)
  await waitForFrame()
  resizeCharts()
}

async function loadOverviewData(options = {}) {
  const force = options.force === true
  const replay = options.replay === true
  return runModuleLoad('overview', async () => {
    const results = await Promise.allSettled([
      cachedRequest('admin:data-overview', fetchAdminOverview, { force }),
      cachedRequest('admin:data-volume-trend', fetchDataVolumeTrend, { force }),
      cachedRequest('admin:pipeline-status', fetchPipelineStatus, { force }),
      cachedRequest('admin:quality-overview', fetchQualityOverview, { force }),
      cachedRequest('admin:quality-issues', fetchQualityIssues, { force })
    ])

    const successCount = [
      applySettled(results[0], (data) => { overview.value = data || {} }, 'data-overview'),
      applySettled(results[1], (data) => { trend.value = data || [] }, 'data-volume-trend'),
      applySettled(results[2], (data) => { pipeline.value = data || { nodes: [], edges: [] } }, 'pipeline-status'),
      applySettled(results[3], (data) => { qualityOverview.value = data || { rule_count: 0, issue_count: 0, avg_pass_rate: 1.0, pending_count: 0 } }, 'quality-overview'),
      applySettled(results[4], (data) => { qualityIssues.value = data || [] }, 'quality-issues')
    ].filter(Boolean).length

    if (successCount === 0 && !hasLoaded.value) {
      throw new Error('数据总览接口暂不可用')
    }
  }, { replayOverview: replay })
}

async function loadAssetsData(options = {}) {
  const force = options.force === true
  return runModuleLoad('assets', async () => {
    const results = await Promise.allSettled([
      cachedRequest('admin:datasets', fetchDatasets, { force, ttl: 10000 }),
      cachedRequest('admin:data-lineage', fetchDataLineage, { force, ttl: 10000 }),
      cachedRequest('admin:quality-overview', fetchQualityOverview, { force })
    ])

    applySettled(results[0], (data) => { datasets.value = data || [] }, 'datasets')
    applySettled(results[1], (data) => { lineage.value = data || { nodes: [], edges: [] } }, 'data-lineage')
    applySettled(results[2], (data) => { qualityOverview.value = data || { rule_count: 0, issue_count: 0, avg_pass_rate: 1.0, pending_count: 0 } }, 'quality-overview')
    await loadLayerData({ force })
  })
}

async function loadJobsData(options = {}) {
  const force = options.force === true
  return runModuleLoad('jobs', async () => {
    await Promise.allSettled([
      loadJobs({ force }),
      loadRules({ force })
    ])
  }, { render: false })
}

async function loadAll(options = {}) {
  const force = options?.force === true
  if (loading.value && moduleRequests.has(activeTab.value)) return moduleRequests.get(activeTab.value)

  if (activeTab.value === 'overview') {
    const shouldForce = force || overviewDirty.value
    overviewDirty.value = false
    return loadOverviewData({ force: shouldForce, replay: force })
  }
  if (activeTab.value === 'assets') return loadAssetsData({ force })
  if (activeTab.value === 'jobs') return loadJobsData({ force })
  return Promise.resolve()
}

onMounted(async () => {
  await loadAll()
  window.addEventListener('resize', resizeCharts)
})

watch(activeTab, async (tab) => {
  if (tab === 'overview' && overviewDirty.value) {
    overviewDirty.value = false
    await loadOverviewData({ force: true })
    return
  }
  await loadAll()
  await scheduleVisibleChartRender()
}, { flush: 'post' })

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCharts)
  trendChart?.dispose()
  funnelChart?.dispose()
  lineageChart?.dispose()
  storageChart?.dispose()
  perfChart?.dispose()
})
</script>
