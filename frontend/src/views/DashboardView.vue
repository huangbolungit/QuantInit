<template>
  <div class="dashboard">
    <section class="dashboard__section">
      <header class="section-header">
        <h2>市场概览</h2>
        <span class="section-subtitle">{{ marketStatus.text }}</span>
      </header>
      <div class="overview-grid" v-if="overviewItems.length">
        <article v-for="item in overviewItems" :key="item.key" class="overview-card bg-card">
          <header>
            <h3>{{ item.name ?? item.key }}</h3>
            <span :class="item.change_pct >= 0 ? 'text-success' : 'text-danger'">
              {{ formatPercent(item.change_pct) }}
            </span>
          </header>
          <dl>
            <div>
              <dt>当前点位</dt>
              <dd>{{ formatNumber(item.current) }}</dd>
            </div>
            <div>
              <dt>成交量</dt>
              <dd>{{ formatNumber(item.volume) }}</dd>
            </div>
          </dl>
        </article>
      </div>
      <p v-else class="empty-state">暂无市场概览数据</p>
    </section>

    <section class="dashboard__section">
      <header class="section-header">
        <h2>行业热点</h2>
        <span class="section-subtitle">Top 10 & Bottom 10</span>
      </header>
      <div class="sectors-grid">
        <div class="sector-list bg-card">
          <h3>表现最佳</h3>
          <ul>
            <li v-for="sector in topSectors" :key="sector.code">
              <span>{{ sector.name }}</span>
              <span class="text-success">{{ formatPercent(sector.change_pct) }}</span>
            </li>
          </ul>
        </div>
        <div class="sector-list bg-card">
          <h3>表现较弱</h3>
          <ul>
            <li v-for="sector in bottomSectors" :key="sector.code">
              <span>{{ sector.name }}</span>
              <span class="text-danger">{{ formatPercent(sector.change_pct) }}</span>
            </li>
          </ul>
        </div>
      </div>
    </section>

    <section class="dashboard__section dashboard__section--half">
      <div class="bg-card northbound-card">
        <header class="section-header">
          <h2>北向资金</h2>
          <span class="section-subtitle">最新数据</span>
        </header>
        <ul class="funds-list">
          <li>
            <span>净流入（总）</span>
            <span :class="northboundFunds.northbound >= 0 ? 'text-success' : 'text-danger'">
              {{ formatCurrency(northboundFunds.northbound) }}
            </span>
          </li>
          <li>
            <span>沪股通</span>
            <span :class="northboundFunds.northbound_sh >= 0 ? 'text-success' : 'text-danger'">
              {{ formatCurrency(northboundFunds.northbound_sh) }}
            </span>
          </li>
          <li>
            <span>深股通</span>
            <span :class="northboundFunds.northbound_sz >= 0 ? 'text-success' : 'text-danger'">
              {{ formatCurrency(northboundFunds.northbound_sz) }}
            </span>
          </li>
        </ul>
      </div>

      <div class="bg-card heatmap-card">
        <header class="section-header">
          <h2>热力图快照</h2>
          <span class="section-subtitle">按涨跌幅排序</span>
        </header>
        <ul class="heatmap-list">
          <li v-for="item in heatmapPreview" :key="item.code">
            <span>{{ item.name }}</span>
            <span :class="item.change_pct >= 0 ? 'text-success' : 'text-danger'">
              {{ formatPercent(item.change_pct) }}
            </span>
          </li>
        </ul>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useMarketStore } from '@/stores/market'

const marketStore = useMarketStore()

const overviewItems = computed(() => {
  const data = marketStore.overview
  if (!data || Object.keys(data).length === 0) {
    return []
  }

  return Object.entries(data).map(([key, value]) => ({
    key,
    ...value
  }))
})

const topSectors = computed(() => marketStore.topSectors)
const bottomSectors = computed(() => marketStore.bottomSectors)
const northboundFunds = computed(() => marketStore.northboundFunds || {})
const heatmapPreview = computed(() => (marketStore.heatmap || []).slice(0, 8))
const marketStatus = computed(() => marketStore.getMarketStatus())

function formatPercent(value) {
  if (value === undefined || value === null) {
    return '--'
  }
  return `${Number(value).toFixed(2)}%`
}

function formatNumber(value) {
  if (value === undefined || value === null) {
    return '--'
  }
  return new Intl.NumberFormat('zh-CN', {
    maximumFractionDigits: 2
  }).format(value)
}

function formatCurrency(value) {
  if (value === undefined || value === null) {
    return '--'
  }
  const billion = 1_000_000_000
  const million = 1_000_000
  const absValue = Math.abs(value)

  if (absValue >= billion) {
    return `${(value / billion).toFixed(2)} 亿`
  }
  if (absValue >= million) {
    return `${(value / million).toFixed(2)} 百万`
  }
  return new Intl.NumberFormat('zh-CN', {
    maximumFractionDigits: 0
  }).format(value)
}
</script>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 24px;
  flex: 1;
  padding: 24px;
  overflow-y: auto;
}

.dashboard__section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.dashboard__section--half {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 16px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.section-header h2 {
  font-size: 18px;
  font-weight: 600;
}

.section-subtitle {
  font-size: 13px;
  color: #8b949e;
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
}

.overview-card header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.overview-card h3 {
  font-size: 16px;
}

.overview-card dl {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.overview-card dt {
  font-size: 12px;
  color: #8b949e;
}

.overview-card dd {
  font-size: 14px;
}

.sectors-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px;
}

.sector-list h3 {
  font-size: 16px;
  margin-bottom: 12px;
}

.sector-list ul {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sector-list li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 14px;
}

.northbound-card,
.heatmap-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.funds-list,
.heatmap-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 14px;
}

.funds-list li,
.heatmap-list li {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.empty-state {
  font-size: 14px;
  color: #8b949e;
  font-style: italic;
}
</style>
