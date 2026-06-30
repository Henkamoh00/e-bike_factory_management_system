<template>
  <div class="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
    <div class="bg-white rounded-3xl shadow-2xl w-full max-w-md mx-4">
      <div class="p-8">
        <h2 class="text-2xl font-bold mb-6">تسجيل بيع جديد</h2>
        
        <input v-model="form.chassis_number" placeholder="رقم الهيكل" class="w-full p-4 border rounded-2xl mb-4" />
        <input v-model="form.customer_name" placeholder="اسم العميل الكامل" class="w-full p-4 border rounded-2xl mb-4" />
        <input v-model="form.phone" placeholder="رقم الجوال" class="w-full p-4 border rounded-2xl mb-4" />
        <textarea v-model="form.notes" placeholder="ملاحظات (اختياري)" class="w-full p-4 border rounded-2xl h-24"></textarea>
      </div>

      <div class="border-t p-4 flex gap-3">
        <button @click="cancel" class="flex-1 py-4 rounded-2xl font-medium text-gray-600 hover:bg-gray-100">إلغاء</button>
        <button @click="submit" :disabled="loading" class="flex-1 py-4 bg-green-600 hover:bg-green-700 text-white rounded-2xl font-bold">
          {{ loading ? 'جاري التسجيل...' : 'تسجيل البيع' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const emit = defineEmits(['close', 'success'])
const loading = ref(false)

const form = ref({
  chassis_number: '',
  customer_name: '',
  phone: '',
  notes: ''
})

const submit = async () => {
  if (!form.value.chassis_number || !form.value.customer_name) {
    alert('رقم الهيكل واسم العميل مطلوبان')
    return
  }

  loading.value = true

  try {
    const res = await fetch('http://localhost:8000/admin/sales/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form.value)
    })

    const data = await res.json()

    if (res.ok) {
      alert('✅ تم تسجيل البيع بنجاح!')
      emit('success')
    } else {
      alert('❌ ' + (data.detail || 'حدث خطأ'))
    }
  } catch (e) {
    alert('تعذر الاتصال بالسيرفر')
  } finally {
    loading.value = false
  }
}

const cancel = () => emit('close')
</script>