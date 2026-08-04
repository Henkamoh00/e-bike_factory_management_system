<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-3xl font-bold">الأعطال</h2>
      <button @click="showFaultModal = true" class="bg-red-600 hover:bg-red-700 text-white px-6 py-3 rounded-2xl font-medium">
        + تسجيل عطل جديد
      </button>
    </div>

    <div class="bg-white rounded-2xl shadow p-5 mb-6 flex flex-wrap gap-4 items-end">
      <div>
        <label class="block text-sm text-gray-500 mb-1">بحث برقم الهيكل</label>
        <input
          v-model="filters.chassis_number"
          type="text"
          placeholder="EB-2026-..."
          class="px-4 py-2 border-2 border-gray-200 rounded-xl focus:border-indigo-400 focus:outline-none font-mono"
        />
      </div>
      <div>
        <SearchableSelect v-model="filters.status" :options="statusOptions" label="تصفية بالحالة" empty-label="كل الحالات" />
      </div>
      <div>
        <SearchableSelect v-model="filters.repaired_by" :async-search="searchWorkers" label="تصفية بالعامل (المصلّح)" empty-label="كل العمال" />
      </div>
      <div>
        <SearchableSelect v-model="filters.responsible_worker" :async-search="searchWorkers" label="تصفية بالعامل المتسبب في العطل" empty-label="كل العمال" />
      </div>
      <button @click="resetFilter" class="px-4 py-2 text-gray-500 hover:text-gray-700 underline text-sm">إعادة تعيين</button>
    </div>

    <BulkActionsBar :count="bulk.selectedCount.value" @clear="bulk.clear">
      <button
        @click="openBulkRepair"
        :disabled="bulkLoading"
        class="bg-white/20 hover:bg-white/30 text-white px-4 py-2 rounded-xl text-sm font-medium"
      >
        ✅ تصليح المحدد ({{ bulk.selectedCount.value }})
      </button>
      <button
        @click="openBulkCancel"
        :disabled="bulkLoading"
        class="bg-white/20 hover:bg-white/30 text-white px-4 py-2 rounded-xl text-sm font-medium"
      >
        ❌ إلغاء المحدد ({{ bulk.selectedCount.value }})
      </button>
    </BulkActionsBar>

    <div class="bg-white rounded-3xl shadow-xl p-6">
      <div v-if="pg.loading.value" class="text-center py-16 text-gray-400 text-lg">جاري التحميل...</div>
      <div v-else-if="pg.items.value.length === 0" class="text-center py-16 text-gray-400 text-lg">لا توجد أعطال مطابقة</div>

      <template v-else>
        <div class="flex items-center gap-3 pb-3 mb-3 border-b border-gray-100 flex-wrap">
          <input
            type="checkbox"
            :checked="bulk.pageAllSelected.value"
            :disabled="pageEligibleCount === 0"
            @change="bulk.toggleAllOnPage"
            class="w-4 h-4 accent-indigo-600 rounded disabled:opacity-30 disabled:cursor-not-allowed"
          />
          <span class="text-xs text-gray-400">
            تحديد الكل بهذه الصفحة ({{ pageEligibleCount }} معلق قابل للتحديد)
          </span>
        </div>

        <div class="divide-y divide-gray-100">
          <div v-for="fault in pg.items.value" :key="fault.id" class="py-3" :class="{ 'opacity-50': fault.status === 'cancelled' }">
            <div class="flex items-center justify-between gap-4 hover:bg-gray-50 transition px-2 -mx-2 rounded-xl py-1">
              <div class="flex items-center gap-3 min-w-0 flex-1">
                <input
                  type="checkbox"
                  :checked="bulk.isSelected(fault)"
                  :disabled="fault.status !== 'pending'"
                  @change="bulk.toggleOne(fault)"
                  class="w-4 h-4 accent-indigo-600 rounded shrink-0 disabled:opacity-20 disabled:cursor-not-allowed"
                />

                <div @click="toggleExpand(fault.id)" class="flex items-center gap-3 min-w-0 cursor-pointer flex-1">
                  <span class="text-lg shrink-0">{{ statusIcon(fault.status) }}</span>
                  <div class="min-w-0">
                    <div class="flex items-center gap-2 flex-wrap">
                      <span class="font-mono font-bold" :class="fault.status === 'cancelled' ? 'text-gray-400 line-through' : 'text-gray-800'">
                        {{ fault.chassis_number }}
                      </span>
                      <span v-if="fault.related_stage" class="text-xs text-gray-500">{{ getStageName(fault.related_stage) }}</span>
                      <span v-if="fault.responsible_worker_name" class="text-xs text-gray-400">— بواسطة {{ fault.responsible_worker_name }}</span>
                      <span v-if="fault.status === 'cancelled'" class="text-xs bg-gray-100 text-gray-500 rounded-full px-2 py-0.5 font-medium">
                        ملغى
                      </span>
                    </div>
                    <div class="text-sm text-gray-600 truncate max-w-md">{{ fault.description }}</div>
                    <div v-if="fault.status === 'cancelled' && fault.cancel_reason" class="text-xs text-gray-400 mt-0.5">
                      سبب الإلغاء: {{ fault.cancel_reason }}
                    </div>
                  </div>
                </div>
              </div>

              <div class="text-left shrink-0 flex items-center gap-3">
                <span :class="statusTextClass(fault.status)" class="text-xs font-medium">{{ statusLabel(fault.status) }}</span>
                <span class="text-xs text-gray-400">{{ new Date(fault.reported_date).toLocaleDateString('ar-EG') }}</span>

                <template v-if="fault.status === 'pending'">
                  <button @click="openRepairModal(fault)" class="text-xs bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-1.5 rounded-full font-medium">
                    ✅ تصليح
                  </button>
                  <button @click="openCancelFault(fault)" class="text-xs bg-red-50 hover:bg-red-100 text-red-600 px-3 py-1.5 rounded-full font-medium">
                    إلغاء
                  </button>
                </template>
              </div>
            </div>

            <div v-if="expandedFaultId === fault.id && fault.repairs?.length" class="mt-3 mr-8 space-y-2">
              <div v-for="repair in fault.repairs" :key="repair.id" class="flex justify-between items-center bg-gray-50 px-4 py-2 rounded-xl">
                <div>
                  <span class="text-xs font-medium text-emerald-700">🔧 {{ repair.worker_name }}</span>
                  <span v-if="repair.notes" class="text-xs text-gray-500 block mt-0.5">{{ repair.notes }}</span>
                </div>
                <span class="text-xs text-gray-400 shrink-0">{{ new Date(repair.repair_date).toLocaleString('ar-EG') }}</span>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>

    <div v-if="pg.totalPages.value > 1" class="flex justify-center items-center gap-3 mt-6">
      <button @click="pg.prevPage" :disabled="pg.page.value === 1" class="px-4 py-2 rounded-xl bg-white shadow disabled:opacity-40 text-sm">السابق</button>
      <span class="text-sm text-gray-500">صفحة {{ pg.page.value }} من {{ pg.totalPages.value }} ({{ pg.total.value }} عطل)</span>
      <button @click="pg.nextPage" :disabled="pg.page.value === pg.totalPages.value" class="px-4 py-2 rounded-xl bg-white shadow disabled:opacity-40 text-sm">التالي</button>
    </div>

    <FaultRepairModal
      v-if="repairingFault"
      :fault="repairingFault"
      @close="repairingFault = null"
      @success="handleRepairSuccess"
    />

    <BulkRepairModal
      v-if="showBulkRepairModal"
      :count="bulk.selectedCount.value"
      :loading="bulkLoading"
      @close="showBulkRepairModal = false"
      @confirm="confirmBulkRepair"
    />

    <CancelReasonModal
      v-if="showBulkCancelModal"
      title="إلغاء الأعطال المحددة"
      :subtitle="`سيتم إلغاء ${bulk.selectedCount.value} عطل معلق`"
      icon="⚠️"
      :loading="bulkLoading"
      @close="showBulkCancelModal = false"
      @confirm="confirmBulkCancel"
    />

    <CancelReasonModal
      v-if="cancellingFault"
      title="إلغاء العطل"
      :subtitle="`الهيكل: ${cancellingFault.chassis_number} — ${cancellingFault.description}`"
      icon="⚠️"
      :loading="cancelLoading"
      @close="cancellingFault = null"
      @confirm="confirmCancelFault"
    />

    <FaultModal
      v-if="showFaultModal"
      :chassis-list="allChassisList"
      @close="showFaultModal = false"
      @success="handleFaultSuccess"
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
import FaultRepairModal from '../modals/FaultRepairModal.vue'
import BulkRepairModal from '../modals/BulkRepairModal.vue'
import FaultModal from '../modals/FaultModal.vue'
import { useBulkSelection } from '../../../composables/useBulkSelection'

