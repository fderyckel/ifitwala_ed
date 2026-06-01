<template>
	<div data-testid="term-reporting-review-page" class="staff-shell min-w-0 space-y-5">
		<header class="page-header">
			<div class="page-header__intro">
				<p class="type-overline text-slate-token/70">{{ __('Assessment') }}</p>
				<h1 class="type-h1 text-canopy">{{ __('Term Reporting Review') }}</h1>
				<p class="type-meta text-slate-token/80">
					{{
						__(
							'Review frozen course results, calculation method, and component evidence before term reports are consumed downstream.'
						)
					}}
				</p>
			</div>

			<div class="page-header__actions">
				<button
					type="button"
					class="if-button if-button--secondary"
					:disabled="loading"
					@click="loadSurface()"
				>
					<FeatherIcon name="refresh-cw" class="h-4 w-4" />
					<span>{{ __('Refresh') }}</span>
				</button>
			</div>
		</header>

		<FiltersBar>
			<label class="grid min-w-[15rem] gap-1">
				<span class="type-caption text-slate-token/70">{{ __('Reporting Cycle') }}</span>
				<select
					v-model="filters.reporting_cycle"
					data-testid="term-reporting-cycle-filter"
					class="h-10 rounded-lg border border-slate-200 bg-white px-3 type-body text-ink shadow-sm outline-none transition focus:border-jacaranda focus:ring-2 focus:ring-jacaranda/20"
					:disabled="loading || !cycleOptions.length"
				>
					<option value="">{{ __('Latest cycle') }}</option>
					<option v-for="cycle in cycleOptions" :key="cycle.name" :value="cycle.name">
						{{ cycleOptionLabel(cycle) }}
					</option>
				</select>
			</label>

			<label class="grid min-w-[10rem] gap-1">
				<span class="type-caption text-slate-token/70">{{ __('Course') }}</span>
				<input
					v-model.trim="filters.course"
					data-testid="term-reporting-course-filter"
					type="text"
					class="h-10 rounded-lg border border-slate-200 bg-white px-3 type-body text-ink shadow-sm outline-none transition focus:border-jacaranda focus:ring-2 focus:ring-jacaranda/20"
					:placeholder="__('Course ID')"
					:disabled="loading"
				/>
			</label>

			<label class="grid min-w-[10rem] gap-1">
				<span class="type-caption text-slate-token/70">{{ __('Student') }}</span>
				<input
					v-model.trim="filters.student"
					type="text"
					class="h-10 rounded-lg border border-slate-200 bg-white px-3 type-body text-ink shadow-sm outline-none transition focus:border-jacaranda focus:ring-2 focus:ring-jacaranda/20"
					:placeholder="__('Student ID')"
					:disabled="loading"
				/>
			</label>

			<label class="grid min-w-[10rem] gap-1">
				<span class="type-caption text-slate-token/70">{{ __('Program') }}</span>
				<input
					v-model.trim="filters.program"
					type="text"
					class="h-10 rounded-lg border border-slate-200 bg-white px-3 type-body text-ink shadow-sm outline-none transition focus:border-jacaranda focus:ring-2 focus:ring-jacaranda/20"
					:placeholder="__('Program ID')"
					:disabled="loading"
				/>
			</label>

			<div class="ml-auto flex flex-wrap items-end gap-2">
				<button
					type="button"
					class="if-button if-button--primary"
					:disabled="loading"
					@click="applyFilters"
				>
					<FeatherIcon name="search" class="h-4 w-4" />
					<span>{{ __('Apply') }}</span>
				</button>
				<button
					type="button"
					class="if-button if-button--quiet"
					:disabled="loading || !hasDetailFilters"
					@click="clearDetailFilters"
				>
					<FeatherIcon name="x" class="h-4 w-4" />
					<span>{{ __('Clear') }}</span>
				</button>
			</div>
		</FiltersBar>

		<section v-if="pageError" class="card-surface border border-flame/30 bg-flame/5 p-5">
			<div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
				<div>
					<p class="type-body-strong text-flame">
						{{ __('Term reporting review could not load.') }}
					</p>
					<p class="type-body text-ink/75">{{ pageError }}</p>
				</div>
				<button
					type="button"
					class="if-button if-button--secondary"
					:disabled="loading"
					@click="loadSurface()"
				>
					<FeatherIcon name="rotate-cw" class="h-4 w-4" />
					<span>{{ __('Retry') }}</span>
				</button>
			</div>
		</section>

		<section v-if="loading && !surface" class="card-surface p-5">
			<p class="type-body text-slate-token/75">{{ __('Loading term reporting review…') }}</p>
		</section>

		<template v-else-if="surface">
			<section class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
				<article class="mini-kpi-card">
					<p class="mini-kpi-label">{{ __('Cycle Status') }}</p>
					<p class="mini-kpi-value">{{ display(cycle?.status) }}</p>
				</article>
				<article class="mini-kpi-card">
					<p class="mini-kpi-label">{{ __('Results') }}</p>
					<p class="mini-kpi-value">{{ formatInteger(surface.results.total_count) }}</p>
				</article>
				<article class="mini-kpi-card">
					<p class="mini-kpi-label">{{ __('Calculation') }}</p>
					<p class="mini-kpi-value truncate text-lg">
						{{ display(cycle?.assessment_calculation_method) }}
					</p>
				</article>
				<article class="mini-kpi-card">
					<p class="mini-kpi-label">{{ __('Cutoff') }}</p>
					<p class="mini-kpi-value">{{ display(cycle?.task_cutoff_date) }}</p>
				</article>
			</section>

			<section v-if="readiness" data-testid="term-reporting-readiness" class="card-surface p-5">
				<div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
					<div class="min-w-0 space-y-2">
						<div class="flex flex-wrap items-center gap-2">
							<h2 class="type-h3 text-ink">{{ __('Readiness') }}</h2>
							<span class="rounded-full px-2.5 py-1 type-caption" :class="readinessBadgeClass">
								{{ readinessLabel }}
							</span>
						</div>
						<p class="type-body text-slate-token/75">
							{{
								__(
									'Readiness checks the frozen Course Term Result snapshot for this cycle and filter.'
								)
							}}
						</p>
						<p v-if="actionMessage" class="type-caption text-canopy">{{ actionMessage }}</p>
						<p v-if="actionError" class="type-caption text-flame">{{ actionError }}</p>
					</div>

					<div class="flex flex-wrap gap-2">
						<button
							type="button"
							class="if-button if-button--secondary"
							:disabled="loading || Boolean(actionLoading) || !readiness.actions.can_recalculate"
							@click="queueAction('recalculate_course_results')"
						>
							<FeatherIcon name="refresh-ccw" class="h-4 w-4" />
							<span>{{ __('Recalculate') }}</span>
						</button>
						<button
							type="button"
							class="if-button if-button--primary"
							:disabled="
								loading || Boolean(actionLoading) || !readiness.actions.can_generate_reports
							"
							@click="queueAction('generate_student_reports')"
						>
							<FeatherIcon name="file-check" class="h-4 w-4" />
							<span>{{ __('Generate Reports') }}</span>
						</button>
					</div>
				</div>

				<div class="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
					<div
						v-for="item in readinessCountItems"
						:key="item.label"
						class="rounded-lg border border-slate-200 bg-slate-50/70 px-3 py-2"
					>
						<p class="type-caption text-slate-token/70">{{ item.label }}</p>
						<p class="type-body-strong text-ink">{{ item.value }}</p>
					</div>
				</div>

				<div
					v-if="
						readiness.blocked_reasons.length ||
						readiness.warnings.length ||
						disabledActionReasons.length
					"
					class="mt-4 grid gap-3 lg:grid-cols-3"
				>
					<div v-if="readiness.blocked_reasons.length" class="space-y-2">
						<p class="type-caption text-flame">{{ __('Blocked') }}</p>
						<ul class="space-y-1">
							<li
								v-for="reason in readiness.blocked_reasons"
								:key="reason"
								class="type-caption text-ink"
							>
								{{ reason }}
							</li>
						</ul>
					</div>

					<div v-if="readiness.warnings.length" class="space-y-2">
						<p class="type-caption text-amber-700">{{ __('Review') }}</p>
						<ul class="space-y-1">
							<li
								v-for="warning in readiness.warnings"
								:key="warning"
								class="type-caption text-ink"
							>
								{{ warning }}
							</li>
						</ul>
					</div>

					<div v-if="disabledActionReasons.length" class="space-y-2">
						<p class="type-caption text-slate-token/70">{{ __('Actions') }}</p>
						<ul class="space-y-1">
							<li
								v-for="reason in disabledActionReasons"
								:key="reason"
								class="type-caption text-ink"
							>
								{{ reason }}
							</li>
						</ul>
					</div>
				</div>
			</section>

			<section v-if="!cycleOptions.length" class="card-surface p-5">
				<p class="type-body-strong text-ink">
					{{ __('No reporting cycles are available in your current scope.') }}
				</p>
				<p class="type-body text-slate-token/75">
					{{ __('Create or scope a Reporting Cycle before reviewing term results.') }}
				</p>
			</section>

			<section v-else class="grid min-w-0 gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(20rem,24rem)]">
				<div class="card-surface min-w-0 overflow-hidden">
					<div class="border-b border-slate-200 px-5 py-4">
						<div class="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
							<div class="min-w-0">
								<h2 class="type-h3 text-ink">{{ cycleTitle }}</h2>
								<p class="type-caption text-slate-token/70">
									{{ resultWindowLabel }}
								</p>
							</div>
							<div class="flex items-center gap-2">
								<button
									type="button"
									class="if-button if-button--quiet"
									:disabled="loading || !canGoPrevious"
									@click="goPrevious"
								>
									<FeatherIcon name="chevron-left" class="h-4 w-4" />
									<span>{{ __('Prev') }}</span>
								</button>
								<button
									type="button"
									class="if-button if-button--quiet"
									:disabled="loading || !canGoNext"
									@click="goNext"
								>
									<span>{{ __('Next') }}</span>
									<FeatherIcon name="chevron-right" class="h-4 w-4" />
								</button>
							</div>
						</div>
					</div>

					<div v-if="!surface.results.rows.length" class="p-5">
						<p class="type-body-strong text-ink">
							{{ __('No course term results match these filters.') }}
						</p>
						<p class="type-body text-slate-token/75">
							{{ __('Adjust the cycle, course, student, or program filter.') }}
						</p>
					</div>

					<div v-else class="overflow-x-auto">
						<table class="min-w-full divide-y divide-slate-200 text-left">
							<thead class="bg-slate-50/80">
								<tr>
									<th class="px-4 py-3 type-caption text-slate-token/70">{{ __('Student') }}</th>
									<th class="px-4 py-3 type-caption text-slate-token/70">{{ __('Course') }}</th>
									<th class="px-4 py-3 type-caption text-slate-token/70">{{ __('Program') }}</th>
									<th class="px-4 py-3 type-caption text-slate-token/70">{{ __('Score') }}</th>
									<th class="px-4 py-3 type-caption text-slate-token/70">{{ __('Grade') }}</th>
									<th class="px-4 py-3 type-caption text-slate-token/70">{{ __('Tasks') }}</th>
									<th class="px-4 py-3 type-caption text-slate-token/70">{{ __('Weight') }}</th>
									<th class="px-4 py-3 type-caption text-slate-token/70">
										{{ __('Components') }}
									</th>
								</tr>
							</thead>
							<tbody class="divide-y divide-slate-100 bg-white">
								<tr
									v-for="row in surface.results.rows"
									:key="row.name"
									role="button"
									tabindex="0"
									class="cursor-pointer transition hover:bg-sky/10 focus:bg-sky/10 focus:outline-none"
									:class="{ 'bg-sky/15': row.name === selectedResultName }"
									@click="selectResult(row.name)"
									@keydown.enter="selectResult(row.name)"
								>
									<td class="px-4 py-3 type-body text-ink">{{ display(row.student) }}</td>
									<td class="px-4 py-3 type-body text-ink">{{ display(row.course) }}</td>
									<td class="px-4 py-3 type-body text-slate-token/80">
										{{ display(row.program) }}
									</td>
									<td class="px-4 py-3 type-body text-ink">
										{{ formatNumber(row.numeric_score) }}
									</td>
									<td class="px-4 py-3">
										<span class="rounded-full bg-canopy/10 px-2.5 py-1 type-caption text-canopy">
											{{ effectiveGrade(row) }}
										</span>
									</td>
									<td class="px-4 py-3 type-body text-slate-token/80">
										{{ formatInteger(row.task_counted) }}
									</td>
									<td class="px-4 py-3 type-body text-slate-token/80">
										{{ formatNumber(row.total_weight) }}
									</td>
									<td class="px-4 py-3 type-body text-slate-token/80">
										{{ row.components.length }}
									</td>
								</tr>
							</tbody>
						</table>
					</div>
				</div>

				<aside class="card-surface min-w-0 overflow-hidden">
					<div class="border-b border-slate-200 px-5 py-4">
						<p class="type-overline text-slate-token/70">{{ __('Selected Result') }}</p>
						<h2 class="type-h3 text-ink">{{ display(selectedResult?.name) }}</h2>
						<p class="type-caption text-slate-token/70">
							{{ display(selectedResult?.student) }} / {{ display(selectedResult?.course) }}
						</p>
					</div>

					<div v-if="!selectedResult" class="p-5">
						<p class="type-body text-slate-token/75">
							{{ __('Select a row to review its components.') }}
						</p>
					</div>

					<div v-else class="space-y-4 p-5">
						<div class="grid grid-cols-2 gap-3">
							<div>
								<p class="type-caption text-slate-token/70">{{ __('Scheme') }}</p>
								<p class="type-body-strong text-ink">
									{{ display(selectedResult.assessment_scheme) }}
								</p>
							</div>
							<div>
								<p class="type-caption text-slate-token/70">{{ __('Grade Scale') }}</p>
								<p class="type-body-strong text-ink">{{ display(selectedResult.grade_scale) }}</p>
							</div>
						</div>

						<div
							v-if="selectedResult.internal_note"
							class="rounded-lg border border-slate-200 bg-slate-50 p-3"
						>
							<p class="type-caption text-slate-token/70">{{ __('Internal Note') }}</p>
							<p class="type-body text-ink">{{ selectedResult.internal_note }}</p>
						</div>

						<div v-if="!selectedResult.components.length">
							<p class="type-body text-slate-token/75">
								{{ __('No calculation components are stored for this result.') }}
							</p>
						</div>

						<div v-else class="space-y-3">
							<article
								v-for="(component, index) in selectedResult.components"
								:key="`${selectedResult.name}-${index}`"
								class="rounded-lg border border-slate-200 bg-white p-3 shadow-sm"
							>
								<div class="flex items-start justify-between gap-3">
									<div class="min-w-0">
										<p class="type-body-strong text-ink">{{ display(component.label) }}</p>
										<p class="type-caption text-slate-token/70">
											{{ display(component.component_type) }} /
											{{ display(component.component_key) }}
										</p>
									</div>
									<span class="rounded-full bg-slate-100 px-2 py-1 type-caption text-slate-token">
										{{ display(component.grade_value) }}
									</span>
								</div>
								<dl class="mt-3 grid grid-cols-2 gap-3 type-caption text-slate-token/80">
									<div>
										<dt>{{ __('Weight') }}</dt>
										<dd class="type-body-strong text-ink">{{ formatNumber(component.weight) }}</dd>
									</div>
									<div>
										<dt>{{ __('Raw') }}</dt>
										<dd class="type-body-strong text-ink">
											{{ formatNumber(component.raw_score) }}
										</dd>
									</div>
									<div>
										<dt>{{ __('Evidence') }}</dt>
										<dd class="type-body-strong text-ink">
											{{ formatInteger(component.evidence_count) }}
										</dd>
									</div>
									<div>
										<dt>{{ __('Included / Excluded') }}</dt>
										<dd class="type-body-strong text-ink">
											{{ formatInteger(component.included_outcome_count) }} /
											{{ formatInteger(component.excluded_outcome_count) }}
										</dd>
									</div>
								</dl>
								<p v-if="component.calculation_note" class="mt-3 type-caption text-slate-token/75">
									{{ component.calculation_note }}
								</p>
							</article>
						</div>
					</div>
				</aside>
			</section>
		</template>
	</div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import { FeatherIcon } from 'frappe-ui';

