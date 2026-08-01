import { ref, computed, watch } from 'vue'

/**
 * Pagination بسيط من جهة العميل (Client-side) للقوائم المُحمّلة بالكامل مسبقًا.
 * @param {Ref<Array>} itemsRef - المصفوفة الكاملة بعد الفلترة
 * @param {number} pageSize - عدد العناصر بكل صفحة (افتراضي 10)
 */
export function usePagination(itemsRef, pageSize = 10) {
  const page = ref(1)

  const total = computed(() => itemsRef.value.length)
  const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

  const paginatedItems = computed(() => {
    const start = (page.value - 1) * pageSize
    return itemsRef.value.slice(start, start + pageSize)
  })

  const prevPage = () => { if (page.value > 1) page.value-- }
  const nextPage = () => { if (page.value < totalPages.value) page.value++ }
  const resetPage = () => { page.value = 1 }

  // إعادة الصفحة للأولى تلقائيًا عند تغيّر القائمة (فلترة/بحث جديد)
  watch(itemsRef, () => { resetPage() })

  return { page, total, totalPages, paginatedItems, prevPage, nextPage, resetPage }
}