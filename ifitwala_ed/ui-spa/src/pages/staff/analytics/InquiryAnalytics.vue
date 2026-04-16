<!-- ifitwala_ed/ui-spa/src/pages/staff/analytics/InquiryAnalytics.vue -->
<template>
	<div class="analytics-shell">
		<header class="page-header">
			<div class="page-header__intro">
				<h1 class="type-h1 text-canopy">Inquiry Analytics</h1>
				<p class="type-meta text-slate-token/80">
					Pipeline volume, response pace, and conversion pressure across inquiry scope.
				</p>
			</div>
			<div class="page-header__actions">
				<DateRangePills
					v-model="filters.date_preset"
					:items="DATE_RANGES"
					@change="handleDatePresetChange"
				/>
				<button
					type="button"
					class="fui-btn-primary rounded-full px-4 py-1.5 text-sm font-medium transition active:scale-95"
					@click="refresh"
				>
					Refresh
				</button>
			</div>
		</header>

		<FiltersBar class="analytics-filters">
			<div class="flex flex-col gap-1">
				<label class="type-label">Academic Year</label>
				<select
					v-model="filters.academic_year"
					class="h-9 rounded-md border px-2 text-sm"
					@change="handleAcademicYearChange"
				>
					<option value="">All Years</option>
					<option v-for="y in academicYears" :key="y" :value="y">{{ y }}</option>
				</select>
			</div>

			<div class="flex flex-col gap-1">
				<label class="type-label">Date Range</label>
				<div class="flex items-center gap-2">
					<input
						type="date"
						v-model="filters.from_date"
						class="h-9 rounded-md border px-2 text-sm"
						@change="handleCustomDateChange"
					/>
					<span class="text-slate-300">-</span>
					<input
						type="date"
						v-model="filters.to_date"
						class="h-9 rounded-md border px-2 text-sm"
						@change="handleCustomDateChange"
					/>
				</div>
			</div>

			<div class="flex flex-col gap-1">
				<label class="type-label">Organization</label>
				<select
					v-model="filters.organization"
					class="h-9 min-w-[160px] max-w-[220px] rounded-md border px-2 text-sm"
				>
					<option value="">All Organizations</option>
					<option v-for="o in allowedOrganizations" :key="o" :value="o">{{ o }}</option>
				</select>
			</div>

			<div class="flex flex-col gap-1">
				<label class="type-label">School</label>
				<select
					v-model="filters.school"
					class="h-9 min-w-[140px] max-w-[200px] rounded-md border px-2 text-sm"
				>
					<option value="">All Permitted</option>
					<option v-for="s in allowedSchools" :key="s" :value="s">{{ s }}</option>
				</select>
			</div>

			<div class="flex flex-col gap-1">
				<label class="type-label">Assignee</label>
				<select
					v-model="filters.assigned_to"
					class="h-9 min-w-[140px] rounded-md border px-2 text-sm"
				>
					<option value="">All Users</option>
					<option v-for="u in users" :key="u.name" :value="u.name">{{ u.full_name }}</option>
				</select>
			</div>

			<div class="flex flex-col gap-1">
				<label class="type-label">Inquiry Type</label>
				<select
					v-model="filters.type_of_inquiry"
					class="h-9 min-w-[140px] rounded-md border px-2 text-sm"
				>
					<option value="">All Types</option>
					<option v-for="t in inquiryTypes" :key="t" :value="t">{{ t }}</option>
				</select>
			</div>

			<div class="flex flex-col gap-1">
				<label class="type-label">Assignment Lane</label>
				<select
					v-model="filters.assignment_lane"
					class="h-9 min-w-[140px] rounded-md border px-2 text-sm"
				>
					<option value="">All Lanes</option>
					<option value="Admission">Admission</option>
					<option value="Staff">Staff</option>
				</select>
			</div>
		</FiltersBar>

		<div v-if="loading" class="py-12 text-center text-slate-500">Loading analytics...</div>

		<template v-else>
			<KpiRow :items="kpiItems" />

			<section class="grid grid-cols-1 gap-6 lg:grid-cols-2">
				<div v-for="lane in laneCards" :key="lane.id" class="flex flex-col gap-4 analytics-card">
					<h3 class="analytics-card__title">{{ lane.title }}</h3>
					<div class="flex flex-wrap gap-3">
						<StatsTile label="Total" :value="lane.counts.total" />
						<StatsTile label="Contacted" :value="lane.counts.contacted" />
						<StatsTile label="Overdue" :value="lane.counts.overdue_first_contact" tone="warning" />
						<StatsTile label="Due Today" :value="lane.counts.due_today" />
						<StatsTile label="Upcoming" :value="lane.counts.upcoming" />
						<StatsTile label="SLA (30d)" :value="lane.sla + '%'" />
					</div>
					<div class="flex gap-6 text-sm">
						<div class="flex flex-col">
							<span class="type-caption">Intake Avg</span>
							<span class="font-medium text-ink">{{ lane.avg.intake_response_hours }}h</span>
						</div>
						<div class="flex flex-col">
							<span class="type-caption">Resolver Avg</span>
							<span class="font-medium text-ink">{{ lane.avg.resolver_response_hours }}h</span>
						</div>
					</div>
				</div>
			</section>

			<div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
				<!-- Pipeline -->
				<HorizontalBarTopN
					title="Pipeline by State"
					:items="pipelineItems"
					class="analytics-card"
				/>

				<!-- Weekly Volume -->
				<section class="analytics-card">
					<h3 class="analytics-card__title">Weekly Volume</h3>
					<AnalyticsChart :option="weeklyChartOption" />
				</section>
			</div>

			<div class="grid grid-cols-1 gap-6 lg:grid-cols-3">
				<HorizontalBarTopN title="Assigned To" :items="assigneeItems" class="analytics-card" />
				<HorizontalBarTopN title="Inquiry Types" :items="typeItems" class="analytics-card" />
				<HorizontalBarTopN
					title="Lane Distribution"
					:items="laneDistributionItems"
					class="analytics-card"
				/>
			</div>

			<!-- Detailed Stats & Trends -->
			<section class="grid grid-cols-1 gap-6 lg:grid-cols-3">
				<!-- SLA & Response Stats -->
				<div class="flex flex-col gap-4 analytics-card">
					<h3 class="analytics-card__title">Performance Metrics</h3>
					<div class="flex flex-wrap gap-3">
						<StatsTile
							label="SLA Compliance (30d)"
							:value="data?.sla?.pct_30d + '%'"
							:tone="slaTone"
						/>
						<StatsTile
							label="First Response (Avg)"
							:value="data?.averages?.overall?.first_contact_hours + 'h'"
						/>
						<StatsTile
							label="From Assign (Avg)"
							:value="data?.averages?.overall?.from_assign_hours + 'h'"
						/>
					</div>

					<h4 class="mt-2 type-overline text-slate-400">Last 30 Days</h4>
					<div class="flex gap-4 text-sm">
						<div class="flex flex-col">
							<span class="type-caption">First Contact</span>
							<span class="font-medium text-ink"
								>{{ data?.averages?.last30d?.first_contact_hours }}h</span
							>
						</div>
						<div class="flex flex-col">
							<span class="type-caption">From Assign</span>
							<span class="font-medium text-ink"
								>{{ data?.averages?.last30d?.from_assign_hours }}h</span
							>
						</div>
					</div>
				</div>

				<!-- Monthly Trends -->
				<div class="col-span-2 flex flex-col analytics-card">
					<h3 class="analytics-card__title mb-4">Monthly Average Response Time (Hours)</h3>
					<AnalyticsChart :option="monthlyChartOption" />
				</div>
			</section>

			<section class="analytics-card">
				<h3 class="analytics-card__title mb-4">Monthly Resolver Average by Lane (Hours)</h3>
				<AnalyticsChart :option="monthlyLaneChartOption" />
			</section>
		</template>
	</div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue';
