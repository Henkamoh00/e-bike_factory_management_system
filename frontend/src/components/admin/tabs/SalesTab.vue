<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-3xl font-bold">المبيعات</h2>
      <button @click="showSaleModal = true" class="bg-green-600 hover:bg-green-700 text-white px-6 py-3 rounded-2xl font-medium">
        + تسجيل بيع جديد
      </button>
    </div>

    <div class="bg-white rounded-2xl shadow p-5 mb-6 flex flex-wrap gap-4 items-end">
      <div>
        <SearchableSelect v-model="filters.customer_name" :async-search="searchCustomers" label="تصفية بالعميل" empty-label="كل العملاء" />
      </div>
      <div>
        <SearchableSelect v-model="filters.status" :options="statusOptions" label="تصفية بالحالة" empty-label="كل الحالات" />
      </div>
      <div>
        <label class="block text-sm text-gray-500 mb-1">من تاريخ</label>
        <input type="date" v-model="filters.date_from" class="px-4 py-2 border-2 border-gray-200 rounded-xl focus:border-indigo-400 focus:outline-none" />
      </div>
      <div>
        <label class="block text-sm text-gray-500 mb-1">إلى تاريخ</label>
        <input type="date" v-model="filters.date_to" class="px-4 py-2 border-2 border-gray-200 rounded-xl focus:border-indigo-400 focus:outline-none" />
      </div>
      <button @click="resetFilter" class="px-4 py-2 text-gray-500 hover:text-gray-700 underline text-sm">إعادة تعيين</button>
    </div>

    <BulkActionsBar :count="bulk.selectedCount.value" @clear="bulk.clear">
      <button
        @click="openBulkCancel"
        :disabled="bulkLoading"
        class="bg-white/20 hover:bg-white/30 text-white px-4 py-2 rounded-xl text-sm font-medium"
      >
        ❌ إلغاء المحدد ({{ bulk.selectedCount.value }})
      </button>
    </BulkActionsBar>

    <div class="bg-white rounded-3xl shadow-xl overflow-hidden">
      <div v-if="pg.loading.value" class="text-center py-16 text-gray-400 text-lg">جاري التحميل...</div>
      <div v-else-if="pg.items.value.length === 0" class="text-center py-16 text-gray-400 text-lg">لا توجد مبيعات مطابقة</div>

      <template v-else>
        <div class="flex items-center gap-3 pb-3 mb-3 px-5 py-2 bg-gray-50 border-b border-gray-100 flex-wrap">
          <input
            type="checkbox"
            :checked="bulk.pageAllSelected.value"
            :disabled="pageEligibleCount === 0"
            @change="bulk.toggleAllOnPage"
            class="w-4 h-4 accent-indigo-600 rounded disabled:opacity-30 disabled:cursor-not-allowed"
          />
          <span class="text-xs text-gray-400">تحديد الكل بهذه الصفحة ({{ pageEligibleCount }} من {{ pg.items.value.length }})</span>
        </div>

        <div class="divide-y divide-gray-100">
          <div
            v-for="sale in pg.items.value"
            :key="sale.id"
            class="flex items-center justify-between gap-4 px-5 py-3 hover:bg-gray-50 transition"
            :class="{ 'opacity-50': sale.status === 'cancelled' }"
          >
            <div class="flex items-center gap-3 min-w-0 flex-1">
              <input
                type="checkbox"
                :checked="bulk.isSelected(sale)"
                :disabled="sale.status !== 'active'"
                @change="bulk.toggleOne(sale)"
                class="w-4 h-4 accent-indigo-600 rounded shrink-0 disabled:opacity-20 disabled:cursor-not-allowed"
              />

              <div
                class="w-9 h-9 rounded-full flex items-center justify-center text-base shrink-0"
                :class="sale.status === 'cancelled' ? 'bg-gray-100 text-gray-400' : 'bg-green-100 text-green-700'"
              >
                {{ sale.status === 'cancelled' ? '✖️' : '💰' }}
              </div>
              <div class="min-w-0">
                <div class="flex items-center gap-2 flex-wrap">
                  <span class="font-mono font-bold" :class="sale.status === 'cancelled' ? 'text-gray-400 line-through' : 'text-gray-800'">
                    {{ sale.chassis_number }}
                  </span>
                  <span v-if="sale.status === 'cancelled'" class="text-xs bg-red-50 text-red-600 rounded-full px-2 py-0.5 font-medium">ملغى</span>
                </div>
                <div class="text-xs text-gray-500 truncate">{{ sale.customer_name }}</div>
                <div v-if="sale.status === 'cancelled' && sale.cancel_reason" class="text-xs text-red-400 mt-0.5">
                  السبب: {{ sale.cancel_reason }}
                </div>
              </div>
            </div>

            <div class="text-left shrink-0 flex items-center gap-3">
              <div>
                <div class="text-xs text-gray-400">{{ new Date(sale.sale_date).toLocaleDateString('ar-EG') }}</div>
                <div v-if="sale.notes" class="text-xs text-gray-400 truncate max-w-[140px]">{{ sale.notes }}</div>
              </div>
              <button
                v-if="sale.status === 'active'"
                @click="openCancelSale(sale)"
                class="text-xs bg-red-50 hover:bg-red-100 text-red-600 px-3 py-1.5 rounded-full font-medium"
              >
                إلغاء البيع
              </button>
            </div>
          </div>
        </div>
      </template>
    </div>

    <div v-if="pg.totalPages.value > 1" class="flex justify-center items-center gap-3 mt-6">
      <button @click="pg.prevPage" :disabled="pg.page.value === 1" class="px-4 py-2 rounded-xl bg-white shadow disabled:opacity-40 text-sm">السابق</button>
      <span class="text-sm text-gray-500">صفحة {{ pg.page.value }} من {{ pg.totalPages.value }} ({{ pg.total.value }} عملية)</span>
      <button @click="pg.nextPage" :disabled="pg.page.value === pg.totalPages.value" class="px-4 py-2 rounded-xl bg-white shadow disabled:opacity-40 text-sm">التالي</button>
    </div>

    <CancelReasonModal
      v-if="showBulkCancelModal"
      title="إلغاء عمليات البيع المحددة"
      :subtitle="`سيتم إلغاء ${bulk.selectedCount.value} عملية بيع نشطة`"
      icon="💰"
      :loading="bulkLoading"
      @close="showBulkCancelModal = false"
      @confirm="confirmBulkCancel"
    />

    <CancelReasonModal
      v-if="cancellingSale"
      title="إلغاء عملية البيع"
      :subtitle="`الهيكل: ${cancellingSale.chassis_number} — العميل: ${cancellingSale.customer_name}`"
      icon="💰"
      :loading="cancelLoading"
      @close="cancellingSale = null"
      @confirm="confirmCancelSale"
    />

    <SaleModal
      v-if="showSaleModal"
      :chassis-list="availableChassisList"
      @close="showSaleModal = false"
      @success="handleSaleSuccess"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useAuth } from '../../../composables/useAuth'
