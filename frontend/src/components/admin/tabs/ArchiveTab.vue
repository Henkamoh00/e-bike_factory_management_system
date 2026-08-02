<template>
  <div>
    <div class="flex gap-2 mb-6 border-b border-gray-100 pb-4">
      <button
        v-for="sub in visibleSubTabs"
        :key="sub.id"
        @click="activeSub = sub.id"
        :class="activeSub === sub.id ? 'bg-indigo-50 text-indigo-700 font-semibold' : 'text-gray-500 hover:bg-gray-50'"
        class="px-4 py-2 rounded-xl text-sm transition"
      >
        {{ sub.icon }} {{ sub.label }}
      </button>
    </div>

    <div class="flex justify-between items-center mb-6">
      <h2 class="text-2xl font-bold">{{ currentSubLabel }} المؤرشفون</h2>
      <span class="text-sm text-gray-400">{{ items.length }} عنصر</span>
    </div>

    <!-- 🆕 توست بدل alert() لعرض نتيجة الاستعادة (نجاح/فشل) -->
    <transition name="fade">
      <div
        v-if="toast.show"
        class="fixed top-6 left-1/2 -translate-x-1/2 px-5 py-3 rounded-2xl text-sm font-medium shadow-lg z-[80] max-w-md text-center"
        :class="toast.type === 'success' ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'"
      >
        {{ toast.message }}
      </div>
    </transition>

    <div class="bg-white rounded-3xl shadow-xl overflow-hidden">
      <div v-if="loading" class="text-center py-16 text-gray-400 text-lg">جاري التحميل...</div>
      <div v-else-if="items.length === 0" class="text-center py-16 text-gray-400 text-lg">لا توجد عناصر مؤرشفة</div>

      <div v-else class="divide-y divide-gray-100">
        <div v-for="item in pagination.paginatedItems.value" :key="item.id" class="flex items-center justify-between gap-4 px-5 py-3 hover:bg-gray-50 transition">
          <div class="flex items-center gap-3 min-w-0 flex-1">
            <div class="w-9 h-9 rounded-full bg-gray-100 text-gray-500 flex items-center justify-center font-bold text-sm shrink-0">
              {{ displayName(item).charAt(0) }}
            </div>
            <div class="min-w-0">
              <div class="font-bold text-gray-800 truncate">{{ displayName(item) }}</div>
              <div class="text-xs text-gray-400 truncate">
                <span v-if="item.role_label">{{ item.role_label }}</span>
                <span v-if="item.phone">{{ item.phone }}</span>
                <span v-if="item.deleted_by_username"> • أُرشف بواسطة: {{ item.deleted_by_username }}</span>
              </div>
            </div>
          </div>

          <button
            @click="restore(item)"
            :disabled="restoringId === item.id"
            class="text-xs bg-emerald-50 hover:bg-emerald-100 text-emerald-700 px-4 py-2 rounded-full font-medium shrink-0"
          >
            {{ restoringId === item.id ? 'جاري الاستعادة...' : '♻️ استعادة' }}
          </button>
        </div>
      </div>
    </div>

    <PaginationControls
      :page="pagination.page.value"
      :total-pages="pagination.totalPages.value"
      @prev="pagination.prevPage"
      @next="pagination.nextPage"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useAuth } from '../../../composables/useAuth'
import { usePagination } from '../../../composables/usePagination'
import PaginationControls from '../../shared/PaginationControls.vue'

const displayName = (item) => item.name || item.full_name || item.username || '—'

const { apiFetch, user: currentUser } = useAuth()

// 🆕 نُصدر حدثًا للأب (DashboardView) عند نجاح الاستعادة، ليُحدّث القائمة الأصلية للتبويب المعني
const emit = defineEmits(['restore-success'])

const allSubTabs = [
  { id: 'users',      label: 'المستخدمون',     icon: '👤', endpoint: '/api/users', adminOnly: true },
  { id: 'workers',    label: 'العمال',         icon: '👷', endpoint: '/api/workers' },
  { id: 'customers',  label: 'العملاء',        icon: '🧑‍🤝‍🧑', endpoint: '/api/customers' },
  { id: 'bike_types', label: 'أنواع الدراجات', icon: '🚲', endpoint: '/api/bike-types' },
  { id: 'bike_colors',label: 'ألوان الدراجات', icon: '🎨', endpoint: '/api/bike-colors' },
]

// 🛡️ أرشيف المستخدمين حساس ومحصور بالأدمن فقط في الـ backend،
// لذا نُخفيه من الواجهة عن أي دور آخر لمنع محاولة وصول تُرفض بـ 403
const visibleSubTabs = computed(() =>
  allSubTabs.filter(sub => !sub.adminOnly || currentUser.value?.role === 'admin')
)

const activeSub = ref(visibleSubTabs.value[0]?.id || 'workers')
const currentSubLabel = computed(() => allSubTabs.find(s => s.id === activeSub.value)?.label || '')
const currentEndpoint = computed(() => allSubTabs.find(s => s.id === activeSub.value)?.endpoint || '')

const items = ref([])
const loading = ref(false)
const restoringId = ref(null)

const pagination = usePagination(items, 10)

// 🆕 حالة التوست (نفس نمط UserRolesSubTab.vue / WorkerFormModal.vue)
const toast = ref({ show: false, type: 'success', message: '' })
let toastTimer = null
const showToast = (type, message, duration = 3000) => {
  clearTimeout(toastTimer)
  toast.value = { show: true, type, message }
  toastTimer = setTimeout(() => { toast.value.show = false }, duration)
}

const loadItems = async () => {
  loading.value = true
  try {
    const res = await apiFetch(`${currentEndpoint.value}/archived/`)
    if (res.ok) {
      items.value = await res.json()
    } else {
      // 403 أو أي خطأ آخر: لا نُظهر بيانات خاطئة، فقط نُفرغ القائمة بهدوء
      items.value = []
    }
  } catch (e) {
    console.error('archive', e)
    items.value = []
  } finally {
    loading.value = false
  }
}

const restore = async (item) => {
  restoringId.value = item.id
  try {
    const res = await apiFetch(`${currentEndpoint.value}/${item.id}/restore/`, { method: 'POST' })
    const data = await res.json()
    if (res.ok) {
      items.value = items.value.filter(i => i.id !== item.id)
      showToast('success', `✅ ${data.message || 'تمت الاستعادة بنجاح'}`)
      // 🆕 نُبلّغ الأب بنوع القسم الذي حدثت فيه الاستعادة، ليُحدّث القائمة الأصلية (workersList مثلاً)
      emit('restore-success', activeSub.value)
    } else {
      showToast('error', '❌ ' + (data.detail || 'تعذر تنفيذ الاستعادة'))
    }
  } catch (e) {
    showToast('error', 'تعذر الاتصال بالسيرفر')
  } finally {
    restoringId.value = null
  }
}

watch(activeSub, loadItems)

defineExpose({ clearSelection: () => {} })

onMounted(() => {
  loadItems()
})
</script>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>