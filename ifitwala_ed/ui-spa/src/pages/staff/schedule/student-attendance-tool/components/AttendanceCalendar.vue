<template>
	<div class="rounded-2xl border border-[color:var(--border)] bg-white shadow-sm">
		<div class="flex items-center justify-between border-b border-[color:var(--border)]/60 px-4 py-3">
			<div>
				<h2 class="text-lg font-semibold text-[color:var(--canopy)]">
					{{ currentMonthLabel }}
				</h2>
				<p class="text-xs text-slate-500">
					{{ meetingSummary }}
				</p>
			</div>

			<div class="flex items-center gap-2">
				<Button
					appearance="minimal"
					icon="chevron-left"
					:disabled="!previousMonthDate || loading"
					@click="goToPrev"
				/>
				<Button
					appearance="minimal"
					icon="chevron-right"
					:disabled="!nextMonthDate || loading"
					@click="goToNext"
				/>
			</div>
		</div>

		<div class="relative">
			<!-- Weekdays -->
			<div
				class="grid grid-cols-7 gap-px bg-slate-100 px-2 pb-2 pt-3 text-center text-xs font-medium tracking-wider text-slate-500"
			>
				<div v-for="weekday in weekdays" :key="weekday" class="uppercase">
					{{ weekday }}
				</div>
			</div>

			<!-- Days grid -->
			<div class="grid grid-cols-7 gap-px bg-slate-100 p-2">
				<button
					v-for="day in days"
					:key="day.iso"
					type="button"
					:disabled="!day.isMeeting || loading"
					:class="dayButtonClass(day)"
					@click="selectDay(day)"
				>
					<div class="flex items-center justify-center">
						<span :class="dayBadgeClass(day)">
							{{ day.label }}
						</span>
					</div>
				</button>
			</div>

			<!-- Loading overlay -->
			<div
				v-if="loading"
				class="absolute inset-0 flex items-center justify-center rounded-2xl bg-white/70 backdrop-blur-sm"
			>
				<Spinner class="h-6 w-6 text-slate-400" />
			</div>
		</div>

		<!-- Legend -->
		<div class="flex items-center gap-4 border-t border-[color:var(--border)]/60 px-4 py-2.5 text-xs text-slate-600">
			<div class="flex items-center gap-1.5">
				<span class="legend-dot legend-dot--recorded"></span>
				<span>{{ __('Recorded') }}</span>
			</div>
			<div class="flex items-center gap-1.5">
				<span class="legend-dot legend-dot--scheduled"></span>
				<span>{{ __('Scheduled') }}</span>
			</div>
			<div class="flex items-center gap-1.5">
				<span class="legend-dot legend-dot--missing"></span>
				<span>{{ __('Missing') }}</span>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Button, Spinner } from 'frappe-ui'
import { __ } from '@/lib/i18n'

type CalendarDay = {
	date: Date
	iso: string
	label: number
	isMeeting: boolean
	isRecorded: boolean
	isMissing: boolean
	inCurrentMonth: boolean
	isPast: boolean
	isToday: boolean
	weekday: number
	isWeekend: boolean
}

const props = defineProps<{
	month: Date
	meetingDates: string[]
	recordedDates: string[]
	selectedDate: string | null
	availableMonths: string[]
	loading?: boolean
	/** Weekend days as JS weekday numbers (0=Sun … 6=Sat). Default: Sat–Sun */
	weekendDays?: number[]
}>()

const emit = defineEmits<{
	(event: 'update:month', value: Date): void
	(event: 'update:selected-date', value: string): void
	(event: 'select', value: string): void
}>()

const weekdayFormatter = new Intl.DateTimeFormat(undefined, { weekday: 'short' })
const monthFormatter = new Intl.DateTimeFormat(undefined, { month: 'long', year: 'numeric' })

const weekdays = computed(() => {
	// Always render Mon→Sun in header
	const monday = startOfWeek(new Date())
	return Array.from({ length: 7 }).map((_, idx) => {
		const d = new Date(monday)
		d.setDate(d.getDate() + idx)
		return weekdayFormatter.format(d)
	})
})

const meetingDateSet = computed(() => new Set(props.meetingDates))
const recordedDateSet = computed(() => new Set(props.recordedDates))
const availableMonthSet = computed(() => new Set(props.availableMonths))

const currentMonthKey = computed(() => formatMonth(props.month))
const currentMonthLabel = computed(() => monthFormatter.format(props.month))

const meetingSummary = computed(() => {
	const count = props.meetingDates.filter((d) => d.startsWith(currentMonthKey.value)).length
	if (!count) {
		return __('No scheduled meetings this month')
	}
	return count === 1 ? __('1 scheduled meeting') : __('{0} scheduled meetings', [count])
})

const previousMonthDate = computed(() => {
	const months = [...availableMonthSet.value].sort()
	const idx = months.indexOf(currentMonthKey.value)
	if (idx <= 0) return null
	return parseMonth(months[idx - 1])
})

const nextMonthDate = computed(() => {
	const months = [...availableMonthSet.value].sort()
	const idx = months.indexOf(currentMonthKey.value)
	if (idx === -1 || idx >= months.length - 1) return null
	return parseMonth(months[idx + 1])
})

const days = computed<CalendarDay[]>(() => {
	const start = startOfCalendarGrid(props.month)
	const todayDate = today()
	const todayIso = formatISO(todayDate)
	const weekendSet = new Set(props.weekendDays ?? [6, 0]) // Sat, Sun default

	return Array.from({ length: 42 }).map((_, idx) => {
		const date = new Date(start)
		date.setDate(start.getDate() + idx)
		const iso = formatISO(date)
		const isMeeting = meetingDateSet.value.has(iso)
		const isRecorded = recordedDateSet.value.has(iso)
		const isPast = date < todayDate
		const isMissing = isMeeting && isPast && !isRecorded

		return {
			date,
			iso,
			label: date.getDate(),
			isMeeting,
			isRecorded,
			isMissing,
			inCurrentMonth: date.getMonth() === props.month.getMonth(),
			isPast,
			isToday: iso === todayIso,
			weekday: date.getDay(),
			isWeekend: weekendSet.has(date.getDay()),
		}
	})
})

