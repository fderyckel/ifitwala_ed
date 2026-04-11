<template>
	<section class="rounded-[2rem] border border-line-soft bg-white p-6 shadow-soft">
		<div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
			<div>
				<p class="type-overline text-ink/60">Curriculum Timeline</p>
				<h2 class="mt-2 type-h2 text-ink">Year-at-a-glance pacing</h2>
				<p class="mt-2 max-w-3xl type-body text-ink/80">
					See the governed unit sequence against real instructional dates so holidays and school
					breaks visibly push the plan forward.
				</p>
			</div>
			<div v-if="timeline.status === 'ready'" class="flex flex-wrap gap-2">
				<span class="chip">{{ scopeLabel }}</span>
				<span v-if="dateRangeLabel" class="chip">{{ dateRangeLabel }}</span>
				<span class="chip">{{ scheduledCountLabel }}</span>
				<span v-if="timeline.summary.overflow_unit_count" class="chip">
					{{ timeline.summary.overflow_unit_count }} overflow
				</span>
				<span v-if="timeline.holidays.length" class="chip"
					>{{ timeline.holidays.length }} holiday spans</span
				>
			</div>
		</div>

		<div
			v-if="timeline.status !== 'ready'"
			class="mt-6 rounded-2xl border border-sand/60 bg-sand/15 px-5 py-4"
		>
			<p class="type-body-strong text-ink">Timeline unavailable</p>
			<p class="mt-1 type-caption text-ink/70">
				{{
					timeline.message ||
					'This plan needs more calendar context before a timeline can be shown.'
				}}
			</p>
		</div>

		<div
			v-else-if="!timeline.units.length"
			class="mt-6 rounded-2xl border border-dashed border-line-soft p-5"
		>
			<p class="type-body-strong text-ink">No governed units yet</p>
			<p class="mt-1 type-caption text-ink/70">
				Add the unit backbone first, then this timeline will lay out the sequence across the
				selected window.
			</p>
		</div>

		<div v-else class="mt-6 space-y-4">
			<p v-if="timeline.summary.unscheduled_unit_count" class="type-caption text-ink/70">
				{{ unscheduledSummary }}
			</p>

			<div class="overflow-x-auto rounded-[1.75rem] border border-line-soft bg-surface-soft/60">
				<div class="timeline-shell min-w-[78rem]">
					<div class="timeline-row timeline-row--header">
						<div class="timeline-label timeline-label--header">
							<p class="type-caption text-ink/60">Units</p>
						</div>
						<div class="timeline-track timeline-track--header">
							<div class="timeline-track__inner">
								<div
									v-for="holiday in timeline.holidays"
									:key="holidayKey(holiday)"
									class="timeline-holiday"
									:style="spanStyle(holiday.start_date, holiday.end_date)"
								>
									<div class="timeline-holiday__label">{{ holiday.titles[0] || 'Holiday' }}</div>
								</div>
								<div
									v-for="term in timeline.terms"
									:key="term.term || `${term.start_date}-${term.end_date}`"
									class="timeline-term"
									:style="spanStyle(term.start_date, term.end_date)"
								>
									<span>{{ term.label || term.term }}</span>
								</div>
								<div
									v-for="segment in monthSegments"
									:key="segment.key"
									class="timeline-month"
									:style="spanStyle(segment.start_date, segment.end_date)"
								>
									<span>{{ segment.label }}</span>
								</div>
							</div>
						</div>
					</div>

					<div
						v-for="unit in timeline.units"
						:key="unit.unit_plan || unit.title"
						class="timeline-row"
					>
						<div class="timeline-label">
							<p class="type-overline text-ink/60">Unit {{ unit.unit_order || '—' }}</p>
							<p class="mt-1 type-body-strong text-ink">{{ unit.title }}</p>
							<div class="mt-2 flex flex-wrap gap-2">
								<span v-if="unit.duration_label" class="chip">{{ unit.duration_label }}</span>
								<span v-if="unit.unit_status" class="chip">{{ unit.unit_status }}</span>
							</div>
						</div>
						<div class="timeline-track">
							<div class="timeline-track__inner">
								<div
									v-for="holiday in timeline.holidays"
									:key="`${unit.unit_plan || unit.title}-${holidayKey(holiday)}`"
									class="timeline-holiday timeline-holiday--row"
									:style="spanStyle(holiday.start_date, holiday.end_date)"
								/>
								<div class="timeline-baseline" />
								<div
									v-if="unit.start_date && unit.end_date"
									class="timeline-bar"
									:class="barClass(unit)"
									:style="spanStyle(unit.start_date, unit.end_date, 1.2)"
								>
									<div class="timeline-bar__title">{{ unit.title }}</div>
									<div class="timeline-bar__meta">
										{{ unit.duration_label || `${unit.duration_weeks || 0} weeks` }}
									</div>
								</div>
								<div v-else class="timeline-note">
									<p class="type-caption text-ink/80">
										{{
											unit.message ||
											'Add a numeric week duration to place this unit on the timeline.'
										}}
									</p>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	</section>
