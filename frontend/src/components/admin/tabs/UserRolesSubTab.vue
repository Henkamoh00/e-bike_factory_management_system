<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <div>
        <h3 class="text-xl font-bold">إدارة الأدوار والصلاحيات</h3>
        <p class="text-sm text-gray-500 mt-1">الأدوار الأساسية الثلاثة محمية ولا يمكن حذفها. يمكنك التحكم في التبويبات المتاحة لكل دور.</p>
      </div>
      <button
        v-if="isAdmin"
        @click="openAdd"
        class="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-3 rounded-2xl font-medium"
      >
        + إضافة دور جديد
      </button>
    </div>

    <div v-if="loading" class="text-center py-16 text-gray-400 text-lg">جاري التحميل...</div>

    <div v-else class="space-y-3">
      <div v-for="role in roles" :key="role.id" class="p-4 border-2 border-gray-100 rounded-2xl">
        <div class="flex items-center justify-between gap-4">
          <div class="flex items-center gap-3 min-w-0 flex-1">
            <span class="text-2xl shrink-0">{{ role.is_system ? '🔒' : '🔑' }}</span>
            <div class="min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="font-bold text-gray-800">{{ role.label }}</span>
                <span class="text-xs bg-gray-50 text-gray-500 px-2 py-0.5 rounded-full font-mono">{{ role.name }}</span>
                <span class="text-xs bg-indigo-50 text-indigo-600 px-2 py-0.5 rounded-full">{{ role.users_count }} مستخدم</span>
              </div>
              <div v-if="role.description" class="text-xs text-gray-400 mt-1 truncate">{{ role.description }}</div>

              <!-- عرض مختصر للتبويبات المسموحة -->
              <div class="flex flex-wrap gap-1.5 mt-2">
                <span v-if="role.name === 'admin'" class="text-xs bg-emerald-50 text-emerald-600 px-2 py-0.5 rounded-full">
                  ✅ كل التبويبات (دائمًا)
                </span>
                <template v-else>
                  <span
                    v-for="tabId in role.allowed_tabs"
                    :key="tabId"
                    class="text-xs bg-emerald-50 text-emerald-600 px-2 py-0.5 rounded-full"
                  >
                    {{ tabLabel(tabId) }}
                  </span>
                  <span v-if="!role.allowed_tabs?.length" class="text-xs bg-red-50 text-red-500 px-2 py-0.5 rounded-full">
                    🚫 لا يملك وصولاً لأي تبويب
                  </span>
                </template>
              </div>
            </div>
          </div>

          <div v-if="isAdmin" class="flex items-center gap-1 shrink-0">
            <button @click="openEdit(role)" class="w-8 h-8 flex items-center justify-center rounded-lg text-gray-400 hover:bg-indigo-50 hover:text-indigo-600 transition">
              ✏️
            </button>
            <button
              v-if="!role.is_system"
              @click="askDelete(role)"
              class="w-8 h-8 flex items-center justify-center rounded-lg text-gray-400 hover:bg-red-50 hover:text-red-600 transition"
            >
              🗑️
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- مودال إضافة / تعديل -->
    <div v-if="showModal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-[60] p-4">
      <div class="bg-white rounded-2xl w-full max-w-lg shadow-2xl relative max-h-[90vh] flex flex-col">

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
          <h3 class="text-xl font-bold mb-6">{{ isEditing ? 'تعديل الدور' : 'إضافة دور جديد' }}</h3>

          <div class="space-y-4">
            <div>
              <label class="block text-sm text-gray-600 mb-1">المعرّف (بالإنجليزية، بدون مسافات)</label>
              <input
                v-model="form.name"
                type="text"
                :disabled="isEditing"
                placeholder="مثال: accountant"
                class="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-indigo-400 focus:outline-none disabled:bg-gray-50 disabled:text-gray-400"
              />
              <p v-if="isEditing" class="text-xs text-gray-400 mt-1">لا يمكن تغيير المعرّف بعد الإنشاء</p>
            </div>
            <div>
              <label class="block text-sm text-gray-600 mb-1">الاسم المعروض (عربي)</label>
              <input v-model="form.label" type="text" placeholder="مثال: محاسب"
                class="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-indigo-400 focus:outline-none" />
            </div>
            <div>
              <label class="block text-sm text-gray-600 mb-1">الوصف (اختياري)</label>
              <textarea v-model="form.description" placeholder="وصف مختصر للدور"
                class="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-indigo-400 focus:outline-none h-20"></textarea>
            </div>

            <!-- ── صلاحيات التبويبات ───────────────────────────────── -->
            <div class="pt-2">
              <label class="block text-sm font-medium text-gray-700 mb-3">التبويبات المتاحة لهذا الدور</label>

              <div v-if="isEditingAdminRole" class="p-4 bg-emerald-50 text-emerald-700 text-sm rounded-2xl">
                ✅ دور "مدير" لديه دائمًا وصول كامل لكل التبويبات، ولا يمكن تقييده لأسباب أمنية (لمنع قفل النظام بالكامل).
              </div>

              <div v-else class="grid grid-cols-2 gap-2">
                <label
                  v-for="tab in TAB_DEFINITIONS"
                  :key="tab.id"
                  class="flex items-center gap-2 p-3 border-2 rounded-xl cursor-pointer transition select-none"
                  :class="form.allowed_tabs.includes(tab.id) ? 'border-indigo-400 bg-indigo-50' : 'border-gray-200 hover:border-gray-300'"
                >
                  <input
                    type="checkbox"
                    :checked="form.allowed_tabs.includes(tab.id)"
                    @change="toggleTab(tab.id)"
                    class="w-4 h-4 accent-indigo-600 rounded"
                  />
                  <span class="text-sm">{{ tab.icon }} {{ tab.label }}</span>
                </label>
              </div>
            </div>
          </div>
        </div>

        <div class="flex gap-3 p-6 pt-4 border-t shrink-0">
          <button @click="submit" :disabled="saving" class="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white py-3 rounded-xl font-bold">
            {{ saving ? 'جاري الحفظ...' : (isEditing ? 'حفظ التعديلات' : 'حفظ') }}
          </button>
          <button @click="closeModal" class="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-800 py-3 rounded-xl font-bold">إلغاء</button>
        </div>
      </div>
    </div>

    <!-- تأكيد الحذف -->
    <div v-if="pendingDelete" class="fixed inset-0 bg-black/60 flex items-center justify-center z-[70]">
      <div class="bg-white rounded-2xl p-8 max-w-md mx-4 shadow-2xl">
        <div class="text-4xl mb-4">⚠️</div>
        <p class="text-gray-800 text-lg mb-8">
          هل أنت متأكد من حذف دور "<strong>{{ pendingDelete.label }}</strong>"؟
          <br /><span class="text-sm text-gray-400">هذا الإجراء لا يمكن التراجع عنه.</span>
        </p>
        <div class="flex gap-3">
          <button @click="confirmDelete" class="flex-1 bg-red-600 text-white py-4 rounded-xl">نعم، احذف</button>
          <button @click="pendingDelete = null" class="flex-1 bg-gray-100 py-4 rounded-xl">إلغاء</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuth } from '../../../composables/useAuth'
