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

    <div class="bg-white rounded-3xl shadow-xl overflow-hidden">
      <div v-if="filteredCustomers.length === 0" class="text-center py-16 text-gray-400 text-lg">لا يوجد عملاء مطابقون</div>

      <div v-else class="divide-y divide-gray-100">
        <div
          v-for="customer in filteredCustomers"
          :key="customer.id"
          class="flex items-center justify-between gap-4 px-5 py-3 hover:bg-gray-50 transition"
        >
          <div class="flex items-center gap-3 min-w-0">
            <div class="w-9 h-9 rounded-full bg-purple-100 text-purple-700 flex items-center justify-center font-bold text-sm shrink-0">
              {{ customer.name.charAt(0) }}
            </div>
            <div class="min-w-0">
              <div class="font-bold text-gray-800 truncate">{{ customer.name }}</div>
              <div class="text-xs text-gray-400 truncate">
                <span v-if="customer.phone">{{ customer.phone }}</span>
                <span v-if="customer.phone && customer.address"> • </span>
                <span v-if="customer.address">{{ customer.address }}</span>
              </div>
            </div>
          </div>

          <span class="text-xs bg-purple-50 text-purple-600 font-medium px-3 py-1 rounded-full shrink-0">
            {{ customer.total_purchases ?? 0 }} دراجة
          </span>
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