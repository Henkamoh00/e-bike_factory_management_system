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
        <!-- 🆕 كارد المبلغ القابل للاسترجاع -->
        <div class="bg-white rounded-2xl shadow p-6 text-center">
          <div class="text-sm text-gray-400 mb-1">قابل للاسترجاع</div>
          <div class="text-2xl font-bold" :class="Number(quickStatement.total_pending_refund) > 0 ? 'text-amber-600' : 'text-gray-400'">
            {{ Number(quickStatement.total_pending_refund).toFixed(2) }}
          </div>
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

    <CustomerStatementCardModal
      v-if="cardCustomerId"
      :customer-id="cardCustomerId"
      @close="cardCustomerId = null"
      @open-invoice="handleOpenInvoiceFromCard"
    />

    <InvoiceDetailModal
      v-if="selectedInvoice"
      :invoice="selectedInvoice"
      @close="selectedInvoice = null"
      @refresh="handleDetailRefresh"
    />
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useAuth } from '../../composables/useAuth'
import { useServerPagination } from '../../composables/useServerPagination'
import SearchableSelect from '../shared/SearchableSelect.vue'
import InvoiceDetailModal from './InvoiceDetailModal.vue'
import CustomerStatementCardModal from './CustomerStatementCardModal.vue'

const { apiFetch } = useAuth()

const selectedCustomerId = ref('')
const quickStatement = ref(null)
const quickLoading = ref(false)

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
const openCard = (customer) => { cardCustomerId.value = customer.id }

const selectedInvoice = ref(null)
const openInvoiceDetail = (inv) => { selectedInvoice.value = inv }
const handleOpenInvoiceFromCard = (inv) => {
  cardCustomerId.value = null
  selectedInvoice.value = inv
}

const handleDetailRefresh = async () => {
  await loadQuickStatement()
  selectedInvoice.value = null
}

onMounted(() => {
  pg.load()
})
</script>