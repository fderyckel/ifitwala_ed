<template>
	<div class="mx-auto flex h-full max-w-7xl flex-col gap-6 p-4 pb-10">
		<header class="flex flex-wrap items-center justify-between gap-4">
			<div>
				<h1 class="text-2xl font-semibold tracking-tight text-slate-900">
					{{ __('Student Attendance') }}
				</h1>
				<p class="text-sm text-slate-500">
					{{ __('Record daily attendance for your active student groups.') }}
				</p>
			</div>

			<div class="flex flex-wrap items-center gap-3">
				<FormControl
					type="select"
					class="min-w-[220px]"
					:options="groupOptions"
					option-label="label"
					option-value="value"
					v-model="filters.student_group"
					:placeholder="__('Select group')"
					:disabled="groupsLoading"
				/>

				<FormControl
					type="select"
					class="min-w-[200px]"
					:options="defaultCodeOptions"
					option-label="label"
					option-value="value"
					v-model="filters.default_code"
					:disabled="!attendanceCodes.length"
				/>

				<Button
					appearance="secondary"
					class="whitespace-nowrap"
					:disabled="!students.length || submitting"
					@click="applyDefaultCode"
				>
					{{ __('Mark everyone as default') }}
				</Button>

				<Button
					appearance="primary"
					class="whitespace-nowrap"
					:loading="submitting"
					:disabled="!canSubmit || submitting"
					@click="submitAttendance"
				>
					{{ submitLabel }}
				</Button>
			</div>
		</header>

		<div class="grid gap-6 xl:grid-cols-[minmax(0,3fr)_minmax(280px,1fr)]">
			<section class="flex flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
				<div class="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-4">
					<div class="min-w-0">
						<h2 class="text-lg font-semibold text-slate-900">
							{{ filters.student_group ? groupTitle : __('Select a student group') }}
						</h2>
						<p v-if="filters.student_group && groupSubtitle" class="text-xs uppercase tracking-wide text-slate-500">
							{{ groupSubtitle }}
						</p>
						<p v-else class="text-sm text-slate-500">
							{{ __('Choose a group to load today’s roster.') }}
						</p>
					</div>

					<div class="flex flex-wrap items-center gap-2">
						<Badge v-if="selectedDateLabel" variant="subtle" class="text-sm font-medium text-slate-700">
							{{ selectedDateLabel }}
						</Badge>
						<Button appearance="minimal" icon="refresh-ccw" :disabled="!canReload" @click="reloadRoster">
							{{ __('Refresh') }}
						</Button>
					</div>
				</div>

				<div class="flex flex-wrap items-center gap-3 border-b border-slate-100 px-5 py-3">
					<FormControl
						v-model="searchTerm"
						type="text"
						class="w-full flex-1 md:max-w-xs"
						:disabled="!filters.student_group || rosterLoading || !students.length"
						:placeholder="__('Search students')"
					/>

					<div v-if="filters.student_group" class="ml-auto text-xs text-slate-500">
						<span v-if="filteredStudents.length !== students.length">
							{{ __('Showing {0} of {1}', [filteredStudents.length, students.length]) }}
						</span>
						<span v-else>
							{{ __('Total students: {0}', [students.length]) }}
						</span>
					</div>
				</div>

				<div class="flex-1 overflow-hidden">
					<div
						v-if="!filters.student_group"
						class="flex h-full flex-col items-center justify-center gap-3 px-8 py-16 text-center text-slate-500"
					>
						<FeatherIcon name="users" class="h-12 w-12 text-slate-300" />
						<p class="text-base font-semibold text-slate-700">
							{{ __('Select a student group to begin taking attendance.') }}
						</p>
						<p class="max-w-sm text-sm">
							{{ __('Meeting days appear in the calendar, and recorded sessions are highlighted for quick reference.') }}
						</p>
					</div>

					<div v-else-if="calendarLoading" class="flex h-full flex-col items-center justify-center gap-3 py-12 text-slate-500">
						<Spinner class="h-6 w-6" />
						<p>{{ __('Loading schedule…') }}</p>
					</div>

					<div
						v-else-if="!meetingDates.length"
						class="flex h-full flex-col items-center justify-center gap-3 px-8 py-16 text-center text-slate-500"
					>
						<FeatherIcon name="calendar-x" class="h-12 w-12 text-slate-300" />
						<p class="text-base font-semibold">{{ __('No scheduled meetings found for this group.') }}</p>
						<p class="max-w-sm text-sm">
							{{ __('Update the Student Group Schedule to add meeting days for this group.') }}
						</p>
					</div>

					<div
						v-else-if="!selectedDate"
						class="flex h-full flex-col items-center justify-center gap-3 px-8 py-16 text-center text-slate-500"
					>
						<FeatherIcon name="calendar" class="h-12 w-12 text-slate-300" />
						<p class="text-base font-semibold">{{ __('Select a date from the calendar to record attendance.') }}</p>
						<p class="max-w-sm text-sm">
							{{ __('Only scheduled meeting days are selectable.') }}
						</p>
					</div>

					<div v-else class="flex h-full flex-col">
						<div v-if="rosterLoading" class="flex h-full flex-col items-center justify-center gap-3 py-12 text-slate-500">
							<Spinner class="h-6 w-6" />
							<p>{{ __('Loading roster…') }}</p>
						</div>

						<div
							v-else-if="!students.length"
							class="flex h-full flex-col items-center justify-center gap-3 px-8 py-16 text-center text-slate-500"
						>
							<FeatherIcon name="search" class="h-12 w-12 text-slate-300" />
							<p class="text-base font-semibold">{{ __('No students found in this group.') }}</p>
						</div>

						<div v-else class="flex h-full flex-col overflow-hidden">
							<div
								v-if="!filteredStudents.length"
								class="flex h-full flex-col items-center justify-center gap-3 px-8 py-16 text-center text-slate-500"
							>
								<FeatherIcon name="filter" class="h-12 w-12 text-slate-300" />
								<p class="text-base font-semibold">{{ __('No students match your search.') }}</p>
								<Button appearance="minimal" size="sm" @click="searchTerm = ''">
									{{ __('Clear search') }}
								</Button>
							</div>

							<div v-else class="flex-1 overflow-auto">
								<AttendanceGrid
									:students="filteredStudents"
									:blocks="blocks"
									:codes="attendanceCodes"
									:code-colors="codeColors"
									:disabled="submitting"
									@change-code="onCodeChanged"
									@open-remark="openRemark"
									@show-medical="showMedical"
								/>
							</div>

							<div class="border-t border-slate-100 px-5 py-3 text-xs text-slate-500">
								{{ __('Students loaded: {0}', [students.length]) }}
								<span v-if="hasExistingAttendance" class="ml-2 text-blue-600">
									{{ __('Existing attendance found for this date.') }}
								</span>
							</div>
						</div>
					</div>
				</div>
			</section>

			<aside class="flex flex-col gap-4">
				<AttendanceCalendar
					:month="calendarMonth"
					:meeting-dates="meetingDates"
					:recorded-dates="recordedDates"
					:available-months="availableMonths"
					:selected-date="selectedDate"
					:loading="calendarLoading"
					@update:month="(month) => (calendarMonth = month)"
					@update:selected-date="onDateSelected"
				/>

				<div class="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
					<h3 class="text-sm font-semibold text-slate-800">
						{{ __('Attendance codes') }}
					</h3>
					<p class="mt-1 text-xs text-slate-500">
						{{ __('Tap a chip to apply the code for the selected student and block.') }}
					</p>

					<div class="mt-3 flex flex-wrap gap-2">
						<div
							v-for="code in attendanceCodes"
							:key="code.name"
							class="flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs"
							:style="{ borderColor: code.color || '#cbd5f5', backgroundColor: withAlpha(code.color || '#2563eb', 0.12) }"
						>
							<span
								class="flex h-6 w-6 items-center justify-center rounded-full text-xs font-semibold text-white shadow-sm"
								:style="{ backgroundColor: code.color || '#2563eb' }"
							>
								{{ code.attendance_code || code.name?.charAt(0) }}
							</span>
							<span class="text-slate-600">{{ code.attendance_code_name || code.name }}</span>
						</div>
					</div>

					<div v-if="selectedDate && dailyTotals.length" class="mt-4 space-y-2">
						<h4 class="text-xs font-semibold uppercase tracking-wide text-slate-400">
							{{ __('Today’s tally') }}
						</h4>
						<div class="space-y-1 text-sm text-slate-600">
							<div v-for="entry in dailyTotals" :key="entry.code.name" class="flex items-center justify-between gap-2">
								<span>{{ entry.code.attendance_code_name || entry.code.name }}</span>
								<span class="font-semibold">{{ entry.count }}</span>
							</div>
						</div>
					</div>
				</div>

				<div v-if="filters.student_group" class="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
					<h3 class="text-sm font-semibold text-slate-800">
						{{ __('Group details') }}
					</h3>
					<dl class="mt-3 space-y-2 text-sm text-slate-600">
						<div v-if="groupInfo.name" class="flex justify-between gap-2">
							<dt class="text-slate-500">{{ __('Group') }}</dt>
							<dd class="font-medium text-right">{{ groupInfo.name }}</dd>
						</div>
						<div v-if="groupInfo.program" class="flex justify-between gap-2">
							<dt class="text-slate-500">{{ __('Program') }}</dt>
							<dd class="font-medium text-right">{{ groupInfo.program }}</dd>
						</div>
						<div v-if="groupInfo.course" class="flex justify-between gap-2">
							<dt class="text-slate-500">{{ __('Course') }}</dt>
							<dd class="font-medium text-right">{{ groupInfo.course }}</dd>
						</div>
						<div v-if="groupInfo.cohort" class="flex justify-between gap-2">
							<dt class="text-slate-500">{{ __('Cohort') }}</dt>
							<dd class="font-medium text-right">{{ groupInfo.cohort }}</dd>
						</div>
					</dl>
				</div>
			</aside>
		</div>

		<RemarkDialog
			v-model="remarkDialog.open"
			:student="remarkDialog.student"
			:block="remarkDialog.block"
			:value="remarkDialog.value"
			@save="onRemarkSaved"
		/>
	</div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch, onMounted } from 'vue'
