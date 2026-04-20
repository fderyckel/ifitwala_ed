<template>
	<TransitionRoot as="template" :show="open" @after-leave="emitAfterLeave">
		<Dialog
			as="div"
			class="if-overlay if-overlay--guardian-calendar"
			:style="overlayStyle"
			:initialFocus="closeBtnEl"
			@close="onDialogClose"
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
				<div class="if-overlay__backdrop" @click="emitClose('backdrop')" />
			</TransitionChild>

			<div class="if-overlay__wrap">
				<TransitionChild
					as="template"
					enter="if-overlay__panel-enter"
					enter-from="if-overlay__panel-from"
					enter-to="if-overlay__panel-to"
					leave="if-overlay__panel-leave"
					leave-from="if-overlay__panel-to"
					leave-to="if-overlay__panel-from"
				>
					<DialogPanel class="if-overlay__panel if-overlay__panel--xl guardian-calendar-overlay">
						<header class="guardian-calendar-overlay__header">
							<div>
								<p class="type-overline text-ink/60">Guardian Portal</p>
								<DialogTitle class="type-h2 text-ink">School Calendar</DialogTitle>
								<p class="mt-2 type-body text-ink/70">
									See school holidays and family-relevant school events in one monthly view.
								</p>
							</div>

							<div class="guardian-calendar-overlay__header-actions">
								<div class="guardian-calendar-overlay__month-nav">
									<button
										type="button"
										class="if-button if-button--secondary"
										@click="stepMonth(-1)"
									>
										<FeatherIcon name="chevron-left" class="h-4 w-4" />
										<span>Previous</span>
									</button>
									<p class="guardian-calendar-overlay__month-label type-body-strong text-ink">
										{{ monthLabel }}
									</p>
									<button
										type="button"
										class="if-button if-button--secondary"
										@click="stepMonth(1)"
									>
										<span>Next</span>
										<FeatherIcon name="chevron-right" class="h-4 w-4" />
									</button>
								</div>

								<div class="flex items-center gap-2">
									<button
										type="button"
										class="if-button if-button--quiet"
										:disabled="loading"
										@click="loadSnapshot"
									>
										Refresh
									</button>
									<button
										ref="closeBtnEl"
										type="button"
										class="if-overlay__icon-button"
										aria-label="Close school calendar"
										@click="emitClose('programmatic')"
									>
										<FeatherIcon name="x" class="h-5 w-5" />
									</button>
								</div>
							</div>
						</header>

						<div class="if-overlay__body guardian-calendar-overlay__body">
							<section class="guardian-calendar-overlay__filters">
								<label class="space-y-1">
									<span class="type-caption text-ink/60">Child filter</span>
									<select v-model="selectedStudent" class="guardian-calendar-overlay__select">
										<option value="">All linked children</option>
										<option v-for="child in children" :key="child.student" :value="child.student">
											{{ child.full_name }}
										</option>
									</select>
								</label>

								<label class="space-y-1">
									<span class="type-caption text-ink/60">School filter</span>
									<select
										v-model="selectedSchool"
										class="guardian-calendar-overlay__select"
										:disabled="schoolFilterLocked"
									>
										<option value="">All family schools</option>
										<option
											v-for="schoolOption in availableSchools"
											:key="schoolOption.school"
											:value="schoolOption.school"
										>
											{{ schoolOption.label }}
										</option>
									</select>
									<p
										v-if="schoolFilterLocked && lockedSchoolLabel"
										class="type-caption text-ink/50"
									>
										School is fixed to {{ lockedSchoolLabel }} for the selected child.
									</p>
								</label>

								<label class="guardian-calendar-overlay__toggle">
									<input v-model="includeHolidays" type="checkbox" />
									<span>Show holidays</span>
								</label>

								<label class="guardian-calendar-overlay__toggle">
									<input v-model="includeSchoolEvents" type="checkbox" />
									<span>Show school events</span>
								</label>
							</section>

							<section class="guardian-calendar-overlay__summary">
								<span class="chip">Holidays {{ summary.holiday_count }}</span>
								<span class="chip">School events {{ summary.school_event_count }}</span>
								<span class="chip">Month {{ monthRangeLabel }}</span>
							</section>

							<section
								v-if="errorMessage"
								class="guardian-calendar-overlay__status guardian-calendar-overlay__status--error"
							>
								<p class="type-body-strong text-flame">Could not load the school calendar.</p>
								<p class="mt-2 type-body text-ink/70">{{ errorMessage }}</p>
							</section>

							<section v-else-if="loading && !snapshot" class="guardian-calendar-overlay__status">
								<p class="type-body text-ink/70">Loading school calendar...</p>
							</section>

							<section v-else class="guardian-calendar-overlay__workspace">
								<div class="guardian-calendar-overlay__calendar card-surface">
									<div class="guardian-calendar-overlay__weekday-row">
										<p
											v-for="weekday in weekdayLabels"
											:key="weekday"
											class="type-caption text-ink/60"
										>
											{{ weekday }}
										</p>
									</div>

									<div class="guardian-calendar-overlay__grid">
										<template
											v-for="(cell, index) in calendarCells"
											:key="cell ? cell.date : `empty-${index}`"
										>
											<div
												v-if="!cell"
												class="guardian-calendar-overlay__empty-cell"
												aria-hidden="true"
											/>
											<button
												v-else
												type="button"
												class="guardian-calendar-overlay__day"
												:class="{
													'guardian-calendar-overlay__day--today': cell.isToday,
													'guardian-calendar-overlay__day--selected': cell.isSelected,
												}"
												@click="selectedDate = cell.date"
											>
												<div class="guardian-calendar-overlay__day-header">
													<span class="type-body-strong text-ink">{{ cell.dayNumber }}</span>
													<span v-if="cell.items.length" class="guardian-calendar-overlay__count">
														{{ cell.items.length }}
													</span>
												</div>

												<div class="guardian-calendar-overlay__day-items">
													<p
														v-for="item in cell.previewItems"
														:key="`${cell.date}-${item.item_id}`"
														class="guardian-calendar-overlay__day-pill"
														:class="dayPillClass(item)"
														:title="item.title"
													>
														{{ item.title }}
													</p>
													<p
														v-if="cell.hiddenCount > 0"
														class="guardian-calendar-overlay__more type-caption text-ink/60"
													>
														+{{ cell.hiddenCount }} more
													</p>
												</div>
											</button>
										</template>
									</div>
								</div>

								<aside class="guardian-calendar-overlay__agenda card-surface">
									<div class="flex items-start justify-between gap-3">
										<div>
											<h3 class="type-h3 text-ink">{{ selectedDateLabel }}</h3>
											<p class="mt-1 type-caption text-ink/60">
												{{ selectedDateItems.length }}
												{{ selectedDateItems.length === 1 ? 'item' : 'items' }}
											</p>
										</div>
										<button
											type="button"
											class="if-button if-button--secondary"
											@click="jumpToToday"
										>
											Today
										</button>
									</div>

									<div
										v-if="!selectedDateItems.length"
										class="guardian-calendar-overlay__empty-agenda"
									>
										<p class="type-body text-ink/70">
											Nothing is scheduled for this day with the current filters.
										</p>
									</div>

									<ul v-else class="guardian-calendar-overlay__agenda-list">
										<li
											v-for="item in selectedDateItems"
											:key="item.item_id"
											class="guardian-calendar-overlay__agenda-item"
										>
											<div class="flex items-start justify-between gap-3">
												<div class="min-w-0">
													<div class="flex flex-wrap items-center gap-2">
														<span class="chip">
															{{
																item.kind === 'holiday'
																	? 'Holiday'
																	: item.event_category || 'School Event'
															}}
														</span>
														<span v-if="itemSchoolLabel(item)" class="chip">
															{{ itemSchoolLabel(item) }}
														</span>
													</div>

													<p class="mt-3 type-body-strong text-ink">
														{{ item.title }}
													</p>
													<p class="mt-1 type-caption text-ink/60">
														{{ itemTimeLabel(item) }}
													</p>

													<p v-if="item.description" class="mt-3 type-body text-ink/75">
														{{ item.description }}
													</p>

													<div class="mt-3 flex flex-wrap gap-2">
														<span
															v-for="child in item.matched_children"
															:key="`${item.item_id}-${child.student}`"
															class="chip"
														>
															{{ child.full_name }}
														</span>
													</div>
												</div>

												<button
													v-if="item.open_target?.type === 'school-event'"
													type="button"
													class="if-action shrink-0"
													@click="openSchoolEvent(item.open_target.name)"
												>
													View details
												</button>
											</div>
										</li>
									</ul>
								</aside>
							</section>
						</div>
					</DialogPanel>
				</TransitionChild>
			</div>
		</Dialog>
	</TransitionRoot>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import {
	Dialog,
	DialogPanel,
	DialogTitle,
	TransitionChild,
	TransitionRoot,
} from '@headlessui/vue';
import { FeatherIcon } from 'frappe-ui';

