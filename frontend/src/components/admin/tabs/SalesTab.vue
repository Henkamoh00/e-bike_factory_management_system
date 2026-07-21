<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-3xl font-bold">المبيعات</h2>
      <button @click="$emit('open-sale-modal')" class="bg-green-600 hover:bg-green-700 text-white px-6 py-3 rounded-2xl font-medium">
        + تسجيل بيع جديد
      </button>
    </div>

    <!-- فلاتر المبيعات -->
    <div class="bg-white rounded-2xl shadow p-5 mb-6 flex flex-wrap gap-4 items-end">
      <div>
        <SearchableSelect
          v-model="salesFilter.customer_name"
          :options="customerOptions"
          label="تصفية بالعميل"
          empty-label="كل العملاء"
        />
      </div>
      <div>
        <label class="block text-sm text-gray-500 mb-1">من تاريخ</label>
        <input type="date" v-model="salesFilter.date_from" class="px-4 py-2 border-2 border-gray-200 rounded-xl focus:border-indigo-400 focus:outline-none" />
      </div>
      <div>
        <label class="block text-sm text-gray-500 mb-1">إلى تاريخ</label>
        <input type="date" v-model="salesFilter.date_to" class="px-4 py-2 border-2 border-gray-200 rounded-xl focus:border-indigo-400 focus:outline-none" />
      </div>
      <button @click="resetFilter" class="px-4 py-2 text-gray-500 hover:text-gray-700 underline text-sm">إعادة تعيين</button>
    </div>

    <div class="bg-white rounded-3xl shadow-xl overflow-hidden">
      <div v-if="filteredSales.length === 0" class="text-center py-16 text-gray-400 text-lg">لا توجد مبيعات مطابقة</div>

      <div v-else class="divide-y divide-gray-100">
        <div
          v-for="sale in filteredSales"
          :key="sale.id"
          class="flex items-center justify-between gap-4 px-5 py-3 hover:bg-gray-50 transition"
        >
          <div class="flex items-center gap-3 min-w-0">
            <div class="w-9 h-9 rounded-full bg-green-100 text-green-700 flex items-center justify-center text-base shrink-0">
              💰
            </div>
            <div class="min-w-0">
              <div class="font-mono font-bold text-gray-800 truncate">{{ sale.chassis_number }}</div>
              <div class="text-xs text-gray-500 truncate">{{ sale.customer_name }}</div>
            </div>
          </div>

          <div class="text-left shrink-0">
            <div class="text-xs text-gray-400">{{ new Date(sale.sale_date).toLocaleDateString('ar-EG') }}</div>
            <div v-if="sale.notes" class="text-xs text-gray-400 truncate max-w-[140px]">{{ sale.notes }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import SearchableSelect from '../../shared/SearchableSelect.vue'

defineEmits(['open-sale-modal'])

const props = defineProps({
  salesList: { type: Array, default: () => [] },
  customersList: { type: Array, default: () => [] }
})

const salesFilter = ref({ customer_name: '', date_from: '', date_to: '' })

const customerOptions = computed(() =>
  props.customersList.map(c => ({ label: c.name, value: c.name }))
)

const filteredSales = computed(() => {
  return props.salesList.filter(s => {
    if (salesFilter.value.customer_name && s.customer_name !== salesFilter.value.customer_name) return false
    if (salesFilter.value.date_from && new Date(s.sale_date) < new Date(salesFilter.value.date_from)) return false
    if (salesFilter.value.date_to && new Date(s.sale_date) > new Date(salesFilter.value.date_to)) return false
    return true
  })
})

const resetFilter = () => { salesFilter.value = { customer_name: '', date_from: '', date_to: '' } }
</script>