<template>
  <div class="fixed inset-0 bg-black/60 flex items-center justify-center z-[70]">
    <div class="bg-white rounded-3xl shadow-2xl w-full max-w-sm mx-4 p-8">
      <div class="text-3xl mb-3">💰</div>
      <h3 class="text-xl font-bold mb-2 text-gray-800">إيداع رصيد للعميل</h3>
      <p class="text-sm text-gray-500 mb-6">{{ customerName }}</p>

      <label class="block text-sm font-medium text-gray-700 mb-2">المبلغ</label>
      <input
        v-model.number="amount"
        type="number"
        min="0"
        step="0.01"
        class="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-emerald-400 focus:outline-none mb-4"
      />

      <label class="block text-sm font-medium text-gray-700 mb-2">ملاحظات (اختياري)</label>
      <textarea
        v-model="notes"
        placeholder="سبب الإيداع..."
        class="w-full p-4 border-2 border-gray-200 rounded-2xl h-20 focus:border-emerald-400 focus:outline-none mb-4"
      ></textarea>

      <p v-if="error" class="text-sm text-red-600 mb-4">{{ error }}</p>

      <div class="flex gap-3">
        <button @click="$emit('close')" class="flex-1 py-3 rounded-2xl font-medium text-gray-600 hover:bg-gray-100">إلغاء</button>
        <button @click="confirm" :disabled="loading" class="flex-1 py-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-2xl font-bold">
          {{ loading ? 'جاري الإيداع...' : 'تأكيد الإيداع' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  customerName: { type: String, default: '' },
  loading: { type: Boolean, default: false }
})
const emit = defineEmits(['close', 'confirm'])

const amount = ref(null)
const notes = ref('')
const error = ref('')

const confirm = () => {
  if (!amount.value || amount.value <= 0) {
    error.value = 'يرجى إدخال مبلغ صحيح'
    return
  }
  error.value = ''
  emit('confirm', { amount: amount.value, notes: notes.value || null })
}
</script>