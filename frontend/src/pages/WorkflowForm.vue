<template>
  <div>
    <h1 class="page-title">{{ isEdit ? '编辑 Workflow' : '创建 Workflow' }}</h1>
    <p class="page-subtitle">编辑 DAG 工作流定义</p>

    <div class="card">
      <div class="form-group">
        <label class="form-label">名称</label>
        <input v-model="form.name" class="form-input" placeholder="如：数据分析流程" />
      </div>
      <div class="form-group">
        <label class="form-label">描述</label>
        <input v-model="form.description" class="form-input" placeholder="可选描述" />
      </div>
      <div class="form-group">
        <label class="form-label">Workflow 定义 (JSON)</label>
        <textarea v-model="form.definitionStr" class="form-textarea" rows="15" />
        <p class="form-hint">nodes 定义节点，edges 定义依赖关系</p>
      </div>

      <div style="display: flex; gap: 0.5rem">
        <button @click="save" class="btn btn-primary">{{ isEdit ? '保存' : '创建' }}</button>
        <button @click="preview" class="btn btn-outline">验证 JSON</button>
        <router-link to="/workflows" class="btn btn-outline">取消</router-link>
      </div>
      <pre v-if="error" style="color: #c62828; margin-top: 1rem; font-size: 0.85rem">{{ error }}</pre>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const isEdit = computed(() => !!route.params.id)
const error = ref('')

const form = ref({
  name: '',
  description: '',
  definitionStr: JSON.stringify({
    nodes: [
      { id: "planner", type: "agent", config: { role: "拆解任务" } },
      { id: "search", type: "tool", config: { tool: "web_search" } },
      { id: "writer", type: "agent", config: { role: "生成报告" } },
    ],
    edges: [
      { source: "planner", target: "search" },
      { source: "search", target: "writer" },
    ],
  }, null, 2),
})

onMounted(async () => {
  if (isEdit.value) {
    try {
      const res = await fetch(`/api/v1/admin/workflows/${route.params.id}`)
      const data = await res.json()
      if (data.id) {
        form.value.name = data.name
        form.value.description = data.description || ''
        form.value.definitionStr = JSON.stringify(data.definition, null, 2)
      }
    } catch { /* ignore */ }
  }
})

function preview() {
  try {
    JSON.parse(form.value.definitionStr)
    error.value = 'JSON 格式正确 ✓'
  } catch (e) {
    error.value = 'JSON 格式错误: ' + e.message
  }
}

async function save() {
  let definition
  try {
    definition = JSON.parse(form.value.definitionStr)
  } catch (e) {
    error.value = 'JSON 格式错误: ' + e.message
    return
  }

  const url = isEdit.value
    ? `/api/v1/admin/workflows/${route.params.id}`
    : '/api/v1/admin/workflows'
  const method = isEdit.value ? 'PUT' : 'POST'

  try {
    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: form.value.name, description: form.value.description, definition }),
    })
    const data = await res.json()
    if (data.id || data.name) router.push('/workflows')
    else error.value = '保存失败: ' + JSON.stringify(data)
  } catch (e) {
    error.value = '保存失败: ' + e.message
  }
}
</script>
