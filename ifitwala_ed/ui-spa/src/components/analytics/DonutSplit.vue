<!-- ifitwala_ed/ui-spa/src/components/analytics/DonutSplit.vue -->
<!--
  DonutSplit.vue
  Displays a donut chart with a side lagend/list of items.
  Matches design system colors (Leaf, Flame, etc.).

  Used by:
  - EnrollmentAnalytics.vue
  - StudentDemographicAnalytics.vue
-->
<template>
  <section class="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
    <header class="mb-2 flex items-center justify-between">
      <h3 class="text-sm font-semibold text-slate-700">{{ title }}</h3>
      <slot name="actions" />
    </header>
    <div class="flex flex-col gap-3 md:flex-row md:items-center">
      <div class="md:w-2/3">
        <VChart
          class="analytics-chart"
          :option="option"
          :autoresize="{ throttle: 100 }"
          @click="handleClick"
        />
      </div>
      <ul class="md:w-1/3 space-y-1 text-sm text-slate-600">
        <li v-for="item in coloredItems" :key="item.label" class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span
              class="h-2.5 w-2.5 rounded-full"
              :style="{ background: item.color || '#0ea5e9' }"
            ></span>
            <span>{{ item.label }}</span>
          </div>
          <span class="text-slate-500">{{ item.count }}<span v-if="item.pct != null"> ({{ item.pct }}%)</span></span>
        </li>
      </ul>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { VChart, type ComposeOption, type PieSeriesOption } from '@/lib/echarts'

type ChartOption = ComposeOption<PieSeriesOption>

type Item = { label: string; count: number; pct?: number; color?: string; sliceKey?: string }

const props = defineProps<{
  title: string
  items: Item[]
}>()

const emit = defineEmits<{
  (e: 'select', sliceKey: string): void
}>()

const tokenColorVars = ['--jacaranda', '--leaf', '--flame', '--moss', '--clay', '--slate', '--canopy', '--ink']
const fallbackPalette = ['#7e6bd6', '#1f7a45', '#f25b32', '#7faa63', '#b6522b', '#475569', '#0b3d2b', '#071019']

function resolveCssColor(variable: string, fallback: string) {
  if (typeof window === 'undefined') return fallback
  const value = getComputedStyle(document.documentElement).getPropertyValue(variable)
  return value?.trim() || fallback
}

const palette = computed(() => tokenColorVars.map((token, idx) => resolveCssColor(token, fallbackPalette[idx])))

const coloredItems = computed<Item[]>(() => {
  const paletteColors = palette.value
  return props.items.map((item, index) => {
    const paletteColor = paletteColors[index % paletteColors.length] || fallbackPalette[index % fallbackPalette.length]
    return { ...item, color: item.color || paletteColor }
  })
})

const option = computed<ChartOption>(() => ({
  color: coloredItems.value.map((i) => i.color),
  tooltip: {
    trigger: 'item',
    formatter: (p: any) => `${p.name}: ${p.value}${p.data?.pct != null ? ` (${p.data.pct}%)` : ''}`,
  },
  legend: { show: false },
  series: [
    {
      type: 'pie',
      radius: ['40%', '70%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 1 },
      label: { show: false },
      emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold' } },
      data: coloredItems.value.map((i) => ({
        name: i.label,
        value: i.count,
        pct: i.pct,
        itemStyle: i.color ? { color: i.color } : undefined,
        sliceKey: i.sliceKey,
      })),
    },
  ],
}))

function handleClick(params: any) {
  const sliceKey = params?.data?.sliceKey
  if (sliceKey) emit('select', sliceKey)
}
</script>
