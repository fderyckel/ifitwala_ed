<!-- ifitwala_ed/ui-spa/src/components/calendar/StudentCalendar.vue -->
<template>
	<div class="relative">
		<section class="paper-card schedule-card p-6">
			<header
				class="flex flex-col gap-4 border-b border-[rgb(var(--border-rgb)/0.9)] pb-4 md:flex-row md:items-center md:justify-between"
			>
				<div>
					<h2 class="type-h2">My Calendar</h2>
					<p class="type-meta">{{ subtitle }}</p>
				</div>

				<div class="flex items-center gap-3 type-caption">
					<button class="if-action type-button-label" @click="handleRefresh">
						<FeatherIcon name="refresh-cw" class="h-4 w-4" :class="{ 'animate-spin': calendarResource.loading }" />
						Refresh
					</button>
				</div>
			</header>

			<div class="mt-4 flex flex-wrap items-center gap-3">
				<div class="mr-auto flex items-center gap-3">
					<button class="if-pill type-button-label" :class="showWeekends ? 'if-pill--off' : 'if-pill--on'" @click="showWeekends = !showWeekends">
						<FeatherIcon name="calendar" class="h-4 w-4" />
						{{ showWeekends ? 'Show all days' : 'Hide weekends' }}
					</button>
				</div>

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
					<span class="if-pill__count type-badge-label">{{ chip.count }}</span>
				</button>
			</div>

			<div
				class="relative mt-6 overflow-hidden rounded-2xl border border-[rgb(var(--border-rgb)/0.95)]
				       bg-white shadow-soft p-3 sm:p-4"
			>
				<FullCalendar ref="calendarRef" :options="calendarOptions" class="calendar-shell" />

				<div v-if="calendarResource.loading" class="absolute inset-0 z-10 flex items-center justify-center rounded-3xl bg-white/70 backdrop-blur">
					<div class="flex items-center gap-2 type-body-strong text-ink/70">
						<FeatherIcon name="loader" class="h-4 w-4 animate-spin" />
						Loading calendar…
					</div>
				</div>
			</div>

			<div
				v-if="interactionError"
				class="mt-4 rounded-2xl border border-[rgb(var(--flame-rgb)/0.25)]
				       bg-[rgb(var(--flame-rgb)/0.05)] px-4 py-3 type-body text-flame"
			>
				{{ interactionError }}
			</div>
			<div
				v-if="calendarErrorMessage"
				class="mt-4 rounded-2xl border border-[rgb(var(--flame-rgb)/0.25)]
				       bg-[rgb(var(--flame-rgb)/0.05)] px-4 py-3 type-body text-flame"
			>
				{{ calendarErrorMessage }}
			</div>
			<div
				v-else-if="isEmpty"
				class="mt-4 rounded-2xl border border-dashed border-[rgb(var(--border-rgb)/0.9)]
				       bg-[rgb(var(--sky-rgb)/0.45)] px-4 py-6 text-center type-body text-ink/70"
			>
				Nothing scheduled for this range. Adjust your filters or view another week.
			</div>
		</section>
	</div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import FullCalendar from '@fullcalendar/vue3'
import dayGridPlugin from '@fullcalendar/daygrid'
import timeGridPlugin from '@fullcalendar/timegrid'
import listPlugin from '@fullcalendar/list'
import { DatesSetArg, EventClickArg } from '@fullcalendar/core'
import { FeatherIcon, createResource } from 'frappe-ui'

import { useOverlayStack } from '@/composables/useOverlayStack'

import '@/styles/fullcalendar/core.css'
import '@/styles/fullcalendar/daygrid.css'
import '@/styles/fullcalendar/timegrid.css'
import '@/styles/fullcalendar/list.css'
import '@/styles/fullcalendar/ifitwala-fullcalendar.css'

type StudentCalendarSource = 'student_group' | 'meeting' | 'school_event' | 'holiday'

const props = defineProps<{
	autoRefreshInterval?: number
}>()

const refreshInterval = computed(() => props.autoRefreshInterval ?? 30 * 60 * 1000)

const overlay = useOverlayStack()

