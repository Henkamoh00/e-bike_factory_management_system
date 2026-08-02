<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-3xl font-bold">العملاء</h2>
      <button @click="$emit('open-customer-modal')" class="bg-purple-600 hover:bg-purple-700 text-white px-6 py-3 rounded-2xl font-medium">
        + إضافة عميل جديد
      </button>
    </div>

    <div class="bg-white rounded-2xl shadow p-5 mb-6 flex flex-wrap gap-4 items-end">
      <div>
        <SearchableSelect v-model="customersFilter.name" :options="customerOptions" label="بحث باسم العميل" empty-label="كل العملاء" />
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
      <div v-if="filteredCustomers.length === 0" class="text-center py-16 text-gray-400 text-lg">لا يوجد عملاء مطابقون</div>

      <template v-else>
        <BulkSelectAllBar
          :bulk="bulk"
          :page-eligible-count="pagination.paginatedItems.value.length"
          :page-total="pagination.paginatedItems.value.length"
        />

        <div class="divide-y divide-gray-100">
          <div
            v-for="customer in pagination.paginatedItems.value"
            :key="customer.id"
            class="flex items-center justify-between gap-4 px-5 py-3 hover:bg-gray-50 transition"
          >
            <div class="flex items-center gap-3 min-w-0 flex-1">
              <input type="checkbox" :checked="bulk.isSelected(customer)" @change="bulk.toggleOne(customer)" class="w-4 h-4 accent-indigo-600 rounded shrink-0" />

              <div class="w-9 h-9 rounded-full bg-purple-100 text-purple-700 flex items-center justify-center font-bold text-sm shrink-0">
                {{ customer.name.charAt(0) }}
              </div>
              <div class="min-w-0">
                <div class="font-bold text-gray-800 truncate">{{ customer.name }}</div>
                <div class="text-xs text-gray-400 truncate">
                  <span v-if="customer.phone">{{ customer.phone }}</span>
                  <span v-if="customer.phone && customer.address"> • </span>
                  <span v-if="customer.address">{{ customer.address }}</span>
                </div>
              </div>
            </div>

            <div class="flex items-center gap-4 shrink-0">
              <span class="text-xs bg-purple-50 text-purple-600 font-medium px-3 py-1 rounded-full">
                {{ customer.total_purchases ?? 0 }} دراجة
              </span>

              <div class="flex items-center gap-1 shrink-0">
                <button @click="$emit('edit-customer', customer)" class="w-8 h-8 flex items-center justify-center rounded-lg text-gray-400 hover:bg-purple-50 hover:text-purple-600 transition">
                  ✏️
                </button>
                <button @click="askDelete(customer)" class="w-8 h-8 flex items-center justify-center rounded-lg text-gray-400 hover:bg-red-50 hover:text-red-600 transition">
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
        <p class="text-gray-800 text-lg mb-8">هل أنت متأكد من حذف العميل "<strong>{{ pendingDelete.name }}</strong>"؟</p>
        <div class="flex gap-3">
          <button @click="confirmDelete" class="flex-1 bg-red-600 text-white py-4 rounded-xl">نعم، احذف</button>
          <button @click="pendingDelete = null" class="flex-1 bg-gray-100 py-4 rounded-xl">إلغاء</button>
        </div>
      </div>
    </div>

    <BulkDeleteConfirmModal
      v-if="showBulkDeleteModal"
      :message="`هل أنت متأكد من حذف ${bulk.selectedCount.value} عميل؟`"
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

const emit = defineEmits(['open-customer-modal', 'edit-customer', 'delete-customer', 'refresh-customers'])

const props = defineProps({
  customersList: { type: Array, default: () => [] }
})

const { apiFetch } = useAuth()

const customersFilter = ref({ name: '' })
const pendingDelete = ref(null)

const customerOptions = computed(() => props.customersList.map(c => ({ label: c.name, value: c.name })))

const filteredCustomers = computed(() => {
  const name = customersFilter.value.name
  if (!name) return props.customersList
  return props.customersList.filter(c => c.name === name)
})

const resetFilter = () => { customersFilter.value = { name: '' } }

const askDelete = (customer) => { pendingDelete.value = customer }

const confirmDelete = () => {
  emit('delete-customer', pendingDelete.value.id)
  pendingDelete.value = null
}

const pagination = usePagination(filteredCustomers, 10)
const bulk = useBulkSelection(filteredCustomers, pagination.paginatedItems)
watch(filteredCustomers, () => { bulk.clear() })

const showBulkDeleteModal = ref(false)
const bulkLoading = ref(false)

const confirmBulkDelete = async () => {
  bulkLoading.value = true
  try {
    const ids = bulk.selectedIdsArray.value
    const res = await apiFetch(`/api/customers/bulk-delete/`, {
      method: 'POST',
      body: JSON.stringify({ ids })
    })
    const data = await res.json()

    if (res.ok) {
      showBulkDeleteModal.value = false
      bulk.clear()
      emit('refresh-customers')
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