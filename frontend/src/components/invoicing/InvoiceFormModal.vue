<template>
  <div class="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
    <div class="bg-white rounded-3xl shadow-2xl w-full max-w-2xl mx-4 max-h-[90vh] flex flex-col">
      <div class="p-8 overflow-y-auto flex-1">
        <h2 class="text-2xl font-bold mb-6 text-emerald-700">🧾 فاتورة جديدة</h2>

        <div class="mb-2">
          <SearchableSelect
            v-model="form.customer_id"
            :async-search="searchCustomers"
            label="العميل"
            placeholder="اختر العميل"
            :allow-empty="false"
          />
        </div>
        <button
          type="button"
          @click="showCustomerForm = true"
          class="text-sm text-indigo-600 hover:text-indigo-800 underline mb-6"
        >
          + إضافة عميل جديد
        </button>

        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-3">بنود الفاتورة (الدراجات)</label>

          <div v-if="form.items.length === 0" class="text-center py-8 text-gray-400 bg-gray-50 rounded-2xl">
            لم تتم إضافة أي بند بعد
          </div>

          <div v-else class="space-y-3 mb-3">
            <div
              v-for="(item, idx) in form.items"
              :key="idx"
              class="flex items-center gap-3 p-3 bg-gray-50 rounded-2xl"
            >
              <div class="shrink-0">
                <span class="font-mono font-bold text-gray-800 block">{{ item.chassis_number }}</span>
                <span v-if="item.bike_type_name" class="text-xs text-gray-400">{{ item.bike_type_name }}</span>
              </div>
              <input
                v-model.number="item.unit_price"
                type="number"
                min="0"
                step="0.01"
                placeholder="السعر"
                class="flex-1 px-3 py-2 border-2 border-gray-200 rounded-xl focus:border-emerald-400 focus:outline-none text-sm"
              />
              <button
                type="button"
                @click="removeItem(idx)"
                class="w-8 h-8 flex items-center justify-center rounded-lg text-red-400 hover:bg-red-50 hover:text-red-600 transition shrink-0"
              >
                🗑️
              </button>
            </div>
          </div>

          <div class="flex gap-2">
            <div class="flex-1">
              <SearchableSelect
                v-model="pendingChassis"
                :options="availableChassisOptions"
                placeholder="اختر هيكلًا لإضافته"
                :allow-empty="false"
              />
            </div>
            <button
              type="button"
              @click="addItem"
              :disabled="!pendingChassis"
              class="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-40 text-white rounded-xl font-medium shrink-0"
            >
              + إضافة
            </button>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-3 mb-4">
          <div>
            <label class="block text-sm text-gray-500 mb-1">نوع الخصم (اختياري)</label>
            <select v-model="form.discount_type" class="w-full px-4 py-2 border-2 border-gray-200 rounded-xl focus:border-emerald-400 focus:outline-none bg-white">
              <option :value="null">بدون خصم</option>
              <option value="percentage">نسبة مئوية %</option>
              <option value="fixed">مبلغ ثابت</option>
            </select>
          </div>
          <div>
            <label class="block text-sm text-gray-500 mb-1">قيمة الخصم</label>
            <input
              v-model.number="form.discount_value"
              type="number"
              min="0"
              step="0.01"
              :disabled="!form.discount_type"
              class="w-full px-4 py-2 border-2 border-gray-200 rounded-xl focus:border-emerald-400 focus:outline-none disabled:bg-gray-50 disabled:text-gray-400"
            />
          </div>
        </div>

        <div class="p-4 bg-emerald-50 rounded-2xl mb-4 space-y-1">
          <div class="flex justify-between text-sm">
            <span class="text-gray-600">المجموع الفرعي</span>
            <span class="font-medium">{{ subtotal.toFixed(2) }}</span>
          </div>
          <div v-if="form.discount_type" class="flex justify-between text-sm text-red-500">
            <span>الخصم</span>
            <span>- {{ discountAmount.toFixed(2) }}</span>
          </div>
          <div class="flex justify-between text-base font-bold text-emerald-700 pt-1 border-t border-emerald-200">
            <span>الإجمالي</span>
            <span>{{ total.toFixed(2) }}</span>
          </div>
        </div>

        <!-- 🆕 دفعة فورية عند الإنشاء (البيع النقدي المباشر) -->
        <div class="p-4 border-2 border-dashed border-indigo-200 rounded-2xl mb-4">
          <label class="flex items-center gap-2 cursor-pointer select-none mb-3">
            <input type="checkbox" v-model="receivePaymentNow" class="w-4 h-4 accent-indigo-600 rounded" />
            <span class="text-sm font-medium text-gray-700">استلام دفعة الآن (عند إنشاء الفاتورة مباشرة)</span>
          </label>

          <div v-if="receivePaymentNow" class="flex gap-2">
            <input
              v-model.number="form.initial_payment_amount"
              type="number"
              min="0"
              :max="total"
              step="0.01"
              placeholder="المبلغ المستلم الآن"
              class="flex-1 px-4 py-2 border-2 border-gray-200 rounded-xl focus:border-indigo-400 focus:outline-none"
            />
            <input
              v-model="form.initial_payment_method"
              type="text"
              placeholder="طريقة الدفع (اختياري)"
              class="flex-1 px-4 py-2 border-2 border-gray-200 rounded-xl focus:border-indigo-400 focus:outline-none"
            />
          </div>
          <p v-if="receivePaymentNow && form.initial_payment_amount > 0" class="text-xs text-indigo-600 mt-2">
            سيتبقى على الفاتورة بعد هذه الدفعة: {{ Math.max(0, total - (Number(form.initial_payment_amount) || 0)).toFixed(2) }}
          </p>
        </div>

        <textarea v-model="form.notes" placeholder="ملاحظات (اختياري)" class="w-full p-4 border rounded-2xl h-20"></textarea>
      </div>

      <div class="border-t p-4 flex gap-3 shrink-0">
        <button @click="cancel" class="flex-1 py-4 rounded-2xl font-medium text-gray-600 hover:bg-gray-100">إلغاء</button>
        <button @click="submit" :disabled="loading" class="flex-1 py-4 bg-emerald-600 hover:bg-emerald-700 text-white rounded-2xl font-bold">
          {{ loading ? 'جاري الإنشاء...' : '✅ إنشاء الفاتورة' }}
        </button>
      </div>
    </div>

    <CustomerFormModal
      v-if="showCustomerForm"
      @close="showCustomerForm = false"
      @success="handleCustomerAdded"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuth } from '../../composables/useAuth'
