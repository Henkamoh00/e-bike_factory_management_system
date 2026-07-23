        <template>
  <transition name="slide-down">
    <div v-if="count > 0" class="sticky top-0 z-20 bg-indigo-600 text-white rounded-2xl px-5 py-3 mb-4 flex items-center justify-between gap-4 shadow-lg">
      <div class="flex items-center gap-3">
        <span class="font-bold">{{ count }} عنصر محدد</span>
        <button @click="$emit('clear')" class="text-indigo-100 hover:text-white text-sm underline">إلغاء التحديد</button>
      </div>
      <div class="flex items-center gap-2 flex-wrap">
        <slot />
      </div>
    </div>
  </transition>
</template>

<script setup>
defineProps({ count: { type: Number, default: 0 } })
defineEmits(['clear'])
</script>

<style scoped>
.slide-down-enter-active, .slide-down-leave-active { transition: all 0.2s ease; }
.slide-down-enter-from, .slide-down-leave-to { opacity: 0; transform: translateY(-8px); }
</style>