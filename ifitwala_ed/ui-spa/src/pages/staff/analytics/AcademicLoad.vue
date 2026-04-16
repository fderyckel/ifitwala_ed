<!-- ifitwala_ed/ui-spa/src/pages/staff/analytics/AcademicLoad.vue -->
<template>
	<div class="analytics-shell space-y-5">
		<header class="page-header">
			<div class="page-header__intro">
				<h1 class="type-h1 text-canopy">Academic Load</h1>
				<p class="type-meta text-slate-token/80">
					See current workload shape for academic staff, compare fairness, and support substitute
					decisions with school-configurable scoring.
				</p>
				<div v-if="policySummary" class="mt-2 flex flex-wrap items-center gap-2">
					<span
						class="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-600"
					>
						{{ policySummary.was_customized ? 'Custom policy' : 'Default policy' }}
					</span>
					<span class="text-xs text-slate-500">
						Meetings: {{ policySummary.meeting_blend_mode }} ·
						{{ policySummary.meeting_window_days }} day lookback ·
						{{ policySummary.future_horizon_days }} day horizon
					</span>
				</div>
			</div>
			<div v-if="policySummary?.name" class="page-header__actions">
				<button type="button" class="if-button if-button--secondary" @click="openPolicySettings">
					<FeatherIcon name="sliders" class="h-4 w-4" />
					<span>Workload settings</span>
				</button>
			</div>
		</header>

		<FiltersBar>
			<div class="flex flex-col gap-1">
				<label class="type-label">School</label>
				<select v-model="filters.school" class="h-9 min-w-[180px] rounded-md border px-2 text-sm">
					<option v-for="school in schoolOptions" :key="school.name" :value="school.name">
						{{ school.label }}
					</option>
				</select>
			</div>

			<div class="flex flex-col gap-1">
				<label class="type-label">Academic Year</label>
				<select
					v-model="filters.academic_year"
					class="h-9 min-w-[180px] rounded-md border px-2 text-sm"
				>
					<option value="">All academic years</option>
					<option v-for="year in academicYearOptions" :key="year.name" :value="year.name">
						{{ year.label || year.name }}
					</option>
				</select>
			</div>

			<div class="flex flex-col gap-1">
				<label class="type-label">Time Mode</label>
				<select
					v-model="filters.time_mode"
					class="h-9 min-w-[180px] rounded-md border px-2 text-sm"
				>
					<option v-for="mode in timeModeOptions" :key="mode.value" :value="mode.value">
						{{ mode.label }}
					</option>
				</select>
			</div>

			<div class="flex flex-col gap-1">
				<label class="type-label">Staff Role</label>
				<select
					v-model="filters.staff_role"
					class="h-9 min-w-[180px] rounded-md border px-2 text-sm"
				>
					<option value="">All roles</option>
					<option v-for="role in staffRoleOptions" :key="role.value" :value="role.value">
						{{ role.label }}
					</option>
				</select>
			</div>

			<div class="flex flex-col gap-1">
				<label class="type-label">Search</label>
				<input
					v-model="filters.search"
					type="search"
					class="h-9 min-w-[220px] rounded-md border px-3 text-sm"
					placeholder="Find an educator"
				/>
			</div>
		</FiltersBar>

		<div v-if="accessDenied" class="rounded-md border border-amber-200 bg-amber-50 px-4 py-3">
			<h2 class="text-sm font-semibold text-amber-900">Access restricted</h2>
			<p class="mt-1 text-xs text-amber-800">
				Academic Load is available only to academic admin and coordinator roles.
			</p>
		</div>

		<div
			v-else-if="pageError"
			class="rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-900"
		>
			{{ pageError }}
		</div>

		<div v-else class="space-y-5">
			<KpiRow :items="kpiItems" />

			<nav class="flex flex-wrap gap-2" aria-label="Academic load views">
				<button
					v-for="tab in tabs"
					:key="tab.value"
					type="button"
					class="if-button"
					:class="activeTab === tab.value ? 'if-button--secondary' : 'if-button--quiet'"
					:aria-pressed="activeTab === tab.value"
					@click="activeTab = tab.value"
				>
					{{ tab.label }}
				</button>
			</nav>

			<div v-if="dashboardLoading" class="py-10 text-center text-sm text-slate-500">
				Loading academic load analytics...
			</div>

			<section
				v-else-if="activeTab === 'overview'"
				class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm"
			>
				<div class="overflow-x-auto">
					<table class="min-w-full divide-y divide-slate-200 text-sm">
						<thead class="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
							<tr>
								<th class="px-4 py-3">Educator</th>
								<th class="px-4 py-3">School</th>
								<th class="px-4 py-3 text-right">Teaching</th>
								<th class="px-4 py-3 text-right">Students</th>
								<th class="px-4 py-3 text-right">Activities</th>
								<th class="px-4 py-3 text-right">Meetings</th>
								<th class="px-4 py-3 text-right">Events</th>
								<th class="px-4 py-3 text-right">Total</th>
								<th class="px-4 py-3">Load Band</th>
								<th class="px-4 py-3 text-right">Free Blocks</th>
							</tr>
						</thead>
						<tbody class="divide-y divide-slate-100">
							<tr
								v-for="row in dashboardRows"
								:key="row.educator.employee"
								class="cursor-pointer transition hover:bg-slate-50"
								@click="openDrawer(row.educator.employee)"
							>
								<td class="px-4 py-3">
									<div class="font-medium text-slate-800">{{ row.educator.full_name }}</div>
									<div class="text-xs text-slate-500">{{ row.educator.employee }}</div>
								</td>
								<td class="px-4 py-3 text-slate-600">{{ row.educator.school }}</td>
								<td class="px-4 py-3 text-right">{{ formatNumber(row.facts.teaching_hours) }}</td>
								<td class="px-4 py-3 text-right">{{ row.facts.students_taught }}</td>
								<td class="px-4 py-3 text-right">{{ formatNumber(row.facts.activity_hours) }}</td>
								<td class="px-4 py-3 text-right">
									{{ formatNumber(row.facts.meeting_weekly_avg_hours) }}
								</td>
								<td class="px-4 py-3 text-right">
									{{ formatNumber(row.facts.event_weekly_avg_hours) }}
								</td>
								<td class="px-4 py-3 text-right font-semibold text-slate-800">
									{{ formatNumber(row.scores.total_load_score) }}
								</td>
								<td class="px-4 py-3">
									<span
										class="inline-flex rounded-full px-2.5 py-1 text-xs font-medium"
										:class="bandClass(row.bands.load_band)"
									>
										{{ row.bands.load_band }}
									</span>
								</td>
								<td class="px-4 py-3 text-right">{{ row.availability.free_blocks_count }}</td>
							</tr>
							<tr v-if="dashboardRows.length === 0">
								<td class="px-4 py-6 text-center text-slate-500" colspan="10">
									No educators match the current filters.
								</td>
							</tr>
						</tbody>
					</table>
				</div>
			</section>

			<section v-else-if="activeTab === 'fairness'" class="grid gap-4 xl:grid-cols-2">
				<article class="analytics-card">
					<h3 class="analytics-card__title">Workload Distribution</h3>
					<p class="analytics-card__meta mt-1">Grouped by total weekly-equivalent score.</p>
					<AnalyticsChart class="mt-4 h-[320px]" :option="distributionOption" />
				</article>
				<article class="analytics-card">
					<h3 class="analytics-card__title">Teaching vs Non-Teaching</h3>
					<p class="analytics-card__meta mt-1">
						Compare stable teaching load against meetings, events, and activities.
					</p>
					<AnalyticsChart class="mt-4 h-[320px]" :option="scatterOption" />
				</article>
				<article class="analytics-card xl:col-span-2">
					<h3 class="analytics-card__title">Ranked by Total Load</h3>
					<p class="analytics-card__meta mt-1">
						Use the score for comparison, then read the breakdown in the drawer.
					</p>
					<div class="mt-4 overflow-x-auto">
						<table class="min-w-full divide-y divide-slate-200 text-sm">
							<thead class="text-left text-xs uppercase tracking-wide text-slate-500">
								<tr>
									<th class="pb-3 pr-4">Educator</th>
									<th class="pb-3 pr-4">School</th>
									<th class="pb-3 pr-4 text-right">Total</th>
									<th class="pb-3">Band</th>
								</tr>
							</thead>
							<tbody class="divide-y divide-slate-100">
								<tr v-for="row in rankedRows" :key="row.employee">
									<td class="py-3 pr-4">{{ row.label }}</td>
									<td class="py-3 pr-4 text-slate-600">{{ row.school }}</td>
									<td class="py-3 pr-4 text-right font-semibold">
										{{ formatNumber(row.total_load_score) }}
									</td>
									<td class="py-3">{{ row.load_band }}</td>
								</tr>
							</tbody>
						</table>
					</div>
				</article>
			</section>

			<section v-else class="space-y-4">
				<article class="analytics-card">
					<h3 class="analytics-card__title">Assignment Support</h3>
					<p class="analytics-card__meta mt-1">
						Rank substitute candidates by fit and current load. Strong fit prefers the same student
						group first, then course/program alignment.
					</p>

					<div class="mt-4 grid gap-3 lg:grid-cols-4">
						<div class="flex flex-col gap-1">
							<label class="type-label">Student Group</label>
							<select
								v-model="assignment.student_group"
								class="h-9 rounded-md border px-2 text-sm"
							>
								<option value="">Select student group</option>
								<option v-for="group in studentGroupOptions" :key="group.name" :value="group.name">
									{{ group.label }}
								</option>
							</select>
						</div>
						<div class="flex flex-col gap-1">
							<label class="type-label">Date</label>
							<input
								v-model="assignment.date"
								type="date"
								class="h-9 rounded-md border px-3 text-sm"
							/>
						</div>
						<div class="flex flex-col gap-1">
							<label class="type-label">Start</label>
							<input
								v-model="assignment.start_time"
								type="time"
								class="h-9 rounded-md border px-3 text-sm"
							/>
						</div>
						<div class="flex flex-col gap-1">
							<label class="type-label">End</label>
							<input
								v-model="assignment.end_time"
								type="time"
								class="h-9 rounded-md border px-3 text-sm"
							/>
						</div>
					</div>

					<p v-if="assignmentError" class="mt-3 text-sm text-rose-700">{{ assignmentError }}</p>
				</article>

				<article class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
					<div class="flex items-center justify-between border-b border-slate-200 px-4 py-3">
						<div>
							<h3 class="text-sm font-semibold text-slate-800">Cover Candidates</h3>
							<p class="text-xs text-slate-500">
								Unavailable rows remain visible with explicit reasons.
							</p>
						</div>
						<span v-if="coverRows.length" class="text-xs text-slate-500">
							{{ coverRows.length }} candidates
						</span>
					</div>
					<div v-if="coverLoading" class="py-10 text-center text-sm text-slate-500">
						Loading cover recommendations...
					</div>
					<div v-else class="overflow-x-auto">
						<table class="min-w-full divide-y divide-slate-200 text-sm">
							<thead class="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
								<tr>
									<th class="px-4 py-3">Educator</th>
									<th class="px-4 py-3">Suitability</th>
									<th class="px-4 py-3 text-right">Current Load</th>
									<th class="px-4 py-3 text-right">Free Blocks</th>
									<th class="px-4 py-3">Why</th>
								</tr>
							</thead>
							<tbody class="divide-y divide-slate-100">
								<tr v-for="row in coverRows" :key="row.educator.employee">
									<td class="px-4 py-3">
										<div class="font-medium text-slate-800">{{ row.educator.full_name }}</div>
										<div class="text-xs text-slate-500">{{ row.educator.school }}</div>
									</td>
									<td class="px-4 py-3">
										<span
											class="inline-flex rounded-full px-2.5 py-1 text-xs font-medium"
											:class="coverClass(row.cover_suitability)"
										>
											{{ row.cover_suitability }}
										</span>
									</td>
									<td class="px-4 py-3 text-right">{{ formatNumber(row.total_load_score) }}</td>
									<td class="px-4 py-3 text-right">{{ row.free_blocks_count ?? '—' }}</td>
									<td class="px-4 py-3 text-slate-600">
										{{ (row.reasons || []).join(' ') }}
									</td>
								</tr>
								<tr v-if="!coverRows.length">
									<td class="px-4 py-6 text-center text-slate-500" colspan="5">
										Select a student group and time window to load candidates.
									</td>
								</tr>
							</tbody>
						</table>
					</div>
				</article>
			</section>
		</div>

		<Teleport to="body">
			<TransitionRoot as="template" :show="drawerOpen">
				<Dialog
					as="div"
					class="if-overlay if-overlay--drawer if-overlay--academic-load-detail"
					:initialFocus="drawerCloseButtonRef"
					@close="closeDrawer"
				>
					<TransitionChild
						as="template"
						enter="if-overlay__fade-enter"
						enter-from="if-overlay__fade-from"
						enter-to="if-overlay__fade-to"
						leave="if-overlay__fade-leave"
						leave-from="if-overlay__fade-to"
						leave-to="if-overlay__fade-from"
					>
						<div class="if-overlay__backdrop" @click="closeDrawer" />
					</TransitionChild>

					<div class="if-overlay__wrap if-overlay__wrap--drawer" @click.self="closeDrawer">
						<TransitionChild
							as="template"
							enter="if-overlay__panel-enter"
							enter-from="if-overlay__panel-from"
							enter-to="if-overlay__panel-to"
							leave="if-overlay__panel-leave"
							leave-from="if-overlay__panel-to"
							leave-to="if-overlay__panel-from"
						>
							<DialogPanel class="if-overlay__panel if-overlay__panel--drawer-lg">
								<header
									class="border-b border-border/60 bg-[rgb(var(--surface-rgb)/0.96)] px-5 py-4"
								>
									<div class="flex items-start justify-between gap-3">
										<div>
											<p class="type-overline text-ink/60">Academic Load Detail</p>
											<DialogTitle class="type-h3 mt-2 text-ink">
												{{ drawerDetail?.educator?.full_name || 'Loading...' }}
											</DialogTitle>
										</div>
										<button
											ref="drawerCloseButtonRef"
											type="button"
											class="if-overlay__icon-button"
											aria-label="Close"
											@click="closeDrawer"
										>
											<FeatherIcon name="x" class="h-4 w-4" />
										</button>
									</div>
									<div class="mt-3 flex flex-wrap gap-2">
										<button
											v-for="tab in drawerTabs"
											:key="tab.value"
											type="button"
											class="rounded-full px-3 py-1.5 text-xs font-medium transition"
											:class="
												drawerTab === tab.value
													? 'bg-canopy text-white'
													: 'border border-slate-200 bg-white text-slate-600'
											"
											@click="drawerTab = tab.value"
										>
											{{ tab.label }}
										</button>
									</div>
								</header>

								<section class="if-overlay__body custom-scrollbar px-5 py-4">
									<div v-if="detailLoading" class="py-10 text-center text-sm text-slate-500">
										Loading educator detail...
									</div>
									<div
										v-else-if="detailError"
										class="rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-900"
									>
										{{ detailError }}
									</div>
									<div v-else-if="drawerDetail" class="space-y-4">
										<div v-if="drawerTab === 'overview'" class="grid gap-3 md:grid-cols-2">
											<div class="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
												<p class="text-xs uppercase tracking-wide text-slate-500">Teaching</p>
												<p class="mt-2 text-2xl font-semibold text-slate-800">
													{{ formatNumber(drawerDetail.facts.teaching_hours) }}
												</p>
												<p class="text-xs text-slate-500">Weekly-equivalent hours</p>
											</div>
											<div class="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
												<p class="text-xs uppercase tracking-wide text-slate-500">Students</p>
												<p class="mt-2 text-2xl font-semibold text-slate-800">
													{{ drawerDetail.facts.students_taught }}
												</p>
												<p class="text-xs text-slate-500">Roster load adjustment</p>
											</div>
											<div class="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
												<p class="text-xs uppercase tracking-wide text-slate-500">Activities</p>
												<p class="mt-2 text-2xl font-semibold text-slate-800">
													{{ formatNumber(drawerDetail.facts.activity_hours) }}
												</p>
												<p class="text-xs text-slate-500">Weekly-equivalent hours</p>
											</div>
											<div class="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
												<p class="text-xs uppercase tracking-wide text-slate-500">
													Meetings + Events
												</p>
												<p class="mt-2 text-2xl font-semibold text-slate-800">
													{{
														formatNumber(
															drawerDetail.facts.meeting_weekly_avg_hours +
																drawerDetail.facts.event_weekly_avg_hours
														)
													}}
												</p>
												<p class="text-xs text-slate-500">Weekly-equivalent hours</p>
											</div>
										</div>

										<div v-else-if="drawerTab === 'teaching'">
											<DetailTable
												:rows="drawerDetail.breakdown.teaching"
												:columns="teachingColumns"
											/>
										</div>

										<div v-else-if="drawerTab === 'activities'">
											<DetailTable
												:rows="drawerDetail.breakdown.activities"
												:columns="activityColumns"
											/>
										</div>

										<div v-else-if="drawerTab === 'meetings'">
											<DetailTable
												:rows="drawerDetail.breakdown.meetings"
												:columns="meetingColumns"
											/>
										</div>

										<div v-else-if="drawerTab === 'events'">
											<DetailTable :rows="drawerDetail.breakdown.events" :columns="eventColumns" />
										</div>

										<div v-else-if="drawerTab === 'timeline'" class="space-y-3">
											<article
												v-for="entry in drawerDetail.breakdown.timeline"
												:key="`${entry.kind}-${entry.label}-${entry.from_datetime || entry.hours}`"
												class="rounded-xl border border-slate-200 px-4 py-3"
											>
												<p class="text-sm font-semibold text-slate-800">{{ entry.label }}</p>
												<p class="text-xs text-slate-500">
													{{ entry.kind }} ·
													{{
														entry.from_datetime
															? `${entry.from_datetime} to ${entry.to_datetime}`
															: `${entry.hours} hrs`
													}}
												</p>
											</article>
										</div>

										<div v-else class="space-y-3">
											<article
												v-for="note in drawerDetail.breakdown.assignment_notes"
												:key="note"
												class="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700"
											>
												{{ note }}
											</article>
										</div>
									</div>
								</section>
							</DialogPanel>
						</TransitionChild>
					</div>
				</Dialog>
			</TransitionRoot>
		</Teleport>
	</div>
