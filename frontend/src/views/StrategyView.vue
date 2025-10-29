<template>
  <div class="strategy-view">
    <header class="strategy-header">
      <div class="header-content">
        <h1>策略管理</h1>
        <p>统一查看与维护智能投顾策略，实时掌握运行状态与信号</p>
      </div>

      <div class="header-actions">
        <button
          class="btn btn-primary"
          @click="showCreateModal = true"
          :disabled="loading"
        >
          <span class="btn-icon">＋</span>
          创建策略
        </button>
        <button
          class="btn btn-secondary"
          @click="refreshData"
          :disabled="loading"
        >
          刷新
        </button>
      </div>
    </header>

    <transition name="fade">
      <div v-if="error" class="strategy-alert">
        <div class="strategy-alert__info">
          <strong>数据加载异常</strong>
          <span>{{ error }}</span>
        </div>
        <button
          class="btn btn-sm btn-outline"
          @click="refreshData"
          :disabled="loading"
        >
          重新尝试
        </button>
      </div>
    </transition>

    <section class="strategy-overview">
      <div class="overview-cards">
        <article class="overview-card">
          <header>
            <span class="overview-card__title">策略总量</span>
            <span class="overview-card__badge">总览</span>
          </header>
          <div class="overview-card__value">{{ strategyCount }}</div>
          <p class="overview-card__meta">
            活跃 {{ activeStrategies.length }} · 暂停 {{ pausedCount }}
          </p>
        </article>

        <article class="overview-card">
          <header>
            <span class="overview-card__title">活跃率</span>
            <span class="overview-card__badge">健康度</span>
          </header>
          <div class="overview-card__value">
            {{ strategyCount ? `${activeRatio}%` : '--' }}
          </div>
          <p class="overview-card__meta">{{ lastUpdatedLabel }}</p>
        </article>

        <article class="overview-card">
          <header>
            <span class="overview-card__title">待关注策略</span>
            <span class="overview-card__badge overview-card__badge--warning">提醒</span>
          </header>
          <div class="overview-card__value">{{ pausedCount + stoppedCount }}</div>
          <p class="overview-card__meta">
            暂停 {{ pausedCount }} · 停止 {{ stoppedCount }}
          </p>
        </article>

        <article class="overview-card">
          <header>
            <span class="overview-card__title">今日信号</span>
            <span class="overview-card__badge overview-card__badge--info">实时</span>
          </header>
          <div class="overview-card__value">{{ signalStats.total }}</div>
          <p class="overview-card__meta">
            买入 {{ signalStats.buy }} · 卖出 {{ signalStats.sell }}
          </p>
        </article>
      </div>
    </section>

    <section class="strategy-layout">
      <div class="strategy-main">
        <section class="strategy-list">
          <div class="section-header">
            <div>
              <h2>策略列表</h2>
              <p class="section-subtitle">
                根据状态筛选并快速执行日常操作
              </p>
            </div>

            <div class="filter-controls">
              <select v-model="statusFilter" class="filter-select">
                <option value="">全部状态</option>
                <option value="active">活跃</option>
                <option value="paused">暂停</option>
                <option value="stopped">停止</option>
              </select>
            </div>
          </div>

          <div
            v-if="!loading && hasStrategies"
            class="strategy-cards"
          >
            <article
              v-for="strategy in filteredStrategies"
              :key="strategy.id"
              class="strategy-card"
              :class="{ 'strategy-card--inactive': strategy.status !== 'active' }"
            >
              <header class="card-header">
                <div class="card-header__info">
                  <h3>{{ strategy.name }}</h3>
                  <span class="card-subtitle">
                    ID: {{ strategy.id.slice(0, 8) }} · {{ getStrategyTypeLabel(strategy.strategy_type) }}
                  </span>
                </div>
                <span class="status-badge" :class="getStatusClass(strategy.status)">
                  {{ getStatusText(strategy.status) }}
                </span>
              </header>

              <div class="card-body">
                <div class="info-grid">
                  <div class="info-block">
                    <span class="info-label">调仓频率</span>
                    <span class="info-value">{{ strategy.rebalance_frequency }} 日</span>
                  </div>
                  <div class="info-block">
                    <span class="info-label">创建时间</span>
                    <span class="info-value">{{ formatDate(strategy.created_at) }}</span>
                  </div>
                  <div class="info-block">
                    <span class="info-label">最近更新</span>
                    <span class="info-value">
                      {{ formatDate(strategy.updated_at || strategy.created_at) }}
                    </span>
                  </div>
                  <div class="info-block">
                    <span class="info-label">股票池数量</span>
                    <span class="info-value">
                      {{ Array.isArray(strategy.stock_pool) ? strategy.stock_pool.length : 0 }} 只
                    </span>
                  </div>
                </div>

                <div class="stock-preview">
                  <span class="info-label">股票池示例</span>
                  <div class="stock-chips" v-if="Array.isArray(strategy.stock_pool) && strategy.stock_pool.length">
                    <span
                      v-for="code in getStockPoolPreview(strategy.stock_pool)"
                      :key="code"
                      class="stock-chip"
                    >
                      {{ code }}
                    </span>
                    <span
                      v-if="getStockPoolOverflow(strategy.stock_pool)"
                      class="stock-chip stock-chip--more"
                    >
                      +{{ getStockPoolOverflow(strategy.stock_pool) }}
                    </span>
                  </div>
                  <span v-else class="info-placeholder">尚未配置股票池</span>
                </div>

                <div class="strategy-params">
                  <h4>参数配置</h4>
                  <div class="param-chips">
                    <span
                      v-for="(value, key) in strategy.parameters"
                      :key="key"
                      class="param-chip"
                    >
                      <span class="param-chip__key">{{ getParamLabel(key) }}</span>
                      <span class="param-chip__value">{{ formatParamValue(key, value) }}</span>
                    </span>
                  </div>
                </div>
              </div>

              <footer class="card-actions">
                <button
                  class="btn btn-sm btn-outline"
                  @click="viewStrategy(strategy)"
                >
                  查看详情
                </button>
                <button
                  class="btn btn-sm btn-outline"
                  @click="generateStrategySignals(strategy.id)"
                  :disabled="loading || strategy.status !== 'active'"
                >
                  生成信号
                </button>
                <button
                  class="btn btn-sm btn-outline"
                  @click="editStrategy(strategy)"
                >
                  编辑
                </button>
                <button
                  class="btn btn-sm btn-danger"
                  @click="deleteStrategyConfirm(strategy)"
                >
                  删除
                </button>
              </footer>
            </article>
          </div>

          <div v-else-if="loading" class="loading-state">
            <div class="loading-spinner"></div>
            <p>加载中...</p>
          </div>

          <div v-else class="empty-state">
            <p>
              {{ statusFilter ? '没有符合条件的策略' : '暂无策略，马上创建第一个策略以开始跟踪' }}
            </p>
          </div>
        </section>
      </div>

      <aside class="strategy-sidebar">
        <section class="sidebar-card">
          <h3>运行概况</h3>
          <ul class="sidebar-metrics">
            <li>
              <span>活跃率</span>
              <strong>{{ strategyCount ? `${activeRatio}%` : '--' }}</strong>
            </li>
            <li>
              <span>暂停策略</span>
              <strong>{{ pausedCount }}</strong>
            </li>
            <li>
              <span>停止策略</span>
              <strong>{{ stoppedCount }}</strong>
            </li>
            <li>
              <span>最近更新</span>
              <strong>{{ lastUpdatedLabel }}</strong>
            </li>
          </ul>
        </section>

        <section class="latest-signals sidebar-card">
          <div class="latest-signals__header">
            <div>
              <h2>最新信号</h2>
              <p class="latest-signals__summary">
                今日 {{ signalStats.total }} 条 · 买入 {{ signalStats.buy }} · 卖出 {{ signalStats.sell }}
              </p>
            </div>
            <button
              class="btn btn-sm btn-outline"
              @click="refreshSignals"
              :disabled="loading"
            >
              刷新
            </button>
          </div>

          <div class="signals-grid">
            <section class="signals-section">
              <h3>买入信号</h3>
              <div class="signal-list" v-if="latestBuySignals.length">
                <article
                  v-for="signal in latestBuySignals.slice(0, 5)"
                  :key="signal.id"
                  class="signal-item signal-item--buy"
                >
                  <div class="signal-header">
                    <span class="stock-code">{{ signal.stock_code }}</span>
                    <span class="signal-confidence">
                      置信度 {{ (signal.confidence * 100).toFixed(1) }}%
                    </span>
                  </div>
                  <div class="signal-price">¥{{ signal.price.toFixed(2) }}</div>
                  <div class="signal-time">{{ formatTime(signal.timestamp) }}</div>
                </article>
              </div>
              <p v-else class="no-signals">暂无买入信号</p>
            </section>

            <section class="signals-section">
              <h3>卖出信号</h3>
              <div class="signal-list" v-if="latestSellSignals.length">
                <article
                  v-for="signal in latestSellSignals.slice(0, 5)"
                  :key="signal.id"
                  class="signal-item signal-item--sell"
                >
                  <div class="signal-header">
                    <span class="stock-code">{{ signal.stock_code }}</span>
                    <span class="signal-confidence">
                      置信度 {{ (signal.confidence * 100).toFixed(1) }}%
                    </span>
                  </div>
                  <div class="signal-price">¥{{ signal.price.toFixed(2) }}</div>
                  <div class="signal-time">{{ formatTime(signal.timestamp) }}</div>
                </article>
              </div>
              <p v-else class="no-signals">暂无卖出信号</p>
            </section>
          </div>
        </section>
      </aside>
    </section>

    <CreateStrategyModal
      v-if="showCreateModal"
      @close="showCreateModal = false"
      @created="onStrategyCreated"
    />

    <StrategyDetailModal
      v-if="showDetailModal"
      :strategy="selectedStrategy"
      @close="showDetailModal = false"
    />

    <EditStrategyModal
      v-if="showEditModal"
      :strategy="selectedStrategy"
      @close="showEditModal = false"
      @updated="onStrategyUpdated"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useStrategyStore } from '@/stores/strategy.js'
