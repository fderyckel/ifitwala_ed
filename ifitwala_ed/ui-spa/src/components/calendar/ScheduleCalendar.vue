<!-- ifitwala_ed/ui-spa/src/components/calendar/ScheduleCalendar.vue -->
<!--
  ScheduleCalendar.vue
  FullCalendar wrapper for displaying staff or resource schedules. Handles event rendering and interaction.
  Supports filtering by source (Classes, Meetings, School Events, Holidays) and toggling weekends/full-day view.

  Used by:
  - StaffHome.vue (pages/staff)
-->
<!--
  ScheduleCalendar.vue
  FullCalendar wrapper for displaying staff or resource schedules. Handles event rendering and interaction.

  Used by:
  - StaffHome.vue (pages/staff)
-->
<template>
	<div class="relative">
		<section class="paper-card schedule-card p-4 sm:p-6">
			<header class="schedule-calendar__header border-b border-[rgb(var(--border-rgb)/0.9)] pb-4">
				<h2 class="type-h2">Your upcoming commitments</h2>
				<p class="type-meta schedule-calendar__header-meta">
					{{ subtitle }}
				</p>
			</header>

			<!-- Chips row -->
			<div class="schedule-calendar__filters mt-4">
				<div
					class="schedule-calendar__filter-group schedule-calendar__filter-group--controls -mx-1 flex items-center gap-3 overflow-x-auto px-1 pb-1 md:mx-0 md:flex-wrap md:overflow-visible md:px-0 md:pb-0"
				>
					<button class="if-action type-button-label" @click="handleRefresh">
						<FeatherIcon name="refresh-cw" class="h-4 w-4" />
						Refresh
					</button>
					<span v-if="lastUpdatedLabel" class="type-caption text-slate-token/70">
						Updated {{ lastUpdatedLabel }}
					</span>
				</div>

				<!-- Weekend / Full-day toggles -->
				<div
					class="schedule-calendar__filter-group -mx-1 flex items-center gap-3 overflow-x-auto px-1 pb-1 md:mx-0 md:flex-wrap md:overflow-visible md:px-0 md:pb-0"
				>
					<button
						class="if-pill type-button-label"
						:class="showWeekends ? 'if-pill--off' : 'if-pill--on'"
						@click="showWeekends = !showWeekends"
					>
						<FeatherIcon name="calendar" class="h-4 w-4" />
						{{ showWeekends ? 'Show all days' : 'Hide weekends' }}
					</button>
					<button
						class="if-pill type-button-label"
						:class="showFullDay ? 'if-pill--off' : 'if-pill--on'"
						@click="showFullDay = !showFullDay"
					>
						<FeatherIcon name="clock" class="h-4 w-4" />
						{{ showFullDay ? 'Full day on' : 'Default hours' }}
					</button>
				</div>

				<!-- Source chips -->
				<div
					class="schedule-calendar__filter-group -mx-1 flex items-center gap-3 overflow-x-auto px-1 pb-1 md:mx-0 md:flex-wrap md:overflow-visible md:px-0 md:pb-0"
				>
					<button
						v-for="chip in sourceChips"
						:key="chip.id"
						type="button"
						class="if-pill type-button-label"
						:class="chip.active ? chip.activeClass : 'if-pill--off'"
						@click="toggleChip(chip.id)"
					>
						<span class="if-pill__dot" :class="chip.dotClass"></span>
						{{ chip.label }}
						<span class="if-pill__count type-badge-label">
							{{ chip.count }}
						</span>
					</button>
				</div>
			</div>

			<!-- Calendar shell with rounded corners + clipping and breathing room -->
			<div
				class="relative mt-6 overflow-hidden rounded-2xl border border-[rgb(var(--border-rgb)/0.95)] bg-white p-2 shadow-soft sm:p-4"
			>
				<FullCalendar ref="calendarRef" :options="calendarOptions" class="calendar-shell" />

				<!-- Loading veil -->
				<div
					v-if="loading"
					class="absolute inset-0 z-10 flex items-center justify-center rounded-3xl bg-white/70 backdrop-blur"
				>
					<div class="flex items-center gap-2 type-body-strong text-ink/70">
						<FeatherIcon name="loader" class="h-4 w-4 animate-spin" />
						Loading calendar…
					</div>
				</div>
			</div>

			<!-- Empty / error messages -->
			<div
				v-if="error"
				class="mt-4 rounded-2xl border border-[rgb(var(--flame-rgb)/0.25)] bg-[rgb(var(--flame-rgb)/0.05)] px-4 py-3 type-body text-flame"
			>
				{{ error }}
			</div>
			<div
				v-else-if="isEmpty"
				class="mt-4 rounded-2xl border border-dashed border-[rgb(var(--border-rgb)/0.9)] bg-[rgb(var(--sky-rgb)/0.45)] px-4 py-6 text-center type-body text-ink/70"
			>
				Nothing scheduled for this range. Enjoy the calm or adjust the view to a different week.
			</div>
		</section>
	</div>
