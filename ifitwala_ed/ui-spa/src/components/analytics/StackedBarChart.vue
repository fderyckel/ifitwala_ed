<!-- ifitwala_ed/ui-spa/src/components/analytics/StackedBarChart.vue -->
<template>
  <section class="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
    <header class="mb-2 flex items-center justify-between">
      <h3 class="text-sm font-semibold text-slate-700">{{ title }}</h3>
      <slot name="actions" />
    </header>
    <VChart
      class="analytics-chart analytics-chart--lg"
      :option="option"
      :autoresize="{ throttle: 100 }"
      @click="handleClick"
    />
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { VChart, type BarSeriesOption, type ComposeOption } from '@/lib/echarts'

type ChartOption = ComposeOption<BarSeriesOption>

type SeriesDef = { key: string; label: string; color?: string }
type StackedRow = { category: string; values: Record<string, number>; sliceKeys?: Record<string, string> }

const props = defineProps<{ title: string; series: SeriesDef[]; rows: StackedRow[] }>()

const emit = defineEmits<{
  (e: 'select', sliceKey: string): void
}>()

const option = computed<ChartOption>(() => {
  const categories = props.rows.map((r) => r.category)

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
    },
    legend: { top: 0 },
    grid: { left: 80, right: 16, bottom: 40, top: 30 },
    xAxis: { type: 'category', data: categories },
    yAxis: { type: 'value' },
    series: props.series.map((s) => ({
      name: s.label,
      type: 'bar',
      stack: 'total',
      itemStyle: s.color ? { color: s.color } : undefined,
      emphasis: { focus: 'series' },
      data: props.rows.map((row) => ({
        value: row.values[s.key] || 0,
        sliceKey: row.sliceKeys?.[s.key],
      })),
    })),
  }
})

function handleClick(params: any) {
  const sliceKey = params?.data?.sliceKey
  if (sliceKey) emit('select', sliceKey)
}
</script>
