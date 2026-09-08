<template>
  <div class="fixed inset-0 bg-black/60 flex items-center justify-center z-[70]" @click.self="$emit('close')">
    <div class="bg-white rounded-3xl shadow-2xl w-full max-w-2xl mx-4 max-h-[90vh] flex flex-col">
      <div class="p-8 overflow-y-auto flex-1">
        <div v-if="loading" class="text-center py-16 text-gray-400 text-lg">جاري التحميل...</div>

        <template v-else-if="statement">
          <div class="flex items-center gap-3 mb-6">
            <div class="w-14 h-14 rounded-2xl bg-purple-100 text-purple-700 flex items-center justify-center font-bold text-xl shrink-0">
              {{ statement.customer_name.charAt(0) }}
            </div>
            <div>
              <h2 class="text-xl font-bold text-gray-800">{{ statement.customer_name }}</h2>
              <p class="text-sm text-gray-400">كشف الحساب الكامل</p>
            </div>
          </div>

          <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
            <div class="bg-gray-50 rounded-2xl p-4 text-center">
              <div class="text-xs text-gray-400 mb-1">إجمالي الفواتير</div>
              <div class="text-lg font-bold text-gray-800">{{ Number(statement.total_invoiced).toFixed(2) }}</div>
            </div>
            <div class="bg-emerald-50 rounded-2xl p-4 text-center">
              <div class="text-xs text-gray-400 mb-1">إجمالي المدفوع</div>
              <div class="text-lg font-bold text-emerald-600">{{ Number(statement.total_paid).toFixed(2) }}</div>
            </div>
            <div class="rounded-2xl p-4 text-center" :class="Number(statement.total_remaining) > 0 ? 'bg-red-50' : 'bg-gray-50'">
              <div class="text-xs text-gray-400 mb-1">المتبقي (الدين)</div>
              <div class="text-lg font-bold" :class="Number(statement.total_remaining) > 0 ? 'text-red-600' : 'text-gray-400'">
                {{ Number(statement.total_remaining).toFixed(2) }}
              </div>
            </div>
            <!-- 🆕 كارد المبلغ القابل للاسترجاع الخاص بهذا العميل -->
            <div class="rounded-2xl p-4 text-center" :class="Number(statement.total_pending_refund) > 0 ? 'bg-amber-50' : 'bg-gray-50'">
              <div class="text-xs text-gray-400 mb-1">قابل للاسترجاع</div>
              <div class="text-lg font-bold" :class="Number(statement.total_pending_refund) > 0 ? 'text-amber-600' : 'text-gray-400'">
                {{ Number(statement.total_pending_refund).toFixed(2) }}
              </div>
            </div>
          </div>

          <h4 class="font-semibold text-sm text-gray-500 mb-3">الفواتير</h4>
          <div v-if="statement.invoices.length === 0" class="text-center py-10 text-gray-400 bg-gray-50 rounded-2xl">
            لا توجد فواتير لهذا العميل
          </div>
          <div v-else class="space-y-2">
            <div
              v-for="inv in statement.invoices"
              :key="inv.id"
              @click="$emit('open-invoice', inv)"
              class="flex items-center justify-between gap-3 p-3 bg-gray-50 hover:bg-gray-100 rounded-xl cursor-pointer transition"
            >
              <div class="flex items-center gap-2 min-w-0">
                <span class="text-lg shrink-0">{{ statusIcon(inv.status) }}</span>
                <div class="min-w-0">
                  <span class="font-mono font-bold text-gray-800 text-sm">{{ inv.invoice_number }}</span>
                  <div class="text-xs text-gray-400">{{ new Date(inv.invoice_date).toLocaleDateString('ar-EG') }}</div>
                </div>
              </div>
              <div class="text-left shrink-0">
                <div class="font-bold text-sm">{{ Number(inv.total_amount).toFixed(2) }}</div>
                <div v-if="Number(inv.remaining_amount) > 0" class="text-xs text-red-500">متبقي {{ Number(inv.remaining_amount).toFixed(2) }}</div>
              </div>
            </div>
          </div>
        </template>

        <div v-else class="text-center py-16 text-gray-400">تعذر تحميل كشف الحساب</div>
      </div>

      <div class="border-t p-4 shrink-0">
        <button @click="$emit('close')" class="w-full py-3 rounded-2xl font-medium text-gray-600 hover:bg-gray-100">إغلاق</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuth } from '../../composables/useAuth'

const { apiFetch } = useAuth()

const props = defineProps({
  customerId: { type: [Number, String], required: true }
})
defineEmits(['close', 'open-invoice'])

const statement = ref(null)
const loading = ref(false)

const statusIcon = (s) => ({ confirmed: '📄', partially_paid: '🟡', paid: '✅', cancelled: '✖️' }[s] || '📄')

const load = async () => {
  loading.value = true
  try {
    const res = await apiFetch(`/api/invoices/customers/${props.customerId}/statement/`)
    if (res.ok) statement.value = await res.json()
  } catch (e) {
    console.error('كشف حساب العميل', e)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>