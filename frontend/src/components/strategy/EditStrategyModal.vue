<template>
  <teleport to="body">
    <div class="modal-overlay" @click="closeModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h2>编辑策略</h2>
          <button class="close-btn" @click="closeModal">
            <i class="icon-close"></i>
          </button>
        </div>

        <form @submit.prevent="handleSubmit" class="strategy-form">
          <!-- 基本信息 -->
          <section class="form-section">
            <h3>基本信息</h3>
            <div class="form-group">
              <label for="strategy-name">策略名称 *</label>
              <input
                id="strategy-name"
                v-model="formData.name"
                type="text"
                required
                class="form-input"
              />
            </div>

            <div class="form-group">
              <label for="strategy-status">策略状态</label>
              <select
                id="strategy-status"
                v-model="formData.status"
                class="form-select"
              >
                <option value="active">活跃</option>
                <option value="paused">暂停</option>
                <option value="stopped">停止</option>
              </select>
            </div>
          </section>

          <!-- 参数配置 -->
          <section class="form-section">
            <h3>参数配置</h3>
            <div class="parameters-grid">
              <div
                v-for="(param, key) in formData.parameters"
                :key="key"
                class="form-group"
              >
                <label :for="key">{{ getParamLabel(key) }}</label>
                <div v-if="key.includes('threshold')" class="threshold-input">
                  <input
                    :id="key"
                    v-model.number="formData.parameters[key]"
                    type="number"
                    :step="0.01"
                    class="form-input"
                  />
                  <span class="input-suffix">{{ (formData.parameters[key] * 100).toFixed(1) }}%</span>
                </div>
                <div v-else-if="key.includes('days')" class="days-input">
                  <input
                    :id="key"
                    v-model.number="formData.parameters[key]"
                    type="number"
                    :min="1"
                    :max="60"
                    class="form-input"
                  />
                  <span class="input-suffix">天</span>
                </div>
                <input
                  v-else
                  :id="key"
                  v-model.number="formData.parameters[key]"
                  type="number"
                  class="form-input"
                />
              </div>
            </div>
          </section>

          <!-- 股票池配置 -->
          <section class="form-section">
            <h3>股票池配置</h3>
            <div class="custom-stocks">
              <label>股票代码</label>
              <div class="stock-input-group">
                <input
                  v-model="stockInput"
                  type="text"
                  placeholder="输入股票代码，如：000001"
                  class="form-input"
                  @keyup.enter="addStock"
                />
                <button
                  type="button"
                  class="btn btn-secondary"
                  @click="addStock"
                >
                  添加
                </button>
              </div>

              <div class="selected-stocks" v-if="formData.stock_pool.length">
                <div class="stocks-list">
                  <div
                    v-for="(stock, index) in formData.stock_pool"
                    :key="stock"
                    class="stock-tag"
                  >
                    {{ stock }}
                    <button
                      type="button"
                      class="remove-stock"
                      @click="removeStock(index)"
                    >
                      <i class="icon-close"></i>
                    </button>
                  </div>
                </div>
              </div>

              <div class="stock-count">
                已选择 {{ formData.stock_pool.length }} 只股票
              </div>
            </div>
          </section>

          <!-- 调频配置 -->
          <section class="form-section">
            <h3>调频配置</h3>
            <div class="form-group">
              <label for="rebalance-freq">调频周期</label>
              <select
                id="rebalance-freq"
                v-model.number="formData.rebalance_frequency"
                class="form-select"
              >
                <option :value="5">5日调频</option>
                <option :value="10">10日调频</option>
                <option :value="20">20日调频</option>
              </select>
            </div>
          </section>

          <!-- 表单操作 -->
          <div class="form-actions">
            <button
              type="button"
              class="btn btn-secondary"
              @click="closeModal"
              :disabled="loading"
            >
              取消
            </button>
            <button
              type="submit"
              class="btn btn-primary"
              :disabled="loading || !isFormValid"
            >
              <span v-if="loading">保存中...</span>
              <span v-else>保存更改</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  </teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useStrategyStore } from '@/stores/strategy.js'

const props = defineProps({
  strategy: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['close', 'updated'])

const strategyStore = useStrategyStore()
const loading = ref(false)
const stockInput = ref('')

// 表单数据
const formData = ref({
  name: '',
  status: 'active',
  parameters: {},
  stock_pool: [],
  rebalance_frequency: 10
})

// 计算属性
const isFormValid = computed(() => {
  return formData.value.name.trim() &&
         formData.value.stock_pool.length > 0 &&
         formData.value.rebalance_frequency > 0
})

// 方法
function closeModal() {
  emit('close')
}

function addStock() {
  const stock = stockInput.value.trim().toUpperCase()
  if (stock && !formData.value.stock_pool.includes(stock)) {
    formData.value.stock_pool.push(stock)
    stockInput.value = ''
  }
}

function removeStock(index) {
  formData.value.stock_pool.splice(index, 1)
}

async function handleSubmit() {
  if (!isFormValid.value) return

  loading.value = true

  try {
    const updateData = {
      name: formData.value.name,
      status: formData.value.status,
      parameters: formData.value.parameters,
      stock_pool: formData.value.stock_pool,
      rebalance_frequency: formData.value.rebalance_frequency
    }

    await strategyStore.updateStrategy(props.strategy.id, updateData)
    emit('updated')
    closeModal()
  } catch (error) {
    console.error('更新策略失败:', error)
    alert('更新策略失败: ' + error.message)
  } finally {
    loading.value = false
  }
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

// 初始化表单数据
function initializeForm() {
  if (props.strategy) {
    formData.value = {
      name: props.strategy.name,
      status: props.strategy.status,
      parameters: { ...props.strategy.parameters },
      stock_pool: [...props.strategy.stock_pool],
      rebalance_frequency: props.strategy.rebalance_frequency
    }
  }
}

// 监听策略变化
watch(() => props.strategy, initializeForm, { immediate: true })
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
  max-width: 700px;
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

.strategy-form {
  padding: 0 24px 24px;
}

.form-section {
  margin-bottom: 32px;
}

.form-section h3 {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-color);
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
  color: var(--text-primary);
}

.form-input,
.form-select {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: var(--input-bg);
  color: var(--text-primary);
  font-size: 14px;
}

.form-input:focus,
.form-select:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
}

.parameters-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
}

.threshold-input,
.days-input {
  display: flex;
  align-items: center;
  gap: 8px;
}

.threshold-input .form-input,
.days-input .form-input {
  flex: 1;
}

.input-suffix {
  color: var(--text-secondary);
  font-size: 14px;
  min-width: 40px;
  text-align: right;
}

.custom-stocks {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.stock-input-group {
  display: flex;
  gap: 12px;
}

.stock-input-group .form-input {
  flex: 1;
}

.selected-stocks {
  margin-bottom: 8px;
}

.stocks-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.stock-tag {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  background: var(--primary-color);
  color: white;
  border-radius: 4px;
  font-size: 14px;
}

.remove-stock {
  background: none;
  border: none;
  color: white;
  cursor: pointer;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
}

.remove-stock:hover {
  background: rgba(255, 255, 255, 0.3);
}

.stock-count {
  font-size: 14px;
  color: var(--text-secondary);
}

.form-actions {
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