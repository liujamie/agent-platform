import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import Dashboard from './pages/Dashboard.vue'
import WorkflowBuilder from './pages/WorkflowBuilder.vue'
import TraceDetail from './pages/TraceDetail.vue'
import './style.css'

const routes = [
  { path: '/', component: Dashboard },
  { path: '/workflow', component: WorkflowBuilder },
  { path: '/trace', component: TraceDetail },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

createApp(App).use(router).mount('#app')
