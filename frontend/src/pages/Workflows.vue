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
          <th>名称</th>
          <th>节点数</th>
          <th>状态</th>
          <th>创建时间</th>
          <th>最近运行</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="wf in workflows" :key="wf.id">
          <td><strong>{{ wf.name }}</strong><br><span style="color:#999;font-size:0.7rem">{{ wf.description || '' }}</span></td>
          <td>{{ wf.definition?.nodes?.length || 0 }} 节点</td>
          <td><span :class="['badge', wf.status === 'active' ? 'badge-active' : 'badge-archived']">{{ wf.status }}</span></td>
          <td style="color:#999;font-size:0.8rem">{{ formatDate(wf.created_at) }}</td>
          <td>
            <span v-if="wf.last_run" style="font-size:0.8rem">
              <span :class="['badge', wf.last_run.status === 'success' ? 'badge-success' : 'badge-error']">{{ wf.last_run.status }}</span>
              {{ formatTime(wf.last_run.started_at) }}
            </span>
            <span v-else style="color:#999;font-size:0.8rem">-</span>
          </td>
          <td>
            <router-link :to="`/workflows/${wf.id}/edit`" class="btn btn-outline btn-sm">编辑</router-link>
            <button @click="runWorkflow(wf.id)" class="btn btn-primary btn-sm">运行</button>
            <button @click="deleteWorkflow(wf.id)" class="btn btn-danger btn-sm">归档</button>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-if="workflows.length === 0" style="text-align:center;color:#999;padding:2rem">暂无 Workflow 定义</p>

    <!-- Run Logs -->
    <!-- Run Input Modal -->
    <div v-if="showRunModal" class="modal-overlay" @click.self="showRunModal = false">
      <div class="modal" style="max-width:500px">
        <h2 style="font-size:0.95rem;margin-bottom:0.5rem">运行 Workflow</h2>
        <p style="font-size:0.78rem;color:#666;margin-bottom:0.75rem">输入参数（JSON 格式，节点中通过 input.xxx 引用）</p>
        <textarea v-model="runInputJson" class="form-textarea" rows="8" style="font-family:monospace;font-size:0.78rem" placeholder='{"code_diff": "diff --git a/src/main.py b/src/main.py\n+ print(1/0)"}'></textarea>
        <div style="display:flex;gap:0.4rem;justify-content:flex-end;margin-top:0.75rem">
          <button @click="showRunModal = false" class="btn btn-outline btn-sm">取消</button>
          <button @click="confirmRun" class="btn btn-primary btn-sm" :disabled="runningWf">{{ runningWf ? '运行中...' : '运行' }}</button>
        </div>
      </div>
    </div>

    <div style="margin-top:1.5rem">
      <h2 style="font-size:1rem;margin-bottom:0.5rem">运行历史</h2>
      <table class="data-table">
        <thead>
          <tr>
            <th>Trace ID</th>
            <th>状态</th>
            <th>耗时</th>
            <th>触发方式</th>
            <th>时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="inst in instances" :key="inst.id">
            <td><code style="font-size:0.75rem">{{ inst.trace_id?.slice(0,12) }}...</code></td>
            <td><span :class="['badge', inst.status === 'success' ? 'badge-success' : inst.status === 'running' ? 'badge-active' : 'badge-error']">{{ inst.status }}</span></td>
            <td style="font-size:0.8rem">{{ inst.duration_ms }}ms</td>
            <td style="font-size:0.8rem">{{ inst.trigger_type }}</td>
            <td style="color:#999;font-size:0.8rem">{{ formatTime(inst.started_at) }}</td>
            <td><router-link :to="`/workflows/runs/${inst.trace_id}`" class="btn btn-outline btn-sm">详情</router-link></td>
          </tr>
        </tbody>
      </table>
      <p v-if="instances.length === 0" style="text-align:center;color:#999;padding:1rem;font-size:0.8rem">暂无运行记录</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const workflows = ref([])
const instances = ref([])
const showRunModal = ref(false)
const runInputJson = ref('')
const runWfId = ref(null)
const runningWf = ref(false)

onMounted(async () => {
  await fetchWorkflows()
  await fetchInstances()
})

async function fetchWorkflows() {
  try {
    const res = await fetch('/api/v1/admin/workflows')
    const data = await res.json()
    workflows.value = (data.workflows || []).map(w => ({
      ...w,
      last_run: null,
    }))
    // Try to fetch last run for each workflow
    const instRes = await fetch('/api/v1/workflow/instances?page_size=50')
    const instData = await instRes.json()
    const runs = instData.instances || []
    for (const w of workflows.value) {
      const last = runs.find(r => r.workflow_id === w.id)
      if (last) w.last_run = last
    }
  } catch { workflows.value = [] }
}

async function fetchInstances() {
  try {
    const res = await fetch('/api/v1/workflow/instances?page_size=10')
    const data = await res.json()
    instances.value = data.instances || []
  } catch { instances.value = [] }
}

async function runWorkflow(id) {
  runWfId.value = id
  runInputJson.value = ''
  showRunModal.value = true
}

async function confirmRun() {
  showRunModal.value = false
  runningWf.value = true
  let inputData = {}
  if (runInputJson.value.trim()) {
    try { inputData = JSON.parse(runInputJson.value) }
    catch { alert('JSON 格式错误，请检查'); runningWf.value = false; return }
  }
  try {
    const res = await fetch(`/api/v1/workflow/run/${runWfId.value}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ workflow_id: runWfId.value, input_data: inputData }),
    })
    const result = await res.json()
    alert(`Workflow 已完成\n状态: ${result.status}\n耗时: ${result.duration_ms}ms`)
    await fetchInstances()
  } catch (e) {
    alert('执行失败: ' + e.message)
  } finally {
    runningWf.value = false
  }
}

async function deleteWorkflow(id) {
  if (!confirm('确认归档此 Workflow？')) return
  await fetch(`/api/v1/admin/workflows/${id}`, { method: 'DELETE' })
  await fetchWorkflows()
}

function formatDate(d) { return d ? new Date(d).toLocaleDateString('zh-CN') : '-' }
function formatTime(d) { return d ? new Date(d).toLocaleString('zh-CN') : '-' }
</script>

<style scoped>
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.4);
  display: flex; align-items: center; justify-content: center; z-index: 100;
}
.modal {
  background: white; border-radius: 8px; padding: 1.5rem;
  width: 90%; max-width: 500px; box-shadow: 0 10px 40px rgba(0,0,0,0.2);
}
</style>
