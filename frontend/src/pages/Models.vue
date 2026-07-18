<template>
  <div>
    <div class="page-actions">
      <h1 class="page-title" style="margin-bottom: 0">模型管理</h1>
      <button @click="openAdd" class="btn btn-primary">+ 添加模型</button>
    </div>
    <p class="page-subtitle">管理 LLM 模型配置，添加后可在 Agent 中选择使用</p>

    <table class="data-table">
      <thead>
        <tr>
          <th>名称</th>
          <th>Provider</th>
          <th>模型名</th>
          <th>API Key</th>
          <th>当前使用</th>
          <th>创建时间</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="m in models" :key="m.id">
          <td><strong>{{ m.name }}</strong></td>
          <td><code>{{ m.provider }}</code></td>
          <td><code>{{ m.model }}</code></td>
          <td>{{ m.has_api_key ? '✅ 已配置' : '❌ 未配置' }}</td>
          <td>
            <span v-if="m.is_current" class="badge badge-active">当前</span>
            <button v-else @click="switchModel(m.id)" class="btn btn-outline btn-sm">切换</button>
          </td>
          <td style="color: #999; font-size: 0.85rem">{{ formatDate(m.created_at) }}</td>
          <td>
            <button @click="openEdit(m)" class="btn btn-outline btn-sm">编辑</button>
            <button @click="deleteModel(m.id, m.name)" class="btn btn-danger btn-sm" :disabled="m.is_current">删除</button>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-if="models.length === 0" style="text-align: center; color: #999; padding: 2rem">暂无模型配置，点击上方按钮添加</p>

    <!-- Modal -->
    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal">
        <h2 style="margin-bottom: 1rem">{{ isEditing ? '编辑模型' : '添加模型' }}</h2>

        <div class="form-group">
          <label class="form-label">名称</label>
          <input v-model="form.name" class="form-input" :disabled="isEditing" placeholder="如：deepseek-main" />
          <p class="form-hint">唯一标识名，创建后不可修改</p>
        </div>

        <div class="form-group">
          <label class="form-label">Provider</label>
          <select v-model="form.provider" class="form-input">
            <option value="openai">OpenAI 兼容（DeepSeek / GPT 等）</option>
            <option value="dashscope">阿里云 DashScope（通义千问）</option>
          </select>
        </div>

        <div class="form-group">
          <label class="form-label">模型名</label>
          <input v-model="form.model" class="form-input" placeholder="如：deepseek-v4-flash / gpt-4o / qwen-plus" />
        </div>

        <div class="form-group">
          <label class="form-label">{{ isEditing ? 'API Key（留空不修改）' : 'API Key' }}</label>
          <input v-model="form.api_key" type="password" class="form-input" :placeholder="isEditing ? '留空则保持不变' : 'sk-...'" />
        </div>

        <div class="form-group" v-if="form.provider === 'openai'">
          <label class="form-label">API 地址</label>
          <input v-model="form.base_url" class="form-input" placeholder="https://api.deepseek.com" />
          <p class="form-hint">默认 https://api.deepseek.com</p>
        </div>

        <div style="display: flex; gap: 0.5rem; justify-content: flex-end; margin-top: 1.5rem">
          <button @click="closeModal" class="btn btn-outline">取消</button>
          <button @click="save" class="btn btn-primary" :disabled="saving">{{ saving ? '保存中...' : '保存' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const models = ref([])
const showModal = ref(false)
const isEditing = ref(false)
const saving = ref(false)
const editingId = ref(null)

const form = ref({
  name: '',
  provider: 'openai',
  model: '',
  api_key: '',
  base_url: '',
})

onMounted(fetchModels)

async function fetchModels() {
  try {
    const res = await fetch('/api/v1/admin/models/')
    const data = await res.json()
    models.value = data.models || []
  } catch { models.value = [] }
}

function openAdd() {
  isEditing.value = false
  editingId.value = null
  form.value = { name: '', provider: 'openai', model: '', api_key: '', base_url: '' }
  showModal.value = true
}

function openEdit(m) {
  isEditing.value = true
  editingId.value = m.id
  form.value = {
    name: m.name,
    provider: m.provider,
    model: m.model,
    api_key: '',
    base_url: m.base_url || '',
  }
  showModal.value = true
}

function closeModal() {
  showModal.value = false
}

async function save() {
  saving.value = true
  try {
    if (isEditing.value) {
      const body = {}
      if (form.value.provider) body.provider = form.value.provider
      if (form.value.model) body.model = form.value.model
      if (form.value.api_key) body.api_key = form.value.api_key
      if (form.value.base_url !== undefined) body.base_url = form.value.base_url || null
      const res = await fetch(`/api/v1/admin/models/${editingId.value}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!res.ok) { const d = await res.json(); alert(d.detail || '保存失败'); return }
    } else {
      const res = await fetch('/api/v1/admin/models/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form.value),
      })
      if (!res.ok) { const d = await res.json(); alert(d.detail || '保存失败'); return }
    }
    closeModal()
    await fetchModels()
  } catch (e) {
    alert('保存失败: ' + e.message)
  } finally {
    saving.value = false
  }
}

async function switchModel(id) {
  try {
    const res = await fetch(`/api/v1/admin/models/${id}/switch`, { method: 'POST' })
    if (!res.ok) { const d = await res.json(); alert(d.detail || '切换失败'); return }
    await fetchModels()
  } catch (e) {
    alert('切换失败: ' + e.message)
  }
}

async function deleteModel(id, name) {
  if (!confirm(`确认删除模型「${name}」？`)) return
  try {
    const res = await fetch(`/api/v1/admin/models/${id}`, { method: 'DELETE' })
    if (!res.ok) { const d = await res.json(); alert(d.detail || '删除失败'); return }
    await fetchModels()
  } catch (e) {
    alert('删除失败: ' + e.message)
  }
}

function formatDate(d) {
  if (!d) return '-'
  return new Date(d).toLocaleString('zh-CN')
}
</script>

<style scoped>
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.4);
  display: flex; align-items: center; justify-content: center; z-index: 100;
}
.modal {
  background: white; border-radius: 12px; padding: 2rem;
  width: 90%; max-width: 520px; max-height: 90vh; overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0,0,0,0.3);
}
</style>
