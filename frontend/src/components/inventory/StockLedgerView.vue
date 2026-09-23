<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-2xl font-bold">📋 حركات المخزون</h2>
      <button @click="showMovementModal = true" class="bg-emerald-600 hover:bg-emerald-700 text-white px-6 py-3 rounded-2xl font-medium">
        + تسجيل حركة
      </button>
    </div>

    <div class="bg-white rounded-2xl shadow p-5 mb-6 flex flex-wrap gap-4 items-end">
      <div>
        <SearchableSelect v-model="filters.part_id" :async-search="searchParts" label="تصفية بالقطعة" empty-label="كل القطع" />
      </div>
      <div>
        <SearchableSelect v-model="filters.movement_type" :options="typeOptions" label="نوع الحركة" empty-label="الكل" />
      </div>
      <button @click="resetFilter" class="px-4 py-2 text-gray-500 hover:text-gray-700 underline text-sm">إعادة تعيين</button>
    </div>

    <div class="bg-white rounded-3xl shadow-xl overflow-hidden">
      <div v-if="pg.loading.value" class="text-center py-16 text-gray-400 text-lg">جاري التحميل...</div>
      <div v-else-if="pg.items.value.length === 0" class="text-center py-16 text-gray-400 text-lg">لا توجد حركات مطابقة</div>

      <div v-else class="divide-y divide-gray-100">
        <div v-for="m in pg.items.value" :key="m.id" class="px-5 py-4">
          <div class="flex items-center justify-between gap-4 flex-wrap mb-1">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="text-lg">{{ m.movement_type === 'in' ? '📥' : '📤' }}</span>
              <span class="font-bold text-gray-800">{{ m.part_name }}</span>
              <span class="text-xs rounded-full px-2 py-0.5" :class="m.movement_type === 'in' ? 'bg-emerald-50 text-emerald-600' : 'bg-orange-50 text-orange-600'">
                {{ m.movement_type === 'in' ? 'وارد' : 'صادر' }}
              </span>
            </div>
            <span class="font-bold" :class="m.movement_type === 'in' ? 'text-emerald-600' : 'text-orange-600'">
              {{ m.movement_type === 'in' ? '+' : '-' }}{{ Number(m.quantity).toFixed(2) }}
            </span>
          </div>
          <div class="text-xs text-gray-400 flex flex-wrap gap-x-3">
            <span>الرصيد بعد الحركة: {{ Number(m.balance_after).toFixed(2) }}</span>
            <span v-if="m.unit_price != null">السعر: {{ Number(m.unit_price).toFixed(2) }}</span>
            <span v-if="m.supplier_name">المورّد: {{ m.supplier_name }}</span>
            <span v-if="m.related_chassis_number">مرتبط بـ: {{ m.related_chassis_number }}</span>
            <span v-if="m.created_by_username">بواسطة: {{ m.created_by_username }}</span>
            <span>{{ new Date(m.created_at).toLocaleString('ar-EG') }}</span>
          </div>
          <div v-if="m.notes" class="text-xs text-gray-500 mt-1">{{ m.notes }}</div>
        </div>
      </div>
    </div>

    <div v-if="pg.totalPages.value > 1" class="flex justify-center items-center gap-3 mt-6">
      <button @click="pg.prevPage" :disabled="pg.page.value === 1" class="px-4 py-2 rounded-xl bg-white shadow disabled:opacity-40 text-sm">السابق</button>
      <span class="text-sm text-gray-500">صفحة {{ pg.page.value }} من {{ pg.totalPages.value }} ({{ pg.total.value }} حركة)</span>
      <button @click="pg.nextPage" :disabled="pg.page.value === pg.totalPages.value" class="px-4 py-2 rounded-xl bg-white shadow disabled:opacity-40 text-sm">التالي</button>
    </div>

    <StockMovementModal
      v-if="showMovementModal"
      @close="showMovementModal = false"
      @success="handleMovementSuccess"
    />
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useAuth } from '../../composables/useAuth'
import { useServerPagination } from '../../composables/useServerPagination'
import SearchableSelect from '../shared/SearchableSelect.vue'
import StockMovementModal from './StockMovementModal.vue'

const { apiFetch } = useAuth()

const filters = ref({ part_id: '', movement_type: '' })
const showMovementModal = ref(false)

const typeOptions = [
  { label: 'وارد', value: 'in' },
  { label: 'صادر', value: 'out' },
]

const searchParts = async (query) => {
  const params = new URLSearchParams({ limit: 20 })
  if (query) params.set('q', query)
  const res = await apiFetch(`/api/inventory/parts/simple/?${params.toString()}`)
  if (!res.ok) return []
  const data = await res.json()
  return data.map(p => ({ label: `${p.name} (${p.unit})`, value: p.id }))
}

const fetchMovementsPage = async ({ skip, limit }) => {
  const params = new URLSearchParams({ skip, limit })
  if (filters.value.part_id) params.set('part_id', filters.value.part_id)
  if (filters.value.movement_type) params.set('movement_type', filters.value.movement_type)
  const res = await apiFetch(`/api/inventory/movements/?${params.toString()}`)
  if (!res.ok) return { items: [], total: 0 }
  return res.json()
}

const pg = useServerPagination(fetchMovementsPage, 15)

let debounceTimer = null
watch(filters, () => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    pg.page.value = 1
    pg.load()
  }, 300)
}, { deep: true })

const resetFilter = () => { filters.value = { part_id: '', movement_type: '' } }

const handleMovementSuccess = () => {
  showMovementModal.value = false
  pg.load()
}

onMounted(() => {
  pg.load()
})
</script>