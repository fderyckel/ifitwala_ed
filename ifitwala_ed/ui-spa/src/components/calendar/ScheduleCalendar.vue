<!-- ifitwala_ed/ui-spa/src/components/calendar -->
<template>
	<div class="relative">
		<section class="paper-card schedule-card p-6">
			<header
				class="flex flex-col gap-4 border-b border-[rgb(var(--border-rgb) / 0.9)] pb-4 md:flex-row md:items-center md:justify-between"
			>
				<div>
					<p class="text-sm uppercase tracking-[0.2em] text-canopy">
						Schedule
					</p>
					<h2 class="text-2xl font-semibold text-canopy">
						Your upcoming commitments
					</h2>
					<p class="text-sm text-[rgb(var(--slate-rgb) / 0.75)]">
						{{ subtitle }}
					</p>
				</div>

				<div class="flex items-center gap-3 text-xs text-[rgb(var(--slate-rgb) / 0.7)]">
					<span v-if="lastUpdatedLabel">
						Updated {{ lastUpdatedLabel }}
					</span>
					<button
						class="inline-flex items-center gap-2 rounded-full border border-[rgb(var(--border-rgb) / 0.95)]
						       bg-white px-3 py-1.5 text-xs font-medium text-[rgb(var(--slate-rgb) / 0.9)]
						       shadow-soft transition hover:border-[rgb(var(--leaf-rgb) / 0.9)] hover:text-[rgb(var(--leaf-rgb))]"
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
				<div class="mr-auto flex items-center gap-3 text-xs">
					<button
						class="inline-flex items-center gap-2 rounded-full border px-3 py-1.5 font-medium transition"
						:class="
							showWeekends
								? 'border-[rgb(var(--border-rgb) / 0.9)] bg-white text-[rgb(var(--slate-rgb) / 0.9)]'
								: 'border-[rgb(var(--leaf-rgb) / 0.9)] bg-[rgb(var(--leaf-rgb) / 0.08)] text-[rgb(var(--canopy-rgb))]'
						"
						@click="showWeekends = !showWeekends"
					>
						<FeatherIcon name="calendar" class="h-4 w-4" />
						{{ showWeekends ? 'Show all days' : 'Hide weekends' }}
					</button>
					<button
						class="inline-flex items-center gap-2 rounded-full border px-3 py-1.5 font-medium transition"
						:class="
							showFullDay
								? 'border-[rgb(var(--border-rgb) / 0.9)] bg-white/90 text-[rgb(var(--slate-rgb) / 0.9)]'
								: 'border-[rgb(var(--leaf-rgb) / 0.9)] bg-[rgb(var(--leaf-rgb) / 0.08)] text-[rgb(var(--canopy-rgb))]'
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
					class="group inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-semibold transition"
					:class="
						chip.active
							? chip.activeClass
							: 'border-[rgb(var(--border-rgb) / 0.9)] bg-white/80 text-[rgb(var(--slate-rgb) / 0.7)] hover:border-[rgb(var(--border-rgb) / 1)]'
					"
					@click="toggleChip(chip.id)"
				>
					<span
						class="mr-1 inline-flex h-2.5 w-2.5 rounded-full"
						:class="chip.dotClass"
					></span>
					{{ chip.label }}
					<span
						class="rounded-full bg-white/70 px-2 py-0.5 text-[10px] font-semibold text-[rgb(var(--slate-rgb) / 0.7)]"
					>
						{{ chip.count }}
					</span>
				</button>
			</div>

			<!-- Calendar shell with rounded corners + clipping and breathing room -->
			<div
				class="mt-6 overflow-hidden rounded-2xl border border-[rgb(var(--border-rgb) / 0.95)]
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
					<div class="flex items-center gap-2 text-sm font-medium text-[rgb(var(--slate-rgb) / 0.8)]">
						<FeatherIcon name="loader" class="h-4 w-4 animate-spin" />
						Loading calendar…
					</div>
				</div>
			</div>

			<!-- Empty / error messages -->
			<div
				v-if="error"
				class="mt-4 rounded-2xl border border-[rgb(var(--flame-rgb) / 0.25)]
				       bg-[rgb(var(--flame-rgb) / 0.05)] px-4 py-3 text-sm text-[rgb(var(--flame-rgb))]"
			>
				{{ error }}
			</div>
			<div
				v-else-if="isEmpty"
				class="mt-4 rounded-2xl border border-dashed border-[rgb(var(--border-rgb) / 0.9)]
				       bg-[rgb(var(--sky-rgb) / 0.45)] px-4 py-6 text-center text-sm text-[rgb(var(--slate-rgb) / 0.8)]"
			>
				Nothing scheduled for this range. Enjoy the calm or adjust the view to a different week.
			</div>
		</section>

		<!-- Modals -->
		<MeetingEventModal
			:open="meetingModal.open"
			:loading="meetingModal.loading"
			:error="meetingModal.error"
			:meeting="meetingModal.data"
			@close="closeMeetingModal"
		/>
		<SchoolEventModal
			:open="schoolEventModal.open"
			:loading="schoolEventModal.loading"
			:error="schoolEventModal.error"
			:event="schoolEventModal.data"
			@close="closeSchoolEventModal"
		/>
		<ClassEventModal
			:open="classEventModal.open"
			:loading="classEventModal.loading"
			:error="classEventModal.error"
			:event="classEventModal.data"
			@close="closeClassEventModal"
		/>
	</div>