import FiltersBar from '@/components/filters/FiltersBar.vue';
import { __ } from '@/lib/i18n';
import {
	getTermReportingReviewSurface,
	queueTermReportingReviewAction,
} from '@/lib/services/termReporting/termReportingService';

import type {
	CourseTermResultRow,
	QueueReviewActionRequest,
	ReportingCycleOption,
	Request as GetTermReportingReviewSurfaceRequest,
	Response as GetTermReportingReviewSurfaceResponse,
} from '@/types/contracts/term_reporting/get_term_reporting_review_surface';

const DEFAULT_PAGE_SIZE = 50;

const filters = reactive({
	reporting_cycle: '',
	course: '',
	student: '',
	program: '',
});

const surface = ref<GetTermReportingReviewSurfaceResponse | null>(null);
const loading = ref(false);
const pageError = ref<string | null>(null);
const actionError = ref<string | null>(null);
const actionMessage = ref<string | null>(null);
const selectedResultName = ref<string | null>(null);
const actionLoading = ref<QueueReviewActionRequest['action'] | null>(null);
const start = ref(0);
let requestVersion = 0;

const cycle = computed(() => surface.value?.cycle ?? null);
const cycleOptions = computed(() => surface.value?.cycles ?? []);
const readiness = computed(() => surface.value?.readiness ?? null);
const selectedReportingCycle = computed(
	() => surface.value?.selected_reporting_cycle || filters.reporting_cycle
);
const selectedResult = computed(() => {
	const rows = surface.value?.results.rows ?? [];
	return rows.find(row => row.name === selectedResultName.value) ?? rows[0] ?? null;
});

