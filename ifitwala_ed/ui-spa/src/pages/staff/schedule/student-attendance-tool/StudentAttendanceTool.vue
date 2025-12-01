<!-- ifitwala_ed/ui-spa/src/pages/staff/schedule/student-attendance-tool/StudentAttendanceTool.vue -->
<template>
  <div class="staff-shell flex h-full flex-col gap-6">
    <header class="flex flex-col gap-4">
      <div
        class="surface-toolbar flex items-center gap-2 overflow-x-auto no-scrollbar"
      >
        <div class="w-44 shrink-0">
          <FormControl
            type="select"
            size="md"
            :options="schoolOptions"
            option-label="label"
            option-value="value"
            :model-value="filters.school"
            :disabled="schoolsLoading || !schoolOptions.length"
            placeholder="School"
            @update:modelValue="onSchoolSelected"
          />
        </div>

        <div class="w-44 shrink-0">
          <FormControl
            type="select"
            size="md"
            :options="programOptions"
            option-label="label"
            option-value="value"
            :model-value="filters.program"
            :disabled="programsLoading || !programOptions.length"
            placeholder="Program"
            @update:modelValue="onProgramSelected"
          />
        </div>

        <div class="w-64 shrink-0">
          <FormControl
            type="select"
            size="md"
            :options="groupOptions"
            option-label="label"
            option-value="value"
            :model-value="filters.student_group"
            @update:modelValue="onStudentGroupChange"
            :disabled="groupsLoading || !groupOptions.length"
            placeholder="Select Group"
          />
        </div>

        <div class="w-32 shrink-0">
          <FormControl
            type="select"
            size="md"
            :options="defaultCodeOptions"
            option-label="label"
            option-value="value"
            :model-value="filters.default_code"
            :disabled="codesLoading || !attendanceCodes.length"
            @update:modelValue="onDefaultCodeChange"
          />
        </div>

        <Button
          appearance="secondary"
          class="shrink-0 whitespace-nowrap"
          :disabled="!students.length || submitting"
          @click="applyDefaultCode"
        >
          {{ __('Mark Default') }}
        </Button>
      </div>
    </header>

    <div class="grid gap-6 xl:grid-cols-[minmax(0,3fr)_minmax(280px,1fr)]">
      <!-- MAIN ATTENDANCE PANEL -->
      <section class="card-panel flex flex-col overflow-hidden">
        <div
          class="flex flex-wrap items-center justify-between gap-3 border-b border-border/60 bg-surface/80 px-5 py-4"
        >
          <div class="min-w-0">
            <h2 class="text-lg font-semibold text-ink">
              {{ filters.student_group ? groupTitle : __('Select a student group') }}
            </h2>
            <p
              v-if="filters.student_group && groupSubtitle"
              class="text-xs uppercase tracking-wide text-ink/60"
            >
              {{ groupSubtitle }}
            </p>
            <p v-else class="text-sm text-ink/70">
              {{ __('Choose a group to load today’s roster.') }}
            </p>
          </div>

          <div class="flex flex-wrap items-center gap-2">
            <Badge v-if="selectedDateLabel" variant="subtle" class="text-sm font-medium text-ink">
              {{ selectedDateLabel }}
            </Badge>
            <Button
              appearance="minimal"
              icon="refresh-ccw"
              :disabled="!canReload"
              @click="reloadRoster"
            >
              {{ __('Refresh') }}
            </Button>
            <span v-if="saving" class="text-xs text-ink/60">{{ __('Saving…') }}</span>
            <span v-else-if="justSaved" class="text-xs text-canopy">{{ __('Saved') }}</span>
          </div>
        </div>

        <div
          class="flex flex-wrap items-center gap-3 border-b border-border/60 bg-surface/60 px-5 py-3"
        >
          <FormControl
            v-model="searchTerm"
            type="text"
            class="w-full flex-1 md:max-w-xs"
            :disabled="!filters.student_group || rosterLoading || !students.length"
            :placeholder="__('Search students')"
          />

          <div v-if="filters.student_group" class="ml-auto text-xs text-ink/70">
            <span v-if="filteredStudents.length !== students.length">
              {{ __('Showing {0} of {1}', [filteredStudents.length, students.length]) }}
            </span>
            <span v-else>
              {{ __('Total students: {0}', [students.length]) }}
            </span>
          </div>
        </div>

        <div class="flex-1 overflow-hidden bg-surface/80">
          <!-- Empty / loading / state views -->
          <div
            v-if="!filters.student_group"
            class="flex h-full flex-col items-center justify-center gap-3 px-8 py-16 text-center text-ink/70"
          >
            <FeatherIcon name="users" class="h-12 w-12 text-ink/30" />
            <p class="text-base font-semibold text-ink">
              {{ __('Select a student group to begin taking attendance.') }}
            </p>
            <p class="max-w-sm text-sm">
              {{
                __(
                  'Meeting days appear in the calendar, and recorded sessions are highlighted for quick reference.'
                )
              }}
            </p>
          </div>

          <div
            v-else-if="calendarLoading"
            class="flex h-full flex-col items-center justify-center gap-3 py-12 text-ink/70"
          >
            <Spinner class="h-6 w-6" />
            <p>{{ __('Loading schedule…') }}</p>
          </div>

          <div
            v-else-if="!meetingDates.length"
            class="flex h-full flex-col items-center justify-center gap-3 px-8 py-16 text-center text-ink/70"
          >
            <FeatherIcon name="calendar-x" class="h-12 w-12 text-ink/30" />
            <p class="text-base font-semibold text-ink">
              {{ __('No scheduled meetings found for this group.') }}
            </p>
            <p class="max-w-sm text-sm text-ink/70">
              {{ __('Update the Student Group Schedule to add meeting days for this group.') }}
            </p>
          </div>

          <div
            v-else-if="!selectedDate"
            class="flex h-full flex-col items-center justify-center gap-3 px-8 py-16 text-center text-ink/70"
          >
            <FeatherIcon name="calendar" class="h-12 w-12 text-ink/30" />
            <p class="text-base font-semibold text-ink">
              {{ __('Select a date from the calendar to record attendance.') }}
            </p>
            <p class="max-w-sm text-sm text-ink/70">
              {{ __('Only scheduled meeting days are selectable.') }}
            </p>
          </div>

          <!-- Date selected -->
          <div v-else class="flex h-full flex-col">
            <div
              v-if="rosterLoading"
              class="flex h-full flex-col items-center justify-center gap-3 py-12 text-ink/70"
            >
              <Spinner class="h-6 w-6" />
              <p>{{ __('Loading roster…') }}</p>
            </div>

            <div
              v-else-if="!students.length"
              class="flex h-full flex-col items-center justify-center gap-3 px-8 py-16 text-center text-ink/70"
            >
              <FeatherIcon name="search" class="h-12 w-12 text-ink/30" />
              <p class="text-base font-semibold text-ink">
                {{ __('No students found in this group.') }}
              </p>
            </div>

            <div v-else-if="isMeetingDay" class="flex h-full flex-col overflow-hidden">
              <div
                v-if="!filteredStudents.length"
                class="flex h-full flex-col items-center justify-center gap-3 px-8 py-16 text-center text-ink/70"
              >
                <FeatherIcon name="filter" class="h-12 w-12 text-ink/30" />
                <p class="text-base font-semibold text-ink">
                  {{ __('No students match your search.') }}
                </p>
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
                  @show-birthday="showBirthday"
                />
              </div>

              <div
                class="border-t border-border/60 bg-surface/70 px-5 py-3 text-xs text-ink/70"
              >
                {{ __('Students loaded: {0}', [students.length]) }}
                <span v-if="hasExistingAttendance" class="ml-2 text-canopy">
                  {{ __('Existing attendance found for this date.') }}
                </span>
              </div>
            </div>

            <div
              v-else
              class="flex h-full flex-col items-center justify-center gap-3 px-8 py-16 text-center text-ink"
            >
              <FeatherIcon name="alert-triangle" class="h-12 w-12 text-ink/40" />
              <p class="text-base font-semibold text-ink">
                {{ __('This group is not scheduled to meet on this date.') }}
              </p>
              <p class="max-w-sm text-sm text-ink/70">
                {{ __('Select another meeting day from the calendar to record attendance.') }}
              </p>
            </div>
          </div>
        </div>
      </section>

      <!-- SIDEBAR -->
      <aside class="flex flex-col gap-4">
        <AttendanceCalendar
          :month="calendarMonth"
          :meeting-dates="meetingDates"
          :recorded-dates="recordedDates"
          :available-months="availableMonths"
          :selected-date="selectedDate"
          :loading="calendarLoading"
          :weekend-days="weekendDays"
          @update:month="(month) => (calendarMonth = month)"
          @update:selected-date="onDateSelected"
        />

        <div class="palette-card p-4">
          <h3 class="text-sm font-semibold text-ink">
            {{ __('Attendance codes') }}
          </h3>
          <p class="mt-1 text-xs text-ink/70">
            {{ __('Tap a chip to apply the code for the selected student and block.') }}
          </p>

          <div class="mt-3 flex flex-wrap gap-2">
            <div
              v-for="code in attendanceCodes"
              :key="code.name"
              class="flex items-center gap-2 rounded-full border border-border/80 bg-sand/60 px-3 py-1 text-xs"
              :style="{
                borderColor: code.color || '#cbd5f5',
                backgroundColor: withAlpha(code.color || '#2563eb', 0.12),
              }"
            >
              <span
                class="flex h-6 w-6 items-center justify-center rounded-full text-xs font-semibold text-white shadow-sm"
                :style="{ backgroundColor: code.color || '#2563eb' }"
              >
                {{ code.attendance_code || code.name?.charAt(0) }}
              </span>
              <span class="text-ink/80">
                {{ code.attendance_code_name || code.name }}
              </span>
            </div>
          </div>

          <div v-if="selectedDate && dailyTotals.length" class="mt-4 space-y-2">
            <h4 class="text-xs font-semibold uppercase tracking-wide text-ink/60">
              {{ __('Today’s tally') }}
            </h4>
            <div class="space-y-1 text-sm text-ink/80">
              <div
                v-for="entry in dailyTotals"
                :key="entry.code.name"
                class="flex items-center justify-between gap-2"
              >
                <span>{{ entry.code.attendance_code_name || entry.code.name }}</span>
                <span class="font-semibold">{{ entry.count }}</span>
              </div>
            </div>
          </div>
        </div>

        <div v-if="filters.student_group" class="palette-card p-4">
          <h3 class="text-sm font-semibold text-ink">
            {{ __('Group details') }}
          </h3>
          <dl class="mt-3 space-y-2 text-sm text-ink/80">
            <div v-if="groupInfo.name" class="flex justify-between gap-2 text-ink">
              <dt class="text-ink/60">{{ __('Group') }}</dt>
              <dd class="text-right font-medium text-ink">
                {{ groupInfo.name }}
              </dd>
            </div>
            <div v-if="groupInfo.program" class="flex justify-between gap-2 text-ink">
              <dt class="text-ink/60">{{ __('Program') }}</dt>
              <dd class="text-right font-medium">
                {{ groupInfo.program }}
              </dd>
            </div>
            <div v-if="groupInfo.course" class="flex justify-between gap-2 text-ink">
              <dt class="text-ink/60">{{ __('Course') }}</dt>
              <dd class="text-right font-medium">
                {{ groupInfo.course }}
              </dd>
            </div>
            <div v-if="groupInfo.cohort" class="flex justify-between gap-2 text-ink">
              <dt class="text-ink/60">{{ __('Cohort') }}</dt>
              <dd class="text-right font-medium">
                {{ groupInfo.cohort }}
              </dd>
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

    <Dialog
      v-model="healthDialog.open"
      :options="{ title: healthDialog.title || __('Medical Info'), size: 'md' }"
    >
      <template #body>
        <div class="prose prose-sm max-w-none text-ink">
          <div v-if="healthDialog.html" v-html="healthDialog.html"></div>
          <p v-else class="text-ink/70">
            {{ __('No medical information available.') }}
          </p>
        </div>
      </template>
    </Dialog>

    <Dialog
      v-model="birthdayDialog.open"
      :options="{ title: __('Birthday'), size: 'sm' }"
    >
      <template #body>
        <div class="space-y-1 text-ink">
          <p class="text-sm font-semibold">
            {{ birthdayDialog.name }}
          </p>
          <p class="text-sm">
            {{ birthdayDialog.dateLabel }}
            <span v-if="birthdayDialog.age !== null">
              · {{ birthdayDialog.age }} {{ __('years old') }}
            </span>
          </p>
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
/* 100% unchanged script */
import { computed, reactive, ref, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Button, FormControl, Badge, Dialog, FeatherIcon, Spinner, call, toast, createResource } from 'frappe-ui'
import { __ } from '@/lib/i18n'
import AttendanceCalendar from './components/AttendanceCalendar.vue'
import AttendanceGrid from './components/AttendanceGrid.vue'
import RemarkDialog from './components/RemarkDialog.vue'
import type { AttendanceCode, StudentRosterEntry, BlockKey } from './types'