import { Button, FormControl, Badge, FeatherIcon, Spinner, call, toast } from 'frappe-ui'
import { __ } from '@/lib/i18n'
import AttendanceCalendar from './components/AttendanceCalendar.vue'
import AttendanceGrid from './components/AttendanceGrid.vue'
import RemarkDialog from './components/RemarkDialog.vue'
import type { AttendanceCode, StudentRosterEntry, BlockKey } from './types'

const DEFAULT_CODE_NAME = 'Present'

const filters = reactive({
	student_group: null as string | null,
	default_code: DEFAULT_CODE_NAME,
})

const searchTerm = ref('')
const calendarMonth = ref(new Date(new Date().getFullYear(), new Date().getMonth(), 1))
const meetingDates = ref<string[]>([])
const recordedDates = ref<string[]>([])
const selectedDate = ref<string | null>(null)
const calendarLoading = ref(false)

const students = ref<StudentRosterEntry[]>([])
const blocks = ref<BlockKey[]>([])
const rosterLoading = ref(false)
const submitting = ref(false)
const rosterTotal = ref(0)

const groupInfo = ref<{ name?: string | null; program?: string | null; course?: string | null; cohort?: string | null }>({})

const attendanceCodes = ref<AttendanceCode[]>([])

const remarkDialog = reactive({
	open: false,
	student: null as StudentRosterEntry | null,
	block: null as BlockKey | null,
	value: '',
})

