<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-3xl font-bold">أنواع الدراجات</h2>
      <button @click="openAdd" class="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-3 rounded-2xl font-medium">
        + إضافة نوع جديد
      </button>
    </div>

    <div class="bg-white rounded-2xl shadow p-5 mb-6 flex flex-wrap gap-4 items-end">
      <div>
        <label class="block text-sm text-gray-500 mb-1">بحث باسم النوع</label>
        <input
          v-model="pg.search.value"
          type="text"
          placeholder="اكتب اسم النوع..."
          class="px-4 py-2 border-2 border-gray-200 rounded-xl focus:border-indigo-400 focus:outline-none"
        />
      </div>
    </div>

    <BulkActionsBar :count="bulk.selectedCount.value" @clear="bulk.clear">
      <button
        @click="showBulkDeleteModal = true"
        :disabled="bulkLoading"
        class="bg-white/20 hover:bg-white/30 text-white px-4 py-2 rounded-xl text-sm font-medium"
      >
        🗑️ حذف المحدد ({{ bulk.selectedCount.value }})
      </button>
    </BulkActionsBar>

    <div class="bg-white rounded-3xl shadow-xl overflow-hidden">
      <div v-if="pg.loading.value" class="text-center py-16 text-gray-400 text-lg">جاري التحميل...</div>
      <div v-else-if="pg.items.value.length === 0" class="text-center py-16 text-gray-400 text-lg">لا توجد أنواع مطابقة</div>

      <template v-else>
        <div class="flex items-center gap-3 px-5 py-2 bg-gray-50 border-b border-gray-100">
          <input
            type="checkbox"
            :checked="bulk.pageAllSelected.value"
            @change="bulk.toggleAllOnPage"
            class="w-4 h-4 accent-indigo-600 rounded"
          />
          <span class="text-xs text-gray-400">تحديد الكل بهذه الصفحة ({{ pg.items.value.length }})</span>
        </div>

        <div class="divide-y divide-gray-100">
          <div
            v-for="type in pg.items.value"
            :key="type.id"
            class="flex items-center justify-between gap-4 px-5 py-3 hover:bg-gray-50 transition"
          >
            <div class="flex items-center gap-3 min-w-0 flex-1">
              <input type="checkbox" :checked="bulk.isSelected(type)" @change="bulk.toggleOne(type)" class="w-4 h-4 accent-indigo-600 rounded shrink-0" />

              <div class="w-9 h-9 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-sm shrink-0">
                🚲
              </div>
              <div class="min-w-0">
                <div class="font-bold text-gray-800 truncate">{{ type.name }}</div>
              </div>
            </div>

            <div class="flex items-center gap-4 shrink-0">
              <span class="text-xs bg-indigo-50 text-indigo-600 font-medium px-3 py-1 rounded-full">
                {{ type.usage_count ?? 0 }} استخدام
              </span>

              <div class="flex items-center gap-1 shrink-0">
                <button @click="openEdit(type)" class="w-8 h-8 flex items-center justify-center rounded-lg text-gray-400 hover:bg-indigo-50 hover:text-indigo-600 transition">
                  ✏️
                </button>
                <button @click="askDelete(type)" class="w-8 h-8 flex items-center justify-center rounded-lg text-gray-400 hover:bg-red-50 hover:text-red-600 transition">
                  🗑️
                </button>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>

    <div v-if="pg.totalPages.value > 1" class="flex justify-center items-center gap-3 mt-6">
      <button @click="pg.prevPage" :disabled="pg.page.value === 1" class="px-4 py-2 rounded-xl bg-white shadow disabled:opacity-40 text-sm">السابق</button>
      <span class="text-sm text-gray-500">صفحة {{ pg.page.value }} من {{ pg.totalPages.value }} ({{ pg.total.value }} نوع)</span>
      <button @click="pg.nextPage" :disabled="pg.page.value === pg.totalPages.value" class="px-4 py-2 rounded-xl bg-white shadow disabled:opacity-40 text-sm">التالي</button>
    </div>

    <div v-if="pendingDelete" class="fixed inset-0 bg-black/60 flex items-center justify-center z-[70]">
      <div class="bg-white rounded-2xl p-8 max-w-md mx-4 shadow-2xl">
        <div class="text-4xl mb-4">⚠️</div>
        <p class="text-gray-800 text-lg mb-8">هل أنت متأكد من حذف نوع "<strong>{{ pendingDelete.name }}</strong>"؟</p>
        <div class="flex gap-3">
          <button @click="confirmDelete" class="flex-1 bg-red-600 text-white py-4 rounded-xl">نعم، احذف</button>
          <button @click="pendingDelete = null" class="flex-1 bg-gray-100 py-4 rounded-xl">إلغاء</button>
        </div>
      </div>
    </div>

    <BulkDeleteConfirmModal
      v-if="showBulkDeleteModal"
      :message="`هل أنت متأكد من حذف ${bulk.selectedCount.value} نوع؟`"
      :loading="bulkLoading"
      @close="showBulkDeleteModal = false"
      @confirm="confirmBulkDelete"
    />

    <BikeTypeFormModal
      v-if="showModal"
      :bike-type="editingType"
      @close="closeModal"
      @success="handleSuccess"
    />
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useAuth } from '../../../composables/useAuth'
import { useServerPagination } from '../../../composables/useServerPagination'
import BulkActionsBar from '../../shared/BulkActionsBar.vue'
import BulkDeleteConfirmModal from '../../shared/BulkDeleteConfirmModal.vue'
import BikeTypeFormModal from '../modals/BikeTypeFormModal.vue'
import { useBulkSelection } from '../../../composables/useBulkSelection'

