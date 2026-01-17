<!-- ui-spa/src/pages/staff/schedule/StudentAttendanceTool.vue -->
<template>
	<div class="staff-shell space-y-5">
		<header class="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
			<div class="min-w-0">
				<h1 class="type-h2">{{ __('Student Attendance') }}</h1>
				<p class="type-caption text-ink/60">
					{{ subtitleText || __('Pick a group and a meeting day, then record attendance.') }}
				</p>
			</div>

			<div class="flex items-center gap-2">
				<Badge
					:variant="statusVariant"
					:label="toolbarStatus"
				/>
				<Button
					appearance="primary"
					:disabled="!canApplyDefault"
					@click="applyDefaultCode"
				>
					{{ __('Apply Default') }}
				</Button>
			</div>
		</header>

		<!-- Errors (inline; no toasts from this page) -->
		<div
			v-if="errorBanner"
			class="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
		>
			<div class="flex items-start gap-3">
				<FeatherIcon name="alert-triangle" class="mt-0.5 h-4 w-4" />
				<div class="min-w-0">
					<p class="font-semibold">{{ __('Something went wrong') }}</p>
					<p class="mt-0.5 break-words">{{ errorBanner }}</p>
				</div>
				<button
					type="button"
					class="ml-auto inline-flex h-7 w-7 items-center justify-center rounded-full text-red-600 hover:bg-red-100"
					@click="errorBanner = null"
					aria-label="Close"
				>
					<FeatherIcon name="x" class="h-4 w-4" />
				</button>
			</div>
		</div>

		<!-- Filters -->
		<section class="rounded-2xl border border-border/70 bg-[rgb(var(--surface-rgb)/0.7)] p-4 shadow-soft">
			<div class="grid gap-3 md:grid-cols-4">
				<FormControl
					type="select"
					:label="__('School')"
					v-model="filters.school"
					:options="schoolOptions"
					:disabled="bootLoading"
				/>

				<FormControl
					type="select"
					:label="__('Program')"
					v-model="filters.program"
					:options="programOptions"
					:disabled="bootLoading"
				/>

				<FormControl
					type="select"
					:label="__('Student Group')"
					v-model="filters.student_group"
					:options="groupOptions"
					:disabled="groupsLoading || bootLoading"
				/>

				<FormControl
					type="select"
					:label="__('Default Code')"
					v-model="filters.default_code"
					:options="codeOptions"
					:disabled="codesLoading || bootLoading"
				/>
			</div>

			<div class="mt-3 flex flex-wrap items-center justify-between gap-3">
				<div class="flex items-center gap-2 text-xs text-ink/60">
					<span v-if="groupLabel" class="inline-flex items-center gap-2">
						<span class="font-semibold text-ink">{{ groupLabel }}</span>
						<span v-if="subtitleText">•</span>
						<span v-if="subtitleText">{{ subtitleText }}</span>
					</span>
				</div>

				<div class="flex items-center gap-2">
					<Button
						appearance="minimal"
						:disabled="!canReload"
						@click="reloadRoster"
					>
						{{ __('Reload') }}
					</Button>

					<div v-if="saving || justSaved" class="flex items-center gap-2 text-xs text-ink/60">
						<Spinner v-if="saving" class="h-4 w-4" />
						<span v-else class="inline-flex items-center gap-1">
							<FeatherIcon name="check" class="h-4 w-4 text-leaf" />
							{{ __('Saved') }}
						</span>
					</div>
				</div>
			</div>
		</section>

		<!-- Main layout -->
		<section class="grid gap-4 lg:grid-cols-[420px_minmax(0,1fr)]">
			<!-- Calendar -->
			<div class="rounded-2xl border border-border/70 bg-[rgb(var(--surface-rgb)/0.7)] shadow-soft">
				<AttendanceCalendar
					:month="calendarMonth"
					:meeting-dates="meetingDates"
					:recorded-dates="recordedDates"
					:selected-date="selectedDate"
					:available-months="availableMonths"
					:loading="calendarLoading"
					:weekend-days="weekendDays"
					@update:month="(d) => (calendarMonth = d)"
					@select="onPickDate"
				/>
			</div>

			<!-- Roster -->
			<div class="rounded-2xl border border-border/70 bg-[rgb(var(--surface-rgb)/0.7)] shadow-soft">
				<div class="flex items-center justify-between border-b border-border/60 px-5 py-4">
					<div class="min-w-0">
						<h2 class="text-base font-semibold text-ink">
							{{ selectedDate ? __('Roster for {0}', [selectedDate]) : __('Roster') }}
						</h2>
						<p class="mt-0.5 text-xs text-ink/60">
							{{ rosterHint }}
						</p>
					</div>

					<div class="flex items-center gap-2">
						<Button
							appearance="minimal"
							icon="message-circle"
							:disabled="!selectedDate || !filters.student_group || rosterLoading || bootLoading"
							@click="openRemarksHelp"
						>
							{{ __('Remark tips') }}
						</Button>
					</div>
				</div>

				<div v-if="bootLoading" class="flex items-center gap-3 px-5 py-6 text-sm text-ink/70">
					<Spinner class="h-5 w-5" />
					{{ __('Loading…') }}
				</div>

				<div v-else-if="!filters.student_group" class="px-5 py-6 text-sm text-ink/70">
					{{ __('Select a student group to begin.') }}
				</div>

				<div v-else-if="!selectedDate" class="px-5 py-6 text-sm text-ink/70">
					{{ __('Select a meeting day from the calendar.') }}
				</div>

				<div v-else class="min-h-[300px]">
					<div v-if="rosterLoading" class="flex items-center gap-3 px-5 py-6 text-sm text-ink/70">
						<Spinner class="h-5 w-5" />
						{{ __('Loading roster…') }}
					</div>

					<div v-else-if="students.length === 0" class="px-5 py-6 text-sm text-ink/70">
						{{ __('No students found for this group.') }}
					</div>

					<AttendanceGrid
						v-else
						:students="filteredStudents"
						:blocks="blocks"
						:codes="attendanceCodes"
						:disabled="submitting || bootLoading"
						:code-colors="codeColors"
						@change-code="onChangeCode"
						@open-remark="openRemark"
					/>
				</div>
			</div>
		</section>

		<!-- Remark Dialog -->
		<RemarkDialog
			v-model="remarkDialog.open"
			:student="remarkDialog.student"
			:block="remarkDialog.block"
			:value="remarkDialog.value"
			@save="saveRemark"
		/>

		<!-- Health Dialog -->
		<Dialog v-model="healthDialog.open" :options="{ title: healthDialog.title, size: 'lg' }">
			<div class="prose max-w-none text-sm" v-html="healthDialog.html" />
		</Dialog>

		<!-- Birthday Dialog -->
		<Dialog v-model="birthdayDialog.open" :options="{ title: __('Birthday'), size: 'sm' }">
			<div class="space-y-2 text-sm text-ink/80">
				<p class="font-semibold text-ink">
					{{ birthdayDialog.name }}
				</p>
				<p>
					{{ birthdayDialog.dateLabel }}
					<span v-if="birthdayDialog.age !== null" class="text-ink/60">• {{ __('Turning {0}', [birthdayDialog.age]) }}</span>
				</p>
			</div>
		</Dialog>
	</div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Button, FormControl, Badge, Dialog, FeatherIcon, Spinner } from 'frappe-ui'

