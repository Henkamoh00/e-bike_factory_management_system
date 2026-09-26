<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-2xl font-bold">كشف حساب عميل</h2>
    </div>

    <div class="bg-white rounded-2xl shadow p-5 mb-6">
      <SearchableSelect
        v-model="selectedCustomerId"
        :async-search="searchCustomers"
        label="بحث سريع عن عميل"
        placeholder="ابحث عن عميل..."
        :allow-empty="false"
      />
    </div>

    <div v-if="quickLoading" class="text-center py-16 text-gray-400 text-lg">جاري التحميل...</div>

    <div v-else-if="quickStatement" class="mb-10">
      <div class="flex items-center justify-end gap-2 mb-4">
        <span class="text-xs text-gray-400">{{ quickStatement.invoices.length }} فاتورة نشطة</span>
        <button
          @click="openNewInvoice(quickStatement)"
          class="bg-emerald-600 hover:bg-emerald-700 text-white px-5 py-2.5 rounded-2xl font-medium text-sm"
        >
          + فاتورة جديدة
        </button>
      </div>

      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div class="bg-white rounded-2xl shadow p-6 text-center">
          <div class="text-sm text-gray-400 mb-1">إجمالي الفواتير</div>
          <div class="text-2xl font-bold text-gray-800">{{ Number(quickStatement.total_invoiced).toFixed(2) }}</div>
        </div>
        <div class="bg-white rounded-2xl shadow p-6 text-center">
          <div class="text-sm text-gray-400 mb-1">إجمالي المدفوع</div>
          <div class="text-2xl font-bold text-emerald-600">{{ Number(quickStatement.total_paid).toFixed(2) }}</div>
        </div>
        <div class="bg-white rounded-2xl shadow p-6 text-center">
          <div class="text-sm text-gray-400 mb-1">المتبقي (الدين)</div>
          <div class="text-2xl font-bold" :class="Number(quickStatement.total_remaining) > 0 ? 'text-red-600' : 'text-gray-400'">
            {{ Number(quickStatement.total_remaining).toFixed(2) }}
          </div>
        </div>
        <div class="bg-white rounded-2xl shadow p-6 text-center">
          <div class="text-sm text-gray-400 mb-1">رصيد العميل</div>
          <div class="text-2xl font-bold" :class="Number(quickStatement.credit_balance) > 0 ? 'text-indigo-600' : 'text-gray-400'">
            {{ Number(quickStatement.credit_balance).toFixed(2) }}
          </div>
        </div>
      </div>

      <div class="bg-white rounded-3xl shadow-xl p-6 mb-6">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-bold text-gray-700">💰 رصيد العميل ومصادره</h3>
          <button
            @click="openDeposit(quickStatement)"
            class="text-xs bg-emerald-50 hover:bg-emerald-100 text-emerald-700 px-3 py-1.5 rounded-full font-medium"
          >
            + إيداع رصيد
          </button>
        </div>

        <div v-if="Number(quickStatement.credit_balance) > 0" class="bg-indigo-50 rounded-2xl p-4 flex items-center justify-between gap-3 flex-wrap mb-4">
          <div>
            <div class="text-xs text-indigo-500 mb-1">الرصيد المتاح حاليًا</div>
            <div class="text-xl font-bold text-indigo-700">{{ Number(quickStatement.credit_balance).toFixed(2) }}</div>
          </div>
          <div class="flex items-center gap-2">
            <button
              @click="openReallocate(quickStatement)"
              class="text-xs bg-white hover:bg-indigo-100 text-indigo-600 px-3 py-2 rounded-full font-medium border border-indigo-200"
            >
              🧾 تسديد فاتورة
            </button>
            <button
              @click="openRefund(quickStatement)"
              class="text-xs bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-2 rounded-full font-medium"
            >
              ✅ استرجاع نقدي
            </button>
          </div>
        </div>

        <div v-if="quickLedgerPg.paginatedItems.value.length" class="space-y-1.5">
          <div
            v-for="entry in quickLedgerPg.paginatedItems.value"
            :key="entry.id"
            class="flex items-center justify-between gap-3 px-3 py-2 bg-gray-50 rounded-xl text-xs"
          >
            <div class="min-w-0">
              <span class="font-medium" :class="Number(entry.amount) >= 0 ? 'text-emerald-600' : 'text-red-500'">
                {{ Number(entry.amount) >= 0 ? '+' : '' }}{{ Number(entry.amount).toFixed(2) }}
              </span>
              <span class="text-gray-400 mr-2">{{ creditActionLabel(entry.action_type) }}</span>
              <span v-if="entry.related_invoice_number" class="text-gray-400">— {{ entry.related_invoice_number }}</span>
              <div v-if="entry.notes" class="text-gray-400 mt-0.5 truncate">{{ entry.notes }}</div>
            </div>
            <span class="text-gray-400 shrink-0">{{ new Date(entry.created_at).toLocaleDateString('ar-EG') }}</span>
          </div>

          <PaginationControls
            :page="quickLedgerPg.page.value"
            :total-pages="quickLedgerPg.totalPages.value"
            @prev="quickLedgerPg.prevPage"
            @next="quickLedgerPg.nextPage"
          />
        </div>
        <div v-else class="text-center py-6 text-gray-400 text-xs bg-gray-50 rounded-2xl">
          لا توجد حركات على الرصيد بعد
        </div>
      </div>

      <div class="bg-white rounded-3xl shadow-xl overflow-hidden">
        <div v-if="quickStatement.invoices.length === 0" class="text-center py-16 text-gray-400 text-lg">
          لا توجد فواتير لهذا العميل
        </div>

        <div v-else class="divide-y divide-gray-100">
          <div
            v-for="inv in quickStatement.invoices"
            :key="inv.id"
            @click="openInvoiceDetail(inv)"
            class="flex items-center justify-between gap-4 px-5 py-3 hover:bg-gray-50 transition cursor-pointer"
          >
            <div class="flex items-center gap-3 min-w-0 flex-1">
              <div class="w-9 h-9 rounded-full flex items-center justify-center text-base shrink-0" :class="statusBadgeClass(inv.status)">
                {{ statusIcon(inv.status) }}
              </div>
              <div class="min-w-0">
                <span class="font-mono font-bold text-gray-800">{{ inv.invoice_number }}</span>
                <div class="text-xs text-gray-400">{{ new Date(inv.invoice_date).toLocaleDateString('ar-EG') }}</div>
              </div>
            </div>

            <div class="text-left shrink-0">
              <div class="font-bold text-gray-800">{{ Number(inv.total_amount).toFixed(2) }}</div>
              <div v-if="Number(inv.remaining_amount) > 0" class="text-xs text-red-500">
                متبقي: {{ Number(inv.remaining_amount).toFixed(2) }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="border-t border-gray-100 pt-6">
      <div class="flex justify-between items-center mb-4">
        <h3 class="text-lg font-bold text-gray-700">كل العملاء</h3>
        <input
          v-model="pg.search.value"
          type="text"
          placeholder="بحث باسم العميل..."
          class="px-4 py-2 border-2 border-gray-200 rounded-xl focus:border-indigo-400 focus:outline-none text-sm"
        />
      </div>

      <div class="bg-white rounded-3xl shadow-xl overflow-hidden">
        <div v-if="pg.loading.value" class="text-center py-16 text-gray-400 text-lg">جاري التحميل...</div>
        <div v-else-if="pg.items.value.length === 0" class="text-center py-16 text-gray-400 text-lg">لا يوجد عملاء</div>

        <div v-else class="divide-y divide-gray-100">
          <div
            v-for="customer in pg.items.value"
            :key="customer.id"
            @click="openCard(customer)"
            class="flex items-center justify-between gap-4 px-5 py-3 hover:bg-gray-50 transition cursor-pointer"
          >
            <div class="flex items-center gap-3 min-w-0">
              <div class="w-9 h-9 rounded-full bg-purple-100 text-purple-700 flex items-center justify-center font-bold text-sm shrink-0">
                {{ customer.name.charAt(0) }}
              </div>
              <div class="min-w-0">
                <div class="font-bold text-gray-800 truncate">{{ customer.name }}</div>
                <div v-if="customer.phone" class="text-xs text-gray-400">{{ customer.phone }}</div>
              </div>
            </div>
            <span class="text-xs text-indigo-600 shrink-0">عرض كشف الحساب ←</span>
          </div>
        </div>
      </div>

      <div v-if="pg.totalPages.value > 1" class="flex justify-center items-center gap-3 mt-6">
        <button @click="pg.prevPage" :disabled="pg.page.value === 1" class="px-4 py-2 rounded-xl bg-white shadow disabled:opacity-40 text-sm">السابق</button>
        <span class="text-sm text-gray-500">صفحة {{ pg.page.value }} من {{ pg.totalPages.value }} ({{ pg.total.value }} عميل)</span>
        <button @click="pg.nextPage" :disabled="pg.page.value === pg.totalPages.value" class="px-4 py-2 rounded-xl bg-white shadow disabled:opacity-40 text-sm">التالي</button>
      </div>
    </div>

    <!--لا يُغلق كشف الحساب المنبثق تلقائيًا عند فتح فاتورة/فاتورة جديدة من داخله؛
         يبقى مفتوحًا خلفها، وإغلاق نافذة الفاتورة يُعيد المستخدم إليه تلقائيًا (بمثابة زر رجوع) -->
    <CustomerStatementCardModal
      v-if="cardCustomerId"
      ref="cardModalRef"
      :customer-id="cardCustomerId"
      @close="cardCustomerId = null"
      @open-invoice="handleOpenInvoiceFromCard"
      @deposit-credit="openDeposit"
      @reallocate-credit="openReallocate"
      @refund-credit="openRefund"
      @add-invoice="openNewInvoiceFromCard"
    />

    <InvoiceDetailModal
      v-if="selectedInvoice"
      :invoice="selectedInvoice"
      @close="selectedInvoice = null"
      @refresh="handleDetailRefresh"
    />

    <CreditDepositModal
      v-if="depositTarget"
      :customer-name="depositTarget.customer_name"
      :loading="creditActionLoading"
      @close="depositTarget = null"
      @confirm="submitDeposit"
    />

    <CreditRefundModal
      v-if="refundTarget"
      :customer-name="refundTarget.customer_name"
      :credit-balance="refundTarget.credit_balance"
      :loading="creditActionLoading"
      @close="refundTarget = null"
      @confirm="submitRefund"
    />

    <CreditReallocateModal
      v-if="reallocateTarget"
      :customer-id="reallocateTarget.customer_id"
      :customer-name="reallocateTarget.customer_name"
      :credit-balance="reallocateTarget.credit_balance"
      @close="reallocateTarget = null"
      @success="handleReallocateSuccess"
    />

    <!-- إنشاء فاتورة مباشرة لعميل مُحدَّد -->
    <InvoiceFormModal
      v-if="newInvoiceTarget"
      :preset-customer-id="newInvoiceTarget.customer_id"
      :preset-customer-name="newInvoiceTarget.customer_name"
      @close="newInvoiceTarget = null"
      @success="handleNewInvoiceSuccess"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useAuth } from '../../composables/useAuth'
