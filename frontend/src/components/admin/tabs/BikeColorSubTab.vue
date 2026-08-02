<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-3xl font-bold">ألوان الدراجات</h2>
      <button @click="$emit('open-bike-color-modal')" class="bg-purple-600 hover:bg-purple-700 text-white px-6 py-3 rounded-2xl font-medium">
        + إضافة لون جديد
      </button>
    </div>

    <div class="bg-white rounded-2xl shadow p-5 mb-6 flex flex-wrap gap-4 items-end">
      <div>
        <SearchableSelect v-model="colorsFilter.name" :options="colorOptions" label="بحث باسم اللون" empty-label="كل الألوان" />
      </div>
      <button @click="resetFilter" class="px-4 py-2 text-gray-500 hover:text-gray-700 underline text-sm">إعادة تعيين</button>
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
      <div v-if="filteredColors.length === 0" class="text-center py-16 text-gray-400 text-lg">لا توجد ألوان مطابقة</div>

      <template v-else>
        <BulkSelectAllBar
          :bulk="bulk"
          :page-eligible-count="pagination.paginatedItems.value.length"
          :page-total="pagination.paginatedItems.value.length"
        />

        <div class="divide-y divide-gray-100">
          <div
            v-for="color in pagination.paginatedItems.value"
            :key="color.id"
            class="flex items-center justify-between gap-4 px-5 py-3 hover:bg-gray-50 transition"
          >
            <div class="flex items-center gap-3 min-w-0 flex-1">
              <input type="checkbox" :checked="bulk.isSelected(color)" @change="bulk.toggleOne(color)" class="w-4 h-4 accent-indigo-600 rounded shrink-0" />

              <div class="w-9 h-9 rounded-full bg-purple-100 text-purple-700 flex items-center justify-center font-bold text-sm shrink-0">
                🎨
              </div>
              <div class="min-w-0">
                <div class="font-bold text-gray-800 truncate">{{ color.name }}</div>
              </div>
            </div>

            <div class="flex items-center gap-4 shrink-0">
              <span class="text-xs bg-purple-50 text-purple-600 font-medium px-3 py-1 rounded-full">
                {{ color.usage_count ?? 0 }} استخدام
              </span>

              <div class="flex items-center gap-1 shrink-0">
                <button @click="$emit('edit-bike-color', color)" class="w-8 h-8 flex items-center justify-center rounded-lg text-gray-400 hover:bg-purple-50 hover:text-purple-600 transition">
                  ✏️
                </button>
                <button @click="askDelete(color)" class="w-8 h-8 flex items-center justify-center rounded-lg text-gray-400 hover:bg-red-50 hover:text-red-600 transition">
                  🗑️
                </button>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>

    <PaginationControls
      :page="pagination.page.value"
      :total-pages="pagination.totalPages.value"
      @prev="pagination.prevPage"
      @next="pagination.nextPage"
    />

    <div v-if="pendingDelete" class="fixed inset-0 bg-black/60 flex items-center justify-center z-[70]">
      <div class="bg-white rounded-2xl p-8 max-w-md mx-4 shadow-2xl">
        <div class="text-4xl mb-4">⚠️</div>
        <p class="text-gray-800 text-lg mb-8">هل أنت متأكد من حذف لون "<strong>{{ pendingDelete.name }}</strong>"؟</p>
        <div class="flex gap-3">
          <button @click="confirmDelete" class="flex-1 bg-red-600 text-white py-4 rounded-xl">نعم، احذف</button>
          <button @click="pendingDelete = null" class="flex-1 bg-gray-100 py-4 rounded-xl">إلغاء</button>
        </div>
      </div>
    </div>

    <BulkDeleteConfirmModal
      v-if="showBulkDeleteModal"
      :message="`هل أنت متأكد من حذف ${bulk.selectedCount.value} لون؟`"
      :loading="bulkLoading"
      @close="showBulkDeleteModal = false"
      @confirm="confirmBulkDelete"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useAuth } from '../../../composables/useAuth'
import { usePagination } from '../../../composables/usePagination'
import SearchableSelect from '../../shared/SearchableSelect.vue'
import BulkActionsBar from '../../shared/BulkActionsBar.vue'
import BulkSelectAllBar from '../../shared/BulkSelectAllBar.vue'
import BulkDeleteConfirmModal from '../../shared/BulkDeleteConfirmModal.vue'
import PaginationControls from '../../shared/PaginationControls.vue'
import { useBulkSelection } from '../../../composables/useBulkSelection'

const emit = defineEmits(['open-bike-color-modal', 'edit-bike-color', 'delete-bike-color', 'refresh-bike-colors'])

const props = defineProps({
  bikeColorsList: { type: Array, default: () => [] }
})

const { apiFetch } = useAuth()

const colorsFilter = ref({ name: '' })
const pendingDelete = ref(null)

const colorOptions = computed(() => props.bikeColorsList.map(c => ({ label: c.name, value: c.name })))

const filteredColors = computed(() => {
  const name = colorsFilter.value.name
  if (!name) return props.bikeColorsList
  return props.bikeColorsList.filter(c => c.name === name)
})

const resetFilter = () => { colorsFilter.value = { name: '' } }

const askDelete = (color) => { pendingDelete.value = color }

const confirmDelete = () => {
  emit('delete-bike-color', pendingDelete.value.id)
  pendingDelete.value = null
}

const pagination = usePagination(filteredColors, 10)
const bulk = useBulkSelection(filteredColors, pagination.paginatedItems)
watch(filteredColors, () => { bulk.clear() })

const showBulkDeleteModal = ref(false)
const bulkLoading = ref(false)

const confirmBulkDelete = async () => {
  bulkLoading.value = true
  try {
    const ids = bulk.selectedIdsArray.value
    const res = await apiFetch(`/api/bike-colors/bulk-delete/`, {
      method: 'POST',
      body: JSON.stringify({ ids })
    })
    const data = await res.json()

    if (res.ok) {
      showBulkDeleteModal.value = false
      bulk.clear()
      emit('refresh-bike-colors')
    } else {
      alert('❌ ' + (data.detail || 'تعذر تنفيذ الحذف الجماعي'))
    }
  } catch (e) {
    alert('تعذر الاتصال بالسيرفر')
  } finally {
    bulkLoading.value = false
  }
}

defineExpose({ clearSelection: bulk.clear })
</script>