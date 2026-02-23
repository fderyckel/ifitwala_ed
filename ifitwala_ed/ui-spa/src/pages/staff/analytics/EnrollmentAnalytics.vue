<!-- ifitwala_ed/ui-spa/src/pages/staff/analytics/EnrollmentAnalytics.vue -->
<template>
	<div class="analytics-shell">
		<header class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
			<div>
				<h1 class="type-h2 text-canopy">Enrollment</h1>
				<p class="text-xs text-slate-500">{{ scopeLabel }}</p>
			</div>
		</header>

		<FiltersBar class="analytics-filters">
			<div class="flex flex-col gap-1">
				<label class="type-label">Organization</label>
				<select
					v-model="filters.organization"
					class="h-9 min-w-[180px] rounded-md border px-2 text-sm"
					@change="handleOrganizationChange"
				>
					<option v-for="org in organizationOptions" :key="org.value" :value="org.value">
						{{ org.label }}
					</option>
				</select>
			</div>

			<div class="flex flex-col gap-1">
				<label class="type-label">School</label>
				<select
					v-model="filters.school"
					class="h-9 min-w-[170px] rounded-md border px-2 text-sm"
					@change="handleSchoolChange"
				>
					<option v-for="school in schoolOptions" :key="school.value" :value="school.value">
						{{ school.label }}
					</option>
				</select>
			</div>

			<div class="flex flex-col gap-1">
				<label class="type-label">Academic Year Range</label>
				<div class="flex flex-wrap items-center gap-2">
					<select
						v-model="yearRange.start"
						class="h-9 min-w-[160px] rounded-md border px-2 text-sm"
					>
						<option :value="null">From</option>
						<option v-for="year in yearRangeOptions" :key="year.value" :value="year.value">
							{{ formatAcademicYearLabel(year) }}
						</option>
					</select>
					<span class="text-slate-300">to</span>
					<select v-model="yearRange.end" class="h-9 min-w-[160px] rounded-md border px-2 text-sm">
						<option :value="null">To</option>
						<option v-for="year in yearRangeOptions" :key="year.value" :value="year.value">
							{{ formatAcademicYearLabel(year) }}
						</option>
					</select>
				</div>
				<span v-if="yearRangeMessage" class="text-[0.65rem] text-amber-600">{{
					yearRangeMessage
				}}</span>
				<span v-else class="text-[0.65rem] text-slate-400">Pick 2-5 consecutive years.</span>
			</div>

			<div class="flex flex-col gap-1">
				<label class="type-label">Compare Dimension</label>
				<select
					v-model="filters.compare_dimension"
					class="h-9 min-w-[140px] rounded-md border px-2 text-sm"
				>
					<option value="school">School</option>
					<option value="program">Program</option>
				</select>
			</div>

			<div class="flex flex-col gap-1">
				<label class="type-label">Chart Mode</label>
				<select
					v-model="filters.chart_mode"
					class="h-9 min-w-[130px] rounded-md border px-2 text-sm"
				>
					<option v-for="mode in chartModeOptions" :key="mode.value" :value="mode.value">
						{{ mode.label }}
					</option>
				</select>
			</div>

			<div class="flex flex-col gap-1">
				<label class="type-label">As-of Date</label>
				<input
					type="date"
					v-model="filters.as_of_date"
					class="h-9 min-w-[150px] rounded-md border px-2 text-sm"
					:disabled="filters.chart_mode !== 'snapshot'"
				/>
			</div>
		</FiltersBar>

		<div v-if="accessDenied" class="rounded-md border border-amber-200 bg-amber-50 px-4 py-3">
			<h2 class="text-sm font-semibold text-amber-900">Access restricted</h2>
			<p class="mt-1 text-xs text-amber-800">You do not have access to Enrollment Analytics.</p>
		</div>

		<div v-else>
			<div v-if="dashboardResource.loading" class="py-10 text-center text-sm text-slate-500">
				Loading enrollment analytics...
			</div>

			<div v-else class="space-y-6">
				<KpiRow :items="kpiItems" clickable @select="handleKpiSelect" />

				<StackedBarChart
					:title="stackedChartTitle"
					:series="stackedChart.series"
					:rows="stackedChart.rows"
					@select="handleSliceSelect"
				/>

				<div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
					<HorizontalBarTopN
						title="Top Cohorts (Active Enrollments)"
						:items="topnCohorts"
						@select="handleSliceSelect"
					/>
					<HorizontalBarTopN
						title="Top Programs (Active Enrollments)"
						:items="topnPrograms"
						@select="handleSliceSelect"
					/>
				</div>
			</div>
		</div>

		<SideDrawerList
			:open="drawerOpen"
			:title="drawerTitle"
			entity-label="Enrollments"
			:rows="drawerRows"
			:loading="drilldownResource.loading"
			:on-load-more="canLoadMore ? loadMore : undefined"
			@close="closeDrawer"
		>
			<template #row="{ row }">
				<div class="flex flex-col">
					<span class="font-medium text-slate-800">{{ row.student_name }}</span>
					<span class="text-xs text-slate-500">{{ formatRowSubtitle(row) }}</span>
				</div>
			</template>
		</SideDrawerList>
	</div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue';
