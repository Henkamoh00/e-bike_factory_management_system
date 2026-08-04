import { ref, computed } from 'vue'
import router from '../router'

const TOKEN_KEY = 'ebike_token'
const USER_KEY = 'ebike_user'
const API = import.meta.env.VITE_API_BASE_URL

const token = ref(localStorage.getItem(TOKEN_KEY) || '')
const user = ref(JSON.parse(localStorage.getItem(USER_KEY) || 'null'))

export function useAuth() {
  // 🛡️ إصلاح: تمت إزالة useRouter() من هنا نهائياً.
  // useRouter() يعتمد على inject() الذي يعمل فقط داخل setup() لمكوّن Vue،
  // بينما useAuth() يُستدعى أيضاً من أماكن خارج سياق المكوّنات مثل:
  // - router.beforeEach() في index.js (Navigation Guards)
  // - الدالة redirect لمسار الجذر '/'
  // عند فشل inject() بصمت، كانت apiFetch تنهار داخلياً عند محاولة استخدام
  // router.replace() عند 401، مما يسبب تعليق تسجيل الدخول بلا أي خطأ ظاهر.
  // الحل: استيراد نسخة الـ router (singleton) مباشرة من '../router' بدل useRouter().
  // هذا آمن تماماً لأن router هنا هو نفس الكائن دائماً، بغض النظر عن مكان الاستدعاء.

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
   * - 403: لا نُسجّل خطأ في الكونسول، فقط نُرجع الاستجابة كما هي
   *   ليتعامل معها الكومبوننت المستدعي (silent by design)
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