import { useToast } from '../../composables/useToast'
import SearchableSelect from '../shared/SearchableSelect.vue'
import CustomerFormModal from '../admin/modals/CustomerFormModal.vue'

const { apiFetch } = useAuth()
const { showToast } = useToast()

const emit = defineEmits(['close', 'success'])
const loading = ref(false)
const showCustomerForm = ref(false)
const receivePaymentNow = ref(false)

const availableChassis = ref([])
const pendingChassis = ref('')

const form = ref({
  customer_id: '',
  items: [],
  discount_type: null,
  discount_value: 0,
  notes: '',
  initial_payment_amount: null,
  initial_payment_method: '',
})

const availableChassisOptions = computed(() =>
  availableChassis.value
    .filter(c => !form.value.items.some(item => item.chassis_number === c.chassis_number))
    .map(c => ({
      label: c.bike_type_name ? `${c.chassis_number} — ${c.bike_type_name}` : c.chassis_number,
      value: c.chassis_number
    }))
)

const loadAvailableChassis = async () => {
  try {
    const res = await apiFetch(`/api/invoices/available-chassis/`)
    if (res.ok) availableChassis.value = await res.json()
  } catch (e) { console.error('هياكل متاحة', e) }
}

const searchCustomers = async (query) => {
  const params = new URLSearchParams({ limit: 20 })
  if (query) params.set('q', query)
  const res = await apiFetch(`/api/customers/simple/?${params.toString()}`)
  if (!res.ok) return []
  const data = await res.json()
  return data.map(c => ({ label: c.name, value: c.id }))
}

const handleCustomerAdded = (newCustomer) => {
  showCustomerForm.value = false
  form.value.customer_id = newCustomer.id
}

const addItem = () => {
  if (!pendingChassis.value) return
  const chassisInfo = availableChassis.value.find(c => c.chassis_number === pendingChassis.value)
  form.value.items.push({
    chassis_number: pendingChassis.value,
    bike_type_name: chassisInfo?.bike_type_name || null,
    unit_price: chassisInfo?.default_price != null ? Number(chassisInfo.default_price) : 0,
    notes: null
  })
  pendingChassis.value = ''
}

const removeItem = (idx) => {
  form.value.items.splice(idx, 1)
}

const subtotal = computed(() =>
  form.value.items.reduce((sum, item) => sum + (Number(item.unit_price) || 0), 0)
)

const discountAmount = computed(() => {
  if (!form.value.discount_type || !form.value.discount_value) return 0
  if (form.value.discount_type === 'percentage') {
    return subtotal.value * (Number(form.value.discount_value) / 100)
  }
  return Number(form.value.discount_value)
})

const total = computed(() => Math.max(0, subtotal.value - discountAmount.value))

const submit = async () => {
  if (!form.value.customer_id) {
    showToast('error', 'يرجى اختيار العميل')
    return
  }
  if (form.value.items.length === 0) {
    showToast('error', 'يرجى إضافة بند واحد على الأقل')
    return
  }
  if (form.value.items.some(item => !item.unit_price || item.unit_price <= 0)) {
    showToast('error', 'يرجى إدخال سعر صحيح لكل بند')
    return
  }
  if (receivePaymentNow.value && form.value.initial_payment_amount > total.value) {
    showToast('error', 'الدفعة الأولية أكبر من إجمالي الفاتورة')
    return
  }

  loading.value = true

  const payload = {
    customer_id: form.value.customer_id,
    items: form.value.items.map(item => ({
      chassis_number: item.chassis_number,
      unit_price: item.unit_price,
      notes: item.notes,
    })),
    discount_type: form.value.discount_type,
    discount_value: form.value.discount_type ? form.value.discount_value : null,
    notes: form.value.notes || null,
  }

  if (receivePaymentNow.value && form.value.initial_payment_amount > 0) {
    payload.initial_payment_amount = form.value.initial_payment_amount
    payload.initial_payment_method = form.value.initial_payment_method || null
  }

  try {
    const res = await apiFetch(`/api/invoices/`, {
      method: 'POST',
      body: JSON.stringify(payload)
    })
    const data = await res.json()

    if (res.ok) {
      showToast('success', `✅ تم إنشاء الفاتورة ${data.invoice_number} بنجاح`)
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
  loadAvailableChassis()
})
</script>