import { createRouter, createWebHistory } from 'vue-router'

import Workshop from '../views/Workshop.vue'
import AdminDashboard from '../views/AdminDashboard.vue'

const routes = [
  {
    path: '/',
    name: 'Workshop',
    component: Workshop
  },
  {
    path: '/admin',
    name: 'Admin',
    component: AdminDashboard
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router