</template>


<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import FullCalendar from '@fullcalendar/vue3';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import listPlugin from '@fullcalendar/list';
import { DatesSetArg, EventClickArg } from '@fullcalendar/core';
import { FeatherIcon } from 'frappe-ui';

import { CalendarSource, useCalendarEvents } from '@/composables/useCalendarEvents';
import { useCalendarPrefs } from '@/composables/useCalendarPrefs';
import { api } from '@/api/client';
import MeetingEventModal from '@/components/calendar/MeetingEventModal.vue';
import SchoolEventModal from '@/components/calendar/SchoolEventModal.vue';
import ClassEventModal from '@/components/calendar/ClassEventModal.vue';
import type { MeetingDetails } from '@/components/calendar/meetingTypes';
import type { SchoolEventDetails } from '@/components/calendar/schoolEventTypes';
import type { ClassEventDetails } from '@/components/calendar/classEventTypes';
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

const resolveSystemTimezone = () =>
	((window as any)?.frappe?.boot?.time_zone ||
		(window as any)?.frappe?.boot?.timezone ||
		timezone.value ||
		Intl.DateTimeFormat().resolvedOptions().timeZone ||
		'UTC') as string;
const systemTimezone = ref<string>(resolveSystemTimezone());
const nowInSystemTz = () => {
	const parts = new Intl.DateTimeFormat('en-US', {
		timeZone: systemTimezone.value,
		year: 'numeric',
		month: '2-digit',
		day: '2-digit',
		hour: '2-digit',
		minute: '2-digit',
		second: '2-digit',
		hour12: false,
	}).formatToParts(new Date());
	const get = (type: string) => parts.find((p) => p.type === type)?.value ?? '0';
	return new Date(
		Date.UTC(
			Number(get('year')),
			Number(get('month')) - 1,
			Number(get('day')),
			Number(get('hour')),
			Number(get('minute')),
			Number(get('second'))
		)
	);
};

async function loadSystemTimezone() {
	try {
		const res = await fetch('/api/resource/System Settings?fields=["time_zone"]', {
			credentials: 'include',
		});
		const json = await res.json();
		const tz = json?.data?.time_zone;
		if (typeof tz === 'string' && tz.trim()) {
			systemTimezone.value = tz.trim();
		}
	} catch (err) {
		console.warn('[ScheduleCalendar] Failed to load system timezone, falling back:', err);
	}
}

function syncCalendarTimezone() {
	const now = nowInSystemTz();
	calendarOptions.value.timeZone = systemTimezone.value;
	calendarOptions.value.now = now;
	const api = calendarRef.value?.getApi();
	if (api) {
		api.setOption('timeZone', systemTimezone.value);
		api.setOption('now', now);
		api.render();
	}
}

