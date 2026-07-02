import { createRouter, createWebHistory } from 'vue-router'
import OverviewView from '../views/OverviewView.vue'
import ReportsView from '../views/ReportsView.vue'
import DataAdminView from '../views/DataAdminView.vue'
import StatisticsView from '../views/StatisticsView.vue'

const routes = [
  { path: '/', redirect: '/data-admin' },
  { path: '/overview', component: OverviewView, meta: { title: '系统总览' } },
  { path: '/data-admin', component: DataAdminView, meta: { title: '数据管理' } },
  { path: '/statistics', component: StatisticsView, meta: { title: '数据统计' } },
  { path: '/reports', component: ReportsView, meta: { title: 'AI 报告' } }
]

export default createRouter({
  history: createWebHistory(),
  routes
})
