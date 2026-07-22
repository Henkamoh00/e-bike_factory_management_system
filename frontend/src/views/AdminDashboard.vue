<template>
  <div class="min-h-screen bg-slate-50 font-sans flex" dir="rtl">

    <!-- Overlay للموبايل/التابلت عند فتح السايدبار -->
    <div
      v-if="isSidebarOpen"
      @click="isSidebarOpen = false"
      class="fixed inset-0 bg-black/50 z-40 lg:hidden transition-opacity duration-300"
    ></div>

    <!-- Sidebar -->
    <aside
      :class="asideClasses"
      class="fixed lg:sticky top-0 right-0 h-screen w-72 max-w-[85vw] overflow-hidden bg-white border-slate-200 flex flex-col shrink-0 z-50 transition-all duration-300 ease-in-out"
    >
      <div class="px-5 sm:px-6 py-6 sm:py-7 border-b border-slate-100 flex items-center justify-between">
        <div class="flex items-center gap-3 min-w-0">
          <div class="w-10 h-10 sm:w-11 sm:h-11 bg-gradient-to-br from-indigo-600 to-indigo-500 rounded-2xl flex items-center justify-center text-white text-lg sm:text-xl shadow-lg shadow-indigo-200 shrink-0">
            📊
          </div>
          <div class="min-w-0">
            <h1 class="text-base sm:text-lg font-bold text-slate-900 leading-tight truncate">لوحة الإدارة</h1>
            <p class="text-xs text-slate-400 truncate">نظام التتبع الشامل</p>
          </div>
        </div>

        <button
          @click="isSidebarOpen = false"
          class="lg:hidden shrink-0 w-9 h-9 flex items-center justify-center rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors"
          aria-label="إغلاق القائمة"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <nav class="flex-1 px-3 sm:px-4 py-4 sm:py-6 space-y-1 overflow-y-auto">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          @click="switchTab(tab.id)"
          :class="activeTab === tab.id
            ? 'bg-indigo-50 text-indigo-700 font-semibold'
            : 'text-slate-500 hover:bg-slate-50 hover:text-slate-800'"
          class="w-full flex items-center gap-3 px-3 sm:px-4 py-2.5 sm:py-3 rounded-xl transition-all duration-200 text-sm"
        >
          <span class="text-base sm:text-lg">{{ tab.icon }}</span>
          <span class="truncate">{{ tab.label }}</span>
          <span
            v-if="activeTab === tab.id"
            class="mr-auto w-1.5 h-1.5 rounded-full bg-indigo-600 shrink-0"
          ></span>
        </button>
      </nav>

      <div class="px-5 sm:px-6 py-4 sm:py-5 border-t border-slate-100">
        <p class="text-[11px] sm:text-xs text-slate-400 text-center">إصدار 1.0 · نظام التجميع الكهربائي</p>
      </div>
    </aside>

    <!-- Main content -->
    <div class="flex-1 min-w-0 w-full">
      <header class="bg-white/80 backdrop-blur border-b border-slate-200 sticky top-0 z-30">
        <div class="px-4 sm:px-6 lg:px-8 py-4 sm:py-5 flex items-center justify-between gap-3">
          <div class="flex items-center gap-3 min-w-0">
            <button
              @click="isDesktopSidebarOpen = !isDesktopSidebarOpen"
              class="hidden lg:flex shrink-0 w-10 h-10 items-center justify-center rounded-xl bg-slate-100 text-slate-600 hover:bg-slate-200 transition-colors duration-200"
              :aria-label="isDesktopSidebarOpen ? 'إغلاق القائمة الجانبية' : 'فتح القائمة الجانبية'"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                <rect x="3" y="4" width="18" height="16" rx="2.5" />
                <line x1="15" y1="4" x2="15" y2="20" />
                <rect v-if="isDesktopSidebarOpen" x="15" y="4" width="6" height="16" rx="0" fill="currentColor" stroke="none" />
              </svg>
            </button>

            <button
              @click="isSidebarOpen = true"
              class="lg:hidden shrink-0 w-10 h-10 flex items-center justify-center rounded-xl bg-slate-100 text-slate-600 hover:bg-slate-200 transition-colors duration-200"
              aria-label="فتح القائمة"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>

            <div class="min-w-0">
              <h2 class="text-lg sm:text-xl font-bold text-slate-900 truncate">{{ currentTabLabel }}</h2>
              <p class="text-xs sm:text-sm text-slate-400 truncate">{{ currentTabIcon }} إدارة ومتابعة البيانات</p>
            </div>
          </div>
        </div>
      </header>

      <main class="p-4 sm:p-6 lg:p-8 max-w-6xl mx-auto">
        <div class="bg-white rounded-xl sm:rounded-2xl border border-slate-200 shadow-sm p-4 sm:p-6 lg:p-8 transition-all duration-300">
          <DashboardStatsTab v-if="activeTab === 'dashboard'" :stats="stats" />

          <AssemblyTab
            v-else-if="activeTab === 'assembly'"
            ref="assemblyTabRef"
            :workers-list="workersList"
            :bike-types-list="bikeTypesList"
            :bike-colors-list="bikeColorsList"
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
            @refresh-faults="loadFaults"
          />

          <WorkersTab
            v-else-if="activeTab === 'workers'"
            :workers-list="workersList"
            @open-worker-modal="openAddWorker"
            @edit-worker="openEditWorker"
            @delete-worker="handleDeleteWorker"
          />

          <CustomersTab
            v-else-if="activeTab === 'customers'"
            :customers-list="customersList"
            @open-customer-modal="openAddCustomer"
            @edit-customer="openEditCustomer"
            @delete-customer="handleDeleteCustomer"
          />
        </div>
      </main>
    </div>

    <AssemblyFormModal
      v-if="showAssemblyModal"
      :workers-list="workersList"
      :bike-types-list="bikeTypesList"
      :bike-colors-list="bikeColorsList"
      @close="showAssemblyModal = false"
      @success="handleAssemblySuccess"
      @worker-added="loadWorkers"
      @type-added="loadBikeTypes"
      @color-added="loadBikeColors"
    />

    <WorkerFormModal
      v-if="showWorkerModal"
      :worker="editingWorker"
      @close="closeWorkerModal"
      @success="handleWorkerFormSuccess"
    />

    <CustomerFormModal
      v-if="showCustomerModal"
      :customer="editingCustomer"
      @close="closeCustomerModal"
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
import { ref, computed, onMounted } from 'vue'

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
const isSidebarOpen = ref(false)
const isDesktopSidebarOpen = ref(true)