</template>

<script setup lang="ts">
import {
	Dialog,
	DialogPanel,
	DialogTitle,
	TransitionChild,
	TransitionRoot,
} from '@headlessui/vue';
import {
	computed,
	defineComponent,
	h,
	nextTick,
	onBeforeUnmount,
	onMounted,
	reactive,
	ref,
	watch,
} from 'vue';
import { createResource, FeatherIcon } from 'frappe-ui';

import AnalyticsChart from '@/components/analytics/AnalyticsChart.vue';
import FiltersBar from '@/components/filters/FiltersBar.vue';
import KpiRow from '@/components/analytics/KpiRow.vue';

type FilterMetaResponse = {
	schools: Array<{ name: string; label: string }>;
	default_school?: string | null;
	academic_years: Array<{ name: string; label?: string | null }>;
	default_academic_year?: string | null;
	time_modes: Array<{ value: string; label: string }>;
	staff_roles: Array<{ value: string; label: string }>;
	student_groups: Array<{
		name: string;
		label: string;
		course?: string | null;
		program?: string | null;
	}>;
	policy?: {
		name: string;
		school: string;
		meeting_window_days: number;
		future_horizon_days: number;
		meeting_blend_mode: string;
		is_system_default: number;
		was_customized: number;
	};
};

type DashboardRow = {
	educator: { employee: string; full_name: string; school: string };
	facts: {
		teaching_hours: number;
		students_taught: number;
		activity_hours: number;
		meeting_weekly_avg_hours: number;
		event_weekly_avg_hours: number;
		free_blocks_count: number;
	};
	scores: {
		total_load_score: number;
		teaching_units: number;
		non_teaching_units: number;
	};
	bands: { load_band: string };
	availability: { free_blocks_count: number };
};

