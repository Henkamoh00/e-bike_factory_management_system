import { ref, computed } from 'vue'

export function useBulkSelection(itemsRef, pageItemsRef, idKey = 'id', isEligible = () => true) {
  const selectedIds = ref(new Set())

  const eligibleAllItems = computed(() => itemsRef.value.filter(isEligible))
  const eligiblePageItems = computed(() => pageItemsRef.value.filter(isEligible))

  const isSelected = (item) => selectedIds.value.has(item[idKey])

  const toggleOne = (item) => {
    if (!isEligible(item)) return
    const id = item[idKey]
    const next = new Set(selectedIds.value)
    next.has(id) ? next.delete(id) : next.add(id)
    selectedIds.value = next
  }

  const pageAllSelected = computed(() => {
    const items = eligiblePageItems.value
    return items.length > 0 && items.every(i => selectedIds.value.has(i[idKey]))
  })

  const toggleAllOnPage = () => {
    const next = new Set(selectedIds.value)
    if (pageAllSelected.value) {
      eligiblePageItems.value.forEach(i => next.delete(i[idKey]))
    } else {
      eligiblePageItems.value.forEach(i => next.add(i[idKey]))
    }
    selectedIds.value = next
  }

  const isAllExpanded = computed(() => {
    const items = eligibleAllItems.value
    return items.length > 0 && items.every(i => selectedIds.value.has(i[idKey]))
  })

  const selectAllAcrossPages = () => {
    selectedIds.value = new Set(eligibleAllItems.value.map(i => i[idKey]))
  }

  const hasMoreToSelect = computed(() =>
    eligibleAllItems.value.length > eligiblePageItems.value.length && !isAllExpanded.value
  )

  const clear = () => { selectedIds.value = new Set() }

  const someSelected = computed(() => selectedIds.value.size > 0)
  const selectedCount = computed(() => selectedIds.value.size)
  const selectedIdsArray = computed(() => Array.from(selectedIds.value))
  const eligibleCount = computed(() => eligibleAllItems.value.length)

  return {
    selectedIds, isSelected, toggleOne,
    pageAllSelected, toggleAllOnPage,
    isAllExpanded, selectAllAcrossPages, hasMoreToSelect,
    someSelected, clear, selectedCount, selectedIdsArray, eligibleCount
  }
}