import { __ } from '@/lib/i18n'
import AttendanceCalendar from './components/AttendanceCalendar.vue'
import AttendanceGrid from './components/AttendanceGrid.vue'
import RemarkDialog from './components/RemarkDialog.vue'

import { createStudentAttendanceService } from '@/lib/services/studentAttendance/studentAttendanceService'

// UI view-model types (page-owned)
import type { StudentRosterEntry, BlockKey } from './student-attendance-tool/types'

// Backend-owned contracts (service + page may use contract DTOs; services MUST use them)
import type { StudentAttendanceCodeRow, BulkUpsertAttendanceRow } from '@/types/contracts/studentAttendance'

// A+ invalidation bus (page is a refresh owner)
import { uiSignals, SIGNAL_ATTENDANCE_INVALIDATE } from '@/lib/uiSignals'

const SAVE_DEBOUNCE_MS = 900

const service = createStudentAttendanceService()

const route = useRoute()
const router = useRouter()

const errorBanner = ref<string | null>(null)

const bootLoading = ref(true)
const groupsLoading = ref(false)
const codesLoading = ref(false)
const calendarLoading = ref(false)
const rosterLoading = ref(false)
const saving = ref(false)
const submitting = ref(false)
const justSaved = ref(false)

let saveTimer: number | null = null

