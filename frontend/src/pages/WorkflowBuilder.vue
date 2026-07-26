<template>
  <div>
    <div class="page-actions">
      <h1 class="page-title" style="margin-bottom:0">{{ isEdit ? '编辑 Workflow' : '创建 Workflow' }}</h1>
      <div style="display:flex;gap:0.4rem">
        <button @click="saveWorkflow" class="btn btn-primary" :disabled="saving">{{ saving ? '保存中...' : '保存' }}</button>
        <router-link to="/workflows" class="btn btn-outline">返回</router-link>
      </div>
    </div>

    <div class="wf-meta" style="display:flex;gap:0.5rem;margin-bottom:0.5rem;align-items:center">
      <input v-model="wfName" class="form-input" placeholder="Workflow 名称" style="max-width:250px;font-size:0.8rem" />
      <input v-model="wfDesc" class="form-input" placeholder="描述（可选）" style="max-width:350px;font-size:0.8rem" />
    </div>

    <div class="wf-layout">
      <!-- Left: Node palette -->
      <div class="wf-palette">
        <div style="font-size:0.8rem;font-weight:600;margin-bottom:0.5rem">节点类型</div>
        <div v-for="nt in nodeTypes" :key="nt.type"
          class="palette-item"
          draggable="true"
          @dragstart="onDragStart($event, nt)">
          <span>{{ nt.icon }}</span>
          <span style="font-size:0.75rem">{{ nt.label }}</span>
        </div>
        <div style="margin-top:1rem;font-size:0.75rem;color:#999">
          将节点拖入画布<br>
          连接：从节点底部拉到另一个节点顶部
        </div>
      </div>

      <!-- Center: DAG Canvas -->
      <div class="wf-canvas" ref="canvasRef" @drop="onDrop" @dragover.prevent>
        <svg v-if="nodes.length" class="wf-svg" :width="svgW" :height="svgH">
          <!-- Edges -->
          <path v-for="(edge, ei) in edges" :key="ei"
            :d="edgePath(edge)"
            :stroke="edgeColor(edge)"
            stroke-width="2"
            fill="none"
            marker-end="url(#arrowhead)"
            class="wf-edge"
            @click="selectEdge(ei)"
          />
          <defs>
            <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
              <polygon points="0 0, 10 3.5, 0 7" fill="#888" />
            </marker>
          </defs>
        </svg>

        <!-- Nodes -->
        <div v-for="(node, ni) in nodes" :key="node.id"
          :class="['wf-node', { selected: selectedNode === ni }]"
          :style="{ left: node.x + 'px', top: node.y + 'px' }"
          @mousedown="startDrag($event, ni)"
          @click="selectNode(ni)">
          <div :class="['wf-node-header', 'wf-node-' + node.type]">
            <span>{{ nodeIcon(node.type) }}</span>
            <input v-model="node.name" class="wf-node-name" placeholder="节点名称" @click.stop @mousedown.stop />
          </div>
          <div class="wf-node-body">{{ nodeTypeLabel(node.type) }}</div>
          <!-- Connection ports -->
          <div class="wf-port wf-port-out" @mousedown.stop="startEdge($event, ni, 'out')" title="拖出连线"></div>
          <div class="wf-port wf-port-in" title="接收连线"></div>
        </div>

        <div v-if="!nodes.length" class="wf-empty">
          从左侧拖入节点开始构建
        </div>

        <!-- Edge config modal -->
        <div v-if="editingEdge !== null" class="wf-edge-modal" @click.stop>
          <div class="wf-edge-modal-content">
            <div style="font-size:0.85rem;font-weight:600;margin-bottom:0.5rem">边配置</div>
            <div style="font-size:0.75rem;margin-bottom:0.3rem">
              {{ edges[editingEdge].source }} → {{ edges[editingEdge].target }}
            </div>
            <div class="form-group">
              <label class="form-label">条件表达式</label>
              <input v-model="edges[editingEdge].condition" class="form-input" placeholder="如：nodes.result.output > 0" style="font-size:0.75rem" />
              <p class="form-hint">留空表示无条件</p>
            </div>
            <div style="display:flex;gap:0.3rem;justify-content:flex-end;margin-top:0.5rem">
              <button @click="deleteEdge(editingEdge)" class="btn btn-danger btn-sm">删除</button>
              <button @click="editingEdge = null" class="btn btn-outline btn-sm">完成</button>
            </div>
          </div>
        </div>
      </div>

      <!-- Right: Config panel -->
      <div class="wf-config" v-if="selectedNode !== null && nodes[selectedNode]">
        <div style="font-size:0.8rem;font-weight:600;margin-bottom:0.75rem">节点配置</div>

        <div class="form-group">
          <label class="form-label">节点 ID</label>
          <input v-model="nodes[selectedNode].id" class="form-input" style="font-size:0.75rem" placeholder="唯一标识" />
        </div>

        <div v-if="nodes[selectedNode].type === 'tool'">
          <div class="form-group">
            <label class="form-label">工具名</label>
            <input v-model="nodes[selectedNode].tool_name" class="form-input" style="font-size:0.75rem" placeholder="如：web_search" />
          </div>
          <div class="form-group">
            <label class="form-label">参数 (JSON)</label>
            <textarea v-model="nodes[selectedNode].tool_params" class="form-textarea" rows="4" style="font-size:0.75rem" placeholder='{"query": "{{ input.query }}"}' />
          </div>
        </div>

        <div v-if="nodes[selectedNode].type === 'agent'">
          <div class="form-group">
            <label class="form-label">Agent ID</label>
            <input v-model="nodes[selectedNode].agent_id" class="form-input" style="font-size:0.75rem" type="number" />
          </div>
          <div class="form-group">
            <label class="form-label">Prompt</label>
            <textarea v-model="nodes[selectedNode].prompt" class="form-textarea" rows="5" style="font-size:0.75rem" placeholder="分析以下内容: {{ input.code }}" />
          </div>
        </div>

        <div v-if="nodes[selectedNode].type === 'llm'">
          <div class="form-group">
            <label class="form-label">Prompt</label>
            <textarea v-model="nodes[selectedNode].prompt" class="form-textarea" rows="5" style="font-size:0.75rem" placeholder="总结: {{ input.content }}" />
          </div>
        </div>

        <div v-if="nodes[selectedNode].type === 'condition'">
          <div class="form-group">
            <label class="form-label">表达式</label>
            <input v-model="nodes[selectedNode].expression" class="form-input" style="font-size:0.75rem" placeholder="nodes.analysis.output > 5" />
            <p class="form-hint">满足条件的走 target edge，不满足的跳过</p>
          </div>
        </div>

        <div v-if="nodes[selectedNode].type === 'transform'">
          <div class="form-group">
            <label class="form-label">转换类型</label>
            <select v-model="nodes[selectedNode].transform_type" class="form-input" style="font-size:0.75rem">
              <option value="jsonpath">JSON Path</option>
              <option value="upper">大写</option>
              <option value="template">模板</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">表达式</label>
            <input v-model="nodes[selectedNode].expression" class="form-input" style="font-size:0.75rem" placeholder="nodes.result.output" />
          </div>
        </div>

        <div v-if="nodes[selectedNode].type === 'human'">
          <div class="form-group">
            <label class="form-label">审批标题</label>
            <input v-model="nodes[selectedNode].human_title" class="form-input" style="font-size:0.75rem" placeholder="请审批以下内容" />
          </div>
          <div class="form-group">
            <label class="form-label">审批人</label>
            <input v-model="nodes[selectedNode].human_assignee" class="form-input" style="font-size:0.75rem" placeholder="admin" />
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">错误策略</label>
          <select v-model="nodes[selectedNode].error_strategy" class="form-input" style="font-size:0.75rem">
            <option value="fail">失败即终止</option>
            <option value="skip">跳过继续</option>
            <option value="retry">重试</option>
          </select>
        </div>

        <div class="form-group">
          <label class="form-label">超时 (秒)</label>
          <input v-model="nodes[selectedNode].timeout" class="form-input" style="font-size:0.75rem" type="number" placeholder="120" />
        </div>

        <div style="display:flex;gap:0.3rem;margin-top:1rem">
          <button @click="deleteNode(selectedNode)" class="btn btn-danger btn-sm">删除节点</button>
        </div>
      </div>
      <div v-else class="wf-config wf-config-empty">
        <p style="color:#999;font-size:0.8rem;text-align:center;padding:2rem 0">点击节点编辑配置</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const isEdit = computed(() => !!route.params.id)
