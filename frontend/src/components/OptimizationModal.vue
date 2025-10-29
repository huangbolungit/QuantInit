<template>
  <div class="optimization-modal-overlay" @click.self="handleClose">
    <div class="optimization-modal">
      <header class="modal-header">
        <h2>策略参数优化</h2>
        <p>选择要优化的策略类型和参数范围</p>
        <button class="close-btn" @click="handleClose">×</button>
      </header>

      <div class="modal-body">
        <!-- 策略类型选择 -->
        <section class="strategy-selection">
          <h3>策略类型</h3>
          <div class="strategy-types">
            <div
              v-for="strategy in strategyTypes"
              :key="strategy.value"
              class="strategy-type"
              :class="{ 'strategy-type--selected': selectedStrategy === strategy.value }"
              @click="selectedStrategy = strategy.value"
            >
              <div class="strategy-icon">{{ strategy.icon }}</div>
              <h4>{{ strategy.name }}</h4>
              <p>{{ strategy.description }}</p>
              <div class="strategy-status" :class="`status-${strategy.status}`">
                {{ getStatusText(strategy.status) }}
              </div>
            </div>
          </div>
        </section>

        <!-- 参数配置 -->
        <section class="parameter-config" v-if="selectedStrategy">
          <h3>参数网格配置</h3>
          <div class="parameter-grid">
            <div
              v-for="(paramConfig, paramKey) in currentParamConfig"
              :key="paramKey"
              class="parameter-item"
            >
              <label class="parameter-label">
                {{ getParamLabel(paramKey) }}
                <span class="parameter-hint">{{ paramConfig.hint }}</span>
              </label>

              <div class="parameter-values">
                <input
                  v-if="paramConfig.type === 'number'"
                  v-model="paramConfig.value"
                  type="number"
                  :min="paramConfig.min"
                  :max="paramConfig.max"
                  :step="paramConfig.step"
                  class="parameter-input"
                />

                <div v-else class="parameter-ranges">
                  <div
                    v-for="(range, index) in paramConfig.ranges"
                    :key="index"
                    class="range-item"
                  >
                    <input
                      v-model="range.value"
                      type="number"
                      :placeholder="paramConfig.placeholder"
                      class="range-input"
                    />
                    <button
                      class="remove-btn"
                      @click="removeRange(paramKey, index)"
                      :disabled="paramConfig.ranges.length <= 1"
                    >
                      ×
                    </button>
                  </div>
                  <button
                    class="add-range-btn"
                    @click="addRange(paramKey)"
                  >
                    + 添加值
                  </button>
                </div>
              </div>
            </div>
          </div>
        </section>

        <!-- 优化配置 -->
        <section class="optimization-config" v-if="selectedStrategy">
          <h3>优化配置</h3>
          <div class="config-grid">
            <div class="config-item">
              <label class="config-label">测试期间</label>
              <select v-model="optimizationConfig.testPeriod" class="config-select">
                <option value="2022-2023">2022-2023 (推荐)</option>
                <option value="2021-2023">2021-2023 (更长)</option>
                <option value="2023">2023 (近期)</option>
              </select>
            </div>

            <div class="config-item">
              <label class="config-label">股票池</label>
              <select v-model="optimizationConfig.stockPool" class="config-select">
                <option value="csi300">CSI300 (大盘股)</option>
                <option value="csi800">CSI800 (中盘股)</option>
                <option value="custom">自定义</option>
              </select>
            </div>

            <div class="config-item">
              <label class="config-label">调仓频率</label>
              <select v-model="optimizationConfig.rebalanceFreq" class="config-select">
                <option value="5">5日</option>
                <option value="10">10日 (推荐)</option>
                <option value="20">20日</option>
                <option value="30">30日</option>
              </select>
            </div>

            <div class="config-item">
              <label class="config-label">性能指标</label>
              <div class="metrics-checkboxes">
                <label class="checkbox-label">
                  <input
                    v-model="optimizationConfig.metrics"
                    type="checkbox"
                    value="total_return"
                    checked
                  />
                  总收益
                </label>
                <label class="checkbox-label">
                  <input
                    v-model="optimizationConfig.metrics"
                    type="checkbox"
                    value="sharpe_ratio"
                    checked
                  />
                  夏普比率
                </label>
                <label class="checkbox-label">
                  <input
                    v-model="optimizationConfig.metrics"
                    type="checkbox"
                    value="max_drawdown"
                  />
                  最大回撤
                </label>
                <label class="checkbox-label">
                  <input
                    v-model="optimizationConfig.metrics"
                    type="checkbox"
                    value="win_rate"
                  />
                  胜率
                </label>
              </div>
            </div>
          </div>
        </section>

        <!-- 预计结果 -->
        <section class="optimization-preview" v-if="selectedStrategy">
          <h3>优化规模预估</h3>
          <div class="preview-stats">
            <div class="stat-item">
              <span class="stat-label">参数组合数</span>
              <span class="stat-value">{{ estimatedCombinations }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">预计耗时</span>
              <span class="stat-value">{{ estimatedTime }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">数据需求</span>
              <span class="stat-value">{{ estimatedDataSize }}</span>
            </div>
          </div>
        </section>
      </div>

      <footer class="modal-footer">
        <div class="footer-info">
          <span v-if="selectedStrategy">
            将测试 {{ estimatedCombinations }} 组参数组合
          </span>
        </div>
        <div class="footer-actions">
          <button
            class="btn btn-secondary"
            @click="handleClose"
            :disabled="optimizing"
          >
            取消
          </button>
          <button
            class="btn btn-primary"
            @click="startOptimization"
            :disabled="!selectedStrategy || optimizing"
          >
            <span v-if="optimizing">优化中...</span>
            <span v-else>开始优化</span>
          </button>
        </div>
      </footer>

      <!-- 优化进度 -->
      <div v-if="optimizing" class="optimization-progress">
        <div class="progress-content">
          <h3>正在进行参数优化...</h3>
          <div class="progress-bar">
            <div
              class="progress-fill"
              :style="{ width: `${progressPercent}%` }"
            ></div>
          </div>
          <div class="progress-details">
            <span>已完成: {{ currentProgress }} / {{ totalProgress }}</span>
            <span>{{ progressPercent }}%</span>
          </div>
          <div class="progress-status">
            {{ progressStatus }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

// Props & Emits
const emit = defineEmits(['close', 'optimization-started'])

// 响应式数据
const selectedStrategy = ref('mean_reversion')
const optimizing = ref(false)
const currentProgress = ref(0)
const totalProgress = ref(1)
const progressStatus = ref('准备开始...')

const optimizationConfig = ref({
  testPeriod: '2022-2023',
  stockPool: 'csi300',
  rebalanceFreq: '10',
  metrics: ['total_return', 'sharpe_ratio']
})

const strategyTypes = ref([
  {
    value: 'mean_reversion',
    name: '均值回归策略',
    icon: '🔄',
    description: '基于价格回归原理的低买高卖策略',
    status: 'completed'
  },
  {
    value: 'momentum',
    name: '动量策略',
    icon: '📈',
    description: '基于价格动量的趋势跟踪策略',
    status: 'pending'
  }
])

const paramConfigs = ref({
  mean_reversion: {
    lookback_period: {
      type: 'ranges',
      label: '回看周期',
      hint: '计算均值的回看天数',
      ranges: [{ value: 5 }, { value: 10 }, { value: 15 }, { value: 20 }]
    },
    buy_threshold: {
      type: 'ranges',
      label: '买入阈值',
      hint: '买入信号的负向阈值',
      ranges: [{ value: -0.03 }, { value: -0.05 }, { value: -0.08 }, { value: -0.10 }]
    },
    sell_threshold: {
      type: 'ranges',
      label: '卖出阈值',
      hint: '卖出信号的正向阈值',
      ranges: [{ value: 0.02 }, { value: 0.03 }, { value: 0.05 }, { value: 0.06 }]
    }
  },
  momentum: {
    momentum_period: {
      type: 'ranges',
      label: '动量周期',
      hint: '计算动量的回看天数',
      ranges: [{ value: 5 }, { value: 10 }, { value: 15 }, { value: 20 }]
    },
    buy_threshold: {
      type: 'ranges',
      label: '买入阈值',
      hint: '买入信号的正向阈值',
      ranges: [{ value: 0.03 }, { value: 0.05 }, { value: 0.08 }, { value: 0.10 }]
    },
    sell_threshold: {
      type: 'ranges',
      label: '卖出阈值',
      hint: '卖出信号的负向阈值',
      ranges: [{ value: -0.02 }, { value: -0.03 }, { value: -0.05 }, { value: -0.08 }]
    },
    profit_target: {
      type: 'ranges',
      label: '止盈目标',
      hint: '盈利目标比例',
      ranges: [{ value: 0.05 }, { value: 0.08 }, { value: 0.10 }, { value: 0.15 }]
    },
    max_hold_days: {
      type: 'ranges',
      label: '最大持有天数',
      hint: '最长持仓时间限制',
      ranges: [{ value: 10 }, { value: 15 }, { value: 20 }, { value: 25 }]
    }
  }
})

// 计算属性
const currentParamConfig = computed(() => {
  return paramConfigs.value[selectedStrategy.value] || {}
})

const estimatedCombinations = computed(() => {
  const config = currentParamConfig.value
  let total = 1

  for (const paramKey in config) {
    const paramConfig = config[paramKey]
    if (paramConfig.type === 'ranges' && paramConfig.ranges) {
      total *= paramConfig.ranges.filter(range => range.value).length
    } else if (paramConfig.type === 'number' && paramConfig.value) {
      total *= 1
    }
  }

  return total
})

const estimatedTime = computed(() => {
  const combinations = estimatedCombinations.value
  if (combinations <= 64) return '~5分钟'
  if (combinations <= 256) return '~15分钟'
  if (combinations <= 1024) return '~30分钟'
  return '~60分钟'
})

const estimatedDataSize = computed(() => {
  const period = optimizationConfig.value.testPeriod
  if (period === '2023') return '~50MB'
  if (period === '2022-2023') return '~100MB'
  return '~150MB'
})

const progressPercent = computed(() => {
  if (totalProgress.value === 0) return 0
  return Math.round((currentProgress.value / totalProgress.value) * 100)
})

// 监听器
watch(selectedStrategy, () => {
  // 重置进度
  currentProgress.value = 0
  totalProgress.value = 1
  progressStatus.value = '准备开始...'
})

// 方法
function getParamLabel(key) {
  const config = currentParamConfig.value[key]
  return config?.label || key
}

function getStatusText(status) {
  const statusMap = {
    completed: '已完成',
    pending: '待优化',
    running: '进行中'
  }
  return statusMap[status] || status
}

function addRange(paramKey) {
  const paramConfig = currentParamConfig.value[paramKey]
  if (paramConfig && paramConfig.type === 'ranges') {
    paramConfig.ranges.push({ value: null })
  }
}

function removeRange(paramKey, index) {
  const paramConfig = currentParamConfig.value[paramKey]
  if (paramConfig && paramConfig.type === 'ranges') {
    paramConfig.ranges.splice(index, 1)
  }
}

async function startOptimization() {
  if (!selectedStrategy.value || optimizing.value) return

  optimizing.value = true
  currentProgress.value = 0
  totalProgress.value = estimatedCombinations.value
  progressStatus.value = '初始化优化器...'

  try {
    // 模拟优化过程
    for (let i = 0; i < totalProgress.value; i++) {
      currentProgress.value = i + 1

      if (i < totalProgress.value * 0.1) {
        progressStatus.value = '加载历史数据...'
      } else if (i < totalProgress.value * 0.8) {
        progressStatus.value = '测试参数组合...'
      } else if (i < totalProgress.value * 0.95) {
        progressStatus.value = '分析优化结果...'
      } else {
        progressStatus.value = '保存优化配置...'
      }

      // 模拟处理时间
      await new Promise(resolve => setTimeout(resolve, 100))
    }

    // 完成优化
    progressStatus.value = '优化完成！'

    emit('optimization-started', {
      strategy_type: selectedStrategy.value,
      total_combinations: totalProgress.value,
      best_parameters: getBestParameters(),
      performance_metrics: getMockPerformanceMetrics()
    })

    setTimeout(() => {
      handleClose()
    }, 1500)

  } catch (error) {
    console.error('优化失败:', error)
    progressStatus.value = '优化失败，请重试'
  } finally {
    // 3秒后重置优化状态
    setTimeout(() => {
      if (progressStatus.value === '优化完成！') {
        optimizing.value = false
      }
    }, 3000)
  }
}

function getBestParameters() {
  const config = currentParamConfig.value
  const bestParams = {}

  for (const paramKey in config) {
    const paramConfig = config[paramKey]
    if (paramConfig.type === 'ranges' && paramConfig.ranges) {
      // 模拟返回第一个有效参数作为最佳参数
      const validRange = paramConfig.ranges.find(range => range.value !== null)
      if (validRange) {
        bestParams[paramKey] = validRange.value
      }
    }
  }

  return bestParams
}

function getMockPerformanceMetrics() {
  return {
    total_return: 0.25 + Math.random() * 0.1,
    sharpe_ratio: 1.2 + Math.random() * 0.3,
    max_drawdown: 0.3 + Math.random() * 0.1,
    trade_count: 10 + Math.floor(Math.random() * 20),
    composite_score: 7 + Math.random() * 2
  }
}

function handleClose() {
  if (!optimizing.value) {
    emit('close')
  }
}
</script>

<style scoped>
.optimization-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.optimization-modal {
  background: var(--card-bg);
  border-radius: 12px;
  max-width: 900px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.15);
  position: relative;
}

.modal-header {
  padding: 24px 24px 16px;
  border-bottom: 1px solid var(--border-light);
  position: relative;
}

.modal-header h2 {
  margin: 0 0 4px;
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary);
}

.modal-header p {
  margin: 0;
  color: var(--text-secondary);
  font-size: 14px;
}

.close-btn {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: 20px;
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.2s ease;
}

.close-btn:hover {
  background: var(--bg-secondary);
  color: var(--text-primary);
}

.modal-body {
  padding: 24px;
}

.strategy-selection,
.parameter-config,
.optimization-config,
.optimization-preview {
  margin-bottom: 32px;
}

.strategy-selection h3,
.parameter-config h3,
.optimization-config h3,
.optimization-preview h3 {
  margin: 0 0 16px;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.strategy-types {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px;
}

.strategy-type {
  padding: 20px;
  border: 2px solid var(--border-light);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: center;
}

.strategy-type:hover {
  border-color: var(--primary-color);
  background: var(--bg-secondary);
}

.strategy-type--selected {
  border-color: var(--primary-color);
  background: rgba(64, 158, 255, 0.05);
}

.strategy-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.strategy-type h4 {
  margin: 0 0 8px;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.strategy-type p {
  margin: 0 0 12px;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.5;
}

.strategy-status {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}

.status-completed {
  background: rgba(103, 194, 58, 0.15);
  color: var(--success-color);
}

.status-pending {
  background: rgba(230, 162, 60, 0.15);
  color: var(--warning-color);
}

.parameter-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
}

.parameter-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.parameter-label {
  font-weight: 600;
  color: var(--text-primary);
  font-size: 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.parameter-hint {
  font-weight: normal;
  color: var(--text-secondary);
  font-size: 12px;
}

.parameter-input {
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--card-bg);
  color: var(--text-primary);
  font-size: 14px;
}

.parameter-input:focus {
  border-color: var(--primary-color);
  outline: none;
  box-shadow: 0 0 0 3px rgba(64, 158, 255, 0.1);
}

.parameter-ranges {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.range-item {
  display: flex;
  gap: 8px;
  align-items: center;
}

.range-input {
  flex: 1;
  padding: 6px 10px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: var(--card-bg);
  color: var(--text-primary);
  font-size: 14px;
}

.remove-btn {
  width: 28px;
  height: 28px;
  border: none;
  background: rgba(245, 108, 108, 0.1);
  color: var(--danger-color);
  border-radius: 4px;
  cursor: pointer;
  font-size: 16px;
  transition: all 0.2s ease;
}

.remove-btn:hover:not(:disabled) {
  background: rgba(245, 108, 108, 0.2);
}

.remove-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.add-range-btn {
  padding: 6px 12px;
  border: 1px dashed var(--primary-color);
  background: transparent;
  color: var(--primary-color);
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s ease;
}

.add-range-btn:hover {
  background: rgba(64, 158, 255, 0.05);
}

.config-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
}

.config-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.config-label {
  font-weight: 600;
  color: var(--text-primary);
  font-size: 14px;
}

.config-select {
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--card-bg);
  color: var(--text-primary);
  font-size: 14px;
}

.config-select:focus {
  border-color: var(--primary-color);
  outline: none;
}

.metrics-checkboxes {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: var(--text-primary);
  cursor: pointer;
}

.checkbox-label input[type="checkbox"] {
  margin: 0;
}

.preview-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 16px;
}