type DashboardResponse = {
	policy?: FilterMetaResponse['policy'];
	summary?: Record<string, number>;
	kpis?: Array<{ id: string; label: string; value: number | string; unit?: string }>;
	rows: DashboardRow[];
	fairness?: {
		distribution: Array<{ bucket: string; count: number }>;
		scatter: Array<{
			employee: string;
			label: string;
			teaching_units: number;
			non_teaching_units: number;
		}>;
		ranked: Array<{
			employee: string;
			label: string;
			school: string;
			total_load_score: number;
			load_band: string;
		}>;
	};
	meta?: { total_rows?: number };
};

type DetailResponse = {
	educator: { full_name: string };
	facts: DashboardRow['facts'];
	scores: Record<string, number>;
	bands: { load_band: string };
	breakdown: {
		teaching: any[];
		activities: any[];
		meetings: any[];
		events: any[];
		timeline: any[];
		assignment_notes: string[];
	};
};

type CoverResponse = {
	rows: Array<{
		educator: { employee: string; full_name: string; school: string };
		cover_suitability: string;
		total_load_score: number;
		free_blocks_count?: number | null;
		reasons?: string[];
	}>;
};

type AnalyticsTab = 'overview' | 'fairness' | 'assignment';
type DrawerTab =
	| 'overview'
	| 'teaching'
	| 'activities'
	| 'meetings'
	| 'events'
	| 'timeline'
	| 'notes';

