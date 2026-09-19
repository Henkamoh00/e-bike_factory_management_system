<template>
  <div>
    <div class="flex items-center justify-between mb-2">
      <h2 class="text-2xl font-bold">🔄 متابعة ما بعد البيع</h2>
      <button
        @click="showReturnModal = true"
        class="bg-orange-600 hover:bg-orange-700 text-white px-5 py-2.5 rounded-2xl font-medium text-sm"
      >
        + تسجيل إرجاع
      </button>
    </div>
    <p class="text-sm text-gray-500 mb-8">
      متابعة الدراجات المباعة التي بها أعطال معلّقة، وسجل كل الدراجات التي أُرجعت بعد الشراء لأي سبب.
    </p>

    <!-- ── دراجات مباعة بها أعطال معلقة ─────────────────────────────── -->
    <div class="mb-10">
      <h3 class="text-lg font-bold text-gray-700 mb-4">⚠️ دراجات مباعة بها أعطال معلّقة</h3>

      <div v-if="loadingFaulty" class="text-center py-10 text-gray-400">جاري التحميل...</div>
      <div v-else-if="soldFaulty.length === 0" class="text-center py-10 text-gray-400 bg-white rounded-2xl shadow">
        ✅ لا توجد دراجات مباعة بأعطال معلّقة حاليًا
      </div>

      <div v-else class="bg-white rounded-3xl shadow-xl divide-y divide-gray-100">
        <div v-for="item in soldFaulty" :key="item.chassis_number" class="px-5 py-4">
          <div class="flex items-center justify-between gap-4 flex-wrap mb-2">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="font-mono font-bold text-gray-800">{{ item.chassis_number }}</span>
              <span class="text-xs bg-red-50 text-red-600 rounded-full px-2 py-0.5">{{ item.faults.length }} عطل معلّق</span>
            </div>
            <button
              @click="openReturnFor(item.chassis_number)"
              class="text-xs bg-orange-50 hover:bg-orange-100 text-orange-600 px-3 py-1.5 rounded-full font-medium"
            >
              🔄 تسجيل إرجاع
            </button>
          </div>
          <div class="text-sm text-gray-500 mb-2">{{ item.invoice_number }} — {{ item.customer_name }}</div>
          <div class="space-y-1">
            <div v-for="f in item.faults" :key="f.id" class="text-xs text-gray-500 bg-gray-50 rounded-lg px-3 py-2">
              {{ f.description }} — {{ new Date(f.reported_date).toLocaleDateString('ar-EG') }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ── سجل المرتجعات ─────────────────────────────────────────────── -->
    <div>
      <h3 class="text-lg font-bold text-gray-700 mb-4">📋 سجل المرتجعات</h3>

      <div v-if="loadingReturns" class="text-center py-10 text-gray-400">جاري التحميل...</div>
      <div v-else-if="returns.length === 0" class="text-center py-10 text-gray-400 bg-white rounded-2xl shadow">
        لا توجد دراجات مُرجَعة مسجَّلة بعد
      </div>

      <div v-else class="bg-white rounded-3xl shadow-xl divide-y divide-gray-100">
        <div v-for="r in returns" :key="r.id" class="px-5 py-4">
          <div class="flex items-center justify-between gap-4 flex-wrap mb-1">
            <span class="font-mono font-bold text-gray-800">{{ r.chassis_number }}</span>
            <span class="text-xs text-gray-400">{{ new Date(r.created_at).toLocaleDateString('ar-EG') }}</span>
          </div>
          <div class="text-sm text-gray-500 mb-1">{{ r.invoice_number }} — {{ r.customer_name }}</div>
          <!-- 🆕🛡️ السبب أصبح دائمًا إحدى القيم الثابتة الخمس (Enum) في
               الباك إند. عند "سبب آخر"، النص الفعلي مخزَّن في notes، لذا
               نعرضه هنا بدل التسمية العامة "سبب آخر" ليبقى واضحًا للمستخدم. -->
          <div class="text-sm text-gray-700">السبب: {{ effectiveReason(r) }}</div>
          <div v-if="r.notes && r.reason !== OTHER_REASON_LABEL" class="text-xs text-gray-400 mt-1">{{ r.notes }}</div>
          <div class="text-xs text-gray-400 mt-1" v-if="r.created_by_username">سجَّله: {{ r.created_by_username }}</div>
        </div>
      </div>
    </div>

    <ReturnFormModal
      v-if="showReturnModal"
      :initial-chassis-number="prefilledChassis"
      @close="closeReturnModal"
      @success="handleReturnSuccess"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuth } from '../../composables/useAuth'
import ReturnFormModal from './ReturnFormModal.vue'

const { apiFetch } = useAuth()

// 🆕🛡️ يجب أن تطابق OTHER القيمة الموجودة في ChassisReturnReason (باك إند)
// وفي reasonOptions (ReturnFormModal.vue)
const OTHER_REASON_LABEL = 'سبب آخر'

const soldFaulty = ref([])
const returns = ref([])
const loadingFaulty = ref(false)
const loadingReturns = ref(false)
const showReturnModal = ref(false)
const prefilledChassis = ref('')

// 🆕 يعرض النص الفعلي (notes) بدل التسمية العامة "سبب آخر" إن وُجد
const effectiveReason = (r) => (r.reason === OTHER_REASON_LABEL && r.notes) ? r.notes : r.reason

const loadSoldFaulty = async () => {
  loadingFaulty.value = true
  try {
    const res = await apiFetch(`/api/invoices/sold-faulty-chassis/`)
    if (res.ok) soldFaulty.value = await res.json()
  } catch (e) {
    console.error('دراجات مباعة معطوبة', e)
  } finally {
    loadingFaulty.value = false
  }
}

const loadReturns = async () => {
  loadingReturns.value = true
  try {
    const res = await apiFetch(`/api/invoices/returns/?limit=50`)
    if (res.ok) {
      const data = await res.json()
      returns.value = data.items
    }
  } catch (e) {
    console.error('سجل المرتجعات', e)
  } finally {
    loadingReturns.value = false
  }
}

const openReturnFor = (chassisNumber) => {
  prefilledChassis.value = chassisNumber
  showReturnModal.value = true
}

const closeReturnModal = () => {
  showReturnModal.value = false
  prefilledChassis.value = ''
}

const handleReturnSuccess = () => {
  closeReturnModal()
  loadSoldFaulty()
  loadReturns()
}

onMounted(() => {
  loadSoldFaulty()
  loadReturns()
})
</script>