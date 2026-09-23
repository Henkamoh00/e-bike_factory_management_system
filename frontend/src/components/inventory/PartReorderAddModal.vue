<template>
  <div class="fixed inset-0 bg-black/60 flex items-center justify-center z-[65]">
    <div class="bg-white rounded-3xl shadow-2xl w-full max-w-md mx-4 p-8">
      <h2 class="text-xl font-bold mb-2 text-red-600">🛒 إضافة قطعة لقائمة الطلب</h2>
      <p class="text-sm text-gray-500 mb-6">
        اختر القطعة التي نفدت أو أوشكت على النفاد، لتظهر ضمن قائمة القطع المطلوب توفيرها.
      </p>

      <SearchableSelect
        v-model="selectedPartId"
        :async-search="searchParts"
        label="القطعة"
        placeholder="ابحث عن القطعة..."
        :allow-empty="false"
      />

      <p v-if="error" class="text-sm text-red-600 mt-4">{{ error }}</p>

      <div class="flex gap-3 mt-8">
        <button
          @click="submit"
          :disabled="loading || !selectedPartId"
          class="flex-1 bg-red-600 hover:bg-red-700 disabled:opacity-40 text-white py-3 rounded-xl font-bold"
        >
          {{ loading ? 'جاري الإضافة...' : 'إضافة للقائمة' }}
        </button>
        <button @click="$emit('close')" class="flex-1 bg-gray-100 hover:bg-gray-200 py-3 rounded-xl font-bold">إلغاء</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useAuth } from '../../composables/useAuth'
import { useToast } from '../../composables/useToast'
import SearchableSelect from '../shared/SearchableSelect.vue'

const { apiFetch } = useAuth()
const { showToast } = useToast()
const emit = defineEmits(['close', 'success'])

const selectedPartId = ref('')
const loading = ref(false)
const error = ref('')

const searchParts = async (query) => {
  const params = new URLSearchParams({ limit: 20 })
  if (query) params.set('q', query)
  const res = await apiFetch(`/api/inventory/parts/simple/?${params.toString()}`)
  if (!res.ok) return []
  const data = await res.json()
  return data.map(p => ({ label: `${p.name} (${p.unit})`, value: p.id }))
}

const submit = async () => {
  if (!selectedPartId.value) return
  error.value = ''
  loading.value = true
  try {
    const res = await apiFetch(`/api/inventory/parts/${selectedPartId.value}/reorder/`, {
      method: 'POST',
      body: JSON.stringify({ flagged: true })
    })
    if (res.ok) {
      showToast('success', '✅ تمت إضافة القطعة لقائمة الطلب')
      emit('success')
    } else {
      const data = await res.json()
      error.value = data.detail || 'تعذر تنفيذ العملية'
    }
  } catch (e) {
    error.value = 'تعذر الاتصال بالسيرفر'
  } finally {
    loading.value = false
  }
}
</script>