const DEFAULT_CODE_NAME = 'Present'
const DEFAULT_COLOR = '#2563eb'
const SAVE_DEBOUNCE_MS = 700

const filters = reactive({
  school: null as string | null,
  program: null as string | null,
  student_group: null as string | null,
  default_code: DEFAULT_CODE_NAME,
})

const defaultSchool = ref<string | null>(null)

const route = useRoute()
const router = useRouter()

function routeStudentGroupParam(): string | null {
  const value = route.query.student_group
  return typeof value === 'string' && value ? value : null
}

const initialRouteGroup = ref<string | null>(routeStudentGroupParam())

const searchTerm = ref('')
const calendarMonth = ref(new Date(new Date().getFullYear(), new Date().getMonth(), 1))
const meetingDates = ref<string[]>([])
const recordedDates = ref<string[]>([])
const selectedDate = ref<string | null>(null)
const calendarLoading = ref(false)
const weekendDays = ref<number[]>([6, 0]) // default; will be replaced from server

const students = ref<StudentRosterEntry[]>([])
const blocks = ref<BlockKey[]>([])
const rosterLoading = ref(false)
const submitting = ref(false)
const saving = ref(false)
const justSaved = ref(false)
let saveTimer: number | null = null

// lastSaved[student][block] = { code, remark }
const lastSaved = ref<Record<string, Record<BlockKey, { code: string; remark: string }>>>({})
// set of "student|block" keys needing save
const dirty = ref<Set<string>>(new Set())

