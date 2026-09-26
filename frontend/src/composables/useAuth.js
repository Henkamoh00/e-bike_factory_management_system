import { ref, computed } from 'vue'
import router from '../router'

const USER_KEY = 'ebike_user'
const HAD_SESSION_KEY = 'ebike_had_session'
const CSRF_COOKIE_NAME = 'ebike_csrf'
const CSRF_HEADER_NAME = 'X-CSRF-Token'
const API = import.meta.env.VITE_API_BASE_URL

const user = ref(JSON.parse(localStorage.getItem(USER_KEY) || 'null'))
const isAuthenticated = ref(!!user.value)

let refreshPromise = null

const markHadSession = () => localStorage.setItem(HAD_SESSION_KEY, '1')
const clearHadSession = () => localStorage.removeItem(HAD_SESSION_KEY)
const hadSessionBefore = () => localStorage.getItem(HAD_SESSION_KEY) === '1'

// يقرأ قيمة كوكي CSRF (غير httpOnly، لذا قابل للقراءة من JS هنا فقط
// لغرض إرفاقه بالهيدر — هذا هو جوهر نمط Double Submit Cookie)
const getCsrfToken = () => {
  const match = document.cookie.match(new RegExp('(^| )' + CSRF_COOKIE_NAME + '=([^;]+)'))
  return match ? decodeURIComponent(match[2]) : null
}

// يبني هيدرز الطلب مع إرفاق CSRF تلقائيًا للطلبات غير الآمنة (غير GET)
const buildHeaders = (method, extraHeaders = {}) => {
  const headers = { 'Content-Type': 'application/json', ...extraHeaders }
  const safe = ['GET', 'HEAD', 'OPTIONS'].includes((method || 'GET').toUpperCase())
  if (!safe) {
    const token = getCsrfToken()
    if (token) headers[CSRF_HEADER_NAME] = token
  }
  return headers
}

export function useAuth() {

  const setSession = (userData) => {
    user.value = userData
    isAuthenticated.value = true
    localStorage.setItem(USER_KEY, JSON.stringify(userData))
    markHadSession()
  }

  const clearSession = () => {
    user.value = null
    isAuthenticated.value = false
    localStorage.removeItem(USER_KEY)
    clearHadSession()
  }

  const logout = async () => {
    try {
      await fetch(`${API}/api/auth/logout/`, {
        method: 'POST',
        credentials: 'include',
        headers: buildHeaders('POST'),
      })
    } catch (e) {
      // فشل الاتصال أثناء تسجيل الخروج ليس خطأً يستحق الإزعاج
    } finally {
      clearSession()
    }
  }

  const tryRefresh = async () => {
    if (!refreshPromise) {
      refreshPromise = fetch(`${API}/api/auth/refresh/`, {
        method: 'POST',
        credentials: 'include',
        headers: buildHeaders('POST'),
      })
        .then(async (res) => {
          if (res.ok) {
            const data = await res.json()
            setSession(data)
            return true
          }
          clearSession()
          return false
        })
        .catch(() => {
          clearSession()
          return false
        })
        .finally(() => {
          refreshPromise = null
        })
    }
    return refreshPromise
  }

  const apiFetch = async (path, options = {}, _isRetry = false) => {
    const { silentAuth, ...fetchOptions } = options
    const method = fetchOptions.method || 'GET'

    const res = await fetch(`${API}${path}`, {
      ...fetchOptions,
      credentials: 'include',
      headers: buildHeaders(method, fetchOptions.headers || {}),
    })

    if (res.status === 401 && !silentAuth && !_isRetry && path !== '/api/auth/refresh/' && path !== '/api/auth/login/') {
      const refreshed = await tryRefresh()
      if (refreshed) {
        return apiFetch(path, options, true)
      }
      clearSession()
      router.replace({ name: 'Login' })
    }

    return res
  }

  const checkInitialSession = async () => {
    if (!hadSessionBefore()) {
      clearSession()
      return
    }

    try {
      const res = await fetch(`${API}/api/auth/me`, {
        credentials: 'include',
      })
      if (res.ok) {
        const data = await res.json()
        setSession(data)
        return
      }
      if (res.status === 401) {
        const refreshed = await tryRefresh()
        if (!refreshed) {
          clearSession()
        }
        return
      }
      clearSession()
    } catch (e) {
      clearSession()
    }
  }

  const fetchCurrentUser = async () => {
    try {
      const res = await apiFetch('/api/auth/me')
      if (res.ok) {
        const data = await res.json()
        setSession(data)
      } else {
        clearSession()
      }
    } catch (e) {
      if (import.meta.env.DEV) {
        console.warn('تعذر تحديث بيانات المستخدم:', e.message)
      }
    }
  }

  return {
    user,
    isAuthenticated,
    setSession,
    logout,
    apiFetch,
    fetchCurrentUser,
    checkInitialSession,
  }
}