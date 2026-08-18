import { ref, computed } from 'vue'
import router from '../router'

const USER_KEY = 'ebike_user'
// 🛡️ مؤشر غير حساس إطلاقًا (قيمة boolean فقط، لا يحمل أي توكن أو بيانات
// شخصية) — يُستخدم فقط لتحديد: هل يستحق الأمر محاولة /refresh عند إقلاع
// التطبيق؟ لو لم تكن هناك جلسة سابقة معروفة (مثال: أول زيارة، أو بعد
// logout)، لا داعي إطلاقًا لمحاولة /refresh لأنها ستفشل حتمًا (401) —
// هذا يقلّل عدد الطلبات الفاشلة من طلبين إلى طلب واحد فقط (أو صفر).
const HAD_SESSION_KEY = 'ebike_had_session'
const API = import.meta.env.VITE_API_BASE_URL

const user = ref(JSON.parse(localStorage.getItem(USER_KEY) || 'null'))
const isAuthenticated = ref(!!user.value)

let refreshPromise = null

const markHadSession = () => localStorage.setItem(HAD_SESSION_KEY, '1')
const clearHadSession = () => localStorage.removeItem(HAD_SESSION_KEY)
const hadSessionBefore = () => localStorage.getItem(HAD_SESSION_KEY) === '1'

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
      })
    } catch (e) {
      // 🛡️ فشل الاتصال بالسيرفر أثناء تسجيل الخروج ليس خطأً يستحق الإزعاج
      // بالكونسول؛ الأولوية هي مسح الجلسة محليًا بغض النظر عن نجاح الطلب
    } finally {
      clearSession()
    }
  }

  /**
   * 🛡️ يحاول تجديد access_token عبر refresh_token المخزّن في الكوكي.
   * silent=true (الافتراضي أثناء الاستخدام الداخلي من apiFetch) يعني:
   * لا نطبع أي شيء بالكونسول من جهتنا مهما كانت النتيجة، فقط نُرجع
   * true/false. فشل التجديد هو حالة متوقعة تمامًا (انتهت صلاحية الجلسة)
   * وليس خطأً برمجيًا يستحق console.error.
   */
  const tryRefresh = async () => {
    if (!refreshPromise) {
      refreshPromise = fetch(`${API}/api/auth/refresh/`, {
        method: 'POST',
        credentials: 'include',
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
          // 🛡️ خطأ شبكة فعلي (لا اتصال بالسيرفر مثلاً)، وليس مجرد 401 —
          // نتعامل معه بصمت بنفس الطريقة: الجلسة غير صالحة، لا داعي لإزعاج
          // المستخدم أو المطوّر بتفاصيل تقنية في هذا السياق تحديدًا
          clearSession()
          return false
        })
        .finally(() => {
          refreshPromise = null
        })
    }
    return refreshPromise
  }

  /**
   * غلاف موحّد لكل طلبات الـ API.
   * options.silentAuth (اختياري، افتراضي false):
   *   عند true، إذا فشل الطلب بـ 401 لا نحاول /refresh تلقائيًا ولا نُعيد
   *   التوجيه لصفحة الدخول — نُعيد الاستجابة كما هي فقط. يُستخدم هذا حصرًا
   *   من فحص الجلسة الأولي عند الإقلاع (checkInitialSession) حيث نُريد
   *   تفادي أي طلب إضافي إن كنا نعلم مسبقًا أن لا جلسة سابقة موجودة.
   */
  const apiFetch = async (path, options = {}, _isRetry = false) => {
    const { silentAuth, ...fetchOptions } = options

    const res = await fetch(`${API}${path}`, {
      ...fetchOptions,
      credentials: 'include',
      headers: { 'Content-Type': 'application/json', ...(fetchOptions.headers || {}) }
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

  /**
   * 🛡️ فحص الجلسة عند إقلاع التطبيق (يُستدعى مرة واحدة من router.beforeEach).
   * الفرق الجوهري عن fetchCurrentUser العادية: هنا نتحقق أولاً من المؤشر
   * المحلي hadSessionBefore() —
   *   - لو false (لا جلسة معروفة سابقًا: أول زيارة، أو بعد logout كامل):
   *     لا نُرسل أي طلب شبكة إطلاقًا. لا فائدة من محاولة /me أو /refresh
   *     لأننا نعلم مسبقًا أنهما سيفشلان بـ 401 — هذا يُلغي الطلبين الفاشلين
   *     نهائيًا في أكثر السيناريوهات شيوعًا (زيارة صفحة تسجيل الدخول لأول مرة).
   *   - لو true (كانت هناك جلسة سابقة، لكن الصفحة أُعيد تحميلها والحالة
   *     المحلية user فُقدت من الذاكرة): نحاول /me بصمت (silentAuth) فقط
   *     مرة واحدة. لو فشل بـ 401 (يعني access token القديم انتهى)، نحاول
   *     /refresh مرة واحدة يدويًا. لو فشل أيضًا (يعني refresh token نفسه
   *     انتهى بعد 7 أيام أو أُبطل)، نمسح المؤشر ونتوقف بصمت — هذا السيناريو
   *     الوحيد المتبقي الذي قد يُظهر طلبًا فاشلًا واحدًا أو اثنين في الشبكة،
   *     وهو متوقع تمامًا (انتهاء جلسة قديمة) لا يستدعي أي قلق.
   */
  const checkInitialSession = async () => {
    if (!hadSessionBefore()) {
      // لا جلسة سابقة معروفة: لا نُرسل أي طلب شبكة إطلاقًا
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
        // access token منتهي، لكن قد يكون refresh token ما زال صالحًا
        const refreshed = await tryRefresh()
        if (!refreshed) {
          clearSession()
        }
        return
      }
      clearSession()
    } catch (e) {
      // 🛡️ خطأ شبكة فعلي (السيرفر غير متاح) — لا نطبع تفاصيله للمستخدم
      // العادي، نكتفي باعتبار الجلسة غير مؤكدة والتعامل معها كغير مسجّلة
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
      // 🛡️ يُستدعى هذا المسار من داخل التطبيق (بعد تسجيل الدخول فعليًا)
      // وليس أثناء الفحص الأولي، لذا فشل هنا أكثر ندرة وقد يستحق تسجيلاً
      // تقنيًا خفيفًا لأغراض التشخيص فقط دون إزعاج، دون طباعة تفاصيل حساسة
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