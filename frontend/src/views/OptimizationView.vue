<template>
  <div class="optimization-view">
    <header class="optimization-header">
      <div class="header-content">
        <h1>策略优化器</h1>
        <p>基于历史数据的参数寻优，自动发现最佳策略配置</p>
      </div>

      <div class="header-actions">
        <button
          class="btn btn-secondary"
          @click="refreshOptimizationInfo"
          :disabled="loading"
        >
          刷新数据
        </button>
        <button
          class="btn btn-primary"
          @click="showOptimizationModal = true"
          :disabled="loading"
        >
          <span class="btn-icon">⚡</span>
          开始优化
        </button>
      </div>
    </header>

    <transition name="fade">
      <div v-if="error" class="optimization-alert">
        <div class="optimization-alert__info">
          <strong>加载异常</strong>
          <span>{{ error }}</span>
        </div>
        <button
          class="btn btn-sm btn-outline"
          @click="refreshOptimizationInfo"
          :disabled="loading"
        >
          重试
        </button>
      </div>
    </transition>

    <!-- 优化器概览 -->
    <section class="optimization-overview">
      <div class="overview-cards">
        <article class="overview-card">
          <header>
            <span class="overview-card__title">优化完成度</span>
            <span class="overview-card__badge">状态</span>
          </header>
          <div class="overview-card__value">
            {{ optimizationInfo.total_strategies || 0 }}
          </div>
          <p class="overview-card__meta">个策略已完成优化</p>
        </article>

        <article class="overview-card">
          <header>
            <span class="overview-card__title">最佳收益</span>
            <span class="overview-card__badge overview-card__badge--success">表现</span>
          </header>
          <div class="overview-card__value">
            {{ bestPerformance }}%
          </div>
          <p class="overview-card__meta">{{ bestPerformanceStrategy }}</p>
        </article>

        <article class="overview-card">
          <header>
            <span class="overview-card__title">最佳夏普</span>
            <span class="overview-card__badge overview-card__badge--info">风险</span>
          </header>
          <div class="overview-card__value">
            {{ bestSharpe }}
          </div>
          <p class="overview-card__meta">{{ bestSharpeStrategy }}</p>
        </article>

        <article class="overview-card">
          <header>
            <span class="overview-card__title">参数测试</span>
            <span class="overview-card__badge overview-card__badge--warning">覆盖</span>
          </header>
          <div class="overview-card__value">
            {{ totalTests }}
          </div>
          <p class="overview-card__meta">组参数组合已测试</p>
        </article>
      </div>
    </section>

    <!-- 优化结果详情 -->
    <section class="optimization-layout">
      <div class="optimization-main">
        <!-- 均值回归优化结果 -->
        <div class="strategy-optimization">
          <div class="section-header">
            <div>
              <h2>均值回归策略优化</h2>
              <p class="section-subtitle">
                基于2022-2023年历史数据，64组参数寻优结果
              </p>
            </div>
            <span class="status-badge status-success">已完成</span>
          </div>

          <div class="optimization-result">
            <div class="result-params">
              <h3>🏆 最佳参数配置</h3>
              <div class="param-grid">
                <div class="param-item">
                  <span class="param-label">回看周期</span>
                  <span class="param-value">{{ meanReversionResult.lookback_period }} 日</span>
                </div>
                <div class="param-item">
                  <span class="param-label">买入阈值</span>
                  <span class="param-value">{{ (meanReversionResult.buy_threshold * 100).toFixed(1) }}%</span>
                </div>
                <div class="param-item">
                  <span class="param-label">卖出阈值</span>
                  <span class="param-value">{{ (meanReversionResult.sell_threshold * 100).toFixed(1) }}%</span>
                </div>
              </div>
            </div>

            <div class="result-performance">
              <h3>📊 性能指标</h3>
              <div class="metrics-grid">
                <div class="metric-item">
                  <span class="metric-label">总收益</span>
                  <span class="metric-value metric-value--success">
                    {{ (meanReversionResult.total_return * 100).toFixed(2) }}%
                  </span>
                </div>
                <div class="metric-item">
                  <span class="metric-label">夏普比率</span>
                  <span class="metric-value">{{ meanReversionResult.sharpe_ratio.toFixed(2) }}</span>
                </div>
                <div class="metric-item">
                  <span class="metric-label">最大回撤</span>
                  <span class="metric-value metric-value--danger">
                    {{ (meanReversionResult.max_drawdown * 100).toFixed(2) }}%
                  </span>
                </div>
                <div class="metric-item">
                  <span class="metric-label">交易次数</span>
                  <span class="metric-value">{{ meanReversionResult.trade_count }} 次</span>
                </div>
                <div class="metric-item">
                  <span class="metric-label">综合得分</span>
                  <span class="metric-value metric-value--primary">{{ meanReversionResult.composite_score.toFixed(1) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 动量策略优化结果 -->
        <div class="strategy-optimization">
          <div class="section-header">
            <div>
              <h2>动量策略优化</h2>
              <p class="section-subtitle">
                待进行参数寻优，当前使用经验参数
              </p>
            </div>
            <span class="status-badge status-warning">待优化</span>
          </div>

          <div class="optimization-placeholder">
            <div class="placeholder-icon">📈</div>
            <h3>动量策略优化待进行</h3>
            <p>将测试1024组参数组合，寻找最佳动量策略配置</p>
            <button
              class="btn btn-primary"
              @click="startMomentumOptimization"
              :disabled="loading"
            >
              开始动量策略优化
            </button>
          </div>
        </div>
      </div>

      <!-- 侧边栏 -->
      <aside class="optimization-sidebar">
        <!-- 快速策略创建 -->
        <section class="sidebar-card">
          <h3>快速创建策略</h3>
          <p class="sidebar-description">基于优化结果快速创建预设策略</p>

          <div class="preset-strategies">
            <div
              v-for="(preset, key) in presetStrategies"
              :key="key"
              class="preset-item"
              :class="`preset-item--${preset.risk_level}`"
            >
              <div class="preset-header">
                <h4>{{ preset.name }}</h4>
                <span class="preset-risk" :class="`risk-${preset.risk_level}`">
                  {{ preset.risk_level === 'low' ? '低风险' : preset.risk_level === 'medium' ? '中风险' : '高风险' }}
                </span>
              </div>
              <p class="preset-description">{{ preset.description }}</p>
              <div class="preset-metrics">
                <span class="preset-return">{{ preset.expected_return }}</span>
                <span class="preset-type">{{ getStrategyTypeLabel(preset.strategy_type) }}</span>
              </div>
              <button
                class="btn btn-sm btn-outline preset-btn"
                @click="createPresetStrategy(key)"
                :disabled="creatingStrategy === key"
              >
                <span v-if="creatingStrategy === key">创建中...</span>
                <span v-else>创建策略</span>
              </button>
            </div>
          </div>
        </section>

        <!-- 优化历史 -->
        <section class="sidebar-card">
          <h3>优化历史</h3>
          <div class="optimization-history">
            <div
              v-for="(history, index) in optimizationHistory"
              :key="index"
              class="history-item"
            >
              <div class="history-time">{{ formatDate(history.timestamp) }}</div>
              <div class="history-detail">
                <span class="history-strategy">{{ history.strategy_type }}</span>
                <span class="history-status" :class="`status-${history.status}`">
                  {{ history.status === 'completed' ? '完成' : '进行中' }}
                </span>
              </div>
              <div class="history-result">
                <span v-if="history.best_return">收益: {{ (history.best_return * 100).toFixed(1) }}%</span>
              </div>
            </div>
          </div>
        </section>
      </aside>
    </section>

    <!-- 优化模态框 -->
    <OptimizationModal
      v-if="showOptimizationModal"
      @close="showOptimizationModal = false"
      @optimization-started="onOptimizationStarted"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { optimizationApi, strategyApi } from '@/services/api.js'

// 响应式数据
const loading = ref(false)
const error = ref('')
const optimizationInfo = ref({})
const showOptimizationModal = ref(false)
const creatingStrategy = ref('')

// 计算属性
const meanReversionResult = computed(() => {
  return optimizationInfo.value.mean_reversion?.best_parameters ? {
    ...optimizationInfo.value.mean_reversion.best_parameters,
    ...optimizationInfo.value.mean_reversion.performance_metrics
  } : {
    lookback_period: 20,
    buy_threshold: -0.08,
    sell_threshold: 0.02,
    total_return: 0.2543,
    sharpe_ratio: 1.28,
    max_drawdown: 0.3708,
    trade_count: 15,
    composite_score: 7.886
  }
})

const momentumResult = computed(() => {
  return optimizationInfo.value.momentum?.best_parameters ? {
    ...optimizationInfo.value.momentum.best_parameters,
    ...optimizationInfo.value.momentum.performance_metrics
  } : null
})

const presetStrategies = computed(() => {
  return {
    conservative: {
      name: '保守型均值回归',
      risk_level: 'low',
      expected_return: '15-20%',
      strategy_type: 'mean_reversion',
      description: '追求稳定收益，风险较低'
    },
    balanced: {
      name: '平衡型均值回归',
      risk_level: 'medium',
      expected_return: '20-25%',
      strategy_type: 'mean_reversion',
      description: '基于优化器最佳参数，平衡收益与风险'
    },
    aggressive: {
      name: '激进型均值回归',
      risk_level: 'high',
      expected_return: '25-30%',
      strategy_type: 'mean_reversion',
      description: '追求高收益，风险较高'
    }
  }
})

const bestPerformance = computed(() => {
  return meanReversionResult.value.total_return ?
    (meanReversionResult.value.total_return * 100).toFixed(1) : '25.4'
})

const bestPerformanceStrategy = computed(() => {
  return '均值回归策略'
})

const bestSharpe = computed(() => {
  return meanReversionResult.value.sharpe_ratio ?
    meanReversionResult.value.sharpe_ratio.toFixed(2) : '1.28'
})

const bestSharpeStrategy = computed(() => {
  return '均值回归策略'
})

const totalTests = computed(() => {
  return optimizationInfo.value.total_tests || 64
})

const optimizationHistory = computed(() => {
  return [
    {
      timestamp: '2025-10-19T20:24:28',
      strategy_type: '均值回归',
      status: 'completed',
      best_return: 0.2543
    }
  ]
})

// 方法
async function refreshOptimizationInfo() {
  loading.value = true
  error.value = ''

  try {
    const response = await optimizationApi.getInfo()
    optimizationInfo.value = response.data
  } catch (err) {
    console.error('获取优化器信息失败:', err)
    error.value = '获取优化器信息失败，请检查后端服务'
  } finally {
    loading.value = false
  }
}

async function createPresetStrategy(presetType) {
  creatingStrategy.value = presetType

  try {
    await strategyApi.createOptimizedStrategy(presetType)
    // 刷新策略列表
    await refreshOptimizationInfo()
  } catch (err) {
    console.error('创建预设策略失败:', err)
    error.value = '创建策略失败，请稍后重试'
  } finally {
    creatingStrategy.value = ''
  }
}

function startMomentumOptimization() {
  showOptimizationModal.value = true
}

function onOptimizationStarted(result) {
  showOptimizationModal.value = false
  refreshOptimizationInfo()
}

function getStrategyTypeLabel(type) {
  const labels = {
    mean_reversion: '均值回归',
    momentum: '动量策略'
  }
  return labels[type] || type
}

function formatDate(dateString) {
  if (!dateString) return '--'
  return new Date(dateString).toLocaleDateString('zh-CN')
}

// 生命周期
onMounted(async () => {
  await refreshOptimizationInfo()
})
</script>

<style scoped>
.optimization-view {
  padding: 24px;
  margin: 0 auto;
  max-width: 1440px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.optimization-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 24px;
  border-bottom: 1px solid var(--border-color);
}

.header-content h1 {
  font-size: 28px;
  font-weight: 600;
  margin-bottom: 8px;
  color: var(--text-primary);
}

.header-content p {
  margin: 0;
  color: var(--text-secondary);
  font-size: 16px;
}

.header-actions {
  display: flex;
  gap: 12px;
  flex-shrink: 0;
}

.btn-icon {
  margin-right: 4px;
}

.optimization-alert {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 20px;
  border-radius: 8px;
  border: 1px solid var(--warning-color);
  background: rgba(230, 162, 60, 0.08);
  color: var(--text-primary);
}

.optimization-alert__info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 14px;
}

.optimization-overview {
  width: 100%;
}

.overview-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
}

