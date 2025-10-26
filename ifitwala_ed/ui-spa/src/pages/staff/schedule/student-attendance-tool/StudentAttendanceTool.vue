<template>
    <div class="mx-auto flex h-full max-w-7xl flex-col gap-6 p-4 pb-10">
        <header class="flex flex-wrap items-center justify-between gap-4">
            <div>
                <h1 class="text-2xl font-semibold tracking-tight text-slate-900">
                    {{ __('Student Attendance') }}
                </h1>
                <p class="text-sm text-slate-500">
                    {{ __('Track and submit attendance with a calendar-first workflow.') }}
                </p>
            </div>

            <div class="flex flex-wrap items-center gap-3">
                <FormControl
                    type="select"
                    class="min-w-[220px]"
                    :loading="groups.loading"
                    :disabled="groups.loading"
                    :options="groupOptions"
                    v-model="filters.student_group"
                    :placeholder="__('Select group')"
                    @update:modelValue="onGroupChange"
                />

                <FormControl
                    type="select"
                    class="min-w-[160px]"
                    :options="attendanceCodeOptions"
                    v-model="filters.default_code"
                    :disabled="!attendanceCodes.length"
                    @update:modelValue="onDefaultCodeChange"
                />

                <Button
                    appearance="secondary"
                    class="whitespace-nowrap"
                    :disabled="!students.length || submitting"
                    @click="applyDefaultCode"
                >
                    {{ __('Apply default to all') }}
                </Button>

                <Button
                    appearance="primary"
                    class="whitespace-nowrap"
                    :loading="submitting"
                    :disabled="!canSubmit"
                    @click="submitAttendance"
                >
                    {{ submitLabel }}
                </Button>
            </div>
        </header>

        <section class="grid gap-6 lg:grid-cols-5">
            <div class="lg:col-span-2">
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
            </div>

            <div class="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm lg:col-span-3">
                <div v-if="!filters.student_group" class="flex h-full flex-col items-center justify-center gap-3 text-center">
                    <FeatherIcon name="users" class="h-12 w-12 text-slate-300" />
                    <p class="text-base font-medium text-slate-600">
                        {{ __('Choose a student group to get started.') }}
                    </p>
                    <p class="text-sm text-slate-500">
                        {{ __('The calendar will show scheduled meeting days for the selected group.') }}
                    </p>
                </div>

                <template v-else>
                    <div class="flex flex-wrap items-center justify-between gap-2">
                        <div>
                            <h2 class="text-lg font-semibold text-slate-900">
                                {{ groupTitle }}
                            </h2>
                            <p v-if="groupSubtitle" class="text-xs uppercase tracking-wide text-slate-500">
                                {{ groupSubtitle }}
                            </p>
                        </div>
                        <Badge v-if="selectedDate" variant="subtle">{{ selectedDate }}</Badge>
                    </div>

                    <div v-if="calendarLoading" class="flex flex-col items-center justify-center gap-3 py-12 text-slate-500">
                        <Spinner class="h-6 w-6" />
                        <p>{{ __('Loading schedule…') }}</p>
                    </div>

                    <div v-else-if="!meetingDates.length" class="flex flex-col items-center justify-center gap-3 py-12 text-center text-slate-500">
                        <FeatherIcon name="calendar-x" class="h-12 w-12 text-slate-300" />
                        <p class="text-base font-medium">{{ __('No scheduled meetings found for this group.') }}</p>
                        <p class="max-w-sm text-sm">{{ __('Verify the School Schedule and rotation days for the student group.') }}</p>
                    </div>

                    <div v-else-if="!selectedDate" class="flex flex-col items-center justify-center gap-3 py-12 text-center text-slate-500">
                        <FeatherIcon name="calendar" class="h-12 w-12 text-slate-300" />
                        <p class="text-base font-medium">{{ __('Select a date from the calendar.') }}</p>
                        <p class="max-w-sm text-sm">{{ __('Only scheduled meeting days are selectable.') }}</p>
                    </div>

                    <div v-else class="flex-1">
                        <div v-if="rosterLoading" class="flex flex-col items-center justify-center gap-3 py-12 text-slate-500">
                            <Spinner class="h-6 w-6" />
                            <p>{{ __('Loading roster…') }}</p>
                        </div>
                        <div v-else-if="!students.length" class="flex flex-col items-center justify-center gap-3 py-12 text-slate-500">
                            <FeatherIcon name="search" class="h-12 w-12 text-slate-300" />
                            <p class="text-base font-medium">{{ __('No students found in this group.') }}</p>
                        </div>
                        <div v-else class="overflow-y-auto pr-2" style="max-height: 560px;">
                            <AttendanceGrid
                                :students="students"
                                :blocks="blocks"
                                :codes="attendanceCodes"
                                :code-colors="codeColors"
                                :disabled="submitting"
                                @change-code="onCodeChanged"
                                @open-remark="openRemark"
                                @show-medical="showMedical"
                            />
                        </div>
                    </div>
                </template>
            </div>
        </section>

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
import { Button, FormControl, Badge, FeatherIcon, Spinner, createResource, call, toast } from 'frappe-ui'
import AttendanceCalendar from './components/AttendanceCalendar.vue'
import AttendanceGrid from './components/AttendanceGrid.vue'
import RemarkDialog from './components/RemarkDialog.vue'
import type { AttendanceCode, StudentRosterEntry, BlockKey } from './types'

