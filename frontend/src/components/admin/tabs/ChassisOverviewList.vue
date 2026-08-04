<template>
  <div>
    <div class="bg-white rounded-2xl shadow p-5 mb-6 flex flex-wrap gap-4 items-end">
      <div>
        <label class="block text-sm text-gray-500 mb-1">بحث برقم الهيكل</label>
        <input
          v-model="filters.chassis_number"
          type="text"
          placeholder="EB-2026-..."
          class="px-4 py-2 border-2 border-gray-200 rounded-xl focus:border-indigo-400 focus:outline-none font-mono"
        />
      </div>

      <div>
        <SearchableSelect
          v-model="filters.status"
          :options="statusOptions"
          label="تصفية بالحالة"
          empty-label="الكل"
        />
      </div>

      <div>
        <SearchableSelect
          v-model="filters.worker_name"
          :async-search="searchWorkers"
          label="تصفية بالعامل"
          empty-label="كل العمال"
        />
      </div>

      <div>
        <SearchableSelect
          v-model="filters.stage"
          :options="stageOptions"
          label="تصفية بمرحلة التجميع"
          empty-label="كل المراحل"
        />
      </div>

      <div>
        <SearchableSelect
          v-model="filters.bike_type"
          :async-search="searchBikeTypes"
          label="تصفية بنوع الدراجة"
          empty-label="كل الأنواع"
        />
      </div>

      <div>
        <SearchableSelect
          v-model="filters.bike_color"
          :async-search="searchBikeColors"
          label="تصفية بلون الدراجة"
          empty-label="كل الألوان"
        />
      </div>

      <button @click="resetFilters" class="px-4 py-2 text-gray-500 hover:text-gray-700 underline text-sm">إعادة تعيين</button>
    </div>

    <div class="bg-white rounded-3xl shadow p-6">
      <h3 class="font-bold text-xl mb-4">
        الهياكل <span class="text-indigo-600">({{ pg.total.value }})</span>
      </h3>

      <div v-if="pg.loading.value" class="text-center py-12 text-gray-400">جاري التحميل...</div>
      <div v-else-if="pg.items.value.length === 0" class="text-center py-12 text-gray-400">
        لا توجد نتائج مطابقة
      </div>

      <div v-else class="divide-y divide-gray-100">
        <div
          v-for="chassis in pg.items.value"
          :key="chassis.chassis_number"
          class="flex items-center justify-between gap-4 py-3 hover:bg-gray-50 transition px-2 -mx-2 rounded-xl"
        >
          <div @click="openDetails(chassis.chassis_number)" class="flex items-center gap-3 min-w-0 cursor-pointer flex-1">
            <span class="text-lg shrink-0">{{ chassis.is_complete ? '✅' : '⚙️' }}</span>
            <div class="min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="font-mono font-bold text-gray-800">{{ chassis.chassis_number }}</span>
                <span class="text-xs text-gray-500">{{ currentStageLabel(chassis) }}</span>
              </div>
              <div class="flex items-center gap-2 mt-1 flex-wrap">
                <span v-if="chassis.bike_type" class="text-xs bg-indigo-50 text-indigo-600 rounded-full px-2 py-0.5">🚲 {{ chassis.bike_type }}</span>
                <span v-if="chassis.bike_color" class="text-xs bg-purple-50 text-purple-600 rounded-full px-2 py-0.5">🎨 {{ chassis.bike_color }}</span>
                <span v-if="chassis.is_sold" class="text-xs text-emerald-600">مباع لـ {{ chassis.customer_name }}</span>
                <span v-else class="text-xs text-amber-600">غير مباع</span>
              </div>
            </div>
          </div>

          <div class="text-left shrink-0 flex items-center gap-3">
            <span v-if="chassis.pending_faults_count > 0" class="text-xs bg-red-100 text-red-700 rounded-full px-2.5 py-1">
              {{ chassis.pending_faults_count }} عطل
            </span>
            <span class="text-xs text-gray-400">{{ new Date(chassis.last_updated).toLocaleDateString('ar-EG') }}</span>
          </div>
        </div>
      </div>
    </div>

    <div v-if="pg.totalPages.value > 1" class="flex justify-center items-center gap-3 mt-6">
      <button @click="pg.prevPage" :disabled="pg.page.value === 1" class="px-4 py-2 rounded-xl bg-white shadow disabled:opacity-40 text-sm">السابق</button>
      <span class="text-sm text-gray-500">صفحة {{ pg.page.value }} من {{ pg.totalPages.value }}</span>
      <button @click="pg.nextPage" :disabled="pg.page.value === pg.totalPages.value" class="px-4 py-2 rounded-xl bg-white shadow disabled:opacity-40 text-sm">التالي</button>
    </div>

    <div v-if="selectedChassis" class="fixed inset-0 bg-black/60 flex items-center justify-center z-50" @click.self="selectedChassis = null">
      <div class="bg-white rounded-3xl shadow-2xl w-full max-w-2xl mx-4 max-h-[85vh] overflow-y-auto p-8">
        <div class="flex justify-between items-start mb-6">
          <h3 class="text-2xl font-bold">
            تاريخ الدراجة <span class="font-mono text-indigo-600">{{ selectedChassis.chassis_number }}</span>
          </h3>

          <div v-if="!loadingDetails && (selectedChassis.bike_type || selectedChassis.bike_color)" class="flex gap-2 mb-6 -mt-2">
            <span v-if="selectedChassis.bike_type" class="text-xs bg-indigo-100 text-indigo-700 rounded-full px-3 py-1.5">
              🚲 النوع: {{ selectedChassis.bike_type }}
            </span>
            <span v-if="selectedChassis.bike_color" class="text-xs bg-purple-100 text-purple-700 rounded-full px-3 py-1.5">
              🎨 اللون: {{ selectedChassis.bike_color }}
            </span>
          </div>

          <button @click="selectedChassis = null" class="text-gray-400 hover:text-gray-600 text-2xl leading-none">×</button>
        </div>

        <div v-if="loadingDetails" class="text-center py-12 text-gray-400">جاري التحميل...</div>

        <div v-else class="grid md:grid-cols-2 gap-8">
          <div>
            <h4 class="font-semibold text-sm text-gray-500 mb-3">📋 سجل التجميع</h4>
            <div v-if="selectedChassis.assembly_history?.length" class="space-y-3">
              <div v-for="rec in selectedChassis.assembly_history" :key="rec.id" class="flex justify-between items-center p-4 bg-gray-50 rounded-2xl">
                <div>
                  <div class="font-medium">{{ getStageName(rec.stage) }}</div>
                  <div class="text-sm text-gray-500">بواسطة: {{ rec.worker_name || 'غير معروف' }}</div>
                </div>
                <div class="text-xs text-gray-400">{{ new Date(rec.timestamp).toLocaleString('ar-EG') }}</div>
              </div>
            </div>
            <div v-else class="text-center py-8 text-gray-400">لا يوجد سجلات تجميع</div>
          </div>

          <div>
            <h4 class="font-semibold text-sm text-gray-500 mb-3">💰 سجل البيع</h4>
            <div v-if="selectedChassis.sales?.length" class="space-y-3">
              <div
                v-for="sale in selectedChassis.sales"
                :key="sale.id"
                class="p-4 rounded-2xl"
                :class="sale.status === 'cancelled' ? 'bg-gray-50 opacity-70' : 'bg-emerald-50'"
              >
                <div class="flex items-center justify-between gap-2">
                  <p class="font-medium text-sm" :class="sale.status === 'cancelled' ? 'text-gray-500 line-through' : ''">
                    {{ sale.status === 'cancelled' ? '✖️ بيع ملغى لـ' : '✅ تم البيع لـ' }}
                    <strong>{{ sale.customer_name }}</strong>
                  </p>
                  <span
                    v-if="sale.status === 'cancelled'"
                    class="text-xs bg-red-100 text-red-600 rounded-full px-2 py-0.5 font-medium shrink-0"
                  >
                    ملغى
                  </span>
                </div>
                <p class="text-xs text-gray-500 mt-1">{{ new Date(sale.sale_date).toLocaleDateString('ar-EG') }}</p>
                <p v-if="sale.status === 'cancelled' && sale.cancel_reason" class="text-xs text-red-500 mt-1">
                  السبب: {{ sale.cancel_reason }}
                </p>
              </div>
            </div>
            <div v-else class="text-center py-8 text-gray-400">لم يتم بيع هذه الدراجة بعد</div>
          </div>
        </div>

        <div v-if="!loadingDetails" class="mt-8">
          <h4 class="font-semibold text-sm text-gray-500 mb-3">⚠️ الأعطال</h4>
          <div v-if="selectedChassis.faults?.length" class="space-y-3">
            <div v-for="fault in selectedChassis.faults" :key="fault.id" class="p-4 bg-gray-50 rounded-2xl">
              <div class="flex justify-between items-center">
                <div>
                  <div class="text-sm">{{ fault.description }}</div>
                  <div v-if="fault.related_stage" class="text-xs text-gray-400 mt-1">
                    المرحلة: {{ getStageName(fault.related_stage) }}
                    <span v-if="fault.responsible_worker_name"> — بواسطة: {{ fault.responsible_worker_name }}</span>
                  </div>
                </div>
                <div class="text-right shrink-0">
                  <span :class="fault.status === 'pending' ? 'text-red-600' : 'text-emerald-600'" class="text-xs font-medium">
                    {{ fault.status === 'pending' ? 'معلق' : 'تم إصلاحه' }}
                  </span>
                  <div class="text-xs text-gray-400 mt-1">{{ new Date(fault.reported_date).toLocaleDateString('ar-EG') }}</div>
                </div>
              </div>

              <div v-if="fault.repairs?.length" class="mt-3 pt-3 border-t border-gray-200 space-y-2">
                <div v-for="repair in fault.repairs" :key="repair.id" class="flex justify-between items-center bg-white px-3 py-2 rounded-xl border border-gray-200">
                  <div>
                    <span class="text-xs font-medium text-emerald-700">🔧 {{ repair.worker_name }}</span>
                    <span v-if="repair.notes" class="text-xs text-gray-500 block mt-0.5">{{ repair.notes }}</span>
                  </div>
                  <span class="text-xs text-gray-400 shrink-0">{{ new Date(repair.repair_date).toLocaleString('ar-EG') }}</span>
                </div>
              </div>
            </div>
          </div>
          <div v-else class="text-center py-8 text-gray-400">لا توجد أعطال مسجلة</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import SearchableSelect from '../../shared/SearchableSelect.vue'