import CreateStrategyModal from '@/components/strategy/CreateStrategyModal.vue'
import StrategyDetailModal from '@/components/strategy/StrategyDetailModal.vue'
import EditStrategyModal from '@/components/strategy/EditStrategyModal.vue'

const strategyStore = useStrategyStore()

const statusFilter = ref('')
const showCreateModal = ref(false)
const showDetailModal = ref(false)
const showEditModal = ref(false)
const selectedStrategy = ref(null)
const refreshInterval = ref(null)

const loading = computed(() => strategyStore.loading)
const error = computed(() => strategyStore.error)
const strategies = computed(() => strategyStore.strategies)
const activeStrategies = computed(() => strategyStore.activeStrategies)
const inactiveStrategies = computed(() => strategyStore.inactiveStrategies)
const strategyCount = computed(() => strategyStore.strategyCount)
const latestSignals = computed(() => strategyStore.latestSignals)
const latestBuySignals = computed(() => strategyStore.latestBuySignals)
const latestSellSignals = computed(() => strategyStore.latestSellSignals)

const pausedCount = computed(
  () => strategies.value.filter(item => item.status === 'paused').length
)
const stoppedCount = computed(
  () => strategies.value.filter(item => item.status === 'stopped').length
)
const activeRatio = computed(() => {
  const total = strategyCount.value
  if (!total) {
    return 0
  }
  return Math.round((activeStrategies.value.length / total) * 100)
})
const signalStats = computed(() => ({
  total: latestSignals.value.length,
  buy: latestBuySignals.value.length,
  sell: latestSellSignals.value.length
}))
const lastUpdatedAt = computed(() => {
  const timestamps = strategies.value
    .map(item => item.updated_at || item.created_at)
    .filter(Boolean)
  if (!timestamps.length) {
    return null
  }
  return new Date(
    Math.max(...timestamps.map(date => new Date(date).getTime()))
  )
})
const lastUpdatedLabel = computed(() => {
  if (!lastUpdatedAt.value) {
    return '等待首批数据'
  }
  const diff = Date.now() - lastUpdatedAt.value.getTime()
  if (diff < 60 * 1000) {
    return '刚刚更新'
  }
  if (diff < 60 * 60 * 1000) {
    const minutes = Math.floor(diff / 60000)
    return `${minutes} 分钟前更新`
  }
  return `更新于 ${lastUpdatedAt.value.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit'
  })}`
})

