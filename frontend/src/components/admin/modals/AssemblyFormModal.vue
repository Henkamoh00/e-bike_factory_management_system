<template>
  <div class="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
    <div class="bg-white rounded-3xl shadow-2xl w-full max-w-lg mx-4">
      <div class="p-8">
        <h2 class="text-2xl font-bold mb-6 text-emerald-700">تسجيل عملية تجميع</h2>

        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-2">رقم الهيكل</label>
          <input
            v-model="form.chassis_number"
            type="text"
            placeholder="مثال: EB-2026-00485"
            class="w-full px-5 py-4 text-lg border-2 border-gray-200 rounded-2xl focus:border-emerald-500 focus:outline-none font-mono"
          />
        </div>

        <div class="mb-2">
          <SearchableSelect
            v-model="form.worker_name"
            :options="workerOptions"
            label="اسم العامل"
            placeholder="اختر العامل"
            :allow-empty="false"
          />
        </div>
        <button
          type="button"
          @click="showWorkerForm = true"
          class="text-sm text-indigo-600 hover:text-indigo-800 underline mb-4"
        >
          + إضافة عامل جديد
        </button>

        <div class="mb-2 mt-2">
          <label class="block text-sm font-medium text-gray-700 mb-3">مرحلة التجميع</label>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
            <button
              type="button"
              @click="form.stage = 'تجميع_الهيكل'"
              :class="form.stage === 'تجميع_الهيكل' ? 'ring-2 ring-emerald-500 bg-emerald-50' : 'border-2 border-gray-200'"
              class="p-4 rounded-2xl hover:border-emerald-300 transition-all flex flex-col items-start"
            >
              <div class="text-2xl mb-2">🔧</div>
              <div class="font-bold">تجميع الهيكل</div>
              <div class="text-xs text-gray-500">المرحلة الأولى</div>
            </button>

            <button
              type="button"
              @click="form.stage = 'توصيل_الكهرباء_والغلاف'"
              :class="form.stage === 'توصيل_الكهرباء_والغلاف' ? 'ring-2 ring-emerald-500 bg-emerald-50' : 'border-2 border-gray-200'"
              class="p-4 rounded-2xl hover:border-emerald-300 transition-all flex flex-col items-start"
            >
              <div class="text-2xl mb-2">⚡</div>
              <div class="font-bold">توصيل الكهرباء والغلاف</div>
              <div class="text-xs text-gray-500">المرحلة الثانية</div>
            </button>

            <button
              type="button"
              @click="form.stage = 'تجميع_كامل'"
              :class="form.stage === 'تجميع_كامل' ? 'ring-2 ring-emerald-500 bg-emerald-50' : 'border-2 border-gray-200'"
              class="p-4 rounded-2xl hover:border-emerald-300 transition-all flex flex-col items-start"
            >
              <div class="text-2xl mb-2">🏁</div>
              <div class="font-bold">التجميع الكامل</div>
              <div class="text-xs text-gray-500">المرحلة النهائية</div>
            </button>
          </div>
        </div>

        <!-- حقل النوع: يظهر فقط عند تجميع_الهيكل أو تجميع_كامل -->
        <div v-if="showTypeField" class="mb-2 mt-4">
          <SearchableSelect
            v-model="form.bike_type_name"
            :options="typeOptions"
            label="نوع الدراجة"
            placeholder="اختر النوع"
            :allow-empty="false"
          />
        </div>
        <button
          v-if="showTypeField"
          type="button"
          @click="showTypeForm = true"
          class="text-sm text-indigo-600 hover:text-indigo-800 underline mb-4"
        >
          + إضافة نوع جديد
        </button>

        <!-- حقل اللون: يظهر فقط عند توصيل_الكهرباء_والغلاف أو تجميع_كامل -->
        <div v-if="showColorField" class="mb-2 mt-2">
          <SearchableSelect
            v-model="form.bike_color_name"
            :options="colorOptions"
            label="لون الدراجة"
            placeholder="اختر اللون"
            :allow-empty="false"
          />
        </div>
        <button
          v-if="showColorField"
          type="button"
          @click="showColorForm = true"
          class="text-sm text-indigo-600 hover:text-indigo-800 underline mb-2"
        >
          + إضافة لون جديد
        </button>
      </div>

      <div class="border-t p-4 flex gap-3">
        <button @click="cancel" class="flex-1 py-4 rounded-2xl font-medium text-gray-600 hover:bg-gray-100">إلغاء</button>
        <button @click="() => submit()" :disabled="loading" class="flex-1 py-4 bg-emerald-600 hover:bg-emerald-700 text-white rounded-2xl font-bold">
          {{ loading ? 'جاري التسجيل...' : '✅ تسجيل العملية' }}
        </button>
      </div>
    </div>

    <!-- تأكيد الكتابة فوق عامل مختلف -->
    <div v-if="pendingConfirm" class="fixed inset-0 bg-black/60 flex items-center justify-center z-[70]">
      <div class="bg-white rounded-2xl p-8 max-w-md mx-4 shadow-2xl">
        <div class="text-4xl mb-4">⚠️</div>
        <p class="text-gray-800 text-lg mb-8">{{ pendingConfirm }}</p>
        <div class="flex gap-3">
          <button @click="confirmForce" class="flex-1 bg-red-600 text-white py-4 rounded-xl">نعم، أكمل التسجيل</button>
          <button @click="pendingConfirm = null" class="flex-1 bg-gray-100 py-4 rounded-xl">إلغاء</button>
        </div>
      </div>
    </div>

    <!-- مودالات متداخلة -->
    <WorkerFormModal
      v-if="showWorkerForm"
      @close="showWorkerForm = false"
      @success="handleWorkerAdded"
    />
    <BikeTypeFormModal
      v-if="showTypeForm"
      @close="showTypeForm = false"
      @success="handleTypeAdded"
    />
    <BikeColorFormModal
      v-if="showColorForm"
      @close="showColorForm = false"
      @success="handleColorAdded"
    />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import SearchableSelect from '../../shared/SearchableSelect.vue'
