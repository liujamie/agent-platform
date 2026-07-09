<template>
  <div>
    <h1 class="page-title">{{ isEdit ? '编辑 Agent' : '创建 Agent' }}</h1>
    <p class="page-subtitle">{{ isEdit ? '修改 Agent 配置' : '定义一个新的 AI Agent' }}</p>

    <div class="card" style="max-width: 700px">
      <div class="form-group">
        <label class="form-label">名称</label>
        <input v-model="form.name" class="form-input" placeholder="如：知识库助手" />
      </div>

      <div class="form-group">
        <label class="form-label">System Prompt</label>
        <textarea v-model="form.role" class="form-textarea" placeholder="你是一个企业知识专家..." rows="5" />
        <p class="form-hint">Agent 的角色和行为定义</p>
      </div>

      <div class="form-group">
        <label class="form-label">模型</label>
        <select v-model="form.model_name" class="form-input">
          <option value="deepseek-chat">DeepSeek Chat</option>
          <option value="qwen-plus">通义千问 Plus</option>
          <option value="gpt-4o-mini">GPT-4o Mini</option>
        </select>
      </div>

      <div class="form-group">
        <label class="form-label">工具（按住 Ctrl 多选）</label>
        <select v-model="form.tools" multiple class="form-input" style="height: 100px">
          <option v-for="t in availableTools" :key="t.name" :value="t.name">{{ t.name }} — {{ t.description }}</option>
        </select>
        <p class="form-hint">Agent 可调用的工具列表</p>
      </div>

      <div class="form-group">
        <label class="form-label">
          <input type="checkbox" v-model="form.memory_enabled" style="margin-right: 0.5rem" />
          启用记忆
        </label>
      </div>

      <div style="display: flex; gap: 0.5rem; margin-top: 1.5rem">
        <button @click="save" class="btn btn-primary">{{ isEdit ? '保存' : '创建' }}</button>
        <router-link to="/agents" class="btn btn-outline">取消</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const isEdit = computed(() => !!route.params.id)
const availableTools = ref([])

const form = ref({
  name: '',
  role: '',
  model_name: 'deepseek-chat',
  tools: [],
  memory_enabled: true,
})

onMounted(async () => {
  try {
    const res = await fetch('/api/v1/tool/list')
    const data = await res.json()
    availableTools.value = data.tools || []
  } catch { availableTools.value = [] }

  if (isEdit.value) {
    try {
      const res = await fetch(`/api/v1/admin/agents/${route.params.id}`)
      const data = await res.json()
      if (data.id) Object.assign(form.value, data)
    } catch { /* ignore */ }
  }
})

async function save() {
  const url = isEdit.value
    ? `/api/v1/admin/agents/${route.params.id}`
    : '/api/v1/admin/agents'
  const method = isEdit.value ? 'PUT' : 'POST'

  try {
    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form.value),
    })
    const data = await res.json()
    if (data.id || data.name) router.push('/agents')
    else alert('保存失败: ' + (data.error || data.detail || 'Unknown'))
  } catch (e) {
    alert('保存失败: ' + e.message)
  }
}
</script>
