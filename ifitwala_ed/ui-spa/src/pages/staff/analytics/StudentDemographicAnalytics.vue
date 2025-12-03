<!-- ifitwala_ed/ui-spa/src/pages/staff/analytics/StudentDemographicAnalytics.vue -->
<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { createResource } from 'frappe-ui'

import FiltersBar from '@/components/analytics/FiltersBar.vue'
import KpiRow from '@/components/analytics/KpiRow.vue'
import HorizontalBarTopN from '@/components/analytics/HorizontalBarTopN.vue'
import HeatmapChart from '@/components/analytics/HeatmapChart.vue'
import StackedBarChart from '@/components/analytics/StackedBarChart.vue'
import DonutSplit from '@/components/analytics/DonutSplit.vue'
import HistogramBuckets from '@/components/analytics/HistogramBuckets.vue'
import TagCloudBar from '@/components/analytics/TagCloudBar.vue'
import SideDrawerList from '@/components/analytics/SideDrawerList.vue'

type ViewPreset = 'student' | 'admissions' | 'marketing'

type FilterState = {
	school: string | null
	cohort: string | null
	preset: ViewPreset
}

type SliceMeta = { entity: 'student' | 'guardian'; title?: string }

type DashboardResponse = {
	kpis: {
		total_students: number
		cohorts_represented: number
		unique_nationalities: number
		unique_home_languages: number
		residency_split_pct: {
			local: number
			expat: number
			boarder: number
			other: number
		}
		pct_with_siblings: number
		guardian_diversity_score: number
	}
	nationality_distribution: { label: string; count: number; pct?: number; sliceKey?: string }[]
	nationality_by_cohort: { cohort: string; buckets: { label: string; count: number; sliceKey?: string }[] }[]
	gender_by_cohort: { cohort: string; female: number; male: number; other: number; sliceKeys?: Record<string, string> }[]
	residency_status: { label: string; count: number; pct?: number; sliceKey?: string }[]
	age_distribution: { bucket: string; count: number; sliceKey?: string }[]
	home_language: { label: string; count: number; pct?: number; sliceKey?: string }[]
	multilingual_profile: { label: string; count: number; pct?: number; sliceKey?: string }[]
	family_kpis: {
		family_count: number
		avg_children_per_family: number
		pct_families_with_2_plus: number
	}
	sibling_distribution: { cohort: string; none: number; older: number; younger: number; sliceKeys?: Record<string, string> }[]
	family_size_histogram: { bucket: string; count: number; sliceKey?: string }[]
	guardian_nationality: { label: string; count: number; pct?: number; sliceKey?: string }[]
	guardian_comm_language: { label: string; count: number; pct?: number; sliceKey?: string }[]
	guardian_residence_country: { label: string; count: number; pct?: number; sliceKey?: string }[]
	guardian_residence_city: { label: string; count: number; sliceKey?: string }[]
	guardian_sector: { label: string; count: number; pct?: number; sliceKey?: string }[]
	financial_guardian: { label: string; count: number; pct?: number; sliceKey?: string }[]
	slices?: Record<string, SliceMeta>
}

const viewPresets: { id: ViewPreset; label: string }[] = [
	{ id: 'student', label: 'Student View' },
	{ id: 'admissions', label: 'Admissions View' },
	{ id: 'marketing', label: 'Marketing View' },
]

const filters = ref<FilterState>({
	school: null,
	cohort: null,
	preset: 'student',
})

const filterMetaResource = createResource({
	url: 'ifitwala_ed.api.student_demographics_dashboard.get_filter_meta',
	method: 'GET',
	auto: true,
})

const filterMeta = computed(() => (filterMetaResource.data as any) || {})
const schools = computed(() => filterMeta.value.schools || [])
const cohorts = computed(() => filterMeta.value.cohorts || [])

watch(
	filterMeta,
	(data) => {
		if (!data) return
		if (data.default_school && !filters.value.school) {
			filters.value.school = data.default_school
		}
	},
	{ immediate: true }
)