const showWeekends = ref(false)
const currentRange = ref<{ start: string; end: string } | null>(null)
const activeSources = ref<Set<StudentCalendarSource>>(new Set(['student_group', 'meeting', 'school_event', 'holiday']))
const interactionError = ref('')

const calendarResource = createResource({
	url: 'ifitwala_ed.api.student_calendar.get_student_calendar',
	makeParams() {
		return {
			from_datetime: currentRange.value?.start,
			to_datetime: currentRange.value?.end,
		}
	},
	auto: false,
	transform: (data: unknown) => {
		if (data && typeof data === 'object' && 'message' in data) {
			return (data as Record<string, unknown>).message
		}
		return data
	},
})

const calendarErrorMessage = computed(() => {
	const err = calendarResource.error
	if (!err) return ''
	if (typeof err === 'string') return err
	if (err instanceof Error) return err.message || 'Unable to load calendar events.'
	if (err && typeof err === 'object' && 'message' in err) {
		const message = typeof err.message === 'string' ? err.message : ''
		return message || 'Unable to load calendar events.'
	}
	return 'Unable to load calendar events.'
})

const allEvents = computed(() => {
	const data = calendarResource.data as { events?: unknown[] } | null | undefined
	return Array.isArray(data?.events) ? data.events : []
})

const filteredEvents = computed(() =>
	allEvents.value.filter((evt) => {
		const source = typeof evt === 'object' && evt && 'source' in evt ? String((evt as Record<string, unknown>).source || '') : ''
		return activeSources.value.has(source as StudentCalendarSource)
	})
)

const counts = computed<Record<StudentCalendarSource, number>>(() => {
	const next: Record<StudentCalendarSource, number> = {
		student_group: 0,
		meeting: 0,
		school_event: 0,
		holiday: 0,
	}

	for (const evt of allEvents.value) {
		const source = typeof evt === 'object' && evt && 'source' in evt ? String((evt as Record<string, unknown>).source || '') : ''
		if (source in next) {
			next[source as StudentCalendarSource] += 1
		}
	}

	return next
})

const subtitle = computed(() => {
	const total = filteredEvents.value.length
	return total ? `${total} event${total === 1 ? '' : 's'} in view` : 'Nothing scheduled in this range'
})

const isEmpty = computed(() => !calendarResource.loading && !calendarErrorMessage.value && filteredEvents.value.length === 0)

const sourcePalette: Record<StudentCalendarSource, { label: string; dot: string; active: string }> = {
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
	holiday: {
		label: 'Holidays',
		dot: 'if-pill__dot--holiday',
		active: 'if-pill--holiday',
	},
}

const sourceChips = computed(() =>
	Object.entries(sourcePalette).map(([id, palette]) => {
		const sourceId = id as StudentCalendarSource
		return {
			id: sourceId,
			label: palette.label,
			active: activeSources.value.has(sourceId),
			count: counts.value[sourceId] ?? 0,
			dotClass: activeSources.value.has(sourceId) ? palette.dot : 'if-pill__dot--muted',
			activeClass: palette.active,
		}
	})
)

function toggleChip(id: StudentCalendarSource) {
	const next = new Set(activeSources.value)
	if (next.has(id)) {
		next.delete(id)
	} else {
		next.add(id)
	}
	activeSources.value = next
}

const calendarRef = ref<InstanceType<typeof FullCalendar> | null>(null)
const calendarOptions = ref({
	plugins: [dayGridPlugin, timeGridPlugin, listPlugin],
	initialView: 'timeGridWeek',
	height: 'auto',
	headerToolbar: {
		left: 'prev,next today',
		center: 'title',
		right: 'dayGridMonth,timeGridWeek,listWeek',
	},
	slotDuration: '00:30:00',
	slotMinTime: '07:00:00',
	slotMaxTime: '18:00:00',
	displayEventTime: false,
	dayMaxEvents: true,
	allDaySlot: true,
	nowIndicator: true,
	eventDisplay: 'block',
	hiddenDays: [0, 6],
	events: filteredEvents.value,
	datesSet: (arg: DatesSetArg) => handleDatesSet(arg),
	eventClick: (info: EventClickArg) => handleEventClick(info),
})

watch(filteredEvents, (val) => {
	calendarOptions.value.events = val
})

