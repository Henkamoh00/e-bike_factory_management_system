<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-2xl font-bold">قائمة الفواتير</h2>
      <button @click="showInvoiceModal = true" class="bg-emerald-600 hover:bg-emerald-700 text-white px-6 py-3 rounded-2xl font-medium">
        + فاتورة جديدة
      </button>
    </div>

    <div class="bg-white rounded-2xl shadow p-5 mb-6 flex flex-wrap gap-4 items-end">
      <div>
        <label class="block text-sm text-gray-500 mb-1">بحث برقم الفاتورة</label>
        <input
          v-model="filters.search"
          type="text"
          placeholder="INV-2026-..."
          class="px-4 py-2 border-2 border-gray-200 rounded-xl focus:border-emerald-400 focus:outline-none font-mono"
        />
      </div>
      <div>
        <SearchableSelect v-model="filters.customer_name" :async-search="searchCustomers" label="تصفية بالعميل" empty-label="كل العملاء" />
      </div>
      <div>
        <SearchableSelect v-model="filters.status" :options="statusOptions" label="تصفية بالحالة" empty-label="كل الحالات" />
      </div>
      <button @click="resetFilter" class="px-4 py-2 text-gray-500 hover:text-gray-700 underline text-sm">إعادة تعيين</button>
    </div>

    <div class="bg-white rounded-3xl shadow-xl overflow-hidden">
      <div v-if="pg.loading.value" class="text-center py-16 text-gray-400 text-lg">جاري التحميل...</div>
      <div v-else-if="pg.items.value.length === 0" class="text-center py-16 text-gray-400 text-lg">لا توجد فواتير مطابقة</div>

      <div v-else class="divide-y divide-gray-100">
        <div
          v-for="inv in pg.items.value"
          :key="inv.id"
          @click="openDetail(inv)"
          class="flex items-center justify-between gap-4 px-5 py-3 hover:bg-gray-50 transition cursor-pointer"
          :class="{ 'opacity-50': inv.status === 'cancelled' }"
        >
          <div class="flex items-center gap-3 min-w-0 flex-1">
            <div
              class="w-9 h-9 rounded-full flex items-center justify-center text-base shrink-0"
              :class="statusBadgeClass(inv.status)"
            >
              {{ statusIcon(inv.status) }}
            </div>
            <div class="min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="font-mono font-bold text-gray-800">{{ inv.invoice_number }}</span>
                <span class="text-xs px-2 py-0.5 rounded-full" :class="statusTextClass(inv.status)">{{ statusLabel(inv.status) }}</span>
              </div>
              <div class="text-xs text-gray-500 truncate">{{ inv.customer_name }} — {{ inv.items?.length || 0 }} صنف</div>
            </div>
          </div>

          <div class="text-left shrink-0">
            <div class="font-bold text-gray-800">{{ Number(inv.total_amount).toFixed(2) }}</div>
            <div v-if="Number(inv.remaining_amount) > 0 && inv.status !== 'cancelled'" class="text-xs text-red-500">
              متبقي: {{ Number(inv.remaining_amount).toFixed(2) }}
            </div>
            <div class="text-xs text-gray-400">{{ new Date(inv.invoice_date).toLocaleDateString('ar-EG') }}</div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="pg.totalPages.value > 1" class="flex justify-center items-center gap-3 mt-6">
      <button @click="pg.prevPage" :disabled="pg.page.value === 1" class="px-4 py-2 rounded-xl bg-white shadow disabled:opacity-40 text-sm">السابق</button>
      <span class="text-sm text-gray-500">صفحة {{ pg.page.value }} من {{ pg.totalPages.value }} ({{ pg.total.value }} فاتورة)</span>
      <button @click="pg.nextPage" :disabled="pg.page.value === pg.totalPages.value" class="px-4 py-2 rounded-xl bg-white shadow disabled:opacity-40 text-sm">التالي</button>
    </div>

    <InvoiceFormModal
      v-if="showInvoiceModal"
      @close="showInvoiceModal = false"
      @success="handleInvoiceSuccess"
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
import InvoiceFormModal from './InvoiceFormModal.vue'
import InvoiceDetailModal from './InvoiceDetailModal.vue'

const { apiFetch } = useAuth()

const filters = ref({ customer_name: '', status: '', search: '' })

const statusOptions = [
  { label: 'مؤكدة',      value: 'confirmed' },
  { label: 'مدفوعة جزئيًا', value: 'partially_paid' },
  { label: 'مدفوعة بالكامل', value: 'paid' },
  { label: 'ملغاة',      value: 'cancelled' },
]

const searchCustomers = async (query) => {
  const params = new URLSearchParams({ limit: 20 })
  if (query) params.set('q', query)
  const res = await apiFetch(`/api/customers/simple/?${params.toString()}`)
  if (!res.ok) return []
  const data = await res.json()
  return data.map(c => ({ label: c.name, value: c.name }))
}

const fetchInvoicesPage = async ({ skip, limit }) => {
  const params = new URLSearchParams({ skip, limit })
  if (filters.value.customer_name) params.set('customer_name', filters.value.customer_name)
  if (filters.value.status) params.set('status', filters.value.status)
  if (filters.value.search) params.set('search', filters.value.search)
  const res = await apiFetch(`/api/invoices/?${params.toString()}`)
  if (!res.ok) return { items: [], total: 0 }
  return res.json()
}

const pg = useServerPagination(fetchInvoicesPage, 10)

let debounceTimer = null
watch(filters, () => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    pg.page.value = 1
    pg.load()
  }, 300)
}, { deep: true })

const resetFilter = () => { filters.value = { customer_name: '', status: '', search: '' } }

const statusIcon = (s) => ({ confirmed: '📄', partially_paid: '🟡', paid: '✅', cancelled: '✖️' }[s] || '📄')
const statusLabel = (s) => ({ confirmed: 'مؤكدة', partially_paid: 'مدفوعة جزئيًا', paid: 'مدفوعة بالكامل', cancelled: 'ملغاة' }[s] || s)
const statusBadgeClass = (s) => ({
  confirmed: 'bg-blue-100 text-blue-700',
  partially_paid: 'bg-amber-100 text-amber-700',
  paid: 'bg-emerald-100 text-emerald-700',
  cancelled: 'bg-gray-100 text-gray-400',
}[s] || 'bg-gray-100 text-gray-500')
const statusTextClass = (s) => ({
  confirmed: 'bg-blue-50 text-blue-600',
  partially_paid: 'bg-amber-50 text-amber-600',
  paid: 'bg-emerald-50 text-emerald-600',
  cancelled: 'bg-gray-50 text-gray-400',
}[s] || 'bg-gray-50 text-gray-500')

const showInvoiceModal = ref(false)
const selectedInvoice = ref(null)

const openDetail = (inv) => { selectedInvoice.value = inv }

const handleInvoiceSuccess = () => {
  showInvoiceModal.value = false
  pg.load()
}

const handleDetailRefresh = async () => {
  await pg.load()
  if (selectedInvoice.value) {
    const updated = pg.items.value.find(i => i.id === selectedInvoice.value.id)
    selectedInvoice.value = updated || null
  }
}

defineExpose({ refresh: pg.load, clearSelection: () => {} })

onMounted(() => {
  pg.load()
})
</script>