const filteredStrategies = computed(() => {
  if (!statusFilter.value) {
    return strategies.value
  }
  return strategies.value.filter(
    strategy => strategy.status === statusFilter.value
  )
})
const hasStrategies = computed(() => filteredStrategies.value.length > 0)

async function refreshData() {
  try {
    await Promise.all([
      strategyStore.fetchStrategies(),
      strategyStore.fetchLatestSignals()
    ])
  } catch (err) {
    console.error('刷新数据失败:', err)
  }
}

async function refreshSignals() {
  try {
    await strategyStore.fetchLatestSignals()
  } catch (err) {
    console.error('刷新信号失败:', err)
  }
}

function viewStrategy(strategy) {
  selectedStrategy.value = strategy
  showDetailModal.value = true
}

function editStrategy(strategy) {
  selectedStrategy.value = strategy
  showEditModal.value = true
}

async function deleteStrategyConfirm(strategy) {
  if (!window.confirm(`确认删除策略「${strategy.name}」吗？`)) {
    return
  }
  try {
    await strategyStore.deleteStrategy(strategy.id)
    await refreshData()
  } catch (err) {
    console.error('删除策略失败:', err)
  }
}

async function onStrategyCreated() {
  showCreateModal.value = false
  await refreshData()
}

async function onStrategyUpdated() {
  showEditModal.value = false
  await refreshData()
}