import { useOverlayStack } from '@/composables/useOverlayStack';
import { getGuardianCalendarOverlay } from '@/lib/services/guardianCalendar/guardianCalendarService';
import type {
	GuardianCalendarItem,
	Response as GuardianCalendarOverlayResponse,
} from '@/types/contracts/guardian/get_guardian_calendar_overlay';

type CloseReason = 'backdrop' | 'esc' | 'programmatic';

type CalendarCell = {
	date: string;
	dayNumber: number;
	isToday: boolean;
	isSelected: boolean;
	items: GuardianCalendarItem[];
	previewItems: GuardianCalendarItem[];
	hiddenCount: number;
};

const weekdayLabels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

const props = defineProps<{
	open: boolean;
	zIndex?: number;
	overlayId?: string;
	initialMonthStart?: string | null;
}>();

const emit = defineEmits<{
	(e: 'close', reason: CloseReason): void;
	(e: 'after-leave'): void;
}>();

const overlay = useOverlayStack();

const closeBtnEl = ref<HTMLButtonElement | null>(null);
const snapshot = ref<GuardianCalendarOverlayResponse | null>(null);
const loading = ref(false);
const errorMessage = ref('');
const selectedStudent = ref('');
const selectedSchool = ref('');
const includeHolidays = ref(true);
const includeSchoolEvents = ref(true);
const selectedDate = ref('');
const currentMonthStart = ref(normalizeMonthStart(props.initialMonthStart || undefined));

