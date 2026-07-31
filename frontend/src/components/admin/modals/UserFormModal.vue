<template>
  <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-[60]">
    <div class="bg-white rounded-2xl w-full max-w-md mx-4 shadow-2xl relative max-h-[90vh] flex flex-col">

      <transition name="fade">
        <div
          v-if="toast.show"
          class="absolute top-4 left-1/2 -translate-x-1/2 px-4 py-2 rounded-xl text-sm font-medium shadow-lg z-10"
          :class="toast.type === 'success' ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'"
        >
          {{ toast.message }}
        </div>
      </transition>

      <div class="p-8 overflow-y-auto flex-1">
        <h3 class="text-xl font-bold mb-6">{{ isEditing ? 'تعديل بيانات المستخدم' : 'إضافة مستخدم جديد' }}</h3>

        <div class="space-y-4">
          <div>
            <label class="block text-sm text-gray-600 mb-1">اسم المستخدم</label>
            <input
              v-model="form.username"
              type="text"
              placeholder="مثال: ahmed_admin"
              :disabled="isEditing"
              class="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-indigo-400 focus:outline-none disabled:bg-gray-50 disabled:text-gray-400"
            />
            <p v-if="isEditing" class="text-xs text-gray-400 mt-1">لا يمكن تغيير اسم المستخدم بعد الإنشاء</p>
          </div>

          <div>
            <label class="block text-sm text-gray-600 mb-1">الاسم الكامل</label>
            <input
              v-model="form.full_name"
              type="text"
              placeholder="الاسم الكامل (اختياري)"
              class="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-indigo-400 focus:outline-none"
            />
          </div>

          <div>
            <label class="block text-sm text-gray-600 mb-1">الدور</label>
            <select
              v-model="form.role"
              class="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-indigo-400 focus:outline-none bg-white"
            >
              <option v-for="r in roleOptions" :key="r.value" :value="r.value">{{ r.label }}</option>
            </select>
          </div>

          <div>
            <label class="block text-sm text-gray-600 mb-1">
              {{ isEditing ? 'كلمة مرور جديدة' : 'كلمة المرور' }}
            </label>
            <input
              v-model="form.password"
              type="password"
              :placeholder="isEditing ? 'اتركه فارغًا لعدم التغيير' : 'كلمة المرور'"
              class="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-indigo-400 focus:outline-none"
            />
          </div>

          <label v-if="isEditing" class="flex items-center gap-2 cursor-pointer select-none pt-2">
            <input type="checkbox" v-model="form.is_active" class="w-4 h-4 accent-indigo-600" />
            <span class="text-sm text-gray-600">الحساب مفعّل</span>
          </label>
        </div>
      </div>

      <div class="flex gap-3 p-6 pt-0 shrink-0">
        <button @click="submit" :disabled="loading"
          class="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white py-3 rounded-xl font-bold">
          {{ loading ? 'جاري الحفظ...' : (isEditing ? 'حفظ التعديلات' : 'حفظ') }}
        </button>
        <button @click="emit('close')"
          class="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-800 py-3 rounded-xl font-bold">
          إلغاء
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuth } from '../../../composables/useAuth'

const { apiFetch } = useAuth()

const props = defineProps({
  userData: { type: Object, default: null },
  roleOptions: { type: Array, default: () => [] }
})

const emit = defineEmits(['close', 'success'])
const loading = ref(false)

const isEditing = computed(() => !!props.userData)

const form = ref({
  username: '',
  full_name: '',
  role: props.roleOptions[0]?.value || 'operator',
  password: '',
  is_active: true
})

onMounted(() => {
  if (props.userData) {
    form.value.username = props.userData.username || ''
    form.value.full_name = props.userData.full_name || ''
    form.value.role = props.userData.role || ''
    form.value.is_active = props.userData.is_active
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
  if (!isEditing.value && !form.value.username.trim()) {
    showToast('error', 'يرجى إدخال اسم المستخدم')
    return
  }
  if (!isEditing.value && !form.value.password.trim()) {
    showToast('error', 'كلمة المرور مطلوبة عند الإنشاء')
    return
  }
  if (!form.value.role) {
    showToast('error', 'يرجى اختيار الدور')
    return
  }

  loading.value = true
  try {
    let url, method, payload

    if (isEditing.value) {
      url = `/api/users/${props.userData.id}/`
      method = 'PUT'
      payload = {
        full_name: form.value.full_name || null,
        role: form.value.role,
        is_active: form.value.is_active,
      }
      if (form.value.password.trim()) payload.password = form.value.password
    } else {
      url = `/api/users/`
      method = 'POST'
      payload = {
        username: form.value.username,
        password: form.value.password,
        full_name: form.value.full_name || null,
        role: form.value.role,
      }
    }

    const res = await apiFetch(url, {
      method,
      body: JSON.stringify(payload)
    })
    const data = await res.json()

    if (res.ok) {
      showToast('success', isEditing.value ? '✅ تم تحديث بيانات المستخدم' : '✅ تم إضافة المستخدم بنجاح')
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