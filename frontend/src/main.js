import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import Dashboard from './pages/Dashboard.vue'
import Agents from './pages/Agents.vue'
import AgentForm from './pages/AgentForm.vue'
import Workflows from './pages/Workflows.vue'
import WorkflowForm from './pages/WorkflowForm.vue'
import WorkflowRun from './pages/WorkflowRun.vue'
import Logs from './pages/Logs.vue'
import Models from './pages/Models.vue'
import Chat from './pages/Chat.vue'
import Tools from './pages/Tools.vue'
import Skills from './pages/Skills.vue'
import SkillGuide from './pages/SkillGuide.vue'
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
  { path: '/models', component: Models },
  { path: '/chat', component: Chat },
  { path: '/tools', component: Tools },
  { path: '/skills', component: Skills },
  { path: '/skills/guide', component: SkillGuide },
  { path: '/workflows/runs/:trace_id', component: WorkflowRun },
]

const router = createRouter({ history: createWebHistory(), routes })
createApp(App).use(router).mount('#app')
