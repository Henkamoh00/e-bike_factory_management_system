<template>
  <div class="min-h-screen bg-gray-50 font-sans">
    <!-- Header -->
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
          <div class="text-sm">
            <span class="text-gray-500">رئيس العمال:</span>
            <span class="font-semibold text-gray-800 mr-1">أحمد علي</span>
          </div>
          <button @click="logout" class="px-4 py-2 text-sm text-red-600 hover:bg-red-50 rounded-lg transition">
            تسجيل خروج
          </button>
        </div>
      </div>
    </header>

    <div class="max-w-4xl mx-auto px-4 py-8">
      <!-- Workshop Input Form -->
      <div class="bg-white rounded-3xl shadow-xl p-8 mb-8">
        <h2 class="text-3xl font-bold text-center mb-8 text-gray-800">تسجيل عملية تجميع</h2>
       
        <form @submit.prevent="() => submitAssembly(false)" class="space-y-8">
          <!-- Chassis Number -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">رقم الهيكل (Chassis Number)</label>
            <div class="relative">
              <input
                v-model="form.chassis_number"
                type="text"
                placeholder="مثال: EB-2026-00485"
                class="w-full px-5 py-4 text-xl border-2 border-gray-200 rounded-2xl focus:border-emerald-500 focus:outline-none font-mono"
                required
              />
              <div class="absolute left-5 top-1/2 -translate-y-1/2 text-gray-400">📟</div>
            </div>
          </div>

          <!-- Worker Name -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">اسم العامل</label>
            <select v-model="form.worker_name" class="w-full px-5 py-4 text-lg border-2 border-gray-200 rounded-2xl focus:border-emerald-500 focus:outline-none" required>
              <option value="">اختر العامل...</option>
              <option value="محمد أحمد">محمد أحمد</option>
              <option value="علي حسن">علي حسن</option>
              <option value="خالد إبراهيم">خالد إبراهيم</option>
              <option value="يوسف عمر">يوسف عمر</option>
            </select>
          </div>

          <!-- Assembly Stage -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-3">مرحلة التجميع</label>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
              <button type="button" @click="selectStage('تجميع_الهيكل')" 
                :class="form.stage === 'تجميع_الهيكل' ? 'ring-2 ring-emerald-500 bg-emerald-50' : 'border-2 border-gray-200'"
                class="p-6 rounded-2xl text-right hover:border-emerald-300 transition-all flex flex-col items-start">
                <div class="text-3xl mb-3">🔧</div>
                <div class="font-bold text-lg">تجميع الهيكل</div>
                <div class="text-sm text-gray-500">المرحلة الأولى</div>
              </button>

              <button type="button" @click="selectStage('توصيل_الكهرباء_والغلاف')" 
                :class="form.stage === 'توصيل_الكهرباء_والغلاف' ? 'ring-2 ring-emerald-500 bg-emerald-50' : 'border-2 border-gray-200'"
                class="p-6 rounded-2xl text-right hover:border-emerald-300 transition-all flex flex-col items-start">
                <div class="text-3xl mb-3">⚡</div>
                <div class="font-bold text-lg">توصيل الكهرباء والغلاف</div>
                <div class="text-sm text-gray-500">المرحلة الثانية</div>
              </button>

              <button type="button" @click="selectStage('تجميع_كامل')" 
                :class="form.stage === 'تجميع_كامل' ? 'ring-2 ring-emerald-500 bg-emerald-50' : 'border-2 border-gray-200'"
                class="p-6 rounded-2xl text-right hover:border-emerald-300 transition-all flex flex-col items-start">
                <div class="text-3xl mb-3">🏁</div>
                <div class="font-bold text-lg">التجميع الكامل</div>
                <div class="text-sm text-gray-500">المرحلة النهائية</div>
              </button>
            </div>
          </div>

          <button type="submit" :disabled="loading"
            class="w-full bg-emerald-600 hover:bg-emerald-700 disabled:bg-gray-400 text-white py-5 rounded-2xl text-xl font-bold transition flex items-center justify-center gap-3 shadow-lg">
            <span v-if="loading">جاري التسجيل...</span>
            <span v-else>✅ تسجيل العملية</span>
          </button>
        </form>
      </div>

      <!-- Recent Records -->
      <div class="bg-white rounded-3xl shadow p-6">
        <h3 class="font-bold text-xl mb-4 flex items-center gap-2">
          <span>آخر العمليات</span>
          <span class="text-emerald-600 text-sm font-normal">({{ recent.length }})</span>
        </h3>
        <div v-if="recent.length === 0" class="text-center py-12 text-gray-400">
          لم يتم تسجيل أي عمليات بعد
        </div>
        <div v-else class="space-y-3">
          <div v-for="record in recent" :key="record.id" class="flex justify-between items-center p-4 bg-gray-50 rounded-2xl">
            <div>
              <div class="font-mono font-bold">{{ record.chassis_number }}</div>
              <div class="text-sm text-gray-500">{{ record.worker_name }} • {{ getStageName(record.stage) }}</div>
            </div>
            <div class="text-xs text-right text-gray-400">
              {{ new Date(record.timestamp).toLocaleTimeString('ar-EG') }}
            </div>
          </div>
        </div>
      </div>
    </div>
    <!-- نافذة تأكيد مخصصة -->
    <div v-if="pendingConfirm" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div class="bg-white rounded-2xl p-6 max-w-sm mx-4 shadow-2xl">
        <div class="text-2xl mb-3">⚠️</div>
        <p class="text-gray-800 mb-6 leading-relaxed">{{ pendingConfirm }}</p>
        <div class="flex gap-3">
          <button @click="confirmForce"
            class="flex-1 bg-red-600 hover:bg-red-700 text-white py-3 rounded-xl font-bold transition">
            تأكيد التغيير
          </button>
          <button @click="cancelForce"
            class="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-800 py-3 rounded-xl font-bold transition">
            إلغاء
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const form = ref({
  chassis_number: '',
  worker_name: '',
  stage: ''
})

