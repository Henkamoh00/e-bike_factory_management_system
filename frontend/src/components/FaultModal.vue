<template>
  <div class="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
    <div class="bg-white rounded-3xl shadow-2xl w-full max-w-md mx-4">
      <div class="p-8">
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

        <textarea v-model="form.description" placeholder="وصف العطل بالتفصيل" class="w-full p-4 border rounded-2xl h-32"></textarea>
      </div>

      <div class="border-t p-4 flex gap-3">
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
import SearchableSelect from './SearchableSelect.vue'

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
  description: ''
})

const submit = async () => {
  if (!form.value.chassis_number || !form.value.description) {
    alert('رقم الهيكل ووصف العطل مطلوبان')
    return
  }

  loading.value = true

  try {
    const res = await fetch('http://localhost:8000/api/admin/faults/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form.value)
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