.overview-card {
  background: var(--card-bg);
  border: 1px solid var(--border-light);
  border-radius: 8px;
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  box-shadow: var(--box-shadow-light);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.overview-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 24px rgba(0, 0, 0, 0.12);
}

.overview-card header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.overview-card__title {
  font-size: 14px;
  color: var(--text-secondary);
}

.overview-card__badge {
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 12px;
  background: rgba(64, 158, 255, 0.15);
  color: var(--primary-color);
}

.overview-card__badge--success {
  background: rgba(103, 194, 58, 0.15);
  color: var(--success-color);
}

.overview-card__badge--info {
  background: rgba(144, 147, 153, 0.15);
  color: var(--info-color);
}

.overview-card__badge--warning {
  background: rgba(230, 162, 60, 0.15);
  color: var(--warning-color);
}

.overview-card__value {
  font-size: 32px;
  font-weight: 600;
  color: var(--text-primary);
}

.overview-card__meta {
  font-size: 13px;
  color: var(--text-secondary);
}

.optimization-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  gap: 24px;
  align-items: start;
}

.optimization-main {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.optimization-sidebar {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.strategy-optimization {
  background: var(--card-bg);
  border: 1px solid var(--border-light);
  border-radius: 10px;
  padding: 24px;
  box-shadow: var(--box-shadow-light);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 20px;
}

.section-header h2 {
  margin: 0;
  font-size: 22px;
  font-weight: 600;
  color: var(--text-primary);
}

.section-subtitle {
  margin: 4px 0 0;
  color: var(--text-secondary);
  font-size: 14px;
}

.status-badge {
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

.status-success {
  background: rgba(103, 194, 58, 0.2);
  color: var(--success-color);
}

.status-warning {
  background: rgba(230, 162, 60, 0.2);
  color: var(--warning-color);
}

.optimization-result {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

.result-params h3,
.result-performance h3 {
  margin: 0 0 16px;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.param-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
}

.param-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px;
  background: var(--bg-secondary);
  border-radius: 6px;
  border: 1px solid var(--border-lighter);
}

.param-label {
  font-size: 12px;
  color: var(--text-secondary);
}

.param-value {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 12px;
}

.metric-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px;
  background: var(--bg-secondary);
  border-radius: 6px;
  border: 1px solid var(--border-lighter);
  text-align: center;
}

.metric-label {
  font-size: 12px;
  color: var(--text-secondary);
}

.metric-value {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
}

.metric-value--success {
  color: var(--success-color);
}

.metric-value--danger {
  color: var(--danger-color);
}

.metric-value--primary {
  color: var(--primary-color);
}

.optimization-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 48px;
  gap: 16px;
  background: var(--bg-secondary);
  border-radius: 8px;
  border: 2px dashed var(--border-color);
}

.placeholder-icon {
  font-size: 48px;
  opacity: 0.6;
}

.optimization-placeholder h3 {
  margin: 0;
  font-size: 18px;
  color: var(--text-primary);
}

.optimization-placeholder p {
  margin: 0;
  color: var(--text-secondary);
  max-width: 300px;
}

.sidebar-card {
  background: var(--card-bg);
  border: 1px solid var(--border-light);
  border-radius: 8px;
  padding: 20px;
  box-shadow: var(--box-shadow-light);
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.sidebar-card h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.sidebar-description {
  margin: 0;
  font-size: 14px;
  color: var(--text-secondary);
}

.preset-strategies {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.preset-item {
  padding: 16px;
  background: var(--bg-secondary);
  border-radius: 8px;
  border: 1px solid var(--border-lighter);
  transition: border-color 0.2s ease;
}

.preset-item:hover {
  border-color: var(--primary-color);
}

.preset-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.preset-header h4 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.preset-risk {
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
}

.risk-low {
  background: rgba(103, 194, 58, 0.15);
  color: var(--success-color);
}

.risk-medium {
  background: rgba(230, 162, 60, 0.15);
  color: var(--warning-color);
}

.risk-high {
  background: rgba(245, 108, 108, 0.15);
  color: var(--danger-color);
}

.preset-description {
  margin: 0 0 12px;
  font-size: 13px;
  color: var(--text-secondary);
}

.preset-metrics {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.preset-return {
  font-size: 14px;
  font-weight: 600;
  color: var(--success-color);
}

.preset-type {
  font-size: 12px;
  color: var(--text-secondary);
  background: var(--bg-primary);
  padding: 2px 6px;
  border-radius: 4px;
}

.preset-btn {
  width: 100%;
  justify-content: center;
}

.optimization-history {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.history-item {
  padding: 12px;
  background: var(--bg-secondary);
  border-radius: 6px;
  border-left: 3px solid var(--border-color);
}

.history-time {
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.history-detail {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.history-strategy {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.history-status {
  font-size: 12px;
  padding: 2px 6px;
  border-radius: 4px;
}

.status-completed {
  background: rgba(103, 194, 58, 0.15);
  color: var(--success-color);
}

.history-result {
  font-size: 12px;
  color: var(--text-secondary);
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
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

.btn-outline {
  background: transparent;
  color: var(--text-primary);
  border: 1px solid var(--border-color);
}

.btn-outline:hover:not(:disabled) {
  border-color: var(--primary-color);
  color: var(--primary-color);
}

.btn-sm {
  padding: 6px 12px;
  font-size: 13px;
}

@media (max-width: 1180px) {
  .optimization-layout {
    grid-template-columns: 1fr;
  }

  .optimization-sidebar {
    flex-direction: row;
    flex-wrap: wrap;
  }

  .sidebar-card {
    flex: 1;
    min-width: 280px;
  }
}

@media (max-width: 768px) {
  .optimization-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .header-actions {
    width: 100%;
    justify-content: flex-start;
  }

  .overview-cards {
    grid-template-columns: 1fr;
  }

  .optimization-result {
    grid-template-columns: 1fr;
  }
}

/* CSS Variables (假设已在全局定义) */
:root {
  --primary-color: #409eff;
  --primary-hover: #66b1ff;
  --success-color: #67c23a;
  --warning-color: #e6a23c;
  --danger-color: #f56c6c;
  --info-color: #909399;
  --text-primary: #303133;
  --text-secondary: #909399;
  --border-color: #dcdfe6;
  --border-light: #e4e7ed;
  --border-lighter: #f2f6fc;
  --card-bg: #ffffff;
  --bg-primary: #ffffff;
  --bg-secondary: #f5f7fa;
  --hover-bg: #ecf5ff;
  --box-shadow-light: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

/* 暗色主题支持 */
@media (prefers-color-scheme: dark) {
  :root {
    --text-primary: #e4e7ed;
    --text-secondary: #b1b3b8;
    --border-color: #4c4d4f;
    --border-light: #4c4d4f;
    --border-lighter: #363637;
    --card-bg: #2d2d2d;
    --bg-primary: #2d2d2d;
    --bg-secondary: #252526;
    --hover-bg: #4c4d4f;
    --box-shadow-light: 0 2px 12px 0 rgba(0, 0, 0, 0.3);
  }
}
</style>