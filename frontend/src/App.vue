<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="brand">
        <Activity :size="22" />
        <span>AgentScope</span>
      </div>
      <nav>
        <RouterLink v-for="item in navItems" :key="item.path" :to="item.path">
          <component :is="item.icon" :size="18" />
          <span>{{ item.label }}</span>
        </RouterLink>
      </nav>
    </aside>

    <main class="main">
      <header class="topbar">
        <div>
          <p class="eyebrow">多智能体运行监测与效能分析平台</p>
          <h1>{{ route.meta.title }}</h1>
        </div>
        <div class="cluster-pill">
          <Server :size="16" />
          <span>实时 - 离线双链路</span>
        </div>
      </header>
      <RouterView />
    </main>
  </div>
</template>

<script setup>
import { useRoute } from 'vue-router'
import { Activity, AlertTriangle, BarChart3, Bot, FileText, GitBranch, LayoutDashboard, Server } from '@lucide/vue'

const route = useRoute()
const navItems = [
  { path: '/overview', label: '系统总览', icon: LayoutDashboard },
  { path: '/agents', label: 'Agent 监控', icon: Bot },
  { path: '/history', label: '历史分析', icon: BarChart3 },
  { path: '/relations', label: '协作关系', icon: GitBranch },
  { path: '/alerts', label: '告警中心', icon: AlertTriangle },
  { path: '/reports', label: 'AI 报告', icon: FileText }
]
</script>
