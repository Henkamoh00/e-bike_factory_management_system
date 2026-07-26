import { createRouter, createWebHistory } from 'vue-router'
import LoginView from '../views/LoginView.vue'
import DashboardView from '../views/DashboardView.vue'
import { useAuth } from '../composables/useAuth'

const routes = [
  {
    path: '/',
    name: 'Login',
    component: LoginView
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: DashboardView,
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to) => {
  const { isAuthenticated } = useAuth()

  // 1. إذا كانت الصفحة تطلب تسجيل دخول والمستخدم غير مسجل -> وجهه للـ Login
  if (to.meta.requiresAuth && !isAuthenticated.value) {
    return { name: 'Login' }
  }

  // 2. إذا كان المستخدم مسجلاً ويحاول فتح صفحة الـ Login -> وجهه للـ Dashboard
  if (to.name === 'Login' && isAuthenticated.value) {
    return { name: 'Dashboard' }
  }

  // 3. السماح بعبور الملاحة بشكل طبيعي (دون الحاجة لاستدعاء next())
})

export default router