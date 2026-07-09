<template>
  <div>
    <div class="page-actions">
      <h1 class="page-title" style="margin-bottom: 0">Agent 管理</h1>
      <router-link to="/agents/new" class="btn btn-primary">+ 创建 Agent</router-link>
    </div>
    <p class="page-subtitle">管理 AI Agent 的定义和配置</p>

    <table class="data-table">
      <thead>
        <tr>
          <th>ID</th>
          <th>名称</th>
          <th>模型</th>
          <th>工具</th>
          <th>状态</th>
          <th>创建时间</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="agent in agents" :key="agent.id">
          <td>{{ agent.id }}</td>
          <td><strong>{{ agent.name }}</strong></td>
          <td><code>{{ agent.model_name }}</code></td>
          <td>{{ (agent.tools || []).join(', ') || '-' }}</td>
          <td><span :class="['badge', agent.status === 'active' ? 'badge-active' : 'badge-archived']">{{ agent.status }}</span></td>
          <td style="color: #999; font-size: 0.85rem">{{ formatDate(agent.created_at) }}</td>
          <td>
            <router-link :to="`/agents/${agent.id}/edit`" class="btn btn-outline btn-sm">编辑</router-link>
            <button @click="deleteAgent(agent.id)" class="btn btn-danger btn-sm">归档</button>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-if="agents.length === 0" style="text-align: center; color: #999; padding: 2rem">暂无 Agent 定义，点击上方按钮创建</p>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const agents = ref([])

onMounted(fetchAgents)
async function fetchAgents() {
  try {
    const res = await fetch('/api/v1/admin/agents')
    const data = await res.json()
    agents.value = data.agents || []
  } catch { agents.value = [] }
}

async function deleteAgent(id) {
  if (!confirm('确认归档此 Agent？')) return
  await fetch(`/api/v1/admin/agents/${id}`, { method: 'DELETE' })
  await fetchAgents()
}

function formatDate(d) {
  if (!d) return '-'
  return new Date(d).toLocaleString('zh-CN')
}
</script>
