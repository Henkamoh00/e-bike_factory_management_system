<template>
  <div class="min-h-screen bg-slate-50 flex items-center justify-center p-6 relative overflow-hidden" dir="rtl">

    <!-- عناصر زخرفية متحركة في الخلفية -->
    <div class="absolute inset-0 pointer-events-none overflow-hidden">
      <div class="absolute -top-24 -right-24 w-96 h-96 bg-indigo-100 rounded-full blur-3xl opacity-60"></div>
      <div class="absolute -bottom-24 -left-24 w-96 h-96 bg-purple-100 rounded-full blur-3xl opacity-60"></div>
      <div class="absolute top-1/3 left-1/4 w-64 h-64 bg-amber-50 rounded-full blur-3xl opacity-50"></div>
    </div>

    <div class="relative z-10 max-w-lg w-full text-center">

      <!-- رسم الدراجة "الضائعة" -->
      <div class="mb-8 flex justify-center">
        <div class="relative">
          <div class="text-[140px] leading-none select-none animate-bounce-slow">🚲</div>
          <div class="absolute -bottom-2 inset-x-0 flex justify-center gap-1">
            <span class="w-2 h-2 rounded-full bg-slate-300 animate-pulse"></span>
            <span class="w-2 h-2 rounded-full bg-slate-300 animate-pulse" style="animation-delay: 0.2s"></span>
            <span class="w-2 h-2 rounded-full bg-slate-300 animate-pulse" style="animation-delay: 0.4s"></span>
          </div>
        </div>
      </div>

      <div class="mb-2">
        <span class="text-8xl font-black bg-gradient-to-br from-indigo-600 via-purple-500 to-indigo-400 bg-clip-text text-transparent tracking-tight">
          404
        </span>
      </div>

      <h1 class="text-2xl font-bold text-slate-900 mb-3">
        الطريق غير موجود 🧭
      </h1>
      <p class="text-slate-500 mb-10 leading-relaxed max-w-sm mx-auto">
        يبدو أن هذه الدراجة سلكت طريقًا غير موجود في الورشة.
        الصفحة التي تبحث عنها غير متوفرة أو تم نقلها.
      </p>

      <div class="flex flex-col sm:flex-row gap-3 justify-center">
        <button
          @click="goHome"
          class="bg-indigo-600 hover:bg-indigo-700 text-white px-8 py-3.5 rounded-2xl font-bold shadow-lg shadow-indigo-200 transition-all hover:shadow-xl hover:-translate-y-0.5"
        >
          🏠 العودة للوحة الإدارة
        </button>
        <button
          @click="goBack"
          class="bg-white hover:bg-slate-100 text-slate-600 px-8 py-3.5 rounded-2xl font-bold border-2 border-slate-200 transition-all"
        >
          ← رجوع للصفحة السابقة
        </button>
      </div>

      <div class="mt-12 pt-8 border-t border-slate-200">
        <p class="text-xs text-slate-400">
          إذا كنت تعتقد أن هذا خطأ، يمكنك
          <button @click="emergencyLogout" class="text-red-500 hover:text-red-700 underline font-medium">
            تسجيل الخروج
          </button>
          وإعادة المحاولة.
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useAuth } from '../composables/useAuth'

const router = useRouter()
const { isAuthenticated, logout } = useAuth()

const goHome = () => {
  router.push(isAuthenticated.value ? { name: 'Dashboard' } : { name: 'Login' })
}

const goBack = () => {
  if (window.history.length > 1) {
    router.back()
  } else {
    goHome()
  }
}

const emergencyLogout = () => {
  logout()
  router.replace({ name: 'Login' })
}
</script>

<style scoped>
@keyframes bounce-slow {
  0%, 100% { transform: translateY(0) rotate(-2deg); }
  50% { transform: translateY(-16px) rotate(2deg); }
}
.animate-bounce-slow {
  animation: bounce-slow 3s ease-in-out infinite;
}
</style>