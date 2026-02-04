<!-- ifitwala_ed/ui-spa/src/components/analytics/AnalyticsChart.vue -->
<!--
  AnalyticsChart.vue
  A wrapper component for ECharts (VChart) to standardize configuration and resizing behavior across analytics pages.

  Used by:
  - HistoryDialog.vue
  - Various Analytics Pages (via composition)
-->
<template>
	<VChart
		class="analytics-chart"
		:option="option"
		:autoresize="{ throttle: 100 }"
	/>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { VChart, type ComposeOption } from '@/lib/echarts'

// Example: base option type; you can refine later with your imported option types.
type BaseChartOption = ComposeOption<unknown>

const props = defineProps<{
	option: BaseChartOption
}>()

const option = computed(() => props.option)
</script>