const filters = reactive({
	school: null as string | null,
	program: null as string | null,
	student_group: null as string | null,
	default_code: null as string | null,
})

const defaultSchool = ref<string | null>(null)

const schoolOptions = ref<Array<{ label: string; value: string }>>([])
const programOptions = ref<Array<{ label: string; value: string }>>([])
const groupOptions = ref<Array<{ label: string; value: string }>>([])

const attendanceCodes = ref<StudentAttendanceCodeRow[]>([])
const codeColors = computed(() => {
	const colors: Record<string, string> = {}
	for (const c of attendanceCodes.value) {
		colors[c.name] = c.color || '#2563eb'
	}
	return colors
})
const codeOptions = computed(() =>
	attendanceCodes.value.map((c) => ({
		label: c.attendance_code_name || c.attendance_code || c.name,
		value: c.name,
	}))
)

const meetingDates = ref<string[]>([])
const recordedDates = ref<string[]>([])
const availableMonths = computed(() => {
	const set = new Set<string>()
	for (const iso of meetingDates.value) {
		if (typeof iso === 'string' && iso.length >= 7) set.add(iso.slice(0, 7))
	}
	return [...set].sort()
})
const weekendDays = ref<number[]>([6, 0])

const selectedDate = ref<string | null>(null)
const calendarMonth = ref(new Date(new Date().getFullYear(), new Date().getMonth(), 1))

const students = ref<StudentRosterEntry[]>([])
const blocks = ref<BlockKey[]>([])
const groupInfo = ref<{ name?: string | null; program?: string | null; course?: string | null; cohort?: string | null }>({})

const lastSaved = ref<Record<string, Record<BlockKey, { code: string; remark: string }>>>({})
const dirty = ref<Set<string>>(new Set())

const remarkDialog = reactive({
	open: false,
	student: null as StudentRosterEntry | null,
	block: null as BlockKey | null,
	value: '',
})

const healthDialog = reactive({
	open: false,
	title: '',
	html: '',
})

const birthdayDialog = reactive({
	open: false,
	name: '',
	dateLabel: '',
	age: null as number | null,
})

const searchTerm = ref('')

const filteredStudents = computed(() => {
	const q = (searchTerm.value || '').trim().toLowerCase()
	if (!q) return students.value
	return students.value.filter((s) => {
		const name = (s.preferred_name || s.student_name || s.student).toLowerCase()
		return name.includes(q) || String(s.student).toLowerCase().includes(q)
	})
})

const groupLabel = computed(() => groupInfo.value?.name || '')
const subtitleText = computed(() => {
	const bits: string[] = []
	if (groupInfo.value?.program) bits.push(groupInfo.value.program)
	if (groupInfo.value?.course) bits.push(groupInfo.value.course)
	if (groupInfo.value?.cohort) bits.push(groupInfo.value.cohort)
	return bits.join(' • ')
})

const canReload = computed(() => !!filters.student_group && !!selectedDate.value && !rosterLoading.value && !bootLoading.value)
const canApplyDefault = computed(() => !!filters.default_code && !!filters.student_group && students.value.length > 0 && !rosterLoading.value)

const toolbarStatus = computed(() => {
	if (bootLoading.value) return __('Loading…')
	if (!filters.student_group) return __('Select a group')
	if (!selectedDate.value) return __('Select a meeting day')
	if (rosterLoading.value) return __('Loading roster…')
	if (saving.value) return __('Saving…')
	if (justSaved.value) return __('Saved')
	return __('Ready')
})

const statusVariant = computed(() => {
	if (bootLoading.value || rosterLoading.value || saving.value) return 'gray'
	if (justSaved.value) return 'green'
	if (!filters.student_group || !selectedDate.value) return 'orange'
	return 'blue'
})

