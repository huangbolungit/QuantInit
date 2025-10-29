<template>
  <teleport to="body">
    <div class="modal-overlay" @click="closeModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h2>创建新策略</h2>
          <button class="close-btn" @click="closeModal">
            <i class="icon-close"></i>
          </button>
        </div>

        <form @submit.prevent="handleSubmit" class="strategy-form">
          <!-- 基本信息 -->
          <section class="form-section">
            <h3>基本信息</h3>
            <div class="form-grid">
              <div class="form-group">
                <label for="strategy-name">策略名称 *</label>
                <input
                  id="strategy-name"
                  v-model="formData.name"
                  type="text"
                  required
                  placeholder="请输入策略名称"
                  class="form-input"
                />
              </div>

              <div class="form-group">
                <label for="strategy-type">策略类型 *</label>
                <select
                  id="strategy-type"
                  v-model="formData.strategy_type"
                  required
                  class="form-select"
                  @change="onStrategyTypeChange"
                >
                  <option value="">请选择策略类型</option>
                  <option
                    v-for="type in strategyTypes"
                    :key="type.value"
                    :value="type.value"
                  >
                    {{ type.label }}
                  </option>
                </select>
              </div>
            </div>

            <div class="form-group" v-if="selectedStrategyType">
              <label>策略描述</label>
              <div class="strategy-description">
                {{ selectedStrategyType.description }}
              </div>
            </div>
          </section>

          <!-- 参数配置 -->
          <section class="form-section" v-if="selectedStrategyType">
            <h3>参数配置</h3>
            <div class="parameters-grid">
              <div
                v-for="param in parameterSchema"
                :key="param.name"
                class="form-group"
              >
                <label :for="param.name">
                  {{ param.label }}
                  <span class="param-hint" v-if="param.description">
                    <i class="icon-info"></i>
                    <span class="hint-text">{{ param.description }}</span>
                  </span>
                </label>

                <!-- 数值输入 -->
                <div v-if="param.type === 'number'" class="number-input-group">
                  <input
                    :id="param.name"
                    v-model.number="formData.parameters[param.name]"
                    type="number"
                    :min="param.min"
                    :max="param.max"
                    :step="param.step"
                    class="form-input"
                  />
                  <div class="input-range">
                    <span>{{ param.min }}</span>
                    <input
                      type="range"
                      :min="param.min"
                      :max="param.max"
                      :step="param.step"
                      v-model.number="formData.parameters[param.name]"
                      class="range-slider"
                    />
                    <span>{{ param.max }}</span>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <!-- 股票池配置 -->
          <section class="form-section">
            <h3>股票池配置</h3>
            <div class="stock-pool-section">
              <div class="preset-pools">
                <label>预设股票池</label>
                <div class="preset-buttons">
                  <button
                    v-for="pool in stockPools"
                    :key="pool.name"
                    type="button"
                    class="preset-btn"
                    :class="{ active: isPoolSelected(pool.stocks) }"
                    @click="selectPresetPool(pool)"
                  >
                    {{ pool.name }}
                  </button>
                </div>
                <div v-if="selectedPresetPool" class="pool-description">
                  {{ selectedPresetPool.description }}
                </div>
              </div>

              <div class="custom-stocks">
                <label>自定义股票代码</label>
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
            </div>
          </section>

          <!-- 调频配置 -->
          <section class="form-section">
            <h3>调频配置</h3>
            <div class="form-group">
              <label for="rebalance-freq">调频周期 *</label>
              <select
                id="rebalance-freq"
                v-model.number="formData.rebalance_frequency"
                required
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
              <span v-if="loading">创建中...</span>
              <span v-else>创建策略</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  </teleport>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import strategyService from '@/services/strategy.js'

// Props
const emit = defineEmits(['close', 'created'])

// 响应式数据
const loading = ref(false)
const stockInput = ref('')
const selectedPresetPool = ref(null)

// 表单数据
const formData = ref({
  name: '',
  strategy_type: '',
  parameters: {},
  stock_pool: [],
  rebalance_frequency: 10
})

// 计算属性
const strategyTypes = computed(() => strategyService.getStrategyTypes())

const selectedStrategyType = computed(() => {
  return strategyTypes.value.find(type => type.value === formData.value.strategy_type)
})

