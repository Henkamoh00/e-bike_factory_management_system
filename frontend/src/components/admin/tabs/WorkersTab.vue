<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-3xl font-bold">العمال</h2>
      <button @click="$emit('open-worker-modal')" class="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-3 rounded-2xl font-medium">
        + إضافة عامل جديد
      </button>
    </div>

    <!-- فلاتر العمال -->
    <div class="bg-white rounded-2xl shadow p-5 mb-6 flex flex-wrap gap-4 items-end">
      <div>
        <SearchableSelect
          v-model="workersFilter.stage"
          :options="stageOptions"
          label="تصفية بنوع المرحلة"
          empty-label="كل المراحل"
        />
      </div>
      <button @click="resetFilter" class="px-4 py-2 text-gray-500 hover:text-gray-700 underline text-sm">إعادة تعيين</button>
    </div>

    <div class="bg-white rounded-3xl shadow-xl overflow-hidden">
      <div v-if="filteredWorkers.length === 0" class="text-center py-16 text-gray-400 text-lg">لا يوجد عمال مطابقون</div>

      <div v-else class="divide-y divide-gray-100">
        <div
          v-for="worker in filteredWorkers"
          :key="worker.id"
          class="flex items-center justify-between gap-4 px-5 py-3 hover:bg-gray-50 transition"
        >
          <div class="flex items-center gap-3 min-w-0">
            <div class="w-9 h-9 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-sm shrink-0">
              {{ worker.name.charAt(0) }}
            </div>
            <div class="min-w-0">
              <div class="font-bold text-gray-800 truncate">{{ worker.name }}</div>
              <div class="text-xs text-gray-400" v-if="worker.phone">{{ worker.phone }}</div>
            </div>
          </div>

          <div class="flex items-center gap-4 shrink-0">
            <span class="text-xs text-gray-500">{{ worker.total_records ?? 0 }} عملية</span>
            <div v-if="workersFilter.stage" class="text-xs text-indigo-600 font-medium">
              {{ worker.filtered_records?.length ?? 0 }} بهذه المرحلة
            </div>

            <div class="flex items-center gap-1 shrink-0">
              <button @click="$emit('edit-worker', worker)" class="w-8 h-8 flex items-center justify-center rounded-lg text-gray-400 hover:bg-indigo-50 hover:text-indigo-600 transition">
                ✏️
              </button>
              <button @click="askDelete(worker)" class="w-8 h-8 flex items-center justify-center rounded-lg text-gray-400 hover:bg-red-50 hover:text-red-600 transition">
                🗑️
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- تأكيد حذف عامل -->
    <div v-if="pendingDelete" class="fixed inset-0 bg-black/60 flex items-center justify-center z-[70]">
      <div class="bg-white rounded-2xl p-8 max-w-md mx-4 shadow-2xl">
        <div class="text-4xl mb-4">⚠️</div>
        <p class="text-gray-800 text-lg mb-8">هل أنت متأكد من حذف العامل "<strong>{{ pendingDelete.name }}</strong>"؟</p>
        <div class="flex gap-3">
          <button @click="confirmDelete" class="flex-1 bg-red-600 text-white py-4 rounded-xl">نعم، احذف</button>
          <button @click="pendingDelete = null" class="flex-1 bg-gray-100 py-4 rounded-xl">إلغاء</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import SearchableSelect from '../../shared/SearchableSelect.vue'

const emit = defineEmits(['open-worker-modal', 'edit-worker', 'delete-worker'])

const props = defineProps({
  workersList: { type: Array, default: () => [] }
})

const workersFilter = ref({ stage: '' })
const pendingDelete = ref(null)

const stageOptions = [
  { label: 'تجميع الهيكل', value: 'تجميع_الهيكل' },
  { label: 'توصيل الكهرباء والغلاف', value: 'توصيل_الكهرباء_والغلاف' },
  { label: 'تجميع كامل', value: 'تجميع_كامل' },
]

const filteredWorkers = computed(() => {
  if (!workersFilter.value.stage) return props.workersList
  return props.workersList
    .map(w => ({
      ...w,
      filtered_records: (w.records || []).filter(r => r.stage === workersFilter.value.stage)
    }))
    .filter(w => w.filtered_records.length > 0)
})

const resetFilter = () => { workersFilter.value = { stage: '' } }

const askDelete = (worker) => { pendingDelete.value = worker }

const confirmDelete = () => {
  emit('delete-worker', pendingDelete.value.id)
  pendingDelete.value = null
}
</script>