const tabs: Array<{ value: AnalyticsTab; label: string }> = [
	{ value: 'overview', label: 'Overview' },
	{ value: 'fairness', label: 'Fairness' },
	{ value: 'assignment', label: 'Assignment Support' },
];

const drawerTabs: Array<{ value: DrawerTab; label: string }> = [
	{ value: 'overview', label: 'Overview' },
	{ value: 'teaching', label: 'Teaching' },
	{ value: 'activities', label: 'Activities' },
	{ value: 'meetings', label: 'Meetings' },
	{ value: 'events', label: 'Events' },
	{ value: 'timeline', label: 'Timeline' },
	{ value: 'notes', label: 'Assignment Notes' },
];

const filters = reactive({
	school: '' as string,
	academic_year: '' as string,
	time_mode: 'current_week',
	staff_role: 'Academic Staff',
	search: '',
});

const assignment = reactive({
	student_group: '',
	date: '',
	start_time: '',
	end_time: '',
});

const meta = ref<FilterMetaResponse | null>(null);
const dashboard = ref<DashboardResponse | null>(null);
const drawerDetail = ref<DetailResponse | null>(null);
const cover = ref<CoverResponse | null>(null);

const accessDenied = ref(false);
const pageError = ref<string | null>(null);
const detailError = ref<string | null>(null);
const assignmentError = ref<string | null>(null);
const dashboardLoading = ref(false);
const detailLoading = ref(false);
const coverLoading = ref(false);
const metaReady = ref(false);
const syncingMeta = ref(false);

