<template>
  <div>
    <div class="page-actions">
      <h1 class="page-title" style="margin-bottom: 0">Skill 管理</h1>
      <button @click="openAdd" class="btn btn-primary">+ 创建 Skill</button>
    </div>
    <p class="page-subtitle">创建可复用的 Markdown 指令片段，绑定到 Agent 后自动注入 system prompt</p>

    <table class="data-table">
      <thead>
        <tr>
          <th>名称</th>
          <th>描述</th>
          <th>创建时间</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="s in skills" :key="s.id">
          <td><strong>{{ s.name }}</strong></td>
          <td style="color: #666">{{ s.description || '-' }}</td>
          <td style="color: #999; font-size: 0.85rem">{{ formatDate(s.created_at) }}</td>
          <td>
            <button @click="openEdit(s)" class="btn btn-outline btn-sm">编辑</button>
            <button @click="del(s)" class="btn btn-danger btn-sm">删除</button>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-if="skills.length === 0" style="text-align: center; color: #999; padding: 2rem">暂无 Skill，点击上方按钮创建</p>

    <!-- Modal -->
    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal">
        <h2 style="margin-bottom: 1rem">{{ isEditing ? '编辑 Skill' : '创建 Skill' }}</h2>

        <div class="form-group">
          <label class="form-label">名称</label>
          <input v-model="form.name" class="form-input" :disabled="isEditing" placeholder="如：code-review" />
        </div>

        <div class="form-group">
          <label class="form-label">描述</label>
          <input v-model="form.description" class="form-input" placeholder="简要说明这个 Skill 的用途" />
        </div>

        <div class="form-group">
          <label class="form-label">内容 (Markdown)</label>
          <textarea v-model="form.content" class="form-textarea" rows="12" placeholder="在此输入 Markdown 指令内容..." style="font-family: monospace"></textarea>
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

const skills = ref([])
const showModal = ref(false)
const isEditing = ref(false)
const saving = ref(false)
const editingId = ref(null)

const form = ref({ name: '', description: '', content: '' })

onMounted(fetchSkills)

async function fetchSkills() {
  try {
    const res = await fetch('/api/v1/admin/skills/')
    const data = await res.json()
    skills.value = data.skills || []
  } catch { skills.value = [] }
}

function openAdd() {
  isEditing.value = false; editingId.value = null
  form.value = { name: '', description: '', content: '' }
  showModal.value = true
}

function openEdit(s) {
  isEditing.value = true; editingId.value = s.id
  form.value = { name: s.name, description: s.description || '', content: s.content }
  showModal.value = true
}

function closeModal() { showModal.value = false }

async function save() {
  saving.value = true
  try {
    const body = isEditing.value
      ? { description: form.value.description, content: form.value.content }
      : { name: form.value.name, description: form.value.description, content: form.value.content }

    const res = await fetch(
      isEditing.value ? `/api/v1/admin/skills/${editingId.value}` : '/api/v1/admin/skills/',
      { method: isEditing.value ? 'PUT' : 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }
    )
    if (!res.ok) { const d = await res.json(); alert(d.detail || '保存失败'); return }
    closeModal(); await fetchSkills()
  } catch (e) { alert('保存失败: ' + e.message) }
  finally { saving.value = false }
}

async function del(s) {
  if (!confirm(`确认删除 Skill「${s.name}」？`)) return
  const res = await fetch(`/api/v1/admin/skills/${s.id}`, { method: 'DELETE' })
  if (!res.ok) { const d = await res.json(); alert(d.detail || '删除失败'); return }
  await fetchSkills()
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
  width: 90%; max-width: 620px; max-height: 90vh; overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0,0,0,0.3);
}
</style>