const rosterHint = computed(() => {
	if (!filters.student_group) return __('Choose a student group first.')
	if (!selectedDate.value) return __('Pick a meeting day to load the roster.')
	if (rosterLoading.value) return __('Loading…')
	return __('Click a code chip to mark attendance. Use the remark icon for notes.')
})

function safeSetError(message: unknown) {
	errorBanner.value = typeof message === 'string' && message ? message : __('Unexpected error')
}

function pickInitialStudentGroupFromRoute(groups: Array<{ value: string }>) {
	const v = route.query.student_group
	const id = typeof v === 'string' && v ? v : null
	if (!id) return
	const exists = groups.some((g) => g.value === id)
	if (exists) filters.student_group = id
}

function pickDefaultDate(dates: string[]): string | null {
	if (!dates.length) return null

	const today = new Date()
	today.setHours(0, 0, 0, 0)

	const parsed = dates
		.map((iso) => ({ iso, date: new Date(`${iso}T00:00:00`) }))
		.filter((x) => !Number.isNaN(x.date.getTime()))
		.sort((a, b) => a.date.getTime() - b.date.getTime())

	const pastOrToday = parsed.filter((x) => x.date.getTime() <= today.getTime())
	return (pastOrToday[pastOrToday.length - 1] || parsed[0])?.iso ?? null
}

async function bootstrap() {
	bootLoading.value = true
	errorBanner.value = null

	try {
		const [ctx, programs, codes] = await Promise.all([
			service.fetchSchoolContext(),
			service.fetchPrograms(),
			service.listAttendanceCodes(),
		])

		defaultSchool.value = ctx.default_school
		schoolOptions.value = ctx.schools.map((s) => ({
			label: s.school_name || s.name,
			value: s.name,
		}))

		// Default school selection
		filters.school = ctx.default_school || ctx.schools[0]?.name || null

		programOptions.value = (programs || []).map((p) => ({
			label: p.program_name || p.name,
			value: p.name,
		}))

		attendanceCodes.value = (codes || []).slice().sort((a, b) => (a.display_order || 0) - (b.display_order || 0))
		filters.default_code = attendanceCodes.value[0]?.name || null

		await reloadGroups()
	} catch (err: any) {
		console.error('Attendance tool bootstrap failed', err)
		safeSetError(err?.message || err)
	} finally {
		bootLoading.value = false
	}
}

async function reloadGroups() {
	groupsLoading.value = true
	errorBanner.value = null

	// Reset group-dependent state
	groupOptions.value = []
	filters.student_group = null
	selectedDate.value = null
	meetingDates.value = []
	recordedDates.value = []
	students.value = []
	blocks.value = []
	groupInfo.value = {}

	try {
		const rows = await service.fetchStudentGroups({
			school: filters.school || defaultSchool.value,
			program: filters.program,
		})

		groupOptions.value = (rows || []).map((g) => ({
			label: g.student_group_name || g.name,
			value: g.name,
		}))

		pickInitialStudentGroupFromRoute(groupOptions.value)

		// Auto-pick if only one
		if (!filters.student_group && groupOptions.value.length === 1) {
			filters.student_group = groupOptions.value[0].value
		}
	} catch (err: any) {
		console.error('Failed to load student groups', err)
		safeSetError(err?.message || err)
	} finally {
		groupsLoading.value = false
	}
}

async function refreshRecordedDatesForCurrentGroup() {
	if (!filters.student_group) return
	try {
		const recorded = await service.getRecordedDates({ student_group: filters.student_group })
		recordedDates.value = Array.isArray(recorded) ? recorded : []
	} catch (err: any) {
		// Silent fail: this is a best-effort refresh hook; page still shows inline errors for core flows.
		console.error('Failed to refresh recorded dates', err)
	}
}

