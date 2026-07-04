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

    <div class="bg-white rounded-3xl shadow-xl p-6">
      <div v-if="filteredWorkers.length === 0" class="text-center py-16 text-gray-400 text-lg">لا يوجد عمال مطابقون</div>
      <div v-else class="space-y-4">
        <div v-for="worker in filteredWorkers" :key="worker.id" class="bg-gray-50 p-5 rounded-2xl">
          <div class="flex justify-between items-start">
            <div>
              <div class="font-bold text-lg">{{ worker.name }}</div>
              <div class="text-sm text-gray-500 mt-1">إجمالي العمليات: {{ worker.total_records ?? 0 }}</div>
            </div>
            <div class="text-right text-sm text-gray-500">
              <div v-if="worker.stages_summary">
                <span v-for="(count, stage) in worker.stages_summary" :key="stage"
                  class="inline-block bg-indigo-100 text-indigo-700 rounded-full px-3 py-1 text-xs ml-1 mb-1">
                  {{ getStageName(stage) }}: {{ count }}
                </span>
              </div>
            </div>
          </div>
          <div v-if="workersFilter.stage && worker.filtered_records?.length" class="mt-4 space-y-2">
            <div v-for="rec in worker.filtered_records" :key="rec.id"
              class="flex justify-between items-center bg-white px-4 py-3 rounded-xl border border-gray-200">
              <span class="font-mono text-sm">{{ rec.chassis_number }}</span>
              <span class="text-xs text-gray-500">{{ new Date(rec.timestamp).toLocaleString('ar-EG') }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import SearchableSelect from '../../shared/SearchableSelect.vue'

defineEmits(['open-worker-modal'])

const props = defineProps({
  workersList: { type: Array, default: () => [] }
})

const workersFilter = ref({ stage: '' })

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

const getStageName = (stage) => {
  const names = {
    'تجميع_الهيكل':           'تجميع الهيكل',
    'توصيل_الكهرباء_والغلاف': 'توصيل الكهرباء والغلاف',
    'تجميع_كامل':             'تجميع كامل',
  }
  return names[stage] || stage
}
</script>