const emit = defineEmits(['bike-type-changed'])

const { apiFetch } = useAuth()

const pendingDelete = ref(null)
const showModal = ref(false)
const editingType = ref(null)

const fetchTypesPage = async ({ skip, limit, search }) => {
  const params = new URLSearchParams({ skip, limit })
  if (search) params.set('search', search)
  const res = await apiFetch(`/api/bike-types/?${params.toString()}`)
  if (!res.ok) return { items: [], total: 0 }
  return res.json()
}

const pg = useServerPagination(fetchTypesPage, 10)

const openAdd = () => { editingType.value = null; showModal.value = true }
const openEdit = (t) => { editingType.value = t; showModal.value = true }
const closeModal = () => { showModal.value = false; editingType.value = null }
const handleSuccess = () => {
  closeModal()
  pg.load()
  emit('bike-type-changed')
}

const askDelete = (type) => { pendingDelete.value = type }

const confirmDelete = async () => {
  if (!pendingDelete.value) return
  try {
    const res = await apiFetch(`/api/bike-types/${pendingDelete.value.id}/`, { method: 'DELETE' })
    const data = await res.json()
    if (res.ok) {
      pendingDelete.value = null
      pg.load()
      emit('bike-type-changed')
    } else {
      alert('❌ ' + (data.detail || 'تعذر حذف النوع'))
      pendingDelete.value = null
    }
  } catch (e) {
    alert('تعذر الاتصال بالسيرفر')
  }
}

const bulk = useBulkSelection(pg.items, pg.items)
watch(pg.items, () => { bulk.clear() })

const showBulkDeleteModal = ref(false)
const bulkLoading = ref(false)

const confirmBulkDelete = async () => {
  bulkLoading.value = true
  try {
    const ids = bulk.selectedIdsArray.value
    const res = await apiFetch(`/api/bike-types/bulk-delete/`, {
      method: 'POST',
      body: JSON.stringify({ ids })
    })
    const data = await res.json()

    if (res.ok) {
      showBulkDeleteModal.value = false
      bulk.clear()
      pg.load()
      emit('bike-type-changed')
    } else {
      alert('❌ ' + (data.detail || 'تعذر تنفيذ الحذف الجماعي'))
    }
  } catch (e) {
    alert('تعذر الاتصال بالسيرفر')
  } finally {
    bulkLoading.value = false
  }
}

defineExpose({
  clearSelection: bulk.clear,
  refresh: pg.load
})

onMounted(() => {
  pg.load()
})
</script>