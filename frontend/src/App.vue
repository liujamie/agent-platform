<template>
  <div class="app-layout">
    <nav class="nav">
      <div class="nav-title">Agent Platform</div>
      <div class="nav-links">
        <router-link to="/">Dashboard</router-link>
        <router-link to="/workflow">Workflow</router-link>
        <router-link to="/trace">Traces</router-link>
      </div>
    </nav>
    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>
