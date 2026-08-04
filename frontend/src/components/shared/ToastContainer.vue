<template>
  <transition name="toast-fade">
    <div
      v-if="toast.show"
      class="fixed top-6 left-1/2 -translate-x-1/2 z-[999998] px-5 py-3 rounded-2xl text-sm font-medium shadow-lg max-w-md text-center"
      :class="toast.type === 'success'
        ? 'bg-emerald-100 text-emerald-700'
        : (toast.type === 'error' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700')"
    >
      {{ toast.message }}
    </div>
  </transition>
</template>

<script setup>
import { useToast } from '../../composables/useToast'

const { toast } = useToast()
</script>

<style scoped>
.toast-fade-enter-active, .toast-fade-leave-active { transition: all 0.25s ease; }
.toast-fade-enter-from, .toast-fade-leave-to { opacity: 0; transform: translate(-50%, -10px); }
</style>