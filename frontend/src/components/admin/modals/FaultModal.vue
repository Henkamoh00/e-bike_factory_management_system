<template>
  <div class="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
    <div class="bg-white rounded-3xl shadow-2xl w-full max-w-md mx-4 max-h-[90vh] flex flex-col">
      <div class="p-8 overflow-y-auto flex-1">
        <h2 class="text-2xl font-bold mb-6 text-red-600">تسجيل عطل جديد</h2>

        <div class="mb-4">
          <SearchableSelect
            v-model="form.chassis_number"
            :options="chassisOptions"
            label="رقم الهيكل"
            placeholder="اختر رقم الهيكل"
            :allow-empty="false"
          />
        </div>

        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-3">المرحلة المرتبطة بالعطل (اختياري)</label>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
            <button
              type="button"
              @click="toggleStage('تجميع_الهيكل')"
              :class="form.related_stage === 'تجميع_الهيكل' ? 'ring-2 ring-red-500 bg-red-50' : 'border-2 border-gray-200'"
              class="p-3 rounded-2xl hover:border-red-300 transition-all flex flex-col items-start"
            >
              <div class="text-xl mb-1">🔧</div>
              <div class="font-bold text-sm">تجميع الهيكل</div>
            </button>

            <button
              type="button"
              @click="toggleStage('توصيل_الكهرباء_والغلاف')"
              :class="form.related_stage === 'توصيل_الكهرباء_والغلاف' ? 'ring-2 ring-red-500 bg-red-50' : 'border-2 border-gray-200'"
              class="p-3 rounded-2xl hover:border-red-300 transition-all flex flex-col items-start"
            >
              <div class="text-xl mb-1">⚡</div>
              <div class="font-bold text-sm">الكهرباء والغلاف</div>
            </button>

            <button
              type="button"
              @click="toggleStage('تجميع_كامل')"
              :class="form.related_stage === 'تجميع_كامل' ? 'ring-2 ring-red-500 bg-red-50' : 'border-2 border-gray-200'"
              class="p-3 rounded-2xl hover:border-red-300 transition-all flex flex-col items-start"
            >
              <div class="text-xl mb-1">🏁</div>
              <div class="font-bold text-sm">التجميع الكامل</div>
            </button>
          </div>
          <p class="text-xs text-gray-400 mt-2">يساعد باقتراح العامل المناسب عند التصليح لاحقًا</p>
        </div>

        <textarea v-model="form.description" placeholder="وصف العطل بالتفصيل" class="w-full p-4 border rounded-2xl h-32"></textarea>
      </div>

      <div class="border-t p-4 flex gap-3 shrink-0">
        <button @click="cancel" class="flex-1 py-4 rounded-2xl font-medium text-gray-600 hover:bg-gray-100">إلغاء</button>
        <button @click="submit" :disabled="loading" class="flex-1 py-4 bg-red-600 hover:bg-red-700 text-white rounded-2xl font-bold">
          {{ loading ? 'جاري التسجيل...' : 'تسجيل العطل' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useAuth } from '../../../composables/useAuth'
import SearchableSelect from '../../shared/SearchableSelect.vue'

const API = import.meta.env.VITE_API_BASE_URL
const { apiFetch } = useAuth()

const emit = defineEmits(['close', 'success'])
const loading = ref(false)

const props = defineProps({
  chassisList: {
    type: Array,
    default: () => []
  }
})

const chassisOptions = computed(() =>
  props.chassisList.map(cn => ({ label: cn, value: cn }))
)

const form = ref({
  chassis_number: '',
  description: '',
  related_stage: ''
})

const toggleStage = (stage) => {
  form.value.related_stage = form.value.related_stage === stage ? '' : stage
}

const submit = async () => {
  if (!form.value.chassis_number || !form.value.description) {
    alert('رقم الهيكل ووصف العطل مطلوبان')
    return
  }

  loading.value = true

  const payload = { ...form.value }
  if (!payload.related_stage) delete payload.related_stage

  try {
    const res = await apiFetch(`/api/faults/`, {
      method: 'POST',
      body: JSON.stringify(payload)
    })

    if (res.ok) {
      alert('⚠️ تم تسجيل العطل بنجاح!')
      emit('success')
    } else {
      const data = await res.json()
      alert('❌ ' + (data.detail || 'حدث خطأ'))
    }
  } catch (e) {
    alert('تعذر الاتصال بالسيرفر')
  } finally {
    loading.value = false
  }
}

const cancel = () => emit('close')
</script>