const DEFAULT_CODE_NAME = 'Present'

const filters = reactive({
    student_group: null as string | null,
    default_code: DEFAULT_CODE_NAME,
})

const calendarMonth = ref(new Date(new Date().getFullYear(), new Date().getMonth(), 1))
const meetingDates = ref<string[]>([])
const recordedDates = ref<string[]>([])
const selectedDate = ref<string | null>(null)
const calendarLoading = ref(false)

const students = ref<StudentRosterEntry[]>([])
const blocks = ref<BlockKey[]>([])
const rosterLoading = ref(false)
const submitting = ref(false)

const groupInfo = ref<{ name?: string | null; program?: string | null; course?: string | null; cohort?: string | null }>({})

const attendanceCodes = ref<AttendanceCode[]>([])

const remarkDialog = reactive({
    open: false,
    student: null as StudentRosterEntry | null,
    block: null as BlockKey | null,
    value: '',
})

const groups = createResource({
    url: 'api/method/ifitwala_ed.schedule.page.student_group_cards.student_group_cards.fetch_student_groups',
    auto: true,
    transform: (res: unknown) => unwrapMessage(res) ?? [],
})

const groupOptions = computed(() =>
    (groups.data || []).map((row: any) => ({
        label: row.student_group_name || row.name,
        value: row.name,
    }))
)

const attendanceCodeOptions = computed(() =>
    attendanceCodes.value.map((code) => ({
        label: code.attendance_code_name || code.name,
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

const hasExistingAttendance = computed(() => recordedDates.value.includes(selectedDate.value || ''))

function unwrapMessage(res: any) {
    if (res && typeof res === 'object' && 'message' in res) {
        return (res as any).message
    }
    return res
}

async function loadAttendanceCodes() {
    try {
        const response = await call('ifitwala_ed.schedule.attendance_utils.list_attendance_codes')
        attendanceCodes.value = unwrapMessage(response) ?? []
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

function onGroupChange() {
    selectedDate.value = null
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
        const blocksForDay: BlockKey[] = (unwrapMessage(blocksRes) ?? [])
        const normalizedBlocks = blocksForDay.length ? blocksForDay : [-1]

        groupInfo.value = roster.group_info || {}

        students.value = roster.students.map((stu: any) => {
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
        toast({
            title: __('Default applied'),
            message: __('Updated all students to {0}.', [filters.default_code]),
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
})
</script>
