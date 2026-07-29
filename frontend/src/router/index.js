import { createRouter, createWebHistory } from 'vue-router'
import LoginView from '../views/LoginView.vue'
import DashboardView from '../views/DashboardView.vue'
import { useAuth } from '../composables/useAuth'
import { isTabAllowed, getDefaultTab } from '../composables/useTabPermissions'

const routes = [
  {
    // أي مسار غير معروف (بما فيه '/') يُعاد توجيهه لصفحة الدخول
    path: '/:pathMatch(.*)*',
    redirect: '/login'
  },
  {
    path: '/login',
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

  // 2. إذا كان المستخدم مسجلاً ويحاول فتح صفحة الـ Login -> وجهه لتبويبه الافتراضي
  if (to.name === 'Login' && isAuthenticated.value) {
    return { name: 'Dashboard', query: { tab: getDefaultTab(user.value?.role) } }
  }

  // 3. 🛡️ حماية ثانية حقيقية الآن: منع الوصول لتبويب محظور عبر تعديل الرابط يدويًا
  //    (مثال: مسيّر يكتب /dashboard?tab=users في المتصفح مباشرة)
  if (to.name === 'Dashboard' && isAuthenticated.value) {
    const requestedTab = to.query.tab
    const role = user.value?.role
    if (!requestedTab || !isTabAllowed(requestedTab, role)) {
      return { name: 'Dashboard', query: { ...to.query, tab: getDefaultTab(role) } }
    }
  }

  // 4. السماح بعبور الملاحة بشكل طبيعي (دون الحاجة لاستدعاء next())
})

export default router