// Calendar preferences and toggles
const { prefs, fetch: fetchPrefs } = useCalendarPrefs();
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
	slotMinTime: slotMin.value,
	slotMaxTime: slotMax.value,
	dayMaxEvents: true,
	navLinks: false,
	nowIndicator: true,
	events: events.value,
	timeZone: systemTimezone.value,
	now: nowInSystemTz(),
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
	await loadSystemTimezone();
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
	frappe_event: {
		label: 'Frappe Events',
		dot: 'bg-amber-500',
		active: 'border-amber-200 bg-amber-50 text-amber-700',
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

const meetingModal = reactive<{
	open: boolean;
	loading: boolean;
	error: string | null;
	data: MeetingDetails | null;
}>({
	open: false,
	loading: false,
	error: null,
	data: null,
});

let meetingRequestSeq = 0;

function closeMeetingModal() {
	meetingModal.open = false;
	meetingModal.data = null;
	meetingModal.error = null;
}

async function openMeetingModal(meetingName: string) {
	meetingModal.open = true;
	meetingModal.loading = true;
	meetingModal.error = null;
	meetingModal.data = null;
	const seq = ++meetingRequestSeq;
	try {
		const payload = (await api('ifitwala_ed.api.calendar.get_meeting_details', {
			meeting: meetingName,
		})) as MeetingDetails;
		if (seq === meetingRequestSeq) {
			meetingModal.data = payload;
		}
	} catch (err) {
		if (seq === meetingRequestSeq) {
			meetingModal.error =
				err instanceof Error ? err.message : 'Unable to load meeting details right now.';
		}
	} finally {
		if (seq === meetingRequestSeq) {
			meetingModal.loading = false;
		}
	}
}

function extractMeetingName(eventId?: string | null) {
	if (!eventId) return null;
	const [prefix, ...rest] = eventId.split('::');
	if (prefix !== 'meeting' || rest.length === 0) return null;
	return rest.join('::');
}

function handleEventClick(info: EventClickArg) {
	info.jsEvent?.preventDefault();
	info.jsEvent?.stopPropagation();

	const rawSource =
		(info.event.extendedProps?.source as string | undefined) ||
		((info.event as unknown as { source?: string }).source ?? undefined);
	if (rawSource === 'meeting') {
		closeSchoolEventModal();
		closeClassEventModal();
		const meetingName = extractMeetingName(info.event.id);
		if (!meetingName) {
			return;
		}
		openMeetingModal(meetingName);
		return;
	}

	if (rawSource === 'school_event') {
		closeMeetingModal();
		closeClassEventModal();
		const schoolEventName = extractSchoolEventName(info.event.id);
		if (!schoolEventName) {
			return;
		}
		openSchoolEventModal(schoolEventName);
		return;
	}

	if (rawSource === 'student_group') {
		closeMeetingModal();
		closeSchoolEventModal();
		const eventId = resolveEventId(info);
		openClassEventModal(eventId);
	}
}

const schoolEventModal = reactive<{
	open: boolean;
	loading: boolean;
	error: string | null;
	data: SchoolEventDetails | null;
}>({
	open: false,
	loading: false,
	error: null,
	data: null,
});

let schoolEventRequestSeq = 0;

function closeSchoolEventModal() {
	schoolEventModal.open = false;
	schoolEventModal.data = null;
	schoolEventModal.error = null;
}

async function openSchoolEventModal(eventName: string) {
	schoolEventModal.open = true;
	schoolEventModal.loading = true;
	schoolEventModal.error = null;
	schoolEventModal.data = null;
	const seq = ++schoolEventRequestSeq;
	try {
		const payload = (await api('ifitwala_ed.api.calendar.get_school_event_details', {
			event: eventName,
		})) as SchoolEventDetails;
		if (seq === schoolEventRequestSeq) {
			schoolEventModal.data = payload;
		}
	} catch (err) {
		if (seq === schoolEventRequestSeq) {
			schoolEventModal.error =
				err instanceof Error ? err.message : 'Unable to load event details right now.';
		}
	} finally {
		if (seq === schoolEventRequestSeq) {
			schoolEventModal.loading = false;
		}
	}
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

const classEventModal = reactive<{
	open: boolean;
	loading: boolean;
	error: string | null;
	data: ClassEventDetails | null;
}>({
	open: false,
	loading: false,
	error: null,
	data: null,
});

let classEventRequestSeq = 0;

function closeClassEventModal() {
	classEventModal.open = false;
	classEventModal.data = null;
	classEventModal.error = null;
}

async function openClassEventModal(eventId: string | null | undefined) {
	const resolvedId = extractClassEventId(eventId);
	if (!resolvedId) {
		classEventModal.open = true;
		classEventModal.loading = false;
		classEventModal.error = 'Could not determine which class was clicked. Please refresh and try again.';
		return;
	}
	classEventModal.open = true;
	classEventModal.loading = true;
	classEventModal.error = null;
	classEventModal.data = null;
	const seq = ++classEventRequestSeq;
	try {
		const payload = (await api('ifitwala_ed.api.calendar.get_student_group_event_details', {
			event_id: resolvedId,
		})) as ClassEventDetails;
		if (seq === classEventRequestSeq) {
			classEventModal.data = payload;
		}
	} catch (err) {
		if (seq === classEventRequestSeq) {
			classEventModal.error =
				err instanceof Error ? err.message : 'Unable to load class details right now.';
		}
	} finally {
		if (seq === classEventRequestSeq) {
			classEventModal.loading = false;
		}
	}
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
	if (intervalHandle) {
		clearInterval(intervalHandle);
	}
});
</script>
