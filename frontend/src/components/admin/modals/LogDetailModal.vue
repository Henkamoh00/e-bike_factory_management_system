<template>
  <div class="fixed inset-0 bg-black/60 flex items-center justify-center z-[70]" @click.self="$emit('close')">
    <div class="bg-white rounded-3xl shadow-2xl w-full max-w-lg mx-4 max-h-[90vh] flex flex-col">
      <div class="p-8 overflow-y-auto flex-1">
        <div v-if="loading" class="text-center py-16 text-gray-400">جاري التحميل...</div>

        <template v-else-if="log">
          <div class="flex items-center gap-3 mb-6">
            <div class="w-12 h-12 rounded-2xl flex items-center justify-center text-2xl shrink-0" :class="actionBadgeClass(log.action)">
              {{ actionIcon(log.action) }}
            </div>
            <div class="min-w-0">
              <h3 class="text-xl font-bold text-gray-800">{{ actionLabel(log.action) }}</h3>
              <p class="text-sm text-gray-400">{{ entityLabel(log.entity_type) }} #{{ log.entity_id ?? '—' }}</p>
            </div>
          </div>

          <div class="space-y-4">
            <div class="p-4 bg-gray-50 rounded-2xl">
              <div class="text-xs text-gray-400 mb-1">الوصف</div>
              <div class="font-medium text-gray-800">{{ log.entity_label || '—' }}</div>
            </div>

            <div v-if="log.details" class="p-4 bg-gray-50 rounded-2xl">
              <div class="text-xs text-gray-400 mb-1">تفاصيل إضافية</div>
              <div class="text-gray-700 whitespace-pre-wrap">{{ log.details }}</div>
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div class="p-4 bg-gray-50 rounded-2xl">
                <div class="text-xs text-gray-400 mb-1">بواسطة</div>
                <div class="font-medium text-indigo-600">{{ log.user_full_name || log.username || 'النظام' }}</div>
              </div>
              <div class="p-4 bg-gray-50 rounded-2xl">
                <div class="text-xs text-gray-400 mb-1">التوقيت</div>
                <div class="font-medium text-gray-700">{{ new Date(log.timestamp).toLocaleString('ar-EG') }}</div>
              </div>
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div class="p-4 bg-gray-50 rounded-2xl">
                <div class="text-xs text-gray-400 mb-1">نوع العملية</div>
                <div class="font-mono text-sm text-gray-600">{{ log.action }}</div>
              </div>
              <div class="p-4 bg-gray-50 rounded-2xl">
                <div class="text-xs text-gray-400 mb-1">نوع العنصر</div>
                <div class="font-mono text-sm text-gray-600">{{ log.entity_type }}</div>
              </div>
            </div>

            <div class="p-4 bg-gray-50 rounded-2xl">
              <div class="text-xs text-gray-400 mb-1">رقم السجل</div>
              <div class="font-mono text-sm text-gray-600">#{{ log.id }}</div>
            </div>
          </div>
        </template>

        <div v-else class="text-center py-16 text-gray-400">تعذر تحميل تفاصيل السجل</div>
      </div>

      <div class="border-t p-4 shrink-0">
        <button @click="$emit('close')" class="w-full py-3 rounded-2xl font-medium text-gray-600 hover:bg-gray-100">
          إغلاق
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuth } from '../../../composables/useAuth'

const { apiFetch } = useAuth()

const props = defineProps({
  logId: { type: Number, required: true }
})
defineEmits(['close'])

const log = ref(null)
const loading = ref(true)

const actionLabels = {
  create: 'إنشاء', update: 'تعديل', delete: 'حذف', cancel: 'إلغاء',
  restore: 'استعادة', repair: 'تصليح', login: 'تسجيل دخول',
  bulk_delete: 'حذف جماعي', bulk_cancel: 'إلغاء جماعي', bulk_repair: 'تصليح جماعي',
  bulk_restore: 'استعادة جماعية', bulk_activate: 'تفعيل جماعي', bulk_deactivate: 'تعطيل جماعي'
}

// 🆕🛡️ نُظّفت من "sale" نهائيًا واستُبدلت بكيانات نظام الفوترة الفعلية
const entityLabels = {
  worker: 'عامل', customer: 'عميل', bike_type: 'نوع دراجة', bike_color: 'لون دراجة',
  assembly: 'تجميع', fault: 'عطل', fault_repair: 'تصليح عطل', user: 'مستخدم', role: 'دور',
  invoice: 'فاتورة', invoice_item: 'بند فاتورة', payment: 'دفعة', chassis_return: 'إرجاع دراجة'
}

const actionLabel = (a) => actionLabels[a] || a
const entityLabel = (e) => entityLabels[e] || e

const actionIcon = (a) => {
  if (a.includes('delete')) return '🗑️'
  if (a.includes('cancel')) return '❌'
  if (a.includes('restore')) return '♻️'
  if (a.includes('repair')) return '🔧'
  if (a === 'create') return '✅'
  if (a === 'update') return '✏️'
  if (a === 'login') return '🔑'
  if (a === 'bulk_activate') return '✅'
  if (a === 'bulk_deactivate') return '🚫'
  return '📌'
}
const actionBadgeClass = (a) => {
  if (a.includes('delete') || a.includes('cancel') || a === 'bulk_deactivate') return 'bg-red-100 text-red-600'
  if (a.includes('restore') || a === 'bulk_activate') return 'bg-emerald-100 text-emerald-600'
  if (a === 'create') return 'bg-indigo-100 text-indigo-600'
  return 'bg-amber-100 text-amber-600'
}

const loadDetail = async () => {
  loading.value = true
  try {
    const res = await apiFetch(`/api/logs/${props.logId}/`)
    if (res.ok) log.value = await res.json()
  } catch (e) {
    console.error('log detail', e)
  } finally {
    loading.value = false
  }
}

onMounted(loadDetail)
</script>