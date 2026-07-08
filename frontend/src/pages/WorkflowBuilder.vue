<template>
  <div>
    <h1 class="page-title">Workflow Builder</h1>
    <p class="page-subtitle">编辑 DAG Workflow JSON 并执行</p>

    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem">
      <div class="card">
        <h3 style="margin-bottom: 0.5rem">Workflow Definition</h3>
        <textarea
          v-model="workflowJson"
          style="width: 100%; height: 300px; font-family: monospace; font-size: 0.85rem; padding: 0.5rem; border: 1px solid #ddd; border-radius: 4px"
        />
        <button
          @click="runWorkflow"
          :disabled="running"
          style="margin-top: 0.5rem; padding: 0.5rem 1.5rem; background: #1a1a2e; color: white; border: none; border-radius: 4px; cursor: pointer"
        >
          {{ running ? 'Running...' : 'Run Workflow' }}
        </button>
      </div>

      <div class="card">
        <h3 style="margin-bottom: 0.5rem">Result</h3>
        <p v-if="!result" style="color: #999">Click "Run Workflow" to execute</p>
        <pre v-if="result" style="background: #f0f0f0; padding: 1rem; border-radius: 4px; overflow: auto; max-height: 350px; font-size: 0.85rem">{{ JSON.stringify(result, null, 2) }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const DEFAULT_WORKFLOW = JSON.stringify({
  nodes: [
    { id: "planner", type: "agent", config: { agent_type: "planner" } },
    { id: "search", type: "tool", config: { tool: "web_search" } },
    { id: "writer", type: "agent", config: { agent_type: "writer" } },
  ],
  edges: [
    { source: "planner", target: "search" },
    { source: "search", target: "writer" },
  ],
}, null, 2)

const workflowJson = ref(DEFAULT_WORKFLOW)
const result = ref(null)
const running = ref(false)

const runWorkflow = async () => {
  running.value = true
  result.value = null
  try {
    const parsed = JSON.parse(workflowJson.value)
    const res = await fetch('/api/v1/workflow/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(parsed),
    })
    result.value = await res.json()
  } catch (e) {
    result.value = { error: e.message }
  }
  running.value = false
}
</script>
