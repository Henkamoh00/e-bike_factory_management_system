import { createRouter, createWebHistory } from 'vue-router'
import LoginView from '../views/LoginView.vue'
import DashboardView from '../views/DashboardView.vue'
import InvoicesView from '../views/InvoicesView.vue'
import NotFoundView from '../views/NotFoundView.vue'
import { useAuth } from '../composables/useAuth'
import { isTabAllowed, getDefaultTab } from '../composables/useTabPermissions'

const routes = [
  {
    path: '/',
    redirect: () => {
      const { isAuthenticated } = useAuth()
      return isAuthenticated.value ? { name: 'Dashboard' } : { name: 'Login' }
    }
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
  },
  {
    // 🆕 صفحة الفواتير أصبحت مستقلة تمامًا عن نظام تبويبات DashboardView
    // (وليست v-else-if داخل <main>)، لأن نظام الفوترة أكبر وأعقد من أن
    // يُحشر كتبويب عادي — راجع الخطة المحفوظة بخصوص هذا القرار المعماري
    path: '/invoices',
    name: 'Invoices',
    component: InvoicesView,
    meta: { requiresAuth: true, tabId: 'invoices' }
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: NotFoundView
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 🛡️ فحص الجلسة الأولي يحدث مرة واحدة فقط طوال عمر التطبيق (SPA)،
// ويستخدم checkInitialSession() بدل fetchCurrentUser() تحديدًا لتفادي
// طلبات الشبكة غير الضرورية عند عدم وجود جلسة سابقة معروفة أصلًا
// (راجع التعليق التفصيلي داخل useAuth.js لفهم المنطق الكامل)
let hasCheckedSession = false

router.beforeEach(async (to) => {
  const { isAuthenticated, user, checkInitialSession } = useAuth()

  if (!hasCheckedSession) {
    hasCheckedSession = true
    await checkInitialSession()
  }

  if (to.meta.requiresAuth && !isAuthenticated.value) {
    return { name: 'Login' }
  }

  const role = user.value?.role
  const allowedTabs = user.value?.allowed_tabs

  if (to.name === 'Login' && isAuthenticated.value) {
    const defaultTab = getDefaultTab(role, allowedTabs)
    return { name: 'Dashboard', query: { tab: defaultTab } }
  }

  // 🆕 حماية صفحة الفواتير: نفس منطق فحص allowed_tabs المستخدم في Dashboard،
  // لكن هنا نُعيد المستخدم للوحة الإدارة (وليس لتبويب آخر داخل نفس الصفحة)
  // لأن /invoices مسار مستقل بالكامل
  if (to.meta.tabId && isAuthenticated.value) {
    if (!isTabAllowed(to.meta.tabId, role, allowedTabs)) {
      return { name: 'Dashboard', query: { tab: getDefaultTab(role, allowedTabs) } }
    }
  }

  if (to.name === 'Dashboard' && isAuthenticated.value) {
    const requestedTab = to.query.tab
    const defaultTab = getDefaultTab(role, allowedTabs)

    if (!requestedTab || !isTabAllowed(requestedTab, role, allowedTabs)) {
      if (requestedTab === defaultTab) {
        return true
      }
      return {
        name: 'Dashboard',
        query: { ...to.query, tab: defaultTab }
      }
    }
  }
})

export default router