<template>
  <!-- شاشة الطوارئ: تظهر فقط عند حدوث خطأ فادح يمنع عرض التطبيق -->
  <div
    v-if="hasFatalError"
    class="fixed inset-0 z-[999999] bg-slate-50 flex items-center justify-center p-6"
    dir="rtl"
  >
    <div class="bg-white rounded-3xl shadow-2xl w-full max-w-md p-8 text-center border border-red-100">
      <div class="w-16 h-16 mx-auto bg-red-50 rounded-2xl flex items-center justify-center text-3xl mb-5">
        ⚠️
      </div>
      <h1 class="text-xl font-bold text-slate-900 mb-2">حدث خطأ غير متوقع</h1>
      <p class="text-sm text-slate-500 mb-8 leading-relaxed">
        واجه التطبيق مشكلة تقنية أثناء العرض. يمكنك محاولة إعادة تحميل الصفحة،
        أو تسجيل الخروج إذا استمرت المشكلة.
      </p>

      <div class="space-y-3">
        <button
          @click="reload"
          class="w-full bg-indigo-600 hover:bg-indigo-700 text-white py-3 rounded-xl font-bold transition-colors"
        >
          🔄 إعادة تحميل الصفحة
        </button>
        <button
          @click="emergencyLogout"
          class="w-full bg-red-50 hover:bg-red-100 text-red-600 py-3 rounded-xl font-bold transition-colors"
        >
          🚪 تسجيل الخروج وإعادة التحميل
        </button>
      </div>

      <p class="text-xs text-slate-300 mt-6">
        إذا لم تعمل هذه الأزرار، استخدم زر "🆘 خروج طوارئ" الظاهر أسفل يسار الشاشة.
      </p>
    </div>
  </div>

  <!-- الواجهة الطبيعية للتطبيق -->
  <router-view v-else />
</template>

<script setup>
import { ref, onErrorCaptured, onMounted, onUnmounted } from 'vue'

const hasFatalError = ref(false)

// ── يلتقط أي خطأ يحدث أثناء render أي مكوّن فرعي داخل الشجرة ──────
onErrorCaptured((err, instance, info) => {
  console.error('❌ تم التقاط خطأ في المكوّنات:', err, info)
  hasFatalError.value = true
  // true = لا نُعيد رمي الخطأ لمنع توقف التطبيق بالكامل بشكل أسوأ
  return false
})

// ── يلتقط الأخطاء العامة المُرسَلة من main.js (app.config.errorHandler) ──
const handleGlobalError = () => { hasFatalError.value = true }

onMounted(() => {
  window.addEventListener('app-fatal-error', handleGlobalError)
})
onUnmounted(() => {
  window.removeEventListener('app-fatal-error', handleGlobalError)
})

const reload = () => {
  window.location.reload()
}

const emergencyLogout = () => {
  localStorage.removeItem('ebike_token')
  localStorage.removeItem('ebike_user')
  window.location.href = '/login'
}
</script>