<!-- ui-spa/src/components/filters/DateRangePills.vue -->
<template>
  <div class="flex items-center gap-1 rounded-lg bg-surface-soft p-1" :class="wrapClass">
    <button
      v-for="item in items"
      :key="item.value"
      type="button"
      class="rounded-md font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-jacaranda/30 disabled:pointer-events-none disabled:opacity-50"
      :class="[sizeClasses, isSelected(item.value) ? selectedClasses : unselectedClasses]"
      :aria-pressed="isSelected(item.value) ? 'true' : 'false'"
      :disabled="disabled"
      @click="select(item.value)"
    >
      {{ item.label }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

type DateRangeItem = { label: string; value: string }

const props = withDefaults(defineProps<{
  modelValue: string
  items: DateRangeItem[]
  size?: 'sm' | 'md'
  wrapClass?: string
  disabled?: boolean
}>(), {
  size: 'md',
  wrapClass: '',
  disabled: false,
})

const emit = defineEmits<{
  (event: 'update:modelValue', value: string): void
  (event: 'change', value: string): void
}>()

const sizeClasses = computed(() =>
  props.size === 'sm' ? 'px-2.5 py-1 text-[11px]' : 'px-3 py-1.5 text-xs'
)

const selectedClasses = 'bg-white text-ink shadow-sm'
const unselectedClasses = 'text-slate-token/60 hover:text-ink hover:bg-white/50'

const isSelected = (value: string) => props.modelValue === value

function select(value: string) {
  if (props.disabled) return
  if (value === props.modelValue) return
  emit('update:modelValue', value)
  emit('change', value)
}
</script>
