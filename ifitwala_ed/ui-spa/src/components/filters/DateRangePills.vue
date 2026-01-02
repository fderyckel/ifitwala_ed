<!-- ifitwala_ed/ui-spa/src/components/filters/DateRangePills.vue -->
<template>
  <div class="flex items-center gap-1 rounded-lg bg-surface-soft p-1" :class="props.class">
    <button
      v-for="item in items"
      :key="item.value"
      type="button"
      class="font-medium rounded-md transition-all"
      :class="[sizeClasses, isSelected(item.value) ? selectedClasses : unselectedClasses]"
      :aria-pressed="isSelected(item.value)"
      @click="select(item.value)"
    >
      {{ item.label }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

type DateRangeItem = {
  label: string
  value: string
}

const props = withDefaults(defineProps<{
  modelValue: string
  items: DateRangeItem[]
  size?: 'sm' | 'md'
  class?: string
}>(), {
  size: 'md',
  class: '',
})

const emit = defineEmits<{
  (event: 'update:modelValue', value: string): void
  (event: 'change', value: string): void
}>()

const sizeClasses = computed(() => (
  props.size === 'sm' ? 'px-2.5 py-1 text-[11px]' : 'px-3 py-1.5 text-xs'
))

const selectedClasses = 'bg-white text-ink shadow-sm'
const unselectedClasses = 'text-slate-token/60 hover:text-ink hover:bg-white/50'

const isSelected = (value: string) => props.modelValue === value

function select(value: string) {
  if (value === props.modelValue) return
  emit('update:modelValue', value)
  emit('change', value)
}
</script>
