<template>
  <header class="app-header">
    <div class="app-header__brand">
      <span class="app-header__logo">A股智能投顾助手</span>
      <small class="app-header__subtitle">量化洞察 · 实时决策</small>
    </div>
    <nav class="app-header__nav">
      <RouterLink to="/">概览</RouterLink>
      <RouterLink to="/strategies">策略管理</RouterLink>
      <RouterLink to="/optimization">策略优化</RouterLink>
    </nav>
  </header>
</template>

<script setup>
import { RouterLink } from 'vue-router'
</script>

<style scoped>
.app-header {
  height: 60px;
  padding: 0 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #161b22;
  border-bottom: 1px solid #30363d;
}

.app-header__brand {
  display: flex;
  flex-direction: column;
}

.app-header__logo {
  font-weight: 600;
  font-size: 18px;
}

.app-header__subtitle {
  font-size: 12px;
  color: #8b949e;
}

.app-header__nav a {
  color: #c9d1d9;
  text-decoration: none;
  margin-left: 16px;
  font-size: 14px;
}

.app-header__nav a.router-link-active {
  color: #58a6ff;
}
</style>