const hasDetailFilters = computed(() =>
	Boolean(filters.course || filters.student || filters.program)
);

const cycleTitle = computed(() => {
	const current = cycle.value;
	if (!current) return __('No Reporting Cycle');
	return current.name_label || current.reporting_cycle || __('Reporting Cycle');
});

const resultWindowLabel = computed(() => {
	const results = surface.value?.results;
	if (!results || results.total_count === 0) return __('No results');
	const from = results.start + 1;
	const to = Math.min(results.start + results.page_count, results.total_count);
	return __('Showing {0}-{1} of {2}', [from, to, results.total_count]);
});

const canGoPrevious = computed(() => start.value > 0);
const canGoNext = computed(() => {
	const results = surface.value?.results;
	if (!results) return false;
	return results.start + results.page_count < results.total_count;
});

const readinessLabel = computed(() => {
	const value = readiness.value?.status;
	if (value === 'ready') return __('Ready');
	if (value === 'attention') return __('Review Needed');
	return __('Blocked');
});

const readinessBadgeClass = computed(() => {
	const value = readiness.value?.status;
	if (value === 'ready') return 'bg-canopy/10 text-canopy';
	if (value === 'attention') return 'bg-amber-100 text-amber-800';
	return 'bg-flame/10 text-flame';
});

