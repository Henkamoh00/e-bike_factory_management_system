<template>
  <div class="fixed inset-0 bg-black/60 flex items-center justify-center z-[70]">
    <div class="bg-white rounded-3xl shadow-2xl w-full max-w-md mx-4 max-h-[90vh] flex flex-col">
      <div class="p-8 overflow-y-auto flex-1">
        <h2 class="text-2xl font-bold mb-2 text-emerald-700">تصليح جماعي</h2>
        <p class="text-sm text-gray-500 mb-6">سيتم تسجيل {{ count }} عطل كمُصلَح بواسطة نفس العامل</p>

        <SearchableSelect
          v-model="workerName"
          :async-search="searchWorkers"
          label="العامل الذي قام بالتصليح"
          placeholder="اختر العامل"
          :allow-empty="false"
        />
      </div>

      <div class="border-t p-4 flex gap-3 shrink-0">
        <button @click="$emit('close')" class="flex-1 py-4 rounded-2xl font-medium text-gray-600 hover:bg-gray-100">إلغاء</button>
        <button @click="confirm" :disabled="loading || !workerName" class="flex-1 py-4 bg-emerald-600 hover:bg-emerald-700 text-white rounded-2xl font-bold">
          {{ loading ? 'جاري التسجيل...' : '✅ تأكيد التصليح' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useAuth } from '../../../composables/useAuth'
import SearchableSelect from '../../shared/SearchableSelect.vue'

const { apiFetch } = useAuth()

const props = defineProps({
  count: { type: Number, default: 0 },
  loading: { type: Boolean, default: false }
})

const emit = defineEmits(['close', 'confirm'])

const workerName = ref('')

const searchWorkers = async (query) => {
  const params = new URLSearchParams({ limit: 20 })
  if (query) params.set('q', query)
  const res = await apiFetch(`/api/workers/simple/?${params.toString()}`)
  if (!res.ok) return []
  const data = await res.json()
  return data.map(w => ({ label: w.name, value: w.name }))
}

const confirm = () => {
  if (!workerName.value) return
  emit('confirm', workerName.value)
}
</script>