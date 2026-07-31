import { createRouter, createWebHistory } from 'vue-router'
import LoginView from '../views/LoginView.vue'
import DashboardView from '../views/DashboardView.vue'
import { useAuth } from '../composables/useAuth'
import { isTabAllowed, getDefaultTab } from '../composables/useTabPermissions'

const routes = [
  {
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

router.beforeEach(async (to) => {
  const { isAuthenticated, user, fetchCurrentUser, loading } = useAuth()

  if (to.meta.requiresAuth && !isAuthenticated.value) {
    return { name: 'Login' }
  }

  if (isAuthenticated.value && !user.value && fetchCurrentUser) {
    await fetchCurrentUser()
  }

  const role = user.value?.role
  const allowedTabs = user.value?.allowed_tabs

  if (to.name === 'Login' && isAuthenticated.value) {
    const defaultTab = getDefaultTab(role, allowedTabs)
    return { name: 'Dashboard', query: { tab: defaultTab } }
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