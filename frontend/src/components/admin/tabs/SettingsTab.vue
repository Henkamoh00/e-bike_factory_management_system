<template>
  <div>
    <div class="flex gap-2 mb-6 border-b border-gray-100 pb-4">
      <button
        v-for="sub in subTabs"
        :key="sub.id"
        @click="activeSub = sub.id"
        :class="activeSub === sub.id ? 'bg-indigo-50 text-indigo-700 font-semibold' : 'text-gray-500 hover:bg-gray-50'"
        class="px-4 py-2 rounded-xl text-sm transition"
      >
        {{ sub.icon }} {{ sub.label }}
      </button>
    </div>

    <BikeTypeSubTab
      v-if="activeSub === 'bike_types'"
      ref="bikeTypeSubTabRef"
      @bike-type-changed="$emit('bike-type-changed')"
    />

    <BikeColorSubTab
      v-else-if="activeSub === 'bike_colors'"
      ref="bikeColorSubTabRef"
      @bike-color-changed="$emit('bike-color-changed')"
    />

    <UserRolesSubTab v-else-if="activeSub === 'roles'" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import BikeTypeSubTab from './BikeTypeSubTab.vue'
import BikeColorSubTab from './BikeColorSubTab.vue'
import UserRolesSubTab from './UserRolesSubTab.vue'

defineEmits(['bike-type-changed', 'bike-color-changed'])

const subTabs = [
  { id: 'bike_types', label: 'أنواع الدراجات', icon: '🚲' },
  { id: 'bike_colors', label: 'ألوان الدراجات', icon: '🎨' },
  { id: 'roles', label: 'الأدوار', icon: '🔑' },
]

const activeSub = ref('bike_types')

const bikeTypeSubTabRef = ref(null)
const bikeColorSubTabRef = ref(null)

defineExpose({
  clearSelection: () => {
    bikeTypeSubTabRef.value?.clearSelection?.()
    bikeColorSubTabRef.value?.clearSelection?.()
  },
  refreshBikeTypes: () => bikeTypeSubTabRef.value?.refresh?.(),
  refreshBikeColors: () => bikeColorSubTabRef.value?.refresh?.()
})
</script>