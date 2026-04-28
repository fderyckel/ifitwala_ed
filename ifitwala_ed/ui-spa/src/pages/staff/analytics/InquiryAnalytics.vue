<!-- ifitwala_ed/ui-spa/src/pages/staff/analytics/InquiryAnalytics.vue -->
<template>
	<div class="analytics-shell">
		<header class="page-header">
			<div class="page-header__intro">
				<h1 class="type-h1 text-canopy">Zero Lost Lead</h1>
				<p class="type-meta text-slate-token/80">
					Operational inquiry queues first; pipeline and response analytics below.
				</p>
			</div>
			<div class="page-header__actions">
				<DateRangePills
					v-model="filters.date_preset"
					:items="DATE_RANGES"
					@change="handleDatePresetChange"
				/>
				<button type="button" class="if-button if-button--quiet" @click="refresh">Refresh</button>
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
				<label class="type-label">Source</label>
				<select v-model="filters.source" class="h-9 min-w-[140px] rounded-md border px-2 text-sm">
					<option value="">All Sources</option>
					<option v-for="s in inquirySources" :key="s" :value="s">{{ s }}</option>
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

		<div v-if="loading" class="py-12 text-center text-slate-500">Loading inquiry queues...</div>
		<div v-else-if="error" class="analytics-card border-red-200 bg-red-50 text-red-700">
			{{ error }}
		</div>

		<template v-else>
			<section class="analytics-card">
				<div class="mb-4 flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
					<div>
						<h2 class="analytics-card__title">Operational Views</h2>
						<p class="type-meta text-slate-token/70">
							All-time queues within the selected organization, school, assignee, type, source, and
							lane.
						</p>
					</div>
					<div class="type-meta text-slate-token/70">
						{{ totalOperationalCount }} queue match{{ totalOperationalCount === 1 ? '' : 'es' }}
					</div>
				</div>

				<div class="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
					<button
						v-for="view in commandViews"
						:key="view.id"
						type="button"
						class="rounded-md border p-4 text-left transition"
						:class="viewCardClass(view)"
						@click="setActiveView(view.id)"
					>
						<div class="flex items-start justify-between gap-3">
							<span class="type-label text-ink">{{ view.title }}</span>
							<span
								class="rounded-full px-2 py-0.5 text-xs font-semibold"
								:class="viewCountClass(view)"
							>
								{{ view.count }}
							</span>
						</div>
						<div class="mt-3 type-caption text-slate-token/70">{{ view.next_action }}</div>
					</button>
				</div>
			</section>

			<section class="analytics-card">
				<div class="mb-4 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
					<div>
						<h2 class="analytics-card__title">
							{{ activeCommandView?.title || 'Selected Queue' }}
						</h2>
						<p class="type-meta text-slate-token/70">
							{{ commandPagination.total }} matching
							{{ commandPagination.total === 1 ? 'inquiry' : 'inquiries' }}
						</p>
					</div>
					<div class="flex items-center gap-2">
						<button
							type="button"
							class="if-button if-button--quiet"
							:disabled="commandPagination.start <= 0"
							@click="previousQueuePage"
						>
							Previous
						</button>
						<button
							type="button"
							class="if-button if-button--quiet"
							:disabled="!commandPagination.has_next"
							@click="nextQueuePage"
						>
							Next
						</button>
					</div>
				</div>

				<div v-if="!leadRows.length" class="analytics-empty">
					{{
						hasAnyOperationalLeads
							? 'No inquiries in this queue.'
							: 'No invisible lead conditions found.'
					}}
				</div>
				<div v-else class="overflow-x-auto">
					<table class="min-w-full divide-y divide-slate-200 text-sm">
						<thead>
							<tr class="text-left type-caption text-slate-token/70">
								<th class="py-2 pr-4 font-medium">Lead</th>
								<th class="py-2 pr-4 font-medium">State</th>
								<th class="py-2 pr-4 font-medium">Owner</th>
								<th class="py-2 pr-4 font-medium">Due</th>
								<th class="py-2 pr-4 font-medium">Context</th>
								<th class="py-2 pr-4 font-medium">Next Action</th>
							</tr>
						</thead>
						<tbody class="divide-y divide-slate-100">
							<tr v-for="row in leadRows" :key="row.name">
								<td class="py-3 pr-4 align-top">
									<div class="font-medium text-ink">{{ row.lead_title }}</div>
									<div class="type-caption text-slate-token/70">{{ row.name }}</div>
									<div
										class="mt-1 flex flex-wrap gap-x-3 gap-y-1 type-caption text-slate-token/70"
									>
										<a v-if="row.email" :href="`mailto:${row.email}`">{{ row.email }}</a>
										<a v-if="row.phone_number" :href="`tel:${row.phone_number}`">{{
											row.phone_number
										}}</a>
									</div>
								</td>
								<td class="py-3 pr-4 align-top">
									<div class="font-medium text-ink">{{ row.workflow_state }}</div>
									<div class="type-caption text-slate-token/70">
										{{ row.sla_status || 'No SLA status' }}
									</div>
									<div
										v-if="row.age_hours !== null && row.age_hours !== undefined"
										class="type-caption text-slate-token/70"
									>
										{{ formatAge(row.age_hours) }}
									</div>
								</td>
								<td class="py-3 pr-4 align-top">
									<div class="font-medium text-ink">{{ row.assigned_to || 'Unassigned' }}</div>
									<div class="type-caption text-slate-token/70">
										{{ row.assignment_lane || 'Admission' }}
									</div>
								</td>
								<td class="py-3 pr-4 align-top">
									<div class="font-medium text-ink">
										{{ formatDate(row.first_contact_due_on) }}
									</div>
									<div class="type-caption text-slate-token/70">
										Submitted {{ formatDateTime(row.submitted_at) }}
									</div>
									<div v-if="row.followup_due_on" class="type-caption text-slate-token/70">
										Follow-up {{ formatDate(row.followup_due_on) }}
									</div>
								</td>
								<td class="py-3 pr-4 align-top">
									<div class="font-medium text-ink">
										{{ row.school || row.organization || 'No scope set' }}
									</div>
									<div class="type-caption text-slate-token/70">
										{{
											[row.type_of_inquiry, row.source].filter(Boolean).join(' / ') ||
											'No type or source'
										}}
									</div>
									<div v-if="row.student_applicant" class="type-caption text-slate-token/70">
										Applicant {{ row.student_applicant_status || 'Linked' }}
									</div>
								</td>
								<td class="py-3 pr-4 align-top">
									<a
										v-if="row.next_action?.target_url"
										class="if-button if-button--secondary inline-flex"
										:href="row.next_action.target_url"
										target="_blank"
										rel="noopener noreferrer"
									>
										{{ row.next_action.label }}
									</a>
									<div
										v-if="row.next_action_note"
										class="mt-2 max-w-xs type-caption text-slate-token/70"
									>
										{{ row.next_action_note }}
									</div>
								</td>
							</tr>
						</tbody>
					</table>
				</div>
			</section>

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

			<div class="grid grid-cols-1 gap-6 lg:grid-cols-4">
				<HorizontalBarTopN title="Assigned To" :items="assigneeItems" class="analytics-card" />
				<HorizontalBarTopN title="Inquiry Types" :items="typeItems" class="analytics-card" />
				<HorizontalBarTopN title="Inquiry Sources" :items="sourceItems" class="analytics-card" />
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
	getZeroLostLeadContext,
	getInquiryOrganizations,
	getInquirySchools,
	getInquirySources,
	getInquiryTypes,
	searchAdmissionUsers,
	searchAcademicYears,
	type DashboardFilters,
} from '@/lib/admission';
import type {
	ZeroLostLeadRow,
	ZeroLostLeadView,
} from '@/types/contracts/inquiry/zero_lost_lead_context';
import FiltersBar from '@/components/filters/FiltersBar.vue';
import KpiRow from '@/components/analytics/KpiRow.vue';
import StatsTile from '@/components/analytics/StatsTile.vue';
import AnalyticsChart from '@/components/analytics/AnalyticsChart.vue';
import HorizontalBarTopN from '@/components/analytics/HorizontalBarTopN.vue';
import DateRangePills from '@/components/filters/DateRangePills.vue';

