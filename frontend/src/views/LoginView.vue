<template>
  <div class="min-h-screen flex items-center justify-center bg-slate-50" dir="rtl">
    <div class="bg-white rounded-3xl shadow-xl w-full max-w-sm p-8">
      <div class="text-center mb-8">
        <div class="w-14 h-14 mx-auto bg-gradient-to-br from-indigo-600 to-indigo-500 rounded-2xl flex items-center justify-center text-white text-2xl mb-4">
          🚲
        </div>
        <h1 class="text-xl font-bold text-slate-900">تسجيل الدخول</h1>
        <p class="text-sm text-slate-400 mt-1">نظام إدارة تجميع الدراجات الكهربائية</p>
      </div>

      <div class="space-y-4">
        <div>
          <label class="block text-sm text-gray-600 mb-1">اسم المستخدم</label>
          <input
            v-model="form.username"
            type="text"
            class="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-indigo-400 focus:outline-none"
            @keyup.enter="submit"
          />
        </div>
        <div>
          <label class="block text-sm text-gray-600 mb-1">كلمة المرور</label>
          <input
            v-model="form.password"
            type="password"
            class="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-indigo-400 focus:outline-none"
            @keyup.enter="submit"
          />
        </div>

        <p v-if="error" class="text-sm text-red-600">{{ error }}</p>

        <button
          @click="submit"
          :disabled="loading"
          class="w-full bg-indigo-600 hover:bg-indigo-700 text-white py-3 rounded-xl font-bold"
        >
          {{ loading ? 'جاري الدخول...' : 'دخول' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '../composables/useAuth'

const API = import.meta.env.VITE_API_BASE_URL

const router = useRouter()
const { setSession } = useAuth()

const form = ref({ username: '', password: '' })
const loading = ref(false)
const error = ref('')

const submit = async () => {
  if (!form.value.username || !form.value.password) {
    error.value = 'يرجى إدخال اسم المستخدم وكلمة المرور'
    return
  }
  loading.value = true
  error.value = ''
  try {
    // 🛡️ طلب تسجيل الدخول لا يمر عبر apiFetch (لتفادي أي منطق retry/refresh
    // غير ذي معنى هنا)، لكن يجب credentials: 'include' ليقبل المتصفح
    // ويخزّن الكوكيز httpOnly التي يُرجعها السيرفر في هذه الاستجابة تحديدًا
    const res = await fetch(`${API}/api/auth/login/`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form.value)
    })
    const data = await res.json()
    if (res.ok) {
      // 🛡️ لا يوجد access_token في الاستجابة بعد الآن؛ فقط بيانات المستخدم
      // للعرض. التوكن الفعلي وصل بالفعل داخل Set-Cookie httpOnly ولا نراه هنا إطلاقًا
      setSession(data)
      router.replace({ name: 'Dashboard' })
    } else {
      error.value = data.detail || 'حدث خطأ أثناء تسجيل الدخول'
    }
  } catch (e) {
    error.value = 'تعذر الاتصال بالسيرفر'
  } finally {
    loading.value = false
  }
}
</script>