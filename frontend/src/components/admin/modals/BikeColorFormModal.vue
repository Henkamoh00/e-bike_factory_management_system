<template>
  <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-[60]">
    <div class="bg-white rounded-2xl w-full max-w-md mx-4 shadow-2xl relative max-h-[90vh] flex flex-col">
      <transition name="fade">
        <div v-if="toast.show" class="absolute top-4 left-1/2 -translate-x-1/2 px-4 py-2 rounded-xl text-sm font-medium shadow-lg z-10"
          :class="toast.type === 'success' ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'">
          {{ toast.message }}
        </div>
      </transition>

      <div class="p-8 overflow-y-auto flex-1">
        <h3 class="text-xl font-bold mb-6">{{ isEditing ? 'تعديل لون الدراجة' : 'إضافة لون دراجة جديد' }}</h3>
        <div>
          <label class="block text-sm text-gray-600 mb-1">اسم اللون</label>
          <input v-model="form.name" type="text" placeholder="مثال: أحمر"
            class="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-indigo-400 focus:outline-none" />
        </div>
      </div>
      <div class="flex gap-3 p-6 pt-0 shrink-0">
        <button @click="submit" :disabled="loading" class="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white py-3 rounded-xl font-bold">
          {{ loading ? 'جاري الحفظ...' : (isEditing ? 'حفظ التعديلات' : 'حفظ') }}
        </button>
        <button @click="emit('close')" class="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-800 py-3 rounded-xl font-bold">إلغاء</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const API = import.meta.env.VITE_API_BASE_URL

const requestHeaders = {
  'Content-Type': 'application/json'
}

if (API.includes('ngrok')) {
  requestHeaders['ngrok-skip-browser-warning'] = 'true'
}

const props = defineProps({
  bikeColor: { type: Object, default: null }
})

const emit = defineEmits(['close', 'success'])
const loading = ref(false)
const form = ref({ name: '' })

const isEditing = computed(() => !!props.bikeColor)

onMounted(() => {
  if (props.bikeColor) {
    form.value.name = props.bikeColor.name || ''
  }
})

const toast = ref({ show: false, type: 'success', message: '' })
let toastTimer = null

const showToast = (type, message, duration = 2000) => {
  clearTimeout(toastTimer)
  toast.value = { show: true, type, message }
  toastTimer = setTimeout(() => { toast.value.show = false }, duration)
}

const submit = async () => {
  if (!form.value.name.trim()) { showToast('error', 'يرجى إدخال اسم اللون'); return }
  loading.value = true
  try {
    const url = isEditing.value
      ? `${API}/api/bike-colors/${props.bikeColor.id}/`
      : `${API}/api/bike-colors/`
    const method = isEditing.value ? 'PUT' : 'POST'

    const res = await fetch(url, {
      method,
      headers: requestHeaders,
      body: JSON.stringify(form.value)
    })
    const data = await res.json()
    if (res.ok) {
      showToast('success', isEditing.value ? '✅ تم تحديث اللون بنجاح' : '✅ تم إضافة اللون بنجاح')
      setTimeout(() => emit('success', data), 700)
    } else {
      showToast('error', '❌ ' + (data.detail || 'حدث خطأ'))
    }
  } catch (e) {
    showToast('error', 'تعذر الاتصال بالسيرفر')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>