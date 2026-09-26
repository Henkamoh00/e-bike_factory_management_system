<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-3xl font-bold">سجل النشاط</h2>
      <span class="text-sm text-gray-400">{{ total }} حدث</span>
    </div>

    <div class="bg-white rounded-2xl shadow p-5 mb-6 flex flex-wrap gap-4 items-end">
      <div>
        <SearchableSelect v-model="filters.action" :options="actionOptions" label="نوع العملية" empty-label="كل العمليات" />
      </div>
      <div>
        <SearchableSelect v-model="filters.entity_type" :options="entityOptions" label="نوع العنصر" empty-label="كل العناصر" />
      </div>
      <div>
        <SearchableSelect v-model="filters.user_id" :options="userOptions" label="المستخدم" empty-label="كل المستخدمين" />
      </div>
      <div>
        <label class="block text-sm text-gray-500 mb-1">بحث</label>
        <input
          v-model="filters.search"
          type="text"
          placeholder="رقم هيكل، اسم..."
          class="px-4 py-2 border-2 border-gray-200 rounded-xl focus:border-indigo-400 focus:outline-none"
        />
      </div>
      <div>
        <label class="block text-sm text-gray-500 mb-1">من تاريخ</label>
        <input type="date" v-model="filters.date_from" class="px-4 py-2 border-2 border-gray-200 rounded-xl focus:border-indigo-400 focus:outline-none" />
      </div>
      <div>
        <label class="block text-sm text-gray-500 mb-1">إلى تاريخ</label>
        <input type="date" v-model="filters.date_to" class="px-4 py-2 border-2 border-gray-200 rounded-xl focus:border-indigo-400 focus:outline-none" />
      </div>
      <button @click="resetFilters" class="px-4 py-2 text-gray-500 hover:text-gray-700 underline text-sm">إعادة تعيين</button>
    </div>

    <div class="bg-white rounded-3xl shadow-xl overflow-hidden">
      <div v-if="loading" class="text-center py-16 text-gray-400 text-lg">جاري التحميل...</div>
      <div v-else-if="logs.length === 0" class="text-center py-16 text-gray-400 text-lg">لا توجد أحداث مطابقة</div>

      <div v-else class="divide-y divide-gray-100">
        <div
          v-for="log in logs"
          :key="log.id"
          @click="openDetail(log.id)"
          class="flex items-center justify-between gap-4 px-5 py-3 hover:bg-gray-50 transition cursor-pointer"
        >
          <div class="flex items-center gap-3 min-w-0 flex-1">
            <div class="w-9 h-9 rounded-full flex items-center justify-center text-base shrink-0" :class="actionBadgeClass(log.action)">
              {{ actionIcon(log.action) }}
            </div>
            <div class="min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="font-bold text-gray-800">{{ actionLabel(log.action) }}</span>
                <span class="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full">{{ entityLabel(log.entity_type) }}</span>
              </div>
              <div class="text-sm text-gray-600 truncate">{{ log.entity_label || '—' }}</div>
              <div v-if="log.details" class="text-xs text-gray-400 truncate mt-0.5">{{ log.details }}</div>
            </div>
          </div>

          <div class="text-left shrink-0">
            <div class="text-xs font-medium text-indigo-600">{{ log.user_full_name || log.username || 'النظام' }}</div>
            <div class="text-xs text-gray-400">{{ new Date(log.timestamp).toLocaleString('ar-EG') }}</div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="total > pageSize" class="flex justify-center items-center gap-3 mt-6">
      <button @click="prevPage" :disabled="page === 1" class="px-4 py-2 rounded-xl bg-white shadow disabled:opacity-40">السابق</button>
      <span class="text-sm text-gray-500">صفحة {{ page }} من {{ totalPages }}</span>
      <button @click="nextPage" :disabled="page === totalPages" class="px-4 py-2 rounded-xl bg-white shadow disabled:opacity-40">التالي</button>
    </div>

    <LogDetailModal
      v-if="selectedLogId"
      :log-id="selectedLogId"
      @close="selectedLogId = null"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useAuth } from '../../../composables/useAuth'
import SearchableSelect from '../../shared/SearchableSelect.vue'
import LogDetailModal from '../modals/LogDetailModal.vue'

const { apiFetch } = useAuth()