const saving = ref(false)
const canvasRef = ref(null)
const selectedNode = ref(null)
const editingEdge = ref(null)
const svgW = ref(2000)
const svgH = ref(2000)

const nodeTypes = [
  { type: 'tool', label: 'Tool', icon: '🔧' },
  { type: 'agent', label: 'Agent', icon: '🤖' },
  { type: 'llm', label: 'LLM', icon: '⚡' },
  { type: 'condition', label: '条件', icon: '🔀' },
  { type: 'transform', label: '转换', icon: '🔄' },
  { type: 'human', label: '人工', icon: '✋' },
  { type: 'skill', label: 'Skill', icon: '📘' },
]

const wfName = ref('')
const wfDesc = ref('')
const nodes = ref([])
const edges = ref([])

let nodeIdCounter = 1
let dragNodeIdx = null
let edgeStartNode = null

function nodeIcon(type) {
  const n = nodeTypes.find(nt => nt.type === type)
  return n ? n.icon : '📦'
}

function nodeTypeLabel(type) {
  const n = nodeTypes.find(nt => nt.type === type)
  return n ? n.label : type
}

function onDragStart(event, nt) {
  event.dataTransfer.setData('node-type', nt.type)
}

function onDrop(event) {
  const type = event.dataTransfer.getData('node-type')
  if (!type) return
  const rect = canvasRef.value.getBoundingClientRect()
  const x = event.clientX - rect.left - 75
  const y = event.clientY - rect.top - 20
  nodes.value.push({
    id: `node_${nodeIdCounter++}`,
    type,
    name: type,
    x: Math.max(0, x),
    y: Math.max(0, y),
    // config fields
    tool_name: '',
    tool_params: '',
    agent_id: null,
    prompt: '',
    expression: '',
    transform_type: 'jsonpath',
    human_title: '',
    human_assignee: 'admin',
    error_strategy: 'fail',
    timeout: 120,
    input_mapping: {},
  })
}

