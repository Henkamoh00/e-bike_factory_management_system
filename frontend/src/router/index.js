import { createRouter, createWebHistory } from 'vue-router'
import LoginView from '../views/LoginView.vue'
import DashboardView from '../views/DashboardView.vue'
import { useAuth } from '../composables/useAuth'
import { isTabAllowed, getDefaultTab } from '../composables/useTabPermissions'

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
  const { isAuthenticated, user } = useAuth()

  // 1. إذا كانت الصفحة تطلب تسجيل دخول والمستخدم غير مسجل -> وجهه للـ Login
  if (to.meta.requiresAuth && !isAuthenticated.value) {
    return { name: 'Login' }
  }

  // 2. إذا كان المستخدم مسجلاً ويحاول فتح صفحة الـ Login -> وجهه للـ Dashboard
  if (to.name === 'Login' && isAuthenticated.value) {
    return { name: 'Dashboard' }
  }

  // 3. 🛡️ حماية ثانية: لو حاول المستخدم الوصول لتبويب محظور مباشرة عبر رابط
  //    مثل /dashboard?tab=users وهو مسيّر (operator) -> يُعاد توجيهه لتبويبه الافتراضي المسموح
  if (to.name === 'Dashboard' && isAuthenticated.value && to.query.tab) {
    const role = user.value?.role
    if (!isTabAllowed(to.query.tab, role)) {
      return { name: 'Dashboard', query: { tab: getDefaultTab(role) } }
    }
  }

  // 4. السماح بعبور الملاحة بشكل طبيعي (دون الحاجة لاستدعاء next())
})

export default router