// -- State --
const loading = ref(false);
const data = ref<any>(null);
const error = ref('');
const commandCenter = ref<any>(null);
const activeView = ref('unassigned_new');
const queueStart = ref(0);
const queueLimit = 25;

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
	source: '',
	assignment_lane: '',
	sla_status: '',
	organization: '',
	school: '',
});

// Options
const inquiryTypes = ref<string[]>([]);
const inquirySources = ref<string[]>([]);
const users = ref<{ name: string; full_name: string }[]>([]);
const academicYears = ref<string[]>([]);
const allowedOrganizations = ref<string[]>([]);
const allowedSchools = ref<string[]>([]);

// -- Actions --
async function loadOptions() {
	const [types, sources, userList, years, organizations, schools] = await Promise.all([
		getInquiryTypes(),
		getInquirySources(),
		searchAdmissionUsers(''),
		searchAcademicYears(''),
		getInquiryOrganizations(),
		getInquirySchools(),
	]);
	inquiryTypes.value = types || [];
	inquirySources.value = sources || [];
	if (userList) users.value = userList.map((u: any) => ({ name: u[0], full_name: u[1] }));
	if (years) academicYears.value = years.map((y: any) => y[0]);
	allowedOrganizations.value = organizations || [];
	allowedSchools.value = schools || [];
}

