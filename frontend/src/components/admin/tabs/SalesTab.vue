<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-3xl font-bold">المبيعات</h2>
      <button @click="$emit('open-sale-modal')" class="bg-green-600 hover:bg-green-700 text-white px-6 py-3 rounded-2xl font-medium">
        + تسجيل بيع جديد
      </button>
    </div>

    <div class="bg-white rounded-2xl shadow p-5 mb-6 flex flex-wrap gap-4 items-end">
      <div>
        <SearchableSelect v-model="salesFilter.customer_name" :options="customerOptions" label="تصفية بالعميل" empty-label="كل العملاء" />
      </div>
      <div>
        <SearchableSelect v-model="salesFilter.status" :options="statusOptions" label="تصفية بالحالة" empty-label="كل الحالات" />
      </div>
      <div>
        <label class="block text-sm text-gray-500 mb-1">من تاريخ</label>
        <input type="date" v-model="salesFilter.date_from" class="px-4 py-2 border-2 border-gray-200 rounded-xl focus:border-indigo-400 focus:outline-none" />
      </div>
      <div>
        <label class="block text-sm text-gray-500 mb-1">إلى تاريخ</label>
        <input type="date" v-model="salesFilter.date_to" class="px-4 py-2 border-2 border-gray-200 rounded-xl focus:border-indigo-400 focus:outline-none" />
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
      <div v-if="filteredSales.length === 0" class="text-center py-16 text-gray-400 text-lg">لا توجد مبيعات مطابقة</div>

      <template v-else>
        <div class="flex items-center gap-3 px-5 py-2 bg-gray-50 border-b border-gray-100">
          <input
            type="checkbox"
            :checked="bulk.allSelected.value"
            :disabled="bulk.eligibleCount.value === 0"
            @change="bulk.toggleAll"
            class="w-4 h-4 accent-indigo-600 rounded disabled:opacity-30 disabled:cursor-not-allowed"
          />
          <span class="text-xs text-gray-400">
            تحديد الكل ({{ bulk.eligibleCount.value }} قابل للتحديد من {{ filteredSales.length }})
          </span>
        </div>

        <div class="divide-y divide-gray-100">
          <div
            v-for="sale in filteredSales"
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
                @click="$emit('cancel-sale', sale)"
                class="text-xs bg-red-50 hover:bg-red-100 text-red-600 px-3 py-1.5 rounded-full font-medium"
              >
                إلغاء البيع
              </button>
            </div>
          </div>
        </div>
      </template>
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
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useAuth } from '../../../composables/useAuth'
import SearchableSelect from '../../shared/SearchableSelect.vue'
import BulkActionsBar from '../../shared/BulkActionsBar.vue'
import CancelReasonModal from '../../shared/CancelReasonModal.vue'
import { useBulkSelection } from '../../../composables/useBulkSelection'

const emit = defineEmits(['open-sale-modal', 'cancel-sale', 'refresh-sales'])

const props = defineProps({
  salesList: { type: Array, default: () => [] },
  customersList: { type: Array, default: () => [] }
})

const API = import.meta.env.VITE_API_BASE_URL
const { apiFetch } = useAuth()

const salesFilter = ref({ customer_name: '', status: '', date_from: '', date_to: '' })

const statusOptions = [
  { label: 'نشط', value: 'active' },
  { label: 'ملغى', value: 'cancelled' },
]

const customerOptions = computed(() => props.customersList.map(c => ({ label: c.name, value: c.name })))

const filteredSales = computed(() => {
  return props.salesList.filter(s => {
    if (salesFilter.value.customer_name && s.customer_name !== salesFilter.value.customer_name) return false
    if (salesFilter.value.status && s.status !== salesFilter.value.status) return false
    if (salesFilter.value.date_from && new Date(s.sale_date) < new Date(salesFilter.value.date_from)) return false
    if (salesFilter.value.date_to && new Date(s.sale_date) > new Date(salesFilter.value.date_to)) return false
    return true
  })
})

const resetFilter = () => { salesFilter.value = { customer_name: '', status: '', date_from: '', date_to: '' } }

// ── التحديد المتعدد: فقط المبيعات النشطة قابلة للتحديد ─────────────────
const bulk = useBulkSelection(filteredSales, 'id', (sale) => sale.status === 'active')
watch(filteredSales, () => { bulk.clear() })

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
      emit('refresh-sales')
    } else {
      alert('❌ ' + (data.detail || 'تعذر تنفيذ الإلغاء الجماعي'))
    }
  } catch (e) {
    alert('تعذر الاتصال بالسيرفر')
  } finally {
    bulkLoading.value = false
  }
}

defineExpose({ clearSelection: bulk.clear })
</script>