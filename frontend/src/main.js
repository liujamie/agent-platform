import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import Dashboard from './pages/Dashboard.vue'
import Agents from './pages/Agents.vue'
import AgentForm from './pages/AgentForm.vue'
import Workflows from './pages/Workflows.vue'
import WorkflowForm from './pages/WorkflowForm.vue'
import Logs from './pages/Logs.vue'
import './style.css'

const routes = [
  { path: '/', component: Dashboard },
  { path: '/agents', component: Agents },
  { path: '/agents/new', component: AgentForm },
  { path: '/agents/:id/edit', component: AgentForm },
  { path: '/workflows', component: Workflows },
  { path: '/workflows/new', component: WorkflowForm },
  { path: '/workflows/:id/edit', component: WorkflowForm },
  { path: '/logs', component: Logs },
]

const router = createRouter({ history: createWebHistory(), routes })
createApp(App).use(router).mount('#app')
