<template>
  <div class="fixed inset-0 bg-black/60 flex items-center justify-center z-[65]" @click.self="$emit('close')">
    <div class="bg-white rounded-3xl shadow-2xl w-full max-w-2xl mx-4 max-h-[90vh] flex flex-col">
      <div class="p-8 overflow-y-auto flex-1">
        <div class="flex items-center justify-between mb-2">
          <div>
            <h2 class="text-2xl font-bold font-mono text-gray-800">{{ invoice.invoice_number }}</h2>
            <p class="text-sm text-gray-500">{{ invoice.customer_name }}</p>
          </div>
          <div class="flex items-center gap-2">
            <button
              @click="openPdf"
              class="text-sm bg-indigo-50 hover:bg-indigo-100 text-indigo-700 px-4 py-2 rounded-full font-medium flex items-center gap-1.5 shrink-0"
              title="فتح/طباعة الفاتورة كملف PDF"
            >
              🖨️ طباعة / PDF
            </button>
            <span class="text-sm px-3 py-1.5 rounded-full font-medium" :class="statusTextClass(invoice.status)">
              {{ statusLabel(invoice.status) }}
            </span>
          </div>
        </div>

        <div v-if="invoice.status === 'paid'" class="mb-6 p-3 bg-emerald-50 text-emerald-700 text-sm rounded-2xl flex items-center gap-2">
          🔒 هذه الفاتورة مدفوعة بالكامل، لذلك جميع التعديلات (الدفعات والبنود) مقفلة تلقائيًا.
        </div>
        <div v-else class="mb-6"></div>

        <div class="mb-6">
          <h4 class="font-semibold text-sm text-gray-500 mb-3">البنود</h4>
          <div class="space-y-2">
            <div
              v-for="item in invoice.items"
              :key="item.id"
              class="p-3 rounded-xl"
              :class="item.is_returned ? 'bg-orange-50' : 'bg-gray-50'"
            >
              <div v-if="editingItemId !== item.id" class="flex justify-between items-center gap-3">
                <div class="min-w-0">
                  <div class="flex items-center gap-2 flex-wrap">
                    <span class="font-mono font-bold" :class="item.is_returned ? 'line-through text-gray-400' : ''">
                      {{ item.chassis_number }}
                    </span>
                    <span v-if="item.is_returned" class="text-xs bg-orange-100 text-orange-600 rounded-full px-2 py-0.5 shrink-0">
                      🔄 مُرجَع
                    </span>
                  </div>
                  <div v-if="item.is_returned && item.return_reason" class="text-xs text-orange-500 mt-0.5">
                    سبب الإرجاع: {{ item.return_reason }}
                  </div>
                  <div v-if="item.notes" class="text-xs text-gray-400 mt-0.5">{{ item.notes }}</div>
                </div>

                <div class="flex items-center gap-3 shrink-0">
                  <span class="text-gray-600" :class="item.is_returned ? 'line-through text-gray-400' : ''">
                    {{ Number(item.unit_price).toFixed(2) }}
                  </span>
                  <template v-if="!item.is_returned && canEditItems">
                    <button
                      @click="startEditItem(item)"
                      class="text-xs text-indigo-600 hover:text-indigo-800 underline"
                    >
                      تعديل
                    </button>
                    <button
                      @click="askDeleteItem(item)"
                      class="text-xs text-red-500 hover:text-red-700 underline"
                    >
                      حذف
                    </button>
                  </template>
                </div>
              </div>

              <div v-else class="flex items-center gap-2">
                <span class="font-mono font-bold text-sm shrink-0">{{ item.chassis_number }}</span>
                <input
                  v-model.number="itemEditForm.unit_price"
                  type="number" min="0" step="0.01"
                  class="flex-1 px-3 py-2 border-2 border-gray-200 rounded-xl focus:border-indigo-400 focus:outline-none text-sm"
                />
                <button @click="saveEditItem(item)" :disabled="itemEditLoading" class="px-3 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-medium shrink-0">
                  حفظ
                </button>
                <button @click="cancelEditItem" class="px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-xl text-xs shrink-0">
                  إلغاء
                </button>
              </div>
            </div>
          </div>
        </div>

        <div class="p-4 bg-emerald-50 rounded-2xl mb-6 space-y-1">
          <div class="flex justify-between text-sm"><span class="text-gray-600">المجموع الفرعي</span><span>{{ Number(invoice.subtotal).toFixed(2) }}</span></div>
          <div v-if="invoice.discount_type" class="flex justify-between text-sm text-red-500">
            <span>الخصم</span><span>- {{ (Number(invoice.subtotal) - Number(invoice.total_amount)).toFixed(2) }}</span>
          </div>
          <div class="flex justify-between text-base font-bold text-emerald-700 pt-1 border-t border-emerald-200">
            <span>الإجمالي</span><span>{{ Number(invoice.total_amount).toFixed(2) }}</span>
          </div>
          <div class="flex justify-between text-sm text-emerald-600"><span>المدفوع</span><span>{{ Number(invoice.paid_amount).toFixed(2) }}</span></div>
          <div v-if="Number(invoice.remaining_amount) > 0" class="flex justify-between text-sm font-bold text-red-600">
            <span>المتبقي</span><span>{{ Number(invoice.remaining_amount).toFixed(2) }}</span>
          </div>
        </div>

        <div class="mb-6">
          <h4 class="font-semibold text-sm text-gray-500 mb-3">سجل الدفعات</h4>
          <div v-if="invoice.payments?.length" class="space-y-2">
            <div v-for="p in invoice.payments" :key="p.id" class="p-3 bg-gray-50 rounded-xl">
              <div v-if="editingPaymentId !== p.id" class="flex justify-between items-center">
                <div>
                  <span class="font-bold text-emerald-700">{{ Number(p.amount).toFixed(2) }}</span>
                  <span v-if="p.payment_method" class="text-xs text-gray-400 mr-2">({{ p.payment_method }})</span>
                </div>
                <div class="flex items-center gap-3 shrink-0">
                  <span class="text-xs text-gray-400">{{ new Date(p.payment_date).toLocaleDateString('ar-EG') }}</span>
                  <template v-if="invoice.status !== 'cancelled' && invoice.status !== 'paid'">
                    <button @click="startEditPayment(p)" class="text-xs text-indigo-600 hover:text-indigo-800 underline">
                      تعديل
                    </button>
                    <button @click="askDeletePayment(p)" class="text-xs text-red-500 hover:text-red-700 underline">
                      حذف
                    </button>
                  </template>
                </div>
              </div>

              <div v-else class="flex items-center gap-2">
                <input
                  v-model.number="editForm.amount"
                  type="number" min="0" step="0.01"
                  class="flex-1 px-3 py-2 border-2 border-gray-200 rounded-xl focus:border-indigo-400 focus:outline-none text-sm"
                />
                <input
                  v-model="editForm.payment_method"
                  type="text" placeholder="طريقة الدفع"
                  class="flex-1 px-3 py-2 border-2 border-gray-200 rounded-xl focus:border-indigo-400 focus:outline-none text-sm"
                />
                <button @click="saveEditPayment(p)" :disabled="editLoading" class="px-3 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-medium shrink-0">
                  حفظ
                </button>
                <button @click="cancelEditPayment" class="px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-xl text-xs shrink-0">
                  إلغاء
                </button>
              </div>
            </div>
          </div>
          <div v-else class="text-center py-6 text-gray-400 text-sm">لا توجد دفعات مسجلة بعد</div>
        </div>

        <div v-if="invoice.status !== 'cancelled' && invoice.status !== 'paid'" class="p-4 border-2 border-dashed border-emerald-200 rounded-2xl">
          <h4 class="font-semibold text-sm text-gray-700 mb-3">تسجيل دفعة جديدة</h4>
          <div class="flex gap-2">
            <input
              v-model.number="paymentAmount"
              type="number"
              min="0"
              :max="invoice.remaining_amount"
              step="0.01"
              placeholder="المبلغ"
              class="flex-1 px-4 py-2 border-2 border-gray-200 rounded-xl focus:border-emerald-400 focus:outline-none"
            />
            <input
              v-model="paymentMethod"
              type="text"
              placeholder="طريقة الدفع (اختياري)"
              class="flex-1 px-4 py-2 border-2 border-gray-200 rounded-xl focus:border-emerald-400 focus:outline-none"
            />
            <button
              @click="submitPayment"
              :disabled="paymentLoading || !paymentAmount"
              class="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-40 text-white rounded-xl font-medium shrink-0"
            >
              {{ paymentLoading ? '...' : 'تسجيل' }}
            </button>
          </div>
        </div>
      </div>

      <div class="border-t p-4 flex gap-3 shrink-0">
        <button
          v-if="invoice.status !== 'cancelled'"
          @click="showCancelModal = true"
          class="flex-1 py-3 rounded-2xl font-medium text-red-600 hover:bg-red-50"
        >
          إلغاء الفاتورة
        </button>
        <button @click="$emit('close')" class="flex-1 py-3 rounded-2xl font-medium text-gray-600 hover:bg-gray-100">إغلاق</button>
      </div>
    </div>

    <!-- 🆕 تأكيد حذف بند -->
    <div v-if="pendingDeleteItem" class="fixed inset-0 bg-black/60 flex items-center justify-center z-[75]">
      <div class="bg-white rounded-2xl p-8 max-w-md mx-4 shadow-2xl">
        <div class="text-4xl mb-4">⚠️</div>
        <p class="text-gray-800 text-lg mb-3">
          هل أنت متأكد من حذف البند "<strong class="font-mono">{{ pendingDeleteItem.chassis_number }}</strong>" من الفاتورة؟
        </p>
        <p class="text-sm text-gray-500 mb-6">
          هذا الإجراء يُستخدم لتصحيح خطأ إدخال (مثل إضافة دراجة خاطئة)، وليس إرجاعًا.
        </p>

        <p v-if="willFullyDeleteInvoice" class="text-sm bg-red-50 text-red-600 rounded-xl p-3 mb-6">
          🗑️ هذا آخر بند في الفاتورة ولا توجد بها أي مدفوعات — ستُحذف
          <strong>الفاتورة بالكامل ونهائيًا</strong> (لا يمكن التراجع)، لأنها لن تحمل بعد ذلك أي معلومة.
        </p>
        <p v-else-if="isLastItem" class="text-sm bg-amber-50 text-amber-700 rounded-xl p-3 mb-6">
          ⚠️ هذا آخر بند في الفاتورة — حذفه سيُلغي الفاتورة تلقائيًا (وليس حذفها)،
          وسينتقل المبلغ المدفوع مسبقًا ({{ Number(invoice.paid_amount).toFixed(2) }}) تلقائيًا
          لقائمة "المدفوعات المعلقة" لمعالجته لاحقًا.
        </p>

        <div class="flex gap-3">
          <button @click="confirmDeleteItem" :disabled="itemEditLoading" class="flex-1 bg-red-600 text-white py-3 rounded-xl font-bold">
            {{ itemEditLoading ? 'جاري الحذف...' : 'نعم، احذف' }}
          </button>
          <button @click="pendingDeleteItem = null" class="flex-1 bg-gray-100 py-3 rounded-xl font-bold">إلغاء</button>
        </div>
      </div>
    </div>

    <!-- 🆕 تأكيد حذف دفعة -->
    <div v-if="pendingDeletePayment" class="fixed inset-0 bg-black/60 flex items-center justify-center z-[75]">
      <div class="bg-white rounded-2xl p-8 max-w-md mx-4 shadow-2xl">
        <div class="text-4xl mb-4">⚠️</div>
        <p class="text-gray-800 text-lg mb-3">
          هل أنت متأكد من حذف دفعة بقيمة "<strong>{{ Number(pendingDeletePayment.amount).toFixed(2) }}</strong>"؟
        </p>
        <p class="text-sm text-gray-500 mb-6">
          هذا الإجراء لتصحيح خطأ إدخال فقط (دفعة سُجِّلت بالخطأ)، ولن يترك أي أثر في سجل الفاتورة —
          إن كانت هذه دفعة حقيقية تريد استرجاعها للعميل، استخدم "إلغاء الفاتورة" بدلاً من ذلك.
        </p>
        <div class="flex gap-3">
          <button @click="confirmDeletePayment" :disabled="editLoading" class="flex-1 bg-red-600 text-white py-3 rounded-xl font-bold">
            {{ editLoading ? 'جاري الحذف...' : 'نعم، احذف' }}
          </button>
          <button @click="pendingDeletePayment = null" class="flex-1 bg-gray-100 py-3 rounded-xl font-bold">إلغاء</button>
        </div>
      </div>
    </div>

    <CancelReasonModal
      v-if="showCancelModal"
      title="إلغاء الفاتورة"
      :subtitle="`الفاتورة: ${invoice.invoice_number} — العميل: ${invoice.customer_name}`"
      icon="🧾"
      :loading="cancelLoading"
      :require-extra-confirm="hasPayments"
      :extra-confirm-text="`أؤكد أنني سأقوم برد المبلغ المدفوع (${Number(invoice.paid_amount).toFixed(2)}) للعميل يدويًا خارج النظام`"
      @close="showCancelModal = false"
      @confirm="confirmCancel"
    />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useAuth } from '../../composables/useAuth'