const readinessCountItems = computed(() => {
	const counts = readiness.value?.counts;
	if (!counts) return [];
	return [
		{ label: __('Total Results'), value: formatInteger(counts.total_results) },
		{ label: __('No Counted Tasks'), value: formatInteger(counts.zero_task_results) },
		{ label: __('Missing Grades'), value: formatInteger(counts.missing_grade_results) },
		{ label: __('Overrides'), value: formatInteger(counts.override_results) },
		{ label: __('Missing Components'), value: formatInteger(counts.missing_component_results) },
		{
			label: __('Missing Comments'),
			value: formatInteger(counts.missing_teacher_comment_results),
		},
	];
});

const disabledActionReasons = computed(() => {
	const current = readiness.value;
	if (!current) return [];
	const reasons = [
		current.actions.recalculate_block_reason,
		current.actions.generate_reports_block_reason,
	].filter((value): value is string => Boolean(value));
	return Array.from(new Set(reasons));
});

function display(value: unknown): string {
	if (value === null || value === undefined || value === '') return '-';
	return String(value);
}

function formatNumber(value: number | null | undefined): string {
	if (value === null || value === undefined || Number.isNaN(Number(value))) return '-';
	return Number(value).toFixed(1);
}

function formatInteger(value: number | null | undefined): string {
	if (value === null || value === undefined || Number.isNaN(Number(value))) return '0';
	return String(Math.trunc(Number(value)));
}