const activeTab = ref<AnalyticsTab>('overview');
const drawerTab = ref<DrawerTab>('overview');
const drawerOpen = ref(false);
const drawerCloseButtonRef = ref<HTMLButtonElement | null>(null);
const selectedEmployee = ref('');

const filterMetaResource = createResource({
	url: 'ifitwala_ed.api.academic_load.get_academic_load_filter_meta',
	method: 'POST',
	auto: false,
});

const dashboardResource = createResource({
	url: 'ifitwala_ed.api.academic_load.get_academic_load_dashboard',
	method: 'POST',
	auto: false,
});

const detailResource = createResource({
	url: 'ifitwala_ed.api.academic_load.get_academic_load_staff_detail',
	method: 'POST',
	auto: false,
});

const coverResource = createResource({
	url: 'ifitwala_ed.api.academic_load.get_academic_load_cover_candidates',
	method: 'POST',
	auto: false,
});

const schoolOptions = computed(() => meta.value?.schools || []);
const academicYearOptions = computed(() => meta.value?.academic_years || []);
const timeModeOptions = computed(() => meta.value?.time_modes || []);
const staffRoleOptions = computed(() => meta.value?.staff_roles || []);
const studentGroupOptions = computed(() => meta.value?.student_groups || []);
const policySummary = computed(() => dashboard.value?.policy || meta.value?.policy || null);
const kpiItems = computed(() => dashboard.value?.kpis || []);
const dashboardRows = computed(() => dashboard.value?.rows || []);
const rankedRows = computed(() => dashboard.value?.fairness?.ranked || []);
const coverRows = computed(() => cover.value?.rows || []);