const overlayStyle = computed(() => ({ zIndex: props.zIndex ?? 0 }));

const children = computed(() => snapshot.value?.family.children ?? []);
const summary = computed(
	() =>
		snapshot.value?.summary ?? {
			holiday_count: 0,
			school_event_count: 0,
		}
);

const selectedChild = computed(
	() => children.value.find(child => child.student === selectedStudent.value) || null
);
const lockedSchoolLabel = computed(() => selectedChild.value?.school || '');
const schoolFilterLocked = computed(() => Boolean(selectedChild.value?.school));
const effectiveSchoolFilter = computed(
	() => lockedSchoolLabel.value || selectedSchool.value || ''
);
const availableSchools = computed(() => {
	if (schoolFilterLocked.value && lockedSchoolLabel.value) {
		return [{ school: lockedSchoolLabel.value, label: lockedSchoolLabel.value }];
	}
	return snapshot.value?.filter_options.schools ?? [];
});

const items = computed(() => snapshot.value?.items ?? []);
const monthLabel = computed(() =>
	new Intl.DateTimeFormat(undefined, {
		month: 'long',
		year: 'numeric',
	}).format(parseIsoDate(currentMonthStart.value))
);
const monthEnd = computed(() => endOfMonth(currentMonthStart.value));
const monthRangeLabel = computed(() => `${currentMonthStart.value} to ${monthEnd.value}`);

const itemsByDate = computed(() => {
	const out = new Map<string, GuardianCalendarItem[]>();

	for (const item of items.value) {
		for (const date of datesInMonthSpan(
			item.start,
			item.end,
			currentMonthStart.value,
			monthEnd.value
		)) {
			if (!out.has(date)) {
				out.set(date, []);
			}
			out.get(date)?.push(item);
		}
	}

	for (const entry of out.values()) {
		entry.sort(compareCalendarItems);
	}

	return out;
});

