<template>
  <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-[60]">
    <div class="bg-white rounded-2xl w-full max-w-md mx-4 shadow-2xl relative max-h-[90vh] flex flex-col">
      <transition name="fade">
        <div v-if="toast.show" class="absolute top-4 left-1/2 -translate-x-1/2 px-4 py-2 rounded-xl text-sm font-medium shadow-lg z-10"
          :class="toast.type === 'success' ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'">
          {{ toast.message }}
        </div>
      </transition>

      <div class="p-8 overflow-y-auto flex-1">
        <h3 class="text-xl font-bold mb-6">{{ isEditing ? 'تعديل القطعة' : 'إضافة قطعة جديدة' }}</h3>
        <div class="space-y-4">
          <div>
            <label class="block text-sm text-gray-600 mb-1">اسم القطعة</label>
            <input v-model="form.name" type="text" placeholder="مثال: صامولة 8 مم"
              class="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-indigo-400 focus:outline-none" />
          </div>
          <div>
            <label class="block text-sm text-gray-600 mb-1">وحدة القياس</label>
            <input v-model="form.unit" type="text" placeholder="مثال: قطعة / متر / كغ"
              class="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-indigo-400 focus:outline-none" />
          </div>
        </div>
      </div>
      <div class="flex gap-3 p-6 pt-0 shrink-0">
        <button @click="submit" :disabled="loading" class="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white py-3 rounded-xl font-bold">
          {{ loading ? 'جاري الحفظ...' : (isEditing ? 'حفظ التعديلات' : 'حفظ') }}
        </button>
        <button @click="emit('close')" class="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-800 py-3 rounded-xl font-bold">إلغاء</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuth } from '../../composables/useAuth'

const { apiFetch } = useAuth()

const props = defineProps({
  part: { type: Object, default: null }
})

const emit = defineEmits(['close', 'success'])
const loading = ref(false)
const form = ref({ name: '', unit: '' })

const isEditing = computed(() => !!props.part)

onMounted(() => {
  if (props.part) {
    form.value.name = props.part.name || ''
    form.value.unit = props.part.unit || ''
  }
})

const toast = ref({ show: false, type: 'success', message: '' })
let toastTimer = null

const showToast = (type, message, duration = 2000) => {
  clearTimeout(toastTimer)
  toast.value = { show: true, type, message }
  toastTimer = setTimeout(() => { toast.value.show = false }, duration)
}

const submit = async () => {
  if (!form.value.name.trim()) { showToast('error', 'يرجى إدخال اسم القطعة'); return }
  if (!form.value.unit.trim()) { showToast('error', 'يرجى إدخال وحدة القياس'); return }

  loading.value = true
  try {
    const url = isEditing.value ? `/api/inventory/parts/${props.part.id}/` : `/api/inventory/parts/`
    const method = isEditing.value ? 'PUT' : 'POST'

    const res = await apiFetch(url, { method, body: JSON.stringify(form.value) })
    const data = await res.json()
    if (res.ok) {
      showToast('success', isEditing.value ? '✅ تم تحديث القطعة بنجاح' : '✅ تم إضافة القطعة بنجاح')
      setTimeout(() => emit('success', data), 700)
    } else {
      showToast('error', '❌ ' + (data.detail || 'حدث خطأ'))
    }
  } catch (e) {
    showToast('error', 'تعذر الاتصال بالسيرفر')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>