.stat-item {
  padding: 16px;
  background: var(--bg-secondary);
  border-radius: 8px;
  text-align: center;
}

.stat-label {
  display: block;
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.stat-value {
  display: block;
  font-size: 18px;
  font-weight: 600;
  color: var(--primary-color);
}

.modal-footer {
  padding: 20px 24px;
  border-top: 1px solid var(--border-light);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.footer-info {
  color: var(--text-secondary);
  font-size: 14px;
}

.footer-actions {
  display: flex;
  gap: 12px;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary {
  background: var(--primary-color);
  color: #ffffff;
}

.btn-primary:hover:not(:disabled) {
  background: var(--primary-hover);
}

.btn-secondary {
  background: var(--bg-secondary);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--hover-bg);
}

.optimization-progress {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.95);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  border-radius: 12px;
  backdrop-filter: blur(4px);
}

.progress-content {
  text-align: center;
  max-width: 300px;
}

.progress-content h3 {
  margin: 0 0 20px;
  font-size: 18px;
  color: var(--text-primary);
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: var(--border-light);
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 12px;
}

.progress-fill {
  height: 100%;
  background: var(--primary-color);
  transition: width 0.3s ease;
  border-radius: 4px;
}

.progress-details {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 14px;
  color: var(--text-secondary);
}

.progress-status {
  font-size: 14px;
  color: var(--text-primary);
  font-weight: 600;
}

/* CSS Variables */
:root {
  --primary-color: #409eff;
  --primary-hover: #66b1ff;
  --success-color: #67c23a;
  --warning-color: #e6a23c;
  --danger-color: #f56c6c;
  --text-primary: #303133;
  --text-secondary: #909399;
  --border-color: #dcdfe6;
  --border-light: #e4e7ed;
  --border-lighter: #f2f6fc;
  --card-bg: #ffffff;
  --bg-secondary: #f5f7fa;
  --hover-bg: #ecf5ff;
}

/* 暗色主题 */
@media (prefers-color-scheme: dark) {
  :root {
    --text-primary: #e4e7ed;
    --text-secondary: #b1b3b8;
    --border-color: #4c4d4f;
    --border-light: #4c4d4f;
    --border-lighter: #363637;
    --card-bg: #2d2d2d;
    --bg-secondary: #252526;
    --hover-bg: #4c4d4f;
  }

  .optimization-progress {
    background: rgba(45, 45, 45, 0.95);
  }
}

/* 响应式 */
@media (max-width: 768px) {
  .optimization-modal {
    margin: 10px;
    max-height: 95vh;
  }

  .strategy-types {
    grid-template-columns: 1fr;
  }

  .parameter-grid,
  .config-grid {
    grid-template-columns: 1fr;
  }

  .preview-stats {
    grid-template-columns: repeat(3, 1fr);
  }

  .modal-footer {
    flex-direction: column;
    gap: 12px;
    text-align: center;
  }
}
</style>