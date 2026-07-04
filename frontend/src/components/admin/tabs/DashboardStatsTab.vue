<template>
  <div>
    <h2 class="text-3xl font-bold mb-8">الإحصائيات العامة</h2>
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <div class="bg-white rounded-3xl shadow p-8 text-center hover:shadow-xl transition">
        <div class="text-6xl mb-6">🚲</div>
        <div class="text-5xl font-bold text-blue-600">{{ stats.total_chassis }}</div>
        <div class="text-gray-500 text-lg">إجمالي الهياكل</div>
      </div>
      <div class="bg-white rounded-3xl shadow p-8 text-center hover:shadow-xl transition">
        <div class="text-6xl mb-6">🏁</div>
        <div class="text-5xl font-bold text-emerald-600">{{ stats.completed }}</div>
        <div class="text-gray-500 text-lg">مكتمل التجميع</div>
      </div>
      <div class="bg-white rounded-3xl shadow p-8 text-center hover:shadow-xl transition">
        <div class="text-6xl mb-6">⚙️</div>
        <div class="text-5xl font-bold text-amber-600">{{ stats.in_progress }}</div>
        <div class="text-gray-500 text-lg">قيد التجميع</div>
      </div>
      <div class="bg-white rounded-3xl shadow p-8 text-center hover:shadow-xl transition">
        <div class="text-6xl mb-6">💰</div>
        <div class="text-5xl font-bold text-purple-600">{{ stats.sold }}</div>
        <div class="text-gray-500 text-lg">تم بيعها</div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  stats: {
    type: Object,
    default: () => ({ total_chassis: 0, completed: 0, in_progress: 0, sold: 0 })
  }
})
</script>