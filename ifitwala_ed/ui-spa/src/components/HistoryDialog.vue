<template>
	<Dialog v-model="show" :options="{ size: 'xl' }">
		<template #body-content>
			<div class="flex flex-col h-[600px]">
				<!-- Header -->
				<div class="px-6 py-5 border-b border-slate-100 flex items-center justify-between shrink-0">
					<div>
						<h3 class="text-xl font-bold text-ink">{{ title }}</h3>
						<p v-if="subtitle" class="text-sm text-slate-500 mt-1">{{ subtitle }}</p>
					</div>
					<div class="flex items-center gap-4">
						<!-- Time Range Toggles -->
						<div class="flex bg-slate-100 p-1 rounded-lg">
							<button v-for="range in ranges" :key="range.value" @click="selectedRange = range.value"
								class="px-3 py-1 text-xs font-semibold rounded-md transition-all"
								:class="selectedRange === range.value ? 'bg-white text-ink shadow-sm' : 'text-slate-500 hover:text-slate-700'">
								{{ range.label }}
							</button>
						</div>

						<button @click="show = false"
							class="p-2 hover:bg-slate-100 rounded-full transition-colors text-slate-400 hover:text-ink">
							<FeatherIcon name="x" class="h-5 w-5" />
						</button>
					</div>
				</div>

				<!-- Content -->
				<div class="flex-1 p-6 flex flex-col items-center justify-center bg-white relative">

					<div v-if="loading" class="absolute inset-0 flex items-center justify-center bg-white/80 z-10">
						<FeatherIcon name="loader" class="h-8 w-8 animate-spin text-jacaranda" />
					</div>

					<div class="w-full h-full">
						<AnalyticsChart :option="chartOption" />
					</div>

					<div class="mt-4 text-xs text-slate-400 font-medium">
						Showing data for: <span class="text-ink">{{ schoolName }}</span>
					</div>

				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Dialog, FeatherIcon, createResource } from 'frappe-ui'
import AnalyticsChart from '@/components/analytics/AnalyticsChart.vue'

const props = defineProps<{
	modelValue: boolean
	title: string
	subtitle?: string
	method: string
	color?: string
	params?: Record<string, any>
}>()

const emit = defineEmits(['update:modelValue'])

const show = computed({
	get: () => props.modelValue,
	set: (val) => emit('update:modelValue', val)
})

const ranges = [
	{ label: '1M', value: '1M' },
	{ label: '3M', value: '3M' },
	{ label: '6M', value: '6M' },
	{ label: 'YTD', value: 'YTD' },
]

const selectedRange = ref('1M')

// Resource
const resource = createResource({
	url: props.method,
	makeParams(values) {
		return {
			time_range: selectedRange.value,
			...props.params
		}
	},
	auto: false
})

const loading = computed(() => resource.loading)
const schoolName = computed(() => resource.data?.school || 'Loading...')

// Watch for open to fetch
watch(show, (isOpen) => {
	if (isOpen) {
		resource.fetch()
	}
})

// Watch for range change to refetch
watch(selectedRange, () => {
	if (show.value) {
		resource.fetch()
	}
})

// Chart Option
const chartOption = computed(() => {
	const data = resource.data?.data || []
	const dates = data.map((d: any) => d.date)
	const counts = data.map((d: any) => d.count)

	// Use prop color or default to Blue-500
	const baseColor = props.color || '#3b82f6'

	// Convert hex to rgba for area style
	// Simple hex to rgb conversion
	let r = 0, g = 0, b = 0
	if (baseColor.length === 7) {
		r = parseInt(baseColor.slice(1, 3), 16)
		g = parseInt(baseColor.slice(3, 5), 16)
		b = parseInt(baseColor.slice(5, 7), 16)
	}

	return {
		tooltip: {
			trigger: 'axis',
			className: 'chart-tooltip',
		},
		grid: {
			top: 30,
			right: 20,
			bottom: 30,
			left: 40,
			containLabel: true
		},
		xAxis: {
			type: 'category',
			data: dates,
			axisLine: { show: false },
			axisTick: { show: false },
			axisLabel: { color: '#64748b', fontSize: 11 }
		},
		yAxis: {
			type: 'value',
			splitLine: {
				lineStyle: { type: 'dashed', color: '#e2e8f0' }
			},
			axisLabel: { color: '#64748b', fontSize: 11 }
		},
		series: [
			{
				data: counts,
				type: 'line',
				smooth: true,
				symbol: 'circle',
				symbolSize: 6,
				itemStyle: { color: baseColor },
				areaStyle: {
					color: {
						type: 'linear',
						x: 0, y: 0, x2: 0, y2: 1,
						colorStops: [
							{ offset: 0, color: `rgba(${r}, ${g}, ${b}, 0.2)` },
							{ offset: 1, color: `rgba(${r}, ${g}, ${b}, 0)` }
						]
					}
				}
			}
		]
	}
})

</script>
