<template>
  <div class="app-layout">
    <nav class="nav">
      <div class="nav-title">Agent Platform</div>
      <div class="nav-links">
        <router-link to="/">Dashboard</router-link>
        <router-link to="/agents">Agents</router-link>
        <router-link to="/workflows">Workflows</router-link>
        <router-link to="/logs">Logs</router-link>
      </div>
    </nav>
    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>
