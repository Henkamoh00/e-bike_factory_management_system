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
          <!-- <button @click="switchTab('search')"    :class="activeTab === 'search'    ? 'active-tab' : ''" class="tab-btn">بحث عن دراجة</button> -->
          <button @click="switchTab('sales')"     :class="activeTab === 'sales'     ? 'active-tab' : ''" class="tab-btn">المبيعات</button>
          <button @click="switchTab('faults')"    :class="activeTab === 'faults'    ? 'active-tab' : ''" class="tab-btn">الأعطال</button>
          <button @click="switchTab('workers')"   :class="activeTab === 'workers'   ? 'active-tab' : ''" class="tab-btn">العمال</button>
          <button @click="switchTab('customers')" :class="activeTab === 'customers' ? 'active-tab' : ''" class="tab-btn">العملاء</button>
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
                    <div class="font-medium">{{ getStageName(rec.stage) }}</div>
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
        <div class="flex justify-between items-center mb-6">
          <h2 class="text-3xl font-bold">المبيعات</h2>
          <button @click="showSaleModal = true" class="bg-green-600 hover:bg-green-700 text-white px-6 py-3 rounded-2xl font-medium">+ تسجيل بيع جديد</button>
        </div>

        <!-- فلاتر المبيعات -->
        <div class="bg-white rounded-2xl shadow p-5 mb-6 flex flex-wrap gap-4 items-end">
          <div>
            <label class="block text-sm text-gray-500 mb-1">تصفية بالعميل</label>
            <select v-model="salesFilter.customer_name" class="px-4 py-2 border-2 border-gray-200 rounded-xl focus:border-indigo-400 focus:outline-none">
              <option value="">كل العملاء</option>
              <option v-for="c in customersList" :key="c.id" :value="c.id">{{ c.name }}</option>
            </select>
          </div>
          <div>
            <label class="block text-sm text-gray-500 mb-1">من تاريخ</label>
            <input type="date" v-model="salesFilter.date_from" class="px-4 py-2 border-2 border-gray-200 rounded-xl focus:border-indigo-400 focus:outline-none" />
          </div>
          <div>
            <label class="block text-sm text-gray-500 mb-1">إلى تاريخ</label>
            <input type="date" v-model="salesFilter.date_to" class="px-4 py-2 border-2 border-gray-200 rounded-xl focus:border-indigo-400 focus:outline-none" />
          </div>
          <button @click="resetFilter('sales')" class="px-4 py-2 text-gray-500 hover:text-gray-700 underline text-sm">إعادة تعيين</button>
        </div>

        <div class="bg-white rounded-3xl shadow-xl p-6">
          <div v-if="filteredSales.length === 0" class="text-center py-16 text-gray-400 text-lg">لا توجد مبيعات مطابقة</div>
          <div v-else class="space-y-4">
            <div v-for="sale in filteredSales" :key="sale.id" class="bg-gray-50 p-5 rounded-2xl flex justify-between items-center">
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
        <div class="flex justify-between items-center mb-6">
          <h2 class="text-3xl font-bold">الأعطال</h2>
          <button @click="showFaultModal = true" class="bg-red-600 hover:bg-red-700 text-white px-6 py-3 rounded-2xl font-medium">+ تسجيل عطل جديد</button>
        </div>

        <!-- فلاتر الأعطال -->
        <div class="bg-white rounded-2xl shadow p-5 mb-6 flex flex-wrap gap-4 items-end">
          <div>
            <label class="block text-sm text-gray-500 mb-1">تصفية بالحالة</label>
            <select v-model="faultsFilter.status" class="px-4 py-2 border-2 border-gray-200 rounded-xl focus:border-indigo-400 focus:outline-none">
              <option value="">كل الحالات</option>
              <option value="pending">معلق</option>
              <option value="resolved">تم إصلاحه</option>
            </select>
          </div>
          <div>
            <label class="block text-sm text-gray-500 mb-1">تصفية بالعامل</label>
            <select v-model="faultsFilter.worker_id" class="px-4 py-2 border-2 border-gray-200 rounded-xl focus:border-indigo-400 focus:outline-none">
              <option value="">كل العمال</option>
              <option v-for="w in workersList" :key="w.id" :value="w.id">{{ w.name }}</option>
            </select>
          </div>
          <button @click="resetFilter('faults')" class="px-4 py-2 text-gray-500 hover:text-gray-700 underline text-sm">إعادة تعيين</button>
        </div>

        <div class="bg-white rounded-3xl shadow-xl p-6">
          <div v-if="filteredFaults.length === 0" class="text-center py-16 text-gray-400 text-lg">لا توجد أعطال مطابقة</div>
          <div v-else class="space-y-4">
            <div v-for="fault in filteredFaults" :key="fault.id" class="bg-gray-50 p-5 rounded-2xl flex justify-between items-center">
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

      <!-- 5. العمال -->
      <div v-else-if="activeTab === 'workers'">
        <div class="flex justify-between items-center mb-6">
          <h2 class="text-3xl font-bold">العمال</h2>
          <button @click="showWorkerModal = true" class="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-3 rounded-2xl font-medium">+ إضافة عامل جديد</button>
        </div>

        <!-- فلاتر العمال -->
        <div class="bg-white rounded-2xl shadow p-5 mb-6 flex flex-wrap gap-4 items-end">
          <div>
            <label class="block text-sm text-gray-500 mb-1">تصفية بنوع المرحلة</label>
            <select v-model="workersFilter.stage" class="px-4 py-2 border-2 border-gray-200 rounded-xl focus:border-indigo-400 focus:outline-none">
              <option value="">كل المراحل</option>
              <option value="تجميع_الهيكل">تجميع الهيكل</option>
              <option value="توصيل_الكهرباء_والغلاف">توصيل الكهرباء والغلاف</option>
              <option value="تجميع_كامل">تجميع كامل</option>
            </select>
          </div>
          <button @click="resetFilter('workers')" class="px-4 py-2 text-gray-500 hover:text-gray-700 underline text-sm">إعادة تعيين</button>
        </div>

        <div class="bg-white rounded-3xl shadow-xl p-6">
          <div v-if="filteredWorkers.length === 0" class="text-center py-16 text-gray-400 text-lg">لا يوجد عمال مطابقون</div>
          <div v-else class="space-y-4">
            <div v-for="worker in filteredWorkers" :key="worker.id" class="bg-gray-50 p-5 rounded-2xl">
              <div class="flex justify-between items-start">
                <div>
                  <div class="font-bold text-lg">{{ worker.name }}</div>
                  <div class="text-sm text-gray-500 mt-1">إجمالي العمليات: {{ worker.total_records ?? 0 }}</div>
                </div>
                <div class="text-right text-sm text-gray-500">
                  <div v-if="worker.stages_summary">
                    <span v-for="(count, stage) in worker.stages_summary" :key="stage"
                      class="inline-block bg-indigo-100 text-indigo-700 rounded-full px-3 py-1 text-xs ml-1 mb-1">
                      {{ getStageName(stage) }}: {{ count }}
                    </span>
                  </div>
                </div>
              </div>
              <!-- سجلات الهيكل الخاصة بهذا العامل عند الفلترة -->
              <div v-if="workersFilter.stage && worker.filtered_records?.length" class="mt-4 space-y-2">
                <div v-for="rec in worker.filtered_records" :key="rec.id"
                  class="flex justify-between items-center bg-white px-4 py-3 rounded-xl border border-gray-200">
                  <span class="font-mono text-sm">{{ rec.chassis_number }}</span>
                  <span class="text-xs text-gray-500">{{ new Date(rec.timestamp).toLocaleString('ar-EG') }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 6. العملاء -->
      <div v-else-if="activeTab === 'customers'">
        <div class="flex justify-between items-center mb-6">
          <h2 class="text-3xl font-bold">العملاء</h2>
          <button @click="showCustomerModal = true" class="bg-purple-600 hover:bg-purple-700 text-white px-6 py-3 rounded-2xl font-medium">+ إضافة عميل جديد</button>
        </div>

        <!-- فلاتر العملاء -->
        <div class="bg-white rounded-2xl shadow p-5 mb-6 flex flex-wrap gap-4 items-end">
          <div>
            <label class="block text-sm text-gray-500 mb-1">بحث باسم العميل</label>
            <input v-model="customersFilter.name" type="text" placeholder="اسم العميل..."
              class="px-4 py-2 border-2 border-gray-200 rounded-xl focus:border-indigo-400 focus:outline-none" />
          </div>
          <button @click="resetFilter('customers')" class="px-4 py-2 text-gray-500 hover:text-gray-700 underline text-sm">إعادة تعيين</button>
        </div>

        <div class="bg-white rounded-3xl shadow-xl p-6">
          <div v-if="filteredCustomers.length === 0" class="text-center py-16 text-gray-400 text-lg">لا يوجد عملاء مطابقون</div>
          <div v-else class="space-y-4">
            <div v-for="customer in filteredCustomers" :key="customer.id" class="bg-gray-50 p-5 rounded-2xl">
              <div class="flex justify-between items-start">
                <div>
                  <div class="font-bold text-lg">{{ customer.name }}</div>
                  <div class="text-sm text-gray-500">{{ customer.phone }}</div>
                  <div class="text-sm text-gray-400">{{ customer.address }}</div>
                </div>
                <div class="text-right">
                  <span class="text-sm text-purple-600 font-medium">{{ customer.total_purchases ?? 0 }} دراجة مشتراة</span>
                </div>
              </div>
              <!-- الدراجات التي اشتراها هذا العميل -->
              <div v-if="customer.sales?.length" class="mt-4 space-y-2">
                <div v-for="sale in customer.sales" :key="sale.id"
                  class="flex justify-between items-center bg-white px-4 py-3 rounded-xl border border-gray-200">
                  <span class="font-mono text-sm">{{ sale.chassis_number }}</span>
                  <span class="text-xs text-gray-500">{{ new Date(sale.sale_date).toLocaleDateString('ar-EG') }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

    </div>

    <!-- Modal إضافة عامل -->
    <div v-if="showWorkerModal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div class="bg-white rounded-2xl p-8 w-full max-w-md mx-4 shadow-2xl">
        <h3 class="text-xl font-bold mb-6">إضافة عامل جديد</h3>
        <div class="space-y-4">
          <div>
            <label class="block text-sm text-gray-600 mb-1">اسم العامل</label>
            <input v-model="workerForm.name" type="text" placeholder="الاسم الكامل"
              class="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-indigo-400 focus:outline-none" />
          </div>
          <div>
            <label class="block text-sm text-gray-600 mb-1">رقم الهاتف (اختياري)</label>
            <input v-model="workerForm.phone" type="text" placeholder="05xxxxxxxx"
              class="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-indigo-400 focus:outline-none" />
          </div>
        </div>
        <div class="flex gap-3 mt-6">
          <button @click="submitWorker" class="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white py-3 rounded-xl font-bold">حفظ</button>
          <button @click="showWorkerModal = false" class="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-800 py-3 rounded-xl font-bold">إلغاء</button>
        </div>
      </div>
    </div>

    <!-- Modal إضافة عميل -->
    <div v-if="showCustomerModal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div class="bg-white rounded-2xl p-8 w-full max-w-md mx-4 shadow-2xl">
        <h3 class="text-xl font-bold mb-6">إضافة عميل جديد</h3>
        <div class="space-y-4">
          <div>
            <label class="block text-sm text-gray-600 mb-1">اسم العميل</label>
            <input v-model="customerForm.name" type="text" placeholder="الاسم الكامل"
              class="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-indigo-400 focus:outline-none" />
          </div>
          <div>
            <label class="block text-sm text-gray-600 mb-1">رقم الهاتف</label>
            <input v-model="customerForm.phone" type="text" placeholder="05xxxxxxxx"
              class="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-indigo-400 focus:outline-none" />
          </div>
          <div>
            <label class="block text-sm text-gray-600 mb-1">العنوان (اختياري)</label>
            <input v-model="customerForm.address" type="text" placeholder="المدينة / الحي"
              class="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-indigo-400 focus:outline-none" />
          </div>
        </div>
        <div class="flex gap-3 mt-6">
          <button @click="submitCustomer" class="flex-1 bg-purple-600 hover:bg-purple-700 text-white py-3 rounded-xl font-bold">حفظ</button>
          <button @click="showCustomerModal = false" class="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-800 py-3 rounded-xl font-bold">إلغاء</button>
        </div>
      </div>
    </div>

    <SaleModal   v-if="showSaleModal"   @close="showSaleModal = false"   @success="handleSaleSuccess" />
    <FaultModal  v-if="showFaultModal"  @close="showFaultModal = false"  @success="handleFaultSuccess" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import SaleModal  from '../components/SaleModal.vue'
import FaultModal from '../components/FaultModal.vue'

const router    = useRouter()
const activeTab = ref('dashboard')

const showSaleModal     = ref(false)
const showFaultModal    = ref(false)
const showWorkerModal   = ref(false)
const showCustomerModal = ref(false)

const stats          = ref({ total_chassis: 0, completed: 0, in_progress: 0, sold: 0 })
const searchQuery    = ref('')
const chassisHistory = ref(null)
const salesList      = ref([])
const faultsList     = ref([])
const workersList    = ref([])
const customersList  = ref([])

// ── فلاتر ──────────────────────────────────────────────────────────────────
const salesFilter     = ref({ customer_name: '', date_from: '', date_to: '' })
const faultsFilter    = ref({ status: '', worker_id: '' })
const workersFilter   = ref({ stage: '' })
const customersFilter = ref({ name: '' })

// ── نماذج الإضافة ───────────────────────────────────────────────────────────
const workerForm   = ref({ name: '', phone: '' })
const customerForm = ref({ name: '', phone: '', address: '' })

// ── Computed مع الفلاتر ─────────────────────────────────────────────────────
const filteredSales = computed(() => {
  return salesList.value.filter(s => {
    if (salesFilter.value.customer_name && s.customer_name !== salesFilter.value.customer_name) return false
    if (salesFilter.value.date_from && new Date(s.sale_date) < new Date(salesFilter.value.date_from)) return false
    if (salesFilter.value.date_to   && new Date(s.sale_date) > new Date(salesFilter.value.date_to))   return false
    return true
  })
})

const filteredFaults = computed(() => {
  return faultsList.value.filter(f => {
    if (faultsFilter.value.status    && f.status    !== faultsFilter.value.status)    return false
    if (faultsFilter.value.worker_id && f.worker_id !== faultsFilter.value.worker_id) return false
    return true
  })
})

const filteredWorkers = computed(() => {
  if (!workersFilter.value.stage) return workersList.value
  return workersList.value
    .map(w => ({
      ...w,
      filtered_records: (w.records || []).filter(r => r.stage === workersFilter.value.stage)
    }))
    .filter(w => w.filtered_records.length > 0)
})

const filteredCustomers = computed(() => {
  const q = customersFilter.value.name.trim().toLowerCase()
  if (!q) return customersList.value
  return customersList.value.filter(c => c.name.toLowerCase().includes(q))
})

// ── helpers ─────────────────────────────────────────────────────────────────
const getStageName = (stage) => {
  const names = {
    'تجميع_الهيكل':           'تجميع الهيكل',
    'توصيل_الكهرباء_والغلاف': 'توصيل الكهرباء والغلاف',
    'تجميع_كامل':             'تجميع كامل',
  }
  return names[stage] || stage
}

const switchTab = (tab) => { activeTab.value = tab }
const goToWorkshop = () => router.push('/')

const resetFilter = (type) => {
  if (type === 'sales')     salesFilter.value     = { customer_name: '', date_from: '', date_to: '' }
  if (type === 'faults')    faultsFilter.value    = { status: '', worker_id: '' }
  if (type === 'workers')   workersFilter.value   = { stage: '' }
  if (type === 'customers') customersFilter.value = { name: '' }
}

// ── API calls ───────────────────────────────────────────────────────────────
const API = 'http://localhost:8000'

const loadStats = async () => {
  try {
    const res = await fetch(`${API}/api/admin/dashboard/`)
    if (res.ok) stats.value = await res.json()
  } catch (e) { console.error('إحصائيات', e) }
}

const searchChassis = async () => {
  if (!searchQuery.value.trim()) return
  try {
    const res = await fetch(`${API}/workshop/history/${searchQuery.value.trim()}`)
    if (res.ok) chassisHistory.value = await res.json()
    else { alert('لم يتم العثور على هذا الهيكل'); chassisHistory.value = null }
  } catch (e) { alert('خطأ في الاتصال') }
}

const loadSales = async () => {
  try {
    const res = await fetch(`${API}/admin/sales/`)
    if (res.ok) salesList.value = await res.json()
  } catch (e) { console.error('مبيعات', e) }
}

const loadFaults = async () => {
  try {
    const res = await fetch(`${API}/admin/faults/`)
    if (res.ok) faultsList.value = await res.json()
  } catch (e) { console.error('أعطال', e) }
}

const loadWorkers = async () => {
  try {
    const res = await fetch(`${API}/api/admin/workers/`)
    if (res.ok) workersList.value = await res.json()
  } catch (e) { console.error('عمال', e) }
}

const loadCustomers = async () => {
  try {
    const res = await fetch(`${API}/api/admin/customers/`)
    if (res.ok) customersList.value = await res.json()
  } catch (e) { console.error('عملاء', e) }
}

const submitWorker = async () => {
  if (!workerForm.value.name.trim()) { alert('يرجى إدخال اسم العامل'); return }
  try {
    const res = await fetch(`${API}/api/admin/workers/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(workerForm.value)
    })
    if (res.ok) {
      showWorkerModal.value = false
      workerForm.value = { name: '', phone: '' }
      await loadWorkers()
    } else {
      const d = await res.json()
      alert('❌ ' + (d.detail || 'حدث خطأ'))
    }
  } catch (e) { alert('خطأ في الاتصال') }
}

const submitCustomer = async () => {
  if (!customerForm.value.name.trim()) { alert('يرجى إدخال اسم العميل'); return }
  try {
    const res = await fetch(`${API}/api/admin/customers/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(customerForm.value)
    })
    if (res.ok) {
      showCustomerModal.value = false
      customerForm.value = { name: '', phone: '', address: '' }
      await loadCustomers()
    } else {
      const d = await res.json()
      alert('❌ ' + (d.detail || 'حدث خطأ'))
    }
  } catch (e) { alert('خطأ في الاتصال') }
}

const handleSaleSuccess  = () => { showSaleModal.value  = false; loadSales() }
const handleFaultSuccess = () => { showFaultModal.value = false; loadFaults() }

onMounted(() => {
  loadStats()
  loadSales()
  loadFaults()
  loadWorkers()
  loadCustomers()
})
</script>

<style scoped>
.tab-btn { padding: 8px 20px; border-radius: 9999px; transition: all 0.3s; }
.active-tab { background-color: #4f46e5; color: white !important; }
</style>