<template>
  <aside class="notification-container">
    <div class="notification-container__status">
      <span class="dot" :class="{ online: isConnected }"></span>
      <span>{{ connectionText }}</span>
    </div>
    <div v-if="lastMessage" class="notification-container__message">
      <span class="label">最新推送</span>
      <span class="content">{{ lastMessage }}</span>
    </div>
    <div v-else class="notification-container__message muted">
      <span>暂无实时推送</span>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { useWebSocketStore } from '@/stores/websocket'

const wsStore = useWebSocketStore()

const isConnected = computed(() => wsStore.isConnected)
const lastMessage = computed(() => wsStore.lastMessage)
const connectionText = computed(() => (isConnected.value ? '实时连接已建立' : '实时连接未建立'))
</script>

<style scoped>
.notification-container {
  width: 260px;
  padding: 16px;
  background: #161b22;
  border-left: 1px solid #30363d;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.notification-container__status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #c9d1d9;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #8b949e;
  display: inline-block;
}

.dot.online {
  background: #2ea043;
}

.notification-container__message {
  font-size: 13px;
  line-height: 1.5;
  color: #c9d1d9;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.notification-container__message .label {
  font-size: 12px;
  color: #8b949e;
  text-transform: uppercase;
  letter-spacing: 0.6px;
}

.notification-container__message .content {
  word-break: break-all;
}

.notification-container__message.muted {
  color: #8b949e;
  font-style: italic;
}
</style>
