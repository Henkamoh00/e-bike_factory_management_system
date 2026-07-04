<template>
  <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-[60]">
    <div class="bg-white rounded-2xl p-8 w-full max-w-md mx-4 shadow-2xl relative">

      <!-- Toast نجاح/خطأ -->
      <transition name="fade">
        <div
          v-if="toast.show"
          class="absolute top-4 left-1/2 -translate-x-1/2 px-4 py-2 rounded-xl text-sm font-medium shadow-lg z-10"
          :class="toast.type === 'success' ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'"
        >
          {{ toast.message }}
        </div>
      </transition>

      <h3 class="text-xl font-bold mb-6">إضافة عميل جديد</h3>
      <div class="space-y-4">
        <div>
          <label class="block text-sm text-gray-600 mb-1">اسم العميل</label>
          <input v-model="form.name" type="text" placeholder="الاسم الكامل"
            class="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-indigo-400 focus:outline-none" />
        </div>
        <div>
          <label class="block text-sm text-gray-600 mb-1">رقم الهاتف</label>
          <input v-model="form.phone" type="text" placeholder="05xxxxxxxx"
            class="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-indigo-400 focus:outline-none" />
        </div>
        <div>
          <label class="block text-sm text-gray-600 mb-1">العنوان (اختياري)</label>
          <input v-model="form.address" type="text" placeholder="المدينة / الحي"
            class="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-indigo-400 focus:outline-none" />
        </div>
      </div>
      <div class="flex gap-3 mt-6">
        <button @click="submit" :disabled="loading"
          class="flex-1 bg-purple-600 hover:bg-purple-700 text-white py-3 rounded-xl font-bold">
          {{ loading ? 'جاري الحفظ...' : 'حفظ' }}
        </button>
        <button @click="emit('close')"
          class="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-800 py-3 rounded-xl font-bold">
          إلغاء
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const emit = defineEmits(['close', 'success'])
const loading = ref(false)

const form = ref({ name: '', phone: '', address: '' })

const toast = ref({ show: false, type: 'success', message: '' })
let toastTimer = null

const showToast = (type, message, duration = 2000) => {
  clearTimeout(toastTimer)
  toast.value = { show: true, type, message }
  toastTimer = setTimeout(() => {
    toast.value.show = false
  }, duration)
}

const submit = async () => {
  if (!form.value.name.trim()) {
    showToast('error', 'يرجى إدخال اسم العميل')
    return
  }
  if (!form.value.phone.trim()) {
    showToast('error', 'رقم الهاتف مطلوب')
    return
  }

  loading.value = true
  try {
    const res = await fetch('http://localhost:8000/api/admin/customers/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form.value)
    })
    const data = await res.json()

    if (res.ok) {
      showToast('success', '✅ تم إضافة العميل بنجاح')
      setTimeout(() => emit('success', data), 700)   // مهلة صغيرة ليرى المستخدم الرسالة قبل إغلاق المودال
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
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}
</style>