<template>
  <div id="app">
    <Header />
    <main class="main-content">
      <router-view />
    </main>
    <NotificationContainer />
  </div>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import { useMarketStore } from '@/stores/market'
import { useWebSocketStore } from '@/stores/websocket'
import Header from '@/components/common/Header.vue'
import NotificationContainer from '@/components/common/NotificationContainer.vue'

const marketStore = useMarketStore()
const wsStore = useWebSocketStore()

onMounted(async () => {
  // 初始化WebSocket连接
  wsStore.connect()

  // 获取初始市场数据
  await marketStore.initializeMarketData()

  // 启动定时刷新
  marketStore.startAutoRefresh()
})

onUnmounted(() => {
  // 清理定时器和连接
  marketStore.stopAutoRefresh()
  wsStore.disconnect()
})
</script>

<style lang="scss">
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: var(--font-family, 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', '微软雅黑', Arial, sans-serif);
  background-color: var(--bg-color, #ffffff);
  color: var(--text-primary, #303133);
  overflow-x: hidden;
}

#app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.main-content {
  flex: 1;
  height: calc(100vh - 60px); /* 减去header高度 */
  overflow-y: auto;
}

/* 自定义滚动条 */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: #1c2128;
}

::-webkit-scrollbar-thumb {
  background: #30363d;
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: #484f58;
}

/* 全局工具类 */
.text-success {
  color: #238636 !important;
}

.text-danger {
  color: #da3633 !important;
}

.text-warning {
  color: #d29922 !important;
}

.text-info {
  color: #1f6feb !important;
}

.text-muted {
  color: #8b949e !important;
}

.bg-card {
  background-color: #161b22;
  border: 1px solid #30363d;
  border-radius: 6px;
  padding: 16px;
}

.clickable {
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    opacity: 0.8;
  }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.3s ease;
}

.slide-up-enter-from {
  transform: translateY(20px);
  opacity: 0;
}

.slide-up-leave-to {
  transform: translateY(-20px);
  opacity: 0;
}
</style>