import { useToast } from '../../composables/useToast'
import CancelReasonModal from '../shared/CancelReasonModal.vue'

const API = import.meta.env.VITE_API_BASE_URL
const { apiFetch } = useAuth()
const { showToast } = useToast()

const props = defineProps({
  invoice: { type: Object, required: true }
})
const emit = defineEmits(['close', 'refresh'])

const hasPayments = computed(() => Number(props.invoice.paid_amount) > 0)
const canEditItems = computed(() => props.invoice.status !== 'cancelled' && props.invoice.status !== 'paid')

const statusLabel = (s) => ({ confirmed: 'مؤكدة', partially_paid: 'مدفوعة جزئيًا', paid: 'مدفوعة بالكامل', cancelled: 'ملغاة' }[s] || s)
const statusTextClass = (s) => ({
  confirmed: 'bg-blue-50 text-blue-600',
  partially_paid: 'bg-amber-50 text-amber-600',
  paid: 'bg-emerald-50 text-emerald-600',
  cancelled: 'bg-gray-50 text-gray-400',
}[s] || 'bg-gray-50 text-gray-500')

// 🆕 فتح/طباعة الفاتورة كـ PDF في تبويب جديد. رابط مباشر (بلا fetch) لأن
// الطلب GET آمن (لا يحتاج هيدر CSRF)، والمتصفح يُرفق الكوكيز httpOnly
// تلقائيًا مع أي تنقل عادي لنفس الدومين — تمامًا كأي رابط تحميل مباشر.
const openPdf = () => {
  window.open(`${API}/api/invoices/${props.invoice.id}/pdf/`, '_blank')
}