const groupInfo = ref<{ name?: string | null; program?: string | null; course?: string | null; cohort?: string | null }>({})

const attendanceCodes = ref<AttendanceCode[]>([])

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

const groups = ref<any[]>([])
const schools = ref<any[]>([])
const programs = ref<any[]>([])
const hasWarnedEmptyGroups = ref(false)

const schoolResource = createResource({
  url: 'ifitwala_ed.api.student_attendance.fetch_school_filter_context',
  cache: 'school-filter-context',
  method: 'POST',
  auto: true,
  transform: unwrapMessage,
  onSuccess: onSchoolsLoaded,
  onError: () => {
    notify({
      title: __('Could not load schools'),
      message: __('Please refresh or choose a student group directly.'),
      appearance: 'danger',
    })
  },
})

const programResource = createResource({
  url: 'ifitwala_ed.api.student_attendance.fetch_active_programs',
  cache: 'active-programs',
  method: 'POST',
  auto: true,
  transform: unwrapMessage,
  onSuccess: onProgramsLoaded,
  onError: () => {
    notify({
      title: __('Could not load programs'),
      message: __('Please refresh to try again.'),
      appearance: 'danger',
    })
  },
})

const groupResource = createResource({
  url: 'ifitwala_ed.api.student_attendance.fetch_portal_student_groups',
  params: () => ({
    school: filters.school || defaultSchool.value,
    program: filters.program,
  }),
  method: 'POST',
  watch: [() => filters.school, () => filters.program],
  immediate: true,
  auto: true,
  transform: unwrapMessage,
  onSuccess: onGroupsLoaded,
  onError: () => {
    groups.value = []
    notify({
      title: __('Could not load student groups'),
      message: __('Please refresh or contact your administrator.'),
      appearance: 'danger',
    })
  },
})

