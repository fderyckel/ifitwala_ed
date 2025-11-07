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
					<!-- Badge-only style: blue for today, green for meeting days -->
					<div class="flex items-center justify-center">
						<span
							v-if="day.isToday"
							class="inline-flex h-7 w-7 items-center justify-center rounded-md bg-indigo-600 text-xs font-semibold text-white"
						>
							{{ day.label }}
						</span>
						<span
							v-else-if="day.isMeeting"
							class="inline-flex h-7 w-7 items-center justify-center rounded-md bg-emerald-600 text-xs font-semibold text-white"
						>
							{{ day.label }}
						</span>
						<span v-else class="text-sm font-medium">{{ day.label }}</span>
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
	const base =
		'group aspect-square rounded-xl border px-2 py-3 text-center text-sm transition ' +
		'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 ' +
		'disabled:cursor-not-allowed disabled:opacity-40'

	const classes = [base, 'border-slate-100 bg-white text-slate-700']

	// Weekend column subtle background
	if (day.isWeekend) classes.push('bg-slate-50')

	// Outside current month
	if (!day.inCurrentMonth) classes.push('text-slate-300')

	// Keep tile neutral; selection shows ring only
	const isSelected = props.selectedDate === day.iso
	if (isSelected) classes.push('ring-2 ring-indigo-500')

	// Non-meeting days look dim
	if (!day.isMeeting) classes.push('text-slate-400')

	// Hover affordance for meeting days
	if (day.isMeeting && !isSelected) classes.push('hover:bg-slate-100')

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
	return date.toISOString().slice(0, 10)
}

function formatMonth(date: Date) {
	return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
}

function parseMonth(key: string) {
	const [year, month] = key.split('-').map((p) => parseInt(p, 10))
	return new Date(year, month - 1, 1)
}

</script>