</template>

<script setup lang="ts">
/**
 * ScheduleCalendar.vue (Overlay stack refactor)
 *
 * Truth now:
 *  - Meeting / School Event / Class Event details open via the global overlay stack.
 *  - Overlays fetch and own their own data (ScheduleCalendar passes only IDs).
 *  - Create-task opens via overlay stack (rendered only by OverlayHost).
 *  - OrgCommunicationQuickCreateModal.
 */

import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import FullCalendar from '@fullcalendar/vue3';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import listPlugin from '@fullcalendar/list';
import { DatesSetArg, EventClickArg } from '@fullcalendar/core';
import { FeatherIcon } from 'frappe-ui';

import { CalendarSource, useCalendarEvents } from '@/composables/useCalendarEvents';
import { useCalendarPrefs } from '@/composables/useCalendarPrefs';
import { SIGNAL_CALENDAR_INVALIDATE, uiSignals } from '@/lib/uiSignals';

// ✅ Overlay stack (single renderer via OverlayHost teleported to #overlay-root)
import { useOverlayStack } from '@/composables/useOverlayStack';

// Vendor local placeholder styles to unblock build
import '@/styles/fullcalendar/core.css';
import '@/styles/fullcalendar/daygrid.css';
import '@/styles/fullcalendar/timegrid.css';
import '@/styles/fullcalendar/list.css';
import '@/styles/fullcalendar/ifitwala-fullcalendar.css';

const props = defineProps<{
	role?: 'staff' | 'student' | 'guardian';
	autoRefreshInterval?: number;
}>();

const refreshInterval = computed(() => props.autoRefreshInterval ?? 30 * 60 * 1000);

const {
	events,
	counts,
	timezone,
	loading,
	error,
	lastUpdated,
	activeSources,
	isEmpty,
	setRange,
	refresh,
	toggleSource,
} = useCalendarEvents({ role: props.role ?? 'staff' });

/**
 * Timezone strategy:
 *  - You already decided: safest is FullCalendar timeZone 'local' (no plugin needed).
 *  - We keep the existing syncCalendarTimezone behavior.
 */
const resolveSystemTimezone = () =>
	((window as any)?.frappe?.boot?.time_zone ||
		(window as any)?.frappe?.boot?.timezone ||
		timezone.value ||
		Intl.DateTimeFormat().resolvedOptions().timeZone ||
		'UTC') as string;

const systemTimezone = ref<string>(resolveSystemTimezone());

function syncCalendarTimezone() {
	// DIAG: force local time zone (no plugin needed)
	const tz = 'local';

	calendarOptions.value.timeZone = tz;
	calendarOptions.value.now = new Date();

	const api = calendarRef.value?.getApi();
	if (api) {
		api.setOption('timeZone', tz);
		api.setOption('now', new Date());
		api.render();
	}
}

// Calendar preferences and toggles
const { fetch: fetchPrefs } = useCalendarPrefs();
const showWeekends = ref(false);
const showFullDay = ref(false);
const hiddenDays = ref<number[]>([0, 6]);
const slotMin = ref<string>('07:00:00');
const slotMax = ref<string>('17:00:00');

const subtitle = computed(() => {
	const total = events.value.length;
	return total
		? `${total} event${total === 1 ? '' : 's'} in view`
		: 'Nothing scheduled in this range';
});

const calendarRef = ref<InstanceType<typeof FullCalendar> | null>(null);
type CalendarScreen = 'phone' | 'tablet' | 'desktop';
type CalendarViewName = 'dayGridMonth' | 'timeGridWeek' | 'timeGridDay' | 'listWeek';
type CalendarHeaderToolbar = {
	left: string;
	center: string;
	right: string;
};

const PHONE_MAX_WIDTH = 767;
const TABLET_MAX_WIDTH = 1023;

const currentScreen = ref<CalendarScreen>(resolveCalendarScreen());
const preferredView = ref<CalendarViewName>(defaultViewForScreen(currentScreen.value));
const calendarHeight = ref<number>(computeCalendarHeight());

