<template>
  <div>
    <!-- فلاتر -->
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
          :options="workerOptions"
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
          :options="bikeTypeOptions"
          label="تصفية بنوع الدراجة"
          empty-label="كل الأنواع"
        />
      </div>

      <div>
        <SearchableSelect
          v-model="filters.bike_color"
          :options="bikeColorOptions"
          label="تصفية بلون الدراجة"
          empty-label="كل الألوان"
        />
      </div>

      <button @click="resetFilters" class="px-4 py-2 text-gray-500 hover:text-gray-700 underline text-sm">إعادة تعيين</button>
    </div>

    <!-- القائمة -->
    <div class="bg-white rounded-3xl shadow p-6">
      <h3 class="font-bold text-xl mb-4">
        الهياكل <span class="text-indigo-600">({{ filteredChassis.length }})</span>
      </h3>

      <div v-if="filteredChassis.length === 0" class="text-center py-12 text-gray-400">
        لا توجد نتائج مطابقة
      </div>

      <div v-else class="space-y-3">
        <div
          v-for="chassis in filteredChassis"
          :key="chassis.chassis_number"
          @click="openDetails(chassis.chassis_number)"
          class="flex justify-between items-center p-4 bg-gray-50 rounded-2xl cursor-pointer hover:bg-gray-100 transition"
        >
          <div>
            <div class="font-mono font-bold">{{ chassis.chassis_number }}</div>
            <div class="text-sm text-gray-500">
              {{ chassis.is_complete ? '✅ مكتمل' : '⚙️ قيد التجميع' }}
              <span v-if="chassis.is_sold" class="text-emerald-600"> • مباع لـ {{ chassis.customer_name }}</span>
              <span v-else class="text-amber-600"> • غير مباع</span>
            </div>
          </div>
          <div class="text-left">
            <span v-if="chassis.pending_faults_count > 0" class="text-xs bg-red-100 text-red-700 rounded-full px-3 py-1">
              {{ chassis.pending_faults_count }} عطل معلق
            </span>
            <div class="text-xs text-gray-400 mt-1">{{ new Date(chassis.last_updated).toLocaleDateString('ar-EG') }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- نافذة التفاصيل -->
    <div v-if="selectedChassis" class="fixed inset-0 bg-black/60 flex items-center justify-center z-50" @click.self="selectedChassis = null">
      <div class="bg-white rounded-3xl shadow-2xl w-full max-w-2xl mx-4 max-h-[85vh] overflow-y-auto p-8">
        <div class="flex justify-between items-start mb-6">
          <h3 class="text-2xl font-bold">
            تاريخ الدراجة <span class="font-mono text-indigo-600">{{ selectedChassis.chassis_number }}</span>
          </h3>
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
            <h4 class="font-semibold text-sm text-gray-500 mb-3">💰 معلومات البيع</h4>
            <div v-if="selectedChassis.sale" class="p-4 bg-emerald-50 rounded-2xl">
              <p class="font-medium text-sm">✅ تم البيع لـ <strong>{{ selectedChassis.sale.customer_name }}</strong></p>
              <p class="text-xs text-gray-500 mt-1">{{ new Date(selectedChassis.sale.sale_date).toLocaleDateString('ar-EG') }}</p>
            </div>
            <div v-else class="text-center py-8 text-gray-400">لم يتم بيع هذه الدراجة بعد</div>
          </div>
        </div>

        <div v-if="!loadingDetails" class="mt-8">
          <h4 class="font-semibold text-sm text-gray-500 mb-3">⚠️ الأعطال</h4>
          <div v-if="selectedChassis.faults?.length" class="space-y-3">
            <div v-for="fault in selectedChassis.faults" :key="fault.id" class="flex justify-between items-center p-4 bg-gray-50 rounded-2xl">
              <div>
                <div class="text-sm">{{ fault.description }}</div>
                <div class="text-xs text-gray-500 mt-1">العامل: {{ fault.worker_name || 'غير معروف' }}</div>
              </div>
              <div class="text-right">
                <span :class="fault.status === 'pending' ? 'text-red-600' : 'text-emerald-600'" class="text-xs font-medium">
                  {{ fault.status === 'pending' ? 'معلق' : 'تم إصلاحه' }}
                </span>
                <div class="text-xs text-gray-400 mt-1">{{ new Date(fault.reported_date).toLocaleDateString('ar-EG') }}</div>
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
import { ref, computed, onMounted } from 'vue'
import SearchableSelect from '../../shared/SearchableSelect.vue'

const API = 'http://localhost:8000'

const props = defineProps({
  workersList: { type: Array, default: () => [] }
})

const chassisList = ref([])
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

const workerOptions = computed(() =>
  props.workersList.map(w => ({ label: w.name, value: w.name }))
)

const bikeTypeOptions = computed(() => {
  const names = [...new Set(chassisList.value.map(c => c.bike_type).filter(Boolean))]
  return names.map(n => ({ label: n, value: n }))
})

const bikeColorOptions = computed(() => {
  const names = [...new Set(chassisList.value.map(c => c.bike_color).filter(Boolean))]
  return names.map(n => ({ label: n, value: n }))
})

const filteredChassis = computed(() => {
  return chassisList.value.filter(c => {
    if (filters.value.chassis_number && !c.chassis_number.toLowerCase().includes(filters.value.chassis_number.toLowerCase())) return false
    if (filters.value.status === 'available' && (!c.is_complete || c.is_sold)) return false
    if (filters.value.status === 'sold' && !c.is_sold) return false
    if (filters.value.status === 'in_progress' && c.is_complete) return false
    if (filters.value.status === 'has_fault' && c.pending_faults_count === 0) return false
    if (filters.value.worker_name && !(c.workers || []).includes(filters.value.worker_name)) return false
    if (filters.value.stage && !(c.stages || []).includes(filters.value.stage)) return false
    if (filters.value.bike_type && c.bike_type !== filters.value.bike_type) return false
    if (filters.value.bike_color && c.bike_color !== filters.value.bike_color) return false
    return true
  })
})

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

const loadChassisSummary = async () => {
  try {
    const res = await fetch(`${API}/api/chassis/summary`)
    if (res.ok) chassisList.value = await res.json()
  } catch (e) { console.error('ملخص الهياكل', e) }
}

const openDetails = async (chassisNumber) => {
  loadingDetails.value = true
  selectedChassis.value = { chassis_number: chassisNumber }
  try {
    const res = await fetch(`${API}/api/chassis/${chassisNumber}`)
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

defineExpose({ loadChassisSummary })

onMounted(() => {
  loadChassisSummary()
})
</script>