function goToPrev() {
	if (!previousMonthDate.value) return
	emit('update:month', previousMonthDate.value)
}

function goToNext() {
	if (!nextMonthDate.value) return
	emit('update:month', nextMonthDate.value)
}

function selectDay(day: CalendarDay) {
	if (!day.isMeeting) return
	emit('update:selected-date', day.iso)
	emit('select', day.iso)
}

function dayButtonClass(day: CalendarDay) {
	return [
		'calendar-day group relative w-full aspect-square p-1',
		'focus-visible:outline-none',
		props.selectedDate === day.iso ? 'calendar-day--selected' : '',
		!day.isMeeting ? 'cursor-default' : 'cursor-pointer',
	].filter(Boolean).join(' ')
}

function dayBadgeClass(day: CalendarDay) {
	const classes = ['calendar-day__badge']

	if (day.isToday && !day.isPast) {
		classes.push('calendar-day__badge--today')
	}

	if (day.isRecorded) {
		classes.push('calendar-day__badge--recorded')
	} else if (day.isMissing) {
		classes.push('calendar-day__badge--missing')
	} else if (day.isMeeting) {
		classes.push('calendar-day__badge--meeting')
	}

	if ((!day.inCurrentMonth || day.isPast) && !day.isRecorded && !day.isToday) {
		classes.push('calendar-day__badge--muted')
	}

	return classes.join(' ')
}

function startOfWeek(date: Date) {
	const d = new Date(date)
	const day = d.getDay()
	const diff = (day === 0 ? -6 : 1) - day
	d.setDate(d.getDate() + diff)
	d.setHours(0, 0, 0, 0)
	return d
}

function startOfCalendarGrid(date: Date) {
	const first = new Date(date.getFullYear(), date.getMonth(), 1)
	return startOfWeek(first)
}

function today() {
	const now = new Date()
	now.setHours(0, 0, 0, 0)
	return now
}

function formatISO(date: Date) {
	const y = date.getFullYear()
	const m = String(date.getMonth() + 1).padStart(2, '0')
	const d = String(date.getDate()).padStart(2, '0')
	return `${y}-${m}-${d}`
}

function formatMonth(date: Date) {
	return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
}

function parseMonth(key: string) {
	const [year, month] = key.split('-').map((p) => parseInt(p, 10))
	return new Date(year, month - 1, 1)
}
</script>

<style scoped>
/* Base day cell */
.calendar-day {
	border: 1px solid transparent;
	background: transparent;
	display: flex;
	align-items: center;
	justify-content: center;
	transition: transform 120ms ease;
}

/* Selected day – filled jacaranda pill */
.calendar-day--selected .calendar-day__badge {
	background: rgb(var(--jacaranda-rgb));
	color: #fff;
	box-shadow: 0 4px 12px rgba(var(--jacaranda-rgb), 0.4);
	transform: scale(1.1);
}

/* Day badge base */
.calendar-day__badge {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	height: 2.25rem;
	width: 2.25rem;
	border-radius: 9999px;
	font-weight: 500;
	font-size: 0.9rem;
	transition: all 150ms ease;
	border: 2px solid transparent;
}

/* Today (outline only, no meeting semantics) */
.calendar-day__badge--today {
	color: rgb(var(--jacaranda-rgb));
	border-color: rgba(var(--jacaranda-rgb), 0.35);
	font-weight: 700;
}

/* Future / upcoming meeting – jacaranda ring */
.calendar-day__badge--meeting {
	background: #fff;
	color: rgb(var(--jacaranda-rgb));
	border-color: rgba(var(--jacaranda-rgb), 0.7);
	box-shadow: 0 1px 2px rgba(var(--jacaranda-rgb), 0.12);
}

/* Recorded attendance – leaf ring */
.calendar-day__badge--recorded {
	background: #fff;
	color: rgb(var(--leaf-rgb));
	border-color: rgba(var(--leaf-rgb), 0.85);
	box-shadow: 0 1px 2px rgba(var(--leaf-rgb), 0.14);
	font-weight: 600;
}

/* Past meeting with NO attendance yet – flame ring */
.calendar-day__badge--missing {
	background: #fff;
	color: rgb(var(--flame-rgb));
	border-color: rgba(var(--flame-rgb), 0.85);
	box-shadow: 0 0 0 1px rgba(var(--flame-rgb), 0.45);
	font-weight: 600;
}

/* Muted (other month / old non-meeting) */
.calendar-day__badge--muted {
	color: rgba(var(--slate-rgb), 0.35);
}

/* Hover for any clickable meeting day */
.calendar-day:hover .calendar-day__badge--meeting,
.calendar-day:hover .calendar-day__badge--recorded,
.calendar-day:hover .calendar-day__badge--missing {
	background: rgba(255, 255, 255, 0.96);
	transform: translateY(-1px);
}

/* Legend dots */
.legend-dot {
	height: 0.9rem;
	width: 0.9rem;
	border-radius: 9999px;
	border-width: 2px;
	border-style: solid;
	background: #fff;
}

.legend-dot--recorded {
	border-color: rgba(var(--leaf-rgb), 0.85);
}

.legend-dot--scheduled {
	border-color: rgba(var(--jacaranda-rgb), 0.7);
}

.legend-dot--missing {
	border-color: rgba(var(--flame-rgb), 0.85);
}
</style>

