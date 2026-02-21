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
		@click="onClick"
	/>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { VChart } from '@/lib/echarts';

// Keep option intentionally broad; concrete chart builders provide their own shape.
type BaseChartOption = Record<string, unknown>;

const props = defineProps<{
	option: BaseChartOption;
}>();

const emit = defineEmits<{
	(event: 'click', payload: unknown): void;
}>();

const option = computed(() => props.option);

function onClick(payload: unknown) {
	emit('click', payload);
}
</script>