import {
	getInquiryDashboardData,
	getInquiryOrganizations,
	getInquirySchools,
	getInquiryTypes,
	searchAdmissionUsers,
	searchAcademicYears,
	type DashboardFilters,
} from '@/lib/admission';
import FiltersBar from '@/components/filters/FiltersBar.vue';
import KpiRow from '@/components/analytics/KpiRow.vue';
import StatsTile from '@/components/analytics/StatsTile.vue';
import AnalyticsChart from '@/components/analytics/AnalyticsChart.vue';
import HorizontalBarTopN from '@/components/analytics/HorizontalBarTopN.vue';
import DateRangePills from '@/components/filters/DateRangePills.vue';

// -- State --
const loading = ref(false);
const data = ref<any>(null);

const DATE_RANGES = [
	{ label: 'Last 7 Days', value: '7d' },
	{ label: 'Last 30 Days', value: '30d' },
	{ label: 'Last 90 Days', value: '90d' },
	{ label: 'YTD', value: 'year' },
	{ label: 'All Time', value: 'all' },
] as const;

const filters = ref<DashboardFilters>({
	date_mode: 'preset',
	date_preset: '90d',
	academic_year: '',
	from_date: '',
	to_date: '',
	assigned_to: '',
	type_of_inquiry: '',
	assignment_lane: '',
	sla_status: '',
	organization: '',
	school: '',
});

