<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-3xl font-bold">المستخدمون</h2>
      <button @click="openAdd" class="bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-3 rounded-2xl font-medium">
        + إضافة مستخدم جديد
      </button>
    </div>

    <div class="bg-white rounded-2xl shadow p-5 mb-6 flex flex-wrap gap-4 items-end">
      <div>
        <label class="block text-sm text-gray-500 mb-1">بحث باسم المستخدم</label>
        <input
          v-model="pg.search.value"
          type="text"
          placeholder="اكتب اسم المستخدم..."
          class="px-4 py-2 border-2 border-gray-200 rounded-xl focus:border-indigo-400 focus:outline-none"
        />
      </div>
    </div>

    <BulkActionsBar :count="bulk.selectedCount.value" @clear="bulk.clear">
      <button
        @click="openBulkDeactivate"
        :disabled="bulkLoading"
        class="bg-white/20 hover:bg-white/30 text-white px-4 py-2 rounded-xl text-sm font-medium"
      >
        🚫 تعطيل المحدد ({{ bulk.selectedCount.value }})
      </button>
      <button
        @click="openBulkActivate"
        :disabled="bulkLoading"
        class="bg-white/20 hover:bg-white/30 text-white px-4 py-2 rounded-xl text-sm font-medium"
      >
        ✅ تفعيل المحدد ({{ bulk.selectedCount.value }})
      </button>
      <button
        @click="openBulkDelete"
        :disabled="bulkLoading"
        class="bg-white/20 hover:bg-white/30 text-white px-4 py-2 rounded-xl text-sm font-medium"
      >
        🗑️ حذف المحدد ({{ bulk.selectedCount.value }})
      </button>
    </BulkActionsBar>

    <div class="bg-white rounded-3xl shadow-xl overflow-hidden">
      <div v-if="pg.loading.value" class="text-center py-16 text-gray-400 text-lg">جاري التحميل...</div>
      <div v-else-if="pg.items.value.length === 0" class="text-center py-16 text-gray-400 text-lg">لا يوجد مستخدمون مطابقون</div>

      <template v-else>
        <div class="flex items-center gap-3 px-5 py-2 bg-gray-50 border-b border-gray-100">
          <input
            type="checkbox"
            :checked="bulk.pageAllSelected.value"
            :disabled="pageEligibleCount === 0"
            @change="bulk.toggleAllOnPage"
            class="w-4 h-4 accent-indigo-600 rounded disabled:opacity-30 disabled:cursor-not-allowed"
          />
          <span class="text-xs text-gray-400">تحديد الكل بهذه الصفحة ({{ pageEligibleCount }} من {{ pg.items.value.length }})</span>
        </div>

        <div class="divide-y divide-gray-100">
          <div
            v-for="u in pg.items.value"
            :key="u.id"
            class="flex items-center justify-between gap-4 px-5 py-3 hover:bg-gray-50 transition"
            :class="{ 'opacity-50': !u.is_active }"
          >
            <div class="flex items-center gap-3 min-w-0 flex-1">
              <input
                type="checkbox"
                :checked="bulk.isSelected(u)"
                :disabled="u.id === currentUser?.id || isTargetProtected(u)"
                @change="bulk.toggleOne(u)"
                class="w-4 h-4 accent-indigo-600 rounded shrink-0 disabled:opacity-20 disabled:cursor-not-allowed"
              />

              <div class="w-9 h-9 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-sm shrink-0">
                {{ (u.full_name || u.username).charAt(0) }}
              </div>
              <div class="min-w-0">
                <div class="flex items-center gap-2 flex-wrap">
                  <span class="font-bold text-gray-800 truncate">{{ u.full_name || u.username }}</span>
                  <span class="text-xs bg-indigo-50 text-indigo-600 font-medium px-2 py-0.5 rounded-full">{{ u.role_label || u.role }}</span>
                  <span v-if="!u.is_active" class="text-xs bg-gray-100 text-gray-500 rounded-full px-2 py-0.5">معطّل</span>
                  <span v-if="u.id === currentUser?.id" class="text-xs bg-amber-50 text-amber-600 rounded-full px-2 py-0.5">أنت</span>
                </div>
                <div class="text-xs text-gray-400 truncate">
                  @{{ u.username }}
                  <span v-if="u.last_login"> • آخر دخول: {{ new Date(u.last_login).toLocaleString('ar-EG') }}</span>
                  <span v-else> • لم يسجل الدخول بعد</span>
                </div>
              </div>
            </div>

            <div class="flex items-center gap-1 shrink-0">
              <button @click="openEdit(u)" class="w-8 h-8 flex items-center justify-center rounded-lg text-gray-400 hover:bg-indigo-50 hover:text-indigo-600 transition">
                ✏️
              </button>
              <button
                v-if="u.id !== currentUser?.id && !isTargetProtected(u)"
                @click="askDelete(u)"
                class="w-8 h-8 flex items-center justify-center rounded-lg text-gray-400 hover:bg-red-50 hover:text-red-600 transition"
              >
                🗑️
              </button>
            </div>
          </div>
        </div>
      </template>
    </div>

    <div v-if="pg.totalPages.value > 1" class="flex justify-center items-center gap-3 mt-6">
      <button @click="pg.prevPage" :disabled="pg.page.value === 1" class="px-4 py-2 rounded-xl bg-white shadow disabled:opacity-40 text-sm">السابق</button>
      <span class="text-sm text-gray-500">صفحة {{ pg.page.value }} من {{ pg.totalPages.value }} ({{ pg.total.value }} مستخدم)</span>
      <button @click="pg.nextPage" :disabled="pg.page.value === pg.totalPages.value" class="px-4 py-2 rounded-xl bg-white shadow disabled:opacity-40 text-sm">التالي</button>
    </div>

    <div v-if="pendingDelete" class="fixed inset-0 bg-black/60 flex items-center justify-center z-[70]">
      <div class="bg-white rounded-2xl p-8 max-w-md mx-4 shadow-2xl">
        <div class="text-4xl mb-4">⚠️</div>
        <p class="text-gray-800 text-lg mb-8">
          هل أنت متأكد من تعطيل المستخدم "<strong>{{ pendingDelete.full_name || pendingDelete.username }}</strong>"؟
          <br /><span class="text-sm text-gray-400">لن يتمكن من تسجيل الدخول بعد ذلك، ويمكن إعادة تفعيله لاحقًا.</span>
        </p>
        <div class="flex gap-3">
          <button @click="confirmDelete" class="flex-1 bg-red-600 text-white py-4 rounded-xl">نعم، عطّل الحساب</button>
          <button @click="pendingDelete = null" class="flex-1 bg-gray-100 py-4 rounded-xl">إلغاء</button>
        </div>
      </div>
    </div>

    <BulkDeleteConfirmModal
      v-if="showBulkDeactivateModal"
      icon="🚫"
      confirm-text="نعم، عطّل"
      loading-text="جاري التعطيل..."
      confirm-color="bg-amber-500 hover:bg-amber-600"
      :message="`هل أنت متأكد من تعطيل ${bulk.selectedCount.value} مستخدم؟`"
      :loading="bulkLoading"
      @close="showBulkDeactivateModal = false"
      @confirm="confirmBulkDeactivate"
    />

    <BulkDeleteConfirmModal
      v-if="showBulkActivateModal"
      icon="✅"
      confirm-text="نعم، فعّل"
      loading-text="جاري التفعيل..."
      confirm-color="bg-emerald-600 hover:bg-emerald-700"
      :message="`هل تريد تفعيل ${bulk.selectedCount.value} مستخدم؟`"
      :loading="bulkLoading"
      @close="showBulkActivateModal = false"
      @confirm="confirmBulkActivate"
    />

    <BulkDeleteConfirmModal
      v-if="showBulkDeleteModal"
      :message="`هل أنت متأكد من حذف ${bulk.selectedCount.value} مستخدم؟`"
      :loading="bulkLoading"
      @close="showBulkDeleteModal = false"
      @confirm="confirmBulkDelete"
    />

    <UserFormModal
      v-if="showModal"
      :user-data="editingUser"
      :role-options="roleOptions"
      @close="closeModal"
      @success="handleSuccess"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useAuth } from '../../../composables/useAuth'
