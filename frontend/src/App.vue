<template>
  <div class="app-shell">
    <header v-if="route.path !== '/overview'" class="site-header">
      <div class="brand">
        <Activity :size="20" />
        <div>
          <strong>AgentScope</strong>
          <span>多智能体运行监测与效能分析平台</span>
        </div>
      </div>

      <nav class="nav-tabs" aria-label="Main navigation">
        <RouterLink v-for="item in navItems" :key="item.path" :to="item.path" class="nav-link">
          <component :is="item.icon" :size="16" />
          <span>{{ item.label }}</span>
        </RouterLink>
        <a href="/overview" target="_blank" class="nav-link nav-link--screen" style="color: #22d3ee; border-color: rgba(34, 211, 238, 0.35);">
          <LayoutDashboard :size="16" />
          <span>实时大屏 ↗</span>
        </a>
      </nav>

      <div class="cluster-pill">
        <Server :size="16" />
        <span>{{ route.meta.title || '实时 - 离线双链路' }}</span>
      </div>
    </header>

    <main :class="['main', { 'main--overview': route.path === '/overview', 'main--content': route.path !== '/overview' }]">
      <RouterView />
    </main>
  </div>
</template>

<script setup>
import { useRoute } from 'vue-router'
import { Activity, BarChart2, Database, FileText, LayoutDashboard, Server } from '@lucide/vue'

const route = useRoute()
const navItems = [
  { path: '/data-admin', label: '数据管理', icon: Database },
  { path: '/statistics', label: '数据统计', icon: BarChart2 },
  { path: '/reports', label: 'AI 报告', icon: FileText }
]
</script>