// Options
const inquiryTypes = ref<string[]>([]);
const users = ref<{ name: string; full_name: string }[]>([]);
const academicYears = ref<string[]>([]);
const allowedOrganizations = ref<string[]>([]);
const allowedSchools = ref<string[]>([]);

// -- Actions --
async function loadOptions() {
	const [types, userList, years, organizations, schools] = await Promise.all([
		getInquiryTypes(),
		searchAdmissionUsers(''),
		searchAcademicYears(''),
		getInquiryOrganizations(),
		getInquirySchools(),
	]);
	inquiryTypes.value = types || [];
	if (userList) users.value = userList.map((u: any) => ({ name: u[0], full_name: u[1] }));
	if (years) academicYears.value = years.map((y: any) => y[0]);
	allowedOrganizations.value = organizations || [];
	allowedSchools.value = schools || [];
}

async function refresh() {
	loading.value = true;
	try {
		const res = await getInquiryDashboardData(filters.value);
		data.value = res;
	} catch (e) {
		console.error(e);
	} finally {
		loading.value = false;
	}
}

function handleDatePresetChange(value: string) {
	if (!value) return;
	filters.value.date_mode = 'preset';
	filters.value.date_preset = value;
	filters.value.from_date = '';
	filters.value.to_date = '';
	filters.value.academic_year = '';
}

function handleCustomDateChange() {
	filters.value.date_mode = 'custom';
	filters.value.date_preset = '';
	filters.value.academic_year = '';
}

function handleAcademicYearChange() {
	filters.value.date_mode = 'academic_year';
	filters.value.date_preset = '';
	filters.value.from_date = '';
	filters.value.to_date = '';
}

watch(
	filters,
	() => {
		// simple debounce could be added here
		refresh();
	},
	{ deep: true }
);

onMounted(async () => {
	await loadOptions();
	refresh();
});

// -- Computed View Models --

const kpiItems = computed(() => {
	if (!data.value) return [];
	const c = data.value.counts;
	return [
		{ id: 'total', label: 'Total Inquiries', value: c.total },
		{ id: 'contacted', label: 'Contacted', value: c.contacted },
		{
			id: 'overdue',
			label: 'Overdue First Contact',
			value: c.overdue_first_contact,
			hint: 'Action Needed',
		},
		{ id: 'due_today', label: 'Due Today', value: c.due_today },
		{
			id: 'upcoming',
			label: 'Upcoming',
			value: c.upcoming,
			hint: `Next ${data.value.config?.upcoming_horizon_days || 7} Days`,
		},
	];
});

const pipelineItems = computed(() => {
	const total = data.value?.counts?.total || 0;
	return (data.value?.pipeline_by_state || []).map((d: any) => ({
		label: d.label,
		count: d.value,
		pct: total ? Math.round((d.value / total) * 100) : 0,
	}));
});

const assigneeItems = computed(() => {
	if (!data.value?.assignee_distribution) return [];
	return data.value.assignee_distribution.map((d: any) => ({
		label: d.label, // This is the ID/Email usually, ideally we map it to full name if possible, but backend sends ID
		count: d.value,
	}));
});