function getStatusClass(status) {
  const classes = {
    active: 'status-success',
    paused: 'status-warning',
    stopped: 'status-danger',
    error: 'status-danger'
  }
  return classes[status] || 'status-warning'
}

function getStatusText(status) {
  const texts = {
    active: '活跃',
    paused: '暂停',
    stopped: '停止',
    error: '错误'
  }
  return texts[status] || status
}

function getStrategyTypeLabel(type) {
  const labels = {
    mean_reversion: '均值回归',
    momentum: '动量策略',
    value: '价值投资'
  }
  return labels[type] || type
}

function getParamLabel(key) {
  const labels = {
    lookback_period: '回看周期',
    buy_threshold: '买入阈值',
    sell_threshold: '卖出阈值',
    max_hold_days: '最大持有天数',
    momentum_period: '动量周期',
    profit_target: '止盈目标'
  }
  return labels[key] || key
}

function formatParamValue(key, value) {
  if (key.includes('threshold') || key === 'profit_target') {
    return `${(value * 100).toFixed(1)}%`
  }
  if (key.includes('days')) {
    return `${value} 日`
  }
  return value
}

function formatDate(dateString) {
  if (!dateString) {
    return '--'
  }
  return new Date(dateString).toLocaleDateString('zh-CN')
}

function formatTime(dateString) {
  return new Date(dateString).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit'
  })
}

function getStockPoolPreview(stockPool) {
  if (!Array.isArray(stockPool)) {
    return []
  }
  return stockPool.slice(0, 4)
}

function getStockPoolOverflow(stockPool) {
  if (!Array.isArray(stockPool)) {
    return 0
  }
  return Math.max(stockPool.length - 4, 0)
}

function generateStrategySignals(strategyId) {
  strategyStore.generateStrategySignals(strategyId)
}

onMounted(async () => {
  await refreshData()
  refreshInterval.value = setInterval(async () => {
    await refreshSignals()
  }, 30000)
})

onUnmounted(() => {
  if (refreshInterval.value) {
    clearInterval(refreshInterval.value)
  }
})
</script>

