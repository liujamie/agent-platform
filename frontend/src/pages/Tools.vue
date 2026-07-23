<template>
  <div>
    <div class="page-actions">
      <h1 class="page-title" style="margin-bottom: 0">工具管理</h1>
      <button @click="openAdd" class="btn btn-primary">+ 注册 MCP 连接</button>
    </div>
    <p class="page-subtitle">注册 MCP 服务器，Agent 可调用其提供的工具。内置工具（web_search、code_executor 等）始终可用。</p>

    <table class="data-table">
      <thead>
        <tr>
          <th>名称</th>
          <th>类型</th>
          <th>命令 / URL</th>
          <th>工具数</th>
          <th>状态</th>
          <th>创建时间</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="c in connections" :key="c.id">
          <td><strong>{{ c.name }}</strong></td>
          <td><code>{{ c.connection_type }}</code></td>
          <td style="max-width: 260px; overflow: hidden; text-overflow: ellipsis">
            {{ c.connection_type === 'stdio' ? (c.command + ' ' + (c.args || []).join(' ')) : c.url }}
          </td>
          <td>{{ (c.tools || []).length }}</td>
          <td>
            <span v-if="c.status === 'connected'" class="badge badge-active">已连接</span>
            <span v-else-if="c.status === 'error'" class="badge badge-error" :title="c.error_message">错误</span>
            <span v-else class="badge badge-archived">未连接</span>
          </td>
          <td style="color: #999; font-size: 0.85rem">{{ formatDate(c.created_at) }}</td>
          <td>
            <button v-if="c.status !== 'connected'" @click="connect(c.id)" class="btn btn-outline btn-sm" :disabled="connecting === c.id">连接</button>
            <button v-else @click="disconnect(c.id)" class="btn btn-outline btn-sm">断开</button>
            <button @click="openEdit(c)" class="btn btn-outline btn-sm">编辑</button>
            <button @click="del(c)" class="btn btn-danger btn-sm">删除</button>
          </td>
        </tr>
        <tr v-if="connections.length === 0">
          <td colspan="7" style="text-align: center; color: #999; padding: 2rem">暂无 MCP 连接，点击上方按钮注册</td>
        </tr>
      </tbody>
    </table>

    <!-- Expandable tool list per connection -->
    <div v-for="c in connectionsWithTools" :key="c.id" class="card" style="margin-top: 1rem">
      <div class="card-title">{{ c.name }} 的工具列表</div>
      <div v-if="c.tools.length === 0" style="color: #999; font-size: 0.9rem; padding: 0.5rem 0">暂未连接</div>
      <table v-else class="data-table" style="margin-top: 0.5rem">
        <thead>
          <tr><th>工具名</th><th>描述</th></tr>
        </thead>
        <tbody>
          <tr v-for="t in c.tools" :key="t">
            <td><code>{{ t }}</code></td>
            <td style="color: #666">{{ getToolDescription(t) }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Modal -->
    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal">
        <h2 style="margin-bottom: 1rem">{{ isEditing ? '编辑 MCP 连接' : '注册 MCP 连接' }}</h2>

        <div class="form-group">
          <label class="form-label">名称</label>
          <input v-model="form.name" class="form-input" :disabled="isEditing" placeholder="如：github-server" />
          <p class="form-hint">唯一标识名，创建后不可修改</p>
        </div>

        <div class="form-group">
          <label class="form-label">连接类型</label>
          <select v-model="form.connection_type" class="form-input">
            <option value="stdio">stdio（子进程）</option>
            <option value="sse">SSE（HTTP 远程）</option>
          </select>
        </div>

        <template v-if="form.connection_type === 'stdio'">
          <div class="form-group">
            <label class="form-label">命令</label>
            <input v-model="form.command" class="form-input" placeholder="如：npx / uvx / python" />
            <p class="form-hint">MCP 服务器的启动命令</p>
          </div>
          <div class="form-group">
            <label class="form-label">参数</label>
            <input v-model="form.argsText" class="form-input" placeholder="如：-y @modelcontextprotocol/server-github" />
            <p class="form-hint">命令参数，用空格分隔</p>
          </div>
        </template>

        <template v-else>
          <div class="form-group">
            <label class="form-label">URL</label>
            <input v-model="form.url" class="form-input" placeholder="如：http://localhost:8080/mcp" />
          </div>
        </template>

        <div class="form-group">
          <label class="form-label">环境变量</label>
          <div v-for="(ev, i) in form.envList" :key="i" style="display: flex; gap: 0.5rem; margin-bottom: 0.5rem">
            <input v-model="ev.key" class="form-input" placeholder="KEY" style="flex: 1" />
            <input v-model="ev.value" class="form-input" type="password" placeholder="VALUE" style="flex: 2" />
            <button @click="form.envList.splice(i, 1)" class="btn btn-outline btn-sm" style="flex-shrink: 0">✕</button>
          </div>
          <button @click="form.envList.push({key:'', value:''})" class="btn btn-outline btn-sm">+ 添加环境变量</button>
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
import { ref, computed, onMounted } from 'vue'

const connections = ref([])
const showModal = ref(false)
const isEditing = ref(false)
const saving = ref(false)
const editingId = ref(null)
const connecting = ref(null)
const allToolDetails = ref({})

const form = ref({
  name: '',
  connection_type: 'stdio',
  command: '',
  argsText: '',
  url: '',
  envList: [],
})

const connectionsWithTools = computed(() =>
  connections.value.filter(c => c.status === 'connected' && (c.tools || []).length > 0)
)

onMounted(fetchConnections)

async function fetchConnections() {
  try {
    const res = await fetch('/api/v1/admin/mcp-connections/')
    const data = await res.json()
    connections.value = data.connections || []
    const details = {}
    for (const c of connections.value) {
      for (const t of (c.tools || [])) {
        details[t] = true
      }
    }
    try {
      const tr = await fetch('/api/v1/tool/list')
      const td = await tr.json()
      for (const t of (td.tools || [])) {
        details[t.name] = t.description
      }
    } catch {}
    allToolDetails.value = details
  } catch { connections.value = [] }
}

function getToolDescription(name) {
  const d = allToolDetails.value[name]
  return typeof d === 'string' ? d : ''
}

function openAdd() {
  isEditing.value = false
  editingId.value = null
  form.value = { name: '', connection_type: 'stdio', command: '', argsText: '', url: '', envList: [] }
  showModal.value = true
}

function openEdit(c) {
  isEditing.value = true
  editingId.value = c.id
  const envList = []
  if (c.env_vars) {
    for (const [k, v] of Object.entries(c.env_vars)) {
      envList.push({ key: k, value: v })
    }
  }
  form.value = {
    name: c.name,
    connection_type: c.connection_type,
    command: c.command || '',
    argsText: (c.args || []).join(' '),
    url: c.url || '',
    envList: envList.length ? envList : [{ key: '', value: '' }],
  }
  showModal.value = true
}

function closeModal() {
  showModal.value = false
}

async function save() {
  saving.value = true
  try {
    const env_vars = {}
    for (const ev of form.value.envList) {
      if (ev.key) env_vars[ev.key] = ev.value
    }
    const body = {
      name: form.value.name,
      connection_type: form.value.connection_type,
      command: form.value.command || null,
      args: form.value.argsText ? form.value.argsText.split(/\s+/) : [],
      url: form.value.url || null,
      env_vars: env_vars,
    }

    if (isEditing.value) {
      const res = await fetch(`/api/v1/admin/mcp-connections/${editingId.value}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!res.ok) { const d = await res.json(); alert(d.detail || '保存失败'); return }
    } else {
      const res = await fetch('/api/v1/admin/mcp-connections/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!res.ok) { const d = await res.json(); alert(d.detail || '保存失败'); return }
    }
    closeModal()
    await fetchConnections()
  } catch (e) {
    alert('保存失败: ' + e.message)
  } finally {
    saving.value = false
  }
}

async function connect(id) {
  connecting.value = id
  try {
    const res = await fetch(`/api/v1/admin/mcp-connections/${id}/connect`, { method: 'POST' })
    if (!res.ok) { const d = await res.json(); alert(d.detail || '连接失败'); return }
    await fetchConnections()
  } catch (e) {
    alert('连接失败: ' + e.message)
  } finally {
    connecting.value = null
  }
}

async function disconnect(id) {
  try {
    const res = await fetch(`/api/v1/admin/mcp-connections/${id}/disconnect`, { method: 'POST' })
    if (!res.ok) { const d = await res.json(); alert(d.detail || '断开失败'); return }
    await fetchConnections()
  } catch (e) {
    alert('断开失败: ' + e.message)
  }
}

async function del(c) {
  if (!confirm(`确认删除 MCP 连接「${c.name}」？`)) return
  try {
    const res = await fetch(`/api/v1/admin/mcp-connections/${c.id}`, { method: 'DELETE' })
    if (!res.ok) { const d = await res.json(); alert(d.detail || '删除失败'); return }
    await fetchConnections()
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
  width: 90%; max-width: 560px; max-height: 90vh; overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0,0,0,0.3);
}
</style>
