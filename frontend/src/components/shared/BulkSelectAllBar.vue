<template>
  <div class="flex items-center gap-3 px-5 py-2 bg-gray-50 border-b border-gray-100 flex-wrap">
    <input
      type="checkbox"
      :checked="bulk.pageAllSelected.value"
      :disabled="pageEligibleCount === 0"
      @change="bulk.toggleAllOnPage"
      class="w-4 h-4 accent-indigo-600 rounded disabled:opacity-30 disabled:cursor-not-allowed"
    />
    <span class="text-xs text-gray-400">
      تحديد الكل بالصفحة ({{ pageEligibleCount }} من {{ pageTotal }})
    </span>

    <button
      v-if="bulk.hasMoreToSelect.value"
      @click="bulk.selectAllAcrossPages"
      class="text-xs text-indigo-600 hover:text-indigo-800 underline font-medium"
    >
      تحديد كل {{ bulk.eligibleCount.value }} عنصر مطابق (عبر كل الصفحات)
    </button>

    <span v-else-if="bulk.selectedCount.value > pageEligibleCount" class="text-xs text-emerald-600 font-medium">
      ✅ تم تحديد كل العناصر المطابقة ({{ bulk.selectedCount.value }})
    </span>
  </div>
</template>

<script setup>
defineProps({
  bulk: { type: Object, required: true },
  pageEligibleCount: { type: Number, default: 0 },
  pageTotal: { type: Number, default: 0 }
})
</script>