function startDrag(event, ni) {
  dragNodeIdx = ni
  const node = nodes.value[ni]
  const offsetX = event.clientX - node.x
  const offsetY = event.clientY - node.y
  function onMove(e) {
    nodes.value[ni].x = Math.max(0, e.clientX - offsetX)
    nodes.value[ni].y = Math.max(0, e.clientY - offsetY)
  }
  function onUp() {
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
  }
  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
}

function selectNode(ni) {
  selectedNode.value = ni
  editingEdge.value = null
}

function selectEdge(ei) {
  editingEdge.value = ei
  selectedNode.value = null
}

function startEdge(event, ni, port) {
  if (port === 'out') {
    edgeStartNode = ni
    const onUp = (e) => {
      document.removeEventListener('mouseup', onUp)
      // Find which node we're over
      const el = document.elementFromPoint(e.clientX, e.clientY)
      // Just try to find a nearby node
      if (edgeStartNode !== null) {
        // Simple heuristic: find closest node
        let closest = -1
        let minDist = 50
        for (let i = 0; i < nodes.value.length; i++) {
          if (i === edgeStartNode) continue
          const n = nodes.value[i]
          const cx = n.x + 75
          const cy = n.y
          const dist = Math.sqrt((e.clientX - cx) ** 2 + (e.clientY - cy) ** 2)
          if (dist < minDist) {
            minDist = dist
            closest = i
          }
        }
        if (closest >= 0) {
          const src = nodes.value[edgeStartNode].id
          const tgt = nodes.value[closest].id
          if (!edges.value.some(e => e.source === src && e.target === tgt)) {
            edges.value.push({ source: src, target: tgt, condition: '' })
          }
        }
      }
      edgeStartNode = null
    }
    document.addEventListener('mouseup', onUp)
  }
}

