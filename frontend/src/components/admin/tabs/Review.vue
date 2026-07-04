<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-2xl font-bold text-gray-800">بحث عن دراجة</h2>
    </div>

    <ChassisOverviewList
      ref="overviewRef"
      summary-endpoint="http://localhost:8000/api/admin/chassis/summary"
      history-endpoint="http://localhost:8000/api/workshop/history"
    />
  </div>
</template>

<script setup>
import ChassisOverviewList from '../../shared/ChassisOverviewList.vue'
</script>