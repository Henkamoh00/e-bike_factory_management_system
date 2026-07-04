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
        <h2 class="text-2xl font-bold text-gray-800">الدراجات</h2>
        <button @click="showAssemblyModal = true" class="bg-emerald-600 hover:bg-emerald-700 text-white px-6 py-3 rounded-2xl font-medium">
          + تسجيل عملية تجميع
        </button>
      </div>

      <ChassisOverviewList
        ref="overviewRef"
        :workers-list="workersList"
        :show-worker-filter="true"
        summary-endpoint="http://localhost:8000/api/workshop/chassis/summary"
        history-endpoint="http://localhost:8000/api/workshop/history"
      />
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
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import AssemblyFormModal from '../components/workshop/modals/AssemblyFormModal.vue'
import ChassisOverviewList from '../components/shared/ChassisOverviewList.vue'

const router = useRouter()

const showAssemblyModal = ref(false)
const workersList = ref([])
const overviewRef = ref(null)

const loadWorkers = async () => {
  try {
    const res = await fetch('http://localhost:8000/api/workshop/workers')
    if (res.ok) workersList.value = await res.json()
  } catch { console.log('لا يمكن تحميل العمال') }
}

const handleAssemblySuccess = () => {
  showAssemblyModal.value = false
  overviewRef.value?.loadChassisSummary()
}

const goToAdmin = () => router.push('/admin')
const logout = () => { if (confirm('هل تريد تسجيل الخروج؟')) window.location.reload() }

onMounted(() => {
  loadWorkers()
})
</script>