function edgePath(edge) {
  const src = nodes.value.find(n => n.id === edge.source)
  const tgt = nodes.value.find(n => n.id === edge.target)
  if (!src || !tgt) return ''
  const x1 = src.x + 75
  const y1 = src.y + 48
  const x2 = tgt.x + 75
  const y2 = tgt.y
  const cy = (y1 + y2) / 2
  return `M${x1},${y1} C${x1},${cy} ${x2},${cy} ${x2},${y2}`
}

function edgeColor(edge) {
  if (edge.condition) return '#e65100'
  return '#888'
}

function deleteNode(ni) {
  const nid = nodes.value[ni].id
  nodes.value.splice(ni, 1)
  edges.value = edges.value.filter(e => e.source !== nid && e.target !== nid)
  selectedNode.value = null
}

function deleteEdge(ei) {
  edges.value.splice(ei, 1)
  editingEdge.value = null
}

function toWorkflowDef() {
  return {
    nodes: nodes.value.map(n => ({
      id: n.id,
      type: n.type,
      config: {
        type: n.type,
        name: n.name,
        input_mapping: n.input_mapping || {},
        error_strategy: n.error_strategy,
        timeout: n.timeout,
        retry_max: n.error_strategy === 'retry' ? 3 : 1,
        config: n.type === 'tool' ? {
          tool_name: n.tool_name,
          params: n.tool_params ? JSON.parse(n.tool_params.replace(/{{/g, '"{{').replace(/}}/g, '}}"')) : {},
        } : n.type === 'agent' ? {
          agent_id: n.agent_id ? parseInt(n.agent_id) : null,
          prompt: n.prompt,
        } : n.type === 'llm' ? {
          prompt: n.prompt,
        } : n.type === 'condition' ? {
          expression: n.expression,
        } : n.type === 'transform' ? {
          transform_type: n.transform_type,
          expression: n.expression,
        } : n.type === 'human' ? {
          title: n.human_title,
          assignee: n.human_assignee,
        } : {},
      },
    })),
    edges: edges.value.map(e => ({
      source: e.source,
      target: e.target,
      condition: e.condition || null,
    })),
  }
}

function fromWorkflowDef(def) {
  nodes.value = (def.nodes || []).map(n => {
    const c = n.config || {}
    const cc = c.config || {}
    return {
      id: n.id,
      type: c.type || n.type,
      name: c.name || n.id,
      x: c.x || 100 + Math.random() * 200,
      y: c.y || 100 + Math.random() * 200,
      tool_name: cc.tool_name || '',
      tool_params: cc.params ? JSON.stringify(cc.params) : '',
      agent_id: cc.agent_id || null,
      prompt: cc.prompt || '',
      expression: cc.expression || '',
      transform_type: cc.transform_type || 'jsonpath',
      human_title: cc.title || '',
      human_assignee: cc.assignee || 'admin',
      error_strategy: c.error_strategy || 'fail',
      timeout: c.timeout || 120,
      input_mapping: c.input_mapping || {},
    }
  })
  edges.value = (def.edges || []).map(e => ({
    source: e.source,
    target: e.target,
    condition: e.condition || '',
  }))
  nodeIdCounter = nodes.value.length + 1
}

async function saveWorkflow() {
  saving.value = true
  const def = toWorkflowDef()
  const payload = {
    name: wfName.value || '未命名 Workflow',
    description: wfDesc.value || '',
    definition: def,
  }
  try {
    const url = isEdit.value
      ? `/api/v1/admin/workflows/${route.params.id}`
      : '/api/v1/admin/workflows'
    const method = isEdit.value ? 'PUT' : 'POST'
    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    const data = await res.json()
    if (data.id || data.name) {
      router.push('/workflows')
    } else {
      alert('保存失败: ' + (data.detail || 'Unknown'))
    }
  } catch (e) {
    alert('保存失败: ' + e.message)
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  if (isEdit.value) {
    try {
      const res = await fetch(`/api/v1/admin/workflows/${route.params.id}`)
      const data = await res.json()
      wfName.value = data.name || ''
      wfDesc.value = data.description || ''
      if (data.definition) fromWorkflowDef(data.definition)
    } catch { /* ignore */ }
  }
})

