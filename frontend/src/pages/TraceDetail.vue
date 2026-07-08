<template>
  <div>
    <h1 class="page-title">Trace Detail</h1>
    <p class="page-subtitle">查看 Agent/Workflow 执行链路</p>

    <div class="card">
      <h3>Search Trace</h3>
      <p style="font-size: 0.85rem; color: #666; margin-bottom: 0.5rem">
        Enter a trace ID from a Workflow or Agent execution
      </p>
      <div style="display: flex; gap: 0.5rem">
        <input
          v-model="traceId"
          placeholder="Enter trace ID..."
          style="flex: 1; padding: 0.5rem; border: 1px solid #ddd; border-radius: 4px"
        />
        <button
          @click="fetchTrace"
          style="padding: 0.5rem 1.5rem; background: #1a1a2e; color: white; border: none; border-radius: 4px; cursor: pointer"
        >
          Search
        </button>
      </div>
    </div>

    <div v-if="trace" class="card">
      <h3>Trace Details</h3>
      <pre style="background: #f0f0f0; padding: 1rem; border-radius: 4px; overflow: auto; font-size: 0.85rem">{{ JSON.stringify(trace, null, 2) }}</pre>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const traceId = ref('')
const trace = ref(null)

const fetchTrace = async () => {
  if (!traceId.value.trim()) return
  try {
    const res = await fetch(`/api/v1/workflow/${traceId.value}/trace`)
    trace.value = await res.json()
  } catch (e) {
    trace.value = { error: e.message }
  }
}
</script>
