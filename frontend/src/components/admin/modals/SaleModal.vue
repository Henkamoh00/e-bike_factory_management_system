<template>
  <div class="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
    <div class="bg-white rounded-3xl shadow-2xl w-full max-w-md mx-4 max-h-[90vh] flex flex-col">
      <div class="p-8 overflow-y-auto flex-1">
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

        <div class="mb-2">
          <SearchableSelect
            v-model="form.customer_id"
            :options="customerOptions"
            label="العميل"
            placeholder="اختر العميل"
            :allow-empty="false"
          />
        </div>
        <button
          type="button"
          @click="showCustomerForm = true"
          class="text-sm text-indigo-600 hover:text-indigo-800 underline mb-4"
        >
          + إضافة عميل جديد
        </button>

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

      <div class="border-t p-4 flex gap-3 shrink-0">
        <button @click="cancel" class="flex-1 py-4 rounded-2xl font-medium text-gray-600 hover:bg-gray-100">إلغاء</button>
        <button @click="submit" :disabled="loading" class="flex-1 py-4 bg-green-600 hover:bg-green-700 text-white rounded-2xl font-bold">
          {{ loading ? 'جاري التسجيل...' : 'تسجيل البيع' }}
        </button>
      </div>
    </div>

    <!-- مودال إضافة عميل متداخل -->
    <CustomerFormModal
      v-if="showCustomerForm"
      @close="showCustomerForm = false"
      @success="handleCustomerAdded"
    />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import SearchableSelect from '../../shared/SearchableSelect.vue'
import CustomerFormModal from '../../admin/modals/CustomerFormModal.vue'

const API = import.meta.env.VITE_API_BASE_URL

const requestHeaders = {
  'Content-Type': 'application/json'
}

if (API.includes('ngrok')) {
  requestHeaders['ngrok-skip-browser-warning'] = 'true'
}

const emit = defineEmits(['close', 'success', 'customer-added'])
const loading = ref(false)
const showCustomerForm = ref(false)

const props = defineProps({
  customersList: { type: Array, default: () => [] },
  chassisList: { type: Array, default: () => [] }
})

const customerOptions = computed(() =>
  props.customersList.map(c => ({ label: c.name, value: c.id }))
)

const chassisOptions = computed(() =>
  props.chassisList.map(cn => ({ label: cn, value: cn }))
)

const today = new Date().toISOString().split('T')[0]

const form = ref({
  chassis_number: '',
  customer_id: '',
  sale_date: '',
  notes: ''
})

const handleCustomerAdded = (newCustomer) => {
  showCustomerForm.value = false
  form.value.customer_id = newCustomer.id
  emit('customer-added')
}

const submit = async () => {
  if (!form.value.chassis_number || !form.value.customer_id) {
    alert('رقم الهيكل والعميل مطلوبان')
    return
  }

  loading.value = true

  const payload = { ...form.value }
  if (!payload.sale_date) delete payload.sale_date

  try {
    const res = await fetch(`${API}/api/sales/`, {
      method: 'POST',
      headers: requestHeaders,
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