import { useServerPagination } from '../../composables/useServerPagination'
import { usePagination } from '../../composables/usePagination'
import { useToast } from '../../composables/useToast'
import SearchableSelect from '../shared/SearchableSelect.vue'
import PaginationControls from '../shared/PaginationControls.vue'
import InvoiceDetailModal from './InvoiceDetailModal.vue'
import InvoiceFormModal from './InvoiceFormModal.vue'
import CustomerStatementCardModal from './CustomerStatementCardModal.vue'
import CreditDepositModal from './CreditDepositModal.vue'
import CreditRefundModal from './CreditRefundModal.vue'
import CreditReallocateModal from './CreditReallocateModal.vue'

const { apiFetch } = useAuth()
const { showToast } = useToast()

const selectedCustomerId = ref('')
const quickStatement = ref(null)
const quickLoading = ref(false)

const creditActionLabels = {
  deposit: 'إيداع يدوي',
  manual_adjust: 'تعديل يدوي',
  from_cancel: 'فائض من إلغاء فاتورة',
  from_return: 'فائض من إرجاع دراجة',
  from_adjustment: 'فائض من تعديل الفاتورة',
  used_on_invoice: 'تسديد فاتورة',
  deposit_excess_payment: 'فائض دفعة نقدية',
  refunded: 'استرجاع نقدي',
  reallocated: 'تسديد فاتورة',
}
const creditActionLabel = (t) => creditActionLabels[t] || t

