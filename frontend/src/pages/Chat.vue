<template>
  <div class="chat-layout">
    <!-- Header -->
    <div class="chat-header">
      <h1 class="page-title" style="margin-bottom: 0">Agent 对话</h1>
      <button v-if="currentSessionId && !loading" @click="newChat" class="btn btn-outline">+ 新建对话</button>
    </div>

    <div class="chat-body">
      <!-- Left: Session sidebar -->
      <aside class="session-sidebar">
        <div class="session-sidebar-header">
          <span style="font-weight: 600; font-size: 0.9rem">会话历史</span>
        </div>

        <div class="session-list">
          <div
            v-for="s in sessions"
            :key="s.session_id"
            :class="['session-item', { active: s.session_id === currentSessionId }]"
            @click="switchSession(s)"
          >
            <div class="session-name">{{ s.name }}</div>
            <div class="session-meta">{{ formatTime(s.created_at) }} · {{ s.message_count }} 条</div>
            <button v-if="s.session_id === currentSessionId" class="session-del" @click.stop="deleteSession(s)" title="删除会话">×</button>
          </div>
          <div v-if="sessions.length === 0" class="session-empty">
            <p v-if="!selectedAgentId">选择一个 Agent 开始</p>
            <p v-else>暂无历史会话，点击上方新建</p>
          </div>
        </div>

        <!-- Agent selector at the bottom of sidebar -->
        <div class="session-sidebar-footer">
          <select v-model="selectedAgentId" class="form-input agent-select" @change="onAgentChange">
            <option value="" disabled>-- 选择 Agent --</option>
            <option v-for="a in agents" :key="a.id" :value="a.id">
              {{ a.name }} ({{ a.model_name }})
            </option>
          </select>
          <div v-if="selectedAgent" class="agent-tools">
            <span style="font-size: 0.75rem; color: #999">工具: </span>
            <code v-for="t in resolvedTools" :key="t" class="tool-tag">{{ t }}</code>
            <span v-if="!resolvedTools.length" style="font-size: 0.75rem; color: #999">无</span>
          </div>
        </div>
      </aside>

      <!-- Right: Chat area -->
      <main class="chat-main">
        <div class="chat-messages" ref="messagesRef">
          <div v-if="messages.length === 0" class="chat-empty">
            <p v-if="!selectedAgentId">选择一个 Agent，输入消息开始对话</p>
            <p v-else>开始一个新对话吧</p>
          </div>
          <div v-for="(msg, i) in messages" :key="i" :class="['chat-msg', msg.role === 'user' ? 'chat-msg-user' : 'chat-msg-agent']">
            <div class="chat-avatar">{{ msg.role === 'user' ? '👤' : '🤖' }}</div>
            <div class="chat-bubble">
              <div v-if="msg.thinking && msg.thinking.length" class="chat-thinking">
                <span v-for="(step, si) in msg.thinking" :key="si" class="thinking-step">{{ step }}</span>
              </div>
              <div v-if="msg.content" class="chat-content" v-html="renderContent(msg.content)"></div>
              <div v-if="msg.tool_calls && msg.tool_calls.length" class="chat-tools">
                <div v-for="tc in msg.tool_calls" :key="tc.id" class="tool-call">🔧 {{ tc.function.name }}({{ tc.function.arguments }})</div>
              </div>
              <div v-if="msg.tool_results && msg.tool_results.length" class="chat-tool-results">
                <div v-for="(tr, ti) in msg.tool_results" :key="ti" class="tool-result">📦 {{ tr }}</div>
              </div>
            </div>
          </div>
          <div v-if="loading" class="chat-msg chat-msg-agent">
            <div class="chat-avatar">🤖</div>
            <div class="chat-bubble">
              <div class="chat-typing">
                <span v-if="streamingText">{{ streamingText }}</span>
                <span v-else class="typing-dots"><span>.</span><span>.</span><span>.</span></span>
              </div>
            </div>
          </div>
        </div>

        <!-- Input area -->
        <div class="chat-input-area">
          <textarea
            v-model="inputText"
            class="form-input chat-input"
            :placeholder="inputPlaceholder"
            rows="2"
            @keydown.enter.prevent="sendMessage"
            :disabled="loading || !selectedAgentId"
          ></textarea>
          <button
            @click="sendMessage"
            class="btn btn-primary send-btn"
            :disabled="loading || !selectedAgentId || !inputText.trim()"
          >{{ loading ? '停止' : '发送' }}</button>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'

const agents = ref([])
const sessions = ref([])
const selectedAgentId = ref('')
const currentSessionId = ref('')
const inputText = ref('')
const messages = ref([])
const loading = ref(false)
const streamingText = ref('')
const abortController = ref(null)
const messagesRef = ref(null)

const mcpConnections = ref([])

const resolvedTools = computed(() => {
  const agent = selectedAgent.value
  if (!agent) return []
  const names = new Set(agent.tools || [])
  for (const connName of (agent.connections || [])) {
    names.add(`🔗 ${connName}`)
  }
  return [...names].sort()
})