watch(showWeekends, (val) => {
	calendarOptions.value.hiddenDays = val ? [] : [0, 6]
})

function handleDatesSet(arg: DatesSetArg) {
	currentRange.value = {
		start: arg.startStr,
		end: arg.endStr,
	}
	calendarResource.fetch()
}

function handleRefresh() {
	interactionError.value = ''
	calendarResource.fetch()
}

function resolveSource(info: EventClickArg) {
	return (
		(info.event.extendedProps?.source as string | undefined) ||
		((info.event as unknown as { source?: string }).source ?? undefined) ||
		''
	)
}

function resolveEventId(info: EventClickArg) {
	return (
		info.event.id ||
		(info.event.extendedProps?.id as string | undefined) ||
		(info.event.extendedProps?.event_id as string | undefined) ||
		null
	)
}

function extractMeetingName(rawId?: string | null) {
	if (!rawId) return null
	const [prefix, ...rest] = rawId.split('::')
	if (prefix !== 'meeting' || rest.length === 0) return null
	return rest.join('::')
}

function extractSchoolEventName(rawId?: string | null) {
	if (!rawId) return null
	const [prefix, ...rest] = rawId.split('::')
	if (prefix !== 'school_event' || rest.length === 0) return null
	return rest.join('::')
}

function extractClassEventId(rawId?: string | null) {
	if (!rawId) return null
	if (rawId.startsWith('sg::') || rawId.startsWith('sg-booking::')) {
		return rawId
	}
	if (rawId.startsWith('sg/')) {
		return rawId.replace('sg/', 'sg::')
	}
	if (rawId.startsWith('student_group::')) {
		return rawId.replace('student_group::', 'sg::')
	}
	return null
}

function inferSourceFromId(rawId?: string | null): StudentCalendarSource | '' {
	if (!rawId) return ''
	if (rawId.startsWith('meeting::')) return 'meeting'
	if (rawId.startsWith('school_event::')) return 'school_event'
	if (rawId.startsWith('holiday::')) return 'holiday'
	if (rawId.startsWith('sg::') || rawId.startsWith('sg-booking::') || rawId.startsWith('sg/')) return 'student_group'
	return ''
}

function handleEventClick(info: EventClickArg) {
	info.jsEvent?.preventDefault()
	info.jsEvent?.stopPropagation()

	interactionError.value = ''
	const rawId = resolveEventId(info)
	const source = resolveSource(info) || inferSourceFromId(rawId)

	if (source === 'holiday') {
		return
	}

	if (source === 'meeting') {
		const meeting = extractMeetingName(rawId)
		if (!meeting) {
			interactionError.value = 'Could not open this meeting. Please refresh and try again.'
			return
		}
		overlay.open('meeting-event', { meeting })
		return
	}

	if (source === 'school_event') {
		const event = extractSchoolEventName(rawId)
		if (!event) {
			interactionError.value = 'Could not open this school event. Please refresh and try again.'
			return
		}
		overlay.open('school-event', { event })
		return
	}

	if (source === 'student_group') {
		const eventId = extractClassEventId(rawId)
		if (!eventId) {
			interactionError.value = 'Could not open class details. Please refresh and try again.'
			return
		}
		overlay.open('class-event', { eventId, portalRole: 'student' })
		return
	}

	interactionError.value = 'This calendar item could not be opened.'
}

let intervalHandle: number | null = null
const cleanupFns: Array<() => void> = []

function maybeAutoRefresh(reason: 'interval' | 'visibility') {
	if (!currentRange.value) return
	if (reason === 'visibility' && document.visibilityState !== 'visible') return
	calendarResource.fetch()
}

function setupIntervals() {
	intervalHandle = window.setInterval(() => maybeAutoRefresh('interval'), refreshInterval.value)
	const onVisibility = () => maybeAutoRefresh('visibility')
	document.addEventListener('visibilitychange', onVisibility)
	cleanupFns.push(() => document.removeEventListener('visibilitychange', onVisibility))
}

onMounted(() => {
	setupIntervals()
})

onBeforeUnmount(() => {
	cleanupFns.forEach((fn) => fn())
	if (intervalHandle) clearInterval(intervalHandle)
})
</script>