// باجينيشن (10 بكل صفحة) لسجل حركات الرصيد في قسم "البحث السريع"
const quickLedgerItems = computed(() => quickStatement.value?.credit_ledger || [])
const quickLedgerPg = usePagination(quickLedgerItems, 10)

const searchCustomers = async (query) => {
  const params = new URLSearchParams({ limit: 20 })
  if (query) params.set('q', query)
  const res = await apiFetch(`/api/customers/simple/?${params.toString()}`)
  if (!res.ok) return []
  const data = await res.json()
  return data.map(c => ({ label: c.name, value: c.id }))
}

const loadQuickStatement = async () => {
  if (!selectedCustomerId.value) {
    quickStatement.value = null
    return
  }
  quickLoading.value = true
  try {
    const res = await apiFetch(`/api/invoices/customers/${selectedCustomerId.value}/statement/`)
    quickStatement.value = res.ok ? await res.json() : null
  } catch (e) {
    console.error('كشف حساب العميل', e)
    quickStatement.value = null
  } finally {
    quickLoading.value = false
  }
}

watch(selectedCustomerId, loadQuickStatement)

const statusIcon = (s) => ({ confirmed: '📄', partially_paid: '🟡', paid: '✅', cancelled: '✖️' }[s] || '📄')
const statusBadgeClass = (s) => ({
  confirmed: 'bg-blue-100 text-blue-700',
  partially_paid: 'bg-amber-100 text-amber-700',
  paid: 'bg-emerald-100 text-emerald-700',
  cancelled: 'bg-gray-100 text-gray-400',
}[s] || 'bg-gray-100 text-gray-500')