import { useServerPagination } from '../../../composables/useServerPagination'
import SearchableSelect from '../../shared/SearchableSelect.vue'
import BulkActionsBar from '../../shared/BulkActionsBar.vue'
import CancelReasonModal from '../../shared/CancelReasonModal.vue'
import SaleModal from '../modals/SaleModal.vue'
import { useBulkSelection } from '../../../composables/useBulkSelection'

const { apiFetch } = useAuth()

const filters = ref({ customer_name: '', status: '', date_from: '', date_to: '' })

const statusOptions = [
  { label: 'نشط', value: 'active' },
  { label: 'ملغى', value: 'cancelled' },
]

const searchCustomers = async (query) => {
  const params = new URLSearchParams({ limit: 20 })
  if (query) params.set('q', query)
  const res = await apiFetch(`/api/customers/simple/?${params.toString()}`)
  if (!res.ok) return []
  const data = await res.json()
  return data.map(c => ({ label: c.name, value: c.name }))
}

const fetchSalesPage = async ({ skip, limit }) => {
  const params = new URLSearchParams({ skip, limit })
  if (filters.value.customer_name) params.set('customer_name', filters.value.customer_name)
  if (filters.value.status) params.set('status', filters.value.status)
  if (filters.value.date_from) params.set('date_from', filters.value.date_from)
  if (filters.value.date_to) params.set('date_to', filters.value.date_to)
  const res = await apiFetch(`/api/sales/?${params.toString()}`)
  if (!res.ok) return { items: [], total: 0 }
  return res.json()
}

const pg = useServerPagination(fetchSalesPage, 10)

watch(filters, () => {
  pg.page.value = 1
  pg.load()
}, { deep: true })

const resetFilter = () => { filters.value = { customer_name: '', status: '', date_from: '', date_to: '' } }

const bulk = useBulkSelection(pg.items, pg.items, 'id', (sale) => sale.status === 'active')
watch(pg.items, () => { bulk.clear() })

const pageEligibleCount = computed(() => pg.items.value.filter(s => s.status === 'active').length)

const showBulkCancelModal = ref(false)
const bulkLoading = ref(false)

const openBulkCancel = () => {
  if (bulk.selectedCount.value === 0) {
    alert('لا توجد عمليات بيع نشطة ضمن التحديد الحالي')
    return
  }
  showBulkCancelModal.value = true
}

const confirmBulkCancel = async (payload) => {
  bulkLoading.value = true
  try {
    const ids = bulk.selectedIdsArray.value
    const res = await apiFetch(`/api/sales/bulk-cancel/`, {
      method: 'POST',
      body: JSON.stringify({ ids, ...payload })
    })
    const data = await res.json()

    if (res.ok) {
      showBulkCancelModal.value = false
      bulk.clear()
      pg.load()
    } else {
      alert('❌ ' + (data.detail || 'تعذر تنفيذ الإلغاء الجماعي'))
    }
  } catch (e) {
    alert('تعذر الاتصال بالسيرفر')
  } finally {
    bulkLoading.value = false
  }
}

const cancellingSale = ref(null)
const cancelLoading = ref(false)
const openCancelSale = (sale) => { cancellingSale.value = sale }

const confirmCancelSale = async (payload) => {
  if (!cancellingSale.value) return
  cancelLoading.value = true
  try {
    const res = await apiFetch(`/api/sales/${cancellingSale.value.id}/cancel/`, {
      method: 'POST',
      body: JSON.stringify(payload)
    })
    const data = await res.json()
    if (res.ok) {
      cancellingSale.value = null
      pg.load()
      loadAvailableChassis()
    } else {
      alert('❌ ' + (data.detail || 'تعذر إلغاء عملية البيع'))
    }
  } catch (e) {
    alert('تعذر الاتصال بالسيرفر')
  } finally {
    cancelLoading.value = false
  }
}

const showSaleModal = ref(false)
const availableChassisList = ref([])

const loadAvailableChassis = async () => {
  try {
    const res = await apiFetch(`/api/chassis/available/`)
    if (res.ok) availableChassisList.value = await res.json()
  } catch (e) { console.error('هياكل متاحة', e) }
}

const handleSaleSuccess = () => {
  showSaleModal.value = false
  pg.load()
  loadAvailableChassis()
}

defineExpose({ clearSelection: bulk.clear, refresh: pg.load })

onMounted(() => {
  pg.load()
  loadAvailableChassis()
})
</script>