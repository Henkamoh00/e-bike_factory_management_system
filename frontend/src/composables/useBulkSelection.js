import { ref, computed } from 'vue'

export function useBulkSelection(itemsRef, idKey = 'id') {
  const selectedIds = ref(new Set())

  const isSelected = (item) => selectedIds.value.has(item[idKey])

  const toggleOne = (item) => {
    const id = item[idKey]
    const next = new Set(selectedIds.value)
    next.has(id) ? next.delete(id) : next.add(id)
    selectedIds.value = next
  }

  const allSelected = computed(() => {
    const items = itemsRef.value
    return items.length > 0 && items.every(i => selectedIds.value.has(i[idKey]))
  })

  const someSelected = computed(() => selectedIds.value.size > 0)

  const toggleAll = () => {
    if (allSelected.value) {
      selectedIds.value = new Set()
    } else {
      selectedIds.value = new Set(itemsRef.value.map(i => i[idKey]))
    }
  }

  const clear = () => { selectedIds.value = new Set() }

  const selectedCount = computed(() => selectedIds.value.size)
  const selectedIdsArray = computed(() => Array.from(selectedIds.value))

  return {
    selectedIds, isSelected, toggleOne, toggleAll,
    allSelected, someSelected, clear, selectedCount, selectedIdsArray
  }
}