const dashboardResource = createResource({
	url: 'ifitwala_ed.api.student_demographics_dashboard.get_dashboard',
	method: 'POST',
	params: () => ({ filters: filters.value }),
	auto: false,
})

const emptyDashboard: DashboardResponse = {
	kpis: {
		total_students: 0,
		cohorts_represented: 0,
		unique_nationalities: 0,
		unique_home_languages: 0,
		residency_split_pct: { local: 0, expat: 0, boarder: 0, other: 0 },
		pct_with_siblings: 0,
		guardian_diversity_score: 0,
	},
	nationality_distribution: [],
	nationality_by_cohort: [],
	gender_by_cohort: [],
	residency_status: [],
	age_distribution: [],
	home_language: [],
	multilingual_profile: [],
	family_kpis: {
		family_count: 0,
		avg_children_per_family: 0,
		pct_families_with_2_plus: 0,
	},
	sibling_distribution: [],
	family_size_histogram: [],
	guardian_nationality: [],
	guardian_comm_language: [],
	guardian_residence_country: [],
	guardian_residence_city: [],
	guardian_sector: [],
	financial_guardian: [],
	slices: {},
}

const dashboard = computed<DashboardResponse>(() => {
	return (dashboardResource.data as DashboardResponse) || emptyDashboard
})

let debounceTimer: number | undefined
function debounce(fn: () => void, delay = 400) {
	window.clearTimeout(debounceTimer)
	debounceTimer = window.setTimeout(fn, delay)
}

async function loadDashboard() {
	await dashboardResource.fetch()
}

watch(
	filters,
	() => {
		debounce(() => loadDashboard())
	},
	{ deep: true, immediate: true }
)

const kpiItems = computed(() => [
	{ id: 'total_students', label: 'Total Students (filtered)', value: dashboard.value.kpis.total_students },
	{ id: 'total_cohorts', label: 'Total Cohorts Represented', value: dashboard.value.kpis.cohorts_represented },
	{ id: 'unique_nationalities', label: 'Unique Nationalities', value: dashboard.value.kpis.unique_nationalities },
	{ id: 'unique_home_languages', label: 'Unique Home Languages', value: dashboard.value.kpis.unique_home_languages },
	{
		id: 'residency_split',
		label: 'Residency Split (Local / Expat / Boarder)',
		value: `${dashboard.value.kpis.residency_split_pct.local}% / ${dashboard.value.kpis.residency_split_pct.expat}% / ${dashboard.value.kpis.residency_split_pct.boarder}%`,
	},
	{ id: 'siblings_pct', label: '% with siblings enrolled', value: `${dashboard.value.kpis.pct_with_siblings}%` },
	{ id: 'guardian_diversity', label: 'Guardian Diversity Score', value: dashboard.value.kpis.guardian_diversity_score },
])

const familyKpis = computed(() => [
	{ id: 'family_count', label: 'Number of Families', value: dashboard.value.family_kpis.family_count },
	{
		id: 'avg_children',
		label: 'Avg. number of children per family',
		value: dashboard.value.family_kpis.avg_children_per_family,
	},
	{
		id: 'pct_two_plus',
		label: '% families with 2+ enrolled children',
		value: `${dashboard.value.family_kpis.pct_families_with_2_plus}%`,
	},
])

const stackedGenderSeries = [
	{ key: 'female', label: 'Female', color: '#fb7185' },
	{ key: 'male', label: 'Male', color: '#38bdf8' },
	{ key: 'other', label: 'Other', color: '#a855f7' },
]

const siblingSeries = [
	{ key: 'none', label: 'No siblings', color: '#94a3b8' },
	{ key: 'older', label: 'Has older siblings', color: '#38bdf8' },
	{ key: 'younger', label: 'Has younger siblings', color: '#fbbf24' },
]

const genderRows = computed(() =>
	dashboard.value.gender_by_cohort.map((row) => ({
		category: row.cohort,
		values: { female: row.female, male: row.male, other: row.other },
		sliceKeys: row.sliceKeys,
	}))
)

const siblingRows = computed(() =>
	dashboard.value.sibling_distribution.map((row) => ({
		category: row.cohort,
		values: { none: row.none, older: row.older, younger: row.younger },
		sliceKeys: row.sliceKeys,
	}))
)

