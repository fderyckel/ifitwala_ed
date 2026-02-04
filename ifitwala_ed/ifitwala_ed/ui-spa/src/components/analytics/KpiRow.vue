<!-- ifitwala_ed/ui-spa/src/components/analytics/KpiRow.vue -->
<!--
  KpiRow.vue
  Responsive grid of KPI cards displaying high-level metrics. Supports click interactions.

  Used by:
  - EnrollmentAnalytics.vue
  - RoomUtilization.vue
  - StudentDemographicAnalytics.vue
  - InquiryAnalytics.vue
  (all in pages/staff/analytics)
-->
<template>
  <section class="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
    <article
      v-for="item in items"
      :key="item.id"
      class="flex flex-col gap-1 rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm"
      :class="clickable ? 'cursor-pointer transition hover:border-slate-300 hover:shadow-md' : ''"
      :tabindex="clickable ? 0 : undefined"
      @click="handleSelect(item)"
      @keydown.enter.prevent="handleSelect(item)"
      @keydown.space.prevent="handleSelect(item)"
    >
      <div class="flex items-center justify-between text-xs text-slate-500">
        <span>{{ item.label }}</span>
        <span v-if="item.hint" class="text-slate-400">{{ item.hint }}</span>
      </div>
      <div class="flex items-end gap-2">
        <p class="text-2xl font-semibold text-slate-800">{{ item.value }}</p>
        <span v-if="item.unit" class="text-sm text-slate-500">{{ item.unit }}</span>
      </div>
      <p v-if="item.subLabel" class="text-xs text-slate-500">{{ item.subLabel }}</p>
    </article>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
type KpiItem = {
  id: string
  label: string
  value: number | string
  unit?: string
  hint?: string
  subLabel?: string
}

const props = defineProps<{ items: KpiItem[]; clickable?: boolean }>()

const emit = defineEmits<{
  (e: 'select', item: KpiItem): void
}>()

const clickable = computed(() => props.clickable ?? false)

function handleSelect(item: KpiItem) {
  if (!clickable.value) return
  emit('select', item)
}
</script>
