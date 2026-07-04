<template>
  <div class="min-h-screen bg-gray-50 font-sans">
    <header class="bg-white shadow-sm border-b">
      <div class="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 bg-emerald-600 rounded-xl flex items-center justify-center text-white text-2xl">⚡</div>
          <div>
            <h1 class="text-2xl font-bold text-gray-900">تجميع الدراجات</h1>
            <p class="text-sm text-gray-500">نظام إدارة الورشة</p>
          </div>
        </div>
        <div class="flex items-center gap-4">
          <button @click="goToAdmin" class="px-5 py-2 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 transition text-sm font-medium">
            📊 لوحة الإدارة
          </button>
          <button @click="logout" class="px-4 py-2 text-sm text-red-600 hover:bg-red-50 rounded-lg transition">تسجيل خروج</button>
        </div>
      </div>
    </header>

    <div class="max-w-4xl mx-auto px-4 py-8">

      <div class="flex justify-between items-center mb-6">
        <h2 class="text-2xl font-bold text-gray-800">سجلات التجميع</h2>
        <button @click="showAssemblyModal = true" class="bg-emerald-600 hover:bg-emerald-700 text-white px-6 py-3 rounded-2xl font-medium">
          + تسجيل عملية تجميع
        </button>
      </div>

      <!-- فلاتر -->
      <div class="bg-white rounded-2xl shadow p-5 mb-6 flex flex-wrap gap-4 items-end">
        <div>
          <label class="block text-sm text-gray-500 mb-1">بحث برقم الهيكل</label>
          <input
            v-model="filters.chassis_number"
            type="text"
            placeholder="EB-2026-..."
            class="px-4 py-2 border-2 border-gray-200 rounded-xl focus:border-emerald-400 focus:outline-none font-mono"
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
            label="تصفية بالمرحلة"
            empty-label="كل المراحل"
          />
        </div>
        <button @click="resetFilters" class="px-4 py-2 text-gray-500 hover:text-gray-700 underline text-sm">إعادة تعيين</button>
      </div>

      <!-- السجلات -->
      <div class="bg-white rounded-3xl shadow p-6">
        <h3 class="font-bold text-xl mb-4">
          السجلات <span class="text-emerald-600">({{ filteredRecords.length }})</span>
        </h3>

        <div v-if="filteredRecords.length === 0" class="text-center py-12 text-gray-400">
          لا توجد سجلات مطابقة
        </div>

        <div v-else class="space-y-3">
          <div v-for="record in filteredRecords" :key="record.id" class="flex justify-between items-center p-4 bg-gray-50 rounded-2xl">
            <div>
              <div class="font-mono font-bold">{{ record.chassis_number }}</div>
              <div class="text-sm text-gray-500">{{ record.worker_name }} • {{ getStageName(record.stage) }}</div>
            </div>
            <div class="text-xs text-gray-400">{{ new Date(record.timestamp).toLocaleString('ar-EG') }}</div>
          </div>
        </div>
      </div>
    </div>

    <AssemblyFormModal
      v-if="showAssemblyModal"
      :workers-list="workersList"
      @close="showAssemblyModal = false"
      @success="handleAssemblySuccess"
      @worker-added="loadWorkers"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import AssemblyFormModal from '../components/AssemblyFormModal.vue'
import SearchableSelect from '../components/SearchableSelect.vue'

const router = useRouter()

const showAssemblyModal = ref(false)
const recent = ref([])
const workersList = ref([])

const filters = ref({ chassis_number: '', worker_name: '', stage: '' })

const workerOptions = computed(() =>
  workersList.value.map(w => ({ label: w.name, value: w.name }))
)

const stageOptions = [
  { label: 'تجميع الهيكل', value: 'تجميع_الهيكل' },
  { label: 'توصيل الكهرباء والغلاف', value: 'توصيل_الكهرباء_والغلاف' },
  { label: 'تجميع كامل', value: 'تجميع_كامل' },
]

const filteredRecords = computed(() => {
  return recent.value.filter(r => {
    if (filters.value.chassis_number && !r.chassis_number.toLowerCase().includes(filters.value.chassis_number.toLowerCase())) return false
    if (filters.value.worker_name && r.worker_name !== filters.value.worker_name) return false
    if (filters.value.stage && r.stage !== filters.value.stage) return false
    return true
  })
})

const resetFilters = () => { filters.value = { chassis_number: '', worker_name: '', stage: '' } }

const getStageName = (stage) => {
  const names = {
    'تجميع_الهيكل': 'تجميع الهيكل',
    'توصيل_الكهرباء_والغلاف': 'توصيل الكهرباء والغلاف',
    'تجميع_كامل': 'تجميع كامل'
  }
  return names[stage] || stage
}

const loadRecent = async () => {
  try {
    const res = await fetch('http://localhost:8000/api/workshop/records')
    if (res.ok) recent.value = await res.json()
  } catch { console.log('لا يمكن تحميل السجلات') }
}

const loadWorkers = async () => {
  try {
    const res = await fetch('http://localhost:8000/api/workshop/workers')
    if (res.ok) workersList.value = await res.json()
  } catch { console.log('لا يمكن تحميل العمال') }
}

const handleAssemblySuccess = () => {
  showAssemblyModal.value = false
  loadRecent()
}

const goToAdmin = () => router.push('/admin')
const logout = () => { if (confirm('هل تريد تسجيل الخروج؟')) window.location.reload() }

onMounted(() => {
  loadRecent()
  loadWorkers()
})
</script>