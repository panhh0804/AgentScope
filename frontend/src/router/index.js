import { createRouter, createWebHistory } from 'vue-router'
import OverviewView from '../views/OverviewView.vue'
import ReportsView from '../views/ReportsView.vue'
import DataAdminView from '../views/DataAdminView.vue'
import StatisticsView from '../views/StatisticsView.vue'
import SystemAdminView from '../views/SystemAdminView.vue'

const routes = [
  { path: '/', redirect: '/data-overview' },
  { path: '/overview', component: OverviewView, meta: { title: '系统总览' } },
  { path: '/data-overview', component: DataAdminView, meta: { title: '数据总览' } },
  { path: '/data-assets', component: DataAdminView, meta: { title: '数据资产' } },
  { path: '/data-jobs', component: DataAdminView, meta: { title: '数据任务' } },
  { path: '/statistics', component: StatisticsView, meta: { title: '数据统计' } },
  { path: '/reports', component: ReportsView, meta: { title: 'AI 报告' } },
  { path: '/system-admin', component: SystemAdminView, meta: { title: '系统管理' } }
]

export default createRouter({
  history: createWebHistory(),
  routes
})