const calendarCells = computed<(CalendarCell | null)[]>(() => {
	const cells: Array<CalendarCell | null> = [];
	const monthStartDate = parseIsoDate(currentMonthStart.value);
	const offset = mondayIndex(monthStartDate);
	const lastDay = endOfMonth(currentMonthStart.value);
	const lastDayNumber = parseIsoDate(lastDay).getDate();

	for (let index = 0; index < offset; index += 1) {
		cells.push(null);
	}

	for (let dayNumber = 1; dayNumber <= lastDayNumber; dayNumber += 1) {
		const cellDate = formatIsoDate(
			new Date(monthStartDate.getFullYear(), monthStartDate.getMonth(), dayNumber)
		);
		const dayItems = itemsByDate.value.get(cellDate) ?? [];
		cells.push({
			date: cellDate,
			dayNumber,
			isToday: cellDate === todayIso(),
			isSelected: cellDate === selectedDate.value,
			items: dayItems,
			previewItems: dayItems.slice(0, 2),
			hiddenCount: Math.max(dayItems.length - 2, 0),
		});
	}

	while (cells.length % 7 !== 0) {
		cells.push(null);
	}

	return cells;
});

const selectedDateLabel = computed(() =>
	new Intl.DateTimeFormat(undefined, {
		weekday: 'long',
		day: 'numeric',
		month: 'long',
		year: 'numeric',
	}).format(parseIsoDate(selectedDate.value || currentMonthStart.value))
);
const selectedDateItems = computed(() => itemsByDate.value.get(selectedDate.value) ?? []);

let requestSeq = 0;

async function loadSnapshot() {
	const seq = ++requestSeq;
	loading.value = true;
	errorMessage.value = '';

	try {
		const payload = await getGuardianCalendarOverlay({
			month_start: currentMonthStart.value,
			student: selectedStudent.value || undefined,
			school: effectiveSchoolFilter.value || undefined,
			include_holidays: includeHolidays.value ? 1 : 0,
			include_school_events: includeSchoolEvents.value ? 1 : 0,
		});

		if (seq !== requestSeq) return;

		snapshot.value = payload;
		currentMonthStart.value = payload.meta.month_start;
		if (!isDateWithinMonth(selectedDate.value, payload.meta.month_start, payload.meta.month_end)) {
			selectedDate.value = defaultSelectedDate(payload.meta.month_start, payload.meta.month_end);
		}
	} catch (error) {
		if (seq !== requestSeq) return;
		const message = error instanceof Error ? error.message : String(error || '');
		errorMessage.value = message || 'Unknown error';
	} finally {
		if (seq === requestSeq) {
			loading.value = false;
		}
	}
}

function emitClose(reason: CloseReason) {
	const overlayId = props.overlayId || null;
	if (overlayId) {
		try {
			overlay.close(overlayId);
			return;
		} catch (_error) {
			// fall through to emit fallback
		}
	}
	emit('close', reason);
}

function emitAfterLeave() {
	emit('after-leave');
}

function onDialogClose(_payload: unknown) {
	// OverlayHost owns close enforcement.
}

function stepMonth(offset: number) {
	const current = parseIsoDate(currentMonthStart.value);
	selectedDate.value = defaultSelectedDate(
		formatIsoDate(new Date(current.getFullYear(), current.getMonth() + offset, 1)),
		endOfMonth(formatIsoDate(new Date(current.getFullYear(), current.getMonth() + offset, 1)))
	);
	currentMonthStart.value = formatIsoDate(
		new Date(current.getFullYear(), current.getMonth() + offset, 1)
	);
}

function jumpToToday() {
	const today = todayIso();
	const normalizedMonth = normalizeMonthStart(today);
	currentMonthStart.value = normalizedMonth;
	selectedDate.value = defaultSelectedDate(normalizedMonth, endOfMonth(normalizedMonth));
}

function openSchoolEvent(eventName: string) {
	if (!eventName) return;
	overlay.open('school-event', { event: eventName });
}

function dayPillClass(item: GuardianCalendarItem) {
	return item.kind === 'holiday'
		? 'guardian-calendar-overlay__day-pill--holiday'
		: 'guardian-calendar-overlay__day-pill--event';
}

