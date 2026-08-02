import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import router from './router'

const app = createApp(App)

// ── معالج أخطاء عام على مستوى التطبيق بأكمله ──────────────────
// يلتقط أي خطأ غير متوقع يحدث في أي مكوّن (خارج نطاق onErrorCaptured المحلي)
// ويمنع "الشاشة البيضاء الصامتة"، كما يسجّل الخطأ في الكونسول للمطوّر.
app.config.errorHandler = (err, instance, info) => {
  console.error('❌ خطأ غير متوقع في التطبيق:', err, info)
  // نُطلق حدثاً مخصصاً يلتقطه App.vue لعرض شاشة الطوارئ الأنيقة
  window.dispatchEvent(new CustomEvent('app-fatal-error', { detail: { err, info } }))
}

app.use(router)

app.mount('#app')