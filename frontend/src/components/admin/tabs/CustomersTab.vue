<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-3xl font-bold">العملاء</h2>
      <button @click="openAdd" class="bg-purple-600 hover:bg-purple-700 text-white px-6 py-3 rounded-2xl font-medium">
        + إضافة عميل جديد
      </button>
    </div>

    <div class="bg-white rounded-2xl shadow p-5 mb-6 flex flex-wrap gap-4 items-end">
      <div>
        <label class="block text-sm text-gray-500 mb-1">بحث باسم العميل</label>
        <input
          v-model="pg.search.value"
          type="text"
          placeholder="اكتب اسم العميل..."
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
      <div v-else-if="pg.items.value.length === 0" class="text-center py-16 text-gray-400 text-lg">لا يوجد عملاء مطابقون</div>

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
            v-for="customer in pg.items.value"
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
                <button @click="openEdit(customer)" class="w-8 h-8 flex items-center justify-center rounded-lg text-gray-400 hover:bg-purple-50 hover:text-purple-600 transition">
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

    <div v-if="pg.totalPages.value > 1" class="flex justify-center items-center gap-3 mt-6">
      <button @click="pg.prevPage" :disabled="pg.page.value === 1" class="px-4 py-2 rounded-xl bg-white shadow disabled:opacity-40 text-sm">السابق</button>
      <span class="text-sm text-gray-500">صفحة {{ pg.page.value }} من {{ pg.totalPages.value }} ({{ pg.total.value }} عميل)</span>
      <button @click="pg.nextPage" :disabled="pg.page.value === pg.totalPages.value" class="px-4 py-2 rounded-xl bg-white shadow disabled:opacity-40 text-sm">التالي</button>
    </div>

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

    <CustomerFormModal
      v-if="showModal"
      :customer="editingCustomer"
      @close="closeModal"
      @success="handleSuccess"
    />
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useAuth } from '../../../composables/useAuth'
import { useServerPagination } from '../../../composables/useServerPagination'
import { useToast } from '../../../composables/useToast'
import BulkActionsBar from '../../shared/BulkActionsBar.vue'
import BulkDeleteConfirmModal from '../../shared/BulkDeleteConfirmModal.vue'
import CustomerFormModal from '../modals/CustomerFormModal.vue'
import { useBulkSelection } from '../../../composables/useBulkSelection'

const emit = defineEmits(['customer-changed'])

const { apiFetch } = useAuth()
const { showToast } = useToast()

const pendingDelete = ref(null)
const showModal = ref(false)
const editingCustomer = ref(null)

const fetchCustomersPage = async ({ skip, limit, search }) => {
  const params = new URLSearchParams({ skip, limit })
  if (search) params.set('search', search)
  const res = await apiFetch(`/api/customers/?${params.toString()}`)
  if (!res.ok) return { items: [], total: 0 }
  return res.json()
}

const pg = useServerPagination(fetchCustomersPage, 10)

const openAdd = () => { editingCustomer.value = null; showModal.value = true }
const openEdit = (c) => { editingCustomer.value = c; showModal.value = true }
const closeModal = () => { showModal.value = false; editingCustomer.value = null }
const handleSuccess = () => {
  closeModal()
  pg.load()
  emit('customer-changed')
}

const askDelete = (customer) => { pendingDelete.value = customer }

const confirmDelete = async () => {
  if (!pendingDelete.value) return
  try {
    const res = await apiFetch(`/api/customers/${pendingDelete.value.id}/`, { method: 'DELETE' })
    const data = await res.json()
    if (res.ok) {
      pendingDelete.value = null
      showToast('success', '✅ تم حذف العميل بنجاح')
      pg.load()
      emit('customer-changed')
    } else {
      showToast('error', '❌ ' + (data.detail || 'تعذر حذف العميل'))
      pendingDelete.value = null
    }
  } catch (e) {
    showToast('error', 'تعذر الاتصال بالسيرفر')
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
    const res = await apiFetch(`/api/customers/bulk-delete/`, {
      method: 'POST',
      body: JSON.stringify({ ids })
    })
    const data = await res.json()

    if (res.ok) {
      showBulkDeleteModal.value = false
      showToast('success', `✅ ${data.message || 'تم الحذف الجماعي بنجاح'}`)
      bulk.clear()
      pg.load()
      emit('customer-changed')
    } else {
      showToast('error', '❌ ' + (data.detail || 'تعذر تنفيذ الحذف الجماعي'))
    }
  } catch (e) {
    showToast('error', 'تعذر الاتصال بالسيرفر')
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