const attendanceCodeResource = createResource({
  url: 'ifitwala_ed.schedule.attendance_utils.list_attendance_codes',
  method: 'POST',
  auto: true,
  transform: unwrapMessage,
  onSuccess: onAttendanceCodesLoaded,
  onError: () => {
    notify({
      title: __('Could not load attendance codes'),
      appearance: 'danger',
    })
  },
})

const weekendResource = createResource({
  url: 'ifitwala_ed.api.student_attendance.get_weekend_days',
  params: () => ({
    student_group: filters.student_group,
  }),
  method: 'POST',
  auto: false,
  transform: unwrapMessage,
  onSuccess: (days) => {
    if (Array.isArray(days) && days.length) {
      weekendDays.value = days
        .map((d: any) => Number(d))
        .filter((n: number) => Number.isInteger(n) && n >= 0 && n <= 6)
    } else {
      weekendDays.value = [6, 0]
    }
  },
  onError: () => {
    weekendDays.value = [6, 0]
  },
})

const meetingDatesResource = createResource({
  url: 'ifitwala_ed.schedule.attendance_utils.get_meeting_dates',
  method: 'GET',
  auto: false,
  makeParams() {
    return {
      student_group: filters.student_group,
    }
  },
  transform: unwrapMessage,
  onSuccess(dates) {
    const arr = Array.isArray(dates) ? dates : []
    meetingDates.value = arr
    console.log('meeting dates loaded', filters.student_group, arr)
  },
  onError() {
    meetingDates.value = []
  },
})

