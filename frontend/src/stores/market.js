import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { marketApi } from '@/services/api'
import dayjs from 'dayjs'

export const useMarketStore = defineStore('market', () => {
  // 状态
  const overview = ref({})
  const sectors = ref([])
  const selectedSector = ref(null)
  const sectorStocks = ref([])
  const northboundFunds = ref({})
  const heatmap = ref([])
  const isLoading = ref(false)
  const lastUpdate = ref(null)

  // 计算属性
  const marketStats = computed(() => {
    if (!overview.value || Object.keys(overview.value).length === 0) {
      return {
        upCount: 0,
        downCount: 0,
        limitUp: 0,
        limitDown: 0,
        totalTurnover: 0,
        marketSentiment: 'neutral'
      }
    }

    // 模拟计算市场统计数据
    const upCount = 3520
    const downCount = 1580
    const limitUp = 85
    const limitDown = 12
    const totalTurnover = 8500
    const marketSentiment = upCount > downCount * 2 ? 'bullish' :
                          downCount > upCount * 2 ? 'bearish' : 'neutral'

    return {
      upCount,
      downCount,
      limitUp,
      limitDown,
      totalTurnover,
      marketSentiment
    }
  })

  const topSectors = computed(() => {
    return sectors.value
      .filter(sector => sector.change_pct > 0)
      .sort((a, b) => b.change_pct - a.change_pct)
      .slice(0, 10)
  })

  const bottomSectors = computed(() => {
    return sectors.value
      .filter(sector => sector.change_pct < 0)
      .sort((a, b) => a.change_pct - b.change_pct)
      .slice(0, 10)
  })

  // 方法
  async function fetchMarketOverview() {
    try {
      isLoading.value = true
      const response = await marketApi.getOverview()
      overview.value = response.data
      lastUpdate.value = dayjs().format('HH:mm:ss')
      return response.data
    } catch (error) {
      console.error('获取市场概览失败:', error)
      throw error
    } finally {
      isLoading.value = false
    }
  }

  async function fetchSectorPerformance(limit = 50) {
    try {
      isLoading.value = true
      const response = await marketApi.getSectors(limit)
      sectors.value = response.data
      return response.data
    } catch (error) {
      console.error('获取板块数据失败:', error)
      throw error
    } finally {
      isLoading.value = false
    }
  }

  async function fetchStocksBySector(sectorName, limit = 50) {
    try {
      isLoading.value = true
      const response = await marketApi.getStocksBySector(sectorName, limit)
      sectorStocks.value = response.data
      selectedSector.value = sectorName
      return response.data
    } catch (error) {
      console.error('获取板块股票失败:', error)
      throw error
    } finally {
      isLoading.value = false
    }
  }

  async function fetchNorthboundFunds() {
    try {
      const response = await marketApi.getNorthboundFunds()
      northboundFunds.value = response.data
      return response.data
    } catch (error) {
      console.error('获取北向资金失败:', error)
      throw error
    }
  }

  async function fetchMarketHeatmap() {
    try {
      const response = await marketApi.getHeatmap()
      heatmap.value = response.data
      return response.data
    } catch (error) {
      console.error('获取热力图数据失败:', error)
      throw error
    }
  }

  async function initializeMarketData() {
    await Promise.all([
      fetchMarketOverview(),
      fetchSectorPerformance(),
      fetchNorthboundFunds(),
      fetchMarketHeatmap()
    ])
  }

  // 自动刷新
  let refreshInterval = null

  function startAutoRefresh(intervalMs = 30000) { // 30秒刷新一次
    stopAutoRefresh() // 先停止之前的定时器

    refreshInterval = setInterval(async () => {
      try {
        await Promise.all([
          fetchMarketOverview(),
          fetchSectorPerformance()
        ])
      } catch (error) {
        console.error('自动刷新失败:', error)
      }
    }, intervalMs)
  }

  function stopAutoRefresh() {
    if (refreshInterval) {
      clearInterval(refreshInterval)
      refreshInterval = null
    }
  }

  // 选择板块
  function selectSector(sector) {
    selectedSector.value = sector.name
    fetchStocksBySector(sector.name)
  }

  // 清空选择
  function clearSelection() {
    selectedSector.value = null
    sectorStocks.value = []
  }

  // 获取市场状态
  function getMarketStatus() {
    const now = dayjs()
    const hour = now.hour()
    const minute = now.minute()
    const day = now.day()

    // 周末
    if (day === 0 || day === 6) {
      return { status: 'closed', text: '周末休市' }
    }

    // 工作日交易时间
    if ((hour === 9 && minute >= 30) || (hour > 9 && hour < 11) ||
        (hour === 11 && minute < 30) ||
        (hour === 13) || (hour === 14) ||
        (hour === 15 && minute === 0)) {
      return { status: 'trading', text: '交易中' }
    }

    // 休市时间
    if ((hour < 9) || (hour === 9 && minute < 30) ||
        (hour === 11 && minute >= 30) ||
        (hour === 12) ||
        (hour > 15)) {
      return { status: 'closed', text: '休市' }
    }

    // 午休时间
    if ((hour === 11 && minute >= 30) || hour === 12) {
      return { status: 'break', text: '午休' }
    }

    return { status: 'closed', text: '休市' }
  }

  return {
    // 状态
    overview,
    sectors,
    selectedSector,
    sectorStocks,
    northboundFunds,
    heatmap,
    isLoading,
    lastUpdate,

    // 计算属性
    marketStats,
    topSectors,
    bottomSectors,

    // 方法
    fetchMarketOverview,
    fetchSectorPerformance,
    fetchStocksBySector,
    fetchNorthboundFunds,
    fetchMarketHeatmap,
    initializeMarketData,
    startAutoRefresh,
    stopAutoRefresh,
    selectSector,
    clearSelection,
    getMarketStatus
  }
})