const logs = ref([])
const total = ref(0)
const loading = ref(false)
const page = ref(1)
const pageSize = 10

const selectedLogId = ref(null)
const openDetail = (id) => { selectedLogId.value = id }

const filters = ref({ action: '', entity_type: '', user_id: '', search: '', date_from: '', date_to: '' })

const meta = ref({ actions: [], entity_types: [], users: [] })

const actionLabels = {
  create: 'إنشاء', update: 'تعديل', delete: 'حذف', cancel: 'إلغاء',
  restore: 'استعادة', repair: 'تصليح', login: 'تسجيل دخول',
  bulk_delete: 'حذف جماعي', bulk_cancel: 'إلغاء جماعي', bulk_repair: 'تصليح جماعي',
  bulk_restore: 'استعادة جماعية', bulk_activate: 'تفعيل جماعي', bulk_deactivate: 'تعطيل جماعي'
}

const entityLabels = {
  worker: 'عامل', customer: 'عميل', bike_type: 'نوع دراجة', bike_color: 'لون دراجة',
  assembly: 'تجميع', fault: 'عطل', fault_repair: 'تصليح عطل', user: 'مستخدم', role: 'دور',
  invoice: 'فاتورة', invoice_item: 'بند فاتورة', payment: 'دفعة', chassis_return: 'إرجاع دراجة'
}

const actionOptions = computed(() => meta.value.actions.map(a => ({ label: actionLabels[a] || a, value: a })))
const entityOptions = computed(() => meta.value.entity_types.map(e => ({ label: entityLabels[e] || e, value: e })))
const userOptions = computed(() => meta.value.users.map(u => ({ label: u.label, value: String(u.id) })))

const actionLabel = (a) => actionLabels[a] || a
const entityLabel = (e) => entityLabels[e] || e

const actionIcon = (a) => {
  if (a.includes('delete')) return '🗑️'
  if (a.includes('cancel')) return '❌'
  if (a.includes('restore')) return '♻️'
  if (a.includes('repair')) return '🔧'
  if (a === 'create') return '✅'
  if (a === 'update') return '✏️'
  if (a === 'login') return '🔑'
  if (a === 'bulk_activate') return '✅'
  if (a === 'bulk_deactivate') return '🚫'
  return '📌'
}
const actionBadgeClass = (a) => {
  if (a.includes('delete') || a.includes('cancel') || a === 'bulk_deactivate') return 'bg-red-100 text-red-600'
  if (a.includes('restore') || a === 'bulk_activate') return 'bg-emerald-100 text-emerald-600'
  if (a === 'create') return 'bg-indigo-100 text-indigo-600'
  return 'bg-amber-100 text-amber-600'
}

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

const loadMeta = async () => {
  try {
    const res = await apiFetch('/api/logs/meta/')
    if (res.ok) meta.value = await res.json()
  } catch (e) { console.error('meta', e) }
}

const loadLogs = async () => {
  loading.value = true
  try {
    const params = new URLSearchParams()
    params.set('skip', (page.value - 1) * pageSize)
    params.set('limit', pageSize)
    if (filters.value.action) params.set('action', filters.value.action)
    if (filters.value.entity_type) params.set('entity_type', filters.value.entity_type)
    if (filters.value.user_id) params.set('user_id', filters.value.user_id)
    if (filters.value.search) params.set('search', filters.value.search)
    if (filters.value.date_from) params.set('date_from', filters.value.date_from)
    if (filters.value.date_to) params.set('date_to', filters.value.date_to)

    const res = await apiFetch(`/api/logs/?${params.toString()}`)
    if (res.ok) {
      const data = await res.json()
      logs.value = data.items
      total.value = data.total
    }
  } catch (e) {
    console.error('logs', e)
  } finally {
    loading.value = false
  }
}

const resetFilters = () => {
  filters.value = { action: '', entity_type: '', user_id: '', search: '', date_from: '', date_to: '' }
  page.value = 1
}

const prevPage = () => { if (page.value > 1) { page.value--; loadLogs() } }
const nextPage = () => { if (page.value < totalPages.value) { page.value++; loadLogs() } }

let debounceTimer = null
watch(filters, () => {
  page.value = 1
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(loadLogs, 350)
}, { deep: true })

defineExpose({ clearSelection: () => {} })

onMounted(() => {
  loadMeta()
  loadLogs()
})
</script>