const { apiFetch } = useAuth()

const filters = ref({ chassis_number: '', status: '', repaired_by: '', responsible_worker: '' })
const repairingFault = ref(null)
const expandedFaultId = ref(null)

const statusOptions = [
  { label: 'معلق', value: 'pending' },
  { label: 'تم إصلاحه', value: 'fixed' },
  { label: 'ملغى', value: 'cancelled' },
]

const searchWorkers = async (query) => {
  const params = new URLSearchParams({ limit: 20 })
  if (query) params.set('q', query)
  const res = await apiFetch(`/api/workers/simple/?${params.toString()}`)
  if (!res.ok) return []
  const data = await res.json()
  return data.map(w => ({ label: w.name, value: w.name }))
}

const fetchFaultsPage = async ({ skip, limit }) => {
  const params = new URLSearchParams({ skip, limit })
  if (filters.value.chassis_number) params.set('chassis_number', filters.value.chassis_number)
  if (filters.value.status) params.set('status', filters.value.status)
  if (filters.value.repaired_by) params.set('repaired_by', filters.value.repaired_by)
  if (filters.value.responsible_worker) params.set('responsible_worker', filters.value.responsible_worker)
  const res = await apiFetch(`/api/faults/?${params.toString()}`)
  if (!res.ok) return { items: [], total: 0 }
  return res.json()
}