function itemSchoolLabel(item: GuardianCalendarItem): string {
	if (item.school) return item.school;
	const schools = Array.from(
		new Set((item.matched_children || []).map(child => child.school).filter(Boolean))
	);
	if (schools.length === 1) return schools[0];
	if (schools.length > 1) return `${schools.length} schools`;
	return '';
}

function itemTimeLabel(item: GuardianCalendarItem): string {
	if (item.kind === 'holiday' || item.all_day) {
		return 'All day';
	}

	const startDate = datePart(item.start);
	const endDate = datePart(item.end);
	const startTime = timePart(item.start);
	const endTime = timePart(item.end);

	if (!startTime && !endTime) {
		return 'Timed event';
	}
	if (startDate === endDate) {
		return `${startTime || 'Start'}${endTime ? ` - ${endTime}` : ''}`;
	}
	return `${shortDateLabel(startDate)} ${startTime || ''} - ${shortDateLabel(endDate)} ${endTime || ''}`.trim();
}

watch(
	() => props.open,
	isOpen => {
		if (!isOpen) return;
		void loadSnapshot();
	},
	{ immediate: true }
);

watch(
	[
		currentMonthStart,
		selectedStudent,
		effectiveSchoolFilter,
		includeHolidays,
		includeSchoolEvents,
	],
	() => {
		if (!props.open) return;
		void loadSnapshot();
	}
);

watch(selectedStudent, () => {
	selectedSchool.value = selectedChild.value?.school || '';
});

watch(currentMonthStart, nextMonth => {
	if (!isDateWithinMonth(selectedDate.value, nextMonth, endOfMonth(nextMonth))) {
		selectedDate.value = defaultSelectedDate(nextMonth, endOfMonth(nextMonth));
	}
});

if (!selectedDate.value) {
	selectedDate.value = defaultSelectedDate(currentMonthStart.value, monthEnd.value);
}

function normalizeMonthStart(value?: string | null): string {
	const resolved = value ? parseIsoDate(datePart(value)) : parseIsoDate(todayIso());
	return formatIsoDate(new Date(resolved.getFullYear(), resolved.getMonth(), 1));
}

function endOfMonth(monthStartValue: string): string {
	const start = parseIsoDate(monthStartValue);
	return formatIsoDate(new Date(start.getFullYear(), start.getMonth() + 1, 0));
}

function defaultSelectedDate(monthStartValue: string, monthEndValue: string): string {
	const today = todayIso();
	if (isDateWithinMonth(today, monthStartValue, monthEndValue)) {
		return today;
	}
	return monthStartValue;
}

function isDateWithinMonth(
	value: string,
	monthStartValue: string,
	monthEndValue: string
): boolean {
	if (!value) return false;
	return value >= monthStartValue && value <= monthEndValue;
}

function parseIsoDate(value: string): Date {
	const [year, month, day] = datePart(value).split('-').map(Number);
	return new Date(year, month - 1, day);
}

function formatIsoDate(value: Date): string {
	const year = value.getFullYear();
	const month = String(value.getMonth() + 1).padStart(2, '0');
	const day = String(value.getDate()).padStart(2, '0');
	return `${year}-${month}-${day}`;
}

function todayIso(): string {
	return formatIsoDate(new Date());
}

function mondayIndex(value: Date): number {
	return (value.getDay() + 6) % 7;
}

function datePart(value: string): string {
	return String(value || '')
		.split('T')[0]
		.split(' ')[0];
}

function timePart(value: string): string {
	const rawValue = String(value || '');
	if (!rawValue) return '';
	const timeValue = rawValue.includes('T') ? rawValue.split('T')[1] : rawValue.split(' ')[1] || '';
	return timeValue ? timeValue.slice(0, 5) : '';
}

