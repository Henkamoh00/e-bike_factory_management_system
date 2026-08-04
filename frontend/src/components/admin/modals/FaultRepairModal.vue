<template>
  <div class="fixed inset-0 bg-black/60 flex items-center justify-center z-[65]">
    <div class="bg-white rounded-3xl shadow-2xl w-full max-w-md mx-4 max-h-[90vh] flex flex-col">
      <div class="p-8 overflow-y-auto flex-1">
        <h2 class="text-2xl font-bold mb-2 text-emerald-700">تسجيل تصليح عطل</h2>
        <p class="text-sm text-gray-500 mb-6 font-mono">{{ fault.chassis_number }} — {{ fault.description }}</p>

        <div class="mb-2">
          <SearchableSelect
            v-model="form.worker_name"
            :async-search="searchWorkers"
            :initial-selected-label="form.worker_name"
            label="العامل الذي قام بالتصليح"
            placeholder="اختر العامل"
            :allow-empty="false"
          />
        </div>
        <p v-if="suggestedWorkerName" class="text-xs text-indigo-600 mb-4">
          💡 مقترح: {{ suggestedWorkerName }} (قام بمرحلة {{ relatedStageLabel }} لهذا الهيكل)
        </p>

        <textarea v-model="form.notes" placeholder="ملاحظات التصليح (اختياري)" class="w-full p-4 border rounded-2xl h-24 mt-2"></textarea>
      </div>

      <div class="border-t p-4 flex gap-3 shrink-0">
        <button @click="cancel" class="flex-1 py-4 rounded-2xl font-medium text-gray-600 hover:bg-gray-100">إلغاء</button>
        <button @click="submit" :disabled="loading" class="flex-1 py-4 bg-emerald-600 hover:bg-emerald-700 text-white rounded-2xl font-bold">
          {{ loading ? 'جاري التسجيل...' : '✅ تأكيد التصليح' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuth } from '../../../composables/useAuth'
import { useToast } from '../../../composables/useToast'
import SearchableSelect from '../../shared/SearchableSelect.vue'

const { apiFetch } = useAuth()
const { showToast } = useToast()

const emit = defineEmits(['close', 'success'])
const loading = ref(false)
const suggestedWorkerName = ref('')

const props = defineProps({
  fault: { type: Object, required: true }
})

const searchWorkers = async (query) => {
  const params = new URLSearchParams({ limit: 20 })
  if (query) params.set('q', query)
  const res = await apiFetch(`/api/workers/simple/?${params.toString()}`)
  if (!res.ok) return []
  const data = await res.json()
  return data.map(w => ({ label: w.name, value: w.name }))
}

const stageNames = {
  'تجميع_الهيكل':           'تجميع الهيكل',
  'توصيل_الكهرباء_والغلاف': 'توصيل الكهرباء والغلاف',
  'تجميع_كامل':             'تجميع كامل',
}
const relatedStageLabel = computed(() => stageNames[props.fault.related_stage] || '')

const form = ref({
  worker_name: '',
  notes: ''
})

const loadSuggestedWorker = async () => {
  try {
    const res = await apiFetch(`/api/faults/${props.fault.id}/suggested-worker/`)
    if (res.ok) {
      const data = await res.json()
      if (data.worker_name) {
        suggestedWorkerName.value = data.worker_name
        form.value.worker_name = data.worker_name
      }
    }
  } catch (e) { console.error('العامل المقترح', e) }
}

const submit = async () => {
  if (!form.value.worker_name) {
    showToast('error', 'يرجى اختيار العامل الذي قام بالتصليح')
    return
  }

  loading.value = true
  try {
    const res = await apiFetch(`/api/faults/${props.fault.id}/repair/`, {
      method: 'POST',
      body: JSON.stringify(form.value)
    })

    const data = await res.json()

    if (res.ok) {
      showToast('success', '✅ تم تسجيل التصليح بنجاح')
      emit('success')
    } else {
      showToast('error', '❌ ' + (data.detail || 'حدث خطأ'))
    }
  } catch (e) {
    showToast('error', 'تعذر الاتصال بالسيرفر')
  } finally {
    loading.value = false
  }
}

const cancel = () => emit('close')

onMounted(() => {
  loadSuggestedWorker()
})
</script>