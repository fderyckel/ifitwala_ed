<!-- ifitwala_ed/ui-spa/src/components/analytics/HeatmapCohortNationality.vue -->
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
import { VChart, type ComposeOption, type HeatmapSeriesOption } from '@/lib/echarts'

type ChartOption = ComposeOption<HeatmapSeriesOption>

type Bucket = {
  label: string
  count: number
  sliceKey?: string
}

type Row = {
  cohort: string
  buckets: Bucket[]
}

const props = defineProps<{
  title: string
  rows: Row[]
  columnOrder?: string[]
}>()

const emit = defineEmits<{
  (e: 'select', sliceKey: string): void
}>()

const option = computed<ChartOption>(() => {
  const columns =
    props.columnOrder?.length
      ? props.columnOrder
      : Array.from(
          new Set(
            props.rows.flatMap((row) => row.buckets.map((b) => b.label))
          )
        )

  const data = props.rows.flatMap((row, rowIdx) =>
    columns.map((col, colIdx) => {
      const bucket = row.buckets.find((b) => b.label === col)
      return [colIdx, rowIdx, bucket?.count || 0, bucket?.sliceKey]
    })
  )

  return {
    tooltip: {
      position: 'top',
      formatter: (params: any) => {
        const cohort = props.rows[params.value[1]]?.cohort || ''
        const nat = columns[params.value[0]] || ''
        const count = params.value[2] || 0
        return `${cohort} - ${nat}: ${count}`
      },
    },
    grid: { top: 10, right: 10, bottom: 40, left: 120 },
    xAxis: {
      type: 'category',
      data: columns,
      splitArea: { show: true },
      axisLabel: { rotate: 30 },
    },
    yAxis: {
      type: 'category',
      data: props.rows.map((r) => r.cohort),
      splitArea: { show: true },
    },
    visualMap: {
      min: 0,
      max: Math.max(...data.map((d) => d[2] as number), 1),
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: 0,
    },
    series: [
      {
        type: 'heatmap',
        data,
        emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.35)' } },
      },
    ],
  }
})

function handleClick(params: any) {
  const sliceKey = params?.value?.[3]
  if (sliceKey) emit('select', sliceKey)
}
</script>

<style scoped>
.analytics-chart {
  width: 100%;
  min-height: 320px;
}
</style>
