<template>
  <div class="min-h-screen bg-slate-50 font-sans" dir="rtl">
    <header class="bg-white/80 backdrop-blur border-b border-slate-200 sticky top-0 z-30">
      <div class="px-4 sm:px-6 lg:px-8 py-4 sm:py-5 flex items-center justify-between gap-3">
        <div class="flex items-center gap-3 min-w-0">
          <button
            @click="goBack"
            class="shrink-0 w-10 h-10 flex items-center justify-center rounded-xl bg-slate-100 text-slate-600 hover:bg-slate-200 transition-colors duration-200"
            aria-label="العودة للوحة الإدارة"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
            </svg>
          </button>

          <div class="min-w-0">
            <h2 class="text-lg sm:text-xl font-bold text-slate-900 truncate">🧾 نظام الفواتير</h2>
            <p class="text-xs sm:text-sm text-slate-400 truncate">إدارة الفواتير والمدفوعات وكشوف الحسابات</p>
          </div>
        </div>
      </div>
    </header>

    <main class="p-4 sm:p-6 lg:p-8 max-w-6xl mx-auto">
      <div class="bg-white rounded-xl sm:rounded-2xl border border-slate-200 shadow-sm p-4 sm:p-6 lg:p-8">

        <div class="flex gap-2 mb-6 border-b border-gray-100 pb-4 flex-wrap">
          <button
            v-for="sub in subTabs"
            :key="sub.id"
            @click="activeSub = sub.id"
            :class="activeSub === sub.id ? 'bg-emerald-50 text-emerald-700 font-semibold' : 'text-gray-500 hover:bg-gray-50'"
            class="px-4 py-2 rounded-xl text-sm transition"
          >
            {{ sub.icon }} {{ sub.label }}
          </button>
        </div>

        <InvoicesListView v-if="activeSub === 'list'" />
        <CustomerStatementView v-else-if="activeSub === 'statement'" />
        <InvoiceStatsView v-else-if="activeSub === 'stats'" />
        <PendingRefundsView v-else-if="activeSub === 'refunds'" />
        <PostSaleTrackingView v-else-if="activeSub === 'post_sale'" />

      </div>
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import InvoicesListView from '../components/invoicing/InvoicesListView.vue'
import CustomerStatementView from '../components/invoicing/CustomerStatementView.vue'
import InvoiceStatsView from '../components/invoicing/InvoiceStatsView.vue'
import PendingRefundsView from '../components/invoicing/PendingRefundsView.vue'
import PostSaleTrackingView from '../components/invoicing/PostSaleTrackingView.vue'

const router = useRouter()

const subTabs = [
  { id: 'list',       label: 'قائمة الفواتير',   icon: '🧾' },
  { id: 'statement',  label: 'كشف حساب عميل',   icon: '📋' },
  { id: 'stats',      label: 'الإحصائيات',       icon: '📊' },
  // 🆕 تم إلغاء "المدفوعات المعلقة" نهائيًا لصالح سجل الاسترجاعات النقدية
  // الفعلية فقط (الخارجة حقًا من النظام)، عبر رصيد كل عميل
  { id: 'refunds',    label: 'الاسترجاعات',      icon: '💸' },
  { id: 'post_sale',  label: 'متابعة ما بعد البيع', icon: '🔄' },
]

const activeSub = ref('list')

const goBack = () => {
  router.push({ name: 'Dashboard' })
}
</script>