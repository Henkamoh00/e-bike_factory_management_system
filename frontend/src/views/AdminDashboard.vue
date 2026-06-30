<template>
  <div class="min-h-screen bg-gray-100 font-sans">
    <!-- Header -->
    <header class="bg-white shadow border-b sticky top-0 z-50">
      <div class="max-w-7xl mx-auto px-6 py-5 flex justify-between items-center">
        <div class="flex items-center gap-4">
          <div class="w-12 h-12 bg-indigo-600 rounded-2xl flex items-center justify-center text-white text-3xl">📊</div>
          <div>
            <h1 class="text-3xl font-bold text-gray-900">لوحة الإدارة</h1>
            <p class="text-gray-500">نظام التتبع والإدارة الشامل</p>
          </div>
        </div>

        <div class="flex items-center gap-8 text-lg font-medium">
          <button @click="switchTab('dashboard')" :class="activeTab === 'dashboard' ? 'active-tab' : ''" class="tab-btn">الإحصائيات</button>
          <button @click="switchTab('search')" :class="activeTab === 'search' ? 'active-tab' : ''" class="tab-btn">بحث عن دراجة</button>
          <button @click="switchTab('sales')" :class="activeTab === 'sales' ? 'active-tab' : ''" class="tab-btn">المبيعات</button>
          <button @click="switchTab('faults')" :class="activeTab === 'faults' ? 'active-tab' : ''" class="tab-btn">الأعطال</button>
        </div>

        <button @click="goToWorkshop" class="px-6 py-3 bg-gray-800 hover:bg-gray-700 text-white rounded-2xl transition">← العودة للورشة</button>
      </div>
    </header>

    <div class="max-w-7xl mx-auto px-6 py-10">
      <!-- 1. الإحصائيات -->
      <div v-if="activeTab === 'dashboard'">
        <h2 class="text-3xl font-bold mb-8">الإحصائيات العامة</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div class="bg-white rounded-3xl shadow p-8 text-center hover:shadow-xl transition">
            <div class="text-6xl mb-6">🚲</div>
            <div class="text-5xl font-bold text-blue-600">{{ stats.total_chassis }}</div>
            <div class="text-gray-500 text-lg">إجمالي الهياكل</div>
          </div>
          <div class="bg-white rounded-3xl shadow p-8 text-center hover:shadow-xl transition">
            <div class="text-6xl mb-6">🏁</div>
            <div class="text-5xl font-bold text-emerald-600">{{ stats.completed }}</div>
            <div class="text-gray-500 text-lg">مكتمل التجميع</div>
          </div>
          <div class="bg-white rounded-3xl shadow p-8 text-center hover:shadow-xl transition">
            <div class="text-6xl mb-6">⚙️</div>
            <div class="text-5xl font-bold text-amber-600">{{ stats.in_progress }}</div>
            <div class="text-gray-500 text-lg">قيد التجميع</div>
          </div>
          <div class="bg-white rounded-3xl shadow p-8 text-center hover:shadow-xl transition">
            <div class="text-6xl mb-6">💰</div>
            <div class="text-5xl font-bold text-purple-600">{{ stats.sold }}</div>
            <div class="text-gray-500 text-lg">تم بيعها</div>
          </div>
        </div>
      </div>

      <!-- 2. بحث عن دراجة -->
      <div v-else-if="activeTab === 'search'">
        <h2 class="text-3xl font-bold mb-8">البحث عن دراجة</h2>
        <div class="max-w-2xl">
          <input
            v-model="searchQuery"
            @keyup.enter="searchChassis"
            placeholder="أدخل رقم الهيكل (مثال: EB-2026-00485)"
            class="w-full px-8 py-6 text-xl border-2 border-gray-300 rounded-3xl focus:border-indigo-500 focus:outline-none font-mono shadow-sm"
          />
        </div>

        <div v-if="chassisHistory" class="mt-10 bg-white rounded-3xl shadow-xl p-8">
          <h3 class="text-2xl font-bold mb-6">
            تاريخ الدراجة: <span class="font-mono text-indigo-600">{{ chassisHistory.chassis_number }}</span>
          </h3>
          <div class="grid md:grid-cols-2 gap-8">
            <div>
              <h4 class="font-semibold text-lg mb-4 text-emerald-700">📋 سجل التجميع</h4>
              <div v-if="chassisHistory.assembly_history?.length" class="space-y-4">
                <div v-for="rec in chassisHistory.assembly_history" :key="rec.id" class="bg-gray-50 p-5 rounded-2xl flex justify-between items-center">
                  <div>
                    <div class="font-medium">{{ rec.stage }}</div>
                    <div class="text-gray-600 text-sm">بواسطة: {{ rec.worker_name || 'غير معروف' }}</div>
                  </div>
                  <div class="text-right text-sm text-gray-500">{{ new Date(rec.timestamp).toLocaleString('ar-EG') }}</div>
                </div>
              </div>
              <p v-else class="text-gray-500 py-8">لا يوجد سجلات تجميع بعد</p>
            </div>
            <div>
              <h4 class="font-semibold text-lg mb-4">💰 معلومات البيع</h4>
              <div v-if="chassisHistory.sale" class="p-6 bg-emerald-50 rounded-2xl">
                <p class="font-medium">✅ تم البيع لـ <strong>{{ chassisHistory.sale.customer_name }}</strong></p>
                <p class="text-sm text-gray-600 mt-2">بتاريخ {{ new Date(chassisHistory.sale.sale_date).toLocaleDateString('ar-EG') }}</p>
              </div>
              <div v-else class="p-6 bg-amber-50 rounded-2xl text-amber-700">لم يتم بيع هذه الدراجة بعد</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 3. المبيعات -->
      <div v-else-if="activeTab === 'sales'">
        <div class="flex justify-between items-center mb-8">
          <h2 class="text-3xl font-bold">المبيعات</h2>
          <button @click="showSaleModal = true" class="bg-green-600 hover:bg-green-700 text-white px-6 py-3 rounded-2xl font-medium">+ تسجيل بيع جديد</button>
        </div>
        
        <div class="bg-white rounded-3xl shadow-xl p-6">
          <div v-if="salesList.length === 0" class="text-center py-16 text-gray-400 text-lg">
            لا توجد مبيعات مسجلة بعد
          </div>
          <div v-else class="space-y-4">
            <div v-for="sale in salesList" :key="sale.id" class="bg-gray-50 p-5 rounded-2xl flex justify-between items-center">
              <div>
                <div class="font-mono font-bold">{{ sale.chassis_number }}</div>
                <div class="text-gray-600">العميل: <strong>{{ sale.customer_name }}</strong></div>
              </div>
              <div class="text-right">
                <div class="text-sm text-gray-500">{{ new Date(sale.sale_date).toLocaleDateString('ar-EG') }}</div>
                <div v-if="sale.notes" class="text-xs text-gray-400 mt-1">{{ sale.notes }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 4. الأعطال -->
      <div v-else-if="activeTab === 'faults'">
        <div class="flex justify-between items-center mb-8">
          <h2 class="text-3xl font-bold">الأعطال</h2>
          <button @click="showFaultModal = true" class="bg-red-600 hover:bg-red-700 text-white px-6 py-3 rounded-2xl font-medium">+ تسجيل عطل جديد</button>
        </div>
        
        <div class="bg-white rounded-3xl shadow-xl p-6">
          <div v-if="faultsList.length === 0" class="text-center py-16 text-gray-400 text-lg">
            لا توجد أعطال مسجلة بعد
          </div>
          <div v-else class="space-y-4">
            <div v-for="fault in faultsList" :key="fault.id" class="bg-gray-50 p-5 rounded-2xl flex justify-between items-center">
              <div>
                <div class="font-mono font-bold">{{ fault.chassis_number }}</div>
                <div class="text-sm text-gray-500">العامل: {{ fault.worker_name || 'غير معروف' }}</div>
                <div class="text-gray-600">{{ fault.description }}</div>
              </div>
              <div class="text-right">
                <span :class="fault.status === 'pending' ? 'text-red-600' : 'text-emerald-600'" class="font-medium">
                  {{ fault.status === 'pending' ? 'معلق' : 'تم إصلاحه' }}
                </span>
                <div class="text-xs text-gray-500 mt-1">{{ new Date(fault.reported_date).toLocaleDateString('ar-EG') }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Modals -->
    <SaleModal v-if="showSaleModal" @close="showSaleModal = false" @success="handleSaleSuccess" />
    <FaultModal v-if="showFaultModal" @close="showFaultModal = false" @success="handleFaultSuccess" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import SaleModal from '../components/SaleModal.vue'
import FaultModal from '../components/FaultModal.vue'

const router = useRouter()
const activeTab = ref('dashboard')
const showSaleModal = ref(false)
const showFaultModal = ref(false)

const stats = ref({ total_chassis: 0, completed: 0, in_progress: 0, sold: 0 })
const searchQuery = ref('')
const chassisHistory = ref(null)
const salesList = ref([])
const faultsList = ref([])

const switchTab = (tab) => { activeTab.value = tab }
const goToWorkshop = () => router.push('/')

const handleSaleSuccess = () => { 
  showSaleModal.value = false 
  loadSales()
}
const handleFaultSuccess = () => { 
  showFaultModal.value = false 
  loadFaults()
}

const loadStats = async () => {
  try {
    const res = await fetch('http://localhost:8000/admin/stats')
    if (res.ok) stats.value = await res.json()
  } catch (e) {
    console.error("خطأ في تحميل الإحصائيات", e)
  }
}

const searchChassis = async () => {
  if (!searchQuery.value.trim()) return
  try {
    const res = await fetch(`http://localhost:8000/workshop/history/${searchQuery.value.trim()}`)
    if (res.ok) {
      chassisHistory.value = await res.json()
    } else {
      alert('لم يتم العثور على هذا الهيكل')
      chassisHistory.value = null
    }
  } catch (e) {
    alert('خطأ في الاتصال')
  }
}

const loadSales = async () => {
  try {
    const res = await fetch('http://localhost:8000/admin/sales/')
    if (res.ok) salesList.value = await res.json()
  } catch (e) {
    console.error("خطأ في تحميل المبيعات", e)
  }
}

const loadFaults = async () => {
  try {
    const res = await fetch('http://localhost:8000/admin/faults/')
    if (res.ok) faultsList.value = await res.json()
  } catch (e) {
    console.error("خطأ في تحميل الأعطال", e)
  }
}

onMounted(() => {
  loadStats()
  loadSales()
  loadFaults()
})
</script>

<style scoped>
.tab-btn {
  padding: 8px 20px;
  border-radius: 9999px;
  transition: all 0.3s;
}
.active-tab {
  background-color: #4f46e5;
  color: white !important;
}
</style>