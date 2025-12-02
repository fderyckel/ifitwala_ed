<!-- ifitwala_ed/ui-spa/src/components/analytics/KpiRow.vue -->
<template>
  <section class="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
    <article
      v-for="item in items"
      :key="item.id"
      class="flex flex-col gap-1 rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm"
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
type KpiItem = {
  id: string
  label: string
  value: number | string
  unit?: string
  hint?: string
  subLabel?: string
}

defineProps<{ items: KpiItem[] }>()
</script>