const calendarOptions = ref({
	plugins: [dayGridPlugin, timeGridPlugin, listPlugin],
	initialView: preferredView.value,
	height: calendarHeight.value,
	headerToolbar: buildHeaderToolbar(currentScreen.value),
	slotDuration: '00:30:00',
	slotMinTime: slotMin.value,
	slotMaxTime: slotMax.value,
	dayMaxEvents: true,
	displayEventTime: false,
	navLinks: false,
	nowIndicator: true,
	events: events.value,
	timeZone: systemTimezone.value,
	now: new Date(),
	hiddenDays: hiddenDays.value,
	datesSet: (arg: DatesSetArg) => handleDatesSet(arg),
	eventDisplay: 'block',
	eventClick: (info: EventClickArg) => handleEventClick(info),
});

watch(events, val => {
	calendarOptions.value.events = val;
});

watch(timezone, tz => {
	systemTimezone.value = tz || resolveSystemTimezone();
	syncCalendarTimezone();
});

watch(systemTimezone, () => {
	syncCalendarTimezone();
});

watch(showWeekends, val => {
	calendarOptions.value.hiddenDays = val ? [] : hiddenDays.value;
});

watch(showFullDay, val => {
	calendarOptions.value.slotMinTime = val ? '00:00:00' : slotMin.value;
	calendarOptions.value.slotMaxTime = val ? '24:00:00' : slotMax.value;
});

function resolveCalendarScreen(): CalendarScreen {
	if (typeof window === 'undefined') return 'desktop';
	const width = window.innerWidth || 0;
	if (width <= PHONE_MAX_WIDTH) return 'phone';
	if (width <= TABLET_MAX_WIDTH) return 'tablet';
	return 'desktop';
}

function defaultViewForScreen(screen: CalendarScreen): CalendarViewName {
	return screen === 'phone' ? 'listWeek' : 'timeGridWeek';
}

function buildHeaderToolbar(screen: CalendarScreen): CalendarHeaderToolbar {
	if (screen === 'phone') {
		return {
			left: 'prev,next',
			center: 'title',
			right: 'today,listWeek',
		};
	}

	if (screen === 'tablet') {
		return {
			left: 'prev,next today',
			center: 'title',
			right: 'timeGridWeek,timeGridDay,listWeek',
		};
	}

	return {
		left: 'prev,next today',
		center: 'title',
		right: 'dayGridMonth,timeGridWeek,timeGridDay,listWeek',
	};
}

function computeCalendarHeight(): number {
	if (typeof window === 'undefined') return 640;
	const viewportHeight = window.innerHeight || 0;
	if (currentScreen.value === 'phone') {
		const target = Math.round(viewportHeight * 0.5);
		return Math.max(360, Math.min(target, 460));
	}

	if (currentScreen.value === 'tablet') {
		const target = Math.round(viewportHeight * 0.58);
		return Math.max(440, Math.min(target, 620));
	}

	const target = Math.round(viewportHeight * 0.65);
	return Math.max(520, Math.min(target, 760));
}

function applyCalendarHeight() {
	const nextHeight = computeCalendarHeight();
	calendarHeight.value = nextHeight;
	calendarOptions.value.height = nextHeight;
	const api = calendarRef.value?.getApi();
	if (api) api.setOption('height', nextHeight);
}

function applyResponsiveCalendarLayout(nextScreen = resolveCalendarScreen()) {
	currentScreen.value = nextScreen;
	calendarOptions.value.headerToolbar = buildHeaderToolbar(nextScreen);
	applyCalendarHeight();

	const nextDefaultView = defaultViewForScreen(nextScreen);
	const api = calendarRef.value?.getApi();
	if (!api) {
		preferredView.value = nextDefaultView;
		calendarOptions.value.initialView = nextDefaultView;
		return;
	}

	api.setOption('headerToolbar', calendarOptions.value.headerToolbar);

	const currentView = api.view.type as CalendarViewName;
	if (nextScreen === 'phone') {
		if (currentView !== 'listWeek') {
			preferredView.value = 'listWeek';
			calendarOptions.value.initialView = 'listWeek';
			api.changeView('listWeek');
		}
		return;
	}

	const tabletAllowedViews: CalendarViewName[] = ['timeGridWeek', 'timeGridDay', 'listWeek'];
	const shouldResetToDefault =
		currentView === 'listWeek' ||
		(nextScreen === 'tablet' && !tabletAllowedViews.includes(currentView));

	if (shouldResetToDefault) {
		preferredView.value = nextDefaultView;
		calendarOptions.value.initialView = nextDefaultView;
		api.changeView(nextDefaultView);
	}
}

