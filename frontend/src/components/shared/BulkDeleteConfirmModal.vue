<template>
  <div class="fixed inset-0 bg-black/60 flex items-center justify-center z-[70]">
    <div class="bg-white rounded-2xl p-8 max-w-md mx-4 shadow-2xl">
      <div class="text-4xl mb-4">⚠️</div>
      <p class="text-gray-800 text-lg mb-8">{{ message }}</p>
      <div class="flex gap-3">
        <button @click="$emit('confirm')" :disabled="loading" class="flex-1 bg-red-600 text-white py-4 rounded-xl">
          {{ loading ? 'جاري الحذف...' : 'نعم، احذف' }}
        </button>
        <button @click="$emit('close')" class="flex-1 bg-gray-100 py-4 rounded-xl">إلغاء</button>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  message: { type: String, default: 'هل أنت متأكد؟' },
  loading: { type: Boolean, default: false }
})
defineEmits(['close', 'confirm'])
</script>