import { createResource } from 'frappe-ui';

import FiltersBar from '@/components/filters/FiltersBar.vue';
import KpiRow from '@/components/analytics/KpiRow.vue';
import StackedBarChart from '@/components/analytics/StackedBarChart.vue';
import HorizontalBarTopN from '@/components/analytics/HorizontalBarTopN.vue';
import SideDrawerList from '@/components/analytics/SideDrawerList.vue';

type CompareDimension = 'school' | 'program';
type ChartMode = 'snapshot' | 'trend';

type KpiResponse = {
	active: number;
	new_in_period: number;
	drops_in_period: number;
	net_change: number;
	archived: number;
};

type StackedChart = {
	series: { key: string; label: string; color?: string }[];
	rows: { category: string; values: Record<string, number>; sliceKeys?: Record<string, string> }[];
};

type TopNItem = { label: string; count: number; pct?: number; color?: string; sliceKey?: string };

type AcademicYearOption = {
	value: string;
	label: string;
	start?: string | null;
	end?: string | null;
	school?: string | null;
	schoolLabel?: string | null;
};

type DashboardResponse = {
	kpis: KpiResponse;
	stacked_chart: StackedChart;
	topn: { cohorts: TopNItem[]; programs: TopNItem[] };
	meta?: {
		filters_echo?: Record<string, any>;
		options?: {
			organizations?: any[];
			schools?: any[];
			academic_years?: any[];
		};
		defaults?: Record<string, any>;
		trend_enabled?: boolean;
	};
};

type SlicePayload = {
	type: 'kpi' | 'stack' | 'topn';
	dimension?: string;
	key?: string;
	bucket?: string;
};

const today = new Date().toISOString().slice(0, 10);
const trendEnabled = false;

const filters = reactive({
	organization: null as string | null,
	school: null as string | null,
	academic_years: [] as string[],
	compare_dimension: 'school' as CompareDimension,
	chart_mode: 'snapshot' as ChartMode,
	as_of_date: today,
	period_from: null as string | null,
	period_to: null as string | null,
	program: null as string | null,
	cohort: null as string | null,
	program_offering: null as string | null,
	top_n: 8,
});

const yearRange = reactive({
	start: null as string | null,
	end: null as string | null,
});

const yearRangeMessage = ref('');
const yearRangeValid = ref(false);
const yearRangeUpdating = ref(false);
const yearRangeInProgress = computed(() => Boolean(yearRange.start || yearRange.end));

const accessDenied = ref(false);
const initialized = ref(false);
const syncing = ref(false);
const lastPayloadKey = ref<string | null>(null);
const pendingPayloadKey = ref<string | null>(null);

