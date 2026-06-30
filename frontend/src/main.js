import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import router from './router'


const app = createApp(App)

app.use(router)

// يمكن إضافة global properties لاحقاً
// app.config.globalProperties.$API = 'http://localhost:8000'

app.mount('#app')