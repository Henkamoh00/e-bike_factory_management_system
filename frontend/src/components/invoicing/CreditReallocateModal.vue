<template>
  <div class="fixed inset-0 bg-black/60 flex items-center justify-center z-[75]">
    <div class="bg-white rounded-3xl shadow-2xl w-full max-w-md mx-4 max-h-[85vh] flex flex-col">
      <div class="p-8 overflow-y-auto flex-1">
        <h3 class="text-xl font-bold mb-2">تسديد فاتورة من الرصيد</h3>
        <p class="text-sm text-gray-500 mb-2">العميل: {{ customerName }}</p>
        <p class="text-sm text-gray-500 mb-6">
          الرصيد المتاح: <strong class="text-indigo-600">{{ Number(creditBalance).toFixed(2) }}</strong>
        </p>

        <div v-if="loading" class="text-center py-10 text-gray-400">جاري تحميل فواتير العميل...</div>
        <div v-else-if="targetOptions.length === 0" class="text-center py-10 text-gray-400">
          لا توجد فواتير نشطة غير مدفوعة بالكامل لهذا العميل حاليًا
        </div>

        <template v-else>
          <div class="space-y-2 mb-4">
            <label
              v-for="inv in targetOptions"
              :key="inv.id"
              class="flex items-center justify-between p-3 border-2 rounded-xl cursor-pointer transition"
              :class="selectedInvoiceId === inv.id ? 'border-indigo-400 bg-indigo-50' : 'border-gray-200 hover:border-gray-300'"
            >
              <div class="flex items-center gap-2">
                <input type="radio" :value="inv.id" v-model="selectedInvoiceId" @change="onSelectTarget(inv)" class="accent-indigo-600" />
                <span class="font-mono font-bold">{{ inv.invoice_number }}</span>
              </div>
              <span class="text-xs text-gray-500">المتبقي هناك: {{ Number(inv.remaining_amount).toFixed(2) }}</span>
            </label>
          </div>

          <div v-if="selectedInvoiceId">
            <label class="block text-sm font-medium text-gray-700 mb-2">المبلغ المُسدَّد</label>
            <input
              v-model.number="amount"
              type="number"
              min="0"
              :max="maxAllowedAmount"
              step="0.01"
              class="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-indigo-400 focus:outline-none mb-1"
            />
            <p class="text-xs text-gray-400">
              الحد الأقصى: {{ maxAllowedAmount.toFixed(2) }} (أقل قيمة بين الرصيد والمتبقي على الفاتورة الهدف)
            </p>
          </div>
        </template>

        <p v-if="error" class="text-sm text-red-600 mt-3">{{ error }}</p>
      </div>

      <div class="border-t p-4 flex gap-3 shrink-0">
        <button @click="$emit('close')" class="flex-1 py-3 rounded-2xl font-medium text-gray-600 hover:bg-gray-100">إلغاء</button>
        <button
          @click="submit"
          :disabled="!selectedInvoiceId || submitting"
          class="flex-1 py-3 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 text-white rounded-2xl font-bold"
        >
          {{ submitting ? 'جاري التسديد...' : 'تأكيد التسديد' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuth } from '../../composables/useAuth'
import { useToast } from '../../composables/useToast'

const { apiFetch } = useAuth()
const { showToast } = useToast()

const props = defineProps({
  customerId: { type: [Number, String], required: true },
  customerName: { type: String, default: '' },
  creditBalance: { type: [Number, String], required: true },
})
const emit = defineEmits(['close', 'success'])

const loading = ref(false)
const submitting = ref(false)
const targetOptions = ref([])
const selectedInvoiceId = ref(null)
const selectedTargetInvoice = ref(null)
const amount = ref(0)
const error = ref('')

const maxAllowedAmount = computed(() => {
  const sourceCredit = Number(props.creditBalance)
  const targetRemaining = selectedTargetInvoice.value ? Number(selectedTargetInvoice.value.remaining_amount) : 0
  return Math.min(sourceCredit, targetRemaining)
})

const onSelectTarget = (inv) => {
  selectedTargetInvoice.value = inv
  amount.value = maxAllowedAmount.value
}

const loadTargets = async () => {
  loading.value = true
  try {
    const params = new URLSearchParams({ customer_name: props.customerName, limit: 50 })
    const res = await apiFetch(`/api/invoices/?${params.toString()}`)
    if (res.ok) {
      const data = await res.json()
      targetOptions.value = data.items.filter(
        inv => inv.status !== 'cancelled' && inv.status !== 'paid' && Number(inv.remaining_amount) > 0
      )
    }
  } catch (e) {
    console.error('فواتير العميل', e)
  } finally {
    loading.value = false
  }
}

const submit = async () => {
  if (!selectedInvoiceId.value) return
  if (!amount.value || amount.value <= 0) {
    error.value = 'يرجى إدخال مبلغ صحيح'
    return
  }
  if (amount.value > maxAllowedAmount.value) {
    error.value = 'المبلغ أكبر من الحد الأقصى المسموح'
    return
  }
  error.value = ''
  submitting.value = true
  try {
    const res = await apiFetch(`/api/invoices/customers/${props.customerId}/credit/reallocate/`, {
      method: 'POST',
      body: JSON.stringify({ target_invoice_id: selectedInvoiceId.value, amount: amount.value })
    })
    const data = await res.json()
    if (res.ok) {
      showToast('success', '✅ تم تسديد الفاتورة من الرصيد بنجاح')
      emit('success')
    } else {
      showToast('error', '❌ ' + (data.detail || 'تعذر تنفيذ العملية'))
    }
  } catch (e) {
    showToast('error', 'تعذر الاتصال بالسيرفر')
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  loadTargets()
})
</script>