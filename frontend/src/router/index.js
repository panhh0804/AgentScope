import { createRouter, createWebHistory } from 'vue-router'
import OverviewView from '../views/OverviewView.vue'
import ReportsView from '../views/ReportsView.vue'

const routes = [
  { path: '/', redirect: '/overview' },
  { path: '/overview', component: OverviewView, meta: { title: '系统总览' } },
  { path: '/reports', component: ReportsView, meta: { title: 'AI 报告' } }
]

export default createRouter({
  history: createWebHistory(),
  routes
})
