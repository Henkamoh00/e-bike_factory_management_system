<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <div>
        <h2 class="text-2xl font-bold text-gray-800">📊 لوحة إحصائيات الفواتير</h2>
        <p class="text-sm text-gray-400 mt-1">نظرة شاملة على أداء المبيعات والتحصيل المالي</p>
      </div>
    </div>

    <div v-if="loading" class="text-center py-16 text-gray-400 text-lg">جاري التحميل...</div>

    <div v-else-if="stats">
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <div class="relative overflow-hidden rounded-2xl p-5 bg-gradient-to-br from-indigo-500 to-indigo-600 text-white shadow-lg shadow-indigo-200">
          <div class="text-3xl mb-2 opacity-80">📅</div>
          <div class="text-xs opacity-80 mb-1">اليوم</div>
          <div class="text-2xl font-bold">{{ Number(stats.today_revenue).toFixed(0) }}</div>
          <div class="text-xs opacity-70 mt-1">{{ stats.today_count }} فاتورة</div>
        </div>
        <div class="relative overflow-hidden rounded-2xl p-5 bg-gradient-to-br from-purple-500 to-purple-600 text-white shadow-lg shadow-purple-200">
          <div class="text-3xl mb-2 opacity-80">🗓️</div>
          <div class="text-xs opacity-80 mb-1">هذا الأسبوع</div>
          <div class="text-2xl font-bold">{{ Number(stats.week_revenue).toFixed(0) }}</div>
          <div class="text-xs opacity-70 mt-1">{{ stats.week_count }} فاتورة</div>
        </div>
        <div class="relative overflow-hidden rounded-2xl p-5 bg-gradient-to-br from-emerald-500 to-emerald-600 text-white shadow-lg shadow-emerald-200">
          <div class="text-3xl mb-2 opacity-80">📆</div>
          <div class="text-xs opacity-80 mb-1">هذا الشهر</div>
          <div class="text-2xl font-bold">{{ Number(stats.month_revenue).toFixed(0) }}</div>
          <div class="text-xs opacity-70 mt-1">{{ stats.month_count }} فاتورة</div>
        </div>
        <div class="relative overflow-hidden rounded-2xl p-5 bg-gradient-to-br from-amber-500 to-amber-600 text-white shadow-lg shadow-amber-200">
          <div class="text-3xl mb-2 opacity-80">📈</div>
          <div class="text-xs opacity-80 mb-1">هذه السنة</div>
          <div class="text-2xl font-bold">{{ Number(stats.year_revenue).toFixed(0) }}</div>
          <div class="text-xs opacity-70 mt-1">{{ stats.year_count }} فاتورة</div>
        </div>
      </div>

      <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 mb-8">
        <h3 class="font-bold text-gray-700 mb-5">الأداء المالي الإجمالي (كل الفترات)</h3>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div class="bg-gray-50 rounded-2xl p-5">
            <div class="flex items-center gap-2 text-xs text-gray-400 mb-2">
              <span class="w-2 h-2 rounded-full bg-gray-400"></span> إجمالي المفوتر
            </div>
            <div class="text-2xl font-bold text-gray-800">{{ Number(stats.total_billed).toFixed(2) }}</div>
          </div>
          <div class="bg-emerald-50 rounded-2xl p-5">
            <div class="flex items-center gap-2 text-xs text-emerald-500 mb-2">
              <span class="w-2 h-2 rounded-full bg-emerald-500"></span> صافي المحصَّل
            </div>
            <div class="text-2xl font-bold text-emerald-600">{{ Number(stats.total_collected).toFixed(2) }}</div>
          </div>
          <div class="bg-red-50 rounded-2xl p-5">
            <div class="flex items-center gap-2 text-xs text-red-400 mb-2">
              <span class="w-2 h-2 rounded-full bg-red-400"></span> المتبقي (الديون)
            </div>
            <div class="text-2xl font-bold text-red-600">{{ Number(stats.total_outstanding).toFixed(2) }}</div>
          </div>
        </div>

        <!-- 🆕 صف يضم: المسترجَع، مجموع الأرصدة، الإجمالي الشامل -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div class="bg-amber-50 rounded-2xl p-5">
            <div class="flex items-center gap-2 text-xs text-amber-600 mb-2">
              <span class="w-2 h-2 rounded-full bg-amber-500"></span> إجمالي المسترجَع للعملاء
            </div>
            <div class="text-2xl font-bold text-amber-600">{{ Number(stats.total_refunded).toFixed(2) }}</div>
          </div>
          <div class="bg-purple-50 rounded-2xl p-5">
            <div class="flex items-center gap-2 text-xs text-purple-600 mb-2">
              <span class="w-2 h-2 rounded-full bg-purple-500"></span> مجموع الأرصدة
            </div>
            <div class="text-2xl font-bold text-purple-600">{{ Number(stats.total_credit_balance ?? 0).toFixed(2) }}</div>
            <div class="text-xs text-purple-400 mt-1">رصيد كل العملاء الحاليين مجتمعًا</div>
          </div>
          <div class="bg-indigo-50 rounded-2xl p-5">
            <div class="flex items-center gap-2 text-xs text-indigo-500 mb-2">
              <span class="w-2 h-2 rounded-full bg-indigo-500"></span> الإجمالي الشامل (كل ما دخل الصندوق)
            </div>
            <div class="text-2xl font-bold text-indigo-600">{{ Number(stats.total_gross_collected).toFixed(2) }}</div>
            <div class="text-xs text-indigo-400 mt-1">= صافٍ + مسترجَع + الأرصدة</div>
          </div>
        </div>

        <div>
          <div class="flex justify-between items-center mb-2">
            <span class="text-sm font-medium text-gray-600">معدل التحصيل من إجمالي المفوتر</span>
            <span class="text-sm font-bold text-gray-800">{{ collectionRate.toFixed(1) }}%</span>
          </div>
          <div class="w-full h-3 bg-gray-100 rounded-full overflow-hidden">
            <div
              class="h-full bg-gradient-to-l from-emerald-400 to-emerald-600 rounded-full transition-all duration-500"
              :style="{ width: Math.min(collectionRate, 100) + '%' }"
            ></div>
          </div>
        </div>
      </div>

      <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
        <h3 class="font-bold text-gray-700 mb-6">المداخيل خلال آخر 12 شهر</h3>

        <div class="relative">
          <div class="absolute inset-0 flex flex-col justify-between pointer-events-none">
            <div v-for="n in 4" :key="n" class="border-t border-dashed border-gray-100 w-full"></div>
            <div class="border-t border-gray-200 w-full"></div>
          </div>

          <div class="relative flex items-end gap-2 h-56 pt-2">
            <div
              v-for="point in stats.monthly_breakdown"
              :key="point.month"
              class="flex-1 flex flex-col items-center justify-end h-full group relative"
            >
              <div
                class="w-full bg-gradient-to-t from-indigo-500 to-indigo-400 hover:to-indigo-500 rounded-t-lg transition-all"
                :style="{ height: barHeight(point.revenue) + '%' }"
              ></div>
              <span class="text-[10px] text-gray-400 mt-2 whitespace-nowrap">{{ formatMonth(point.month) }}</span>

              <div class="absolute -top-9 opacity-0 group-hover:opacity-100 transition-opacity bg-gray-800 text-white text-xs px-2.5 py-1.5 rounded-lg whitespace-nowrap z-10">
                {{ Number(point.revenue).toFixed(2) }} — {{ point.invoices_count }} فاتورة
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="text-center py-16 text-gray-400">تعذر تحميل الإحصائيات</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuth } from '../../composables/useAuth'

