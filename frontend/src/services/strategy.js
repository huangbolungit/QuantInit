/**
 * 策略管理API服务
 */

import api from './api.js'

const STRATEGY_ENDPOINTS = {
  // 策略管理
  STRATEGIES: '/strategies',
  STRATEGY_DETAIL: (id) => `/strategies/${id}`,

  // 信号相关
  GENERATE_SIGNALS: (id) => `/strategies/${id}/signals`,
  STRATEGY_SIGNALS: (id) => `/strategies/${id}/signals`,
  ALL_SIGNALS: '/signals/generate',
  LATEST_SIGNALS: '/signals/latest',

  // 性能相关
  STRATEGY_PERFORMANCE: (id) => `/strategies/${id}/performance`,

  // 参数优化
  OPTIMIZE_PARAMETERS: (id) => `/strategies/${id}/optimize`,

  // 优化器相关
  CREATE_OPTIMIZED: '/strategies/optimized',
  OPTIMIZATION_INFO: '/optimization/info',
  VALIDATE_PARAMETERS: '/optimization/validate'
}

class StrategyService {
  /**
   * 获取所有策略
   */
  async getStrategies() {
    try {
      const response = await api.get(STRATEGY_ENDPOINTS.STRATEGIES)
      return response.data
    } catch (error) {
      console.error('获取策略列表失败:', error)
      throw error
    }
  }

  /**
   * 获取策略详情
   */
  async getStrategy(strategyId) {
    try {
      const response = await api.get(STRATEGY_ENDPOINTS.STRATEGY_DETAIL(strategyId))
      return response.data
    } catch (error) {
      console.error('获取策略详情失败:', error)
      throw error
    }
  }

  /**
   * 创建策略
   */
  async createStrategy(strategyData) {
    try {
      const response = await api.post(STRATEGY_ENDPOINTS.STRATEGIES, strategyData)
      return response.data
    } catch (error) {
      console.error('创建策略失败:', error)
      throw error
    }
  }

  /**
   * 更新策略
   */
  async updateStrategy(strategyId, updateData) {
    try {
      const response = await api.put(STRATEGY_ENDPOINTS.STRATEGY_DETAIL(strategyId), updateData)
      return response.data
    } catch (error) {
      console.error('更新策略失败:', error)
      throw error
    }
  }

  /**
   * 删除策略
   */
  async deleteStrategy(strategyId) {
    try {
      const response = await api.delete(STRATEGY_ENDPOINTS.STRATEGY_DETAIL(strategyId))
      return response.data
    } catch (error) {
      console.error('删除策略失败:', error)
      throw error
    }
  }

  /**
   * 生成交易信号
   */
  async generateSignals(strategyId) {
    try {
      const response = await api.post(STRATEGY_ENDPOINTS.GENERATE_SIGNALS(strategyId))
      return response.data
    } catch (error) {
      console.error('生成交易信号失败:', error)
      throw error
    }
  }

  /**
   * 获取策略历史信号
   */
  async getStrategySignals(strategyId, limit = 100) {
    try {
      const response = await api.get(STRATEGY_ENDPOINTS.STRATEGY_SIGNALS(strategyId), {
        params: { limit }
      })
      return response.data
    } catch (error) {
      console.error('获取策略信号失败:', error)
      throw error
    }
  }

  /**
   * 获取所有最新信号
   */
  async generateAllSignals() {
    try {
      const response = await api.post(STRATEGY_ENDPOINTS.ALL_SIGNALS)
      return response.data
    } catch (error) {
      console.error('生成所有信号失败:', error)
      throw error
    }
  }

  /**
   * 获取最新信号
   */
  async getLatestSignals(limit = 50, strategyId = null) {
    try {
      const params = { limit }
      if (strategyId) {
        params.strategy_id = strategyId
      }

      const response = await api.get(STRATEGY_ENDPOINTS.LATEST_SIGNALS, { params })
      return response.data
    } catch (error) {
      console.error('获取最新信号失败:', error)
      throw error
    }
  }

  /**
   * 获取策略性能指标
   */
  async getStrategyPerformance(strategyId) {
    try {
      const response = await api.get(STRATEGY_ENDPOINTS.STRATEGY_PERFORMANCE(strategyId))
      return response.data
    } catch (error) {
      console.error('获取策略性能失败:', error)
      throw error
    }
  }

