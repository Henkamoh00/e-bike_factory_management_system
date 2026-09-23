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
            <h2 class="text-lg sm:text-xl font-bold text-slate-900 truncate">📦 إدارة المخزون</h2>
            <p class="text-xs sm:text-sm text-slate-400 truncate">قطع الغيار وحركات الوارد والصادر</p>
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
            :class="activeSub === sub.id ? 'bg-indigo-50 text-indigo-700 font-semibold' : 'text-gray-500 hover:bg-gray-50'"
            class="px-4 py-2 rounded-xl text-sm transition"
          >
            {{ sub.icon }} {{ sub.label }}
          </button>
        </div>

        <PartsListView v-if="activeSub === 'parts'" />
        <StockLedgerView v-else-if="activeSub === 'ledger'" />
        <ReorderListView v-else-if="activeSub === 'reorder'" />

      </div>
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import PartsListView from '../components/inventory/PartsListView.vue'
import StockLedgerView from '../components/inventory/StockLedgerView.vue'
import ReorderListView from '../components/inventory/ReorderListView.vue'

const router = useRouter()

const subTabs = [
  { id: 'parts',   label: 'قائمة القطع',        icon: '🧩' },
  { id: 'ledger',  label: 'حركات المخزون',      icon: '📋' },
  { id: 'reorder', label: 'قطع تحتاج طلب',      icon: '🛒' },
]

const activeSub = ref('parts')

const goBack = () => {
  router.push({ name: 'Dashboard' })
}
</script>