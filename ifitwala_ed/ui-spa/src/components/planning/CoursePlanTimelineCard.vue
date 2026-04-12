<template>
	<section :class="cardClasses">
		<template v-if="!hideHeader">
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
					<span v-if="timeline.holidays.length" class="chip">
						{{ timeline.holidays.length }} holiday spans
					</span>
				</div>
			</div>
		</template>

		<div v-if="timeline.status !== 'ready'" :class="blockedStateClasses">
			<p class="type-body-strong text-ink">Timeline unavailable</p>
			<p class="mt-1 type-caption text-ink/70">
				{{
					timeline.message ||
					'This plan needs more calendar context before a timeline can be shown.'
				}}
			</p>
		</div>

		<div v-else-if="!timeline.units.length" :class="emptyStateClasses">
			<p class="type-body-strong text-ink">No governed units yet</p>
			<p class="mt-1 type-caption text-ink/70">
				Add the unit backbone first, then this timeline will lay out the sequence across the
				selected window.
			</p>
		</div>

		<div v-else :class="contentClasses">
			<p v-if="timeline.summary.unscheduled_unit_count" class="type-caption text-ink/70">
				{{ unscheduledSummary }}
			</p>

			<div class="overflow-x-auto rounded-[1.75rem] border border-line-soft bg-surface-soft/60">
				<div class="timeline-shell" :style="timelineShellStyle">
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
							<p class="timeline-label__title type-body-strong text-ink">{{ unit.title }}</p>
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
									:style="spanStyle(unit.start_date, unit.end_date, 0.8)"
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

const props = withDefaults(
	defineProps<{
		timeline: StaffCoursePlanTimeline;
		hideHeader?: boolean;
		embedded?: boolean;
	}>(),
	{
		hideHeader: false,
		embedded: false,
	}
);

const DAY_MS = 24 * 60 * 60 * 1000;
const DAY_WIDTH_PX = 11;
const MIN_TRACK_WIDTH_PX = 1600;
const timeline = computed(() => props.timeline);
const hideHeader = computed(() => props.hideHeader);

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

const windowStart = computed(() => parseDate(timeline.value.scope.window_start));
const windowEnd = computed(() => parseDate(timeline.value.scope.window_end));
const totalDays = computed(() => {
	if (!windowStart.value || !windowEnd.value) return 0;
	return Math.max(diffDays(windowStart.value, windowEnd.value) + 1, 0);
});
const trackWidthPx = computed(() => Math.max(totalDays.value * DAY_WIDTH_PX, MIN_TRACK_WIDTH_PX));
const timelineShellStyle = computed(() => ({
	'--timeline-track-width': `${trackWidthPx.value}px`,
}));
const cardClasses = computed(() =>
	props.embedded ? 'space-y-4' : 'rounded-[2rem] border border-line-soft bg-white p-6 shadow-soft'
);
const contentClasses = computed(() => (props.hideHeader ? 'space-y-4' : 'mt-6 space-y-4'));
const blockedStateClasses = computed(() =>
	props.hideHeader
		? 'rounded-2xl border border-sand/60 bg-sand/15 px-5 py-4'
		: 'mt-6 rounded-2xl border border-sand/60 bg-sand/15 px-5 py-4'
);
const emptyStateClasses = computed(() =>
	props.hideHeader
		? 'rounded-2xl border border-dashed border-line-soft p-5'
		: 'mt-6 rounded-2xl border border-dashed border-line-soft p-5'
);

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
	const scope = timeline.value.scope;
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
	return `${timeline.value.summary.scheduled_unit_count || 0} scheduled units`;
});

