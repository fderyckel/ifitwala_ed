<template>
	<section class="w-full rounded-3xl border border-slate-200 bg-white/95 p-6 shadow-sm backdrop-blur">
		<header class="flex flex-col gap-4 border-b border-slate-100 pb-4 md:flex-row md:items-center md:justify-between">
			<div>
				<p class="text-sm uppercase tracking-[0.2em] text-slate-400">Schedule</p>
				<h2 class="text-2xl font-semibold text-slate-900">Your upcoming commitments</h2>
				<p class="text-sm text-slate-500">{{ subtitle }}</p>
			</div>
			<div class="flex items-center gap-3 text-xs text-slate-500">
				<span v-if="lastUpdatedLabel">Updated {{ lastUpdatedLabel }}</span>
				<button
					class="inline-flex items-center gap-2 rounded-full border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 transition hover:border-blue-500 hover:text-blue-600"
					@click="handleRefresh"
				>
					<FeatherIcon name="refresh-cw" class="h-4 w-4" />
					Refresh
				</button>
			</div>
		</header>

		<div class="mt-4 flex flex-wrap items-center gap-3">
			<!-- Weekend / Full-day toggles -->
			<div class="mr-auto flex items-center gap-3 text-xs">
				<button
					class="inline-flex items-center gap-2 rounded-full border px-3 py-1.5 font-medium transition"
					:class="showWeekends ? 'border-slate-300 text-slate-700 bg-white' : 'border-blue-200 bg-blue-50 text-blue-700'"
					@click="showWeekends = !showWeekends"
				>
					<FeatherIcon name="calendar" class="h-4 w-4" />
					{{ showWeekends ? 'Show all days' : 'Hide weekends' }}
				</button>
				<button
					class="inline-flex items-center gap-2 rounded-full border px-3 py-1.5 font-medium transition"
					:class="showFullDay ? 'border-slate-300 text-slate-700 bg-white' : 'border-emerald-200 bg-emerald-50 text-emerald-700'"
					@click="showFullDay = !showFullDay"
				>
					<FeatherIcon name="clock" class="h-4 w-4" />
					{{ showFullDay ? 'Full day on' : 'Default hours' }}
				</button>
			</div>
			<button
				v-for="chip in sourceChips"
				:key="chip.id"
				type="button"
				class="group inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-semibold transition"
				:class="chip.active ? chip.activeClass : 'border-slate-200 text-slate-500 hover:border-slate-300'"
				@click="toggleChip(chip.id)"
			>
				<span class="mr-1 inline-flex h-2.5 w-2.5 rounded-full" :class="chip.dotClass"></span>
				{{ chip.label }}
				<span class="rounded-full bg-white/60 px-2 py-0.5 text-[10px] font-semibold text-slate-500">{{ chip.count }}</span>
			</button>
		</div>

		<div class="mt-6 relative">
			<FullCalendar ref="calendarRef" :options="calendarOptions" class="rounded-2xl border border-slate-100" />

			<div
				v-if="loading"
				class="absolute inset-0 z-10 flex items-center justify-center rounded-2xl bg-white/70 backdrop-blur"
			>
				<div class="flex items-center gap-2 text-sm font-medium text-slate-500">
					<FeatherIcon name="loader" class="h-4 w-4 animate-spin" />
					Loading calendar…
				</div>
			</div>
		</div>

		<div v-if="error" class="mt-4 rounded-2xl border border-rose-100 bg-rose-50 px-4 py-3 text-sm text-rose-700">
			{{ error }}
		</div>
		<div
			v-else-if="isEmpty"
			class="mt-4 rounded-2xl border border-dashed border-slate-200 px-4 py-6 text-center text-sm text-slate-500"
		>
			Nothing scheduled for this range. Enjoy the calm or adjust the view to a different week.
		</div>
	</section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import FullCalendar from '@fullcalendar/vue3';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import listPlugin from '@fullcalendar/list';
import { DatesSetArg } from '@fullcalendar/core';
import { FeatherIcon } from 'frappe-ui';

import { CalendarSource, useCalendarEvents } from '@/composables/useCalendarEvents';
import { useCalendarPrefs } from '@/composables/useCalendarPrefs';
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

const calendarOptions = ref({
	plugins: [dayGridPlugin, timeGridPlugin, listPlugin],
	initialView: preferredView.value,
	height: 'auto',
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
	timeZone: timezone.value,
	hiddenDays: hiddenDays.value,
	datesSet: (arg: DatesSetArg) => handleDatesSet(arg),
	eventDisplay: 'block',
});

watch(events, (val) => {
	calendarOptions.value.events = val;
});

watch(timezone, (tz) => {
	calendarOptions.value.timeZone = tz;
});

watch(showWeekends, (val) => {
	calendarOptions.value.hiddenDays = val ? [] : hiddenDays.value;
});

watch(showFullDay, (val) => {
	calendarOptions.value.slotMinTime = val ? '00:00:00' : slotMin.value;
	calendarOptions.value.slotMaxTime = val ? '24:00:00' : slotMax.value;
});

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

onMounted(() => {
	setupMediaWatcher();
	setupIntervals();
});

onBeforeUnmount(() => {
	cleanupFns.forEach((fn) => fn());
	if (intervalHandle) {
		clearInterval(intervalHandle);
	}
});
</script>

<style scoped>
:global(.fc) {
	font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

:global(.fc-toolbar-title) {
	font-size: 1rem;
	font-weight: 600;
	color: #0f172a;
}

:global(.fc-button) {
	border-radius: 9999px !important;
	border: 1px solid #e2e8f0 !important;
	background: #fff !important;
	color: #0f172a !important;
	padding: 0.3rem 0.75rem !important;
	font-size: 0.8rem !important;
	font-weight: 500 !important;
}

:global(.fc-button-active),
:global(.fc-button-primary:not(:disabled).fc-button-active) {
	border-color: #2563eb !important;
	background: #2563eb !important;
	color: #fff !important;
}

:global(.fc-daygrid-event),
:global(.fc-timegrid-event) {
	border-radius: 0.85rem !important;
	padding: 0.3rem 0.45rem !important;
	border: none !important;
}

:global(.fc-list-event-dot) {
	border-color: transparent !important;
}
</style>
