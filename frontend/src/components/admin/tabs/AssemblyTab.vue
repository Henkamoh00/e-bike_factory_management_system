<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-3xl font-bold">التجميع</h2>
      <button @click="$emit('open-assembly-modal')" class="bg-emerald-600 hover:bg-emerald-700 text-white px-6 py-3 rounded-2xl font-medium">
        + تسجيل عملية تجميع
      </button>
    </div>

    <ChassisOverviewList
      ref="overviewRef"
      :workers-list="workersList"
      :bike-types-list="bikeTypesList"
      :bike-colors-list="bikeColorsList"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import ChassisOverviewList from './ChassisOverviewList.vue'

defineEmits(['open-assembly-modal'])

const props = defineProps({
  workersList: { type: Array, default: () => [] },
  bikeTypesList: { type: Array, default: () => [] },
  bikeColorsList: { type: Array, default: () => [] }
})

const overviewRef = ref(null)

defineExpose({
  refresh: () => overviewRef.value?.loadChassisSummary()
})
</script>