const pg = useServerPagination(fetchFaultsPage, 10)

let debounceTimer = null
watch(filters, () => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    pg.page.value = 1
    pg.load()
  }, 300)
}, { deep: true })

const resetFilter = () => {
  filters.value = { chassis_number: '', status: '', repaired_by: '', responsible_worker: '' }
}

const getStageName = (stage) => {
  const names = {
    'تجميع_الهيكل': 'تجميع الهيكل',
    'توصيل_الكهرباء_والغلاف': 'توصيل الكهرباء والغلاف',
    'تجميع_كامل': 'تجميع كامل',
  }
  return names[stage] || stage
}

const statusIcon = (status) => status === 'pending' ? '🔴' : status === 'fixed' ? '🟢' : '⚪'
const statusLabel = (status) => status === 'pending' ? 'معلق' : status === 'fixed' ? 'تم إصلاحه' : 'ملغى'
const statusTextClass = (status) => status === 'pending' ? 'text-red-600' : status === 'fixed' ? 'text-emerald-600' : 'text-gray-400'

const toggleExpand = (faultId) => {
  expandedFaultId.value = expandedFaultId.value === faultId ? null : faultId
}

const openRepairModal = (fault) => { repairingFault.value = fault }

const handleRepairSuccess = () => {
  repairingFault.value = null
  pg.load()
  loadAvailableChassis()
}

const bulk = useBulkSelection(pg.items, pg.items, 'id', (fault) => fault.status === 'pending')
watch(pg.items, () => { bulk.clear() })

const pageEligibleCount = computed(() => pg.items.value.filter(f => f.status === 'pending').length)

const showBulkRepairModal = ref(false)
const showBulkCancelModal = ref(false)
const bulkLoading = ref(false)

const openBulkRepair = () => {
  if (bulk.selectedCount.value === 0) { alert('لا توجد أعطال معلقة ضمن التحديد الحالي'); return }
  showBulkRepairModal.value = true
}

const openBulkCancel = () => {
  if (bulk.selectedCount.value === 0) { alert('لا توجد أعطال معلقة ضمن التحديد الحالي'); return }
  showBulkCancelModal.value = true
}

const confirmBulkRepair = async (workerName) => {
  bulkLoading.value = true
  try {
    const ids = bulk.selectedIdsArray.value
    const res = await apiFetch(`/api/faults/bulk-repair/`, {
      method: 'POST',
      body: JSON.stringify({ ids, worker_name: workerName })
    })
    const data = await res.json()

    if (res.ok) {
      showBulkRepairModal.value = false
      bulk.clear()
      pg.load()
    } else {
      alert('❌ ' + (data.detail || 'تعذر تنفيذ التصليح الجماعي'))
    }
  } catch (e) {
    alert('تعذر الاتصال بالسيرفر')
  } finally {
    bulkLoading.value = false
  }
}

const confirmBulkCancel = async (payload) => {
  bulkLoading.value = true
  try {
    const ids = bulk.selectedIdsArray.value
    const res = await apiFetch(`/api/faults/bulk-cancel/`, {
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

const cancellingFault = ref(null)
const cancelLoading = ref(false)
const openCancelFault = (fault) => { cancellingFault.value = fault }

const confirmCancelFault = async (payload) => {
  if (!cancellingFault.value) return
  cancelLoading.value = true
  try {
    const res = await apiFetch(`/api/faults/${cancellingFault.value.id}/cancel/`, {
      method: 'POST',
      body: JSON.stringify(payload)
    })
    const data = await res.json()
    if (res.ok) {
      cancellingFault.value = null
      pg.load()
      loadAvailableChassis()
    } else {
      alert('❌ ' + (data.detail || 'تعذر إلغاء العطل'))
    }
  } catch (e) {
    alert('تعذر الاتصال بالسيرفر')
  } finally {
    cancelLoading.value = false
  }
}

const showFaultModal = ref(false)
const allChassisList = ref([])
const availableChassisList = ref([])

const loadAllChassis = async () => {
  try {
    const res = await apiFetch(`/api/chassis/all/`)
    if (res.ok) allChassisList.value = await res.json()
  } catch (e) { console.error('كل الهياكل', e) }
}

const loadAvailableChassis = async () => {
  try {
    const res = await apiFetch(`/api/chassis/available/`)
    if (res.ok) availableChassisList.value = await res.json()
  } catch (e) { console.error('هياكل متاحة', e) }
}

const handleFaultSuccess = () => {
  showFaultModal.value = false
  pg.load()
  loadAvailableChassis()
}

defineExpose({ clearSelection: bulk.clear, refresh: pg.load })

onMounted(() => {
  pg.load()
  loadAllChassis()
})
</script>