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
        <label class="block text-sm text-gray-500 mb-1">بحث برقم الهيكل</label>
        <input
          v-model="faultsFilter.chassis_number"
          type="text"
          placeholder="EB-2026-..."
          class="px-4 py-2 border-2 border-gray-200 rounded-xl focus:border-indigo-400 focus:outline-none font-mono"
        />
      </div>
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
          v-model="faultsFilter.repaired_by"
          :options="workerOptions"
          label="تصفية بالعامل (المصلّح)"
          empty-label="كل العمال"
        />
      </div>
      <div>
        <SearchableSelect
          v-model="faultsFilter.responsible_worker"
          :options="workerOptions"
          label="تصفية بالعامل المتسبب في العطل"
          empty-label="كل العمال"
        />
      </div>
      <button @click="resetFilter" class="px-4 py-2 text-gray-500 hover:text-gray-700 underline text-sm">إعادة تعيين</button>
    </div>

    <div class="bg-white rounded-3xl shadow-xl p-6">
      <div v-if="filteredFaults.length === 0" class="text-center py-16 text-gray-400 text-lg">لا توجد أعطال مطابقة</div>
      <div v-else class="space-y-4">
        <div v-for="fault in filteredFaults" :key="fault.id" class="bg-gray-50 p-5 rounded-2xl">
          <div class="flex justify-between items-start">
            <div>
              <div class="font-mono font-bold">{{ fault.chassis_number }}</div>
              <div v-if="fault.related_stage" class="text-xs text-gray-400 mt-0.5">
                المرحلة: {{ getStageName(fault.related_stage) }}
                <span v-if="fault.responsible_worker_name"> — بواسطة: {{ fault.responsible_worker_name }}</span>
              </div>
              <div class="text-gray-600 mt-1">{{ fault.description }}</div>
            </div>
            <div class="text-right shrink-0">
              <span :class="fault.status === 'pending' ? 'text-red-600' : 'text-emerald-600'" class="font-medium">
                {{ fault.status === 'pending' ? 'معلق' : 'تم إصلاحه' }}
              </span>
              <div class="text-xs text-gray-500 mt-1">{{ new Date(fault.reported_date).toLocaleDateString('ar-EG') }}</div>
              <button
                v-if="fault.status === 'pending'"
                @click="openRepairModal(fault)"
                class="mt-2 text-xs bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-1.5 rounded-full font-medium"
              >
                ✅ تسجيل تصليح
              </button>
            </div>
          </div>

          <!-- تاريخ التصليحات -->
          <div v-if="fault.repairs?.length" class="mt-4 pt-4 border-t border-gray-200 space-y-2">
            <div v-for="repair in fault.repairs" :key="repair.id" class="flex justify-between items-center bg-white px-4 py-3 rounded-xl border border-gray-200">
              <div>
                <span class="text-sm font-medium text-emerald-700">🔧 {{ repair.worker_name }}</span>
                <span v-if="repair.notes" class="text-xs text-gray-500 block mt-1">{{ repair.notes }}</span>
              </div>
              <span class="text-xs text-gray-400 shrink-0">{{ new Date(repair.repair_date).toLocaleString('ar-EG') }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <FaultRepairModal
      v-if="repairingFault"
      :fault="repairingFault"
      :workers-list="workersList"
      @close="repairingFault = null"
      @success="handleRepairSuccess"
    />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import SearchableSelect from '../../shared/SearchableSelect.vue'
import FaultRepairModal from '../modals/FaultRepairModal.vue'

const emit = defineEmits(['open-fault-modal', 'refresh-faults'])

const props = defineProps({
  faultsList: { type: Array, default: () => [] },
  workersList: { type: Array, default: () => [] }
})

const faultsFilter = ref({
  chassis_number: '',
  status: '',
  repaired_by: '',
  responsible_worker: ''
})
const repairingFault = ref(null)

const statusOptions = [
  { label: 'معلق', value: 'pending' },
  { label: 'تم إصلاحه', value: 'fixed' },
]

const workerOptions = computed(() =>
  props.workersList.map(w => ({ label: w.name, value: w.name }))
)

const filteredFaults = computed(() => {
  return props.faultsList.filter(f => {
    if (faultsFilter.value.chassis_number && !f.chassis_number.toLowerCase().includes(faultsFilter.value.chassis_number.toLowerCase())) return false
    if (faultsFilter.value.status && f.status !== faultsFilter.value.status) return false
    if (faultsFilter.value.repaired_by && !(f.repairs || []).some(r => r.worker_name === faultsFilter.value.repaired_by)) return false
    if (faultsFilter.value.responsible_worker && f.responsible_worker_name !== faultsFilter.value.responsible_worker) return false
    return true
  })
})

const resetFilter = () => {
  faultsFilter.value = { chassis_number: '', status: '', repaired_by: '', responsible_worker: '' }
}

const getStageName = (stage) => {
  const names = {
    'تجميع_الهيكل':           'تجميع الهيكل',
    'توصيل_الكهرباء_والغلاف': 'توصيل الكهرباء والغلاف',
    'تجميع_كامل':             'تجميع كامل',
  }
  return names[stage] || stage
}

const openRepairModal = (fault) => { repairingFault.value = fault }

const handleRepairSuccess = () => {
  repairingFault.value = null
  emit('refresh-faults')
}
</script>