async function refresh() {
	loading.value = true;
	error.value = '';
	try {
		const res = await getZeroLostLeadContext({
			filters: filters.value,
			active_view: activeView.value,
			start: queueStart.value,
			limit: queueLimit,
		});
		commandCenter.value = res.command_center;
		data.value = res.analytics;
		activeView.value = res.command_center?.active_view || activeView.value;
	} catch (e) {
		console.error(e);
		error.value = e instanceof Error ? e.message : 'Could not load inquiry queues.';
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
		queueStart.value = 0;
		refresh();
	},
	{ deep: true }
);

onMounted(async () => {
	await loadOptions();
	refresh();
});

function setActiveView(viewId: string) {
	if (!viewId || activeView.value === viewId) return;
	activeView.value = viewId;
	queueStart.value = 0;
	refresh();
}

function nextQueuePage() {
	if (!commandPagination.value.has_next) return;
	queueStart.value += commandPagination.value.limit;
	refresh();
}

function previousQueuePage() {
	if (commandPagination.value.start <= 0) return;
	queueStart.value = Math.max(0, commandPagination.value.start - commandPagination.value.limit);
	refresh();
}

// -- Computed View Models --

const commandViews = computed<ZeroLostLeadView[]>(() => commandCenter.value?.views || []);
const leadRows = computed<ZeroLostLeadRow[]>(() => commandCenter.value?.rows || []);
const commandPagination = computed(() => {
	return (
		commandCenter.value?.pagination || {
			start: 0,
			limit: queueLimit,
			total: 0,
			has_next: false,
		}
	);
});
const activeCommandView = computed(() => {
	return (
		commandViews.value.find(view => view.id === activeView.value) || commandViews.value[0] || null
	);
});
const totalOperationalCount = computed(() =>
	commandViews.value.reduce((total, view) => total + Number(view.count || 0), 0)
);
const hasAnyOperationalLeads = computed(() => totalOperationalCount.value > 0);

function viewCardClass(view: ZeroLostLeadView) {
	const active = activeCommandView.value?.id === view.id;
	if (active) return 'border-canopy bg-canopy/5 shadow-sm';
	if (view.count > 0 && view.tone === 'danger')
		return 'border-red-200 bg-red-50 hover:border-red-300';
	if (view.count > 0 && view.tone === 'warning')
		return 'border-amber-200 bg-amber-50 hover:border-amber-300';
	if (view.count > 0) return 'border-sky-200 bg-sky-50 hover:border-sky-300';
	return 'border-slate-200 bg-white hover:border-slate-300';
}

function viewCountClass(view: ZeroLostLeadView) {
	if (view.count <= 0) return 'bg-slate-100 text-slate-500';
	if (view.tone === 'danger') return 'bg-red-100 text-red-700';
	if (view.tone === 'warning') return 'bg-amber-100 text-amber-700';
	return 'bg-sky-100 text-sky-700';
}

function formatDate(value?: string | null) {
	if (!value) return 'No date';
	return String(value).slice(0, 10);
}

function formatDateTime(value?: string | null) {
	if (!value) return 'unknown';
	return String(value).replace('T', ' ').slice(0, 16);
}

function formatAge(hours: number) {
	if (hours < 24) return `${Math.round(hours)}h old`;
	return `${Math.round(hours / 24)}d old`;
}

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

const sourceItems = computed(() => {
	if (!data.value?.source_distribution) return [];
	return data.value.source_distribution.map((d: any) => ({
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