const selectedAgent = computed(() =>
  agents.value.find(a => a.id === selectedAgentId.value)
)

const inputPlaceholder = computed(() =>
  selectedAgentId.value ? '输入消息...' : '请先选择一个 Agent'
)

onMounted(fetchAgents)

async function fetchAgents() {
  try {
    const [agentsRes, mcpRes] = await Promise.all([
      fetch('/api/v1/admin/agents').then(r => r.json()),
      fetch('/api/v1/admin/mcp-connections/').then(r => r.json()),
    ])
    agents.value = (agentsRes.agents || []).filter(a => a.status === 'active')
    mcpConnections.value = mcpRes.connections || []
  } catch { agents.value = []; mcpConnections.value = [] }
}

async function fetchSessions() {
  if (!selectedAgentId.value) {
    sessions.value = []
    return
  }
  try {
    const res = await fetch(`/api/v1/agent/${selectedAgentId.value}/sessions`)
    const data = await res.json()
    sessions.value = data.sessions || []
  } catch { sessions.value = [] }
}

function onAgentChange() {
  currentSessionId.value = ''
  messages.value = []
  streamingText.value = ''
  fetchSessions()
}

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts * 1000)
  const now = new Date()
  const isToday = d.toDateString() === now.toDateString()
  if (isToday) return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  return d.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
}

async function newChat() {
  if (loading.value || !selectedAgentId.value) return
  try {
    const res = await fetch(`/api/v1/agent/${selectedAgentId.value}/sessions`, { method: 'POST' })
    const data = await res.json()
    currentSessionId.value = data.session_id
    messages.value = []
    streamingText.value = ''
    await fetchSessions()
    scrollToBottom()
  } catch { /* ignore */ }
}

async function switchSession(session) {
  if (loading.value) return
  currentSessionId.value = session.session_id
  messages.value = []
  streamingText.value = ''

  try {
    const res = await fetch(`/api/v1/agent/session/messages/${session.session_id}`)
    const data = await res.json()
    messages.value = data.messages || []
    nextTick(scrollToBottom)
  } catch { /* ignore */ }
}

async function deleteSession(session) {
  if (!confirm(`删除会话「${session.name}」？`)) return
  try {
    await fetch(`/api/v1/agent/session/${session.session_id}`, { method: 'DELETE' })
    if (currentSessionId.value === session.session_id) {
      currentSessionId.value = ''
      messages.value = []
    }
    await fetchSessions()
  } catch { /* ignore */ }
}

