<!-- ifitwala_ed/ui-spa/src/components/analytics/TagCloudBar.vue -->
<!--
  TagCloudBar.vue
  Displays a simple horizontal bar chart suited for "tag cloud" style data (high cardinality, low counts).

  Used by:
  - StudentLogAnalytics.vue (Frequency analysis)
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
			class="analytics-chart analytics-chart--sm"
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

type Item = { label: string; count: number; sliceKey?: string };

const props = withDefaults(
	defineProps<{
		title: string;
		items: Item[];
		max?: number;
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
	const limited = props.max ? props.items.slice(0, props.max) : props.items;
	const labels = limited.map(i => i.label);
	const data = limited.map(i => ({ value: i.count, sliceKey: i.sliceKey }));

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
				const item = limited[p.dataIndex];
				return `${item?.label || ''}: ${item?.count || 0}`;
			},
		},
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
