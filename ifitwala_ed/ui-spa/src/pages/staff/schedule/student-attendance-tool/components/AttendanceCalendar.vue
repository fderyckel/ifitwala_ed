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
					<div class="flex flex-col items-center gap-1">
						<span class="text-sm font-medium">{{ day.label }}</span>
						<span
							v-if="day.isRecorded"
							class="inline-flex h-1.5 w-1.5 rounded-full bg-emerald-500"
						/>
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

type CalendarDay = {
	date: Date
	iso: string
	label: number
	isMeeting: boolean
	isRecorded: boolean
	inCurrentMonth: boolean
	isPast: boolean
}

const props = defineProps<{
	month: Date
	meetingDates: string[]
	recordedDates: string[]
	selectedDate: string | null
	availableMonths: string[]
	loading?: boolean
}>()

const emit = defineEmits<{
	(event: 'update:month', value: Date): void
	(event: 'update:selected-date', value: string): void
	(event: 'select', value: string): void
}>()

const weekdayFormatter = new Intl.DateTimeFormat(undefined, { weekday: 'short' })
const monthFormatter = new Intl.DateTimeFormat(undefined, { month: 'long', year: 'numeric' })

const weekdays = computed(() => {
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
		return {
			date,
			iso,
			label: date.getDate(),
			isMeeting: meetingDateSet.value.has(iso),
			isRecorded: recordedDateSet.value.has(iso),
			inCurrentMonth: date.getMonth() === props.month.getMonth(),
			isPast: date < today(),
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
		'group aspect-square rounded-xl border border-slate-100 bg-white px-2 py-3 text-center text-slate-600 transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:cursor-not-allowed disabled:border-slate-100 disabled:bg-slate-50 disabled:text-slate-300'

	const classes = [base]

	if (!day.inCurrentMonth) {
		classes.push('text-slate-300')
	}

	if (day.isMeeting) {
		classes.push('hover:border-blue-200 hover:bg-blue-50 hover:text-blue-600')
	}

	if (props.selectedDate === day.iso) {
		classes.push('border-blue-400 bg-blue-50 text-blue-700 ring-2 ring-blue-200')
	}

	if (!day.isMeeting) {
		classes.push('opacity-60')
	}

	if (day.isPast && day.isMeeting && props.selectedDate !== day.iso) {
		classes.push('border-slate-200 bg-slate-50 text-slate-500')
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