onMounted(async () => {
	const p = await fetchPrefs();
	if (p) {
		hiddenDays.value = p.weekendDays && p.weekendDays.length ? p.weekendDays : [0, 6];
		slotMin.value = p.defaultSlotMin || '07:00:00';
		slotMax.value = p.defaultSlotMax || '17:00:00';
		if (!showWeekends.value) {
			calendarOptions.value.hiddenDays = hiddenDays.value;
		}
		if (!showFullDay.value) {
			calendarOptions.value.slotMinTime = slotMin.value;
			calendarOptions.value.slotMaxTime = slotMax.value;
		}
	}
	syncCalendarTimezone();
	applyResponsiveCalendarLayout();
});

function handleDatesSet(arg: DatesSetArg) {
	setRange(arg.startStr, arg.endStr);
}

function handleRefresh() {
	refresh({ force: true, reason: 'manual' });
}

const sourcePalette: Record<CalendarSource, { label: string; dot: string; active: string }> = {
	student_group: {
		label: 'Class',
		dot: 'if-pill__dot--scheduled',
		active: 'if-pill--class',
	},
	meeting: {
		label: 'Meeting',
		dot: 'if-pill__dot--scheduled',
		active: 'if-pill--meeting',
	},
	school_event: {
		label: 'School',
		dot: 'if-pill__dot--scheduled',
		active: 'if-pill--school',
	},
	staff_holiday: {
		label: 'Holidays',
		dot: 'if-pill__dot--holiday',
		active: 'if-pill--holiday',
	},
};

const sourceChips = computed(() =>
	Object.entries(sourcePalette).map(([id, palette]) => {
		const sourceId = id as CalendarSource;
		return {
			id: sourceId,
			label: palette.label,
			active: activeSources.value.has(sourceId),
			count: counts.value?.[sourceId] ?? 0,
			dotClass: activeSources.value.has(sourceId) ? palette.dot : 'if-pill__dot--muted',
			activeClass: palette.active,
		};
	})
);

const lastUpdatedLabel = computed(() => {
	if (!lastUpdated.value) return '';
	const delta = Date.now() - lastUpdated.value;
	if (delta < 60_000) return 'just now';
	const minutes = Math.floor(delta / 60_000);
	if (minutes < 60) return `${minutes} min ago`;
	const hours = Math.floor(minutes / 60);
	return `${hours} hr${hours === 1 ? '' : 's'} ago`;
});

function toggleChip(id: CalendarSource) {
	toggleSource(id);
}

/**
 * Overlay stack:
 * - schedule calendar never mounts event dialogs
 * - we pass IDs only; overlays fetch and own their data
 */
const overlay = useOverlayStack();

function extractMeetingName(eventId?: string | null) {
	if (!eventId) return null;
	const [prefix, ...rest] = eventId.split('::');
	if (prefix !== 'meeting' || rest.length === 0) return null;
	return rest.join('::');
}

function extractSchoolEventName(eventId?: string | null) {
	if (!eventId) return null;
	const [prefix, ...rest] = eventId.split('::');
	if (prefix !== 'school_event' || rest.length === 0) return null;
	return rest.join('::');
}

function asMetaText(value: unknown) {
	if (value === null || value === undefined) return '';
	return String(value).trim();
}

function resolveSchoolEventReference(info: EventClickArg) {
	const ext = (info.event.extendedProps || {}) as Record<string, unknown>;
	const meta = (ext.meta && typeof ext.meta === 'object' ? ext.meta : {}) as Record<
		string,
		unknown
	>;
	const referenceType = asMetaText(meta.reference_type ?? ext.reference_type);
	const referenceName = asMetaText(meta.reference_name ?? ext.reference_name);
	return { referenceType, referenceName };
}

function resolveEventId(info: EventClickArg) {
	return (
		info.event.id ||
		(info.event.extendedProps?.id as string | undefined) ||
		(info.event.extendedProps?.event_id as string | undefined) ||
		null
	);
}

function extractClassEventId(rawId?: string | null) {
	if (!rawId) return null;
	if (rawId.startsWith('sg::') || rawId.startsWith('sg-booking::')) {
		return rawId;
	}
	if (rawId.startsWith('sg/')) {
		return rawId.replace('sg/', 'sg::');
	}
	if (rawId.startsWith('student_group::')) {
		return rawId.replace('student_group::', 'sg::');
	}
	return null;
}