const dashboardResource = createResource({
	url: 'ifitwala_ed.api.enrollment_analytics.get_enrollment_dashboard',
	method: 'POST',
	auto: false,
});

const drilldownResource = createResource({
	url: 'ifitwala_ed.api.enrollment_analytics.get_enrollment_drilldown',
	method: 'POST',
	auto: false,
});

const emptyDashboard: DashboardResponse = {
	kpis: {
		active: 0,
		new_in_period: 0,
		drops_in_period: 0,
		net_change: 0,
		archived: 0,
	},
	stacked_chart: { series: [], rows: [] },
	topn: { cohorts: [], programs: [] },
	meta: { options: { organizations: [], schools: [], academic_years: [] } },
};

const dashboard = computed<DashboardResponse>(() => {
	const raw = dashboardResource.data as any;
	if (!raw) return emptyDashboard;
	return (raw.message as DashboardResponse) || (raw as DashboardResponse) || emptyDashboard;
});

const options = computed(() => dashboard.value.meta?.options || {});

const organizationOptions = computed(() => {
	const orgs = options.value.organizations || [];
	return orgs.map((org: any) => ({
		value: org.name,
		label: (org.abbr ? `${org.abbr} — ` : '') + (org.organization_name || org.name),
	}));
});

const schoolOptions = computed(() => {
	const schools = options.value.schools || [];
	const filtered = filters.organization
		? schools.filter((s: any) => s.organization === filters.organization)
		: schools;
	return filtered.map((s: any) => ({
		value: s.name,
		label: (s.abbr ? `${s.abbr} — ` : '') + (s.school_name || s.name),
	}));
});

const academicYearOptions = computed(() => {
	const years = options.value.academic_years || [];
	return years.map((y: any) => ({
		value: y.name,
		label: y.label || y.name,
		start: y.year_start_date,
		end: y.year_end_date,
		school: y.school || null,
		schoolLabel: y.school_label || y.school_name || y.school || null,
	}));
});

const yearRangeSchool = computed(() => {
	const start = findAcademicYear(yearRange.start);
	if (start?.school) return start.school;
	const end = findAcademicYear(yearRange.end);
	if (end?.school) return end.school;
	return null;
});

const yearRangeOptions = computed<AcademicYearOption[]>(() => {
	const explicitSchool = filters.school;
	const scopedSchool =
		explicitSchool && academicYearOptions.value.some(y => y.school === explicitSchool)
			? explicitSchool
			: null;
	const school = yearRangeSchool.value || scopedSchool;
	const filtered = school
		? academicYearOptions.value.filter(y => y.school === school)
		: academicYearOptions.value;
	return [...filtered].sort((a, b) => yearSortKey(a) - yearSortKey(b));
});

const showYearSchoolLabel = computed(() => {
	const schools = new Set(academicYearOptions.value.map(y => y.school).filter(s => s));
	return schools.size > 1;
});

const chartModeOptions = computed(() =>
	trendEnabled
		? [
				{ value: 'snapshot', label: 'Snapshot' },
				{ value: 'trend', label: 'Trend' },
			]
		: [{ value: 'snapshot', label: 'Snapshot' }]
);

const scopeLabel = computed(() => {
	const orgLabel =
		organizationOptions.value.find(o => o.value === filters.organization)?.label ||
		filters.organization ||
		'Organization';
	const schoolLabel =
		schoolOptions.value.find(s => s.value === filters.school)?.label || filters.school || 'School';
	const yearsLabel = yearRangeLabel.value;
	return `${orgLabel} • ${schoolLabel} • ${yearsLabel}`;
});

const yearRangeLabel = computed(() => {
	const start = findAcademicYear(yearRange.start);
	const end = findAcademicYear(yearRange.end);
	if (start && end) {
		return `${start.label} to ${end.label}`;
	}
	if (yearRange.start || yearRange.end) {
		return 'Academic Years';
	}
	if (filters.academic_years.length) {
		return filters.academic_years.join(', ');
	}
	return 'Academic Years';
});