const unscheduledSummary = computed(() => {
	const unscheduledCount = timeline.value.summary.unscheduled_unit_count || 0;
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
	width: calc(var(--timeline-label-width) + var(--timeline-track-width));
	--timeline-label-width: 21.5rem;
}

.timeline-row {
	display: grid;
	grid-template-columns: var(--timeline-label-width) var(--timeline-track-width);
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
	z-index: 8;
	display: flex;
	flex-direction: column;
	justify-content: center;
	gap: 0.15rem;
	min-width: 0;
	padding: 1rem 1.25rem;
	border-right: 1px solid rgb(var(--border-rgb) / 0.9);
	background: rgb(var(--surface-soft-rgb));
	overflow: hidden;
	box-shadow:
		22px 0 0 rgb(var(--surface-soft-rgb)),
		28px 0 30px rgb(var(--surface-soft-rgb) / 0.98);
}

.timeline-label--header {
	background: white;
	box-shadow:
		22px 0 0 rgb(255 255 255),
		28px 0 30px rgb(255 255 255 / 0.98);
}

.timeline-label::after {
	content: '';
	position: absolute;
	top: 0;
	right: -1px;
	bottom: 0;
	width: 2.4rem;
	background: linear-gradient(
		90deg,
		rgb(var(--surface-soft-rgb)),
		rgb(var(--surface-soft-rgb) / 0.96) 58%,
		rgb(var(--surface-soft-rgb) / 0)
	);
	pointer-events: none;
}

.timeline-label--header::after {
	background: linear-gradient(
		90deg,
		rgb(255 255 255),
		rgb(255 255 255 / 0.96) 58%,
		rgb(255 255 255 / 0)
	);
}

.timeline-label__title {
	margin-top: 0.35rem;
	display: -webkit-box;
	overflow: hidden;
	-webkit-box-orient: vertical;
	-webkit-line-clamp: 2;
}

.timeline-track {
	position: relative;
	min-width: 0;
	padding: 0.9rem 1.25rem 0.9rem 2.5rem;
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
	overflow: hidden;
	isolation: isolate;
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
	white-space: nowrap;
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
	border: 1px solid rgb(var(--clay-rgb) / 0.28);
	background:
		repeating-linear-gradient(
			135deg,
			rgb(var(--ink-rgb) / 0.11),
			rgb(var(--ink-rgb) / 0.11) 9px,
			transparent 9px,
			transparent 18px
		),
		linear-gradient(180deg, rgb(var(--sand-rgb) / 0.46), rgb(var(--sand-rgb) / 0.26));
	box-shadow:
		inset 0 0 0 1px rgb(255 255 255 / 0.2),
		0 0 0 1px rgb(var(--sand-rgb) / 0.08);
	opacity: 0.98;
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
	font-weight: 700;
	color: rgb(var(--ink-rgb) / 0.72);
}

.timeline-holiday--row {
	top: 0.45rem;
	bottom: 0.45rem;
	border-radius: 0.75rem;
	background:
		repeating-linear-gradient(
			135deg,
			rgb(var(--ink-rgb) / 0.1),
			rgb(var(--ink-rgb) / 0.1) 9px,
			transparent 9px,
			transparent 18px
		),
		linear-gradient(180deg, rgb(var(--sand-rgb) / 0.52), rgb(var(--sand-rgb) / 0.3));
	border-color: rgb(var(--clay-rgb) / 0.34);
}

.timeline-baseline {
	position: absolute;
	top: calc(50% - 1px);
	left: 0;
	right: 0;
	height: 2px;
	background: rgb(var(--border-rgb) / 0.95);
	z-index: 0;
}

.timeline-bar {
	position: absolute;
	top: calc(50% - 1.45rem);
	display: flex;
	flex-direction: column;
	justify-content: center;
	gap: 0.12rem;
	height: 2.9rem;
	border: 1px solid transparent;
	border-radius: 999px;
	padding: 0.38rem 0.85rem;
	overflow: hidden;
	white-space: normal;
	z-index: 2;
}

.timeline-bar__title {
	display: block;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
	font-size: 0.8rem;
	font-weight: 700;
	color: rgb(var(--ink-rgb) / 0.94);
}

.timeline-bar__meta {
	display: block;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
	font-size: 0.7rem;
	font-weight: 600;
	color: rgb(var(--ink-rgb) / 0.74);
}

.timeline-bar--published {
	border-color: rgb(var(--jacaranda-rgb) / 0.42);
	background: linear-gradient(
		90deg,
		rgb(var(--jacaranda-rgb) / 0.24),
		rgb(var(--jacaranda-rgb) / 0.14)
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
	z-index: 2;
	display: inline-flex;
	max-width: 27rem;
	margin-top: 0.9rem;
	padding: 0.55rem 0.75rem;
	border-radius: 1rem;
	background: white;
	box-shadow: inset 0 0 0 1px rgb(var(--border-rgb) / 0.92);
}

@media (max-width: 1023px) {
	.timeline-shell {
		--timeline-label-width: 16rem;
	}
}
</style>
