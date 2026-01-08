<!-- ifitwala_ed/ui-spa/src/components/calendar/ScheduleCalendar.vue -->
<template>
	<div class="relative">
		<section class="paper-card schedule-card p-6">
			<header
				class="flex flex-col gap-4 border-b border-[rgb(var(--border-rgb)/0.9)] pb-4 md:flex-row md:items-center md:justify-between"
			>
				<div>
					<h2 class="type-h2">
						Your upcoming commitments
					</h2>
					<p class="type-meta">
						{{ subtitle }}
					</p>
				</div>

				<div class="flex items-center gap-3 type-caption">
					<span v-if="lastUpdatedLabel">
						Updated {{ lastUpdatedLabel }}
					</span>
					<button
						class="inline-flex items-center gap-2 rounded-full border border-[rgb(var(--border-rgb)/0.95)]
						       bg-white px-3 py-1.5 type-button-label text-ink/70
						       shadow-soft transition hover:border-[rgb(var(--leaf-rgb)/0.9)] hover:text-leaf"
						@click="handleRefresh"
					>
						<FeatherIcon name="refresh-cw" class="h-4 w-4" />
						Refresh
					</button>
				</div>
			</header>

			<!-- Chips row -->
			<div class="mt-4 flex flex-wrap items-center gap-3">
				<!-- Weekend / Full-day toggles -->
				<div class="mr-auto flex items-center gap-3">
					<button
						class="inline-flex items-center gap-2 rounded-full border px-3 py-1.5 type-button-label transition"
						:class="
							showWeekends
								? 'border-[rgb(var(--border-rgb)/0.9)] bg-white text-ink/80'
								: 'border-[rgb(var(--leaf-rgb)/0.9)] bg-[rgb(var(--leaf-rgb)/0.08)] text-canopy'
						"
						@click="showWeekends = !showWeekends"
					>
						<FeatherIcon name="calendar" class="h-4 w-4" />
						{{ showWeekends ? 'Show all days' : 'Hide weekends' }}
					</button>
					<button
						class="inline-flex items-center gap-2 rounded-full border px-3 py-1.5 type-button-label transition"
						:class="
							showFullDay
								? 'border-[rgb(var(--border-rgb)/0.9)] bg-white/90 text-ink/80'
								: 'border-[rgb(var(--leaf-rgb)/0.9)] bg-[rgb(var(--leaf-rgb)/0.08)] text-canopy'
						"
						@click="showFullDay = !showFullDay"
					>
						<FeatherIcon name="clock" class="h-4 w-4" />
						{{ showFullDay ? 'Full day on' : 'Default hours' }}
					</button>
				</div>

				<!-- Source chips -->
				<button
					v-for="chip in sourceChips"
					:key="chip.id"
					type="button"
					class="group inline-flex items-center gap-2 rounded-full border px-3 py-1.5 type-button-label transition"
					:class="
						chip.active
							? chip.activeClass
							: 'border-[rgb(var(--border-rgb)/0.9)] bg-white/80 text-ink/70 hover:border-[rgb(var(--border-rgb)/1)]'
					"
					@click="toggleChip(chip.id)"
				>
					<span
						class="mr-1 inline-flex h-2.5 w-2.5 rounded-full"
						:class="chip.dotClass"
					></span>
					{{ chip.label }}
					<span
						class="rounded-full bg-white/70 px-2 py-0.5 type-badge-label text-ink/70"
					>
						{{ chip.count }}
					</span>
				</button>
			</div>

			<!-- Calendar shell with rounded corners + clipping and breathing room -->
			<div
				class="relative mt-6 overflow-hidden rounded-2xl border border-[rgb(var(--border-rgb)/0.95)]
				       bg-white shadow-soft p-3 sm:p-4"
			>
				<FullCalendar
					ref="calendarRef"
					:options="calendarOptions"
					class="calendar-shell"
				/>

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
				class="mt-4 rounded-2xl border border-[rgb(var(--flame-rgb)/0.25)]
				       bg-[rgb(var(--flame-rgb)/0.05)] px-4 py-3 type-body text-flame"
			>
				{{ error }}
			</div>
			<div
				v-else-if="isEmpty"
				class="mt-4 rounded-2xl border border-dashed border-[rgb(var(--border-rgb)/0.9)]
				       bg-[rgb(var(--sky-rgb)/0.45)] px-4 py-6 text-center type-body text-ink/70"
			>
				Nothing scheduled for this range. Enjoy the calm or adjust the view to a different week.
			</div>
		</section>

		<!-- ============================================================
		     LEGACY FRAPPE-UI MODAL (PHASE 0) — still OK
		     (We did NOT refactor this to overlay stack yet.)
		     ============================================================ -->
		<OrgCommunicationQuickCreateModal
			v-model="orgCommModal.open"
			:event="orgCommModal.event"
			@created="handleOrgCommCreated"
		/>

		<!-- ============================================================
		     PHASE 0 RULE:
		     - Meeting / School Event / Class Event are OVERLAYS (overlay stack).
		     - Create-task is also an OVERLAY (overlay stack).
		     - This page does NOT mount any HeadlessUI event dialogs anymore.
		     ============================================================ -->
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
 *
 * Still legacy (Phase 0):
 *  - OrgCommunicationQuickCreateModal remains a local Frappe-UI modal for now.
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

import OrgCommunicationQuickCreateModal from '@/components/calendar/OrgCommunicationQuickCreateModal.vue';

