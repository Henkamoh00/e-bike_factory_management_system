<template>
  <div>
    <div class="flex items-center justify-between mb-2 flex-wrap gap-3">
      <h2 class="text-2xl font-bold">💸 معالجة مبالغ الفواتير الملغاة</h2>

      <div class="inline-flex bg-gray-100 rounded-full p-1">
        <button
          @click="viewMode = 'pending'"
          class="px-4 py-1.5 rounded-full text-sm font-medium transition-all"
          :class="viewMode === 'pending' ? 'bg-white text-amber-600 shadow' : 'text-gray-500 hover:text-gray-700'"
        >
          🟠 المعلّقة
        </button>
        <button
          @click="switchToResolved"
          class="px-4 py-1.5 rounded-full text-sm font-medium transition-all"
          :class="viewMode === 'resolved' ? 'bg-white text-gray-600 shadow' : 'text-gray-500 hover:text-gray-700'"
        >
          ✅ المسترجعة
        </button>
      </div>
    </div>

    <p class="text-sm text-gray-500 mb-6">
      يمكنك تقسيم المبلغ على أكثر من إجراء (استرجاع جزئي + نقل جزئي لأكثر من فاتورة) حتى تتم معالجة كامل المبلغ.
      لا يُحذف أي سجل أبدًا — كل إجراء استرجاع يظهر فورًا في قائمة "المسترجعة" أدناه بمجرد تسجيله، وتبقى الفاتورة
      ظاهرة في "المعلّقة" أيضًا حتى تكتمل معالجة كامل المبلغ.
    </p>

    <div v-if="loading" class="text-center py-16 text-gray-400 text-lg">جاري التحميل...</div>

    <template v-else-if="viewMode === 'pending'">
      <div v-if="pendingItems.length === 0" class="text-center py-16 text-gray-400 text-lg">
        ✅ لا توجد مبالغ معلّقة بحاجة لمعالجة حاليًا
      </div>

      <div v-else class="bg-white rounded-3xl shadow-xl divide-y divide-gray-100">
        <div v-for="inv in pendingItems" :key="inv.invoice_id" class="flex items-center justify-between gap-4 px-5 py-4 flex-wrap">
          <div class="min-w-0">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="font-mono font-bold text-gray-800">{{ inv.invoice_number }}</span>
              <span
                class="text-xs rounded-full px-2 py-0.5"
                :class="inv.invoice_status === 'cancelled' ? 'bg-gray-100 text-gray-500' : 'bg-blue-50 text-blue-600'"
              >
                {{ inv.invoice_status === 'cancelled' ? 'ملغاة' : 'فائض بعد إرجاع' }}
              </span>
              <span v-if="Number(inv.processed_amount) > 0" class="text-xs bg-emerald-50 text-emerald-600 rounded-full px-2 py-0.5">
                🔄 معالجة جزئية جارية
              </span>
            </div>
            <div class="text-sm text-gray-500 mt-1">{{ inv.customer_name }}</div>
            <div v-if="inv.cancelled_at" class="text-xs text-gray-400 mt-0.5">
              أُلغيت: {{ new Date(inv.cancelled_at).toLocaleDateString('ar-EG') }}
            </div>
          </div>

          <div class="flex items-center gap-3 shrink-0 flex-wrap">
            <div class="text-left">
              <div class="font-bold text-lg text-amber-600">{{ Number(inv.remaining_unprocessed).toFixed(2) }}</div>
              <div v-if="Number(inv.processed_amount) > 0" class="text-xs text-gray-400">
                من أصل {{ Number(inv.paid_amount).toFixed(2) }} (عُولج {{ Number(inv.processed_amount).toFixed(2) }})
              </div>
            </div>
            <button
              @click="openReallocate(inv)"
              class="text-xs bg-indigo-50 hover:bg-indigo-100 text-indigo-600 px-3 py-2 rounded-full font-medium"
            >
              ↪️ نقل لفاتورة أخرى
            </button>
            <button
              @click="openConfirmRefund(inv)"
              class="text-xs bg-emerald-50 hover:bg-emerald-100 text-emerald-700 px-3 py-2 rounded-full font-medium"
            >
              ✅ تسجيل استرجاع
            </button>
          </div>
        </div>
      </div>
    </template>

    <template v-else>
      <div v-if="resolvedItems.length === 0" class="text-center py-16 text-gray-400 text-lg">
        لا توجد إجراءات استرجاع مسجَّلة بعد
      </div>

      <div v-else class="bg-white rounded-3xl shadow-xl divide-y divide-gray-100">
        <div
          v-for="inv in resolvedItems"
          :key="inv.invoice_id"
          class="px-5 py-4"
          :class="inv.fully_resolved ? 'opacity-60' : ''"
        >
          <div class="flex items-center justify-between gap-4 flex-wrap mb-2">
            <div class="flex items-center gap-2 flex-wrap min-w-0">
              <span
                class="font-mono font-bold text-gray-700"
                :class="inv.fully_resolved ? 'line-through text-gray-500' : ''"
              >
                {{ inv.invoice_number }}
              </span>
              <span
                class="text-xs rounded-full px-2 py-0.5"
                :class="inv.fully_resolved ? 'bg-gray-200 text-gray-500' : 'bg-amber-100 text-amber-600'"
              >
                {{ inv.fully_resolved ? 'مُعالَجة بالكامل' : '🔄 معالجة جزئية' }}
              </span>
            </div>
            <span class="font-bold text-gray-500">{{ Number(inv.paid_amount).toFixed(2) }}</span>
          </div>
          <div class="text-sm text-gray-400 mb-2">{{ inv.customer_name }}</div>

          <div class="flex flex-wrap gap-2">
            <span
              v-for="(action, idx) in inv.actions"
              :key="idx"
              class="text-xs bg-gray-100 text-gray-500 rounded-full px-3 py-1"
            >
              {{ action.action_type === 'refunded' ? '💵 استرجاع' : '↪️ نقل' }}
              {{ Number(action.amount).toFixed(2) }}
              <span v-if="action.target_invoice_number">→ {{ action.target_invoice_number }}</span>
            </span>
          </div>
        </div>
      </div>
    </template>

    <ReallocatePaymentModal
      v-if="reallocatingInvoice"
      :invoice="reallocatingInvoice"
      @close="reallocatingInvoice = null"
      @success="handleActionSuccess"
    />

    <ConfirmRefundModal
      v-if="confirmingInvoice"
      :invoice="confirmingInvoice"
      :loading="confirmLoading"
      @close="confirmingInvoice = null"
      @confirm="submitConfirmRefund"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuth } from '../../composables/useAuth'
