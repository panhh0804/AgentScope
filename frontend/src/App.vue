<template>
  <div class="app-shell">
    <header class="site-header">
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
import { Activity, Database, FileText, LayoutDashboard, Server } from '@lucide/vue'

const route = useRoute()
const navItems = [
  { path: '/overview', label: '系统总览', icon: LayoutDashboard },
  { path: '/data-admin', label: '数据管理', icon: Database },
  { path: '/reports', label: 'AI 报告', icon: FileText }
]
</script>