const recordedDatesResource = createResource({
  url: 'ifitwala_ed.schedule.attendance_utils.attendance_recorded_dates',
  method: 'GET',
  auto: false,
  makeParams() {
    return {
      student_group: filters.student_group,
    }
  },
  transform: unwrapMessage,
  onSuccess(dates) {
    const arr = Array.isArray(dates) ? dates : []
    recordedDates.value = arr
    console.log('recorded dates loaded', filters.student_group, arr)
  },
  onError() {
    recordedDates.value = []
  },
})

const schoolsLoading = computed(() => schoolResource.loading)
const programsLoading = computed(() => programResource.loading)
const groupsLoading = computed(() => groupResource.loading)
const codesLoading = computed(() => attendanceCodeResource.loading)

const groupOptions = computed(() =>
  (groups.value || []).map((row: any) => ({
    label: row.student_group_name || row.name,
    value: row.name,
  })),
)

const schoolOptions = computed(() => {
  const base = (schools.value || []).map((row: any) => ({
    label: row.school_name || row.name,
    value: row.name,
  }))

  if (defaultSchool.value) {
    return base
  }

  return base.length
    ? [
        { label: __('All schools'), value: null },
        ...base,
      ]
    : base
})

const programOptions = computed(() => {
  const base = (programs.value || []).map((row: any) => ({
    label: row.program_name || row.name,
    value: row.name,
  }))
  return [
    { label: __('All programs'), value: null },
    ...base,
  ]
})

