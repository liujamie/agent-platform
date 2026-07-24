<template>
  <div>
    <h1 class="page-title">Dashboard</h1>
    <p class="page-subtitle">Agent Platform 运行状态概览</p>

    <div class="grid-4">
      <div class="card">
        <div class="card-title">Agent 数量</div>
        <div class="card-value">{{ stats.agent_count }}</div>
      </div>
      <div class="card">
        <div class="card-title">Workflow 数量</div>
        <div class="card-value">{{ stats.workflow_count }}</div>
      </div>
      <div class="card">
        <div class="card-title">运行记录</div>
        <div class="card-value">{{ stats.log_count }}</div>
      </div>
      <div class="card">
        <div class="card-title">已注册工具</div>
        <div class="card-value">{{ groupedToolCount }}</div>
      </div>
    </div>

    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem">
      <div class="card">
        <h3 style="margin-bottom: 0.75rem">已注册工具</h3>
        <div v-for="g in toolGroups" :key="g.label" style="margin-bottom: 0.75rem">
          <div style="font-size: 0.8rem; color: #999; text-transform: uppercase; margin-bottom: 0.3rem">{{ g.label }}</div>
          <div v-for="t in g.items" :key="t.name" style="padding: 0.4rem 0; border-bottom: 1px solid #eee">
            <strong>{{ t.name }}</strong>
            <span v-if="t.count" class="badge badge-active" style="margin-left: 0.5rem; font-size: 0.75rem">{{ t.count }} 个工具</span>
            <p v-if="t.description" style="color: #666; font-size: 0.85rem">{{ t.description }}</p>
          </div>
        </div>
        <p v-if="tools.length === 0" style="color: #999; font-size: 0.9rem">暂无已注册工具</p>
      </div>

      <div class="card">
        <h3 style="margin-bottom: 0.75rem">最近运行记录</h3>
        <div v-for="log in recentLogs" :key="log.id" style="padding: 0.4rem 0; border-bottom: 1px solid #eee; font-size: 0.85rem">
          <span :class="['badge', log.status === 'success' ? 'badge-success' : 'badge-error']">{{ log.status }}</span>
          <span style="margin-left: 0.5rem; color: #666">{{ log.trace_id?.slice(0, 8) }}...</span>
          <span style="float: right; color: #999">{{ log.duration_ms }}ms</span>
        </div>
        <p v-if="recentLogs.length === 0" style="color: #999; font-size: 0.9rem; margin-top: 0.5rem">No logs yet</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const stats = ref({ agent_count: 0, workflow_count: 0, log_count: 0 })
const tools = ref([])
const recentLogs = ref([])

const toolGroups = computed(() => {
  const groups = {}
  for (const t of tools.value) {
    const key = t.source && t.source !== 'built-in' ? `MCP: ${t.source}` : '内置工具'
    if (!groups[key]) groups[key] = { label: key, items: [] }
    groups[key].items.push(t)
  }
  // Merge MCP tools into a single entry per connection
  const result = []
  for (const [label, group] of Object.entries(groups)) {
    if (label === '内置工具') {
      result.push({ label, items: group.items })
    } else {
      const connName = label.replace('MCP: ', '')
      result.push({ label, items: [{ name: connName, description: `MCP: ${group.items.length} 个工具`, count: group.items.length }] })
    }
  }
  return result
})

const groupedToolCount = computed(() =>
  toolGroups.value.reduce((sum, g) => sum + g.items.length, 0)
)

onMounted(async () => {
  try {
    const [statsRes, toolRes, logRes] = await Promise.all([
      fetch('/api/v1/admin/stats').then(r => r.json()),
      fetch('/api/v1/tool/list').then(r => r.json()),
      fetch('/api/v1/admin/logs?page_size=5').then(r => r.json()),
    ])
    stats.value = statsRes
    tools.value = toolRes.tools || []
    recentLogs.value = logRes.logs || []
  } catch { /* graceful */ }
})
</script>