const groups = ref<any[]>([])
const groupsLoading = ref(false)

const groupOptions = computed(() =>
	(groups.value || []).map((row: any) => ({
		label: row.student_group_name || row.name,
		value: row.name,
	}))
)

const defaultCodeOptions = computed(() =>
	attendanceCodes.value.map((code) => ({
		label: code.attendance_code ? `${code.attendance_code} · ${code.attendance_code_name || code.name}` : code.attendance_code_name || code.name,
		value: code.name,
	}))
)

const codeColors = computed<Record<string, string>>(() => {
	const map: Record<string, string> = {}
	for (const code of attendanceCodes.value) {
		if (code.color) {
			map[code.name] = code.color
		}
	}
	return map
})

const codeDictionary = computed<Record<string, AttendanceCode>>(() => {
	const dict: Record<string, AttendanceCode> = {}
	for (const code of attendanceCodes.value) {
		dict[code.name] = code
	}
	return dict
})

const groupTitle = computed(() => groupInfo.value?.name || filters.student_group || '')
const groupSubtitle = computed(() => {
	const info = groupInfo.value || {}
	return [info.program, info.course, info.cohort].filter(Boolean).join(' • ')
})

const availableMonths = computed(() => {
	const monthSet = new Set<string>()
	for (const date of meetingDates.value) {
		monthSet.add(date.slice(0, 7))
	}
	return Array.from(monthSet).sort()
})

