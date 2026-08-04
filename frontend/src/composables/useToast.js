import { ref } from 'vue'

// حالة مشتركة (singleton) بنفس أسلوب useAuth.js — تضمن ظهور توست واحد
// موحّد فوق كل التطبيق، حتى لو المكوّن الذي استدعاه أُغلق بعد ذلك مباشرة
// (مثال: مودال ينجح وتُغلق نفسها، ويبقى التوست ظاهرًا في الطبقة العليا)
const toast = ref({ show: false, type: 'success', message: '' })
let toastTimer = null

export function useToast() {
  const showToast = (type, message, duration = 3000) => {
    clearTimeout(toastTimer)
    toast.value = { show: true, type, message }
    toastTimer = setTimeout(() => {
      toast.value.show = false
    }, duration)
  }

  const hideToast = () => {
    clearTimeout(toastTimer)
    toast.value.show = false
  }

  return { toast, showToast, hideToast }
}