const nationalityHeatmapRows = computed(() =>
	dashboard.value.nationality_by_cohort.map((row) => ({
		row: row.cohort,
		buckets: row.buckets,
	}))
)

const sliceDrawerOpen = ref(false)
const activeSliceKey = ref<string | null>(null)
const sliceRows = ref<any[]>([])
const sliceStart = ref(0)
const slicePageLength = 50

const sliceResource = createResource({
	url: 'ifitwala_ed.api.student_demographics_dashboard.get_slice_entities',
	method: 'POST',
	params: () => ({
		slice_key: activeSliceKey.value,
		filters: filters.value,
		start: sliceStart.value,
		page_length: slicePageLength,
	}),
	auto: false,
})

const sliceMeta = computed<SliceMeta | null>(() => {
	if (!activeSliceKey.value) return null
	return dashboard.value.slices?.[activeSliceKey.value] || null
})

async function loadSlice(reset = false) {
	if (!activeSliceKey.value) return
	if (reset) {
		sliceStart.value = 0
		sliceRows.value = []
	}
	console.log('Fetching slice:', activeSliceKey.value, 'Start:', sliceStart.value)
	await sliceResource.fetch()
	let rows = (sliceResource.data as any) || []
	console.log('Raw slice response type:', typeof rows, 'Is Array:', Array.isArray(rows))
	console.log('Raw slice response content:', JSON.stringify(rows))

	// Handle case where frappe-ui doesn't unwrap the message list automatically
	if (rows.message && Array.isArray(rows.message)) {
		console.log('Unwrapping message object...')
		rows = rows.message
	}

	if (Array.isArray(rows) && rows.length) {
		console.log('Updating sliceRows with', rows.length, 'rows')
		sliceRows.value = reset ? rows : [...sliceRows.value, ...rows]
		sliceStart.value += rows.length
	} else {
		console.log('No rows found or rows is empty')
	}
	console.log('Final sliceRows length:', sliceRows.value.length)
}

function openSliceDrawer(sliceKey: string) {
	console.log('Opening drawer for slice:', sliceKey)
	activeSliceKey.value = sliceKey
	sliceDrawerOpen.value = true
	loadSlice(true)
}

function closeSliceDrawer() {
	sliceDrawerOpen.value = false
	activeSliceKey.value = null
	sliceRows.value = []
}

function setPreset(preset: ViewPreset) {
	filters.value.preset = preset
}
</script>

