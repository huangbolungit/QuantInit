import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useWebSocketStore = defineStore('websocket', () => {
  const isConnected = ref(false)
  const lastMessage = ref(null)
  const lastError = ref(null)

  let socket = null

  function resolveUrl() {
    if (typeof window === 'undefined') {
      return null
    }
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${protocol}//${window.location.host}/ws/realtime`
  }

  function connect(url) {
    if (socket && isConnected.value) {
      return
    }
    const target = url ?? resolveUrl()
    if (!target) {
      return
    }

    socket = new WebSocket(target)

    socket.onopen = () => {
      isConnected.value = true
      lastError.value = null
    }

    socket.onmessage = event => {
      lastMessage.value = event.data
    }

    socket.onerror = error => {
      lastError.value = error
    }

    socket.onclose = () => {
      isConnected.value = false
      socket = null
    }
  }

  function disconnect() {
    if (socket) {
      socket.close()
      socket = null
    }
    isConnected.value = false
  }

  function send(payload) {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      return false
    }
    const message = typeof payload === 'string' ? payload : JSON.stringify(payload)
    socket.send(message)
    return true
  }

  return {
    isConnected,
    lastMessage,
    lastError,
    connect,
    disconnect,
    send
  }
})