const parameterSchema = computed(() => {
  return selectedStrategyType.value?.parameterSchema || []
})

const stockPools = computed(() => strategyService.getStockPools())

const isFormValid = computed(() => {
  return formData.value.name.trim() &&
         formData.value.strategy_type &&
         formData.value.stock_pool.length > 0 &&
         formData.value.rebalance_frequency > 0
})

// 方法
function closeModal() {
  emit('close')
}

function onStrategyTypeChange() {
  // 重置参数为默认值
  if (selectedStrategyType.value) {
    formData.value.parameters = { ...selectedStrategyType.value.defaultParameters }
  }
}

function isPoolSelected(stocks) {
  return JSON.stringify(formData.value.stock_pool.sort()) ===
         JSON.stringify(stocks.sort())
}

function selectPresetPool(pool) {
  formData.value.stock_pool = [...pool.stocks]
  selectedPresetPool.value = pool
}

function addStock() {
  const stock = stockInput.value.trim().toUpperCase()
  if (stock && !formData.value.stock_pool.includes(stock)) {
    formData.value.stock_pool.push(stock)
    stockInput.value = ''
    selectedPresetPool.value = null
  }
}

function removeStock(index) {
  formData.value.stock_pool.splice(index, 1)
  if (selectedPresetPool.value && !isPoolSelected(selectedPresetPool.value.stocks)) {
    selectedPresetPool.value = null
  }
}

async function handleSubmit() {
  if (!isFormValid.value) return

  loading.value = true

  try {
    const result = await strategyService.createStrategy(formData.value)
    emit('created', result)

    // 重置表单
    resetForm()
    closeModal()
  } catch (error) {
    console.error('创建策略失败:', error)
    alert('创建策略失败: ' + error.message)
  } finally {
    loading.value = false
  }
}

function resetForm() {
  formData.value = {
    name: '',
    strategy_type: '',
    parameters: {},
    stock_pool: [],
    rebalance_frequency: 10
  }
  stockInput.value = ''
  selectedPresetPool.value = null
}

// 监听参数变化
watch(() => formData.value.strategy_type, (newType) => {
  if (newType && strategyTypes.value.length) {
    const type = strategyTypes.value.find(t => t.value === newType)
    if (type) {
      formData.value.parameters = { ...type.defaultParameters }
    }
  }
})

// 生命周期
onMounted(() => {
  // 设置默认选中的策略类型
  if (strategyTypes.value.length > 0) {
    formData.value.strategy_type = strategyTypes.value[0].value
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
  max-width: 800px;
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

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
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

.strategy-description {
  padding: 12px;
  background: var(--info-bg);
  border: 1px solid var(--info-border);
  border-radius: 4px;
  font-size: 14px;
  color: var(--text-secondary);
}

.parameters-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
}

.param-hint {
  position: relative;
  margin-left: 4px;
  color: var(--text-secondary);
  cursor: help;
}

.param-hint .hint-text {
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%);
  background: #333;
  color: white;
  padding: 6px 8px;
  border-radius: 4px;
  font-size: 12px;
  white-space: nowrap;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.2s;
  z-index: 10;
}

.param-hint:hover .hint-text {
  opacity: 1;
}

.number-input-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.input-range {
  display: flex;
  align-items: center;
  gap: 12px;
}

.range-slider {
  flex: 1;
  height: 4px;
  background: var(--border-color);
  border-radius: 2px;
  outline: none;
}

.range-slider::-webkit-slider-thumb {
  appearance: none;
  width: 16px;
  height: 16px;
  background: var(--primary-color);
  border-radius: 50%;
  cursor: pointer;
}

/* 股票池配置 */
.stock-pool-section {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.preset-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.preset-btn {
  padding: 8px 16px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: var(--input-bg);
  color: var(--text-primary);
  cursor: pointer;
  transition: all 0.2s ease;
}

.preset-btn:hover {
  background: var(--hover-bg);
}

.preset-btn.active {
  background: var(--primary-color);
  color: white;
  border-color: var(--primary-color);
}

.pool-description {
  padding: 8px 12px;
  background: var(--info-bg);
  border-radius: 4px;
  font-size: 13px;
  color: var(--text-secondary);
}

.stock-input-group {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
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