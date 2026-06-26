import { createRouter, createWebHistory } from 'vue-router'
import OverviewView from '../views/OverviewView.vue'
import RelationView from '../views/RelationView.vue'
import AlertsView from '../views/AlertsView.vue'
import ReportsView from '../views/ReportsView.vue'

const routes = [
  { path: '/', redirect: '/overview' },
  { path: '/overview', component: OverviewView, meta: { title: '系统总览' } },
  { path: '/relations', component: RelationView, meta: { title: '协作关系' } },
  { path: '/alerts', component: AlertsView, meta: { title: '告警中心' } },
  { path: '/reports', component: ReportsView, meta: { title: 'AI 报告' } }
]

export default createRouter({
  history: createWebHistory(),
  routes
})