async function loadCalendarContext() {
	if (!filters.student_group) return

	calendarLoading.value = true
	errorBanner.value = null
	meetingDates.value = []
	recordedDates.value = []
	selectedDate.value = null

	try {
		const group = filters.student_group
		const [weekend, meetings, recorded] = await Promise.all([
			service.getWeekendDays({ student_group: group }),
			service.getMeetingDates({ student_group: group }),
			service.getRecordedDates({ student_group: group }),
		])

		weekendDays.value = Array.isArray(weekend) && weekend.length ? weekend : [6, 0]
		meetingDates.value = Array.isArray(meetings) ? meetings : []
		recordedDates.value = Array.isArray(recorded) ? recorded : []

		selectedDate.value = pickDefaultDate(meetingDates.value)
		if (selectedDate.value) {
			calendarMonth.value = new Date(`${selectedDate.value}T00:00:00`)
		}
	} catch (err: any) {
		console.error('Failed to load calendar context', err)
		safeSetError(err?.message || err)
	} finally {
		calendarLoading.value = false
	}
}

async function loadRoster() {
	if (!filters.student_group || !selectedDate.value) return

	rosterLoading.value = true
	errorBanner.value = null
	students.value = []
	blocks.value = []
	groupInfo.value = {}

	try {
		const { roster, prevMap, existingMap, blocks: blockKeys } = await service.fetchRosterContext({
			student_group: filters.student_group,
			attendance_date: selectedDate.value,
		})

		groupInfo.value = roster.group_info || {}
		blocks.value = Array.isArray(blockKeys) && blockKeys.length ? blockKeys : [-1]

		// Build student rows
		const built: StudentRosterEntry[] = (roster.students || []).map((s) => {
			const attendance: Record<BlockKey, string> = {}
			const remarks: Record<BlockKey, string> = {}

			for (const b of blocks.value) {
				const existing = existingMap?.[s.student]?.[b]
				const code = existing?.code || prevMap?.[`${s.student}|${b}`] || (filters.default_code || '')
				attendance[b] = code
				remarks[b] = existing?.remark || ''
			}

			return {
				student: s.student,
				student_name: s.student_name,
				preferred_name: s.preferred_name || null,
				student_image: s.student_image || null,
				birth_date: s.birth_date || null,
				medical_info: s.medical_info || null,
				blocks: blocks.value,
				attendance,
				remarks,
			}
		})

		students.value = built

		// Prime lastSaved snapshot
		const snapshot: Record<string, Record<BlockKey, { code: string; remark: string }>> = {}
		for (const s of built) {
			snapshot[s.student] = {}
			for (const b of blocks.value) {
				snapshot[s.student][b] = { code: s.attendance[b], remark: s.remarks[b] }
			}
		}
		lastSaved.value = snapshot
		dirty.value = new Set()
	} catch (err: any) {
		console.error('Failed to load roster', err)
		safeSetError(err?.message || err)
	} finally {
		rosterLoading.value = false
	}
}

function onPickDate(iso: string) {
	if (!iso || iso === selectedDate.value) return
	selectedDate.value = iso
	void loadRoster()
}

function reloadRoster() {
	if (!canReload.value) return
	void loadRoster()
}

function markDirty(studentId: string, block: BlockKey) {
	dirty.value.add(`${studentId}|${block}`)
	queueAutosave()
}

function onChangeCode(payload: { studentId: string; block: BlockKey; code: string }) {
	const s = students.value.find((x) => x.student === payload.studentId)
	if (!s) return
	s.attendance[payload.block] = payload.code
	markDirty(payload.studentId, payload.block)
}

function openRemark(payload: { student: StudentRosterEntry; block: BlockKey }) {
	remarkDialog.student = payload.student
	remarkDialog.block = payload.block
	remarkDialog.value = payload.student.remarks?.[payload.block] || ''
	remarkDialog.open = true
}

function saveRemark(value: string) {
	const s = remarkDialog.student
	const b = remarkDialog.block
	if (!s || b === null) return
	s.remarks[b] = value
	markDirty(s.student, b)
}

function applyDefaultCode() {
	if (!filters.default_code) return
	for (const s of students.value) {
		for (const b of blocks.value) {
			s.attendance[b] = filters.default_code
			markDirty(s.student, b)
		}
	}
}

function queueAutosave() {
	if (saveTimer) window.clearTimeout(saveTimer)
	saveTimer = window.setTimeout(() => {
		void persistChanges()
	}, SAVE_DEBOUNCE_MS)
}

