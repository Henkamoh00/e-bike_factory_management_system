import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'

const TOKEN_KEY = 'ebike_token'
const USER_KEY = 'ebike_user'
const API = import.meta.env.VITE_API_BASE_URL

// State مشترك بين كل استخدامات useAuth() في التطبيق (Singleton pattern)
const token = ref(localStorage.getItem(TOKEN_KEY) || '')
const user = ref(JSON.parse(localStorage.getItem(USER_KEY) || 'null'))

export function useAuth() {
  const router = useRouter()

  const isAuthenticated = computed(() => !!token.value)

  const setSession = (accessToken, userData) => {
    token.value = accessToken
    user.value = userData
    localStorage.setItem(TOKEN_KEY, accessToken)
    localStorage.setItem(USER_KEY, JSON.stringify(userData))
  }

  const logout = () => {
    token.value = ''
    user.value = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  }

  const authHeaders = () => {
    const headers = { 'Content-Type': 'application/json' }
    if (token.value) headers['Authorization'] = `Bearer ${token.value}`
    return headers
  }

  /**
   * غلاف موحّد لكل طلبات الـ API:
   * - يضيف الهيدرز والتوكن تلقائيًا
   * - يعالج انتهاء الجلسة (401) تلقائيًا
   * path: يبدأ بـ '/' مثل '/api/workers/' (بدون ${API})
   */
  const apiFetch = async (path, options = {}) => {
    const res = await fetch(`${API}${path}`, {
      ...options,
      headers: { ...authHeaders(), ...(options.headers || {}) }
    })

    if (res.status === 401) {
      logout()
      router.replace({ name: 'Login' })
    }

    return res
  }


   /**
   * يُعيد جلب بيانات المستخدم الحالي من السيرفر (يشمل allowed_tabs المحدّثة)
   * ويحدّث الحالة المشتركة + localStorage. يُستخدم في:
   * - router guard عند التنقل
   * - Polling دوري لاكتشاف تغيّر الصلاحيات في الوقت الفعلي تقريبًا
   */
  const fetchCurrentUser = async () => {
    try {
      const res = await apiFetch('/api/auth/me')
      if (res.ok) {
        const data = await res.json()
        user.value = data
        localStorage.setItem(USER_KEY, JSON.stringify(data))
      }
    } catch (e) {
      console.error('تحديث بيانات المستخدم', e)
    }
  }

  return {
    token,
    user,
    isAuthenticated,
    setSession,
    logout,
    apiFetch,
    fetchCurrentUser
  }
}