const paymentAmount = ref(null)
const paymentMethod = ref('')
const paymentLoading = ref(false)

const submitPayment = async () => {
  if (!paymentAmount.value || paymentAmount.value <= 0) {
    showToast('error', 'يرجى إدخال مبلغ صحيح')
    return
  }
  paymentLoading.value = true
  try {
    const res = await apiFetch(`/api/invoices/${props.invoice.id}/payments/`, {
      method: 'POST',
      body: JSON.stringify({
        amount: paymentAmount.value,
        payment_method: paymentMethod.value || null
      })
    })
    const data = await res.json()
    if (res.ok) {
      showToast('success', '✅ تم تسجيل الدفعة بنجاح')
      paymentAmount.value = null
      paymentMethod.value = ''
      emit('refresh')
    } else {
      showToast('error', '❌ ' + (data.detail || 'حدث خطأ'))
    }
  } catch (e) {
    showToast('error', 'تعذر الاتصال بالسيرفر')
  } finally {
    paymentLoading.value = false
  }
}

const editingPaymentId = ref(null)
const editForm = ref({ amount: 0, payment_method: '' })
const editLoading = ref(false)

const startEditPayment = (p) => {
  editingPaymentId.value = p.id
  editForm.value = { amount: Number(p.amount), payment_method: p.payment_method || '' }
}

