<template>
  <teleport to="body">
    <div class="modal-overlay" @click="closeModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h2>策略详情</h2>
          <button class="close-btn" @click="closeModal">
            <i class="icon-close"></i>
          </button>
        </div>

        <div class="strategy-detail" v-if="strategy">
          <!-- 基本信息 -->
          <section class="detail-section">
            <h3>基本信息</h3>
            <div class="detail-grid">
              <div class="detail-item">
                <label>策略名称:</label>
                <span>{{ strategy.name }}</span>
              </div>
              <div class="detail-item">
                <label>策略类型:</label>
                <span>{{ getStrategyTypeLabel(strategy.strategy_type) }}</span>
              </div>
              <div class="detail-item">
                <label>状态:</label>
                <span class="status-badge" :class="getStatusClass(strategy.status)">
                  {{ getStatusText(strategy.status) }}
                </span>
              </div>
              <div class="detail-item">
                <label>创建时间:</label>
                <span>{{ formatDate(strategy.created_at) }}</span>
              </div>
              <div class="detail-item">
                <label>更新时间:</label>
                <span>{{ formatDate(strategy.updated_at) }}</span>
              </div>
            </div>
          </section>

          <!-- 参数配置 -->
          <section class="detail-section">
            <h3>参数配置</h3>
            <div class="params-grid">
              <div
                v-for="(value, key) in strategy.parameters"
                :key="key"
                class="param-item"
              >
                <label>{{ getParamLabel(key) }}:</label>
                <span>{{ formatParamValue(key, value) }}</span>
              </div>
            </div>
          </section>

          <!-- 股票池 -->
          <section class="detail-section">
            <h3>股票池 ({{ strategy.stock_pool.length }} 只)</h3>
            <div class="stock-pool">
              <span
                v-for="stock in strategy.stock_pool"
                :key="stock"
                class="stock-tag"
              >
                {{ stock }}
              </span>
            </div>
          </section>

          <!-- 调频配置 -->
          <section class="detail-section">
            <h3>调频配置</h3>
            <div class="rebalance-info">
              <div class="detail-item">
                <label>调频周期:</label>
                <span>{{ strategy.rebalance_frequency }} 日</span>
              </div>
            </div>
          </section>

          <!-- 性能指标 -->
          <section class="detail-section">
            <h3>性能指标</h3>
            <div class="performance-grid">
              <div class="metric-item">
                <label>生成信号数:</label>
                <span>{{ performance.signals_generated || 0 }}</span>
              </div>
              <div class="metric-item">
                <label>成功交易数:</label>
                <span>{{ performance.successful_trades || 0 }}</span>
              </div>
              <div class="metric-item">
                <label>总收益率:</label>
                <span>{{ (performance.total_return || 0).toFixed(2) }}%</span>
              </div>
              <div class="metric-item">
                <label>夏普比率:</label>
                <span>{{ (performance.sharpe_ratio || 0).toFixed(2) }}</span>
              </div>
              <div class="metric-item">
                <label>最大回撤:</label>
                <span>{{ (performance.max_drawdown || 0).toFixed(2) }}%</span>
              </div>
            </div>
          </section>

          <!-- 操作按钮 -->
          <div class="modal-actions">
            <button
              class="btn btn-primary"
              @click="generateSignals"
              :disabled="loading || strategy.status !== 'active'"
            >
              生成信号
            </button>
            <button
              class="btn btn-secondary"
              @click="closeModal"
            >
              关闭
            </button>
          </div>
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useStrategyStore } from '@/stores/strategy.js'

const props = defineProps({
  strategy: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['close'])

const strategyStore = useStrategyStore()
const loading = ref(false)

const performance = computed(() => {
  return strategyStore.getStrategyPerformance(props.strategy.id)
})

// 方法
function closeModal() {
  emit('close')
}

function getStatusClass(status) {
  const classes = {
    active: 'status-success',
    paused: 'status-warning',
    stopped: 'status-danger',
    error: 'status-danger'
  }
  return classes[status] || 'status-secondary'
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
    max_hold_days: '最大持有'
  }
  return labels[key] || key
}

function formatParamValue(key, value) {
  if (key.includes('threshold')) {
    return (value * 100).toFixed(1) + '%'
  }
  if (key.includes('days')) {
    return value + '天'
  }
  return value
}

function formatDate(dateString) {
  return new Date(dateString).toLocaleString('zh-CN')
}

async function generateSignals() {
  loading.value = true
  try {
    await strategyStore.generateSignals(props.strategy.id)
    alert('信号生成成功！')
    await strategyStore.fetchStrategyPerformance(props.strategy.id)
  } catch (err) {
    console.error('生成信号失败:', err)
    alert('生成信号失败: ' + err.message)
  } finally {
    loading.value = false
  }
}

// 生命周期
onMounted(async () => {
  if (props.strategy) {
    await strategyStore.fetchStrategyPerformance(props.strategy.id)
  }
})
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.modal-content {
  background: var(--card-bg);
  border-radius: 8px;
  max-width: 600px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px 24px 0;
  margin-bottom: 24px;
}

.modal-header h2 {
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.close-btn {
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  color: var(--text-secondary);
  padding: 4px;
}

.close-btn:hover {
  color: var(--text-primary);
}

.strategy-detail {
  padding: 0 24px 24px;
}

.detail-section {
  margin-bottom: 32px;
}

.detail-section h3 {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-color);
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.detail-item label {
  color: var(--text-secondary);
  font-weight: 500;
}

.detail-item span {
  color: var(--text-primary);
  font-weight: 600;
}

.status-badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.status-success {
  background: #d4edda;
  color: #155724;
}

.status-warning {
  background: #fff3cd;
  color: #856404;
}

.status-danger {
  background: #f8d7da;
  color: #721c24;
}

.params-grid,
.performance-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.param-item,
.metric-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: var(--input-bg);
  border-radius: 4px;
}

.param-item label,
.metric-item label {
  color: var(--text-secondary);
  font-weight: 500;
}

.param-item span,
.metric-item span {
  color: var(--text-primary);
  font-weight: 600;
}

.stock-pool {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.stock-tag {
  padding: 6px 12px;
  background: var(--primary-color);
  color: white;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 500;
}

.rebalance-info {
  background: var(--input-bg);
  padding: 16px;
  border-radius: 4px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 24px;
  border-top: 1px solid var(--border-color);
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary {
  background: var(--primary-color);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: var(--primary-hover);
}

.btn-secondary {
  background: var(--secondary-color);
  color: white;
}

.btn-secondary:hover:not(:disabled) {
  background: var(--secondary-hover);
}
</style>