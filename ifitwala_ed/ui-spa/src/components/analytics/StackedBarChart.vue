<!-- ifitwala_ed/ui-spa/src/components/analytics/StackedBarChart.vue -->
<!--
  StackedBarChart.vue
  Displays a stacked bar chart to show composition across multiple categories.

  Used by:
  - StudentDemographicAnalytics.vue
  - StudentLogAnalytics.vue
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
			class="analytics-chart analytics-chart--lg"
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

type SeriesDef = { key: string; label: string; color?: string };
type StackedRow = {
	category: string;
	values: Record<string, number>;
	sliceKeys?: Record<string, string>;
};

const props = withDefaults(
	defineProps<{
		title: string;
		series: SeriesDef[];
		rows: StackedRow[];
		expandable?: boolean;
	}>(),
	{
		expandable: false,
	}
);

const emit = defineEmits<{
	(e: 'select', sliceKey: string): void;
	(e: 'expand', option: Record<string, unknown>): void;
}>();

let suppressExpand = false;

const option = computed<ChartOption>(() => {
	const categories = props.rows.map(r => r.category);

	return {
		tooltip: {
			trigger: 'axis',
			axisPointer: { type: 'shadow' },
		},
		legend: { top: 0 },
		grid: { left: 80, right: 16, bottom: 40, top: 30 },
		xAxis: { type: 'category', data: categories },
		yAxis: { type: 'value' },
		series: props.series.map(s => ({
			name: s.label,
			type: 'bar',
			stack: 'total',
			itemStyle: s.color ? { color: s.color } : undefined,
			emphasis: { focus: 'series' },
			data: props.rows.map(row => ({
				value: row.values[s.key] || 0,
				sliceKey: row.sliceKeys?.[s.key],
			})),
		})),
	};
});

function handleClick(params: any) {
	const sliceKey = params?.data?.sliceKey;
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