import WorkerFormModal from '../../admin/modals/WorkerFormModal.vue'
import BikeTypeFormModal from '../../admin/modals/BikeTypeFormModal.vue'
import BikeColorFormModal from '../../admin/modals/BikeColorFormModal.vue'

const API = import.meta.env.VITE_API_BASE_URL

// إنشاء كائن الـ Headers الأساسي
const requestHeaders = {
  'Content-Type': 'application/json'
}

// 3. إضافة الـ Header الخاص بـ ngrok فقط إذا كان الرابط يحتوي على كلمة ngrok
if (API.includes('ngrok')) {
  requestHeaders['ngrok-skip-browser-warning'] = 'true'
}

const emit = defineEmits(['close', 'success', 'worker-added', 'type-added', 'color-added'])
const loading = ref(false)
const pendingConfirm = ref(null)
const showWorkerForm = ref(false)
const showTypeForm = ref(false)
const showColorForm = ref(false)

const props = defineProps({
  workersList: { type: Array, default: () => [] },
  bikeTypesList: { type: Array, default: () => [] },
  bikeColorsList: { type: Array, default: () => [] }
})

const workerOptions = computed(() =>
  props.workersList.map(w => ({ label: w.name, value: w.name }))
)
const typeOptions = computed(() =>
  props.bikeTypesList.map(t => ({ label: t.name, value: t.name }))
)
const colorOptions = computed(() =>
  props.bikeColorsList.map(c => ({ label: c.name, value: c.name }))
)

const form = ref({
  chassis_number: '',
  worker_name: '',
  stage: '',
  bike_type_name: '',
  bike_color_name: ''
})

const showTypeField = computed(() =>
  form.value.stage === 'تجميع_الهيكل' || form.value.stage === 'تجميع_كامل'
)
const showColorField = computed(() =>
  form.value.stage === 'توصيل_الكهرباء_والغلاف' || form.value.stage === 'تجميع_كامل'
)

const handleWorkerAdded = (newWorker) => {
  showWorkerForm.value = false
  form.value.worker_name = newWorker.name
  emit('worker-added')
}
const handleTypeAdded = (newType) => {
  showTypeForm.value = false
  form.value.bike_type_name = newType.name
  emit('type-added')
}
const handleColorAdded = (newColor) => {
  showColorForm.value = false
  form.value.bike_color_name = newColor.name
  emit('color-added')
}

const submit = async (force = false) => {
  if (!form.value.chassis_number || !form.value.worker_name || !form.value.stage) {
    alert('يرجى ملء جميع الحقول')
    return
  }
  if (showTypeField.value && !form.value.bike_type_name) {
    alert('يرجى اختيار نوع الدراجة')
    return
  }
  if (showColorField.value && !form.value.bike_color_name) {
    alert('يرجى اختيار لون الدراجة')
    return
  }

  loading.value = true
  try {
    const url = force
      ? `${API}/api/assembly/record?force=true/`
      : `${API}/api/assembly/record/`

    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json',
      requestHeaders
       },
      body: JSON.stringify(form.value)
    })

    const data = await res.json()

    if (res.ok) {
      alert('✅ تم تسجيل العملية بنجاح!')
      pendingConfirm.value = null
      emit('success')
    } else if (res.status === 409 && data.detail?.includes('هل أنت متأكد')) {
      pendingConfirm.value = data.detail
    } else {
      alert('❌ ' + (data.detail || 'حدث خطأ'))
    }
  } catch (e) {
    alert('تعذر الاتصال بالسيرفر')
  } finally {
    loading.value = false
  }
}

const confirmForce = () => submit(true)
const cancel = () => emit('close')
</script>