const typeItems = computed(() => {
	if (!data.value?.type_distribution) return [];
	return data.value.type_distribution.map((d: any) => ({
		label: d.label,
		count: d.value,
		pct: data.value.counts.total ? Math.round((d.value / data.value.counts.total) * 100) : 0,
	}));
});

const laneDistributionItems = computed(() => {
	if (!data.value?.lane_distribution) return [];
	const total = data.value?.counts?.total || 0;
	return data.value.lane_distribution.map((d: any) => ({
		label: d.label || 'Admission',
		count: d.value,
		pct: total ? Math.round((d.value / total) * 100) : 0,
	}));
});

const laneCards = computed(() => {
	const breakdown = data.value?.lane_breakdown || {};
	const admission = breakdown.Admission || {};
	const staff = breakdown.Staff || {};
	return [
		{
			id: 'lane-admission',
			title: 'Admission Lane',
			counts: admission.counts || {
				total: 0,
				contacted: 0,
				overdue_first_contact: 0,
				due_today: 0,
				upcoming: 0,
			},
			avg: admission.averages || { intake_response_hours: 0, resolver_response_hours: 0 },
			sla: admission.sla?.pct_30d || 0,
		},
		{
			id: 'lane-staff',
			title: 'Staff Lane',
			counts: staff.counts || {
				total: 0,
				contacted: 0,
				overdue_first_contact: 0,
				due_today: 0,
				upcoming: 0,
			},
			avg: staff.averages || { intake_response_hours: 0, resolver_response_hours: 0 },
			sla: staff.sla?.pct_30d || 0,
		},
	];
});

const slaTone = computed(() => {
	const pct = data.value?.sla?.pct_30d || 0;
	if (pct >= 90) return 'success';
	if (pct >= 70) return 'info';
	return 'warning';
});

// -- Charts --

const weeklyChartOption = computed(() => {
	const s = data.value?.weekly_volume_series;
	if (!s) return {};
	return {
		tooltip: { trigger: 'axis' },
		grid: { left: 40, right: 20, top: 20, bottom: 20, containLabel: true },
		xAxis: { type: 'category', data: s.labels, axisLabel: { color: '#64748b' } },
		yAxis: { type: 'value', splitLine: { lineStyle: { type: 'dashed' } } },
		series: [
			{
				data: s.values,
				type: 'line',
				smooth: true,
				areaStyle: { opacity: 0.1 },
				itemStyle: { color: '#3b82f6' },
			},
		],
	};
});

const monthlyChartOption = computed(() => {
	const s = data.value?.monthly_avg_series;
	if (!s) return {};
	return {
		tooltip: { trigger: 'axis' },
		legend: { bottom: 0 },
		grid: { left: 40, right: 20, top: 20, bottom: 40, containLabel: true },
		xAxis: { type: 'category', data: s.labels, axisLabel: { color: '#64748b' } },
		yAxis: { type: 'value', splitLine: { lineStyle: { type: 'dashed' } }, name: 'Hours' },
		series: [
			{
				name: 'First Contact',
				data: s.first_contact,
				type: 'bar',
				itemStyle: { color: '#8b5cf6' },
			},
			{
				name: 'From Assign',
				data: s.from_assign,
				type: 'bar',
				itemStyle: { color: '#10b981' },
			},
		],
	};
});

const monthlyLaneChartOption = computed(() => {
	const s = data.value?.monthly_lane_series;
	if (!s) return {};
	return {
		tooltip: { trigger: 'axis' },
		legend: { bottom: 0 },
		grid: { left: 40, right: 20, top: 20, bottom: 40, containLabel: true },
		xAxis: { type: 'category', data: s.labels, axisLabel: { color: '#64748b' } },
		yAxis: { type: 'value', splitLine: { lineStyle: { type: 'dashed' } }, name: 'Hours' },
		series: [
			{
				name: 'Admission Lane',
				data: s.admission,
				type: 'line',
				smooth: true,
				itemStyle: { color: '#2563eb' },
			},
			{
				name: 'Staff Lane',
				data: s.staff,
				type: 'line',
				smooth: true,
				itemStyle: { color: '#ea580c' },
			},
		],
	};
});
</script>
