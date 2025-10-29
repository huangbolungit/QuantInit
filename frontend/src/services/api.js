import axios from 'axios'

const http = axios.create({
  baseURL: '/api',
  timeout: 10000
})

// 导出默认实例
export default http

export const marketApi = {
  async getOverview() {
    const { data } = await http.get('/market/overview')
    return {
      data: data?.data ?? data ?? {},
      meta: {
        success: data?.success ?? true,
        timestamp: data?.timestamp ?? null
      }
    }
  },

  async getSectors(limit = 50) {
    const { data } = await http.get('/market/sectors', { params: { limit } })
    return {
      data: data?.data ?? [],
      meta: {
        count: (data?.data ?? []).length,
        timestamp: data?.timestamp ?? null
      }
    }
  },

  async getStocksBySector(sectorName, limit = 50) {
    const { data } = await http.get(`/market/sectors/${encodeURIComponent(sectorName)}/stocks`, {
      params: { limit }
    })
    return {
      data: data?.data ?? [],
      meta: {
        sector: data?.sector ?? sectorName,
        count: data?.count ?? (data?.data ?? []).length,
        timestamp: data?.timestamp ?? null
      }
    }
  },

  async getNorthboundFunds() {
    const { data } = await http.get('/market/northbound')
    return {
      data: data?.data ?? data ?? {},
      meta: {
        timestamp: data?.timestamp ?? null
      }
    }
  },

  async getHeatmap() {
    const { data } = await http.get('/market/heatmap')
    return {
      data: data?.data ?? [],
      meta: {
        timestamp: data?.timestamp ?? null
      }
    }
  }
}

export const optimizationApi = {
  // 获取优化器信息
  async getInfo() {
    const { data } = await http.get('/optimization/info')
    return {
      data: data?.data ?? data ?? {},
      meta: {
        success: data?.success ?? true,
        timestamp: data?.timestamp ?? null
      }
    }
  },

  // 验证策略参数
  async validateParameters(parameters, strategyType = 'mean_reversion') {
    const { data } = await http.post('/optimization/validate', {
      parameters,
      strategy_type: strategyType
    })
    return {
      data: data?.data ?? data ?? {},
      meta: {
        success: data?.success ?? true,
        timestamp: data?.timestamp ?? null
      }
    }
  },

  // 创建基于优化器的策略
  async createOptimizedStrategy(presetType = 'balanced') {
    const { data } = await http.post('/strategies/optimized', {
      preset_type: presetType
    })
    return {
      data: data?.data ?? data ?? {},
      meta: {
        success: data?.success ?? true,
        timestamp: data?.timestamp ?? null
      }
    }
  }
}

export const strategyApi = {
  // 获取策略列表
  async getStrategies(status = null) {
    const params = status ? { status } : {}
    const { data } = await http.get('/strategies', { params })
    return {
      data: data?.data ?? data ?? [],
      meta: {
        count: (data?.data ?? data ?? []).length,
        timestamp: data?.timestamp ?? null
      }
    }
  },

  // 创建策略
  async createStrategy(strategyData) {
    const { data } = await http.post('/strategies', strategyData)
    return {
      data: data?.data ?? data ?? {},
      meta: {
        success: data?.success ?? true,
        timestamp: data?.timestamp ?? null
      }
    }
  },

  // 获取策略信号
  async getSignals(strategyId) {
    const { data } = await http.get(`/strategies/${strategyId}/signals`)
    return {
      data: data?.data ?? data ?? [],
      meta: {
        count: (data?.data ?? data ?? []).length,
        timestamp: data?.timestamp ?? null
      }
    }
  },

  // 生成策略信号
  async generateSignals(strategyId) {
    const { data } = await http.post(`/strategies/${strategyId}/signals`)
    return {
      data: data?.data ?? data ?? {},
      meta: {
        success: data?.success ?? true,
        timestamp: data?.timestamp ?? null
      }
    }
  }
}
