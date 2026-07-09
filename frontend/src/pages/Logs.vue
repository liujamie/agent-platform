<template>
  <div>
    <h1 class="page-title">运行记录</h1>
    <p class="page-subtitle">查看 Agent/Workflow 执行历史</p>

    <div class="toolbar">
      <input v-model="searchTrace" class="form-input" placeholder="搜索 Trace ID..." @input="filterLogs" style="max-width: 300px" />
      <select v-model="statusFilter" class="form-input" @change="filterLogs" style="max-width: 150px">
        <option value="">全部状态</option>
        <option value="success">成功</option>
        <option value="error">失败</option>
      </select>
    </div>

    <table class="data-table">
      <thead>
        <tr>
          <th>Trace ID</th>
          <th>类型</th>
          <th>状态</th>
          <th>Token</th>
          <th>耗时</th>
          <th>时间</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="log in filteredLogs" :key="log.id">
          <td><code style="font-size: 0.8rem">{{ log.trace_id?.slice(0, 12) }}...</code></td>
          <td>{{ log.agent_id ? 'Agent' : log.workflow_id ? 'Workflow' : '-' }}</td>
          <td><span :class="['badge', log.status === 'success' ? 'badge-success' : 'badge-error']">{{ log.status }}</span></td>
          <td>{{ log.tokens }}</td>
          <td>{{ log.duration_ms }}ms</td>
          <td style="color: #999; font-size: 0.85rem">{{ formatDate(log.created_at) }}</td>
        </tr>
      </tbody>
    </table>
    <p v-if="filteredLogs.length === 0" style="text-align: center; color: #999; padding: 2rem">暂无运行记录</p>

    <div v-if="totalPages > 1" style="display: flex; justify-content: center; gap: 0.5rem; margin-top: 1rem">
      <button @click="changePage(page - 1)" :disabled="page <= 1" class="btn btn-outline btn-sm">上一页</button>
      <span style="padding: 0.3rem 0.5rem; font-size: 0.85rem">{{ page }} / {{ totalPages }}</span>
      <button @click="changePage(page + 1)" :disabled="page >= totalPages" class="btn btn-outline btn-sm">下一页</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const logs = ref([])
const page = ref(1)
const total = ref(0)
const pageSize = 15
const searchTrace = ref('')
const statusFilter = ref('')

const totalPages = computed(() => Math.ceil(total.value / pageSize) || 1)
const filteredLogs = computed(() => {
  let result = logs.value
  if (searchTrace.value) {
    const q = searchTrace.value.toLowerCase()
    result = result.filter(l => l.trace_id?.toLowerCase().includes(q))
  }
  if (statusFilter.value) {
    result = result.filter(l => l.status === statusFilter.value)
  }
  return result
})

onMounted(() => fetchLogs())

async function fetchLogs() {
  try {
    const res = await fetch(`/api/v1/admin/logs?page=${page.value}&page_size=${pageSize}`)
    const data = await res.json()
    logs.value = data.logs || []
    total.value = data.total || 0
  } catch { logs.value = [] }
}

function changePage(p) {
  page.value = p
  fetchLogs()
}

function filterLogs() {
  page.value = 1
}

function formatDate(d) {
  if (!d) return '-'
  return new Date(d).toLocaleString('zh-CN')
}
</script>
