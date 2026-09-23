<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-2xl font-bold">قائمة القطع</h2>
      <button @click="openAdd" class="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-3 rounded-2xl font-medium">
        + إضافة قطعة جديدة
      </button>
    </div>

    <div class="bg-white rounded-2xl shadow p-5 mb-6 flex flex-wrap gap-4 items-end">
      <div class="min-w-[220px]">
        <SearchableSelect
          v-model="pg.search.value"
          :async-search="searchPartsForFilter"
          label="تصفية باسم القطعة"
          placeholder="ابحث عن قطعة..."
          empty-label="كل القطع"
        />
      </div>
    </div>

    <div class="bg-white rounded-3xl shadow-xl overflow-hidden">
      <div v-if="pg.loading.value" class="text-center py-16 text-gray-400 text-lg">جاري التحميل...</div>
      <div v-else-if="pg.items.value.length === 0" class="text-center py-16 text-gray-400 text-lg">لا توجد قطع مطابقة</div>

      <div v-else class="divide-y divide-gray-100">
        <div
          v-for="part in pg.items.value"
          :key="part.id"
          class="flex items-center justify-between gap-4 px-5 py-3 hover:bg-gray-50 transition flex-wrap"
        >
          <div class="flex items-center gap-3 min-w-0 flex-1">
            <div class="w-9 h-9 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-sm shrink-0">
              🧩
            </div>
            <div class="min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="font-bold text-gray-800 truncate">{{ part.name }}</span>
                <span v-if="part.flagged_for_reorder" class="text-xs bg-red-50 text-red-600 rounded-full px-2 py-0.5">
                  🛒 بحاجة لطلب
                </span>
              </div>
              <div class="text-xs text-gray-400">الوحدة: {{ part.unit }}</div>
            </div>
          </div>

          <div class="flex items-center gap-4 shrink-0">
            <span class="text-sm font-bold" :class="Number(part.current_stock) <= 0 ? 'text-red-600' : 'text-emerald-600'">
              {{ Number(part.current_stock).toFixed(2) }} {{ part.unit }}
            </span>

            <div class="flex items-center gap-1 shrink-0">
              <button @click="openMovement(part, 'in')" class="text-xs bg-emerald-50 hover:bg-emerald-100 text-emerald-700 px-3 py-1.5 rounded-full font-medium">
                📥 وارد
              </button>
              <button @click="openMovement(part, 'out')" class="text-xs bg-orange-50 hover:bg-orange-100 text-orange-600 px-3 py-1.5 rounded-full font-medium">
                📤 صادر
              </button>
              <button @click="toggleReorder(part)" class="text-xs bg-red-50 hover:bg-red-100 text-red-600 px-3 py-1.5 rounded-full font-medium">
                🛒 {{ part.flagged_for_reorder ? 'إلغاء العلامة' : 'وسم كنافد' }}
              </button>
              <button @click="openEdit(part)" class="w-8 h-8 flex items-center justify-center rounded-lg text-gray-400 hover:bg-indigo-50 hover:text-indigo-600 transition">
                ✏️
              </button>
              <button @click="askDelete(part)" class="w-8 h-8 flex items-center justify-center rounded-lg text-gray-400 hover:bg-red-50 hover:text-red-600 transition">
                🗑️
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="pg.totalPages.value > 1" class="flex justify-center items-center gap-3 mt-6">
      <button @click="pg.prevPage" :disabled="pg.page.value === 1" class="px-4 py-2 rounded-xl bg-white shadow disabled:opacity-40 text-sm">السابق</button>
      <span class="text-sm text-gray-500">صفحة {{ pg.page.value }} من {{ pg.totalPages.value }} ({{ pg.total.value }} قطعة)</span>
      <button @click="pg.nextPage" :disabled="pg.page.value === pg.totalPages.value" class="px-4 py-2 rounded-xl bg-white shadow disabled:opacity-40 text-sm">التالي</button>
    </div>

    <div v-if="pendingDelete" class="fixed inset-0 bg-black/60 flex items-center justify-center z-[70]">
      <div class="bg-white rounded-2xl p-8 max-w-md mx-4 shadow-2xl">
        <div class="text-4xl mb-4">⚠️</div>
        <p class="text-gray-800 text-lg mb-8">هل أنت متأكد من حذف القطعة "<strong>{{ pendingDelete.name }}</strong>"؟</p>
        <div class="flex gap-3">
          <button @click="confirmDelete" class="flex-1 bg-red-600 text-white py-4 rounded-xl">نعم، احذف</button>
          <button @click="pendingDelete = null" class="flex-1 bg-gray-100 py-4 rounded-xl">إلغاء</button>
        </div>
      </div>
    </div>

    <PartFormModal
      v-if="showModal"
      :part="editingPart"
      @close="closeModal"
      @success="handleSuccess"
    />

    <StockMovementModal
      v-if="movementTarget"
      :preset-part-id="movementTarget.part.id"
      :preset-part-name="movementTarget.part.name"
      :preset-part-unit="movementTarget.part.unit"
      :preset-type="movementTarget.type"
      @close="movementTarget = null"
      @success="handleMovementSuccess"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useAuth } from '../../composables/useAuth'
