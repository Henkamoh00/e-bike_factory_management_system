import { ref, computed } from 'vue'

/**
 * @param {Ref<Array>} itemsRef - قائمة العناصر المعروضة حاليًا (بعد الفلترة)
 * @param {string} idKey
 * @param {(item: any) => boolean} isEligible - دالة تحدد إن كان العنصر قابلاً للتحديد (اختيارية، افتراضيًا الكل مؤهل)
 */
export function useBulkSelection(itemsRef, idKey = 'id', isEligible = () => true) {
  const selectedIds = ref(new Set())

  // العناصر المؤهلة فقط ضمن القائمة المعروضة حاليًا
  const eligibleItems = computed(() => itemsRef.value.filter(isEligible))

  const isItemEligible = (item) => isEligible(item)

  const isSelected = (item) => selectedIds.value.has(item[idKey])

  const toggleOne = (item) => {
    if (!isEligible(item)) return // لا تحديد لعنصر غير مؤهل
    const id = item[idKey]
    const next = new Set(selectedIds.value)
    next.has(id) ? next.delete(id) : next.add(id)
    selectedIds.value = next
  }

  const allSelected = computed(() => {
    const items = eligibleItems.value
    return items.length > 0 && items.every(i => selectedIds.value.has(i[idKey]))
  })

  const someSelected = computed(() => selectedIds.value.size > 0)

  const toggleAll = () => {
    if (allSelected.value) {
      selectedIds.value = new Set()
    } else {
      selectedIds.value = new Set(eligibleItems.value.map(i => i[idKey]))
    }
  }

  const clear = () => { selectedIds.value = new Set() }

  const selectedCount = computed(() => selectedIds.value.size)
  const selectedIdsArray = computed(() => Array.from(selectedIds.value))
  const eligibleCount = computed(() => eligibleItems.value.length)

  return {
    selectedIds, isSelected, toggleOne, toggleAll,
    allSelected, someSelected, clear, selectedCount, selectedIdsArray,
    isItemEligible, eligibleCount
  }
}