const teachingColumns = [
	{ key: 'student_group_name', label: 'Student Group' },
	{ key: 'course', label: 'Course' },
	{ key: 'student_count', label: 'Students' },
	{ key: 'hours', label: 'Hours' },
];
const activityColumns = [
	{ key: 'student_group_name', label: 'Activity Group' },
	{ key: 'program', label: 'Program' },
	{ key: 'student_count', label: 'Students' },
	{ key: 'hours', label: 'Hours' },
];
const meetingColumns = [
	{ key: 'meeting_name', label: 'Meeting' },
	{ key: 'meeting_category', label: 'Category' },
	{ key: 'from_datetime', label: 'From' },
	{ key: 'hours', label: 'Hours' },
];
const eventColumns = [
	{ key: 'subject', label: 'Event' },
	{ key: 'event_category', label: 'Category' },
	{ key: 'starts_on', label: 'Starts' },
	{ key: 'hours', label: 'Hours' },
];

const distributionOption = computed(() => {
	const rows = dashboard.value?.fairness?.distribution || [];
	return {
		grid: { left: 40, right: 16, top: 20, bottom: 40 },
		xAxis: { type: 'category', data: rows.map(row => row.bucket) },
		yAxis: { type: 'value' },
		series: [
			{
				type: 'bar',
				data: rows.map(row => row.count),
				itemStyle: { color: '#2f6c53' },
			},
		],
	};
});

