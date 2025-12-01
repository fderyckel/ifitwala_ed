<!-- ifitwala_ed/ui-spa/src/components/analytics/AnalyticsChart.vue -->
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

<style scoped>
.analytics-chart {
	width: 100%;
	min-height: 260px;
}
</style>