const cancelEditPayment = () => {
  editingPaymentId.value = null
}

const saveEditPayment = async (p) => {
  if (!editForm.value.amount || editForm.value.amount <= 0) {
    showToast('error', 'يرجى إدخال مبلغ صحيح')
    return
  }
  editLoading.value = true
  try {
    const res = await apiFetch(`/api/invoices/${props.invoice.id}/payments/${p.id}/`, {
      method: 'PUT',
      body: JSON.stringify({
        amount: editForm.value.amount,
        payment_method: editForm.value.payment_method || null
      })
    })
    const data = await res.json()
    if (res.ok) {
      showToast('success', '✅ تم تعديل الدفعة بنجاح')
      editingPaymentId.value = null
      emit('refresh')
    } else {
      showToast('error', '❌ ' + (data.detail || 'تعذر تعديل الدفعة'))
    }
  } catch (e) {
    showToast('error', 'تعذر الاتصال بالسيرفر')
  } finally {
    editLoading.value = false
  }
}

// 🆕 حذف دفعة
const pendingDeletePayment = ref(null)
const askDeletePayment = (p) => { pendingDeletePayment.value = p }

const confirmDeletePayment = async () => {
  if (!pendingDeletePayment.value) return
  editLoading.value = true
  try {
    const res = await apiFetch(`/api/invoices/${props.invoice.id}/payments/${pendingDeletePayment.value.id}/`, {
      method: 'DELETE'
    })
    const data = await res.json()
    if (res.ok) {
      showToast('success', '✅ تم حذف الدفعة بنجاح')
      pendingDeletePayment.value = null
      emit('refresh')
    } else {
      showToast('error', '❌ ' + (data.detail || 'تعذر حذف الدفعة'))
    }
  } catch (e) {
    showToast('error', 'تعذر الاتصال بالسيرفر')
  } finally {
    editLoading.value = false
  }
}

