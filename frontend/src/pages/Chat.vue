<template>
  <div>
    <div class="page-actions">
      <h1 class="page-title" style="margin-bottom: 0">Agent 对话</h1>
    </div>

    <!-- Agent 选择 + 设置 -->
    <div class="chat-toolbar">
      <select v-model="selectedAgentId" class="form-input" style="max-width: 300px">
        <option value="" disabled>-- 选择 Agent --</option>
        <option v-for="a in agents" :key="a.id" :value="a.id">
          {{ a.name }} ({{ a.model_name }})
        </option>
      </select>
      <label class="chat-tools-label">
        工具:
        <span v-if="selectedAgent && selectedAgent.tools.length">
          <code v-for="t in selectedAgent.tools" :key="t" class="tool-tag">{{ t }}</code>
        </span>
        <span v-else style="color: #999">无</span>
      </label>
    </div>

    <!-- 对话区域 -->
    <div class="chat-messages" ref="messagesRef">
      <div v-if="messages.length === 0" class="chat-empty">
        <p>选择一个 Agent，输入消息开始对话</p>
      </div>
      <div v-for="(msg, i) in messages" :key="i" :class="['chat-msg', msg.role === 'user' ? 'chat-msg-user' : 'chat-msg-agent']">
        <div class="chat-avatar">{{ msg.role === 'user' ? '👤' : '🤖' }}</div>
        <div class="chat-bubble">
          <div v-if="msg.thinking" class="chat-thinking">
            <span v-for="(step, si) in msg.thinking" :key="si" class="thinking-step">
              {{ step }}
            </span>
          </div>
          <div v-if="msg.content" class="chat-content" v-html="renderContent(msg.content)"></div>
          <div v-if="msg.tool_calls && msg.tool_calls.length" class="chat-tools">
            <div v-for="tc in msg.tool_calls" :key="tc.id" class="tool-call">
              🔧 {{ tc.function.name }}({{ tc.function.arguments }})
            </div>
          </div>
          <div v-if="msg.tool_results && msg.tool_results.length" class="chat-tool-results">
            <div v-for="(tr, ti) in msg.tool_results" :key="ti" class="tool-result">
              📦 {{ tr }}
            </div>
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

    <!-- 输入区域 -->
    <div class="chat-input-area">
      <textarea
        v-model="inputText"
        class="form-input chat-input"
        placeholder="输入消息..."
        rows="2"
        @keydown.enter.prevent="sendMessage"
        :disabled="loading || !selectedAgentId"
      ></textarea>
      <button
        @click="sendMessage"
        class="btn btn-primary send-btn"
        :disabled="loading || !selectedAgentId || !inputText.trim()"
      >
        {{ loading ? '停止' : '发送' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'

const agents = ref([])
const selectedAgentId = ref('')
const inputText = ref('')
const messages = ref([])
const loading = ref(false)
const streamingText = ref('')
const abortController = ref(null)
const messagesRef = ref(null)

const selectedAgent = computed(() =>
  agents.value.find(a => a.id === selectedAgentId.value)
)
const sessionId = computed(() =>
  selectedAgentId.value ? `agent-${selectedAgentId.value}` : ''
)

onMounted(fetchAgents)
async function fetchAgents() {
  try {
    const res = await fetch('/api/v1/admin/agents')
    const data = await res.json()
    agents.value = (data.agents || []).filter(a => a.status === 'active')
  } catch { agents.value = [] }
}

function renderContent(text) {
  if (!text) return ''
  // Simple markdown-like rendering
  return text
    .replace(/### (.+)/g, '<h3>$1</h3>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
}

async function sendMessage() {
  const msg = inputText.value.trim()
  if (!msg || loading.value || !selectedAgentId.value) return

  // If already loading, abort
  if (loading.value && abortController.value) {
    abortController.value.abort()
    loading.value = false
    return
  }

  // Add user message
  messages.value.push({ role: 'user', content: msg })
  inputText.value = ''
  scrollToBottom()

  // Start loading agent response
  loading.value = true
  streamingText.value = ''
  abortController.value = new AbortController()

  const msgIndex = messages.value.length
  messages.value.push({
    role: 'agent',
    content: '',
    thinking: [],
    tool_calls: [],
    tool_results: [],
  })

  try {
    const res = await fetch(`/api/v1/agent/stream/${selectedAgentId.value}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg, session_id: sessionId.value }),
      signal: abortController.value.signal,
    })

    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('event: ')) {
          const eventType = line.slice(7).trim()
          // Next line is data
          continue
        }
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            const content = data.content || ''

            // Update the last agent message
            const last = messages.value[msgIndex]

            // Check if event type was tool_call or tool_result from previous line
            // Since we have data but not event, infer from content
            if (content.startsWith('Calling tool:')) {
              if (!last.thinking.includes(content)) {
                last.thinking.push(content)
              }
            } else if (content && !last.content) {
              // This is the final output
              streamingText.value = content
              last.content = content
            } else if (content) {
              streamingText.value = content
              last.content = content
            }
          } catch { /* ignore parse errors */ }
        }
      }
      scrollToBottom()
    }
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
.chat-toolbar {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
  flex-wrap: wrap;
}
.chat-tools-label {
  font-size: 0.85rem;
  color: #666;
}
.tool-tag {
  display: inline-block;
  background: #e8f5e9;
  color: #2e7d32;
  padding: 0.1rem 0.4rem;
  border-radius: 4px;
  font-size: 0.8rem;
  margin: 0 0.2rem;
}

.chat-messages {
  height: calc(100vh - 320px);
  min-height: 300px;
  overflow-y: auto;
  background: white;
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 1rem;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}
.chat-empty {
  text-align: center;
  color: #999;
  padding: 4rem 0;
}

.chat-msg {
  display: flex;
  gap: 0.75rem;
  margin-bottom: 1rem;
}
.chat-msg-user {
  flex-direction: row-reverse;
}
.chat-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2rem;
  flex-shrink: 0;
  background: #f5f5f5;
}
.chat-bubble {
  max-width: 75%;
  padding: 0.75rem 1rem;
  border-radius: 12px;
  background: #f5f5f5;
  line-height: 1.6;
  font-size: 0.9rem;
}
.chat-msg-user .chat-bubble {
  background: #1a1a2e;
  color: white;
}
.chat-content {
  word-break: break-word;
}
.chat-content :deep(h3) {
  font-size: 1rem;
  margin: 0.5rem 0 0.25rem;
}

.chat-thinking {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  margin-bottom: 0.5rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px dashed #ddd;
}
.thinking-step {
  font-size: 0.8rem;
  color: #666;
  font-style: italic;
}

.chat-tools, .chat-tool-results {
  margin-top: 0.5rem;
  padding-top: 0.5rem;
  border-top: 1px dashed #ddd;
}
.tool-call, .tool-result {
  font-size: 0.8rem;
  padding: 0.2rem 0;
  color: #555;
  font-family: monospace;
}
.chat-msg-user .tool-call,
.chat-msg-user .tool-result {
  color: #ccc;
}

.chat-typing {
  color: #666;
}
.typing-dots span {
  animation: blink 1.4s infinite;
  font-size: 1.5rem;
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
  gap: 0.5rem;
  align-items: flex-end;
}
.chat-input {
  flex: 1;
  resize: none;
  min-height: 44px;
}
.send-btn {
  height: 44px;
  white-space: nowrap;
}
</style>