const { apiFetch } = useAuth()

const stats = ref(null)
const loading = ref(false)

const collectionRate = computed(() => {
  if (!stats.value || Number(stats.value.total_billed) <= 0) return 0
  return (Number(stats.value.total_collected) / Number(stats.value.total_billed)) * 100
})

const maxRevenue = () => {
  if (!stats.value?.monthly_breakdown?.length) return 1
  const max = Math.max(...stats.value.monthly_breakdown.map(p => Number(p.revenue)))
  return max > 0 ? max : 1
}

const barHeight = (revenue) => {
  const pct = (Number(revenue) / maxRevenue()) * 100
  return Math.max(pct, 2)
}

const formatMonth = (monthStr) => {
  const [, month] = monthStr.split('-')
  const names = ['يناير','فبراير','مارس','أبريل','مايو','يونيو','يوليو','أغسطس','سبتمبر','أكتوبر','نوفمبر','ديسمبر']
  return names[parseInt(month, 10) - 1]?.slice(0, 3) || month
}

const loadStats = async () => {
  loading.value = true
  try {
    const res = await apiFetch(`/api/invoices/stats/summary/`)
    if (res.ok) stats.value = await res.json()
  } catch (e) {
    console.error('إحصائيات الفواتير', e)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadStats()
})
</script>