import { useServerPagination } from '../../composables/useServerPagination'
import { useToast } from '../../composables/useToast'
import SearchableSelect from '../shared/SearchableSelect.vue'
import PartFormModal from './PartFormModal.vue'
import StockMovementModal from './StockMovementModal.vue'

const { apiFetch } = useAuth()
const { showToast } = useToast()

const pendingDelete = ref(null)
const showModal = ref(false)
const editingPart = ref(null)
const movementTarget = ref(null)

const fetchPartsPage = async ({ skip, limit, search }) => {
  const params = new URLSearchParams({ skip, limit })
  if (search) params.set('search', search)
  const res = await apiFetch(`/api/inventory/parts/?${params.toString()}`)
  if (!res.ok) return { items: [], total: 0 }
  return res.json()
}

const pg = useServerPagination(fetchPartsPage, 10)

// 🆕 يُرجع اسم القطعة كقيمة (value) بدل المعرّف، لأن فلتر get_parts في
// الباك إند يستقبل نصًا (search) ويبحث بـ ilike، وليس معرّف قطعة محدد
const searchPartsForFilter = async (query) => {
  const params = new URLSearchParams({ limit: 20 })
  if (query) params.set('q', query)
  const res = await apiFetch(`/api/inventory/parts/simple/?${params.toString()}`)
  if (!res.ok) return []
  const data = await res.json()
  return data.map(p => ({ label: `${p.name} (${p.unit})`, value: p.name }))
}

const openAdd = () => { editingPart.value = null; showModal.value = true }
const openEdit = (p) => { editingPart.value = p; showModal.value = true }
const closeModal = () => { showModal.value = false; editingPart.value = null }
const handleSuccess = () => { closeModal(); pg.load() }

const openMovement = (part, type) => { movementTarget.value = { part, type } }
const handleMovementSuccess = () => { movementTarget.value = null; pg.load() }

const toggleReorder = async (part) => {
  try {
    const res = await apiFetch(`/api/inventory/parts/${part.id}/reorder/`, {
      method: 'POST',
      body: JSON.stringify({ flagged: !part.flagged_for_reorder })
    })
    if (res.ok) {
      showToast('success', '✅ تم التحديث')
      pg.load()
    } else {
      showToast('error', 'تعذر تنفيذ العملية')
    }
  } catch (e) {
    showToast('error', 'تعذر الاتصال بالسيرفر')
  }
}

const askDelete = (part) => { pendingDelete.value = part }

const confirmDelete = async () => {
  if (!pendingDelete.value) return
  try {
    const res = await apiFetch(`/api/inventory/parts/${pendingDelete.value.id}/`, { method: 'DELETE' })
    const data = await res.json()
    if (res.ok) {
      pendingDelete.value = null
      showToast('success', '✅ تم حذف القطعة بنجاح')
      pg.load()
    } else {
      showToast('error', '❌ ' + (data.detail || 'تعذر حذف القطعة'))
      pendingDelete.value = null
    }
  } catch (e) {
    showToast('error', 'تعذر الاتصال بالسيرفر')
  }
}

defineExpose({ refresh: pg.load, clearSelection: () => {} })

pg.load()
</script>