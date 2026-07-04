<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-3xl font-bold">العملاء</h2>
      <button @click="$emit('open-customer-modal')" class="bg-purple-600 hover:bg-purple-700 text-white px-6 py-3 rounded-2xl font-medium">
        + إضافة عميل جديد
      </button>
    </div>

    <!-- فلاتر العملاء -->
    <div class="bg-white rounded-2xl shadow p-5 mb-6 flex flex-wrap gap-4 items-end">
      <div>
        <SearchableSelect
          v-model="customersFilter.name"
          :options="customerOptions"
          label="بحث باسم العميل"
          empty-label="كل العملاء"
        />
      </div>
      <button @click="resetFilter" class="px-4 py-2 text-gray-500 hover:text-gray-700 underline text-sm">إعادة تعيين</button>
    </div>

    <div class="bg-white rounded-3xl shadow-xl p-6">
      <div v-if="filteredCustomers.length === 0" class="text-center py-16 text-gray-400 text-lg">لا يوجد عملاء مطابقون</div>
      <div v-else class="space-y-4">
        <div v-for="customer in filteredCustomers" :key="customer.id" class="bg-gray-50 p-5 rounded-2xl">
          <div class="flex justify-between items-start">
            <div>
              <div class="font-bold text-lg">{{ customer.name }}</div>
              <div class="text-sm text-gray-500">{{ customer.phone }}</div>
              <div class="text-sm text-gray-400">{{ customer.address }}</div>
            </div>
            <div class="text-right">
              <span class="text-sm text-purple-600 font-medium">{{ customer.total_purchases ?? 0 }} دراجة مشتراة</span>
            </div>
          </div>
          <div v-if="customer.sales?.length" class="mt-4 space-y-2">
            <div v-for="sale in customer.sales" :key="sale.id"
              class="flex justify-between items-center bg-white px-4 py-3 rounded-xl border border-gray-200">
              <span class="font-mono text-sm">{{ sale.chassis_number }}</span>
              <span class="text-xs text-gray-500">{{ new Date(sale.sale_date).toLocaleDateString('ar-EG') }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import SearchableSelect from '../../shared/SearchableSelect.vue'

defineEmits(['open-customer-modal'])

const props = defineProps({
  customersList: { type: Array, default: () => [] }
})

const customersFilter = ref({ name: '' })

const customerOptions = computed(() =>
  props.customersList.map(c => ({ label: c.name, value: c.name }))
)

const filteredCustomers = computed(() => {
  const name = customersFilter.value.name
  if (!name) return props.customersList
  return props.customersList.filter(c => c.name === name)
})

const resetFilter = () => { customersFilter.value = { name: '' } }
</script>