<template>
  <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-[60]">
    <div class="bg-white rounded-2xl w-full max-w-sm mx-4 shadow-2xl p-8">
      <h3 class="text-xl font-bold mb-6">+ إضافة مورّد جديد</h3>

      <label class="block text-sm text-gray-600 mb-1">اسم المورّد</label>
      <input
        v-model="name"
        type="text"
        placeholder="اسم المورّد أو الشركة"
        class="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-indigo-400 focus:outline-none mb-6"
        @keyup.enter="submit"
      />

      <p v-if="error" class="text-sm text-red-600 mb-4">{{ error }}</p>

      <div class="flex gap-3">
        <button @click="submit" :disabled="loading" class="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white py-3 rounded-xl font-bold">
          {{ loading ? 'جاري الحفظ...' : 'حفظ' }}
        </button>
        <button @click="emit('close')" class="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-800 py-3 rounded-xl font-bold">إلغاء</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useAuth } from '../../composables/useAuth'

const { apiFetch } = useAuth()

const emit = defineEmits(['close', 'success'])
const name = ref('')
const loading = ref(false)
const error = ref('')

const submit = async () => {
  if (!name.value.trim()) {
    error.value = 'يرجى إدخال اسم المورّد'
    return
  }
  error.value = ''
  loading.value = true
  try {
    const res = await apiFetch(`/api/inventory/suppliers/`, {
      method: 'POST',
      body: JSON.stringify({ name: name.value })
    })
    const data = await res.json()
    if (res.ok) {
      emit('success', data)
    } else {
      error.value = data.detail || 'حدث خطأ'
    }
  } catch (e) {
    error.value = 'تعذر الاتصال بالسيرفر'
  } finally {
    loading.value = false
  }
}
</script>