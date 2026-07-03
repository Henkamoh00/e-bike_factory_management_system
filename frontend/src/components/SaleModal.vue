<template>
  <div class="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
    <div class="bg-white rounded-3xl shadow-2xl w-full max-w-md mx-4">
      <div class="p-8">
        <h2 class="text-2xl font-bold mb-6">تسجيل بيع جديد</h2>

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
          <SearchableSelect
            v-model="form.customer_name"
            :options="customerOptions"
            label="العميل"
            placeholder="اختر العميل"
            :allow-empty="false"
          />
        </div>

        <div class="mb-4">
          <label class="block text-sm text-gray-500 mb-1">تاريخ البيع (اختياري)</label>
          <input
            v-model="form.sale_date"
            type="date"
            :max="today"
            class="w-full p-4 border rounded-2xl"
          />
          <p class="text-xs text-gray-400 mt-1">اتركه فارغًا إذا كان البيع اليوم</p>
        </div>

        <textarea v-model="form.notes" placeholder="ملاحظات (اختياري)" class="w-full p-4 border rounded-2xl h-24"></textarea>
      </div>

      <div class="border-t p-4 flex gap-3">
        <button @click="cancel" class="flex-1 py-4 rounded-2xl font-medium text-gray-600 hover:bg-gray-100">إلغاء</button>
        <button @click="submit" :disabled="loading" class="flex-1 py-4 bg-green-600 hover:bg-green-700 text-white rounded-2xl font-bold">
          {{ loading ? 'جاري التسجيل...' : 'تسجيل البيع' }}
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
  customersList: { type: Array, default: () => [] },
  chassisList: { type: Array, default: () => [] }
})

const customerOptions = computed(() =>
  props.customersList.map(c => ({ label: c.name, value: c.name }))
)

const chassisOptions = computed(() =>
  props.chassisList.map(cn => ({ label: cn, value: cn }))
)

const today = new Date().toISOString().split('T')[0] // يمنع اختيار تاريخ مستقبلي

const form = ref({
  chassis_number: '',
  customer_name: '',
  sale_date: '',   // ← جديد، فارغ افتراضيًا
  notes: ''
})

const submit = async () => {
  if (!form.value.chassis_number || !form.value.customer_name) {
    alert('رقم الهيكل واسم العميل مطلوبان')
    return
  }

  loading.value = true

  // نبني الـ payload ونحذف sale_date إذا فارغ، حتى الباك اند يستخدم القيمة الافتراضية (الآن)
  const payload = { ...form.value }
  if (!payload.sale_date) delete payload.sale_date

  try {
    const res = await fetch('http://localhost:8000/api/admin/sales/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })

    const data = await res.json()

    if (res.ok) {
      alert('✅ تم تسجيل البيع بنجاح!')
      emit('success')
    } else {
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