import { useServerPagination } from '../../../composables/useServerPagination'
import { useToast } from '../../../composables/useToast'
import BulkActionsBar from '../../shared/BulkActionsBar.vue'
import BulkDeleteConfirmModal from '../../shared/BulkDeleteConfirmModal.vue'
import UserFormModal from '../modals/UserFormModal.vue'
import { useBulkSelection } from '../../../composables/useBulkSelection'

const { apiFetch, user: currentUser } = useAuth()
const { showToast } = useToast()
const isTargetProtected = (u) => currentUser.value?.role !== 'admin' && u.role === 'admin'

const showModal = ref(false)
const editingUser = ref(null)
const pendingDelete = ref(null)

const roleOptions = ref([])

const loadRoles = async () => {
  try {
    const res = await apiFetch('/api/roles/')
    if (res.ok) {
      const data = await res.json()
      roleOptions.value = data.map(r => ({ label: r.label, value: r.name }))
    }
  } catch (e) { console.error('أدوار', e) }
}

const fetchUsersPage = async ({ skip, limit, search }) => {
  const params = new URLSearchParams({ skip, limit })
  if (search) params.set('search', search)
  const res = await apiFetch(`/api/users/?${params.toString()}`)
  if (!res.ok) return { items: [], total: 0 }
  return res.json()
}

