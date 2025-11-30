<template>
	<div class="rounded-2xl border border-slate-200 bg-white shadow-sm">
		<!-- Header -->
		<div class="flex items-center justify-between border-b border-slate-100 px-4 py-3">
			<div>
				<h2 class="text-lg font-semibold text-slate-900">{{ currentMonthLabel }}</h2>
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

		<!-- Calendar grid -->
		<div class="relative">
			<!-- Weekday header -->
			<div
				class="grid grid-cols-7 gap-px bg-slate-100 px-2 pb-2 pt-3 text-center text-xs font-medium tracking-wider text-slate-500"
			>
				<div v-for="weekday in weekdays" :key="weekday" class="uppercase">
					{{ weekday }}
				</div>
			</div>

			<!-- Days -->
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
		<div class="calendar-legend flex items-center justify-between px-4 pb-3 pt-2 text-xs text-slate-500">
			<div class="flex items-center gap-2">
				<span class="legend-dot legend-dot--recorded"></span>
				<span>{{ __('Recorded') }}</span>
			</div>
			<div class="flex items-center gap-2">
				<span class="legend-dot legend-dot--meeting"></span>
				<span>{{ __('Scheduled') }}</span>
			</div>
			<div class="flex items-center gap-2">
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
	const weekendSet = new Set(props.weekendDays ?? [6, 0]) // Sat, Sun by default
	const todayDate = today()
	const todayIso = formatISO(todayDate)

	return Array.from({ length: 42 }).map((_, idx) => {
		const date = new Date(start)
		date.setDate(start.getDate() + idx)

		const iso = formatISO(date)
		const weekday = date.getDay()

		const isMeeting = meetingDateSet.value.has(iso)
		const isRecorded = recordedDateSet.value.has(iso)
		const isPast = date < todayDate
		const isToday = iso === todayIso
		const isMissing = isMeeting && !isRecorded && isPast

		return {
			date,
			iso,
			label: date.getDate(),
			isMeeting,
			isRecorded,
			isMissing,
			inCurrentMonth: date.getMonth() === props.month.getMonth(),
			isPast,
			isToday,
			weekday,
			isWeekend: weekendSet.has(weekday),
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

	if (day.isToday) {
		classes.push('calendar-day__badge--today')
	} else if (day.isRecorded) {
		classes.push('calendar-day__badge--recorded')
	} else if (day.isMissing) {
		classes.push('calendar-day__badge--missing')
	} else if (day.isMeeting) {
		classes.push('calendar-day__badge--meeting')
	}

	if ((!day.inCurrentMonth || day.isPast) && !day.isRecorded && !day.isToday && !day.isMissing) {
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
  // Local, timezone-agnostic YYYY-MM-DD (no UTC conversion)
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
/* 1. Base Day Cell */
.calendar-day {
	border: 1px solid transparent;
	background: transparent;
	display: flex;
	align-items: center;
	justify-content: center;
	transition: transform 120ms ease;
}

/* 2. Selected day – the only “boxed” look */
.calendar-day--selected .calendar-day__badge {
	background: rgb(var(--jacaranda-rgb));
	color: #fff;
	box-shadow: 0 4px 12px rgba(var(--jacaranda-rgb), 0.4);
	transform: scale(1.1);
}

/* 3. Badge pill */
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
	border: 1px solid transparent;
}

/* 4. Badge states */

/* Today */
.calendar-day__badge--today {
	color: rgb(var(--jacaranda-rgb));
	border-color: rgba(var(--jacaranda-rgb), 0.3);
	font-weight: 700;
}

/* Meeting day – green ring */
.calendar-day__badge--meeting {
	background: #fff;
	color: rgb(var(--leaf-rgb));
	border-color: rgba(var(--leaf-rgb), 0.5);
	box-shadow: 0 1px 2px rgba(var(--leaf-rgb), 0.1);
}

/* Meeting + recorded – filled green */
.calendar-day__badge--recorded {
	background: rgba(var(--leaf-rgb), 0.15);
	color: rgb(var(--leaf-rgb));
	border-color: transparent;
	font-weight: 600;
}

/* Past meeting, no attendance yet – flame warning ring */
.calendar-day__badge--missing {
	background: rgba(var(--flame-rgb), 0.06);
	color: rgb(var(--flame-rgb));
	border-color: rgba(var(--flame-rgb), 0.85);
	box-shadow: 0 0 0 1px rgba(var(--flame-rgb), 0.35);
	font-weight: 600;
}

/* Background / muted days */
.calendar-day__badge--muted {
	color: rgba(var(--slate-rgb), 0.3);
}

/* Hover on active meeting days */
.calendar-day:hover .calendar-day__badge--meeting {
	border-color: rgb(var(--leaf-rgb));
	background: rgba(var(--leaf-rgb), 0.05);
	cursor: pointer;
}

/* 5. Legend */

.calendar-legend {
	border-top: 1px solid rgba(var(--border-rgb), 0.8);
	background: linear-gradient(180deg, rgba(var(--sky-rgb), 0.65), #fff);
}

.legend-dot {
	display: inline-flex;
	height: 0.75rem;
	width: 0.75rem;
	border-radius: 9999px;
	border: 1px solid transparent;
}

/* Matches recorded pill */
.legend-dot--recorded {
	background: rgba(var(--leaf-rgb), 0.85);
	border-color: rgba(var(--leaf-rgb), 0.95);
}

/* Matches meeting ring */
.legend-dot--meeting {
	background: #fff;
	border-color: rgba(var(--leaf-rgb), 0.9);
}

/* Matches missing flame ring */
.legend-dot--missing {
	background: rgba(var(--flame-rgb), 0.06);
	border-color: rgba(var(--flame-rgb), 0.9);
}
</style>
