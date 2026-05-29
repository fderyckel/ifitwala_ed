<!-- ifitwala_ed/ui-spa/src/pages/staff/analytics/InquiryAnalytics.vue -->
<template>
	<div class="analytics-shell">
		<header class="page-header">
			<div class="page-header__intro">
				<h1 class="type-h1 text-canopy">{{ __('Zero Lost Lead') }}</h1>
				<p class="type-meta text-slate-token/80">
					{{ __('Operational inquiry queues first; pipeline and response analytics below.') }}
				</p>
			</div>
			<div class="page-header__actions">
				<DateRangePills
					v-model="filters.date_preset"
					:items="DATE_RANGES"
					@change="handleDatePresetChange"
				/>
				<button type="button" class="if-button if-button--quiet" @click="refresh">
					{{ __('Refresh') }}
				</button>
			</div>
		</header>

		<FiltersBar class="analytics-filters">
			<div class="flex flex-col gap-1">
				<label class="type-label">{{ __('Academic Year') }}</label>
				<select
					v-model="filters.academic_year"
					class="h-9 rounded-md border px-2 text-sm"
					@change="handleAcademicYearChange"
				>
					<option value="">{{ __('All Years') }}</option>
					<option v-for="y in academicYears" :key="y" :value="y">{{ y }}</option>
				</select>
			</div>

			<div class="flex flex-col gap-1">
				<label class="type-label">{{ __('Date Range') }}</label>
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
				<label class="type-label">{{ __('Organization') }}</label>
				<select
					v-model="filters.organization"
					class="h-9 min-w-[160px] max-w-[220px] rounded-md border px-2 text-sm"
				>
					<option value="">{{ __('All Organizations') }}</option>
					<option v-for="o in allowedOrganizations" :key="o" :value="o">{{ o }}</option>
				</select>
			</div>

			<div class="flex flex-col gap-1">
				<label class="type-label">{{ __('School') }}</label>
				<select
					v-model="filters.school"
					class="h-9 min-w-[140px] max-w-[200px] rounded-md border px-2 text-sm"
				>
					<option value="">{{ __('All Permitted') }}</option>
					<option v-for="s in allowedSchools" :key="s" :value="s">{{ s }}</option>
				</select>
			</div>

			<div class="flex flex-col gap-1">
				<label class="type-label">{{ __('Assignee') }}</label>
				<select
					v-model="filters.assigned_to"
					class="h-9 min-w-[140px] rounded-md border px-2 text-sm"
				>
					<option value="">{{ __('All Users') }}</option>
					<option v-for="u in users" :key="u.name" :value="u.name">{{ u.full_name }}</option>
				</select>
			</div>

			<div class="flex flex-col gap-1">
				<label class="type-label">{{ __('Inquiry Type') }}</label>
				<select
					v-model="filters.type_of_inquiry"
					class="h-9 min-w-[140px] rounded-md border px-2 text-sm"
				>
					<option value="">{{ __('All Types') }}</option>
					<option v-for="t in inquiryTypes" :key="t" :value="t">{{ t }}</option>
				</select>
			</div>

			<div class="flex flex-col gap-1">
				<label class="type-label">{{ __('Source') }}</label>
				<select v-model="filters.source" class="h-9 min-w-[140px] rounded-md border px-2 text-sm">
					<option value="">{{ __('All Sources') }}</option>
					<option v-for="s in inquirySources" :key="s" :value="s">{{ s }}</option>
				</select>
			</div>

			<div class="flex flex-col gap-1">
				<label class="type-label">{{ __('Assignment Lane') }}</label>
				<select
					v-model="filters.assignment_lane"
					class="h-9 min-w-[140px] rounded-md border px-2 text-sm"
				>
					<option value="">{{ __('All Lanes') }}</option>
					<option value="Admission">{{ __('Admission') }}</option>
					<option value="Staff">{{ __('Staff') }}</option>
				</select>
			</div>
		</FiltersBar>

		<div v-if="loading" class="py-12 text-center text-slate-500">Loading inquiry queues...</div>
		<div v-else-if="error" class="analytics-card border-red-200 bg-red-50 text-red-700">
			{{ error }}
		</div>

		<template v-else>
			<section class="analytics-card analytics-card--dense">
				<div class="mb-2 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
					<div>
						<h2 class="analytics-card__title">{{ __('Operational Queues') }}</h2>
						<p class="type-caption text-slate-token/70">
							{{
								__(
									'All-time lead-loss queues. Organization, school, assignee, type, source, and lane filters still apply.'
								)
							}}
						</p>
					</div>
					<div
						class="inline-flex w-fit items-baseline gap-2 rounded-md border border-slate-200 bg-white px-3 py-1.5"
					>
						<span class="text-xl font-semibold tabular-nums text-ink">{{
							totalOperationalCount
						}}</span>
						<span class="type-caption text-slate-token/70">{{ queueMatchLabel }}</span>
					</div>
				</div>

				<div class="zero-lost-grid">
					<button
						v-for="view in commandViews"
						:key="view.id"
						type="button"
						class="min-h-[96px] rounded-md border p-3 text-left transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-canopy"
						:class="viewCardClass(view)"
						@click="setActiveView(view.id)"
					>
						<div class="flex h-full flex-col justify-between gap-3">
							<div class="flex items-start justify-between gap-3">
								<span class="type-label leading-snug text-ink">{{ view.title }}</span>
								<span
									class="text-3xl font-semibold leading-none tabular-nums"
									:class="viewNumberClass(view)"
								>
									{{ view.count }}
								</span>
							</div>
							<span class="line-clamp-2 type-caption leading-snug text-slate-token/70">
								{{ view.next_action }}
							</span>
						</div>
					</button>
				</div>
			</section>

			<section class="analytics-card">
				<div class="mb-4 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
					<div>
						<h2 class="analytics-card__title">
							{{ activeCommandView?.title || __('Selected Queue') }}
						</h2>
						<p class="type-meta text-slate-token/70">{{ matchingInquiryLabel }}</p>
					</div>
					<div class="flex items-center gap-2">
						<button
							type="button"
							class="if-button if-button--quiet"
							:disabled="commandPagination.start <= 0"
							@click="previousQueuePage"
						>
							{{ __('Previous') }}
						</button>
						<button
							type="button"
							class="if-button if-button--quiet"
							:disabled="!commandPagination.has_next"
							@click="nextQueuePage"
						>
							{{ __('Next') }}
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
								<th class="py-2 pr-4 font-medium">{{ __('Lead') }}</th>
								<th class="py-2 pr-4 font-medium">{{ __('State') }}</th>
								<th class="py-2 pr-4 font-medium">{{ __('Owner') }}</th>
								<th class="py-2 pr-4 font-medium">{{ __('Due') }}</th>
								<th class="py-2 pr-4 font-medium">{{ __('Context') }}</th>
								<th class="py-2 pr-4 font-medium">{{ __('Next Action') }}</th>
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
										{{ row.sla_status || __('No SLA status') }}
									</div>
									<div
										v-if="row.age_hours !== null && row.age_hours !== undefined"
										class="type-caption text-slate-token/70"
									>
										{{ formatAge(row.age_hours) }}
									</div>
								</td>
								<td class="py-3 pr-4 align-top">
									<div class="font-medium text-ink">{{ row.assigned_to || __('Unassigned') }}</div>
									<div class="type-caption text-slate-token/70">
										{{ row.assignment_lane || __('Admission') }}
									</div>
								</td>
								<td class="py-3 pr-4 align-top">
									<div class="font-medium text-ink">
										{{ formatDate(row.first_contact_due_on) }}
									</div>
									<div class="type-caption text-slate-token/70">
										{{ __('Submitted {0}', [formatDateTime(row.submitted_at)]) }}
									</div>
									<div v-if="row.followup_due_on" class="type-caption text-slate-token/70">
										{{ __('Follow-up {0}', [formatDate(row.followup_due_on)]) }}
									</div>
								</td>
								<td class="py-3 pr-4 align-top">
									<div class="font-medium text-ink">
										{{ row.school || row.organization || __('No scope set') }}
									</div>
									<div class="type-caption text-slate-token/70">
										{{
											[row.type_of_inquiry, row.source].filter(Boolean).join(' / ') ||
											__('No type or source')
										}}
									</div>
									<div v-if="row.student_applicant" class="type-caption text-slate-token/70">
										{{ __('Applicant {0}', [row.student_applicant_status || __('Linked')]) }}
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
						<StatsTile :label="__('Total')" :value="lane.counts.total" />
						<StatsTile :label="__('Contacted')" :value="lane.counts.contacted" />
						<StatsTile
							:label="__('Overdue')"
							:value="lane.counts.overdue_first_contact"
							tone="warning"
						/>
						<StatsTile :label="__('Due Today')" :value="lane.counts.due_today" />
						<StatsTile :label="__('Upcoming')" :value="lane.counts.upcoming" />
						<StatsTile :label="__('SLA (30d)')" :value="lane.sla + '%'" />
					</div>
					<div class="flex gap-6 text-sm">
						<div class="flex flex-col">
							<span class="type-caption">{{ __('Intake Avg') }}</span>
							<span class="font-medium text-ink">{{ lane.avg.intake_response_hours }}h</span>
						</div>
						<div class="flex flex-col">
							<span class="type-caption">{{ __('Resolver Avg') }}</span>
							<span class="font-medium text-ink">{{ lane.avg.resolver_response_hours }}h</span>
						</div>
					</div>
				</div>
			</section>

			<div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
				<!-- Pipeline -->
				<HorizontalBarTopN
					:title="__('Pipeline by State')"
					:items="pipelineItems"
					class="analytics-card"
				/>

				<!-- Weekly Volume -->
				<section class="analytics-card">
					<h3 class="analytics-card__title">{{ __('Weekly Volume') }}</h3>
					<AnalyticsChart :option="weeklyChartOption" />
				</section>
			</div>

			<div class="grid grid-cols-1 gap-6 lg:grid-cols-4">
				<HorizontalBarTopN
					:title="__('Assigned To')"
					:items="assigneeItems"
					class="analytics-card"
				/>
				<HorizontalBarTopN
					:title="__('Inquiry Types')"
					:items="typeItems"
					class="analytics-card"
				/>
				<HorizontalBarTopN
					:title="__('Inquiry Sources')"
					:items="sourceItems"
					class="analytics-card"
				/>
				<HorizontalBarTopN
					:title="__('Lane Distribution')"
					:items="laneDistributionItems"
					class="analytics-card"
				/>
			</div>

			<!-- Detailed Stats & Trends -->
			<section class="grid grid-cols-1 gap-6 lg:grid-cols-3">
				<!-- SLA & Response Stats -->
				<div class="flex flex-col gap-4 analytics-card">
					<h3 class="analytics-card__title">{{ __('Performance Metrics') }}</h3>
					<div class="flex flex-wrap gap-3">
						<StatsTile
							:label="__('SLA Compliance (30d)')"
							:value="data?.sla?.pct_30d + '%'"
							:tone="slaTone"
						/>
						<StatsTile
							:label="__('First Response (Avg)')"
							:value="data?.averages?.overall?.first_contact_hours + 'h'"
						/>
						<StatsTile
							:label="__('From Assign (Avg)')"
							:value="data?.averages?.overall?.from_assign_hours + 'h'"
						/>
					</div>

					<h4 class="mt-2 type-overline text-slate-400">{{ __('Last 30 Days') }}</h4>
					<div class="flex gap-4 text-sm">
						<div class="flex flex-col">
							<span class="type-caption">{{ __('First Contact') }}</span>
							<span class="font-medium text-ink"
								>{{ data?.averages?.last30d?.first_contact_hours }}h</span
							>
						</div>
						<div class="flex flex-col">
							<span class="type-caption">{{ __('From Assign') }}</span>
							<span class="font-medium text-ink"
								>{{ data?.averages?.last30d?.from_assign_hours }}h</span
							>
						</div>
					</div>
				</div>

				<!-- Monthly Trends -->
				<div class="col-span-2 flex flex-col analytics-card">
					<h3 class="analytics-card__title mb-4">
						{{ __('Monthly Average Response Time (Hours)') }}
					</h3>
					<AnalyticsChart :option="monthlyChartOption" />
				</div>
			</section>

			<section class="analytics-card">
				<h3 class="analytics-card__title mb-4">
					{{ __('Monthly Resolver Average by Lane (Hours)') }}
				</h3>
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
import { __ } from '@/lib/i18n';