import { TAB_DEFINITIONS } from '../../../composables/useTabPermissions'

const { apiFetch, user: currentUser } = useAuth()

const roles = ref([])
const loading = ref(false)
const isAdmin = computed(() => currentUser.value?.role === 'admin')

const showModal = ref(false)
const editingRole = ref(null)
const isEditing = computed(() => !!editingRole.value)
const isEditingAdminRole = computed(() => editingRole.value?.name === 'admin')
const saving = ref(false)
const pendingDelete = ref(null)

const form = ref({ name: '', label: '', description: '', allowed_tabs: [] })

const tabLabel = (tabId) => TAB_DEFINITIONS.find(t => t.id === tabId)?.label || tabId

const toast = ref({ show: false, type: 'success', message: '' })
let toastTimer = null
const showToast = (type, message, duration = 2200) => {
  clearTimeout(toastTimer)
  toast.value = { show: true, type, message }
  toastTimer = setTimeout(() => { toast.value.show = false }, duration)
}

const loadRoles = async () => {
  loading.value = true
  try {
    const res = await apiFetch('/api/roles/')
    if (res.ok) roles.value = await res.json()
  } catch (e) {
    console.error('أدوار', e)
  } finally {
    loading.value = false
  }
}

const toggleTab = (tabId) => {
  const idx = form.value.allowed_tabs.indexOf(tabId)
  if (idx === -1) {
    form.value.allowed_tabs.push(tabId)
  } else {
    form.value.allowed_tabs.splice(idx, 1)
  }
}

const openAdd = () => {
  editingRole.value = null
  form.value = { name: '', label: '', description: '', allowed_tabs: [] }
  showModal.value = true
}

const openEdit = (role) => {
  editingRole.value = role
  form.value = {
    name: role.name,
    label: role.label,
    description: role.description || '',
    allowed_tabs: [...(role.allowed_tabs || [])]
  }
  showModal.value = true
}

const closeModal = () => {
  showModal.value = false
  editingRole.value = null
}

const submit = async () => {
  if (!isEditing.value && !form.value.name.trim()) {
    showToast('error', 'يرجى إدخال معرّف الدور')
    return
  }
  if (!form.value.label.trim()) {
    showToast('error', 'يرجى إدخال الاسم المعروض')
    return
  }

  saving.value = true
  try {
    const url = isEditing.value ? `/api/roles/${editingRole.value.id}/` : `/api/roles/`
    const method = isEditing.value ? 'PUT' : 'POST'
    const payload = isEditing.value
      ? { label: form.value.label, description: form.value.description || null, allowed_tabs: form.value.allowed_tabs }
      : { name: form.value.name, label: form.value.label, description: form.value.description || null, allowed_tabs: form.value.allowed_tabs }

    const res = await apiFetch(url, { method, body: JSON.stringify(payload) })
    const data = await res.json()

    if (res.ok) {
      showToast('success', isEditing.value ? '✅ تم تحديث الدور والصلاحيات' : '✅ تم إضافة الدور بنجاح')
      setTimeout(() => { closeModal(); loadRoles() }, 600)
    } else {
      showToast('error', '❌ ' + (data.detail || 'حدث خطأ'))
    }
  } catch (e) {
    showToast('error', 'تعذر الاتصال بالسيرفر')
  } finally {
    saving.value = false
  }
}

const askDelete = (role) => { pendingDelete.value = role }

const confirmDelete = async () => {
  if (!pendingDelete.value) return
  try {
    const res = await apiFetch(`/api/roles/${pendingDelete.value.id}/`, { method: 'DELETE' })
    const data = await res.json()
    if (res.ok) {
      pendingDelete.value = null
      loadRoles()
    } else {
      alert('❌ ' + (data.detail || 'تعذر حذف الدور'))
      pendingDelete.value = null
    }
  } catch (e) {
    alert('تعذر الاتصال بالسيرفر')
  }
}

onMounted(() => {
  loadRoles()
})
</script>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>