const kpiItems = computed(() => [
	{ id: 'active', label: 'Active Enrollments', value: dashboard.value.kpis.active },
	{ id: 'new', label: 'New Enrollments (period)', value: dashboard.value.kpis.new_in_period },
	{ id: 'drops', label: 'Course Drops (period)', value: dashboard.value.kpis.drops_in_period },
	{ id: 'net_change', label: 'Net Change (period)', value: dashboard.value.kpis.net_change },
	{ id: 'archived', label: 'Archived', value: dashboard.value.kpis.archived },
]);

const stackedChart = computed(() => dashboard.value.stacked_chart || { series: [], rows: [] });

const stackedChartTitle = computed(() => {
	const compare = filters.compare_dimension === 'program' ? 'Program' : 'School';
	if (filters.chart_mode === 'trend') {
		return `Enrollment Trend by ${compare}`;
	}
	return `Enrollment Snapshot by ${compare}`;
});

const topnCohorts = computed(() => dashboard.value.topn?.cohorts || []);
const topnPrograms = computed(() => dashboard.value.topn?.programs || []);

const drawerOpen = ref(false);
const drawerRows = ref<any[]>([]);
const drawerTotal = ref(0);
const drawerStart = ref(0);
const drawerPageLength = 50;
const activeSlice = ref<SlicePayload | null>(null);

const drawerTitle = computed(() => {
	if (!activeSlice.value) return 'Drill-down';
	const slice = activeSlice.value;
	if (slice.type === 'kpi') {
		const label = kpiItems.value.find(item => item.id === slice.key)?.label;
		return label || 'Drill-down';
	}
	if (slice.type === 'topn') {
		const prefix = slice.dimension === 'program' ? 'Program' : 'Cohort';
		return `${prefix}: ${slice.key || ''}`.trim();
	}
	if (slice.type === 'stack') {
		const bucket = slice.bucket ? ` • ${slice.bucket}` : '';
		const prefix = slice.dimension === 'program' ? 'Program' : 'School';
		return `${prefix}: ${slice.key || ''}${bucket}`.trim();
	}
	return 'Drill-down';
});

const canLoadMore = computed(
	() => drawerRows.value.length < drawerTotal.value && !drilldownResource.loading
);

function formatRowSubtitle(row: any) {
	const parts = [
		row.cohort,
		row.program_label || row.program,
		row.school_label || row.school,
		row.enrollment_date,
	].filter(Boolean);
	return parts.join(' • ');
}

function formatAcademicYearLabel(option: AcademicYearOption) {
	if (!showYearSchoolLabel.value) return option.label;
	const schoolLabel = option.schoolLabel || option.school;
	return schoolLabel ? `${option.label} - ${schoolLabel}` : option.label;
}

function yearSortKey(option: AcademicYearOption) {
	if (option.start) {
		const ts = new Date(option.start).getTime();
		if (!Number.isNaN(ts)) return ts;
	}
	return 0;
}

function findAcademicYear(value: string | null) {
	if (!value) return null;
	return academicYearOptions.value.find(y => y.value === value) || null;
}