const submitLabel = computed(() => (hasExistingAttendance.value ? __('Update Attendance') : __('Submit Attendance')))
const canSubmit = computed(() => !!(filters.student_group && selectedDate.value && students.value.length))
const canReload = computed(() => !!(filters.student_group && selectedDate.value && !calendarLoading.value))
const hasExistingAttendance = computed(() => recordedDates.value.includes(selectedDate.value || ''))

const filteredStudents = computed(() => {
	if (!searchTerm.value) {
		return students.value
	}
	const q = searchTerm.value.toLowerCase().trim()
	return students.value.filter((stu) => {
		const haystack = [
			stu.student,
			stu.student_name,
			stu.preferred_name,
		]
			.filter(Boolean)
			.map((val) => String(val).toLowerCase())
			.join(' ')
		return haystack.includes(q)
	})
})

const selectedDateLabel = computed(() => {
	if (!selectedDate.value) return ''
	try {
		const date = new Date(selectedDate.value + 'T00:00:00')
		return new Intl.DateTimeFormat(undefined, {
			weekday: 'long',
			month: 'long',
			day: 'numeric',
			year: 'numeric',
		}).format(date)
	} catch (error) {
		console.warn('Failed to format selected date', selectedDate.value, error)
		return selectedDate.value
	}
})

const dailyTotals = computed(() => {
	if (!students.value.length || !blocks.value.length) {
		return []
	}
	const counts: Record<string, number> = {}
	for (const student of students.value) {
		for (const block of blocks.value) {
			const codeName = student.attendance[block]
			if (!codeName) continue
			counts[codeName] = (counts[codeName] || 0) + 1
		}
	}
	return attendanceCodes.value
		.map((code) => ({
			code,
			count: counts[code.name] || 0,
		}))
		.filter((entry) => entry.count > 0)
})

const DEFAULT_COLOR = '#2563eb'

