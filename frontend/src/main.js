import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import router from './router'

const app = createApp(App)

app.config.errorHandler = (err, instance, info) => {
  console.error('❌ خطأ غير متوقع في التطبيق:', err, info)
  window.dispatchEvent(new CustomEvent('app-fatal-error', { detail: { err, info } }))
}

app.use(router)

app.mount('#app')