<template>
  <div v-if="totalPages > 1" class="flex justify-center items-center gap-3 mt-6">
    <button @click="$emit('prev')" :disabled="page === 1" class="px-4 py-2 rounded-xl bg-white shadow disabled:opacity-40 text-sm">السابق</button>
    <span class="text-sm text-gray-500">صفحة {{ page }} من {{ totalPages }}</span>
    <button @click="$emit('next')" :disabled="page === totalPages" class="px-4 py-2 rounded-xl bg-white shadow disabled:opacity-40 text-sm">التالي</button>
  </div>
</template>

<script setup>
defineProps({
  page: { type: Number, required: true },
  totalPages: { type: Number, required: true }
})
defineEmits(['prev', 'next'])
</script>