const editingItemId = ref(null)
const itemEditForm = ref({ unit_price: 0 })
const itemEditLoading = ref(false)

const startEditItem = (item) => {
  editingItemId.value = item.id
  itemEditForm.value = { unit_price: Number(item.unit_price) }
}

const cancelEditItem = () => {
  editingItemId.value = null
}

const saveEditItem = async (item) => {
  if (!itemEditForm.value.unit_price || itemEditForm.value.unit_price <= 0) {
    showToast('error', 'يرجى إدخال سعر صحيح')
    return
  }
  itemEditLoading.value = true
  try {
    const res = await apiFetch(`/api/invoices/${props.invoice.id}/items/${item.id}/`, {
      method: 'PUT',
      body: JSON.stringify({ unit_price: itemEditForm.value.unit_price })
    })
    const data = await res.json()
    if (res.ok) {
      showToast('success', '✅ تم تعديل سعر البند بنجاح')
      editingItemId.value = null
      emit('refresh')
    } else {
      showToast('error', '❌ ' + (data.detail || 'تعذر تعديل البند'))
    }
  } catch (e) {
    showToast('error', 'تعذر الاتصال بالسيرفر')
  } finally {
    itemEditLoading.value = false
  }
}

// 🆕 حذف بند
const pendingDeleteItem = ref(null)
const isLastItem = computed(() => {
  if (!pendingDeleteItem.value) return false
  return (props.invoice.items?.length || 0) <= 1
})
// 🆕 يُحذف كامل الفاتورة فعليًا فقط عندما يكون هذا آخر بند ولا توجد أي مدفوعات
const willFullyDeleteInvoice = computed(() => isLastItem.value && Number(props.invoice.paid_amount) <= 0)

const askDeleteItem = (item) => { pendingDeleteItem.value = item }

const confirmDeleteItem = async () => {
  if (!pendingDeleteItem.value) return
  itemEditLoading.value = true
  try {
    const params = isLastItem.value ? '?confirm=true' : ''
    const res = await apiFetch(`/api/invoices/${props.invoice.id}/items/${pendingDeleteItem.value.id}/${params}`, {
      method: 'DELETE'
    })
    const data = await res.json()
    if (res.ok) {
      pendingDeleteItem.value = null
      if (data.deleted) {
        // 🆕 الفاتورة حُذفت بالكامل من قاعدة البيانات — لا معنى لبقاء
        // المودال مفتوحًا على فاتورة لم تعد موجودة، فنُغلقه مباشرة
        showToast('success', '✅ ' + (data.message || 'تم حذف الفاتورة بالكامل بنجاح'))
        emit('refresh')
        emit('close')
      } else {
        showToast('success', '✅ تم حذف البند بنجاح')
        emit('refresh')
      }
    } else {
      showToast('error', '❌ ' + (data.detail || 'تعذر حذف البند'))
    }
  } catch (e) {
    showToast('error', 'تعذر الاتصال بالسيرفر')
  } finally {
    itemEditLoading.value = false
  }
}

const showCancelModal = ref(false)
const cancelLoading = ref(false)

const confirmCancel = async (payload) => {
  cancelLoading.value = true
  try {
    const res = await apiFetch(`/api/invoices/${props.invoice.id}/cancel/`, {
      method: 'POST',
      body: JSON.stringify({
        reason: payload.reason,
        confirm_no_reason: payload.confirm_no_reason,
        confirm_refund: payload.confirm_extra || false,
      })
    })
    const data = await res.json()
    if (res.ok) {
      showCancelModal.value = false
      showToast('success', '✅ تم إلغاء الفاتورة بنجاح')
      emit('refresh')
    } else {
      showToast('error', '❌ ' + (data.detail || 'تعذر إلغاء الفاتورة'))
    }
  } catch (e) {
    showToast('error', 'تعذر الاتصال بالسيرفر')
  } finally {
    cancelLoading.value = false
  }
}
</script>