// Watch for node positions to update SVG
watch([nodes, edges], () => {
  nextTick(() => {
    if (nodes.value.length) {
      const maxX = Math.max(...nodes.value.map(n => n.x + 200))
      const maxY = Math.max(...nodes.value.map(n => n.y + 100))
      svgW.value = Math.max(2000, maxX)
      svgH.value = Math.max(2000, maxY)
    }
  })
}, { deep: true })
</script>

<style scoped>
.wf-layout { display: flex; gap: 0.5rem; height: calc(100vh - 120px); min-height: 500px; }

.wf-palette {
  width: 120px; flex-shrink: 0;
  background: white; border-radius: 6px; box-shadow: 0 1px 2px rgba(0,0,0,0.06);
  padding: 0.75rem; overflow-y: auto;
}
.palette-item {
  display: flex; align-items: center; gap: 0.3rem;
  padding: 0.4rem 0.5rem; margin-bottom: 0.2rem;
  border-radius: 4px; cursor: grab; font-size: 0.75rem;
  background: #f8f8f8; border: 1px solid #eee;
}
.palette-item:hover { background: #eef2ff; border-color: #c5cae9; }

.wf-canvas {
  flex: 1; position: relative; overflow: auto;
  background: #fafafa; border-radius: 6px;
  border: 1px solid #eee; min-width: 0;
}
.wf-svg { position: absolute; top: 0; left: 0; pointer-events: none; }
.wf-edge { cursor: pointer; pointer-events: stroke; }
.wf-edge:hover { stroke: #e65100; stroke-width: 3; }

.wf-node {
  position: absolute; width: 150px;
  background: white; border-radius: 6px;
  box-shadow: 0 2px 6px rgba(0,0,0,0.1);
  cursor: move; z-index: 10;
  border: 2px solid transparent;
}
.wf-node:hover { box-shadow: 0 3px 12px rgba(0,0,0,0.15); }
.wf-node.selected { border-color: #1a1a2e; }
.wf-node-header {
  display: flex; align-items: center; gap: 0.3rem;
  padding: 0.3rem 0.5rem; border-radius: 4px 4px 0 0;
  font-size: 0.75rem; color: white;
}
.wf-node-tool { background: #1565c0; }
.wf-node-agent { background: #2e7d32; }
.wf-node-llm { background: #e65100; }
.wf-node-condition { background: #6a1b9a; }
.wf-node-transform { background: #00838f; }
.wf-node-human { background: #c62828; }
.wf-node-skill { background: #4e342e; }

.wf-node-name {
  background: transparent; border: none; color: white;
  font-size: 0.72rem; font-weight: 500; flex: 1;
  outline: none; padding: 0;
}
.wf-node-body { padding: 0.35rem 0.5rem; font-size: 0.68rem; color: #666; }
.wf-port {
  position: absolute; width: 10px; height: 10px;
  background: #ccc; border: 2px solid white;
  border-radius: 50%; cursor: crosshair;
}
.wf-port-out { bottom: -5px; left: 50%; margin-left: -5px; background: #888; }
.wf-port-in { top: -5px; left: 50%; margin-left: -5px; background: #bbb; }
.wf-port:hover { background: #1a1a2e; }

.wf-empty {
  text-align: center; color: #bbb; font-size: 0.85rem;
  padding: 4rem 2rem;
}

.wf-edge-modal {
  position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
  z-index: 100; background: white; border-radius: 6px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.2); padding: 1rem;
  min-width: 250px;
}

.wf-config { width: 220px; background: white; border-radius: 6px; box-shadow: 0 1px 2px rgba(0,0,0,0.06); padding: 0.75rem; overflow-y: auto; flex-shrink: 0; }
.wf-config-empty { display: flex; align-items: center; justify-content: center; }
</style>
