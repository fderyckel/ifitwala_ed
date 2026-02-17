<!-- ifitwala_ed/ui-spa/src/components/analytics/HistogramBuckets.vue -->
<!--
  HistogramBuckets.vue
  Displays a column/bar chart representing distribution buckets.

  Used by:
  - EnrollmentAnalytics.vue (Age distribution)
-->
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
import { computed } from 'vue';
import { VChart, type BarSeriesOption, type ComposeOption } from '@/lib/echarts';

type ChartOption = ComposeOption<BarSeriesOption>;

type Bucket = { label: string; count: number; sliceKey?: string };

const props = defineProps<{
	title: string;
	buckets: Bucket[];
}>();

const emit = defineEmits<{
	(e: 'select', sliceKey: string): void;
}>();

const option = computed<ChartOption>(() => ({
	tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
	grid: { left: 50, right: 10, bottom: 40, top: 20 },
	xAxis: { type: 'category', data: props.buckets.map(b => b.label) },
	yAxis: { type: 'value' },
	series: [
		{
			type: 'bar',
			data: props.buckets.map(b => ({ value: b.count, sliceKey: b.sliceKey })),
			itemStyle: { borderRadius: [4, 4, 0, 0] },
			showBackground: true,
			backgroundStyle: { color: '#f8fafc' },
		},
	],
}));

function handleClick(params: any) {
	const sliceKey = params?.data?.sliceKey;
	if (sliceKey) emit('select', sliceKey);
}
</script>
