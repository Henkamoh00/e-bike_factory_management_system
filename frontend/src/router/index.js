import { createRouter, createWebHistory } from 'vue-router'


import AdminDashboard from '../views/AdminDashboard.vue'

const routes = [
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