const pg = useServerPagination(fetchUsersPage, 10)

const openAdd = () => { editingUser.value = null; showModal.value = true }
const openEdit = (u) => { editingUser.value = u; showModal.value = true }
const closeModal = () => { showModal.value = false; editingUser.value = null }
const handleSuccess = () => { closeModal(); pg.load() }

const askDelete = (u) => { pendingDelete.value = u }

const confirmDelete = async () => {
  if (!pendingDelete.value) return
  try {
    const res = await apiFetch(`/api/users/${pendingDelete.value.id}/`, { method: 'DELETE' })
    const data = await res.json()
    if (res.ok) {
      pendingDelete.value = null
      showToast('success', '✅ تم إلغاء تفعيل المستخدم بنجاح')
      pg.load()
    } else {
      showToast('error', '❌ ' + (data.detail || 'تعذر تعطيل المستخدم'))
    }
  } catch (e) {
    showToast('error', 'تعذر الاتصال بالسيرفر')
  }
}

const bulk = useBulkSelection(
  pg.items,
  pg.items,
  'id',
  (u) => u.id !== currentUser.value?.id && !isTargetProtected(u)
)
watch(pg.items, () => { bulk.clear() })

const pageEligibleCount = computed(() =>
  pg.items.value.filter(u => u.id !== currentUser.value?.id && !isTargetProtected(u)).length
)

const showBulkDeactivateModal = ref(false)
const showBulkActivateModal = ref(false)
const showBulkDeleteModal = ref(false)
const bulkLoading = ref(false)

const openBulkDeactivate = () => {
  if (bulk.selectedCount.value === 0) { showToast('error', 'لا يوجد مستخدمون محددون'); return }
  showBulkDeactivateModal.value = true
}
const openBulkActivate = () => {
  if (bulk.selectedCount.value === 0) { showToast('error', 'لا يوجد مستخدمون محددون'); return }
  showBulkActivateModal.value = true
}
const openBulkDelete = () => {
  if (bulk.selectedCount.value === 0) { showToast('error', 'لا يوجد مستخدمون محددون'); return }
  showBulkDeleteModal.value = true
}

const runBulkAction = async (endpoint, closeModalRef) => {
  bulkLoading.value = true
  try {
    const ids = bulk.selectedIdsArray.value
    const res = await apiFetch(`/api/users/${endpoint}/`, {
      method: 'POST',
      body: JSON.stringify({ ids })
    })
    const data = await res.json()
    if (res.ok) {
      closeModalRef.value = false
      showToast('success', `✅ ${data.message || 'تم تنفيذ الإجراء بنجاح'}`)
      bulk.clear()
      pg.load()
    } else {
      showToast('error', '❌ ' + (data.detail || 'تعذر تنفيذ الإجراء الجماعي'))
    }
  } catch (e) {
    showToast('error', 'تعذر الاتصال بالسيرفر')
  } finally {
    bulkLoading.value = false
  }
}

const confirmBulkDeactivate = () => runBulkAction('bulk-deactivate', showBulkDeactivateModal)
const confirmBulkActivate = () => runBulkAction('bulk-activate', showBulkActivateModal)
const confirmBulkDelete = () => runBulkAction('bulk-delete', showBulkDeleteModal)

defineExpose({ refresh: pg.load, clearSelection: bulk.clear })

onMounted(() => {
  pg.load()
  loadRoles()
})
</script>