function cycleOptionLabel(cycleOption: ReportingCycleOption): string {
	return (
		cycleOption.name_label ||
		[cycleOption.academic_year, cycleOption.term, cycleOption.program]
			.filter(Boolean)
			.join(' / ') ||
		cycleOption.name
	);
}

function effectiveGrade(row: CourseTermResultRow): string {
	if (row.override_grade_value) return __('{0} override', [row.override_grade_value]);
	return display(row.grade_value);
}

function cleanFilter(value: string): string | undefined {
	const cleaned = String(value || '').trim();
	return cleaned || undefined;
}

function buildPayload(): GetTermReportingReviewSurfaceRequest {
	const payload: GetTermReportingReviewSurfaceRequest = {
		limit: DEFAULT_PAGE_SIZE,
		start: start.value,
	};
	const reportingCycle = cleanFilter(filters.reporting_cycle);
	const course = cleanFilter(filters.course);
	const student = cleanFilter(filters.student);
	const program = cleanFilter(filters.program);
	if (reportingCycle) payload.reporting_cycle = reportingCycle;
	if (course) payload.course = course;
	if (student) payload.student = student;
	if (program) payload.program = program;
	return payload;
}

function extractErrorMessage(error: unknown): string {
	if (!error) return __('Request failed.');
	if (typeof error === 'string') return error;
	if (typeof error === 'object' && 'message' in error) {
		const message = String((error as { message?: unknown }).message || '').trim();
		if (message) return message;
	}
	return __('Request failed.');
}

