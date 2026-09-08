<template>
  <div class="fixed inset-0 bg-black/60 flex items-center justify-center z-[70]">
    <div class="bg-white rounded-3xl shadow-2xl w-full max-w-md mx-4 max-h-[90vh] flex flex-col">
      <div class="p-8 overflow-y-auto flex-1">
        <div class="text-3xl mb-3">{{ icon }}</div>
        <h2 class="text-xl font-bold mb-2 text-gray-800">{{ title }}</h2>
        <p class="text-sm text-gray-500 mb-6">{{ subtitle }}</p>

        <label class="block text-sm font-medium text-gray-700 mb-2">سبب الإلغاء</label>
        <textarea
          v-model="reason"
          :disabled="noReason"
          placeholder="اكتب سبب الإلغاء..."
          class="w-full p-4 border-2 border-gray-200 rounded-2xl h-24 focus:border-red-400 focus:outline-none disabled:bg-gray-50 disabled:text-gray-400"
        ></textarea>

        <label class="flex items-center gap-2 mt-3 cursor-pointer select-none">
          <input type="checkbox" v-model="noReason" class="w-4 h-4 accent-red-600" />
          <span class="text-sm text-gray-600">لا يوجد سبب محدد، متابعة الإلغاء بدون كتابة سبب</span>
        </label>

        <!-- 🆕 تأكيد إضافي اختياري (مثال: رد مبلغ مدفوع للعميل عند إلغاء فاتورة) -->
        <label v-if="requireExtraConfirm" class="flex items-start gap-2 mt-4 p-3 bg-amber-50 rounded-xl cursor-pointer select-none">
          <input type="checkbox" v-model="extraConfirmed" class="w-4 h-4 accent-amber-600 mt-0.5" />
          <span class="text-sm text-amber-700">{{ extraConfirmText }}</span>
        </label>

        <p v-if="error" class="text-sm text-red-600 mt-3">{{ error }}</p>
      </div>

      <div class="border-t p-4 flex gap-3 shrink-0">
        <button @click="$emit('close')" class="flex-1 py-4 rounded-2xl font-medium text-gray-600 hover:bg-gray-100">
          تراجع
        </button>
        <button
          @click="confirm"
          :disabled="loading"
          class="flex-1 py-4 bg-red-600 hover:bg-red-700 text-white rounded-2xl font-bold"
        >
          {{ loading ? 'جاري الإلغاء...' : 'تأكيد الإلغاء' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  title: { type: String, default: 'تأكيد الإلغاء' },
  subtitle: { type: String, default: '' },
  icon: { type: String, default: '⚠️' },
  loading: { type: Boolean, default: false },
  // 🆕 تأكيد إضافي اختياري لا علاقة له بسبب الإلغاء (مثال: تأكيد رد مبلغ)
  requireExtraConfirm: { type: Boolean, default: false },
  extraConfirmText: { type: String, default: '' }
})

const emit = defineEmits(['close', 'confirm'])

const reason = ref('')
const noReason = ref(false)
const extraConfirmed = ref(false)
const error = ref('')

const confirm = () => {
  const trimmed = reason.value.trim()
  if (!trimmed && !noReason.value) {
    error.value = 'يرجى كتابة سبب الإلغاء، أو تفعيل الخيار أدناه للمتابعة بدون سبب'
    return
  }
  if (props.requireExtraConfirm && !extraConfirmed.value) {
    error.value = 'يرجى تأكيد الخيار الإضافي أعلاه للمتابعة'
    return
  }
  error.value = ''
  const payload = { reason: trimmed, confirm_no_reason: noReason.value }
  if (props.requireExtraConfirm) {
    payload.confirm_extra = true
  }
  emit('confirm', payload)
}
</script>