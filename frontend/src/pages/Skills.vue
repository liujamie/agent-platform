<template>
  <div>
    <div class="page-actions">
      <h1 class="page-title" style="margin-bottom: 0">Skill 管理</h1>
      <div style="display: flex; gap: 0.5rem">
        <span v-if="syncing" class="badge badge-active">同步中...</span>
        <button @click="syncFromGit" class="btn btn-outline" :disabled="syncing">
          {{ syncing ? '同步中...' : '从 Git 同步' }}
        </button>
        <router-link to="/skills/guide" class="btn btn-outline">创建指南</router-link>
      </div>
    </div>
    <p class="page-subtitle">
      Skill 内容由 Git 管理版本，元数据自动同步到数据库。
      修改 prompt 请在 IDE 中编辑 <code>skills/&lt;name&gt;/prompt.md</code> 或点击"编辑 Prompt"。
    </p>

    <table class="data-table">
      <thead>
        <tr>
          <th>名称</th>
          <th>描述</th>
          <th>标签</th>
          <th>版本</th>
          <th>Git Commit</th>
          <th>状态</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="s in skills" :key="s.id">
          <td><strong>{{ s.name }}</strong></td>
          <td style="color: #666; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap">{{ s.description || '-' }}</td>
          <td>
            <span v-for="t in (s.tags || [])" :key="t" class="badge badge-active" style="margin-right: 0.25rem; font-size: 0.75rem">{{ t }}</span>
            <span v-if="!s.tags || s.tags.length === 0" style="color: #999">-</span>
          </td>
          <td><code>{{ s.version || '1.0.0' }}</code></td>
          <td>
            <code v-if="s.git_commit_hash" style="font-size: 0.8rem" :title="s.git_commit_hash">{{ s.git_commit_hash.slice(0, 8) }}</code>
            <span v-else style="color: #999">-</span>
          </td>
          <td><span :class="['badge', s.status === 'active' ? 'badge-active' : 'badge-archived']">{{ s.status }}</span></td>
          <td>
            <button @click="openEditor(s)" class="btn btn-outline btn-sm">编辑 Prompt</button>
            <button v-if="s.status === 'active'" @click="archiveSkill(s)" class="btn btn-danger btn-sm">归档</button>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-if="skills.length === 0" style="text-align: center; color: #999; padding: 2rem">
      暂无 Skill。在 <code>skills/</code> 目录下创建 skill 后点击"从 Git 同步"。
    </p>

    <!-- Prompt Editor Modal -->
    <div v-if="showEditor" class="modal-overlay" @click.self="closeEditor">
      <div class="modal" style="max-width: 800px">
        <h2 style="margin-bottom: 0.25rem">编辑 Prompt — {{ editingSkill?.name }}</h2>
        <p style="color: #999; font-size: 0.85rem; margin-bottom: 1rem">
          修改将直接写入 <code>{{ editingSkill?.path }}/prompt.md</code>，
          建议修改后执行 <code>git commit</code> 以保留版本历史。
        </p>

        <div v-if="editingSkill?.ext_files?.length" style="margin-bottom: 1rem; padding: 0.75rem; background: #f8f9fa; border-radius: 6px; font-size: 0.85rem">
          <strong>扩展文件（只读，请在 IDE 中编辑）：</strong>
          <div v-for="g in editingSkill.ext_files" :key="g.dir" style="margin-top: 0.3rem">
            <code style="color: #666">{{ g.dir }}/</code>
            <span v-for="f in g.files" :key="f" style="display: inline-block; margin-left: 0.5rem; color: #999">{{ f }}</span>
          </div>
        </div>

        <div class="form-group">
          <textarea v-model="promptContent" class="form-textarea" rows="16" style="font-family: monospace; font-size: 0.85rem"></textarea>
        </div>

        <div style="display: flex; gap: 0.5rem; justify-content: flex-end">
          <button @click="closeEditor" class="btn btn-outline">取消</button>
          <button @click="savePrompt" class="btn btn-primary" :disabled="saving">{{ saving ? '保存中...' : '保存' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const skills = ref([])
const syncing = ref(false)
const showEditor = ref(false)
const editingSkill = ref(null)
const promptContent = ref('')
const saving = ref(false)

onMounted(fetchSkills)

async function fetchSkills() {
  try {
    const res = await fetch('/api/v1/admin/skills/')
    const data = await res.json()
    skills.value = data.skills || []
  } catch { skills.value = [] }
}

async function syncFromGit() {
  syncing.value = true
  try {
    const res = await fetch('/api/v1/admin/skills/sync', { method: 'POST' })
    const data = await res.json()
    if (data.status === 'ok') {
      alert(`同步完成：新增 ${data.added}，更新 ${data.updated}${data.archived ? '，归档 ' + data.archived : ''}${data.errors?.length ? '，错误 ' + data.errors.length : ''}`)
    } else {
      alert('同步失败：' + (data.message || '未知错误'))
    }
    await fetchSkills()
  } catch (e) {
    alert('同步失败：' + e.message)
  } finally {
    syncing.value = false
  }
}

async function openEditor(s) {
  editingSkill.value = s
  promptContent.value = ''
  try {
    const res = await fetch(`/api/v1/admin/skills/${s.id}`)
    const data = await res.json()
    promptContent.value = data.content || ''
    editingSkill.value = { ...editingSkill.value, ext_files: data.ext_files || [], path: data.path }
  } catch (e) {
    alert('加载失败：' + e.message)
  }
  showEditor.value = true
}

function closeEditor() {
  showEditor.value = false
  editingSkill.value = null
  promptContent.value = ''
}

async function savePrompt() {
  if (!editingSkill.value) return
  saving.value = true
  try {
    const res = await fetch(`/api/v1/admin/skills/${editingSkill.value.id}/content`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: promptContent.value }),
    })
    if (!res.ok) {
      const d = await res.json()
      alert('保存失败：' + (d.detail || '未知错误'))
      return
    }
    closeEditor()
  } catch (e) {
    alert('保存失败：' + e.message)
  } finally {
    saving.value = false
  }
}

async function archiveSkill(s) {
  if (!confirm(`确认归档 Skill「${s.name}」？不会删除文件，仅标记为归档。`)) return
  const res = await fetch(`/api/v1/admin/skills/${s.id}`, { method: 'DELETE' })
  if (!res.ok) { const d = await res.json(); alert(d.detail || '归档失败'); return }
  await fetchSkills()
}
</script>

<style scoped>
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.4);
  display: flex; align-items: center; justify-content: center; z-index: 100;
}
.modal {
  background: white; border-radius: 12px; padding: 2rem;
  width: 90%; max-width: 800px; max-height: 90vh; overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0,0,0,0.3);
}
</style>
