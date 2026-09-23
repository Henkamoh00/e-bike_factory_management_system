<template>
  <div class="fixed inset-0 bg-black/60 flex items-center justify-center z-[65]">
    <div class="bg-white rounded-3xl shadow-2xl w-full max-w-2xl mx-4 max-h-[90vh] flex flex-col">
      <div class="p-8 overflow-y-auto flex-1">
        <h2 class="text-2xl font-bold mb-2" :class="form.movement_type === 'in' ? 'text-emerald-700' : 'text-orange-600'">
          {{ form.movement_type === 'in' ? '📥 تسجيل وارد' : '📤 تسجيل صادر' }}
        </h2>
        <p class="text-sm text-gray-500 mb-6">
          يمكنك إضافة عدة قطع دفعة واحدة لتسهيل الإدخال، لكن كل سطر يُسجَّل كحركة
          مستقلة تمامًا في سجل المخزون (لا ترتبط الأسطر ببعضها بأي شكل).
        </p>

        <div class="flex gap-2 mb-6">
          <button
            type="button"
            @click="form.movement_type = 'in'"
            :class="form.movement_type === 'in' ? 'ring-2 ring-emerald-500 bg-emerald-50' : 'border-2 border-gray-200'"
            class="flex-1 p-3 rounded-2xl transition-all"
          >
            📥 وارد
          </button>
          <button
            type="button"
            @click="form.movement_type = 'out'"
            :class="form.movement_type === 'out' ? 'ring-2 ring-orange-500 bg-orange-50' : 'border-2 border-gray-200'"
            class="flex-1 p-3 rounded-2xl transition-all"
          >
            📤 صادر
          </button>
        </div>

        <!-- حقول مشتركة تُنسَخ لكل سطر عند الإرسال (وليست حركة واحدة مجمَّعة) -->
        <div v-if="form.movement_type === 'in'" class="mb-4">
          <SearchableSelect
            v-model="form.supplier_name"
            :async-search="searchSuppliers"
            label="المورّد (اختياري، يُطبَّق على كل الأسطر)"
            placeholder="اختر المورّد"
          />
          <button
            type="button"
            @click="showSupplierForm = true"
            class="text-sm text-indigo-600 hover:text-indigo-800 underline mt-2"
          >
            + إضافة مورّد جديد
          </button>
        </div>

        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-1">
            {{ form.movement_type === 'out' ? 'مرجع/رقم هيكل مرتبط (اختياري، لكل الأسطر)' : 'مرجع اختياري (لكل الأسطر)' }}
          </label>
          <input
            v-model="form.related_chassis_number"
            type="text" placeholder="مثال: EB-2026-00485"
            class="w-full px-4 py-2 border-2 border-gray-200 rounded-xl focus:border-indigo-400 focus:outline-none font-mono"
          />
        </div>

        <!-- الأسطر -->
        <label class="block text-sm font-medium text-gray-700 mb-3">القطع</label>

        <div v-if="form.lines.length === 0" class="text-center py-8 text-gray-400 bg-gray-50 rounded-2xl mb-3">
          لم تتم إضافة أي قطعة بعد
        </div>

        <div v-else class="space-y-3 mb-3">
          <div
            v-for="(line, idx) in form.lines"
            :key="idx"
            class="p-3 bg-gray-50 rounded-2xl"
          >
            <div class="flex items-start gap-2 mb-2">
              <div class="flex-1">
                <SearchableSelect
                  v-model="line.part_id"
                  :async-search="searchParts"
                  :initial-selected-label="line.part_label"
                  placeholder="اختر القطعة"
                  :allow-empty="false"
                  @update:modelValue="(val) => onSelectPart(line, val)"
                />
              </div>
              <button
                type="button"
                @click="removeLine(idx)"
                class="w-9 h-9 flex items-center justify-center rounded-lg text-red-400 hover:bg-red-50 hover:text-red-600 transition shrink-0 mt-1"
              >
                🗑️
              </button>
            </div>
            <div class="grid gap-2" :class="form.movement_type === 'in' ? 'grid-cols-2' : 'grid-cols-1'">
              <input
                v-model.number="line.quantity"
                type="number" min="0" step="0.001"
                :placeholder="`الكمية${line.unit ? ' (' + line.unit + ')' : ''}`"
                class="px-3 py-2 border-2 border-gray-200 rounded-xl focus:border-indigo-400 focus:outline-none text-sm"
              />
              <input
                v-if="form.movement_type === 'in'"
                v-model.number="line.unit_price"
                type="number" min="0" step="0.01"
                placeholder="السعر"
                class="px-3 py-2 border-2 border-gray-200 rounded-xl focus:border-indigo-400 focus:outline-none text-sm"
              />
            </div>
          </div>
        </div>

        <button
          type="button"
          @click="addLine"
          class="w-full py-2.5 border-2 border-dashed border-gray-300 rounded-xl text-gray-500 hover:border-indigo-400 hover:text-indigo-600 transition text-sm font-medium"
        >
          + إضافة قطعة أخرى للسطر
        </button>

        <div class="mt-6">
          <textarea
            v-model="form.notes"
            :placeholder="form.movement_type === 'out' ? 'سبب الصرف (تجميع / صيانة / تلف...) — يُطبَّق على كل الأسطر' : 'ملاحظات عامة (اختياري) — تُطبَّق على كل الأسطر'"
            class="w-full p-4 border-2 border-gray-200 rounded-2xl h-20 focus:border-indigo-400 focus:outline-none"
          ></textarea>
        </div>
      </div>

      <div class="border-t p-4 flex gap-3 shrink-0">
        <button @click="$emit('close')" class="flex-1 py-3 rounded-2xl font-medium text-gray-600 hover:bg-gray-100">إلغاء</button>
        <button
          @click="submit"
          :disabled="loading || form.lines.length === 0"
          class="flex-1 py-3 text-white rounded-2xl font-bold disabled:opacity-40"
          :class="form.movement_type === 'in' ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-orange-600 hover:bg-orange-700'"
        >
          {{ loading ? `جاري التسجيل... (${progress})` : `✅ تأكيد (${form.lines.length} سطر)` }}
        </button>
      </div>
    </div>

    <SupplierFormModal
      v-if="showSupplierForm"
      @close="showSupplierForm = false"
      @success="handleSupplierAdded"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useAuth } from '../../composables/useAuth'