function applyYearRange() {
	if (yearRangeUpdating.value) return;
	yearRangeMessage.value = '';
	yearRangeValid.value = false;

	const start = yearRange.start || null;
	const end = yearRange.end || null;

	if (!start && !end) {
		if (filters.academic_years.length) {
			filters.academic_years = [];
		}
		return;
	}

	if (!start || !end) {
		yearRangeMessage.value = 'Select both a start and end year.';
		return;
	}

	const startOption = findAcademicYear(start);
	const endOption = findAcademicYear(end);
	if (startOption?.school && endOption?.school && startOption.school !== endOption.school) {
		yearRangeMessage.value = 'Pick years from the same school.';
		yearRangeUpdating.value = true;
		yearRange.end = null;
		yearRangeUpdating.value = false;
		return;
	}

	const options = yearRangeOptions.value;
	const startIndex = options.findIndex(y => y.value === start);
	const endIndex = options.findIndex(y => y.value === end);
	if (startIndex === -1 || endIndex === -1) {
		yearRangeMessage.value = 'Selected years are out of scope.';
		return;
	}

	if (startIndex > endIndex) {
		yearRangeUpdating.value = true;
		[yearRange.start, yearRange.end] = [yearRange.end, yearRange.start];
		yearRangeUpdating.value = false;
		applyYearRange();
		return;
	}

	const range = options.slice(startIndex, endIndex + 1);
	if (range.length < 2) {
		yearRangeMessage.value = 'Select at least two consecutive years.';
		return;
	}

	if (range.length > 5) {
		yearRangeMessage.value = 'Select no more than five consecutive years.';
		return;
	}

	const rangeValues = range.map(y => y.value);
	if (!arraysEqual(rangeValues, filters.academic_years)) {
		filters.academic_years = rangeValues;
	}
	yearRangeValid.value = true;
}

function arraysEqual(a: string[], b: string[]) {
	if (a.length !== b.length) return false;
	for (let i = 0; i < a.length; i += 1) {
		if (a[i] !== b[i]) return false;
	}
	return true;
}
function parseSliceKey(sliceKey: string): SlicePayload | null {
	if (!sliceKey) return null;
	try {
		const parsed = JSON.parse(sliceKey);
		if (parsed && typeof parsed === 'object') return parsed as SlicePayload;
	} catch (error) {
		return null;
	}
	return null;
}

function handleSliceSelect(sliceKey: string) {
	const slice = parseSliceKey(sliceKey);
	if (!slice) return;
	openDrawer(slice);
}

function handleKpiSelect(item: any) {
	openDrawer({ type: 'kpi', key: item.id });
}

function openDrawer(slice: SlicePayload) {
	activeSlice.value = slice;
	drawerOpen.value = true;
	loadDrilldown(true);
}

function closeDrawer() {
	drawerOpen.value = false;
	activeSlice.value = null;
	drawerRows.value = [];
	drawerStart.value = 0;
	drawerTotal.value = 0;
}

async function loadDrilldown(reset = false) {
	if (!activeSlice.value) return;
	if (reset) {
		drawerRows.value = [];
		drawerStart.value = 0;
		drawerTotal.value = 0;
	}
	const payload = {
		...buildPayload(),
		slice: activeSlice.value,
		start: drawerStart.value,
		page_length: drawerPageLength,
	};
	await drilldownResource.submit(payload);
	const raw = drilldownResource.data as any;
	const data = raw?.message || raw || {};
	const rows = Array.isArray(data.rows) ? data.rows : [];
	const total = Number(data.total_count || 0);
	drawerRows.value = reset ? rows : [...drawerRows.value, ...rows];
	drawerStart.value = drawerRows.value.length;
	drawerTotal.value = total;
}

function loadMore() {
	if (!canLoadMore.value) return;
	loadDrilldown(false);
}

function buildPayload() {
	return {
		organization: filters.organization,
		school: filters.school,
		academic_years: filters.academic_years,
		compare_dimension: filters.compare_dimension,
		chart_mode: filters.chart_mode,
		as_of_date: filters.as_of_date || null,
		period_from: filters.period_from || null,
		period_to: filters.period_to || null,
		program: filters.program,
		cohort: filters.cohort,
		program_offering: filters.program_offering,
		top_n: filters.top_n,
	};
}

let debounceTimer: number | undefined;
function debounceLoad() {
	window.clearTimeout(debounceTimer);
	debounceTimer = window.setTimeout(() => {
		loadDashboard();
	}, 250);
}