<template>
	<div class="min-h-full px-4 py-4 md:px-6 lg:px-8">
		<header class="flex flex-wrap items-center justify-between gap-3">
			<div>
				<h1 class="text-base font-semibold tracking-tight text-slate-900">
					Student Demographic Analytics
				</h1>
				<p class="mt-0.5 text-xs text-slate-500">
					Active-student demographics for academic admin, admissions, and marketing.
				</p>
			</div>
		</header>

		<FiltersBar>
			<div class="flex flex-col gap-1 w-40">
				<label class="text-[0.65rem] font-medium uppercase tracking-wide text-slate-500">
					School
				</label>
				<select v-model="filters.school" class="h-8 rounded-md border border-slate-200 px-2 text-xs">
					<option value="">
						All
					</option>
					<option v-for="s in schools" :key="s.name" :value="s.name">
						{{ s.label || s.name }}
					</option>
				</select>
			</div>

			<div class="flex flex-col gap-1 w-40">
				<label class="text-[0.65rem] font-medium uppercase tracking-wide text-slate-500">
					Cohort
				</label>
				<select v-model="filters.cohort" class="h-8 rounded-md border border-slate-200 px-2 text-xs">
					<option value="">
						All
					</option>
					<option v-for="c in cohorts" :key="c.name" :value="c.name">
						{{ c.label || c.name }}
					</option>
				</select>
			</div>

			<div class="flex flex-col gap-1">
				<label class="text-[0.65rem] font-medium uppercase tracking-wide text-slate-500">
					View Preset
				</label>
				<div class="flex items-center gap-2">
					<button v-for="preset in viewPresets" :key="preset.id" class="rounded-md border px-2 py-1 text-xs" :class="filters.preset === preset.id
						? 'border-sky-500 bg-sky-50 text-sky-700'
						: 'border-slate-200 text-slate-600 hover:bg-slate-50'
						" @click="setPreset(preset.id)">
						{{ preset.label }}
					</button>
				</div>
			</div>
		</FiltersBar>

		<section class="mt-4 space-y-4">
			<KpiRow :items="kpiItems" />

			<div class="grid gap-4 lg:grid-cols-2">
				<HorizontalBarTopN title="Nationality Distribution (Top 10 + Other)" :items="dashboard.nationality_distribution"
					@select="openSliceDrawer" />
				<HeatmapChart title="Nationality by Cohort" :rows="nationalityHeatmapRows" @select="openSliceDrawer" />
				<StackedBarChart title="Gender Split by Cohort" :series="stackedGenderSeries" :rows="genderRows"
					@select="openSliceDrawer" />
				<DonutSplit title="Residency Status" :items="dashboard.residency_status" @select="openSliceDrawer" />
				<HistogramBuckets title="Age Distribution"
					:buckets="dashboard.age_distribution.map((b) => ({ label: b.bucket, count: b.count, sliceKey: b.sliceKey }))"
					@select="openSliceDrawer" />
			</div>

			<div class="grid gap-4 lg:grid-cols-2">
				<DonutSplit title="Home Language Distribution" :items="dashboard.home_language" @select="openSliceDrawer" />
				<DonutSplit title="Multilingual Profile (1 / 2 / 3+)" :items="dashboard.multilingual_profile"
					@select="openSliceDrawer" />
			</div>

			<section class="space-y-3">
				<h2 class="text-sm font-semibold text-slate-700">Family Structure & Sibling Analytics</h2>
				<KpiRow :items="familyKpis" />
				<div class="grid gap-4 lg:grid-cols-2">
					<StackedBarChart title="Sibling Distribution" :series="siblingSeries" :rows="siblingRows"
						@select="openSliceDrawer" />
					<HistogramBuckets title="Family Size Histogram"
						:buckets="dashboard.family_size_histogram.map((b) => ({ label: b.bucket, count: b.count, sliceKey: b.sliceKey }))"
						@select="openSliceDrawer" />
				</div>
			</section>

			<section class="space-y-3">
				<h2 class="text-sm font-semibold text-slate-700">Guardian Demographics</h2>
				<div class="grid gap-4 lg:grid-cols-2">
					<HorizontalBarTopN title="Guardian Nationality (Top)" :items="dashboard.guardian_nationality"
						@select="openSliceDrawer" />
					<DonutSplit title="Preferred Communication Language" :items="dashboard.guardian_comm_language"
						@select="openSliceDrawer" />
					<HorizontalBarTopN title="Guardian Residence (Country)" :items="dashboard.guardian_residence_country"
						@select="openSliceDrawer" />
					<TagCloudBar title="Guardian Residence (City)" :items="dashboard.guardian_residence_city" :max="12"
						@select="openSliceDrawer" />
					<HorizontalBarTopN title="Guardian Employment Sector" :items="dashboard.guardian_sector"
						@select="openSliceDrawer" />
					<DonutSplit title="Financial Guardian Spread" :items="dashboard.financial_guardian"
						@select="openSliceDrawer" />
				</div>
			</section>
		</section>

		<SideDrawerList :open="sliceDrawerOpen" :title="sliceMeta?.title || 'Drill-down'"
			:entity="sliceMeta?.entity || 'student'" :rows="sliceRows" :loading="sliceResource.loading"
			:on-load-more="sliceResource.loading ? undefined : loadSlice" @close="closeSliceDrawer">
			<template #row="{ row }">
				<div class="flex flex-col">
					<span class="font-medium text-slate-800">{{ row.name || row.title }}</span>
					<span class="text-xs text-slate-500">{{ row.subtitle || row.cohort }}</span>
				</div>
			</template>
		</SideDrawerList>
	</div>
</template>
