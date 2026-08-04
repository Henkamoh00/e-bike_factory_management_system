<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-3xl font-bold">التجميع</h2>
      <button @click="showAssemblyModal = true" class="bg-emerald-600 hover:bg-emerald-700 text-white px-6 py-3 rounded-2xl font-medium">
        + تسجيل عملية تجميع
      </button>
    </div>

    <ChassisOverviewList ref="overviewRef" />

    <AssemblyFormModal
      v-if="showAssemblyModal"
      @close="showAssemblyModal = false"
      @success="handleAssemblySuccess"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import ChassisOverviewList from './ChassisOverviewList.vue'
import AssemblyFormModal from '../modals/AssemblyFormModal.vue'

const showAssemblyModal = ref(false)
const overviewRef = ref(null)

const handleAssemblySuccess = () => {
  showAssemblyModal.value = false
  overviewRef.value?.refresh?.()
}

defineExpose({
  refresh: () => overviewRef.value?.refresh?.()
})
</script>