async function persistChanges() {
	if (!filters.student_group || !selectedDate.value) return
	if (dirty.value.size === 0) return
	if (saving.value) return

	saving.value = true
	justSaved.value = false
	errorBanner.value = null

	try {
		const rows: BulkUpsertAttendanceRow[] = []

		for (const key of dirty.value) {
			const [studentId, blockStr] = key.split('|')
			const block = Number(blockStr)

			const s = students.value.find((x) => x.student === studentId)
			if (!s) continue

			rows.push({
				student: studentId,
				student_group: filters.student_group,
				attendance_date: selectedDate.value,
				block_number: Number.isFinite(block) ? block : -1,
				attendance_code: s.attendance[block as BlockKey] || '',
				remark: s.remarks[block as BlockKey] || '',
			})
		}

		await service.bulkUpsertAttendance({ payload: rows })

		// Commit local snapshot
		for (const r of rows) {
			lastSaved.value[r.student] = lastSaved.value[r.student] || {}
			lastSaved.value[r.student][r.block_number as BlockKey] = { code: r.attendance_code, remark: r.remark }
		}

		dirty.value = new Set()
		justSaved.value = true
		window.setTimeout(() => (justSaved.value = false), 1200)
	} catch (err: any) {
		console.error('Attendance autosave failed', err)
		safeSetError(err?.message || err)
	} finally {
		saving.value = false
	}
}

function beforeUnloadGuard(e: BeforeUnloadEvent) {
	if (dirty.value.size === 0) return
	e.preventDefault()
	e.returnValue = ''
}

function openRemarksHelp() {
	healthDialog.title = __('Remark guidelines')
	healthDialog.html = `
		<ul>
			<li>${__('Keep remarks factual and short.')}</li>
			<li>${__('Avoid sensitive medical details; use the health note workflow instead.')}</li>
			<li>${__('Stick to today’s context (date + block).')}</li>
		</ul>
	`
	healthDialog.open = true
}

/* -------------------- Watchers (A+ filter discipline) -------------------- */

let groupReloadTimer: number | null = null

watch(
	() => ({ school: filters.school, program: filters.program }),
	() => {
		if (bootLoading.value) return
		if (groupReloadTimer) window.clearTimeout(groupReloadTimer)
		groupReloadTimer = window.setTimeout(() => {
			void reloadGroups()
		}, 250)
	},
	{ deep: true }
)

watch(
	() => filters.student_group,
	async () => {
		if (bootLoading.value) return

		// Clear route param once consumed (avoid surprises when navigating back)
		if (route.query.student_group) {
			const q = { ...route.query }
			delete (q as any).student_group
			void router.replace({ query: q })
		}

		await loadCalendarContext()
		if (selectedDate.value) {
			await loadRoster()
		}
	}
)

/* -------------------- A+ uiSignals subscription (refresh-owner) -------------------- */

let unsubscribeAttendanceInvalidate: null | (() => void) = null
let attendanceInvalidateTimer: number | null = null

function onAttendanceInvalidated() {
	// Coalesce rapid emits (autosave can emit multiple times)
	if (attendanceInvalidateTimer) window.clearTimeout(attendanceInvalidateTimer)
	attendanceInvalidateTimer = window.setTimeout(() => {
		attendanceInvalidateTimer = null
		// Best-effort: only update the calendar badges (recorded days)
		void refreshRecordedDatesForCurrentGroup()
	}, 150)
}

onMounted(() => {
	window.addEventListener('beforeunload', beforeUnloadGuard)

	unsubscribeAttendanceInvalidate = uiSignals.subscribe(
		SIGNAL_ATTENDANCE_INVALIDATE,
		onAttendanceInvalidated,
	)

	void bootstrap()
})

onBeforeUnmount(() => {
	if (saveTimer) window.clearTimeout(saveTimer)
	if (attendanceInvalidateTimer) window.clearTimeout(attendanceInvalidateTimer)

	if (unsubscribeAttendanceInvalidate) {
		unsubscribeAttendanceInvalidate()
		unsubscribeAttendanceInvalidate = null
	}

	window.removeEventListener('beforeunload', beforeUnloadGuard)
})
</script>