const scatterOption = computed(() => {
	const rows = dashboard.value?.fairness?.scatter || [];
	return {
		grid: { left: 48, right: 16, top: 20, bottom: 40 },
		xAxis: { type: 'value', name: 'Teaching' },
		yAxis: { type: 'value', name: 'Non-Teaching' },
		tooltip: {
			trigger: 'item',
		},
		series: [
			{
				type: 'scatter',
				symbolSize: 14,
				data: rows.map(row => [row.teaching_units, row.non_teaching_units, row.label]),
				itemStyle: { color: '#1f7a45' },
			},
		],
	};
});

let dashboardTimer: ReturnType<typeof setTimeout> | null = null;
let assignmentTimer: ReturnType<typeof setTimeout> | null = null;

async function loadFilterMeta() {
	pageError.value = null;
	accessDenied.value = false;
	syncingMeta.value = true;
	try {
		const response = (await filterMetaResource.submit({
			payload: {
				school: filters.school || null,
				academic_year: filters.academic_year || null,
			},
		})) as FilterMetaResponse;
		meta.value = response;
		if (!filters.school && response.default_school) {
			filters.school = response.default_school;
		}
		if (!filters.academic_year && response.default_academic_year) {
			filters.academic_year = response.default_academic_year;
		}
		if (
			filters.staff_role &&
			!response.staff_roles.some(role => role.value === filters.staff_role)
		) {
			filters.staff_role = '';
		}
		if (
			assignment.student_group &&
			!response.student_groups.some(group => group.name === assignment.student_group)
		) {
			assignment.student_group = '';
		}
		metaReady.value = true;
	} catch (error: any) {
		const message = String(error?.message || error || '');
		accessDenied.value = /permission|not permitted|not have permission/i.test(message);
		pageError.value = accessDenied.value
			? null
			: message || 'Failed to load Academic Load filters.';
	} finally {
		syncingMeta.value = false;
	}
}

async function loadDashboard() {
	if (!metaReady.value || !filters.school) return;
	dashboardLoading.value = true;
	pageError.value = null;
	try {
		dashboard.value = (await dashboardResource.submit({
			payload: { ...filters },
			start: 0,
			page_length: 50,
		})) as DashboardResponse;
	} catch (error: any) {
		const message = String(error?.message || error || '');
		accessDenied.value = /permission|not permitted|not have permission/i.test(message);
		pageError.value = accessDenied.value ? null : message || 'Failed to load Academic Load.';
	} finally {
		dashboardLoading.value = false;
	}
}

async function openDrawer(employee: string) {
	selectedEmployee.value = employee;
	drawerOpen.value = true;
	drawerTab.value = 'overview';
	detailLoading.value = true;
	detailError.value = null;
	try {
		drawerDetail.value = (await detailResource.submit({
			payload: { filters: { ...filters } },
			employee,
		})) as DetailResponse;
	} catch (error: any) {
		detailError.value = String(error?.message || error || 'Failed to load educator detail.');
	} finally {
		detailLoading.value = false;
	}
}

function closeDrawer() {
	drawerOpen.value = false;
	selectedEmployee.value = '';
	drawerDetail.value = null;
}

function buildAssignmentDatetimes() {
	if (!assignment.date || !assignment.start_time || !assignment.end_time) return null;
	return {
		from_datetime: `${assignment.date} ${assignment.start_time}`,
		to_datetime: `${assignment.date} ${assignment.end_time}`,
	};
}

