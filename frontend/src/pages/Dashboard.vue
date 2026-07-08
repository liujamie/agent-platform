<template>
  <div>
    <h1 class="page-title">Dashboard</h1>
    <p class="page-subtitle">Agent Platform 运行状态概览</p>

    <div class="grid-4">
      <div class="card">
        <div class="card-title">已注册工具</div>
        <div class="card-value">{{ tools.length }}</div>
      </div>
    </div>

    <div class="card">
      <h3 style="margin-bottom: 1rem">Available Tools</h3>
      <p v-if="tools.length === 0" style="color: #999">No tools registered</p>
      <div v-for="t in tools" :key="t.name" style="padding: 0.5rem 0; border-bottom: 1px solid #eee">
        <strong>{{ t.name }}</strong>
        <p style="color: #666; font-size: 0.85rem">{{ t.description }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const tools = ref([])

onMounted(async () => {
  try {
    const res = await fetch('/api/v1/tool/list')
    const data = await res.json()
    tools.value = data.tools || []
  } catch {
    tools.value = []
  }
})
</script>