import { useToast } from '../../composables/useToast'
import ReallocatePaymentModal from './ReallocatePaymentModal.vue'
import ConfirmRefundModal from './ConfirmRefundModal.vue'

const { apiFetch } = useAuth()
const { showToast } = useToast()

const viewMode = ref('pending')
const pendingItems = ref([])
const resolvedItems = ref([])
const loading = ref(false)

const reallocatingInvoice = ref(null)
const confirmingInvoice = ref(null)
const confirmLoading = ref(false)

const loadPending = async () => {
  loading.value = true
  try {
    const res = await apiFetch(`/api/invoices/pending-refunds/`)
    if (res.ok) pendingItems.value = await res.json()
  } catch (e) {
    console.error('مبالغ معلقة', e)
  } finally {
    loading.value = false
  }
}

const loadResolved = async () => {
  loading.value = true
  try {
    const res = await apiFetch(`/api/invoices/resolved-refunds/`)
    if (res.ok) resolvedItems.value = await res.json()
  } catch (e) {
    console.error('مبالغ مسترجعة', e)
  } finally {
    loading.value = false
  }
}

const switchToResolved = () => {
  viewMode.value = 'resolved'
  loadResolved()
}

const openReallocate = (inv) => { reallocatingInvoice.value = inv }
const openConfirmRefund = (inv) => { confirmingInvoice.value = inv }

const submitConfirmRefund = async (amount) => {
  if (!confirmingInvoice.value) return
  confirmLoading.value = true
  try {
    const res = await apiFetch(`/api/invoices/${confirmingInvoice.value.invoice_id}/refund/mark-refunded/`, {
      method: 'POST',
      body: JSON.stringify({ amount })
    })
    const data = await res.json()
    if (res.ok) {
      showToast('success', '✅ تم تسجيل الاسترجاع بنجاح')
      confirmingInvoice.value = null
      loadPending()
    } else {
      showToast('error', '❌ ' + (data.detail || 'تعذر تسجيل الاسترجاع'))
    }
  } catch (e) {
    showToast('error', 'تعذر الاتصال بالسيرفر')
  } finally {
    confirmLoading.value = false
  }
}

const handleActionSuccess = () => {
  reallocatingInvoice.value = null
  loadPending()
}

onMounted(() => {
  loadPending()
})
</script>