<style scoped>
.strategy-view {
  padding: 24px;
  margin: 0 auto;
  max-width: 1440px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.strategy-header {
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
  font-size: 16px;
}

.strategy-alert {
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

.strategy-alert__info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 14px;
}

.strategy-overview {
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

.overview-card__badge--warning {
  background: rgba(230, 162, 60, 0.18);
  color: var(--warning-color);
}

.overview-card__badge--info {
  background: rgba(144, 147, 153, 0.2);
  color: var(--info-color);
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

.strategy-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  gap: 24px;
  align-items: start;
}

.strategy-main {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.strategy-sidebar {
  display: flex;
  flex-direction: column;
  gap: 20px;
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

.sidebar-metrics {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  font-size: 14px;
}

.sidebar-metrics li {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: var(--text-secondary);
}

.sidebar-metrics strong {
  color: var(--text-primary);
  font-weight: 600;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
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

.filter-controls {
  flex-shrink: 0;
}

.filter-select {
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--input-bg);
  color: var(--text-primary);
  min-width: 140px;
  font-weight: 500;
}

.filter-select:focus {
  border-color: var(--primary-color);
  outline: none;
  box-shadow: 0 0 0 3px rgba(64, 158, 255, 0.15);
}

.strategy-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(380px, 1fr));
  gap: 18px;
}

.strategy-card {
  background: var(--card-bg);
  border: 1px solid var(--border-light);
  border-radius: 10px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 18px;
  box-shadow: var(--box-shadow-light);
  transition: border 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
}

.strategy-card:hover {
  border-color: var(--primary-color);
  transform: translateY(-2px);
  box-shadow: 0 14px 28px rgba(0, 0, 0, 0.12);
}

.strategy-card--inactive {
  opacity: 0.82;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.card-header__info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.card-header__info h3 {
  margin: 0;
  font-size: 20px;
  color: var(--text-primary);
}

.card-subtitle {
  font-size: 13px;
  color: var(--text-secondary);
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

.status-danger {
  background: rgba(245, 108, 108, 0.2);
  color: var(--danger-color);
}

.card-body {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}

.info-block {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-label {
  font-size: 12px;
  color: var(--text-secondary);
}

.info-value {
  font-size: 15px;
  color: var(--text-primary);
  font-weight: 600;
}

.info-placeholder {
  font-size: 13px;
  color: var(--text-secondary);
  font-style: italic;
}

.stock-preview {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stock-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.stock-chip {
  padding: 4px 8px;
  background: var(--bg-secondary);
  border-radius: 6px;
  font-size: 12px;
  color: var(--text-primary);
  border: 1px solid var(--border-lighter);
}

.stock-chip--more {
  background: rgba(64, 158, 255, 0.15);
  color: var(--primary-color);
  border-color: rgba(64, 158, 255, 0.25);
}

.strategy-params h4 {
  margin: 0 0 8px;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.param-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.param-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(64, 158, 255, 0.12);
  color: var(--primary-color);
  font-size: 12px;
}

.param-chip__key {
  font-weight: 600;
}

.param-chip__value {
  color: var(--text-primary);
  font-weight: 600;
}

.card-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}

.latest-signals__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.latest-signals__header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.latest-signals__summary {
  margin: 6px 0 0;
  font-size: 13px;
  color: var(--text-secondary);
}

.signals-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.signals-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.signals-section h3 {
  margin: 0;
  font-size: 15px;
  color: var(--text-primary);
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-lighter);
}

.signal-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 320px;
  overflow-y: auto;
  padding-right: 4px;
}

.signal-item {
  padding: 10px 12px;
  border-radius: 8px;
  border-left: 4px solid var(--border-color);
  background: var(--bg-secondary);
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.signal-item--buy {
  border-left-color: var(--success-color);
}

.signal-item--sell {
  border-left-color: var(--danger-color);
}

.signal-header {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: var(--text-secondary);
}

.stock-code {
  font-weight: 600;
  color: var(--text-primary);
}

.signal-price {
  font-weight: 700;
  color: var(--text-primary);
  font-size: 15px;
}

.signal-time {
  font-size: 12px;
  color: var(--text-secondary);
}

.no-signals {
  text-align: center;
  color: var(--text-secondary);
  padding: 16px;
  font-size: 13px;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 40px;
  color: var(--text-secondary);
}

.loading-spinner {
  width: 36px;
  height: 36px;
  border: 3px solid var(--border-light);
  border-top-color: var(--primary-color);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

.empty-state {
  text-align: center;
  padding: 48px 16px;
  color: var(--text-secondary);
  background: var(--bg-secondary);
  border-radius: 8px;
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

.btn-danger {
  background: rgba(245, 108, 108, 0.12);
  color: var(--danger-color);
  border: 1px solid rgba(245, 108, 108, 0.35);
}

.btn-danger:hover:not(:disabled) {
  background: rgba(245, 108, 108, 0.18);
}

.btn-sm {
  padding: 6px 12px;
  font-size: 13px;
}

@media (max-width: 1180px) {
  .strategy-layout {
    grid-template-columns: 1fr;
  }

  .strategy-sidebar {
    flex-direction: row;
    flex-wrap: wrap;
  }

  .sidebar-card {
    flex: 1;
    min-width: 280px;
  }
}

@media (max-width: 768px) {
  .strategy-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .header-actions {
    width: 100%;
    justify-content: flex-start;
  }

  .strategy-cards {
    grid-template-columns: 1fr;
  }

  .signals-grid {
    grid-template-columns: 1fr;
  }
}
</style>