</template>

<script setup lang="ts">
import { computed } from 'vue';

import type {
	StaffCoursePlanTimeline,
	StaffCoursePlanTimelineHoliday,
	StaffCoursePlanTimelineUnit,
} from '@/types/contracts/staff_teaching/get_staff_course_plan_surface';

const props = defineProps<{
	timeline: StaffCoursePlanTimeline;
}>();

const DAY_MS = 24 * 60 * 60 * 1000;

function parseDate(value?: string | null): Date | null {
	if (!value) return null;
	const parsed = new Date(`${value}T00:00:00`);
	return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function clampDate(value: Date, min: Date, max: Date): Date {
	if (value < min) return min;
	if (value > max) return max;
	return value;
}

function diffDays(start: Date, end: Date): number {
	return Math.round((end.getTime() - start.getTime()) / DAY_MS);
}

function formatIsoDate(value: Date): string {
	const year = value.getFullYear();
	const month = `${value.getMonth() + 1}`.padStart(2, '0');
	const day = `${value.getDate()}`.padStart(2, '0');
	return `${year}-${month}-${day}`;
}

const windowStart = computed(() => parseDate(props.timeline.scope.window_start));
const windowEnd = computed(() => parseDate(props.timeline.scope.window_end));
const totalDays = computed(() => {
	if (!windowStart.value || !windowEnd.value) return 0;
	return Math.max(diffDays(windowStart.value, windowEnd.value) + 1, 0);
});

const monthFormatter = new Intl.DateTimeFormat(undefined, { month: 'short', year: 'numeric' });
const shortDateFormatter = new Intl.DateTimeFormat(undefined, { day: 'numeric', month: 'short' });

const monthSegments = computed(() => {
	if (!windowStart.value || !windowEnd.value) return [];

	const segments: Array<{ key: string; label: string; start_date: string; end_date: string }> = [];
	let cursor = new Date(windowStart.value.getFullYear(), windowStart.value.getMonth(), 1);

	while (cursor <= windowEnd.value) {
		const segmentStart = clampDate(cursor, windowStart.value, windowEnd.value);
		const nextMonth = new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1);
		const segmentEnd = clampDate(
			new Date(nextMonth.getTime() - DAY_MS),
			windowStart.value,
			windowEnd.value
		);
		segments.push({
			key: `${cursor.getFullYear()}-${cursor.getMonth() + 1}`,
			label: monthFormatter.format(segmentStart),
			start_date: formatIsoDate(segmentStart),
			end_date: formatIsoDate(segmentEnd),
		});
		cursor = nextMonth;
	}

	return segments;
});

const scopeLabel = computed(() => {
	const scope = props.timeline.scope;
	if (scope.mode === 'student_group_term') {
		return scope.student_group_label
			? `${scope.student_group_label} · ${scope.term_label || scope.term || 'Term'}`
			: scope.term_label || scope.term || 'Term';
	}
	return scope.academic_year || 'Academic Year';
});

const dateRangeLabel = computed(() => {
	if (!windowStart.value || !windowEnd.value) return '';
	return `${shortDateFormatter.format(windowStart.value)} to ${shortDateFormatter.format(windowEnd.value)}`;
});

const scheduledCountLabel = computed(() => {
	return `${props.timeline.summary.scheduled_unit_count || 0} scheduled units`;
});

const unscheduledSummary = computed(() => {
	const unscheduledCount = props.timeline.summary.unscheduled_unit_count || 0;
	if (!unscheduledCount) return '';
	return `${unscheduledCount} unit${unscheduledCount === 1 ? '' : 's'} still need a usable week duration or timeline room before the full sequence can be shown.`;
});

function holidayKey(holiday: StaffCoursePlanTimelineHoliday) {
	return `${holiday.start_date || 'start'}-${holiday.end_date || 'end'}`;
}

function spanStyle(start?: string | null, end?: string | null, minWidthPercent = 0.8) {
	if (!windowStart.value || !windowEnd.value || !totalDays.value) return {};
	const startDate = parseDate(start);
	const endDate = parseDate(end);
	if (!startDate || !endDate) return {};

	const clampedStart = clampDate(startDate, windowStart.value, windowEnd.value);
	const clampedEnd = clampDate(endDate, windowStart.value, windowEnd.value);
	if (clampedEnd < clampedStart) return {};

	const leftPercent = (diffDays(windowStart.value, clampedStart) / totalDays.value) * 100;
	const widthPercent = Math.max(
		((diffDays(clampedStart, clampedEnd) + 1) / totalDays.value) * 100,
		minWidthPercent
	);

	return {
		left: `${leftPercent}%`,
		width: `${widthPercent}%`,
	};
}

function barClass(unit: StaffCoursePlanTimelineUnit) {
	if (unit.schedule_state === 'overflow') {
		return 'timeline-bar--overflow';
	}
	if (unit.is_published) {
		return 'timeline-bar--published';
	}
	return 'timeline-bar--draft';
}
</script>

