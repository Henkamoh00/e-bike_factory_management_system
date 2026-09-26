<template>
  <div class="fixed inset-0 bg-black/60 flex items-center justify-center z-[65]">
    <div class="bg-white rounded-3xl shadow-2xl w-full max-w-md mx-4 max-h-[85vh] flex flex-col">
      <div class="p-8 overflow-y-auto flex-1">
        <h2 class="text-2xl font-bold mb-2 text-orange-600">🔄 تسجيل إرجاع دراجة</h2>
        <p class="text-sm text-gray-500 mb-6">
          سيُخصَم سعر هذا البند تلقائيًا من إجمالي الفاتورة، وتعود الدراجة متاحة للبيع فورًا.
        </p>

        <div class="mb-4">
          <SearchableSelect
            v-model="form.invoice_item_id"
            :options="chassisOptions"
            label="الدراجة المُرجَعة"
            placeholder="اختر رقم الهيكل"
            :allow-empty="false"
          />
        </div>

        <div v-if="loadingFaults" class="text-xs text-gray-400 mb-4">جاري البحث عن أعطال مرتبطة...</div>
        <div v-else-if="relatedFaults.length > 0" class="mb-4">
          <SearchableSelect
            v-model="form.related_fault_id"
            :options="faultOptions"
            label="ربط بعطل معلَّق لهذه الدراجة (اختياري)"
            placeholder="بدون ربط"
          />
        </div>

        <!-- قائمة أسباب محددة مسبقًا + خيار "سبب آخر" -->
        <label class="block text-sm font-medium text-gray-700 mb-2">سبب الإرجاع</label>
        <select
          v-model="reasonOption"
          class="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-orange-400 focus:outline-none bg-white mb-3"
        >
          <option value="">اختر السبب</option>
          <option v-for="r in reasonOptions" :key="r" :value="r">{{ r }}</option>
        </select>

        <!-- تنبيه: إذا كان السبب عطلاً ولم يُربط بعطل موجود، سيُفتح عطل جديد تلقائيًا -->
        <div
          v-if="willAutoCreateFault"
          class="text-xs bg-red-50 text-red-600 rounded-xl px-3 py-2 mb-3 flex items-start gap-2"
        >
          <span class="shrink-0">⚠️</span>
          <span>
            بما أنك لم تربط هذا الإرجاع بعطل موجود مسبقًا، سيتم فتح
            <strong>عطل جديد "معلّق"</strong> تلقائيًا لهذه الدراجة في مرحلة
            "{{ fautStageLabel }}" ليظهر في تبويب الأعطال فورًا.
          </span>
        </div>

        <textarea
          v-if="reasonOption === OTHER_REASON"
          v-model="customReason"
          placeholder="اكتب سبب الإرجاع بالتفصيل (إلزامي عند اختيار سبب آخر)"
          class="w-full p-4 border-2 border-gray-200 rounded-2xl h-20 focus:border-orange-400 focus:outline-none mb-3"
        ></textarea>

        <textarea
          v-model="form.notes"
          placeholder="ملاحظات إضافية (اختياري)"
          class="w-full p-4 border-2 border-gray-200 rounded-2xl h-20 focus:border-orange-400 focus:outline-none"
        ></textarea>
      </div>

      <div class="border-t p-4 flex gap-3 shrink-0">
        <button @click="$emit('close')" class="flex-1 py-3 rounded-2xl font-medium text-gray-600 hover:bg-gray-100">إلغاء</button>
        <button @click="submit" :disabled="loading" class="flex-1 py-3 bg-orange-600 hover:bg-orange-700 text-white rounded-2xl font-bold">
          {{ loading ? 'جاري التسجيل...' : '✅ تأكيد الإرجاع' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useAuth } from '../../composables/useAuth'
import { useToast } from '../../composables/useToast'
import SearchableSelect from '../shared/SearchableSelect.vue'

const { apiFetch } = useAuth()
const { showToast } = useToast()

const props = defineProps({
  initialChassisNumber: { type: String, default: '' }
})
const emit = defineEmits(['close', 'success'])

// هذه القيم الخمس يجب أن تطابق حرفيًا قيم ChassisReturnReason في
// invoicing/schemas.py (الباك إند). أي تعديل هنا يتطلب تعديلًا مطابقًا هناك.
const OTHER_REASON = 'سبب آخر'
const REASON_CHASSIS = 'عطل في الهيكل'
const REASON_ELECTRICAL = 'عطل في الكهرباء أو الغلاف'

const reasonOptions = [
  REASON_CHASSIS,
  REASON_ELECTRICAL,
  'الدراجة مكسورة',
  'لا تطابق المواصفات المطلوبة',
  OTHER_REASON,
]

// خريطة سبب الإرجاع ↔ مرحلة التجميع المرتبطة، تُستخدم لإنشاء عطل تلقائيًا
const FAULT_STAGE_MAP = {
  [REASON_CHASSIS]: 'تجميع_الهيكل',
  [REASON_ELECTRICAL]: 'توصيل_الكهرباء_والغلاف',
}
const FAULT_STAGE_LABELS = {
  'تجميع_الهيكل': 'تجميع الهيكل',
  'توصيل_الكهرباء_والغلاف': 'توصيل الكهرباء والغلاف',
}

const loading = ref(false)
const loadingFaults = ref(false)
const returnableChassis = ref([])
const relatedFaults = ref([])
const reasonOption = ref('')
const customReason = ref('')

const form = ref({
  invoice_item_id: '',
  related_fault_id: '',
  notes: '',
})

// هل سيُفتح عطل جديد تلقائيًا؟ فقط إذا كان السبب من نوع "عطل" معروف
// المرحلة، ولم يتم ربط الإرجاع بعطل موجود مسبقًا يدويًا
const autoFaultStage = computed(() => FAULT_STAGE_MAP[reasonOption.value] || null)
const willAutoCreateFault = computed(() => !!autoFaultStage.value && !form.value.related_fault_id)
const fautStageLabel = computed(() => FAULT_STAGE_LABELS[autoFaultStage.value] || '')

const chassisOptions = computed(() =>
  returnableChassis.value.map(c => ({
    label: `${c.chassis_number} — ${c.invoice_number} — ${c.customer_name}`,
    value: c.invoice_item_id,
  }))
)

const faultOptions = computed(() =>
  relatedFaults.value.map(f => ({ label: f.description, value: f.id }))
)

const loadReturnableChassis = async () => {
  try {
    const res = await apiFetch(`/api/invoices/returns/returnable-chassis/`)
    if (res.ok) {
      returnableChassis.value = await res.json()
      if (props.initialChassisNumber) {
        const match = returnableChassis.value.find(c => c.chassis_number === props.initialChassisNumber)
        if (match) form.value.invoice_item_id = match.invoice_item_id
      }
    }
  } catch (e) { console.error('دراجات قابلة للإرجاع', e) }
}

const loadFaultsForSelectedChassis = async () => {
  const selected = returnableChassis.value.find(c => c.invoice_item_id === form.value.invoice_item_id)
  if (!selected) {
    relatedFaults.value = []
    return
  }
  loadingFaults.value = true
  try {
    const params = new URLSearchParams({ chassis_number: selected.chassis_number, status: 'pending', limit: 20 })
    const res = await apiFetch(`/api/faults/?${params.toString()}`)
    if (res.ok) {
      const data = await res.json()
      relatedFaults.value = data.items || []
    }
  } catch (e) {
    console.error('أعطال الدراجة', e)
  } finally {
    loadingFaults.value = false
  }
}

watch(() => form.value.invoice_item_id, () => {
  form.value.related_fault_id = ''
  loadFaultsForSelectedChassis()
})

const submit = async () => {
  if (!form.value.invoice_item_id) {
    showToast('error', 'يرجى اختيار الدراجة المُرجَعة')
    return
  }
  if (!reasonOption.value) {
    showToast('error', 'يرجى اختيار سبب الإرجاع')
    return
  }
  if (reasonOption.value === OTHER_REASON && !customReason.value.trim()) {
    showToast('error', 'يرجى كتابة السبب في الحقل النصي')
    return
  }

  loading.value = true
  try {
    let combinedNotes = form.value.notes ? form.value.notes.trim() : ''
    if (reasonOption.value === OTHER_REASON) {
      const customText = customReason.value.trim()
      combinedNotes = combinedNotes ? `${customText} — ${combinedNotes}` : customText
    }

    const payload = {
      invoice_item_id: form.value.invoice_item_id,
      reason: reasonOption.value,
      related_fault_id: form.value.related_fault_id || null,
      notes: combinedNotes || null,
    }
    // إرسال مرحلة العطل فقط إذا لم يُربط الإرجاع بعطل موجود مسبقًا
    if (willAutoCreateFault.value) {
      payload.create_fault_stage = autoFaultStage.value
    }

    const res = await apiFetch(`/api/invoices/returns/`, {
      method: 'POST',
      body: JSON.stringify(payload)
    })
    const data = await res.json()
    if (res.ok) {
      const faultMsg = willAutoCreateFault.value ? ' وفُتح عطل جديد تلقائيًا لمتابعته' : ''
      showToast('success', `✅ تم تسجيل الإرجاع وخصم قيمته من الفاتورة تلقائيًا${faultMsg}`)
      emit('success')
    } else {
      showToast('error', '❌ ' + (data.detail || 'تعذر تسجيل الإرجاع'))
    }
  } catch (e) {
    showToast('error', 'تعذر الاتصال بالسيرفر')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadReturnableChassis()
})
</script>