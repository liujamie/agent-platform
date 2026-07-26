<template>
  <div>
    <div class="page-actions">
      <h1 class="page-title" style="margin-bottom:0">Workflow 执行详情</h1>
      <router-link to="/workflows" class="btn btn-outline">← 返回</router-link>
    </div>

    <div v-if="loading" style="text-align:center;padding:2rem;color:#999">加载中...</div>

    <div v-if="instance">
      <!-- Summary card -->
      <div class="card" style="display:flex;gap:2rem;align-items:center;padding:0.75rem 1rem">
        <div>
          <div style="font-size:0.7rem;color:#999">状态</div>
          <span :class="['badge', instance.status === 'success' ? 'badge-success' : instance.status === 'running' ? 'badge-active' : 'badge-error']" style="font-size:0.85rem;margin-top:0.2rem">
            {{ instance.status === 'success' ? '✅ 成功' : instance.status === 'running' ? '⏳ 运行中' : '❌ 失败' }}
          </span>
        </div>
        <div>
          <div style="font-size:0.7rem;color:#999">Trace ID</div>
          <code style="font-size:0.75rem">{{ instance.trace_id }}</code>
        </div>
        <div>
          <div style="font-size:0.7rem;color:#999">耗时</div>
          <div style="font-size:0.85rem;font-weight:600">{{ instance.duration_ms }}ms</div>
        </div>
        <div>
          <div style="font-size:0.7rem;color:#999">触发</div>
          <div style="font-size:0.85rem">{{ instance.trigger_type }}</div>
        </div>
        <div>
          <div style="font-size:0.7rem;color:#999">开始</div>
          <div style="font-size:0.85rem">{{ instance.started_at }}</div>
        </div>
      </div>

      <!-- Nodes execution timeline -->
      <div style="margin-top:1rem">
        <h3 style="font-size:0.85rem;margin-bottom:0.5rem">节点执行</h3>
        <table class="data-table">
          <thead>
            <tr>
              <th>节点</th>
              <th>类型</th>
              <th>状态</th>
              <th>耗时</th>
              <th>重试</th>
              <th>错误</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="n in instance.node_executions" :key="n.node_id">
              <td><strong style="font-size:0.8rem">{{ n.node_name || n.node_id }}</strong></td>
              <td><code style="font-size:0.72rem">{{ n.node_type }}</code></td>
              <td>
                <span :class="['badge', n.status === 'success' ? 'badge-success' : n.status === 'running' ? 'badge-active' : n.status === 'skipped' ? 'badge-archived' : 'badge-error']">{{ n.status }}</span>
              </td>
              <td style="font-size:0.8rem">{{ n.duration_ms }}ms</td>
              <td style="font-size:0.8rem">{{ n.retry_count > 0 ? n.retry_count + '次' : '-' }}</td>
              <td style="font-size:0.75rem;color:#c62828;max-width:200px;overflow:hidden;text-overflow:ellipsis">{{ n.error || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- DAG Visualization -->
      <div class="card" style="margin-top:1rem">
        <h3 style="font-size:0.85rem;margin-bottom:0.5rem">执行图</h3>
        <div class="dag-viz" ref="dagRef" style="position:relative;height:300px;background:#fafafa;border-radius:4px;overflow:hidden">
          <svg :width="dagSvgW" :height="dagSvgH" style="position:absolute;top:0;left:0">
            <path v-for="(edge, ei) in dagEdges" :key="ei"
              :d="edge.path" stroke="#ccc" stroke-width="2" fill="none"
              :stroke-dasharray="edge.condition ? '5,3' : 'none'"
            />
          </svg>
          <div v-for="(n, ni) in dagNodes" :key="n.id"
            :style="{ position:'absolute', left:n.x+'px', top:n.y+'px', width:'120px' }"
            :class="['dag-node', 'dag-node-' + (n.status||'pending')]">
            <div style="font-size:0.7rem;font-weight:500;padding:0.15rem 0.3rem">{{ n.name || n.id }}</div>
            <div style="font-size:0.6rem;color:#999;padding:0 0.3rem 0.15rem">{{ n.type }}</div>
          </div>
        </div>
      </div>

      <!-- Input/Output -->
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem;margin-top:1rem">
        <div class="card">
          <h3 style="font-size:0.8rem;margin-bottom:0.3rem">输入</h3>
          <pre style="font-size:0.72rem;background:#f5f5f5;padding:0.5rem;border-radius:4px;max-height:200px;overflow:auto">{{ JSON.stringify(instance.input_data, null, 2) }}</pre>
        </div>
        <div class="card">
          <h3 style="font-size:0.8rem;margin-bottom:0.3rem">输出</h3>
          <pre style="font-size:0.72rem;background:#f5f5f5;padding:0.5rem;border-radius:4px;max-height:200px;overflow:auto">{{ JSON.stringify(instance.output_data, null, 2) }}</pre>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const loading = ref(true)
const instance = ref(null)
const dagNodes = ref([])
const dagEdges = ref([])
const dagSvgW = ref(800)
const dagSvgH = ref(300)

onMounted(async () => {
  const traceId = route.params.trace_id
  try {
    const res = await fetch(`/api/v1/workflow/instances/${traceId}`)
    instance.value = await res.json()
    buildDag()
  } catch { /* ignore */ }
  finally { loading.value = false }
})

function buildDag() {
  const inst = instance.value
  if (!inst || !inst.node_executions) return

  const nodes = []
  const execs = inst.node_executions || []

  // Layout in order
  const cols = 4
  execs.forEach((n, i) => {
    nodes.push({
      id: n.node_id,
      name: n.node_name || n.node_id,
      type: n.node_type,
      status: n.status,
      x: 20 + (i % cols) * 150,
      y: 20 + Math.floor(i / cols) * 70,
    })
  })
  dagNodes.value = nodes

  // Inferred edges: connect consecutive nodes
  const edges = []
  for (let i = 0; i < execs.length - 1; i++) {
    edges.push({
      path: `M${nodes[i].x + 60},${nodes[i].y + 50} C${nodes[i].x + 60},${nodes[i].y + 70} ${nodes[i+1].x + 60},${nodes[i+1].y - 10} ${nodes[i+1].x + 60},${nodes[i+1].y}`,
      condition: '',
    })
  }
  dagEdges.value = edges

  if (nodes.length) {
    dagSvgW.value = Math.max(800, (cols) * 150 + 100)
    dagSvgH.value = Math.max(300, Math.ceil(execs.length / cols) * 70 + 50)
  }
}
</script>

<style scoped>
.dag-node {
  background: white; border-radius: 4px;
  border: 2px solid #e0e0e0; font-size:0.75rem;
  cursor: default;
}
.dag-node-success { border-color: #4caf50; background: #e8f5e9; }
.dag-node-failed { border-color: #f44336; background: #fbe9e7; }
.dag-node-running { border-color: #2196f3; background: #e3f2fd; animation: pulse 1s infinite; }
.dag-node-skipped { border-color: #e0e0e0; opacity: 0.5; }
@keyframes pulse {
  0% { box-shadow: 0 0 0 0 rgba(33,150,243,0.4); }
  70% { box-shadow: 0 0 0 6px rgba(33,150,243,0); }
  100% { box-shadow: 0 0 0 0 rgba(33,150,243,0); }
}
</style>
