<template>
  <div class="fixed inset-0 bg-black/60 flex items-center justify-center z-[70]" @click.self="$emit('close')">
    <div class="bg-white rounded-3xl shadow-2xl w-full max-w-2xl mx-4 max-h-[90vh] flex flex-col">
      <div class="p-8 overflow-y-auto flex-1">
        <div v-if="loading" class="text-center py-16 text-gray-400 text-lg">جاري التحميل...</div>

        <template v-else-if="statement">
          <div class="flex items-center justify-between gap-3 mb-6">
            <div class="flex items-center gap-3 min-w-0">
              <div class="w-14 h-14 rounded-2xl bg-purple-100 text-purple-700 flex items-center justify-center font-bold text-xl shrink-0">
                {{ statement.customer_name.charAt(0) }}
              </div>
              <div class="min-w-0">
                <h2 class="text-xl font-bold text-gray-800 truncate">{{ statement.customer_name }}</h2>
                <p class="text-sm text-gray-400">كشف الحساب الكامل</p>
              </div>
            </div>
            <!-- 🆕 فاتورة جديدة مباشرة لهذا العميل + عدد فواتيره -->
            <div class="flex flex-col items-end gap-1 shrink-0">
              <button
                @click="$emit('add-invoice', statement)"
                class="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-full font-medium text-xs"
              >
                + فاتورة جديدة
              </button>
              <span class="text-xs text-gray-400">{{ statement.invoices.length }} فاتورة نشطة</span>
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
            <div class="rounded-2xl p-4 text-center" :class="Number(statement.credit_balance) > 0 ? 'bg-indigo-50' : 'bg-gray-50'">
              <div class="text-xs text-gray-400 mb-1">رصيد العميل</div>
              <div class="text-lg font-bold" :class="Number(statement.credit_balance) > 0 ? 'text-indigo-600' : 'text-gray-400'">
                {{ Number(statement.credit_balance).toFixed(2) }}
              </div>
            </div>
          </div>

          <div class="mb-6">
            <div class="flex items-center justify-between mb-3">
              <h4 class="font-semibold text-sm text-gray-500">💰 رصيد العميل ومصادره</h4>
              <button
                @click="$emit('deposit-credit', statement)"
                class="text-xs bg-emerald-50 hover:bg-emerald-100 text-emerald-700 px-3 py-1.5 rounded-full font-medium"
              >
                + إيداع رصيد
              </button>
            </div>

            <div v-if="Number(statement.credit_balance) > 0" class="bg-indigo-50 rounded-2xl p-4 flex items-center justify-between gap-3 flex-wrap mb-3">
              <div>
                <div class="text-xs text-indigo-500 mb-1">الرصيد المتاح حاليًا</div>
                <div class="text-xl font-bold text-indigo-700">{{ Number(statement.credit_balance).toFixed(2) }}</div>
              </div>
              <div class="flex items-center gap-2">
                <button
                  @click="$emit('reallocate-credit', statement)"
                  class="text-xs bg-white hover:bg-indigo-100 text-indigo-600 px-3 py-2 rounded-full font-medium border border-indigo-200"
                >
                  🧾 تسديد فاتورة
                </button>
                <button
                  @click="$emit('refund-credit', statement)"
                  class="text-xs bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-2 rounded-full font-medium"
                >
                  ✅ استرجاع نقدي
                </button>
              </div>
            </div>

            <div v-if="ledgerPg.paginatedItems.value.length" class="space-y-1.5">
              <div
                v-for="entry in ledgerPg.paginatedItems.value"
                :key="entry.id"
                class="flex items-center justify-between gap-3 px-3 py-2 bg-gray-50 rounded-xl text-xs"
              >
                <div class="min-w-0">
                  <span class="font-medium" :class="Number(entry.amount) >= 0 ? 'text-emerald-600' : 'text-red-500'">
                    {{ Number(entry.amount) >= 0 ? '+' : '' }}{{ Number(entry.amount).toFixed(2) }}
                  </span>
                  <span class="text-gray-400 mr-2">{{ creditActionLabel(entry.action_type) }}</span>
                  <span v-if="entry.related_invoice_number" class="text-gray-400">— {{ entry.related_invoice_number }}</span>
                  <div v-if="entry.notes" class="text-gray-400 mt-0.5 truncate">{{ entry.notes }}</div>
                </div>
                <span class="text-gray-400 shrink-0">{{ new Date(entry.created_at).toLocaleDateString('ar-EG') }}</span>
              </div>

              <PaginationControls
                :page="ledgerPg.page.value"
                :total-pages="ledgerPg.totalPages.value"
                @prev="ledgerPg.prevPage"
                @next="ledgerPg.nextPage"
              />
            </div>
            <div v-else class="text-center py-6 text-gray-400 text-xs bg-gray-50 rounded-2xl">
              لا توجد حركات على الرصيد بعد
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
import { ref, computed, onMounted } from 'vue'
import { useAuth } from '../../composables/useAuth'
import { usePagination } from '../../composables/usePagination'
import PaginationControls from '../shared/PaginationControls.vue'

const { apiFetch } = useAuth()

const props = defineProps({
  customerId: { type: [Number, String], required: true }
})
defineEmits(['close', 'open-invoice', 'deposit-credit', 'reallocate-credit', 'refund-credit', 'add-invoice'])

const statement = ref(null)
const loading = ref(false)

const statusIcon = (s) => ({ confirmed: '📄', partially_paid: '🟡', paid: '✅', cancelled: '✖️' }[s] || '📄')

const creditActionLabels = {
  deposit: 'إيداع يدوي',
  manual_adjust: 'تعديل يدوي',
  from_cancel: 'فائض من إلغاء فاتورة',
  from_return: 'فائض من إرجاع دراجة',
  from_adjustment: 'فائض من تعديل الفاتورة',
  used_on_invoice: 'تسديد فاتورة',
  deposit_excess_payment: 'فائض دفعة نقدية',
  refunded: 'استرجاع نقدي',
  reallocated: 'تسديد فاتورة', // توافق مع سجلات قديمة قبل توحيد التسمية
}
const creditActionLabel = (t) => creditActionLabels[t] || t

// 🆕 باجينيشن (10 بكل صفحة) لسجل حركات الرصيد كي لا تطول القائمة داخل المودال
const creditLedgerItems = computed(() => statement.value?.credit_ledger || [])
const ledgerPg = usePagination(creditLedgerItems, 10)

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

defineExpose({ reload: load })

onMounted(load)
</script>