function actionSuccessMessage(action: QueueReviewActionRequest['action']): string {
	if (action === 'recalculate_course_results') {
		return __('Course result recalculation was queued. Refresh after the job completes.');
	}
	return __('Student term report generation was queued. Refresh after the job completes.');
}

function selectResult(name: string) {
	selectedResultName.value = name;
}

async function loadSurface() {
	const version = ++requestVersion;
	loading.value = true;
	pageError.value = null;
	actionError.value = null;
	try {
		const payload = await getTermReportingReviewSurface(buildPayload());
		if (version !== requestVersion) return;
		surface.value = payload;
		filters.reporting_cycle =
			payload.filters.reporting_cycle || payload.selected_reporting_cycle || '';
		filters.course = payload.filters.course || '';
		filters.student = payload.filters.student || '';
		filters.program = payload.filters.program || '';
		start.value = payload.results.start;

		const rows = payload.results.rows;
		if (!rows.length) {
			selectedResultName.value = null;
		} else if (!rows.some(row => row.name === selectedResultName.value)) {
			selectedResultName.value = rows[0].name;
		}
	} catch (error) {
		if (version !== requestVersion) return;
		pageError.value = extractErrorMessage(error);
	} finally {
		if (version === requestVersion) {
			loading.value = false;
		}
	}
}

async function queueAction(action: QueueReviewActionRequest['action']) {
	const reportingCycle = selectedReportingCycle.value;
	if (!reportingCycle) {
		actionError.value = __('Select a Reporting Cycle first.');
		return;
	}

	actionLoading.value = action;
	actionError.value = null;
	actionMessage.value = null;
	try {
		await queueTermReportingReviewAction({ reporting_cycle: reportingCycle, action });
		actionMessage.value = actionSuccessMessage(action);
	} catch (error) {
		actionError.value = extractErrorMessage(error);
	} finally {
		actionLoading.value = null;
	}
}

function applyFilters() {
	start.value = 0;
	loadSurface();
}

function clearDetailFilters() {
	filters.course = '';
	filters.student = '';
	filters.program = '';
	start.value = 0;
	loadSurface();
}

function goPrevious() {
	start.value = Math.max(0, start.value - DEFAULT_PAGE_SIZE);
	loadSurface();
}

function goNext() {
	start.value += DEFAULT_PAGE_SIZE;
	loadSurface();
}

onMounted(() => {
	loadSurface();
});
</script>
