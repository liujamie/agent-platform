<template>
  <div>
    <div class="page-actions">
      <h1 class="page-title" style="margin-bottom: 0">Workflow 管理</h1>
      <router-link to="/workflows/new" class="btn btn-primary">+ 创建 Workflow</router-link>
    </div>
    <p class="page-subtitle">编排多 Agent 协作流程</p>

    <table class="data-table">
      <thead>
        <tr>
          <th>ID</th>
          <th>名称</th>
          <th>节点数</th>
          <th>状态</th>
          <th>创建时间</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="wf in workflows" :key="wf.id">
          <td>{{ wf.id }}</td>
          <td><strong>{{ wf.name }}</strong></td>
          <td>{{ wf.definition?.nodes?.length || 0 }}</td>
          <td><span :class="['badge', wf.status === 'active' ? 'badge-active' : 'badge-archived']">{{ wf.status }}</span></td>
          <td style="color: #999; font-size: 0.85rem">{{ formatDate(wf.created_at) }}</td>
          <td>
            <router-link :to="`/workflows/${wf.id}/edit`" class="btn btn-outline btn-sm">编辑</router-link>
            <button @click="runWorkflow(wf)" class="btn btn-primary btn-sm">运行</button>
            <button @click="deleteWorkflow(wf.id)" class="btn btn-danger btn-sm">归档</button>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-if="workflows.length === 0" style="text-align: center; color: #999; padding: 2rem">暂无 Workflow 定义</p>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const workflows = ref([])

onMounted(fetchWorkflows)
async function fetchWorkflows() {
  try {
    const res = await fetch('/api/v1/admin/workflows')
    const data = await res.json()
    workflows.value = data.workflows || []
  } catch { workflows.value = [] }
}

async function runWorkflow(wf) {
  try {
    const res = await fetch('/api/v1/workflow/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(wf.definition),
    })
    const result = await res.json()
    alert('Workflow 已执行完成\n状态: ' + result.status)
  } catch (e) {
    alert('执行失败: ' + e.message)
  }
}

async function deleteWorkflow(id) {
  if (!confirm('确认归档此 Workflow？')) return
  await fetch(`/api/v1/admin/workflows/${id}`, { method: 'DELETE' })
  await fetchWorkflows()
}

function formatDate(d) {
  if (!d) return '-'
  return new Date(d).toLocaleString('zh-CN')
}
</script>
