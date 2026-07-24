<template>
  <div class="app-layout">
    <aside class="sidebar">
      <div class="sidebar-title">Agent Platform</div>
      <nav class="sidebar-nav">
        <router-link to="/">Dashboard</router-link>
        <router-link to="/agents">Agents</router-link>
        <router-link to="/workflows">Workflows</router-link>
        <router-link to="/models">Models</router-link>
        <router-link to="/tools">Tools</router-link>
        <router-link to="/chat">Chat</router-link>
        <router-link to="/skills">Skills</router-link>
        <router-link to="/logs">Logs</router-link>
      </nav>
    </aside>
    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>