const recent = ref([])
const loading = ref(false)

const selectStage = (stage) => {
  form.value.stage = stage
}

const getStageName = (stage) => {
  const names = {
    'تجميع_الهيكل': 'تجميع الهيكل',
    'توصيل_الكهرباء_والغلاف': 'توصيل الكهرباء والغلاف',
    'تجميع_كامل': 'تجميع كامل'
  }
  return names[stage] || stage
}

const pendingConfirm = ref(null)  // يحمل الرسالة التحذيرية عند الحاجة

const submitAssembly = async (force = false) => {
  if (!form.value.chassis_number || !form.value.worker_name || !form.value.stage) {
    alert('يرجى ملء جميع الحقول')
    return
  }

  loading.value = true

  try {
    const url = force
      ? 'http://localhost:8000/workshop/record?force=true'
      : 'http://localhost:8000/workshop/record'

    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form.value)
    })

    const data = await response.json()

    if (response.ok) {
      alert('✅ تم تسجيل العملية بنجاح!')
      form.value.chassis_number = ''
      form.value.stage = ''
      pendingConfirm.value = null
      await loadRecent()

    } else if (response.status === 409 && data.detail && data.detail.includes('هل أنت متأكد')) {
      pendingConfirm.value = data.detail  // ← أظهر النافذة المخصصة

    } else {
      alert('❌ خطأ: ' + (data.detail || 'حدث خطأ غير معروف'))
    }

  } catch (error) {
    console.error(error)
    alert('تعذر الاتصال بالسيرفر')
  } finally {
    loading.value = false
  }
}

const confirmForce = async () => {
  pendingConfirm.value = null
  await submitAssembly(true)
}

const cancelForce = () => {
  pendingConfirm.value = null
}

const loadRecent = async () => {
  try {
    const res = await fetch('http://localhost:8000/workshop/records')
    if (res.ok) {
      recent.value = await res.json()
    }
  } catch (e) {
    console.log('لا يمكن تحميل السجلات')
  }
}

const logout = () => {
  if (confirm('هل تريد تسجيل الخروج؟')) {
    window.location.reload()
  }
}

onMounted(() => {
  loadRecent()
})
</script>