// -- State --
const loading = ref(false);
const data = ref<any>(null);
const error = ref('');
const commandCenter = ref<any>(null);
const activeView = ref('unassigned_new');
const queueStart = ref(0);
const queueLimit = 25;

const DATE_RANGES = [
	{ label: __('Last 7 Days'), value: '7d' },
	{ label: __('Last 30 Days'), value: '30d' },
	{ label: __('Last 90 Days'), value: '90d' },
	{ label: __('YTD'), value: 'year' },
	{ label: __('All Time'), value: 'all' },
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
const queueMatchLabel = computed(() =>
	totalOperationalCount.value === 1
		? __('{0} queue match', [totalOperationalCount.value])
		: __('{0} queue matches', [totalOperationalCount.value])
);
const matchingInquiryLabel = computed(() =>
	commandPagination.value.total === 1
		? __('{0} matching inquiry', [commandPagination.value.total])
		: __('{0} matching inquiries', [commandPagination.value.total])
);

function viewCardClass(view: ZeroLostLeadView) {
	const active = activeCommandView.value?.id === view.id;
	if (active) return 'border-canopy bg-canopy/5 shadow-sm ring-1 ring-canopy/30';
	if (view.count > 0 && view.tone === 'danger')
		return 'border-red-200 bg-red-50/70 hover:border-red-300 hover:bg-red-50';
	if (view.count > 0 && view.tone === 'warning')
		return 'border-amber-200 bg-amber-50/70 hover:border-amber-300 hover:bg-amber-50';
	if (view.count > 0) return 'border-sky-200 bg-sky-50/70 hover:border-sky-300 hover:bg-sky-50';
	return 'border-slate-200 bg-white hover:border-slate-300';
}

function viewNumberClass(view: ZeroLostLeadView) {
	if (view.count <= 0) return 'text-slate-400';
	if (view.tone === 'danger') return 'text-red-600';
	if (view.tone === 'warning') return 'text-amber-600';
	return 'text-sky-600';
}

function formatDate(value?: string | null) {
	if (!value) return __('No date');
	return String(value).slice(0, 10);
}

function formatDateTime(value?: string | null) {
	if (!value) return __('unknown');
	return String(value).replace('T', ' ').slice(0, 16);
}

function formatAge(hours: number) {
	if (hours < 24) return __('{0}h old', [Math.round(hours)]);
	return __('{0}d old', [Math.round(hours / 24)]);
}

const kpiItems = computed(() => {
	if (!data.value) return [];
	const c = data.value.counts;
	return [
		{ id: 'total', label: __('Total Inquiries'), value: c.total },
		{ id: 'contacted', label: __('Contacted'), value: c.contacted },
		{
			id: 'overdue',
			label: __('Overdue First Contact'),
			value: c.overdue_first_contact,
			hint: __('Action Needed'),
		},
		{ id: 'due_today', label: __('Due Today'), value: c.due_today },
		{
			id: 'upcoming',
			label: __('Upcoming'),
			value: c.upcoming,
			hint: __('Next {0} Days', [data.value.config?.upcoming_horizon_days || 7]),
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
		label: d.label || __('Admission'),
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
			title: __('Admission Lane'),
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
			title: __('Staff Lane'),
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
		yAxis: { type: 'value', splitLine: { lineStyle: { type: 'dashed' } }, name: __('Hours') },
		series: [
			{
				name: __('First Contact'),
				data: s.first_contact,
				type: 'bar',
				itemStyle: { color: '#8b5cf6' },
			},
			{
				name: __('From Assign'),
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
		yAxis: { type: 'value', splitLine: { lineStyle: { type: 'dashed' } }, name: __('Hours') },
		series: [
			{
				name: __('Admission Lane'),
				data: s.admission,
				type: 'line',
				smooth: true,
				itemStyle: { color: '#2563eb' },
			},
			{
				name: __('Staff Lane'),
				data: s.staff,
				type: 'line',
				smooth: true,
				itemStyle: { color: '#ea580c' },
			},
		],
	};
});
</script>
