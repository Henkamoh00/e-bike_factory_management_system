<template>
  <div class="fixed inset-0 bg-black/60 flex items-center justify-center z-[75]">
    <div class="bg-white rounded-3xl shadow-2xl w-full max-w-sm mx-4 p-8">
      <div class="text-3xl mb-3">✅</div>
      <h3 class="text-xl font-bold mb-2 text-gray-800">تأكيد استرجاع المبلغ</h3>
      <p class="text-sm text-gray-500 mb-6">
        الفاتورة: <span class="font-mono font-bold">{{ invoice.invoice_number }}</span> — العميل: {{ invoice.customer_name }}
      </p>

      <label class="block text-sm font-medium text-gray-700 mb-2">المبلغ المُسترجَع فعليًا</label>
      <input
        v-model.number="amount"
        type="number"
        min="0"
        :max="Number(invoice.remaining_unprocessed)"
        step="0.01"
        class="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-emerald-400 focus:outline-none mb-1"
      />
      <p class="text-xs text-gray-400 mb-6">
        الحد الأقصى: {{ Number(invoice.remaining_unprocessed).toFixed(2) }} — يمكنك إدخال مبلغ أقل إن كان الاسترجاع جزئيًا
      </p>

      <p v-if="error" class="text-sm text-red-600 mb-4">{{ error }}</p>

      <div class="flex gap-3">
        <button @click="$emit('close')" class="flex-1 py-3 rounded-2xl font-medium text-gray-600 hover:bg-gray-100">تراجع</button>
        <button @click="confirm" :disabled="loading" class="flex-1 py-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-2xl font-bold">
          {{ loading ? 'جاري التأكيد...' : 'تأكيد الاسترجاع' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  invoice: { type: Object, required: true },
  loading: { type: Boolean, default: false }
})
const emit = defineEmits(['close', 'confirm'])

const amount = ref(Number(props.invoice.remaining_unprocessed))
const error = ref('')

const confirm = () => {
  if (!amount.value || amount.value <= 0) {
    error.value = 'يرجى إدخال مبلغ صحيح'
    return
  }
  if (amount.value > Number(props.invoice.remaining_unprocessed)) {
    error.value = 'المبلغ أكبر من المتبقي غير المُعالَج'
    return
  }
  error.value = ''
  emit('confirm', amount.value)
}
</script>