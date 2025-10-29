import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'dashboard',
    component: () => import('@/views/DashboardView.vue')
  },
  {
    path: '/strategies',
    name: 'strategies',
    component: () => import('@/views/StrategyView.vue')
  },
  {
    path: '/optimization',
    name: 'optimization',
    component: () => import('@/views/OptimizationView.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