import { useToast } from '../../composables/useToast'
import SearchableSelect from '../shared/SearchableSelect.vue'
import SupplierFormModal from './SupplierFormModal.vue'

const { apiFetch } = useAuth()
const { showToast } = useToast()

const props = defineProps({
  presetPartId: { type: [Number, String], default: '' },
  presetPartName: { type: String, default: '' },
  presetPartUnit: { type: String, default: '' },
  presetType: { type: String, default: 'in' },
})
const emit = defineEmits(['close', 'success'])

const loading = ref(false)
const progress = ref('')
const showSupplierForm = ref(false)

const makeEmptyLine = () => ({ part_id: '', part_label: '', unit: '', quantity: null, unit_price: null })

const form = ref({
  movement_type: props.presetType,
  supplier_name: '',
  related_chassis_number: '',
  notes: '',
  lines: props.presetPartId
    ? [{ part_id: props.presetPartId, part_label: `${props.presetPartName} (${props.presetPartUnit})`, unit: props.presetPartUnit, quantity: null, unit_price: null }]
    : [makeEmptyLine()],
})

const searchParts = async (query) => {
  const params = new URLSearchParams({ limit: 20 })
  if (query) params.set('q', query)
  const res = await apiFetch(`/api/inventory/parts/simple/?${params.toString()}`)
  if (!res.ok) return []
  const data = await res.json()
  return data.map(p => ({ label: `${p.name} (${p.unit})`, value: p.id }))
}

const searchSuppliers = async (query) => {
  const params = new URLSearchParams({ limit: 20 })
  if (query) params.set('q', query)
  const res = await apiFetch(`/api/inventory/suppliers/simple/?${params.toString()}`)
  if (!res.ok) return []
  const data = await res.json()
  return data.map(s => ({ label: s.name, value: s.name }))
}

// 🆕 عند اختيار قطعة لسطر معيّن، نحفظ وحدة القياس الخاصة بها لعرضها في
// حقل الكمية (placeholder) — لا علاقة له بمنطق العمل، فقط تسهيل إدخال
const partsCache = ref({})
const onSelectPart = async (line, partId) => {
  if (!partsCache.value[partId]) {
    const res = await apiFetch(`/api/inventory/parts/simple/?limit=100`)
    if (res.ok) {
      const data = await res.json()
      data.forEach(p => { partsCache.value[p.id] = p })
    }
  }
  const found = partsCache.value[partId]
  line.unit = found?.unit || ''
}

const addLine = () => { form.value.lines.push(makeEmptyLine()) }
const removeLine = (idx) => { form.value.lines.splice(idx, 1) }

const handleSupplierAdded = (newSupplier) => {
  showSupplierForm.value = false
  form.value.supplier_name = newSupplier.name
}

const validate = () => {
  if (form.value.lines.length === 0) {
    showToast('error', 'يرجى إضافة قطعة واحدة على الأقل')
    return false
  }
  for (const line of form.value.lines) {
    if (!line.part_id) {
      showToast('error', 'يرجى اختيار القطعة في كل سطر')
      return false
    }
    if (!line.quantity || line.quantity <= 0) {
      showToast('error', 'يرجى إدخال كمية صحيحة لكل سطر')
      return false
    }
  }
  return true
}

// 🆕 كل سطر يُرسَل كطلب POST مستقل تمامًا لأن الحركات غير مرتبطة ببعضها
// بأي شكل في قاعدة البيانات — الفورم هنا مجرد تسهيل لإدخال عدة قطع معًا
const submit = async () => {
  if (!validate()) return

  loading.value = true
  let successCount = 0
  let failCount = 0

  for (let i = 0; i < form.value.lines.length; i++) {
    const line = form.value.lines[i]
    progress.value = `${i + 1}/${form.value.lines.length}`
    try {
      const payload = {
        part_id: line.part_id,
        movement_type: form.value.movement_type,
        quantity: line.quantity,
        unit_price: form.value.movement_type === 'in' ? (line.unit_price || null) : null,
        supplier_name: form.value.movement_type === 'in' ? (form.value.supplier_name || null) : null,
        related_chassis_number: form.value.related_chassis_number || null,
        notes: form.value.notes || null,
      }
      const res = await apiFetch(`/api/inventory/movements/`, { method: 'POST', body: JSON.stringify(payload) })
      if (res.ok) {
        successCount++
      } else {
        failCount++
      }
    } catch (e) {
      failCount++
    }
  }

  loading.value = false

  if (failCount === 0) {
    showToast('success', `✅ تم تسجيل ${successCount} حركة بنجاح`)
  } else {
    showToast('error', `⚠️ نجحت ${successCount} وفشلت ${failCount} — راجع الكميات المتوفرة`)
  }
  emit('success')
}
</script>