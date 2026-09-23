<template>
  <div>
    <div class="flex justify-between items-center mb-2">
      <h2 class="text-2xl font-bold">🛒 قطع تحتاج طلب</h2>
      <button @click="showAddModal = true" class="bg-red-600 hover:bg-red-700 text-white px-5 py-2.5 rounded-2xl font-medium text-sm">
        + إضافة قطعة نفدت
      </button>
    </div>
    <p class="text-sm text-gray-500 mb-6">
      القطع المُعلَّمة يدويًا بأنها نفدت أو أوشكت على النفاد. بعد إتمام الطلب
      والاستلام، سجّل حركة "وارد" من قائمة القطع ثم أزل العلامة من هنا.
    </p>

    <div v-if="loading" class="text-center py-16 text-gray-400 text-lg">جاري التحميل...</div>
    <div v-else-if="items.length === 0" class="text-center py-16 text-gray-400 text-lg bg-white rounded-2xl shadow">
      ✅ لا توجد قطع مُعلَّمة للطلب حاليًا
    </div>

    <div v-else class="bg-white rounded-3xl shadow-xl divide-y divide-gray-100">
      <div v-for="part in items" :key="part.id" class="flex items-center justify-between gap-4 px-5 py-4 flex-wrap">
        <div class="min-w-0">
          <div class="font-bold text-gray-800">{{ part.name }}</div>
          <div class="text-xs text-gray-400 mt-1">
            الرصيد الحالي: {{ Number(part.current_stock).toFixed(2) }} {{ part.unit }}
          </div>
        </div>
        <button
          @click="untoggle(part)"
          :disabled="togglingId === part.id"
          class="text-xs bg-emerald-50 hover:bg-emerald-100 text-emerald-700 px-4 py-2 rounded-full font-medium shrink-0"
        >
          {{ togglingId === part.id ? '...' : '✅ تم الطلب' }}
        </button>
      </div>
    </div>

    <PartReorderAddModal
      v-if="showAddModal"
      @close="showAddModal = false"
      @success="handleAddSuccess"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuth } from '../../composables/useAuth'
import { useToast } from '../../composables/useToast'
import PartReorderAddModal from './PartReorderAddModal.vue'

const { apiFetch } = useAuth()
const { showToast } = useToast()

const items = ref([])
const loading = ref(false)
const togglingId = ref(null)
const showAddModal = ref(false)

const load = async () => {
  loading.value = true
  try {
    const res = await apiFetch(`/api/inventory/reorder-list/`)
    if (res.ok) items.value = await res.json()
  } catch (e) {
    console.error('قائمة الطلب', e)
  } finally {
    loading.value = false
  }
}

const handleAddSuccess = () => {
  showAddModal.value = false
  load()
}

const untoggle = async (part) => {
  togglingId.value = part.id
  try {
    const res = await apiFetch(`/api/inventory/parts/${part.id}/reorder/`, {
      method: 'POST',
      body: JSON.stringify({ flagged: false })
    })
    if (res.ok) {
      showToast('success', '✅ تمت إزالة القطعة من قائمة الطلب')
      load()
    } else {
      showToast('error', 'تعذر تنفيذ العملية')
    }
  } catch (e) {
    showToast('error', 'تعذر الاتصال بالسيرفر')
  } finally {
    togglingId.value = null
  }
}

onMounted(load)
</script>