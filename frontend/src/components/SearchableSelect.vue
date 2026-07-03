<template>
  <div class="relative" ref="rootEl">
    <label v-if="label" class="block text-sm text-gray-500 mb-1">{{ label }}</label>

    <button
      type="button"
      @click="toggleOpen"
      class="w-full min-w-[180px] px-4 py-2 border-2 border-gray-200 rounded-xl focus:border-indigo-400 focus:outline-none flex justify-between items-center bg-white"
    >
      <span :class="!selectedLabel ? 'text-gray-400' : ''">{{ selectedLabel || placeholder }}</span>
      <svg class="w-4 h-4 transition-transform shrink-0" :class="{ 'rotate-180': isOpen }" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
      </svg>
    </button>

    <div
      v-if="isOpen"
      class="absolute z-20 w-full mt-1 bg-white border-2 border-gray-200 rounded-xl shadow-lg"
    >
      <!-- خانة البحث تظهر فقط إذا searchable -->
      <div v-if="showSearch" class="p-2 border-b border-gray-100">
        <input
          ref="searchInput"
          v-model="query"
          type="text"
          placeholder="اكتب للبحث..."
          class="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:border-indigo-400 focus:outline-none"
          @keydown.esc="close"
        />
      </div>

      <!-- القائمة: 4 عناصر ظاهرة والباقي تمرير -->
      <div class="overflow-y-auto" style="max-height: 168px;">
        <div
          v-if="allowEmpty"
          @click="select('')"
          class="px-4 py-2 hover:bg-indigo-50 cursor-pointer text-sm"
          :class="{ 'bg-indigo-100': modelValue === '' }"
        >
          {{ emptyLabel }}
        </div>

        <div
          v-for="opt in filteredOptions"
          :key="opt.value"
          @click="select(opt.value)"
          class="px-4 py-2 hover:bg-indigo-50 cursor-pointer text-sm"
          :class="{ 'bg-indigo-100': modelValue === opt.value }"
        >
          {{ opt.label }}
        </div>

        <div v-if="filteredOptions.length === 0" class="px-4 py-3 text-sm text-gray-400 text-center">
          لا توجد نتائج
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onBeforeUnmount } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  options: { type: Array, default: () => [] },
  label: { type: String, default: '' },
  placeholder: { type: String, default: 'اختر...' },
  emptyLabel: { type: String, default: 'الكل' },
  allowEmpty: { type: Boolean, default: true },
})

// يقرر تلقائيًا: إذا الخيارات 3 أو أقل ما نعرض خانة البحث
const showSearch = computed(() => props.options.length > 3)

const emit = defineEmits(['update:modelValue'])

const isOpen = ref(false)
const query = ref('')
const rootEl = ref(null)
const searchInput = ref(null)

const filteredOptions = computed(() => {
  const q = query.value.trim().toLowerCase()
  if (!q) return props.options
  return props.options.filter(o => o.label.toLowerCase().includes(q))
})

const selectedLabel = computed(() => {
  if (!props.modelValue) return ''
  const found = props.options.find(o => o.value === props.modelValue)
  return found ? found.label : props.modelValue
})

const toggleOpen = () => {
  isOpen.value = !isOpen.value
  if (isOpen.value && showSearch.value) {
    query.value = ''
    nextTick(() => searchInput.value?.focus())
  }
}

const select = (value) => {
  emit('update:modelValue', value)
  close()
}

const close = () => { isOpen.value = false }

const onClickOutside = (e) => {
  if (rootEl.value && !rootEl.value.contains(e.target)) close()
}

onMounted(() => document.addEventListener('click', onClickOutside))
onBeforeUnmount(() => document.removeEventListener('click', onClickOutside))
</script>