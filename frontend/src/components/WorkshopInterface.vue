<template>
  <div class="space-y-8">
    <!-- Barcode Input -->
    <div class="bg-white rounded-2xl shadow p-8">
      <h2 class="text-2xl font-bold text-gray-800 mb-6 text-center">تسجيل عملية تجميع جديدة</h2>
      
      <div class="mb-6">
        <label class="block text-gray-700 text-sm font-medium mb-2">رقم الهيكل (Chassis Number)</label>
        <input
          v-model="chassisNumber"
          @keyup.enter="submitRecord"
          type="text"
          placeholder="أدخل أو امسح رقم الهيكل"
          class="w-full px-6 py-5 text-2xl border-2 border-gray-300 rounded-2xl focus:border-blue-500 focus:outline-none text-center font-mono tracking-widest"
          autofocus
        />
      </div>

      <!-- Workers -->
      <div class="mb-6">
        <label class="block text-gray-700 text-sm font-medium mb-3">اسم العامل</label>
        <div class="grid grid-cols-2 gap-3">
          <button
            v-for="worker in workers"
            :key="worker.id"
            @click="selectWorker(worker)"
            :class="selectedWorker?.id === worker.id ? 'bg-blue-600 text-white' : 'bg-gray-100 hover:bg-gray-200'"
            class="py-4 px-6 rounded-2xl text-lg font-medium transition-all"
          >
            {{ worker.name }}
          </button>
        </div>
      </div>

      <!-- Stages -->
      <div class="mb-8">
        <label class="block text-gray-700 text-sm font-medium mb-3">مرحلة التجميع</label>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <button
            v-for="stage in stages"
            :key="stage.value"
            @click="selectStage(stage)"
            :class="selectedStage?.value === stage.value ? 'ring-4 ring-blue-500 bg-blue-50' : 'hover:bg-gray-50'"
            class="p-6 border-2 border-gray-200 rounded-3xl text-center transition-all hover:border-blue-300"
          >
            <div class="text-4xl mb-3">{{ stage.icon }}</div>
            <div class="font-bold text-lg">{{ stage.label }}</div>
          </button>
        </div>
      </div>

      <button
        @click="submitRecord"
        :disabled="!canSubmit"
        class="w-full bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white text-2xl font-bold py-6 rounded-3xl transition-all active:scale-95 shadow-lg"
      >
        ✅ تسجيل العملية
      </button>
    </div>

    <!-- Recent Records -->
    <div class="bg-white rounded-2xl shadow p-6">
      <h3 class="text-xl font-semibold mb-4 flex items-center gap-2">
        <span>آخر العمليات</span>
        <span class="text-sm bg-gray-100 px-3 py-1 rounded-full">{{ recentRecords.length }}</span>
      </h3>
      <div v-if="recentRecords.length" class="space-y-3 max-h-96 overflow-auto">
        <div v-for="record in recentRecords" :key="record.id" class="flex justify-between items-center bg-gray-50 p-4 rounded-2xl">
          <div>
            <div class="font-mono font-bold">{{ record.chassis_number }}</div>
            <div class="text-sm text-gray-600">{{ record.stage }}</div>
          </div>
          <div class="text-right">
            <div class="text-sm">{{ record.worker_name || 'غير معروف' }}</div>
            <div class="text-xs text-gray-500">{{ new Date(record.timestamp).toLocaleTimeString('ar-EG') }}</div>
          </div>
        </div>
      </div>
      <p v-else class="text-gray-500 text-center py-8">لا توجد عمليات مسجلة بعد</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'

const API_BASE = 'http://localhost:8000'

const chassisNumber = ref('')
const selectedWorker = ref(null)
const selectedStage = ref(null)
const workers = ref([])
const recentRecords = ref([])

const stages = [
  { value: 'تجميع الهيكل', label: 'تجميع الهيكل', icon: '🔧' },
  { value: 'توصيل الكهرباء والغلاف', label: 'توصيل الكهرباء', icon: '⚡' },
  { value: 'تجميع كامل', label: 'تجميع كامل', icon: '🏁' }
]

const canSubmit = computed(() => {
  return chassisNumber.value.trim() && selectedWorker.value && selectedStage.value
})

const loadWorkers = async () => {
  try {
    // For demo - in real, fetch from API
    workers.value = [
      { id: 1, name: 'أحمد محمد' },
      { id: 2, name: 'محمود علي' },
      { id: 3, name: 'خالد حسن' }
    ]
  } catch (e) {
    console.error(e)
  }
}

const loadRecent = async () => {
  try {
    const res = await axios.get(`${API_BASE}/workshop/records?limit=10`)
    recentRecords.value = res.data
  } catch (e) {
    console.error('Failed to load recent', e)
  }
}

const selectWorker = (worker) => {
  selectedWorker.value = worker
}

const selectStage = (stage) => {
  selectedStage.value = stage
}

const submitRecord = async () => {
  if (!canSubmit.value) return

  try {
    await axios.post(`${API_BASE}/workshop/record`, {
      chassis_number: chassisNumber.value.trim().toUpperCase(),
      worker_id: selectedWorker.value.id,
      stage: selectedStage.value.value
    })

    alert('تم تسجيل العملية بنجاح!')
    
    // Reset form
    chassisNumber.value = ''
    selectedStage.value = null
    // selectedWorker remains for convenience

    await loadRecent()
  } catch (error) {
    alert(error.response?.data?.detail || 'حدث خطأ أثناء التسجيل')
  }
}

onMounted(() => {
  loadWorkers()
  loadRecent()
})
</script>