const defaultCodeOptions = computed(() =>
  attendanceCodes.value.map((code) => ({
    label: code.attendance_code
      ? `${code.attendance_code} · ${code.attendance_code_name || code.name}`
      : code.attendance_code_name || code.name,
    value: code.name,
  })),
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
const isMeetingDay = computed(() => (selectedDate.value ? meetingDates.value.includes(selectedDate.value) : false))
const canSubmit = computed(() => !!(filters.student_group && selectedDate.value && students.value.length && isMeetingDay.value))
const canReload = computed(() => !!(filters.student_group && selectedDate.value && !calendarLoading.value))
const hasExistingAttendance = computed(() => recordedDates.value.includes(selectedDate.value || ''))

const filteredStudents = computed(() => {
  if (!searchTerm.value) {
    return students.value
  }
  const q = searchTerm.value.toLowerCase().trim()
  return students.value.filter((stu) => {
    const haystack = [stu.student, stu.student_name, stu.preferred_name]
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

function withAlpha(hex: string, alpha: number) {
  if (!hex) return `rgb(37 99 235 / ${alpha})`

  const value = hex.replace('#', '')
  if (value.length !== 6) {
    return `rgb(37 99 235 / ${alpha})`
  }

  const r = parseInt(value.substring(0, 2), 16)
  const g = parseInt(value.substring(2, 4), 16)
  const b = parseInt(value.substring(4, 6), 16)

  // Modern CSS syntax, matches what we did elsewhere
  return `rgb(${r} ${g} ${b} / ${alpha})`
}


function unwrapMessage(res: any) {
  if (res && typeof res === 'object' && 'message' in res) {
    return (res as any).message
  }
  return res
}

function notify(payload: any) {
  if (typeof toast === 'function') {
    return toast(payload)
  }
  console.warn('Toast unavailable', payload)
}

function setRouteStudentGroupQuery(groupName: string | null) {
  const current = routeStudentGroupParam()
  if (current === groupName || (!current && !groupName)) {
    return
  }
  const nextQuery = { ...route.query }
  if (groupName) {
    nextQuery.student_group = groupName
  } else {
    delete nextQuery.student_group
  }
  router.replace({ query: nextQuery }).catch(() => {})
}

function onSchoolsLoaded(payload: any) {
  const data = payload || {}
  const rows = Array.isArray(data.schools) ? data.schools : []
  schools.value = rows
  defaultSchool.value = data.default_school || null

  const schoolNames = rows.map((row: any) => row.name)
  const preferred =
    defaultSchool.value && schoolNames.includes(defaultSchool.value)
      ? defaultSchool.value
      : schoolNames[0] || null

  if (!filters.school || !schoolNames.includes(filters.school)) {
    filters.school = preferred
  }
}

function onProgramsLoaded(payload: any) {
  programs.value = Array.isArray(payload) ? payload : []
}

function onGroupsLoaded(payload: any) {
  const list = Array.isArray(payload) ? payload : []
  groups.value = list
  const names = list.map((g: any) => g.name)

  if (initialRouteGroup.value) {
    if (names.includes(initialRouteGroup.value)) {
      void selectStudentGroup(initialRouteGroup.value, { updateRoute: false })
    }
    initialRouteGroup.value = null
  }

  if (filters.student_group && names.includes(filters.student_group)) {
    return
  }

  if (filters.student_group && !names.includes(filters.student_group)) {
    void selectStudentGroup(null)
    return
  }

  if (!filters.student_group && list.length === 1) {
    void selectStudentGroup(list[0].name)
    return
  }

  if (!list.length && hasWarnedEmptyGroups.value) {
    return
  }
  if (!list.length) {
    hasWarnedEmptyGroups.value = true
    notify({
      title: __('No student groups found'),
      message: __('You have no active student groups assigned.'),
      appearance: 'warning',
    })
  }
}

function onAttendanceCodesLoaded(items: any) {
  const rows = Array.isArray(items) ? items : []
  attendanceCodes.value = rows.map((row: any) => ({
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
}

function clearGroupState() {
  selectedDate.value = null
  searchTerm.value = ''
  meetingDates.value = []
  recordedDates.value = []
  groupInfo.value = {}
  students.value = []
  blocks.value = []
  lastSaved.value = {}
  dirty.value.clear()
  saving.value = false
  justSaved.value = false
  weekendDays.value = [6, 0]
}

async function onSchoolSelected(value: string | null) {
  if (filters.school === value) return
  if (saveTimer) window.clearTimeout(saveTimer)
  if (dirty.value.size) {
    await persistChanges()
  }
  filters.school = value
  filters.program = null
  filters.student_group = null
  setRouteStudentGroupQuery(null)
  clearGroupState()
  await groupResource.reload()
}

async function onProgramSelected(value: string | null) {
  if (filters.program === value) return
  if (saveTimer) window.clearTimeout(saveTimer)
  if (dirty.value.size) {
    await persistChanges()
  }
  filters.program = value
  filters.student_group = null
  setRouteStudentGroupQuery(null)
  clearGroupState()
  await groupResource.reload()
}

async function onStudentGroupChange(value: string | null) {
  await selectStudentGroup(value)
}

function onDefaultCodeChange(value: string) {
  if (filters.default_code === value) return
  filters.default_code = value
  applyDefaultCode({ silent: true })
}

async function selectStudentGroup(groupName: string | null, options: { updateRoute?: boolean } = {}) {
  const current = filters.student_group
  if (current === groupName) return

  if (saveTimer) window.clearTimeout(saveTimer)
  if (dirty.value.size) {
    await persistChanges()
  }

  filters.student_group = groupName
  if (options.updateRoute !== false) {
    setRouteStudentGroupQuery(groupName)
  }

  clearGroupState()

  if (!groupName) {
    return
  }

  await groupResource.reload()
  await loadWeekendAndSchedule()
}

async function loadWeekendAndSchedule() {
  try {
    await weekendResource.reload()
  } catch {
    weekendDays.value = [6, 0]
  }
  await loadCalendarData({ preserveSelection: false })
}

async function loadCalendarData(options: { preserveSelection?: boolean } = {}) {
  if (!filters.student_group) return
  const preserveSelection = options.preserveSelection ?? false
  calendarLoading.value = true
  try {
    await Promise.all([meetingDatesResource.reload(), recordedDatesResource.reload()])

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
    notify({
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

    students.value = (roster.students || []).map((stu: any) => {
      const studentEntry: StudentRosterEntry = {
        student: stu.student,
        student_name: stu.student_name,
        preferred_name: stu.preferred_name,
        student_image: stu.student_image,
        birth_date: stu.birth_date || stu.student_date_of_birth || null,
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
    lastSaved.value = snapshotFromExisting(existingMap, normalizedBlocks)
    dirty.value.clear()
  } catch (error) {
    console.error('Failed to load roster', error)
    notify({
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

function keyOf(studentId: string, block: BlockKey) {
  return `${studentId}|${block}`
}

function snapshotFromExisting(existingMap: any, blocksForDay: BlockKey[]) {
  const snap: Record<string, Record<BlockKey, { code: string; remark: string }>> = {}
  for (const student of students.value) {
    const sId = student.student
    snap[sId] = {} as any
    for (const b of blocksForDay) {
      const ex = existingMap?.[sId]?.[b]
      snap[sId][b] = {
        code: ex?.code || '',
        remark: ex?.remark || '',
      }
    }
  }
  return snap
}

function markDirty(studentId: string, block: BlockKey) {
  if (!filters.student_group || !selectedDate.value) return
  dirty.value.add(keyOf(studentId, block))
  scheduleSave()
}

function scheduleSave() {
  if (saveTimer) {
    window.clearTimeout(saveTimer)
  }
  saveTimer = window.setTimeout(() => {
    void persistChanges()
  }, SAVE_DEBOUNCE_MS)
}

async function onDateSelected(date: string) {
  if (saveTimer) window.clearTimeout(saveTimer)
  if (dirty.value.size) {
    await persistChanges()
  }
  dirty.value.clear()
  selectedDate.value = date
  await loadRoster()
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
  markDirty(payload.studentId, payload.block)
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
  markDirty(remarkDialog.student.student, remarkDialog.block)
}

function applyDefaultCode(options: { silent?: boolean } = {}) {
  if (!filters.default_code || !students.value.length) return
  for (const student of students.value) {
    for (const block of blocks.value) {
      student.attendance[block] = filters.default_code
      markDirty(student.student, block)
    }
  }
  if (!options.silent) {
    const code = codeDictionary.value[filters.default_code]
    const label = code?.attendance_code_name || filters.default_code
    notify({
      title: __('Default applied'),
      message: __('Updated all students to {0}.', [label]),
      appearance: 'info',
    })
  }
}

async function persistChanges() {
  if (!filters.student_group || !selectedDate.value) return
  if (!dirty.value.size) return
  saving.value = true
  justSaved.value = false
  try {
    const payload: any[] = []
    for (const k of Array.from(dirty.value)) {
      const [studentId, blockStr] = k.split('|')
      const block = Number(blockStr) as BlockKey
      const s = students.value.find((x) => x.student === studentId)
      if (!s) continue
      const nowCode = s.attendance[block] || ''
      const nowRemark = s.remarks[block] || ''
      const prev = lastSaved.value?.[studentId]?.[block] || { code: '', remark: '' }
      if (nowCode !== prev.code || nowRemark !== prev.remark) {
        payload.push({
          student: studentId,
          student_group: filters.student_group,
          attendance_date: selectedDate.value,
          block_number: block,
          attendance_code: nowCode,
          remark: nowRemark,
        })
      }
    }
    if (!payload.length) {
      dirty.value.clear()
      saving.value = false
      return
    }
    await call('ifitwala_ed.schedule.attendance_utils.bulk_upsert_attendance', { payload })
    for (const row of payload) {
      lastSaved.value[row.student] = lastSaved.value[row.student] || ({} as any)
      lastSaved.value[row.student][row.block_number] = {
        code: row.attendance_code || '',
        remark: row.remark || '',
      }
      dirty.value.delete(keyOf(row.student, row.block_number))
    }

    if (selectedDate.value && !recordedDates.value.includes(selectedDate.value)) {
      recordedDates.value = [...recordedDates.value, selectedDate.value].sort()
    }

    justSaved.value = true
    window.setTimeout(() => (justSaved.value = false), 1200)
  } catch (error: any) {
    console.error('Failed to autosave attendance', error)
    notify({
      title: __('Autosave failed'),
      message: error?.message || __('Please try again.'),
      appearance: 'danger',
    })
  } finally {
    saving.value = false
  }
}

function showMedical(student: StudentRosterEntry) {
  const html = formatMedicalInfo(student?.medical_info || '')
  if (!html) {
    notify({
      title: __('No medical info'),
      message: __('There is no medical information for this student.'),
      appearance: 'info',
    })
    return
  }

  healthDialog.title = __('Medical Info')
  healthDialog.html = html
  healthDialog.open = true
}

function formatMedicalInfo(input: string) {
  const raw = String(input || '')
  const plain = raw.replace(/<[^>]*>/g, ' ').replace(/&nbsp;/gi, ' ').trim()
  if (!plain) return ''
  let safe = raw
    .replace(/<\s*(script|style)[^>]*>[\s\S]*?<\s*\/\s*\1\s*>/gi, '')
    .replace(/\son\w+="[^"]*"/gi, '')
    .replace(/\son\w+='[^']*'/gi, '')
    .replace(/\sjavascript:/gi, '')
  return safe
}

function showBirthday(student: StudentRosterEntry) {
  const dob = student.birth_date
  if (!dob) return
  try {
    const d = new Date(dob + 'T00:00:00')
    const dateLabel = new Intl.DateTimeFormat(undefined, { dateStyle: 'long' }).format(d)
    const today = new Date()
    let age: number | null = today.getFullYear() - d.getFullYear()
    const m = today.getMonth() - d.getMonth()
    if (m < 0 || (m === 0 && today.getDate() < d.getDate())) age--
    birthdayDialog.name = student.preferred_name || student.student_name || student.student
    birthdayDialog.dateLabel = dateLabel
    birthdayDialog.age = Number.isFinite(age) ? age : null
    birthdayDialog.open = true
  } catch {
    // ignore
  }
}

function beforeUnloadGuard(e: BeforeUnloadEvent) {
  if (saving.value || dirty.value.size) {
    if (dirty.value.size) {
      void persistChanges()
    }
    e.preventDefault()
    e.returnValue = ''
  }
}

onMounted(() => {
  window.addEventListener('beforeunload', beforeUnloadGuard)
})

onBeforeUnmount(() => {
  window.removeEventListener('beforeunload', beforeUnloadGuard)
})
</script>