import { useAuth } from '../../../composables/useAuth'
import { useServerPagination } from '../../../composables/useServerPagination'

const { apiFetch } = useAuth()

const filters = ref({
  chassis_number: '',
  status: '',
  worker_name: '',
  stage: '',
  bike_type: '',
  bike_color: ''
})

const selectedChassis = ref(null)
const loadingDetails = ref(false)

const statusOptions = [
  { label: 'مكتمل وغير مباع', value: 'available' },
  { label: 'مباع', value: 'sold' },
  { label: 'قيد التجميع', value: 'in_progress' },
  { label: 'به عطل معلق', value: 'has_fault' },
]

const stageOptions = [
  { label: 'تجميع الهيكل', value: 'تجميع_الهيكل' },
  { label: 'توصيل الكهرباء والغلاف', value: 'توصيل_الكهرباء_والغلاف' },
  { label: 'تجميع كامل', value: 'تجميع_كامل' },
]

const searchWorkers = async (query) => {
  const params = new URLSearchParams({ limit: 20 })
  if (query) params.set('q', query)
  const res = await apiFetch(`/api/workers/simple/?${params.toString()}`)
  if (!res.ok) return []
  const data = await res.json()
  return data.map(w => ({ label: w.name, value: w.name }))
}

const searchBikeTypes = async (query) => {
  const params = new URLSearchParams({ limit: 20 })
  if (query) params.set('q', query)
  const res = await apiFetch(`/api/bike-types/simple/?${params.toString()}`)
  if (!res.ok) return []
  const data = await res.json()
  return data.map(t => ({ label: t.name, value: t.name }))
}