function withAlpha(hex: string, alpha: number) {
	if (!hex) return `rgba(37, 99, 235, ${alpha})`
	const value = hex.replace('#', '')
	if (value.length !== 6) {
		return `rgba(37, 99, 235, ${alpha})`
	}
	const r = parseInt(value.substring(0, 2), 16)
	const g = parseInt(value.substring(2, 4), 16)
	const b = parseInt(value.substring(4, 6), 16)
	return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

function unwrapMessage(res: any) {
	if (res && typeof res === 'object' && 'message' in res) {
		return (res as any).message
	}
	return res
}

async function loadAttendanceCodes() {
	try {
		const response = await call('ifitwala_ed.schedule.attendance_utils.list_attendance_codes')
		const items = unwrapMessage(response) ?? []
		attendanceCodes.value = items.map((row: any) => ({
			...row,
			color: row.color || DEFAULT_COLOR,
		}))
		if (!attendanceCodes.value.length) {
			filters.default_code = ''
			return
		}
		if (!attendanceCodes.value.find((code) => code.name === filters.default_code)) {
			const present = attendanceCodes.value.find((code) => code.name === DEFAULT_CODE_NAME)
			filters.default_code = present?.name || attendanceCodes.value[0].name
		}
	} catch (error) {
		console.error('Failed to load attendance codes', error)
		toast({
			title: __('Could not load attendance codes'),
			appearance: 'danger',
		})
	}
}

async function loadGroups() {
	groupsLoading.value = true
	try {
		console.debug('[Attendance] Loading student groups')
		const response = await call('ifitwala_ed.api.student_attendance.fetch_portal_student_groups')
		const data = unwrapMessage(response)
		groups.value = Array.isArray(data) ? data : []
		console.debug('[Attendance] Loaded groups:', groups.value)
		if (!(groups.value?.length)) {
			console.debug('[Attendance] No student groups returned from server')
		}
	} catch (error) {
		console.error('Failed to load student groups', error)
		toast({
			title: __('Could not load student groups'),
			appearance: 'danger',
		})
		groups.value = []
	} finally {
		groupsLoading.value = false
	}
}

function onGroupChange() {
	selectedDate.value = null
	searchTerm.value = ''
	meetingDates.value = []
	recordedDates.value = []
	groupInfo.value = {}
	students.value = []
	if (filters.student_group) {
		void loadCalendarData({ preserveSelection: false })
	}
}

function onDefaultCodeChange() {
	applyDefaultCode({ silent: true })
}

async function loadCalendarData(options: { preserveSelection?: boolean } = {}) {
	if (!filters.student_group) return
	const preserveSelection = options.preserveSelection ?? false
	calendarLoading.value = true
	try {
		const [meetingsResponse, recordedResponse] = await Promise.all([
			call('ifitwala_ed.schedule.attendance_utils.get_meeting_dates', { student_group: filters.student_group }),
			call('ifitwala_ed.schedule.attendance_utils.attendance_recorded_dates', { student_group: filters.student_group }),
		])
		meetingDates.value = unwrapMessage(meetingsResponse) ?? []
		recordedDates.value = unwrapMessage(recordedResponse) ?? []

		if (!meetingDates.value.length) {
			selectedDate.value = null
			students.value = []
			return
		}

		let nextDate: string | null = null
		if (preserveSelection && selectedDate.value && meetingDates.value.includes(selectedDate.value)) {
			nextDate = selectedDate.value
		} else {
			nextDate = pickDefaultDate(meetingDates.value)
		}

		selectedDate.value = nextDate

		if (nextDate) {
			calendarMonth.value = new Date(nextDate + 'T00:00:00')
			await loadRoster()
		} else {
			students.value = []
		}
	} catch (error) {
		console.error('Failed to load calendar data', error)
		toast({
			title: __('Could not load meeting dates'),
			appearance: 'danger',
		})
	} finally {
		calendarLoading.value = false
	}
}

async function loadRoster() {
	if (!filters.student_group || !selectedDate.value) return
	rosterLoading.value = true
	try {
		const [rosterRes, prevRes, existingRes, blocksRes] = await Promise.all([
			call('ifitwala_ed.schedule.attendance_utils.fetch_students', {
				student_group: filters.student_group,
				start: 0,
				page_length: 500,
			}),
			call('ifitwala_ed.schedule.attendance_utils.previous_status_map', {
				student_group: filters.student_group,
				attendance_date: selectedDate.value,
			}),
			call('ifitwala_ed.schedule.attendance_utils.fetch_existing_attendance', {
				student_group: filters.student_group,
				attendance_date: selectedDate.value,
			}),
			call('ifitwala_ed.schedule.attendance_utils.fetch_blocks_for_day', {
				student_group: filters.student_group,
				attendance_date: selectedDate.value,
			}),
		])

		const roster = unwrapMessage(rosterRes) ?? { students: [], group_info: {} }
		const prevMap = unwrapMessage(prevRes) ?? {}
		const existingMap = unwrapMessage(existingRes) ?? {}
		const blocksForDay: BlockKey[] = unwrapMessage(blocksRes) ?? []
		const normalizedBlocks = blocksForDay.length ? blocksForDay : [-1]

		groupInfo.value = roster.group_info || {}
		rosterTotal.value = roster.total || (roster.students ? roster.students.length : 0)

		students.value = (roster.students || []).map((stu: any) => {
			const studentEntry: StudentRosterEntry = {
				student: stu.student,
				student_name: stu.student_name,
				preferred_name: stu.preferred_name,
				student_image: stu.student_image,
				birth_date: stu.birth_date,
				medical_info: stu.medical_info,
				blocks: normalizedBlocks,
				attendance: {} as Record<BlockKey, string>,
				remarks: {} as Record<BlockKey, string>,
			}

			for (const block of normalizedBlocks) {
				const existing = existingMap?.[stu.student]?.[block]
				const previous = prevMap?.[stu.student]
				const fallbackCode = filters.default_code || attendanceCodes.value[0]?.name || ''

				studentEntry.attendance[block] = existing?.code || previous || fallbackCode
				studentEntry.remarks[block] = existing?.remark || ''
			}

			return studentEntry
		})

		blocks.value = normalizedBlocks
	} catch (error) {
		console.error('Failed to load roster', error)
		toast({
			title: __('Could not load attendance roster'),
			appearance: 'danger',
		})
	} finally {
		rosterLoading.value = false
	}
}

function pickDefaultDate(dates: string[]) {
	if (!dates.length) return null
	const today = new Date()
	today.setHours(0, 0, 0, 0)
	let closest = dates[0]
	let minDiff = Infinity
	for (const dateStr of dates) {
		const d = new Date(dateStr + 'T00:00:00')
		const diff = Math.abs(d.getTime() - today.getTime())
		if (diff < minDiff) {
			minDiff = diff
			closest = dateStr
		}
	}
	return closest
}

function onDateSelected(date: string) {
	selectedDate.value = date
	loadRoster()
}

function reloadRoster() {
	if (canReload.value) {
		void loadRoster()
	}
}

function onCodeChanged(payload: { studentId: string; block: BlockKey; code: string }) {
	const student = students.value.find((s) => s.student === payload.studentId)
	if (student) {
		student.attendance[payload.block] = payload.code
	}
}

function openRemark(payload: { student: StudentRosterEntry; block: BlockKey }) {
	remarkDialog.student = payload.student
	remarkDialog.block = payload.block
	remarkDialog.value = payload.student.remarks[payload.block] || ''
	remarkDialog.open = true
}

function onRemarkSaved(value: string) {
	if (!remarkDialog.student || remarkDialog.block === null) return
	const target = students.value.find((s) => s.student === remarkDialog.student?.student)
	if (target) {
		target.remarks[remarkDialog.block] = value
	}
}

function applyDefaultCode(options: { silent?: boolean } = {}) {
	if (!filters.default_code || !students.value.length) return
	for (const student of students.value) {
		for (const block of blocks.value) {
			student.attendance[block] = filters.default_code
		}
	}
	if (!options.silent) {
		const code = codeDictionary.value[filters.default_code]
		const label = code?.attendance_code_name || filters.default_code
		toast({
			title: __('Default applied'),
			message: __('Updated all students to {0}.', [label]),
			appearance: 'info',
		})
	}
}

async function submitAttendance() {
	if (!canSubmit.value || submitting.value) return
	submitting.value = true
	try {
		const payload = []
		for (const student of students.value) {
			for (const block of blocks.value) {
				payload.push({
					student: student.student,
					student_group: filters.student_group,
					attendance_date: selectedDate.value,
					block_number: block,
					attendance_code: student.attendance[block],
					remark: student.remarks[block] || '',
				})
			}
		}

		const response = await call('ifitwala_ed.schedule.attendance_utils.bulk_upsert_attendance', { payload })
		const result = unwrapMessage(response) || {}
		toast({
			title: __('Attendance saved'),
			message: __('{0} created | {1} updated', [result.created || 0, result.updated || 0]),
			appearance: 'success',
		})
		await loadCalendarData({ preserveSelection: true })
	} catch (error: any) {
		console.error('Failed to submit attendance', error)
		toast({
			title: __('Error submitting attendance'),
			message: error?.message || __('Please try again.'),
			appearance: 'danger',
		})
	} finally {
		submitting.value = false
	}
}

function showMedical(student: StudentRosterEntry) {
	if (!student.medical_info) return
	frappe.msgprint({
		title: __('Health Note for {0}', [student.preferred_name || student.student_name || student.student]),
		message: student.medical_info,
		indicator: 'red',
	})
}

onMounted(() => {
	loadAttendanceCodes()
	loadGroups()
})

watch(
	() => groups.value,
	(newVal) => {
		console.debug('[Attendance] groups updated:', newVal)
	},
	{ deep: true }
)

watch(() => filters.student_group, onGroupChange)
watch(() => filters.default_code, onDefaultCodeChange)
</script>
