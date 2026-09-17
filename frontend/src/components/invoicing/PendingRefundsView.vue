<template>
  <div>
    <h2 class="text-2xl font-bold mb-2">💸 سجل الاسترجاعات النقدية</h2>
    <p class="text-sm text-gray-500 mb-6">
      يعرض هذا السجل فقط عمليات الاسترجاع النقدي الحقيقية التي خرجت فعليًا من
      النظام وعادت لصاحبها (زر "استرجاع نقدي" من رصيد أي عميل). فوائض إلغاء
      الفواتير أو إرجاع الدراجات لا تظهر هنا لأنها لم تخرج من النظام بعد —
      تبقى كرصيد قابل للاستخدام، وتظهر ضمن سجل حركات الرصيد في كشف حساب كل عميل.
    </p>

    <div v-if="loading" class="text-center py-16 text-gray-400 text-lg">جاري التحميل...</div>
    <div v-else-if="items.length === 0" class="text-center py-16 text-gray-400 text-lg bg-white rounded-2xl shadow">
      لا توجد أي عمليات استرجاع نقدي مسجَّلة بعد
    </div>

    <div v-else class="bg-white rounded-3xl shadow-xl divide-y divide-gray-100">
      <div v-for="item in items" :key="item.id" class="flex items-center justify-between gap-4 px-5 py-4 flex-wrap">
        <div class="min-w-0">
          <div class="font-bold text-gray-800">{{ item.customer_name }}</div>
          <div v-if="item.notes" class="text-xs text-gray-400 mt-1">{{ item.notes }}</div>
          <div class="text-xs text-gray-400 mt-1" v-if="item.created_by_username">بواسطة: {{ item.created_by_username }}</div>
        </div>
        <div class="text-left shrink-0">
          <div class="font-bold text-lg text-emerald-600">{{ Number(item.amount).toFixed(2) }}</div>
          <div class="text-xs text-gray-400">{{ new Date(item.created_at).toLocaleDateString('ar-EG') }}</div>
        </div>
      </div>
    </div>

    <div v-if="totalPages > 1" class="flex justify-center items-center gap-3 mt-6">
      <button @click="prevPage" :disabled="page === 1" class="px-4 py-2 rounded-xl bg-white shadow disabled:opacity-40 text-sm">السابق</button>
      <span class="text-sm text-gray-500">صفحة {{ page }} من {{ totalPages }}</span>
      <button @click="nextPage" :disabled="page === totalPages" class="px-4 py-2 rounded-xl bg-white shadow disabled:opacity-40 text-sm">التالي</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuth } from '../../composables/useAuth'

const { apiFetch } = useAuth()

const items = ref([])
const total = ref(0)
const loading = ref(false)
const page = ref(1)
const pageSize = 20

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

const load = async () => {
  loading.value = true
  try {
    const params = new URLSearchParams({ skip: (page.value - 1) * pageSize, limit: pageSize })
    const res = await apiFetch(`/api/invoices/credit-refunds/?${params.toString()}`)
    if (res.ok) {
      const data = await res.json()
      items.value = data.items
      total.value = data.total
    }
  } catch (e) {
    console.error('سجل الاسترجاعات', e)
  } finally {
    loading.value = false
  }
}

const prevPage = () => { if (page.value > 1) { page.value--; load() } }
const nextPage = () => { if (page.value < totalPages.value) { page.value++; load() } }

onMounted(load)
</script>