function datesInMonthSpan(
	startValue: string,
	endValue: string,
	monthStartValue: string,
	monthEndValue: string
): string[] {
	const spanStart = datePart(startValue || endValue);
	const spanEnd = datePart(endValue || startValue);
	if (!spanStart) return [];

	const start = parseIsoDate(spanStart);
	const end = parseIsoDate(spanEnd || spanStart);
	const boundedStart =
		start < parseIsoDate(monthStartValue) ? parseIsoDate(monthStartValue) : start;
	const boundedEnd = end > parseIsoDate(monthEndValue) ? parseIsoDate(monthEndValue) : end;

	if (boundedEnd < boundedStart) return [];

	const out: string[] = [];
	let cursor = new Date(boundedStart);
	while (cursor <= boundedEnd) {
		out.push(formatIsoDate(cursor));
		cursor = new Date(cursor.getFullYear(), cursor.getMonth(), cursor.getDate() + 1);
	}
	return out;
}

function shortDateLabel(value: string): string {
	return new Intl.DateTimeFormat(undefined, {
		day: 'numeric',
		month: 'short',
	}).format(parseIsoDate(value));
}

function compareCalendarItems(a: GuardianCalendarItem, b: GuardianCalendarItem): number {
	if (a.kind !== b.kind) {
		return a.kind === 'holiday' ? -1 : 1;
	}
	return `${a.start}-${a.title}`.localeCompare(`${b.start}-${b.title}`);
}
</script>

<style scoped>
.guardian-calendar-overlay {
	min-height: min(46rem, calc(100vh - 2.5rem));
}

.guardian-calendar-overlay__header {
	display: flex;
	flex-wrap: wrap;
	align-items: flex-start;
	justify-content: space-between;
	gap: 1rem;
	padding: 1.5rem 1.5rem 1rem;
	border-bottom: 1px solid rgb(var(--border-rgb) / 0.7);
}

.guardian-calendar-overlay__header-actions {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	justify-content: flex-end;
	gap: 0.75rem;
}

.guardian-calendar-overlay__month-nav {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	justify-content: flex-end;
	gap: 0.75rem;
}

.guardian-calendar-overlay__month-label {
	min-width: 11rem;
	text-align: center;
}

.guardian-calendar-overlay__body {
	display: flex;
	flex-direction: column;
	gap: 1rem;
	padding-top: 1rem;
}

.guardian-calendar-overlay__filters {
	display: grid;
	grid-template-columns: repeat(4, minmax(0, 1fr));
	gap: 0.875rem;
}

.guardian-calendar-overlay__select {
	width: 100%;
	border-radius: 1rem;
	border: 1px solid rgb(var(--border-rgb) / 0.8);
	background: rgb(var(--surface-strong-rgb) / 1);
	padding: 0.625rem 0.75rem;
	font-size: 0.95rem;
	color: rgb(var(--ink-rgb) / 1);
}

.guardian-calendar-overlay__toggle {
	display: flex;
	align-items: center;
	gap: 0.625rem;
	align-self: end;
	min-height: 2.75rem;
	border-radius: 1rem;
	border: 1px solid rgb(var(--border-rgb) / 0.75);
	background: rgb(var(--surface-rgb) / 0.75);
	padding: 0.625rem 0.875rem;
	font-size: 0.95rem;
	color: rgb(var(--ink-rgb) / 0.9);
}

.guardian-calendar-overlay__summary {
	display: flex;
	flex-wrap: wrap;
	gap: 0.5rem;
}

.guardian-calendar-overlay__workspace {
	display: grid;
	grid-template-columns: minmax(0, 2.2fr) minmax(20rem, 1fr);
	gap: 1rem;
	min-height: 0;
}

.guardian-calendar-overlay__calendar,
.guardian-calendar-overlay__agenda {
	padding: 1rem;
}

.guardian-calendar-overlay__weekday-row {
	display: grid;
	grid-template-columns: repeat(7, minmax(0, 1fr));
	gap: 0.5rem;
	margin-bottom: 0.5rem;
}

.guardian-calendar-overlay__weekday-row p {
	text-align: center;
}

.guardian-calendar-overlay__grid {
	display: grid;
	grid-template-columns: repeat(7, minmax(0, 1fr));
	gap: 0.5rem;
}

.guardian-calendar-overlay__empty-cell {
	aspect-ratio: 1 / 1;
	border-radius: 1rem;
	border: 1px dashed rgb(var(--border-rgb) / 0.55);
	background: rgb(var(--surface-rgb) / 0.35);
}