async function applyDefaults(meta?: DashboardResponse['meta']) {
	if (!meta?.defaults) return;
	syncing.value = true;
	const defaults = meta.defaults;

	const orgValues = new Set(organizationOptions.value.map(o => o.value));
	if ((!filters.organization || !orgValues.has(filters.organization)) && defaults.organization) {
		filters.organization = defaults.organization;
	}

	const schoolValues = new Set(schoolOptions.value.map(s => s.value));
	if ((!filters.school || !schoolValues.has(filters.school)) && defaults.school) {
		filters.school = defaults.school;
	}

	if (
		!yearRangeInProgress.value &&
		Array.isArray(defaults.academic_years) &&
		defaults.academic_years.length
	) {
		const range = resolveYearRange(defaults.academic_years);
		if (range.start || range.end) {
			yearRange.start = range.start;
			yearRange.end = range.end;
			applyYearRange();
		}
	}

	if (defaults.compare_dimension && ['school', 'program'].includes(defaults.compare_dimension)) {
		filters.compare_dimension = defaults.compare_dimension;
	}

	if (defaults.chart_mode && ['snapshot', 'trend'].includes(defaults.chart_mode)) {
		filters.chart_mode = defaults.chart_mode;
	}

	if (!trendEnabled && filters.chart_mode === 'trend') {
		filters.chart_mode = 'snapshot';
	}

	if (defaults.as_of_date) {
		filters.as_of_date = defaults.as_of_date;
	}

	if (defaults.top_n) {
		filters.top_n = defaults.top_n;
	}

	await nextTick();
	syncing.value = false;
}

async function loadDashboard() {
	const payload = buildPayload();
	const payloadKey = JSON.stringify(payload);
	if (dashboardResource.loading) {
		pendingPayloadKey.value = payloadKey;
		return;
	}
	if (lastPayloadKey.value === payloadKey && dashboardResource.data) {
		return;
	}
	lastPayloadKey.value = payloadKey;

	try {
		accessDenied.value = false;
		await dashboardResource.submit(payload);
		await applyDefaults(dashboard.value.meta);
		if (!initialized.value) initialized.value = true;
	} catch (error) {
		accessDenied.value = true;
	} finally {
		if (pendingPayloadKey.value && pendingPayloadKey.value !== lastPayloadKey.value) {
			const nextKey = pendingPayloadKey.value;
			pendingPayloadKey.value = null;
			if (nextKey !== lastPayloadKey.value) {
				loadDashboard();
			}
		} else {
			pendingPayloadKey.value = null;
		}
	}
}

function handleOrganizationChange() {
	if (syncing.value) return;
	filters.school = null;
	filters.academic_years = [];
	yearRange.start = null;
	yearRange.end = null;
	yearRangeMessage.value = '';
}

function handleSchoolChange() {
	if (syncing.value) return;
	filters.academic_years = [];
	yearRange.start = null;
	yearRange.end = null;
	yearRangeMessage.value = '';
}

function resolveYearRange(years: string[]) {
	const options = academicYearOptions.value.filter(y => years.includes(y.value));
	if (!options.length) return { start: null, end: null };
	const sorted = [...options].sort((a, b) => yearSortKey(a) - yearSortKey(b));
	return {
		start: sorted[0]?.value || null,
		end: sorted[sorted.length - 1]?.value || null,
	};
}

watch(
	filters,
	() => {
		if (!initialized.value || syncing.value) return;
		closeDrawer();
		if (yearRangeInProgress.value && !yearRangeValid.value) return;
		debounceLoad();
	},
	{ deep: true }
);

watch(
	[() => yearRange.start, () => yearRange.end],
	() => {
		if (syncing.value) return;
		closeDrawer();
		applyYearRange();
	},
	{ deep: true }
);

watch(
	() => filters.chart_mode,
	mode => {
		if (!trendEnabled && mode === 'trend') {
			filters.chart_mode = 'snapshot';
		}
	}
);

onMounted(() => {
	loadDashboard();
});
</script>
