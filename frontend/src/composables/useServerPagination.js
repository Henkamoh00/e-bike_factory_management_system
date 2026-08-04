import { ref, computed, watch } from 'vue'

/**
 * باجينيشن حقيقي من جهة السيرفر.
 * fetchPage(params) يجب أن يُرجع Promise<{ items, total }>
 * params = { skip, limit, search }
 */
export function useServerPagination(fetchPage, pageSize = 10) {
  const items = ref([])
  const total = ref(0)
  const page = ref(1)
  const loading = ref(false)
  const search = ref('')

  const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

  const load = async () => {
    loading.value = true
    try {
      const skip = (page.value - 1) * pageSize
      const result = await fetchPage({ skip, limit: pageSize, search: search.value })
      items.value = result.items
      total.value = result.total
    } finally {
      loading.value = false
    }
  }

  const prevPage = () => { if (page.value > 1) { page.value--; load() } }
  const nextPage = () => { if (page.value < totalPages.value) { page.value++; load() } }

  // عند تغيّر البحث: إعادة الصفحة للأولى + تحميل (بمهلة بسيطة لمنع طلبات متتالية)
  let debounceTimer = null
  watch(search, () => {
    page.value = 1
    clearTimeout(debounceTimer)
    debounceTimer = setTimeout(load, 350)
  })

  return { items, total, page, totalPages, loading, search, load, prevPage, nextPage }
}