// -----------------------------------------------------------------------------
// Legacy org comm quick create (still local in Phase 0)
// -----------------------------------------------------------------------------
const orgCommModal = reactive<{
	open: boolean;
	event: any | null;
}>({
	open: false,
	event: null,
});

function handleOrgCommCreated() {
	orgCommModal.open = false;
}

watch(
	() => orgCommModal.open,
	open => {
		if (!open) orgCommModal.event = null;
	}
);

// -----------------------------------------------------------------------------
// Central event click routing (overlay stack only)
// -----------------------------------------------------------------------------
function handleEventClick(info: EventClickArg) {
	info.jsEvent?.preventDefault();
	info.jsEvent?.stopPropagation();

	const rawSource =
		(info.event.extendedProps?.source as string | undefined) ||
		((info.event as unknown as { source?: string }).source ?? undefined);

	if (rawSource === 'staff_holiday') {
		// Holidays are all-day blocks; no overlay
		return;
	}

	if (rawSource === 'meeting') {
		const meetingName = extractMeetingName(info.event.id);
		if (!meetingName) return;

		overlay.open('meeting-event', { meeting: meetingName });
		return;
	}

	if (rawSource === 'school_event') {
		const schoolEventName = extractSchoolEventName(info.event.id);
		if (!schoolEventName) return;

		const { referenceType, referenceName } = resolveSchoolEventReference(info);
		if (referenceType === 'Applicant Interview' && referenceName) {
			overlay.open('admissions-workspace', {
				interview: referenceName,
				schoolEvent: schoolEventName,
			});
			return;
		}

		overlay.open('school-event', { event: schoolEventName });
		return;
	}

	if (rawSource === 'student_group') {
		const rawId = resolveEventId(info);
		const eventId = extractClassEventId(rawId);
		if (!eventId) return;

		// NOTE: requires OverlayType to include 'class-event'
		overlay.open('class-event', { eventId });
	}
}

const cleanupFns: Array<() => void> = [];
let intervalHandle: number | null = null;
let disposeCalendarInvalidate: (() => void) | null = null;

function maybeAutoRefresh(reason: 'interval' | 'visibility') {
	if (!lastUpdated.value) {
		refresh({ reason, force: false });
		return;
	}
	const stale = Date.now() - (lastUpdated.value ?? 0);
	if (stale > refreshInterval.value) {
		refresh({ reason, force: false });
	}
}

function setupIntervals() {
	intervalHandle = window.setInterval(() => maybeAutoRefresh('interval'), refreshInterval.value);
	const onVisibility = () => {
		if (document.visibilityState === 'visible') {
			maybeAutoRefresh('visibility');
		}
	};
	document.addEventListener('visibilitychange', onVisibility);
	cleanupFns.push(() => document.removeEventListener('visibilitychange', onVisibility));
}

function setupCalendarHeightListener() {
	if (typeof window === 'undefined') return;
	const handleResize = () => applyResponsiveCalendarLayout();
	window.addEventListener('resize', handleResize);
	cleanupFns.push(() => window.removeEventListener('resize', handleResize));
}

onMounted(() => {
	setupIntervals();
	setupCalendarHeightListener();
	disposeCalendarInvalidate = uiSignals.subscribe(SIGNAL_CALENDAR_INVALIDATE, () => {
		refresh({ force: true, reason: 'manual' });
	});
});

onBeforeUnmount(() => {
	cleanupFns.forEach(fn => fn());
	if (intervalHandle) clearInterval(intervalHandle);
	if (disposeCalendarInvalidate) disposeCalendarInvalidate();
});
</script>

<style scoped>
.schedule-calendar__header {
	display: grid;
	grid-template-columns: minmax(0, 1fr) auto;
	align-items: end;
	column-gap: 1rem;
	row-gap: 0.25rem;
}

.schedule-calendar__header-meta {
	justify-self: end;
	text-align: right;
	white-space: nowrap;
}

.schedule-calendar__filters {
	display: flex;
	flex-direction: column;
	gap: 0.75rem;
}

@media (max-width: 639px) {
	.schedule-calendar__header {
		grid-template-columns: minmax(0, 1fr);
	}

	.schedule-calendar__header-meta {
		justify-self: start;
		text-align: left;
		white-space: normal;
	}
}

@media (min-width: 1024px) {
	.schedule-calendar__filters {
		flex-direction: row;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.75rem 1rem;
	}

	.schedule-calendar__filter-group {
		flex: 0 1 auto;
	}

	.schedule-calendar__filter-group--controls {
		margin-right: 0.5rem;
	}
}
</style>
