<!-- ifitwala_ed/ui-spa/src/components/analytics/HorizontalBarTopN.vue -->
<template>
  <section class="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
    <header class="mb-2 flex items-center justify-between">
      <h3 class="text-sm font-semibold text-slate-700">{{ title }}</h3>
      <slot name="actions" />
    </header>
    <VChart
      class="analytics-chart"
      :option="option"
      :autoresize="{ throttle: 100 }"
      @click="handleClick"
    />
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { VChart, type ComposeOption, type BarSeriesOption } from '@/lib/echarts'

type ChartOption = ComposeOption<BarSeriesOption>

type Item = {
  label: string
  count: number
  pct?: number
  color?: string
  sliceKey?: string
}

const props = defineProps<{
  title: string
  items: Item[]
}>()

const emit = defineEmits<{
  (e: 'select', sliceKey: string): void
}>()

const option = computed<ChartOption>(() => {
  const labels = props.items.map((i) => i.label)
  const data = props.items.map((i) => ({
    value: i.count,
    itemStyle: i.color ? { color: i.color } : undefined,
    sliceKey: i.sliceKey,
  }))

  return {
    grid: { left: 120, right: 24, top: 16, bottom: 16 },
    xAxis: { type: 'value', axisLabel: { color: '#64748b' } },
    yAxis: { type: 'category', data: labels, axisLabel: { color: '#0f172a' } },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: any) => {
        const p = Array.isArray(params) ? params[0] : params
        const item = props.items[p.dataIndex]
        const pct = item?.pct != null ? ` (${item.pct}%)` : ''
        return `${item?.label || ''}: ${item?.count}${pct}`
      },
    },
    series: [
      {
        type: 'bar',
        data,
        showBackground: true,
        backgroundStyle: { color: '#f8fafc' },
      },
    ],
  }
})

function handleClick(params: any) {
  const sliceKey = params?.data?.sliceKey
  if (sliceKey) emit('select', sliceKey)
}
</script>