const fetchCustomersPage = async ({ skip, limit, search }) => {
  const params = new URLSearchParams({ skip, limit })
  if (search) params.set('search', search)
  const res = await apiFetch(`/api/customers/?${params.toString()}`)
  if (!res.ok) return { items: [], total: 0 }
  return res.json()
}

const pg = useServerPagination(fetchCustomersPage, 10)

const cardCustomerId = ref(null)
const cardModalRef = ref(null)
const openCard = (customer) => { cardCustomerId.value = customer.id }

const selectedInvoice = ref(null)
const openInvoiceDetail = (inv) => { selectedInvoice.value = inv }

// لا نُغلق كشف الحساب (card) عند فتح فاتورة من داخله — يبقى بالخلفية،
// وإغلاق نافذة الفاتورة (@close="selectedInvoice = null") يُعيد المستخدم
// إليه تلقائيًا، وهذا هو "زر الرجوع" المطلوب دون الحاجة لأي زر إضافي
const handleOpenInvoiceFromCard = (inv) => {
  selectedInvoice.value = inv
}

const handleDetailRefresh = async () => {
  await loadQuickStatement()
  if (cardModalRef.value) await cardModalRef.value.reload()
  selectedInvoice.value = null
}

const depositTarget = ref(null)
const refundTarget = ref(null)
const reallocateTarget = ref(null)
const creditActionLoading = ref(false)

const openDeposit = (target) => { depositTarget.value = target }
const openRefund = (target) => { refundTarget.value = target }
const openReallocate = (target) => { reallocateTarget.value = target }

const refreshAfterCreditAction = async () => {
  await loadQuickStatement()
  if (cardModalRef.value) await cardModalRef.value.reload()
}

const submitDeposit = async ({ amount, notes }) => {
  if (!depositTarget.value) return
  creditActionLoading.value = true
  try {
    const res = await apiFetch(`/api/invoices/customers/${depositTarget.value.customer_id}/credit/deposit/`, {
      method: 'POST',
      body: JSON.stringify({ amount, notes })
    })
    const data = await res.json()
    if (res.ok) {
      showToast('success', '✅ تم إيداع الرصيد بنجاح')
      depositTarget.value = null
      await refreshAfterCreditAction()
    } else {
      showToast('error', '❌ ' + (data.detail || 'تعذر إيداع الرصيد'))
    }
  } catch (e) {
    showToast('error', 'تعذر الاتصال بالسيرفر')
  } finally {
    creditActionLoading.value = false
  }
}

const submitRefund = async (amount) => {
  if (!refundTarget.value) return
  creditActionLoading.value = true
  try {
    const res = await apiFetch(`/api/invoices/customers/${refundTarget.value.customer_id}/credit/refund/`, {
      method: 'POST',
      body: JSON.stringify({ amount })
    })
    const data = await res.json()
    if (res.ok) {
      showToast('success', '✅ تم تسجيل الاسترجاع النقدي بنجاح')
      refundTarget.value = null
      await refreshAfterCreditAction()
    } else {
      showToast('error', '❌ ' + (data.detail || 'تعذر تسجيل الاسترجاع'))
    }
  } catch (e) {
    showToast('error', 'تعذر الاتصال بالسيرفر')
  } finally {
    creditActionLoading.value = false
  }
}

const handleReallocateSuccess = async () => {
  reallocateTarget.value = null
  await refreshAfterCreditAction()
}

// فاتورة جديدة مباشرة لعميل مُحدَّد
const newInvoiceTarget = ref(null)

const openNewInvoice = (stmt) => {
  newInvoiceTarget.value = { customer_id: stmt.customer_id, customer_name: stmt.customer_name }
}
// لا نُغلق كشف الحساب (card) عند فتح فاتورة جديدة من داخله — نفس منطق
// handleOpenInvoiceFromCard أعلاه، لإتاحة الرجوع التلقائي إليه بعد الإغلاق
const openNewInvoiceFromCard = (stmt) => {
  newInvoiceTarget.value = { customer_id: stmt.customer_id, customer_name: stmt.customer_name }
}
const handleNewInvoiceSuccess = async () => {
  newInvoiceTarget.value = null
  await loadQuickStatement()
  if (cardModalRef.value) await cardModalRef.value.reload()
  pg.load()
}

onMounted(() => {
  pg.load()
})
</script>