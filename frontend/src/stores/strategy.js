/**
 * 策略状态管理
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import strategyService from '@/services/strategy.js'

export const useStrategyStore = defineStore('strategy', () => {
  // 状态
  const strategies = ref([])
  const currentStrategy = ref(null)
  const signals = ref([])
  const latestSignals = ref([])
  const performanceData = ref({})
  const loading = ref(false)
  const error = ref(null)

  // 计算属性
  const activeStrategies = computed(() =>
    strategies.value.filter(strategy => strategy.status === 'active')
  )

  const inactiveStrategies = computed(() =>
    strategies.value.filter(strategy => strategy.status !== 'active')
  )

  const strategyCount = computed(() => strategies.value.length)

  const latestBuySignals = computed(() =>
    latestSignals.value.filter(signal => signal.signal_type === 'buy')
  )

  const latestSellSignals = computed(() =>
    latestSignals.value.filter(signal => signal.signal_type === 'sell')
  )

  // 动作
  async function fetchStrategies() {
    loading.value = true
    error.value = null

    try {
      const data = await strategyService.getStrategies()
      strategies.value = data
    } catch (err) {
      error.value = '获取策略列表失败: ' + err.message
      console.error('获取策略列表失败:', err)
    } finally {
      loading.value = false
    }
  }

  async function fetchStrategy(strategyId) {
    loading.value = true
    error.value = null

    try {
      const data = await strategyService.getStrategy(strategyId)
      currentStrategy.value = data
      return data
    } catch (err) {
      error.value = '获取策略详情失败: ' + err.message
      console.error('获取策略详情失败:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createStrategy(strategyData) {
    loading.value = true
    error.value = null

    try {
      const data = await strategyService.createStrategy(strategyData)
      strategies.value.push(data)
      return data
    } catch (err) {
      error.value = '创建策略失败: ' + err.message
      console.error('创建策略失败:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateStrategy(strategyId, updateData) {
    loading.value = true
    error.value = null

    try {
      const data = await strategyService.updateStrategy(strategyId, updateData)

      // 更新策略列表中的对应项
      const index = strategies.value.findIndex(s => s.id === strategyId)
      if (index !== -1) {
        strategies.value[index] = data
      }

      // 如果是当前策略，也更新当前策略
      if (currentStrategy.value?.id === strategyId) {
        currentStrategy.value = data
      }

      return data
    } catch (err) {
      error.value = '更新策略失败: ' + err.message
      console.error('更新策略失败:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteStrategy(strategyId) {
    loading.value = true
    error.value = null

    try {
      await strategyService.deleteStrategy(strategyId)

      // 从策略列表中移除
      strategies.value = strategies.value.filter(s => s.id !== strategyId)

      // 如果是当前策略，清空当前策略
      if (currentStrategy.value?.id === strategyId) {
        currentStrategy.value = null
      }

      return true
    } catch (err) {
      error.value = '删除策略失败: ' + err.message
      console.error('删除策略失败:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function generateSignals(strategyId) {
    loading.value = true
    error.value = null

    try {
      const data = await strategyService.generateSignals(strategyId)
      signals.value = data
      return data
    } catch (err) {
      error.value = '生成信号失败: ' + err.message
      console.error('生成信号失败:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchStrategySignals(strategyId, limit = 100) {
    loading.value = true
    error.value = null

    try {
      const data = await strategyService.getStrategySignals(strategyId, limit)
      signals.value = data
      return data
    } catch (err) {
      error.value = '获取策略信号失败: ' + err.message
      console.error('获取策略信号失败:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchLatestSignals(limit = 50, strategyId = null) {
    loading.value = true
    error.value = null

    try {
      const data = await strategyService.getLatestSignals(limit, strategyId)
      latestSignals.value = data
      return data
    } catch (err) {
      error.value = '获取最新信号失败: ' + err.message
      console.error('获取最新信号失败:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchStrategyPerformance(strategyId) {
    loading.value = true
    error.value = null

    try {
      const data = await strategyService.getStrategyPerformance(strategyId)
      performanceData.value = { ...performanceData.value, [strategyId]: data }
      return data
    } catch (err) {
      error.value = '获取策略性能失败: ' + err.message
      console.error('获取策略性能失败:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function optimizeParameters(strategyId, optimizationConfig) {
    loading.value = true
    error.value = null

    try {
      const data = await strategyService.optimizeParameters(strategyId, optimizationConfig)

      // 重新获取策略信息
      await fetchStrategy(strategyId)

      return data
    } catch (err) {
      error.value = '参数优化失败: ' + err.message
      console.error('参数优化失败:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  // 工具函数
  function clearError() {
    error.value = null
  }

  function setCurrentStrategy(strategy) {
    currentStrategy.value = strategy
  }

  function getStrategyPerformance(strategyId) {
    return performanceData.value[strategyId] || {}
  }

  function reset() {
    strategies.value = []
    currentStrategy.value = null
    signals.value = []
    latestSignals.value = []
    performanceData.value = {}
    loading.value = false
    error.value = null
  }

  return {
    // 状态
    strategies,
    currentStrategy,
    signals,
    latestSignals,
    performanceData,
    loading,
    error,

    // 计算属性
    activeStrategies,
    inactiveStrategies,
    strategyCount,
    latestBuySignals,
    latestSellSignals,

    // 动作
    fetchStrategies,
    fetchStrategy,
    createStrategy,
    updateStrategy,
    deleteStrategy,
    generateSignals,
    fetchStrategySignals,
    fetchLatestSignals,
    fetchStrategyPerformance,
    optimizeParameters,

    // 工具函数
    clearError,
    setCurrentStrategy,
    getStrategyPerformance,
    reset
  }
})