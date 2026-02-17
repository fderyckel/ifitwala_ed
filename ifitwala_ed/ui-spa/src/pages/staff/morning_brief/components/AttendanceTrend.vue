<template>
	<div class="paper-card p-5">
		<div class="flex items-center justify-between mb-4">
			<h3 class="section-header flex items-center gap-2 text-slate-500">
				<FeatherIcon name="bar-chart-2" class="h-3 w-3" /> 30-Day Absence Trend
			</h3>
		</div>
		<div class="h-64 w-full">
			<AnalyticsChart :option="chartOption" />
		</div>
	</div>
</template>

<script setup>
import { computed } from 'vue';
import { FeatherIcon } from 'frappe-ui';
import AnalyticsChart from '@/components/analytics/AnalyticsChart.vue';

const props = defineProps({
	data: {
		type: Array,
		default: () => [],
	},
});

const chartOption = computed(() => {
	// Data is expected to be [{ date: '2023-10-01', count: 5 }, ...]
	// We need to fill in missing dates? Or just plot what we have?
	// Ideally fill missing dates for a smooth line.

	// Let's just map for now.
	const dates = props.data.map(d => {
		const date = new Date(d.date);
		return `${date.getDate()}/${date.getMonth() + 1}`;
	});
	const counts = props.data.map(d => d.count);

	return {
		tooltip: {
			trigger: 'axis',
			formatter: '{b}: {c} Absences',
		},
		grid: {
			top: '10%',
			left: '3%',
			right: '4%',
			bottom: '3%',
			containLabel: true,
		},
		xAxis: {
			type: 'category',
			boundaryGap: false,
			data: dates,
			axisLine: { show: false },
			axisTick: { show: false },
			axisLabel: { color: '#64748b', fontSize: 10 },
		},
		yAxis: {
			type: 'value',
			splitLine: { lineStyle: { type: 'dashed', color: '#e2e8f0' } },
			axisLabel: { color: '#64748b', fontSize: 10 },
		},
		series: [
			{
				name: 'Absences',
				type: 'line',
				smooth: true,
				symbol: 'none',
				areaStyle: {
					color: {
						type: 'linear',
						x: 0,
						y: 0,
						x2: 0,
						y2: 1,
						colorStops: [
							{ offset: 0, color: 'rgba(239, 68, 68, 0.2)' }, // Red-500 with opacity
							{ offset: 1, color: 'rgba(239, 68, 68, 0)' },
						],
					},
				},
				lineStyle: { width: 2, color: '#ef4444' }, // Red-500
				data: counts,
			},
		],
	};
});
</script>