const asideClasses = computed(() => {
  const mobile = isSidebarOpen.value ? 'translate-x-0' : 'translate-x-full'
  const desktop = isDesktopSidebarOpen.value
    ? 'lg:translate-x-0 lg:w-72 lg:opacity-100 lg:pointer-events-auto lg:border-l'
    : 'lg:-translate-x-full lg:w-0 lg:opacity-0 lg:pointer-events-none lg:border-l-0'
  return `${mobile} ${desktop}`
})

const showAssemblyModal = ref(false)
const showSaleModal     = ref(false)
const showFaultModal    = ref(false)
const showWorkerModal   = ref(false)
const showCustomerModal = ref(false)

const editingWorker   = ref(null)
const editingCustomer = ref(null)

const stats                = ref({ total_chassis: 0, completed: 0, in_progress: 0, sold: 0 })
const assemblyTabRef = ref(null)
const bikeTypesList = ref([])
const bikeColorsList = ref([])
const salesList             = ref([])
const availableChassisList  = ref([])
const faultsList             = ref([])
const allChassisList         = ref([])
const workersList            = ref([])
const customersList          = ref([])

const tabs = [
  { id: 'dashboard', label: 'الإحصائيات', icon: '📈' },
  { id: 'assembly',  label: 'الورشة',      icon: '⚙️' },
  { id: 'sales',     label: 'المبيعات',    icon: '💰' },
  { id: 'faults',    label: 'الأعطال',     icon: '⚠️' },
  { id: 'workers',   label: 'العمال',      icon: '👷' },
  { id: 'customers', label: 'العملاء',     icon: '🧑‍🤝‍🧑' },
]

const currentTabLabel = computed(() => tabs.find(t => t.id === activeTab.value)?.label || '')
const currentTabIcon  = computed(() => tabs.find(t => t.id === activeTab.value)?.icon || '')

const switchTab = (tab) => {
  activeTab.value = tab
  isSidebarOpen.value = false
}

// ── API calls ───────────────────────────────────────────────────────────────
const API = import.meta.env.VITE_API_BASE_URL

const requestHeaders = {
  'Content-Type': 'application/json'
}

if (API.includes('ngrok')) {
  requestHeaders['ngrok-skip-browser-warning'] = 'true'
}

const loadStats = async () => {
  try {
    const res = await fetch(`${API}/api/stats/`, { headers: requestHeaders })
    if (res.ok) stats.value = await res.json()
  } catch (e) { console.error('إحصائيات', e) }
}