.guardian-calendar-overlay__day {
	display: flex;
	flex-direction: column;
	align-items: stretch;
	gap: 0.5rem;
	aspect-ratio: 1 / 1;
	border-radius: 1rem;
	border: 1px solid rgb(var(--border-rgb) / 0.85);
	background: rgb(var(--surface-strong-rgb) / 1);
	padding: 0.625rem;
	text-align: left;
	transition:
		border-color 120ms ease,
		box-shadow 120ms ease,
		transform 120ms ease;
}

.guardian-calendar-overlay__day:hover {
	transform: translateY(-1px);
	border-color: rgb(var(--jacaranda-rgb) / 0.35);
}

.guardian-calendar-overlay__day--today {
	border-color: rgb(var(--jacaranda-rgb) / 0.45);
}

.guardian-calendar-overlay__day--selected {
	box-shadow: 0 0 0 2px rgb(var(--jacaranda-rgb) / 0.35);
}

.guardian-calendar-overlay__day-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 0.5rem;
}

.guardian-calendar-overlay__count {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	min-width: 1.5rem;
	height: 1.5rem;
	border-radius: 999px;
	background: rgb(var(--sand-rgb) / 0.7);
	font-size: 0.75rem;
	font-weight: 600;
	color: rgb(var(--ink-rgb) / 0.7);
}

.guardian-calendar-overlay__day-items {
	display: flex;
	flex-direction: column;
	gap: 0.35rem;
	min-height: 0;
	overflow: hidden;
}

.guardian-calendar-overlay__day-pill {
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
	border-radius: 999px;
	padding: 0.2rem 0.5rem;
	font-size: 0.72rem;
	font-weight: 600;
}

.guardian-calendar-overlay__day-pill--holiday {
	background: rgb(var(--flame-rgb) / 0.12);
	color: rgb(var(--flame-rgb) / 1);
}

.guardian-calendar-overlay__day-pill--event {
	background: rgb(var(--jacaranda-rgb) / 0.12);
	color: rgb(var(--jacaranda-rgb) / 1);
}

.guardian-calendar-overlay__more {
	padding-left: 0.25rem;
}

.guardian-calendar-overlay__agenda {
	display: flex;
	flex-direction: column;
	gap: 1rem;
	min-height: 0;
}

.guardian-calendar-overlay__empty-agenda {
	border-radius: 1rem;
	border: 1px dashed rgb(var(--border-rgb) / 0.7);
	background: rgb(var(--surface-rgb) / 0.55);
	padding: 1rem;
}

.guardian-calendar-overlay__agenda-list {
	display: flex;
	flex-direction: column;
	gap: 0.875rem;
	overflow-y: auto;
}

.guardian-calendar-overlay__agenda-item {
	border-radius: 1rem;
	border: 1px solid rgb(var(--border-rgb) / 0.75);
	background: rgb(var(--surface-rgb) / 0.55);
	padding: 1rem;
}

.guardian-calendar-overlay__status {
	border-radius: 1rem;
	border: 1px dashed rgb(var(--border-rgb) / 0.7);
	background: rgb(var(--surface-rgb) / 0.55);
	padding: 1rem;
}

.guardian-calendar-overlay__status--error {
	border-color: rgb(var(--flame-rgb) / 0.3);
	background: rgb(var(--flame-rgb) / 0.05);
}

@media (max-width: 1023px) {
	.guardian-calendar-overlay__filters,
	.guardian-calendar-overlay__workspace {
		grid-template-columns: 1fr;
	}

	.guardian-calendar-overlay__month-label {
		min-width: 0;
	}
}

@media (max-width: 767px) {
	.guardian-calendar-overlay__header {
		padding: 1rem 1rem 0.75rem;
	}

	.guardian-calendar-overlay__body {
		padding-top: 0.75rem;
	}

	.guardian-calendar-overlay__calendar,
	.guardian-calendar-overlay__agenda {
		padding: 0.875rem;
	}

	.guardian-calendar-overlay__grid,
	.guardian-calendar-overlay__weekday-row {
		gap: 0.35rem;
	}

	.guardian-calendar-overlay__day {
		padding: 0.45rem;
	}
}
</style>
