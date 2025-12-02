<!-- ifitwala_ed/ui-spa/src/components/analytics/TagCloudBar.vue -->
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
import { VChart, type BarSeriesOption, type ComposeOption } from '@/lib/echarts'

type ChartOption = ComposeOption<BarSeriesOption>

type Item = { label: string; count: number; sliceKey?: string }

const props = defineProps<{
  title: string
  items: Item[]
  max?: number
}>()

const emit = defineEmits<{
  (e: 'select', sliceKey: string): void
}>()

const option = computed<ChartOption>(() => {
  const limited = props.max ? props.items.slice(0, props.max) : props.items
  const labels = limited.map((i) => i.label)
  const data = limited.map((i) => ({ value: i.count, sliceKey: i.sliceKey }))

  return {
    grid: { left: 120, right: 20, top: 16, bottom: 16 },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: labels },
    series: [
      {
        type: 'bar',
        data,
        itemStyle: { borderRadius: [0, 6, 6, 0] },
      },
    ],
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (p: any) => {
        const item = limited[p.dataIndex]
        return `${item?.label || ''}: ${item?.count || 0}`
      },
    },
  }
})

function handleClick(params: any) {
  const sliceKey = params?.data?.sliceKey
  if (sliceKey) emit('select', sliceKey)
}
</script>

<style scoped>
.analytics-chart {
  width: 100%;
  min-height: 240px;
}
</style>