const searchBikeColors = async (query) => {
  const params = new URLSearchParams({ limit: 20 })
  if (query) params.set('q', query)
  const res = await apiFetch(`/api/bike-colors/simple/?${params.toString()}`)
  if (!res.ok) return []
  const data = await res.json()
  return data.map(c => ({ label: c.name, value: c.name }))
}

const fetchChassisPage = async ({ skip, limit }) => {
  const params = new URLSearchParams({ skip, limit })
  if (filters.value.chassis_number) params.set('chassis_number', filters.value.chassis_number)
  if (filters.value.status) params.set('status', filters.value.status)
  if (filters.value.worker_name) params.set('worker_name', filters.value.worker_name)
  if (filters.value.stage) params.set('stage', filters.value.stage)
  if (filters.value.bike_type) params.set('bike_type', filters.value.bike_type)
  if (filters.value.bike_color) params.set('bike_color', filters.value.bike_color)
  const res = await apiFetch(`/api/chassis/summary/?${params.toString()}`)
  if (!res.ok) return { items: [], total: 0 }
  return res.json()
}

const pg = useServerPagination(fetchChassisPage, 10)

let debounceTimer = null
watch(filters, () => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    pg.page.value = 1
    pg.load()
  }, 300)
}, { deep: true })

const resetFilters = () => {
  filters.value = { chassis_number: '', status: '', worker_name: '', stage: '', bike_type: '', bike_color: '' }
}

const getStageName = (stage) => {
  const names = {
    'تجميع_الهيكل':           'تجميع الهيكل',
    'توصيل_الكهرباء_والغلاف': 'توصيل الكهرباء والغلاف',
    'تجميع_كامل':             'تجميع كامل',
  }
  return names[stage] || stage
}

const currentStageLabel = (chassis) => {
  const stages = chassis.stages || []

  if (chassis.is_complete) {
    if (stages.includes('تجميع_كامل')) return 'تجميع كامل ✅'
    return 'تجميع الهيكل + توصيل الكهرباء والغلاف ✅ (مكتمل)'
  }

  if (stages.includes('توصيل_الكهرباء_والغلاف')) return 'توصيل الكهرباء والغلاف'
  if (stages.includes('تجميع_الهيكل')) return 'تجميع الهيكل'
  return 'لم تبدأ بعد'
}

const openDetails = async (chassisNumber) => {
  loadingDetails.value = true
  selectedChassis.value = { chassis_number: chassisNumber }
  try {
    const res = await apiFetch(`/api/chassis/${chassisNumber}/`)
    if (res.ok) {
      selectedChassis.value = await res.json()
    } else {
      alert('تعذر جلب تفاصيل الهيكل')
      selectedChassis.value = null
    }
  } catch (e) {
    alert('خطأ في الاتصال')
    selectedChassis.value = null
  } finally {
    loadingDetails.value = false
  }
}

defineExpose({ refresh: pg.load })

onMounted(() => {
  pg.load()
})
</script>