async function loadCoverCandidates() {
	const datetimes = buildAssignmentDatetimes();
	if (!assignment.student_group || !datetimes) {
		cover.value = { rows: [] };
		return;
	}

	coverLoading.value = true;
	assignmentError.value = null;
	try {
		cover.value = (await coverResource.submit({
			payload: {
				filters: {
					...filters,
					student_group: assignment.student_group,
					from_datetime: datetimes.from_datetime,
					to_datetime: datetimes.to_datetime,
				},
			},
			student_group: assignment.student_group,
			from_datetime: datetimes.from_datetime,
			to_datetime: datetimes.to_datetime,
		})) as CoverResponse;
	} catch (error: any) {
		assignmentError.value = String(error?.message || error || 'Failed to load cover candidates.');
	} finally {
		coverLoading.value = false;
	}
}

function scheduleDashboardReload() {
	if (!metaReady.value) return;
	if (dashboardTimer) clearTimeout(dashboardTimer);
	dashboardTimer = setTimeout(() => {
		loadDashboard();
	}, 220);
}

function scheduleAssignmentReload() {
	if (assignmentTimer) clearTimeout(assignmentTimer);
	assignmentTimer = setTimeout(() => {
		if (activeTab.value === 'assignment') {
			loadCoverCandidates();
		}
	}, 180);
}

async function refreshMetaAndDashboard() {
	if (!metaReady.value || syncingMeta.value) return;
	await loadFilterMeta();
	await loadDashboard();
	if (activeTab.value === 'assignment') {
		await loadCoverCandidates();
	}
}

function formatNumber(value: number | string | null | undefined) {
	const number = Number(value || 0);
	return Number.isFinite(number) ? number.toFixed(1).replace(/\.0$/, '') : '0';
}

function bandClass(band: string) {
	if (band === 'Critical') return 'bg-rose-100 text-rose-700';
	if (band === 'High') return 'bg-amber-100 text-amber-700';
	if (band === 'Normal') return 'bg-emerald-100 text-emerald-700';
	return 'bg-slate-100 text-slate-700';
}

function coverClass(label: string) {
	if (label === 'Strong fit') return 'bg-emerald-100 text-emerald-700';
	if (label === 'Possible') return 'bg-sky-100 text-sky-700';
	if (label === 'Last resort') return 'bg-amber-100 text-amber-700';
	return 'bg-rose-100 text-rose-700';
}

function openPolicySettings() {
	if (!policySummary.value?.name) return;
	window.open(
		`/app/academic-load-policy/${encodeURIComponent(policySummary.value.name)}`,
		'_blank',
		'noopener'
	);
}

watch(
	() => [filters.school, filters.academic_year],
	() => {
		refreshMetaAndDashboard();
	},
	{ flush: 'sync' }
);

watch(
	() => [filters.time_mode, filters.staff_role, filters.search],
	() => {
		if (!metaReady.value) return;
		scheduleDashboardReload();
	}
);

watch(
	() => [
		assignment.student_group,
		assignment.date,
		assignment.start_time,
		assignment.end_time,
		activeTab.value,
	],
	() => {
		scheduleAssignmentReload();
	}
);

onMounted(async () => {
	await loadFilterMeta();
	await nextTick();
	await loadDashboard();
});

onBeforeUnmount(() => {
	if (dashboardTimer) clearTimeout(dashboardTimer);
	if (assignmentTimer) clearTimeout(assignmentTimer);
});

const DetailTable = defineComponent({
	name: 'AcademicLoadDetailTable',
	props: {
		rows: { type: Array, required: true },
		columns: { type: Array, required: true },
	},
	setup(props) {
		return () =>
			h('div', { class: 'overflow-x-auto' }, [
				h('table', { class: 'min-w-full divide-y divide-slate-200 text-sm' }, [
					h(
						'thead',
						{ class: 'text-left text-xs uppercase tracking-wide text-slate-500' },
						h(
							'tr',
							{},
							(props.columns as Array<any>).map(column =>
								h('th', { class: 'pb-3 pr-4' }, String(column.label || ''))
							)
						)
					),
					h(
						'tbody',
						{ class: 'divide-y divide-slate-100' },
						(props.rows as Array<any>).map(row =>
							h(
								'tr',
								{},
								(props.columns as Array<any>).map(column =>
									h('td', { class: 'py-3 pr-4 text-slate-700' }, String(row?.[column.key] ?? '—'))
								)
							)
						)
					),
				]),
			]);
	},
});
</script>