<style scoped>
.timeline-shell {
	display: flex;
	flex-direction: column;
}

.timeline-row {
	display: grid;
	grid-template-columns: 17rem minmax(0, 1fr);
	min-height: 5.5rem;
}

.timeline-row + .timeline-row {
	border-top: 1px solid rgb(var(--border-rgb) / 0.85);
}

.timeline-row--header {
	min-height: 4.75rem;
}

.timeline-label {
	position: sticky;
	left: 0;
	z-index: 3;
	display: flex;
	flex-direction: column;
	justify-content: center;
	gap: 0.15rem;
	padding: 1rem 1.25rem;
	border-right: 1px solid rgb(var(--border-rgb) / 0.9);
	background: rgb(var(--surface-soft-rgb) / 0.94);
}

.timeline-label--header {
	background: white;
}

.timeline-track {
	position: relative;
	min-width: 58rem;
	padding: 0.9rem 1rem;
}

.timeline-track--header {
	padding-top: 0.75rem;
	padding-bottom: 0.85rem;
	background:
		linear-gradient(
			to bottom,
			rgb(var(--surface-soft-rgb) / 0.45),
			rgb(var(--surface-soft-rgb) / 0)
		),
		white;
}

.timeline-track__inner {
	position: relative;
	height: 100%;
	min-height: 2.75rem;
}

.timeline-month {
	position: absolute;
	top: 1.8rem;
	bottom: 0.2rem;
	display: flex;
	align-items: flex-start;
	padding-left: 0.35rem;
	border-left: 1px solid rgb(var(--border-rgb) / 0.8);
	font-size: 0.72rem;
	font-weight: 600;
	color: rgb(var(--ink-rgb) / 0.62);
}

.timeline-term {
	position: absolute;
	top: 0;
	height: 1.35rem;
	display: flex;
	align-items: center;
	justify-content: center;
	padding: 0 0.5rem;
	border-radius: 999px;
	background: rgb(var(--jacaranda-rgb) / 0.12);
	color: rgb(var(--ink-rgb) / 0.85);
	font-size: 0.7rem;
	font-weight: 600;
}

.timeline-holiday {
	position: absolute;
	top: 0;
	bottom: 0;
	border-radius: 0.9rem;
	background: repeating-linear-gradient(
		135deg,
		rgb(var(--ink-rgb) / 0.06),
		rgb(var(--ink-rgb) / 0.06) 10px,
		rgb(var(--ink-rgb) / 0.1) 10px,
		rgb(var(--ink-rgb) / 0.1) 20px
	);
}

.timeline-holiday__label {
	position: absolute;
	top: 0.3rem;
	left: 0.45rem;
	max-width: calc(100% - 0.9rem);
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
	font-size: 0.68rem;
	font-weight: 600;
	color: rgb(var(--ink-rgb) / 0.62);
}

.timeline-holiday--row {
	top: 0.35rem;
	bottom: 0.35rem;
	border-radius: 0.75rem;
}

.timeline-baseline {
	position: absolute;
	top: calc(50% - 1px);
	left: 0;
	right: 0;
	height: 2px;
	background: rgb(var(--border-rgb) / 0.95);
}

.timeline-bar {
	position: absolute;
	top: calc(50% - 1rem);
	height: 2rem;
	border: 1px solid transparent;
	border-radius: 999px;
	padding: 0.2rem 0.75rem;
	overflow: hidden;
	white-space: nowrap;
	text-overflow: ellipsis;
}

.timeline-bar__title {
	font-size: 0.78rem;
	font-weight: 700;
	color: rgb(var(--ink-rgb) / 0.92);
}

.timeline-bar__meta {
	font-size: 0.68rem;
	color: rgb(var(--ink-rgb) / 0.62);
}

.timeline-bar--published {
	border-color: rgb(var(--jacaranda-rgb) / 0.38);
	background: linear-gradient(
		90deg,
		rgb(var(--jacaranda-rgb) / 0.2),
		rgb(var(--jacaranda-rgb) / 0.12)
	);
}

.timeline-bar--draft {
	border-color: rgb(var(--sand-rgb) / 0.9);
	background: linear-gradient(
		90deg,
		rgb(var(--sand-rgb) / 0.55),
		rgb(var(--surface-soft-rgb) / 0.95)
	);
}

.timeline-bar--overflow {
	border-color: rgb(var(--clay-rgb) / 0.65);
	background: linear-gradient(90deg, rgb(var(--sand-rgb) / 0.75), rgb(var(--clay-rgb) / 0.26));
}

.timeline-note {
	position: relative;
	z-index: 1;
	display: inline-flex;
	max-width: 27rem;
	margin-top: 0.9rem;
	padding: 0.55rem 0.75rem;
	border-radius: 1rem;
	background: white;
	box-shadow: inset 0 0 0 1px rgb(var(--border-rgb) / 0.92);
}

@media (max-width: 1023px) {
	.timeline-row {
		grid-template-columns: 13.5rem minmax(0, 1fr);
	}
}
</style>