// ✅ Overlay stack (single renderer via OverlayHost teleported to #overlay-root)
import { useOverlayStack } from '@/composables/useOverlayStack';

// Vendor local placeholder styles to unblock build
import '@/styles/fullcalendar/core.css';
import '@/styles/fullcalendar/daygrid.css';
import '@/styles/fullcalendar/timegrid.css';
import '@/styles/fullcalendar/list.css';

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

function nowProvider() {
	return new Date();
}

function syncCalendarTimezone() {
	// DIAG: force local time zone (no plugin needed)
	const tz = 'local';

	calendarOptions.value.timeZone = tz;
	calendarOptions.value.now = nowProvider;

	const api = calendarRef.value?.getApi();
	if (api) {
		api.setOption('timeZone', tz);
		api.setOption('now', nowProvider);
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
	return total ? `${total} event${total === 1 ? '' : 's'} in view` : 'Nothing scheduled in this range';
});

const calendarRef = ref<InstanceType<typeof FullCalendar> | null>(null);

const prefersCompact =
	typeof window !== 'undefined' && typeof window.matchMedia === 'function'
		? window.matchMedia('(max-width: 768px)').matches
		: false;

const preferredView = ref<'timeGridWeek' | 'listWeek'>(prefersCompact ? 'listWeek' : 'timeGridWeek');
const calendarHeight = ref<number>(computeCalendarHeight());

const calendarOptions = ref({
	plugins: [dayGridPlugin, timeGridPlugin, listPlugin],
	initialView: preferredView.value,
	height: calendarHeight.value,
	headerToolbar: {
		left: 'prev,next today',
		center: 'title',
		right: 'dayGridMonth,timeGridWeek,timeGridDay,listWeek',
	},
	slotDuration: '00:30:00',
	slotMinTime: slotMin.value,
	slotMaxTime: slotMax.value,
	dayMaxEvents: true,
	displayEventTime: false,
	navLinks: false,
	nowIndicator: true,
	events: events.value,
	timeZone: systemTimezone.value,
	now: nowProvider(),
	hiddenDays: hiddenDays.value,
	datesSet: (arg: DatesSetArg) => handleDatesSet(arg),
	eventDisplay: 'block',
	eventClick: (info: EventClickArg) => handleEventClick(info),
});

watch(events, (val) => {
	calendarOptions.value.events = val;
});

watch(timezone, (tz) => {
	systemTimezone.value = tz || resolveSystemTimezone();
	syncCalendarTimezone();
});

watch(systemTimezone, () => {
	syncCalendarTimezone();
});

watch(showWeekends, (val) => {
	calendarOptions.value.hiddenDays = val ? [] : hiddenDays.value;
});

watch(showFullDay, (val) => {
	calendarOptions.value.slotMinTime = val ? '00:00:00' : slotMin.value;
	calendarOptions.value.slotMaxTime = val ? '24:00:00' : slotMax.value;
});

function computeCalendarHeight(): number {
	if (typeof window === 'undefined') return 640;
	const viewportHeight = window.innerHeight || 0;
	const target = Math.round(viewportHeight * 0.65);
	return Math.max(520, Math.min(target, 760));
}

function applyCalendarHeight() {
	const nextHeight = computeCalendarHeight();
	calendarHeight.value = nextHeight;
	calendarOptions.value.height = nextHeight;
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
	applyCalendarHeight();
});

function handleDatesSet(arg: DatesSetArg) {
	setRange(arg.startStr, arg.endStr);
}

function handleRefresh() {
	refresh({ force: true, reason: 'manual' });
}

const sourcePalette: Record<CalendarSource, { label: string; dot: string; active: string }> = {
	student_group: {
		label: 'Classes',
		dot: 'bg-blue-500',
		active: 'border-blue-200 bg-blue-50 text-blue-700',
	},
	meeting: {
		label: 'Meetings',
		dot: 'bg-violet-500',
		active: 'border-violet-200 bg-violet-50 text-violet-700',
	},
	school_event: {
		label: 'School Events',
		dot: 'bg-emerald-500',
		active: 'border-emerald-200 bg-emerald-50 text-emerald-700',
	},
	staff_holiday: {
		label: 'Holidays',
		dot: 'bg-slate-500',
		active: 'border-slate-200 bg-slate-50 text-slate-700',
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
			dotClass: activeSources.value.has(sourceId) ? palette.dot : 'bg-slate-300',
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
	(open) => {
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

// -----------------------------------------------------------------------------
// Responsiveness / auto-refresh / resize (unchanged)
// -----------------------------------------------------------------------------
function setupMediaWatcher() {
	if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return;
	const mq = window.matchMedia('(max-width: 768px)');
	const handler = (event: MediaQueryListEvent) => {
		const newView = event.matches ? 'listWeek' : 'timeGridWeek';
		preferredView.value = newView;
		const calendarApi = calendarRef.value?.getApi?.();
		calendarApi?.changeView(newView);
	};
	mq.addEventListener('change', handler);
	cleanupFns.push(() => mq.removeEventListener('change', handler));
}

const cleanupFns: Array<() => void> = [];
let intervalHandle: number | null = null;

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
	const handleResize = () => applyCalendarHeight();
	window.addEventListener('resize', handleResize);
	cleanupFns.push(() => window.removeEventListener('resize', handleResize));
}

onMounted(() => {
	setupMediaWatcher();
	setupIntervals();
	setupCalendarHeightListener();
});

onBeforeUnmount(() => {
	cleanupFns.forEach((fn) => fn());
	if (intervalHandle) clearInterval(intervalHandle);
});
</script>
