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
      :bike-types-list="bikeTypesList"
      @open-bike-type-modal="$emit('open-bike-type-modal')"
      @edit-bike-type="$emit('edit-bike-type', $event)"
      @delete-bike-type="$emit('delete-bike-type', $event)"
      @refresh-bike-types="$emit('refresh-bike-types')"
    />

    <BikeColorSubTab
      v-else-if="activeSub === 'bike_colors'"
      :bike-colors-list="bikeColorsList"
      @open-bike-color-modal="$emit('open-bike-color-modal')"
      @edit-bike-color="$emit('edit-bike-color', $event)"
      @delete-bike-color="$emit('delete-bike-color', $event)"
      @refresh-bike-colors="$emit('refresh-bike-colors')"
    />

    <UserRolesSubTab v-else-if="activeSub === 'roles'" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import BikeTypeSubTab from './BikeTypeSubTab.vue'
import BikeColorSubTab from './BikeColorSubTab.vue'
import UserRolesSubTab from './UserRolesSubTab.vue'

defineProps({
  bikeTypesList: { type: Array, default: () => [] },
  bikeColorsList: { type: Array, default: () => [] }
})

defineEmits([
  'open-bike-type-modal', 'edit-bike-type', 'delete-bike-type', 'refresh-bike-types',
  'open-bike-color-modal', 'edit-bike-color', 'delete-bike-color', 'refresh-bike-colors'
])

const subTabs = [
  { id: 'bike_types', label: 'أنواع الدراجات', icon: '🚲' },
  { id: 'bike_colors', label: 'ألوان الدراجات', icon: '🎨' },
  { id: 'roles', label: 'الأدوار', icon: '🔑' },
]

const activeSub = ref('bike_types')

defineExpose({ clearSelection: () => {} })
</script>