const loadBikeTypes = async () => {
  try {
    const res = await fetch(`${API}/api/bike-types/`, { headers: requestHeaders })
    if (res.ok) bikeTypesList.value = await res.json()
  } catch (e) { console.error('أنواع الدراجات', e) }
}

const loadBikeColors = async () => {
  try {
    const res = await fetch(`${API}/api/bike-colors/`, { headers: requestHeaders })
    if (res.ok) bikeColorsList.value = await res.json()
  } catch (e) { console.error('ألوان الدراجات', e) }
}

const loadSales = async () => {
  try {
    const res = await fetch(`${API}/api/sales/`, { headers: requestHeaders })
    if (res.ok) salesList.value = await res.json()
  } catch (e) { console.error('مبيعات', e) }
}

const loadAvailableChassis = async () => {
  try {
    const res = await fetch(`${API}/api/chassis/available/`, { headers: requestHeaders })
    if (res.ok) availableChassisList.value = await res.json()
  } catch (e) { console.error('هياكل متاحة', e) }
}

const loadFaults = async () => {
  try {
    const res = await fetch(`${API}/api/faults/`, { headers: requestHeaders })
    if (res.ok) faultsList.value = await res.json()
  } catch (e) { console.error('أعطال', e) }
}

const loadAllChassis = async () => {
  try {
    const res = await fetch(`${API}/api/chassis/all/`, { headers: requestHeaders })
    if (res.ok) allChassisList.value = await res.json()
  } catch (e) { console.error('كل الهياكل', e) }
}

const loadWorkers = async () => {
  try {
    const res = await fetch(`${API}/api/workers/`, { headers: requestHeaders })
    if (res.ok) workersList.value = await res.json()
  } catch (e) { console.error('عمال', e) }
}

const loadCustomers = async () => {
  try {
    const res = await fetch(`${API}/api/customers/`, { headers: requestHeaders })
    if (res.ok) customersList.value = await res.json()
  } catch (e) { console.error('عملاء', e) }
}

// ── فتح/إغلاق مودال العامل (إضافة أو تعديل) ─────────────────────────────
const openAddWorker = () => {
  editingWorker.value = null
  showWorkerModal.value = true
}
const openEditWorker = (worker) => {
  editingWorker.value = worker
  showWorkerModal.value = true
}
const closeWorkerModal = () => {
  showWorkerModal.value = false
  editingWorker.value = null
}

// ── فتح/إغلاق مودال العميل (إضافة أو تعديل) ─────────────────────────────
const openAddCustomer = () => {
  editingCustomer.value = null
  showCustomerModal.value = true
}
const openEditCustomer = (customer) => {
  editingCustomer.value = customer
  showCustomerModal.value = true
}
const closeCustomerModal = () => {
  showCustomerModal.value = false
  editingCustomer.value = null
}

// ── حذف عامل / عميل (Soft Delete عبر الباك اند) ──────────────────────────
const handleDeleteWorker = async (workerId) => {
  try {
    const res = await fetch(`${API}/api/workers/${workerId}/`, {
      method: 'DELETE',
      headers: requestHeaders
    })
    if (res.ok) {
      loadWorkers()
    } else {
      const data = await res.json()
      alert('❌ ' + (data.detail || 'تعذر حذف العامل'))
    }
  } catch (e) {
    alert('تعذر الاتصال بالسيرفر')
  }
}

const handleDeleteCustomer = async (customerId) => {
  try {
    const res = await fetch(`${API}/api/customers/${customerId}/`, {
      method: 'DELETE',
      headers: requestHeaders
    })
    if (res.ok) {
      loadCustomers()
    } else {
      const data = await res.json()
      alert('❌ ' + (data.detail || 'تعذر حذف العميل'))
    }
  } catch (e) {
    alert('تعذر الاتصال بالسيرفر')
  }
}

const handleAssemblySuccess = () => { showAssemblyModal.value = false; assemblyTabRef.value?.refresh() }
const handleSaleSuccess = () => { showSaleModal.value = false; loadSales(); loadAvailableChassis() }
const handleFaultSuccess        = () => { showFaultModal.value    = false; loadFaults() }
const handleCustomerFormSuccess = () => { closeCustomerModal(); loadCustomers() }
const handleWorkerFormSuccess   = () => { closeWorkerModal(); loadWorkers() }

onMounted(() => {
  loadStats()
  loadBikeTypes()
  loadBikeColors()
  loadSales()
  loadAvailableChassis()
  loadFaults()
  loadAllChassis()
  loadWorkers()
  loadCustomers()
})
</script>