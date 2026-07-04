<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-3xl font-bold">الأعطال</h2>
      <button @click="$emit('open-fault-modal')" class="bg-red-600 hover:bg-red-700 text-white px-6 py-3 rounded-2xl font-medium">
        + تسجيل عطل جديد
      </button>
    </div>

    <!-- فلاتر الأعطال -->
    <div class="bg-white rounded-2xl shadow p-5 mb-6 flex flex-wrap gap-4 items-end">
      <div>
        <SearchableSelect
          v-model="faultsFilter.status"
          :options="statusOptions"
          label="تصفية بالحالة"
          empty-label="كل الحالات"
        />
      </div>
      <div>
        <SearchableSelect
          v-model="faultsFilter.worker_name"
          :options="workerOptions"
          label="تصفية بالعامل"
          empty-label="كل العمال"
        />
      </div>
      <button @click="resetFilter" class="px-4 py-2 text-gray-500 hover:text-gray-700 underline text-sm">إعادة تعيين</button>
    </div>

    <div class="bg-white rounded-3xl shadow-xl p-6">
      <div v-if="filteredFaults.length === 0" class="text-center py-16 text-gray-400 text-lg">لا توجد أعطال مطابقة</div>
      <div v-else class="space-y-4">
        <div v-for="fault in filteredFaults" :key="fault.id" class="bg-gray-50 p-5 rounded-2xl flex justify-between items-center">
          <div>
            <div class="font-mono font-bold">{{ fault.chassis_number }}</div>
            <div class="text-sm text-gray-500">العامل: {{ fault.worker_name || 'غير معروف' }}</div>
            <div class="text-gray-600">{{ fault.description }}</div>
          </div>
          <div class="text-right">
            <span :class="fault.status === 'pending' ? 'text-red-600' : 'text-emerald-600'" class="font-medium">
              {{ fault.status === 'pending' ? 'معلق' : 'تم إصلاحه' }}
            </span>
            <div class="text-xs text-gray-500 mt-1">{{ new Date(fault.reported_date).toLocaleDateString('ar-EG') }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import SearchableSelect from '../../shared/SearchableSelect.vue'

defineEmits(['open-fault-modal'])

const props = defineProps({
  faultsList: { type: Array, default: () => [] },
  workersList: { type: Array, default: () => [] }
})

const faultsFilter = ref({ status: '', worker_name: '' })

const statusOptions = [
  { label: 'معلق', value: 'pending' },
  { label: 'تم إصلاحه', value: 'resolved' },
]

const workerOptions = computed(() =>
  props.workersList.map(w => ({ label: w.name, value: w.name }))
)

const filteredFaults = computed(() => {
  return props.faultsList.filter(f => {
    if (faultsFilter.value.status && f.status !== faultsFilter.value.status) return false
    if (faultsFilter.value.worker_name && f.worker_name !== faultsFilter.value.worker_name) return false
    return true
  })
})

const resetFilter = () => { faultsFilter.value = { status: '', worker_name: '' } }
</script>