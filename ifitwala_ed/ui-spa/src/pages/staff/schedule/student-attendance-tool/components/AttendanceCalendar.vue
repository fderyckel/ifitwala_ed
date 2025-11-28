<template>
	<div class="rounded-2xl border border-slate-200 bg-white shadow-sm">
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

		<div class="relative">
			<div class="grid grid-cols-7 gap-px bg-slate-100 px-2 pb-2 pt-3 text-center text-xs font-medium tracking-wider text-slate-500">
				<div v-for="weekday in weekdays" :key="weekday" class="uppercase">
					{{ weekday }}
				</div>
			</div>

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

			<div
				v-if="loading"
				class="absolute inset-0 flex items-center justify-center rounded-2xl bg-white/70 backdrop-blur-sm"
			>
				<Spinner class="h-6 w-6 text-slate-400" />
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
	return Array.from({ length: 42 }).map((_, idx) => {
		const date = new Date(start)
		date.setDate(start.getDate() + idx)
		const iso = formatISO(date)
		const weekday = date.getDay()
		const weekendSet = new Set(props.weekendDays ?? [6, 0]) // Sat, Sun by default
		const todayIso = formatISO(today())
		return {
			date,
			iso,
			label: date.getDate(),
			isMeeting: meetingDateSet.value.has(iso),
			isRecorded: recordedDateSet.value.has(iso),
			inCurrentMonth: date.getMonth() === props.month.getMonth(),
			isPast: date < today(),
			isToday: iso === todayIso,
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
	const classes = [
		'calendar-day group aspect-square rounded-xl px-2 py-3 text-center text-sm transition text-slate-700',
		'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--jacaranda-rgb),0.52)] focus-visible:ring-offset-2 focus-visible:ring-offset-white',
		'disabled:cursor-not-allowed disabled:opacity-50',
	]

	if (day.isWeekend) classes.push('calendar-day--weekend')
	if (!day.inCurrentMonth) classes.push('calendar-day--muted')
	if (day.isMeeting) classes.push('calendar-day--meeting')
	if (day.isRecorded) classes.push('calendar-day--recorded')
	if (props.selectedDate === day.iso) classes.push('calendar-day--selected')
	if (day.isPast) classes.push('calendar-day--past')
	if (!day.isMeeting) classes.push('calendar-day--inactive')

	return classes.join(' ')
}

function dayBadgeClass(day: CalendarDay) {
	const classes = ['calendar-day__badge']

	if (!day.inCurrentMonth) {
		classes.push('calendar-day__badge--muted')
	}

	if (day.isToday) {
		classes.push('calendar-day__badge--today')
	} else if (day.isRecorded) {
		classes.push('calendar-day__badge--recorded')
	} else if (day.isMeeting) {
		classes.push('calendar-day__badge--meeting')
	} else {
		classes.push('calendar-day__badge--idle')
	}

	if (day.isPast && !day.isToday && !day.isRecorded) {
		classes.push('calendar-day__badge--past')
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
.calendar-day {
	border: 1px solid transparent;
	background: transparent;
	transition:
		border-color 120ms ease,
		box-shadow 120ms ease,
		transform 120ms ease,
		background-color 120ms ease;
}

.calendar-day--weekend {
	background: linear-gradient(180deg, rgba(var(--sky-rgb), 0.14), rgba(255, 255, 255, 0.08));
}

.calendar-day--muted {
	color: rgba(var(--slate-rgb), 0.6);
}

.calendar-day--inactive {
	background: transparent;
}

.calendar-day--meeting {
	border-color: rgba(var(--leaf-rgb), 0.32);
	background: rgba(var(--leaf-rgb), 0.08);
	box-shadow: 0 8px 20px rgba(var(--leaf-rgb), 0.16);
}

.calendar-day--meeting:not(.calendar-day--selected):not(:disabled):hover {
	transform: translateY(-1px);
}

.calendar-day--selected {
	border-color: rgba(var(--jacaranda-rgb), 0.55);
	background: linear-gradient(180deg, rgba(var(--jacaranda-rgb), 0.08), rgba(255, 255, 255, 0.96));
	box-shadow: 0 0 0 3px rgba(var(--jacaranda-rgb), 0.45);
}

.calendar-day--past {
	color: rgba(var(--slate-rgb), 0.7);
}

.calendar-day__badge {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	height: 2.4rem;
	min-width: 2.4rem;
	padding: 0.25rem 0.65rem;
	border-radius: 0.9rem;
	font-weight: 600;
	font-size: 0.95rem;
	letter-spacing: -0.01em;
	border: 1px solid transparent;
	transition:
		background-color 140ms ease,
		color 140ms ease,
		box-shadow 140ms ease,
		border-color 140ms ease;
}

.calendar-day__badge--today {
	background: rgb(var(--jacaranda-rgb));
	color: #fff;
	box-shadow: 0 10px 24px rgba(var(--jacaranda-rgb), 0.3);
}

.calendar-day__badge--meeting {
	background: rgba(var(--leaf-rgb), 0.18);
	color: rgb(var(--leaf-rgb));
	border-color: rgba(var(--leaf-rgb), 0.36);
	box-shadow: 0 10px 22px rgba(var(--leaf-rgb), 0.2);
}

.calendar-day__badge--recorded {
	background: rgba(var(--leaf-rgb), 0.32);
	color: #fff;
	border-color: rgba(var(--leaf-rgb), 0.55);
	box-shadow: 0 12px 28px rgba(var(--leaf-rgb), 0.26);
}

.calendar-day__badge--idle {
	color: rgba(var(--slate-rgb), 0.82);
}

.calendar-day__badge--muted {
	color: rgba(var(--slate-rgb), 0.55);
}

.calendar-day__badge--past {
	background: rgba(var(--slate-rgb), 0.1);
	color: rgba(var(--slate-rgb), 0.78);
	border-color: rgba(var(--slate-rgb), 0.2);
	box-shadow: none;
}

.calendar-day__badge--meeting.calendar-day__badge--past {
	background: rgba(var(--slate-rgb), 0.14);
	color: rgba(var(--slate-rgb), 0.82);
	border-color: rgba(var(--slate-rgb), 0.26);
	box-shadow: none;
}
</style>
