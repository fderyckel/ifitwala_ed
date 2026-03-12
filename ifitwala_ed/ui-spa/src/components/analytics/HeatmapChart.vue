<!-- ifitwala_ed/ui-spa/src/components/analytics/HeatmapChart.vue -->
<!--
  HeatmapChart.vue
  ECharts wrapper for rendering 2D heatmap visualizations.
  Expects row/bucket data structure.

  Used by:
  - StudentDemographicAnalytics.vue (pages/staff/analytics)
-->
<template>
	<section
		class="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm"
		:class="expandable ? 'analytics-card--interactive' : ''"
		:role="expandable ? 'button' : undefined"
		:tabindex="expandable ? 0 : undefined"
		@click="handleSectionClick"
		@keydown.enter.prevent="handleKeyboardExpand"
		@keydown.space.prevent="handleKeyboardExpand"
	>
		<header class="mb-2 flex items-center justify-between">
			<h3 class="text-sm font-semibold text-slate-700">{{ title }}</h3>
			<slot name="actions" />
		</header>
		<VChart
			class="analytics-chart analytics-chart--xl"
			:option="option"
			:autoresize="{ throttle: 100 }"
			@click="handleClick"
		/>
	</section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { VChart, type ComposeOption, type HeatmapSeriesOption } from '@/lib/echarts';

type ChartOption = ComposeOption<HeatmapSeriesOption>;

type Bucket = { label: string; count: number; sliceKey?: string };
type HeatmapRow = { row: string; buckets: Bucket[] };

const props = withDefaults(
	defineProps<{
		title: string;
		rows: HeatmapRow[];
		columnOrder?: string[];
		expandable?: boolean;
		colorRange?: string[];
	}>(),
	{
		expandable: false,
		colorRange: () => ['#eff6ff', '#93c5fd', '#2563eb'],
	}
);

const emit = defineEmits<{
	(e: 'select', sliceKey: string): void;
	(e: 'expand', option: Record<string, unknown>): void;
}>();

let suppressExpand = false;

const option = computed<ChartOption>(() => {
	const columns = props.columnOrder?.length
		? props.columnOrder
		: Array.from(new Set(props.rows.flatMap(row => row.buckets.map(b => b.label))));

	const data = props.rows.flatMap((row, rowIdx) =>
		columns.map((col, colIdx) => {
			const bucket = row.buckets.find(b => b.label === col);
			return [colIdx, rowIdx, bucket?.count || 0, bucket?.sliceKey];
		})
	);
	const maxValue = Math.max(1, ...data.map(d => Number(d[2]) || 0));

	return {
		tooltip: {
			position: 'top',
			formatter: (params: any) => {
				const rowLabel = props.rows[params.value[1]]?.row || '';
				const colLabel = columns[params.value[0]] || '';
				const count = params.value[2] || 0;
				return `${rowLabel} - ${colLabel}: ${count}`;
			},
		},
		grid: { top: 10, right: 10, bottom: 24, left: 120 },
		xAxis: {
			type: 'category',
			data: columns,
			splitArea: { show: false },
			axisLabel: { rotate: 30 },
		},
		yAxis: {
			type: 'category',
			data: props.rows.map(r => r.row),
			splitArea: { show: false },
		},
		visualMap: {
			show: false,
			min: 0,
			max: maxValue,
			orient: 'horizontal',
			left: 'center',
			bottom: 0,
			inRange: {
				color: props.colorRange,
			},
		},
		series: [
			{
				type: 'heatmap',
				data,
				label: {
					show: true,
					color: '#0f172a',
					fontSize: 11,
					formatter: (params: any) => {
						const count = Number(params?.value?.[2] || 0);
						return count > 0 ? String(count) : '';
					},
				},
				itemStyle: {
					borderColor: '#e2e8f0',
					borderWidth: 1,
				},
				emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.35)' } },
			},
		],
	};
});

function handleClick(params: any) {
	const sliceKey = params?.value?.[3];
	if (sliceKey) {
		suppressNextExpand();
		emit('select', sliceKey);
		return;
	}
	if (props.expandable) {
		suppressNextExpand();
		emit('expand', option.value as Record<string, unknown>);
	}
}

function handleSectionClick() {
	if (!props.expandable || suppressExpand) return;
	emit('expand', option.value as Record<string, unknown>);
}

function handleKeyboardExpand() {
	if (!props.expandable) return;
	emit('expand', option.value as Record<string, unknown>);
}

function suppressNextExpand() {
	suppressExpand = true;
	window.setTimeout(() => {
		suppressExpand = false;
	}, 0);
}
</script>
