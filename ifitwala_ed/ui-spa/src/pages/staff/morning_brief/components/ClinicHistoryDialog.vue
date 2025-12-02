<template>
	<Dialog v-model="show" :options="{ size: 'xl' }">
		<template #body-content>
			<div class="flex flex-col h-[600px]">
				<!-- Header -->
				<div class="px-6 py-5 border-b border-slate-100 flex items-center justify-between shrink-0">
					<div>
						<h3 class="text-xl font-bold text-ink">Clinic Volume History</h3>
						<p class="text-sm text-slate-500 mt-1">Student patient visits over time</p>
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
const visits = createResource({
	url: 'ifitwala_ed.api.morning_brief.get_clinic_visits_trend',
	makeParams(values) {
		return {
			time_range: selectedRange.value
		}
	},
	auto: false
})

const loading = computed(() => visits.loading)
const schoolName = computed(() => visits.data?.school || 'Loading...')

// Watch for open to fetch
watch(show, (isOpen) => {
	if (isOpen) {
		visits.fetch()
	}
})

// Watch for range change to refetch
watch(selectedRange, () => {
	if (show.value) {
		visits.fetch()
	}
})

// Chart Option
const chartOption = computed(() => {
	const data = visits.data?.data || []
	const dates = data.map(d => d.date)
	const counts = data.map(d => d.count)

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
				itemStyle: { color: '#3b82f6' }, // Blue-500
				areaStyle: {
					color: {
						type: 'linear',
						x: 0, y: 0, x2: 0, y2: 1,
						colorStops: [
							{ offset: 0, color: 'rgba(59, 130, 246, 0.2)' },
							{ offset: 1, color: 'rgba(59, 130, 246, 0)' }
						]
					}
				}
			}
		]
	}
})

</script>