  /**
   * 优化策略参数
   */
  async optimizeParameters(strategyId, optimizationConfig) {
    try {
      const response = await api.post(STRATEGY_ENDPOINTS.OPTIMIZE_PARAMETERS(strategyId), optimizationConfig)
      return response.data
    } catch (error) {
      console.error('参数优化失败:', error)
      throw error
    }
  }

  /**
   * 策略类型配置
   */
  getStrategyTypes() {
    return [
      {
        value: 'mean_reversion',
        label: '均值回归策略',
        description: '基于价格均值回归原理的交易策略',
        defaultParameters: {
          lookback_period: 10,
          buy_threshold: -0.05,
          sell_threshold: 0.03,
          max_hold_days: 15
        },
        parameterSchema: [
          {
            name: 'lookback_period',
            label: '回看周期',
            type: 'number',
            min: 5,
            max: 30,
            step: 1,
            description: '计算均值的周期天数'
          },
          {
            name: 'buy_threshold',
            label: '买入阈值',
            type: 'number',
            min: -0.15,
            max: -0.01,
            step: 0.01,
            description: '价格低于均值的买入触发阈值（负数）'
          },
          {
            name: 'sell_threshold',
            label: '卖出阈值',
            type: 'number',
            min: 0.01,
            max: 0.15,
            step: 0.01,
            description: '价格高于均值的卖出触发阈值'
          },
          {
            name: 'max_hold_days',
            label: '最大持有天数',
            type: 'number',
            min: 1,
            max: 60,
            step: 1,
            description: '最长持仓时间，超过时间强制卖出'
          }
        ]
      }
    ]
  }

  /**
   * 预设股票池
   */
  getStockPools() {
    return [
      {
        name: '核心蓝筹股',
        stocks: ['000001', '000002', '600036', '600519', '000858', '600900'],
        description: '优质蓝筹股票池，适合稳健投资'
      },
      {
        name: '科技成长股',
        stocks: ['000725', '002415', '300059', '002475', '000063'],
        description: '科技成长股池，适合追求高收益'
      },
      {
        name: '金融板块',
        stocks: ['000001', '600036', '601318', '601398', '600000'],
        description: '金融行业股票池'
      },
      {
        name: '消费板块',
        stocks: ['000858', '600519', '000568', '002304', '600887'],
        description: '消费行业股票池'
      }
    ]
  }

  /**
   * 创建基于优化器的策略
   */
  async createOptimizedStrategy(presetType = 'balanced', customName = null) {
    try {
      const { data } = await api.post(STRATEGY_ENDPOINTS.CREATE_OPTIMIZED, {
        preset_type: presetType,
        custom_name: customName
      })

      return {
        data: data?.data ?? data ?? {},
        meta: {
          success: data?.success ?? true,
          timestamp: data?.timestamp ?? null
        }
      }
    } catch (error) {
      console.error('创建优化器策略失败:', error)
      throw new Error(`创建优化器策略失败: ${error.message}`)
    }
  }

  /**
   * 获取优化器信息
   */
  async getOptimizationInfo() {
    try {
      const { data } = await api.get(STRATEGY_ENDPOINTS.OPTIMIZATION_INFO)

      return {
        data: data?.data ?? data ?? {},
        meta: {
          success: data?.success ?? true,
          timestamp: data?.timestamp ?? null
        }
      }
    } catch (error) {
      console.error('获取优化器信息失败:', error)
      throw new Error(`获取优化器信息失败: ${error.message}`)
    }
  }

  /**
   * 验证策略参数
   */
  async validateParameters(parameters) {
    try {
      const { data } = await api.post(STRATEGY_ENDPOINTS.VALIDATE_PARAMETERS, {
        parameters
      })

      return {
        data: data?.data ?? data ?? {},
        meta: {
          success: data?.success ?? true,
          timestamp: data?.timestamp ?? null
        }
      }
    } catch (error) {
      console.error('验证参数失败:', error)
      throw new Error(`验证参数失败: ${error.message}`)
    }
  }
}

export default new StrategyService()