function renderContent(text) {
  if (!text) return ''
  return text
    .replace(/### (.+)/g, '<h3>$1</h3>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
}

async function sendMessage() {
  const msg = inputText.value.trim()
  if (!msg || loading.value || !selectedAgentId.value) return

  // Auto-create session if none exists
  if (!currentSessionId.value) {
    try {
      const res = await fetch(`/api/v1/agent/${selectedAgentId.value}/sessions`, { method: 'POST' })
      const data = await res.json()
      currentSessionId.value = data.session_id
      await fetchSessions()
    } catch { return }
  }

  if (loading.value && abortController.value) {
    abortController.value.abort()
    loading.value = false
    return
  }

  messages.value.push({ role: 'user', content: msg })
  inputText.value = ''
  scrollToBottom()

  loading.value = true
  streamingText.value = ''
  abortController.value = new AbortController()

  const msgIndex = messages.value.length
  messages.value.push({ role: 'agent', content: '', thinking: [], tool_calls: [], tool_results: [] })

  try {
    const res = await fetch(`/api/v1/agent/stream/${selectedAgentId.value}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg, session_id: currentSessionId.value }),
      signal: abortController.value.signal,
    })

    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let currentEvent = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const parts = buffer.split('\n')
      buffer = parts.pop() || ''

      for (const line of parts) {
        if (line.startsWith('event: ')) {
          currentEvent = line.slice(7).trim()
        } else if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            const last = messages.value[msgIndex]

            if (currentEvent === 'tool_call') {
              if (!last.thinking.includes(data.content)) last.thinking.push(data.content)
            } else if (currentEvent === 'tool_result') {
              if (!last.tool_results.includes(data.content)) last.tool_results.push(data.content)
            } else if (currentEvent === 'chunk' || currentEvent === 'end') {
              streamingText.value = data.content
              last.content = data.content
            }
          } catch { /* ignore parse errors */ }
        }
      }
      scrollToBottom()
    }

    // Refresh session list (name may have been auto-updated)
    await fetchSessions()
  } catch (err) {
    if (err.name !== 'AbortError') {
      messages.value[msgIndex].content = `Error: ${err.message}`
    }
  } finally {
    loading.value = false
    streamingText.value = ''
    abortController.value = null
    scrollToBottom()
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
}
</script>

<style scoped>
.chat-layout {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 48px);
}

.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
  flex-shrink: 0;
}

.chat-body {
  display: flex;
  gap: 0.5rem;
  flex: 1;
  min-height: 0;
}

/* ── Session Sidebar ── */
.session-sidebar {
  width: 210px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: white;
  border-radius: 6px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.06);
  overflow: hidden;
}

.session-sidebar-header {
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid #f0f0f0;
  flex-shrink: 0;
}

.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 0.25rem 0.35rem;
}

.session-item {
  padding: 0.4rem 0.55rem;
  border-radius: 4px;
  cursor: pointer;
  margin-bottom: 1px;
  position: relative;
  transition: background 0.1s;
}
.session-item:hover { background: #f5f5f5; }
.session-item.active { background: #eef2ff; }

.session-name {
  font-size: 0.75rem;
  font-weight: 500;
  color: #333;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding-right: 1rem;
}
.session-meta {
  font-size: 0.65rem;
  color: #aaa;
  margin-top: 1px;
}
.session-del {
  position: absolute;
  top: 0.3rem;
  right: 0.3rem;
  width: 16px;
  height: 16px;
  border: none;
  background: transparent;
  color: #ccc;
  cursor: pointer;
  font-size: 0.85rem;
  line-height: 1;
  border-radius: 3px;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
}
.session-item:hover .session-del { opacity: 1; }
.session-del:hover { background: #ffebee; color: #e53935; }

.session-empty {
  text-align: center;
  color: #aaa;
  font-size: 0.72rem;
  padding: 1.5rem 0;
}

.session-sidebar-footer {
  padding: 0.5rem 0.65rem;
  border-top: 1px solid #f0f0f0;
  flex-shrink: 0;
}
.agent-select { font-size: 0.75rem; padding: 0.3rem 0.45rem; }
.agent-tools {
  margin-top: 0.25rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.15rem;
}

/* ── Chat Main ── */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  background: white;
  border-radius: 6px;
  padding: 0.75rem;
  margin-bottom: 0.5rem;
  box-shadow: 0 1px 2px rgba(0,0,0,0.06);
}
.chat-empty {
  text-align: center;
  color: #aaa;
  font-size: 0.8rem;
  padding: 3rem 0;
}

.chat-msg {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}
.chat-msg-user { flex-direction: row-reverse; }
.chat-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.85rem;
  flex-shrink: 0;
  background: #f0f0f0;
}
.chat-bubble {
  max-width: 80%;
  padding: 0.5rem 0.75rem;
  border-radius: 8px;
  background: #f7f7f8;
  line-height: 1.55;
  font-size: 0.8rem;
}
.chat-msg-user .chat-bubble { background: #1a1a2e; color: white; }
.chat-content { word-break: break-word; }
.chat-content :deep(h3) { font-size: 0.85rem; margin: 0.35rem 0 0.15rem; }
.chat-content :deep(code) { font-size: 0.75rem; background: #f0f0f0; padding: 0.1rem 0.3rem; border-radius: 3px; }
.chat-msg-user .chat-content :deep(code) { background: rgba(255,255,255,0.15); }
.chat-content :deep(pre) { font-size: 0.72rem; background: #f8f8f8; padding: 0.5rem; border-radius: 4px; overflow-x: auto; }
.chat-msg-user .chat-content :deep(pre) { background: rgba(255,255,255,0.08); }

.chat-thinking {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  margin-bottom: 0.25rem;
  padding-bottom: 0.25rem;
  border-bottom: 1px solid #eee;
}
.thinking-step { font-size: 0.7rem; color: #888; font-style: italic; }

.chat-tools, .chat-tool-results {
  margin-top: 0.25rem;
  padding-top: 0.25rem;
  border-top: 1px dashed #e0e0e0;
}
.tool-call, .tool-result {
  font-size: 0.72rem;
  padding: 0.1rem 0;
  color: #666;
  font-family: 'SFMono-Regular', Consolas, monospace;
}
.chat-msg-user .tool-call,
.chat-msg-user .tool-result { color: #bbb; }

.tool-tag {
  display: inline-block;
  background: #e8f5e9;
  color: #2e7d32;
  padding: 0.05rem 0.3rem;
  border-radius: 3px;
  font-size: 0.68rem;
}

.chat-typing { color: #888; font-size: 0.8rem; }
.typing-dots span {
  animation: blink 1.4s infinite;
  font-size: 1.2rem;
}
.typing-dots span:nth-child(2) { animation-delay: 0.2s; }
.typing-dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes blink {
  0% { opacity: 0.2; }
  50% { opacity: 1; }
  100% { opacity: 0.2; }
}

.chat-input-area {
  display: flex;
  gap: 0.4rem;
  align-items: flex-end;
  flex-shrink: 0;
}
.chat-input {
  flex: 1;
  resize: none;
  min-height: 36px;
  padding: 0.4rem 0.55rem;
  font-size: 0.8rem;
}
.send-btn {
  height: 36px;
  white-space: nowrap;
  padding: 0.3rem 0.65rem;
}
</style>
