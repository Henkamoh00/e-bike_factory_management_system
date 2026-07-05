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

        <div class="flex items-center gap-3 flex-wrap text-lg font-medium">
          <button @click="switchTab('dashboard')" :class="activeTab === 'dashboard' ? 'active-tab' : ''" class="tab-btn">الإحصائيات</button>
          <button @click="switchTab('assembly')" :class="activeTab === 'assembly' ? 'active-tab' : ''" class="tab-btn">الورشة</button>
          <button @click="switchTab('sales')"     :class="activeTab === 'sales'     ? 'active-tab' : ''" class="tab-btn">المبيعات</button>
          <button @click="switchTab('faults')"    :class="activeTab === 'faults'    ? 'active-tab' : ''" class="tab-btn">الأعطال</button>
          <button @click="switchTab('workers')"   :class="activeTab === 'workers'   ? 'active-tab' : ''" class="tab-btn">العمال</button>
          <button @click="switchTab('customers')" :class="activeTab === 'customers' ? 'active-tab' : ''" class="tab-btn">العملاء</button>
        </div>

      </div>
    </header>

    <div class="max-w-7xl mx-auto px-6 py-10">
      <DashboardStatsTab v-if="activeTab === 'dashboard'" :stats="stats" />

      <AssemblyTab
        v-else-if="activeTab === 'assembly'"
        ref="assemblyTabRef"
        :workers-list="workersList"
        @open-assembly-modal="showAssemblyModal = true"
      />

      <SalesTab
        v-else-if="activeTab === 'sales'"
        :sales-list="salesList"
        :customers-list="customersList"
        @open-sale-modal="showSaleModal = true"
      />

      <FaultsTab
        v-else-if="activeTab === 'faults'"
        :faults-list="faultsList"
        :workers-list="workersList"
        @open-fault-modal="showFaultModal = true"
      />

      <WorkersTab
        v-else-if="activeTab === 'workers'"
        :workers-list="workersList"
        @open-worker-modal="showWorkerModal = true"
      />

      <CustomersTab
        v-else-if="activeTab === 'customers'"
        :customers-list="customersList"
        @open-customer-modal="showCustomerModal = true"
      />
    </div>

    <AssemblyFormModal
      v-if="showAssemblyModal"
      :workers-list="workersList"
      @close="showAssemblyModal = false"
      @success="handleAssemblySuccess"
      @worker-added="loadWorkers"
    />

    <WorkerFormModal
      v-if="showWorkerModal"
      @close="showWorkerModal = false"
      @success="handleWorkerFormSuccess"
    />

    <CustomerFormModal
      v-if="showCustomerModal"
      @close="showCustomerModal = false"
      @success="handleCustomerFormSuccess"
    />

    <SaleModal
      v-if="showSaleModal"
      :customers-list="customersList"
      :chassis-list="availableChassisList"
      @close="showSaleModal = false"
      @success="handleSaleSuccess"
      @customer-added="loadCustomers"
    />

    <FaultModal
      v-if="showFaultModal"
      :chassis-list="allChassisList"
      @close="showFaultModal = false"
      @success="handleFaultSuccess"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

import AssemblyFormModal from '../components/admin/modals/AssemblyFormModal.vue'
import SaleModal from '../components/admin/modals/SaleModal.vue'
import FaultModal from '../components/admin/modals/FaultModal.vue'
import CustomerFormModal from '../components/admin/modals/CustomerFormModal.vue'
import WorkerFormModal from '../components/admin/modals/WorkerFormModal.vue'

import DashboardStatsTab from '../components/admin/tabs/DashboardStatsTab.vue'
import AssemblyTab from '../components/admin/tabs/AssemblyTab.vue'
import SalesTab from '../components/admin/tabs/SalesTab.vue'
import FaultsTab from '../components/admin/tabs/FaultsTab.vue'
import WorkersTab from '../components/admin/tabs/WorkersTab.vue'
import CustomersTab from '../components/admin/tabs/CustomersTab.vue'

const activeTab = ref('dashboard')

const showAssemblyModal = ref(false)
const showSaleModal     = ref(false)
const showFaultModal    = ref(false)
const showWorkerModal   = ref(false)
const showCustomerModal = ref(false)

const stats                = ref({ total_chassis: 0, completed: 0, in_progress: 0, sold: 0 })
const assemblyTabRef = ref(null)
const salesList             = ref([])
const availableChassisList  = ref([])
const faultsList             = ref([])
const allChassisList         = ref([])
const workersList            = ref([])
const customersList          = ref([])

const switchTab = (tab) => { activeTab.value = tab }

// ── API calls ───────────────────────────────────────────────────────────────
const API = 'http://localhost:8000'

const loadStats = async () => {
  try {
    const res = await fetch(`${API}/api/stats/`)
    if (res.ok) stats.value = await res.json()
  } catch (e) { console.error('إحصائيات', e) }
}

const loadSales = async () => {
  try {
    const res = await fetch(`${API}/api/sales/`)
    if (res.ok) salesList.value = await res.json()
  } catch (e) { console.error('مبيعات', e) }
}

const loadAvailableChassis = async () => {
  try {
    const res = await fetch(`${API}/api/chassis/available`)
    if (res.ok) availableChassisList.value = await res.json()
  } catch (e) { console.error('هياكل متاحة', e) }
}

const loadFaults = async () => {
  try {
    const res = await fetch(`${API}/api/faults/`)
    if (res.ok) faultsList.value = await res.json()
  } catch (e) { console.error('أعطال', e) }
}

const loadAllChassis = async () => {
  try {
    const res = await fetch(`${API}/api/chassis/all`)
    if (res.ok) allChassisList.value = await res.json()
  } catch (e) { console.error('كل الهياكل', e) }
}

const loadWorkers = async () => {
  try {
    const res = await fetch(`${API}/api/workers/`)
    if (res.ok) workersList.value = await res.json()
  } catch (e) { console.error('عمال', e) }
}

const loadCustomers = async () => {
  try {
    const res = await fetch(`${API}/api/customers/`)
    if (res.ok) customersList.value = await res.json()
  } catch (e) { console.error('عملاء', e) }
}

const handleAssemblySuccess = () => { showAssemblyModal.value = false; assemblyTabRef.value?.refresh() }
const handleSaleSuccess = () => { showSaleModal.value = false; loadSales(); loadAvailableChassis() }
const handleFaultSuccess        = () => { showFaultModal.value    = false; loadFaults() }
const handleCustomerFormSuccess = () => { showCustomerModal.value = false; loadCustomers() }
const handleWorkerFormSuccess   = () => { showWorkerModal.value   = false; loadWorkers() }

onMounted(() => {
  loadStats()
  loadSales()
  loadAvailableChassis()
  loadFaults()
  loadAllChassis()
  loadWorkers()
  loadCustomers()
})
</script>

<style scoped>
.tab-btn { padding: 8px 20px; border-radius: 9999px; transition: all 0.3s; }
.active-tab { background-color: #4f46e5; color: white !important; }
</style>