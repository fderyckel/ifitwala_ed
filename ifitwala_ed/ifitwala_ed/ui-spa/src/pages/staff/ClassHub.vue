<template>
  <div class="staff-shell space-y-6">
    <ClassHubHeader
      :header="currentBundle.header"
      :now="currentBundle.now"
      :session="currentBundle.session"
      @start="handleStartSession"
      @quick-evidence="openQuickEvidence"
      @end="handleEndSession"
    />

    <div v-if="actionMessage" class="rounded-xl border border-slate-200 bg-white/90 px-4 py-3">
      <p class="type-caption text-flame">{{ actionMessage }}</p>
    </div>

    <TodayList :items="currentBundle.today_items" @open="openTodayItem" />

    <FocusStudentsRow :students="currentBundle.focus_students" @open="openFocusStudent" />

    <StudentsGrid :students="currentBundle.students" @open="openStudent" />

    <MyTeachingPanel
      :notes="currentBundle.notes_preview"
      :tasks="currentBundle.task_items"
      @add-note="openQuickEvidence"
      @open-note="openNote"
      @open-task="openTask"
    />

    <ClassPulse :items="currentBundle.pulse_items" />

    <FollowUpsList :items="currentBundle.follow_up_items" @open="openFollowUp" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import { useOverlayStack } from '@/composables/useOverlayStack'
import { createClassHubService } from '@/lib/classHubService'
import type { ClassHubBundle } from '@/types/classHub'

import ClassHubHeader from '@/components/class-hub/ClassHubHeader.vue'
import TodayList from '@/components/class-hub/TodayList.vue'
import FocusStudentsRow from '@/components/class-hub/FocusStudentsRow.vue'
import StudentsGrid from '@/components/class-hub/StudentsGrid.vue'
import MyTeachingPanel from '@/components/class-hub/MyTeachingPanel.vue'
import ClassPulse from '@/components/class-hub/ClassPulse.vue'
import FollowUpsList from '@/components/class-hub/FollowUpsList.vue'

const route = useRoute()
const overlay = useOverlayStack()
const service = createClassHubService()

const bundle = ref<ClassHubBundle | null>(null)
const actionMessage = ref('')
const loading = ref(false)

const studentGroup = computed(() => String(route.params.studentGroup || '').trim())
const queryDate = computed(() => (route.query.date ? String(route.query.date) : null))
const queryBlock = computed(() => {
  if (!route.query.block) return null
  const parsed = Number(route.query.block)
  return Number.isFinite(parsed) ? parsed : null
})

const demoBundle = computed(() => buildDemoBundle(studentGroup.value || 'DEMO-GROUP'))

const currentBundle = computed(() => bundle.value || demoBundle.value)

async function loadBundle() {
  actionMessage.value = ''

  if (!studentGroup.value) {
    actionMessage.value = 'Student group is required to load the Class Hub.'
    bundle.value = demoBundle.value
    return
  }

  loading.value = true
  try {
    const payload = await service.getBundle({
      student_group: studentGroup.value,
      date: queryDate.value,
      block_number: queryBlock.value,
    })

    if (payload && typeof payload === 'object' && payload.header) {
      bundle.value = payload
    } else {
      bundle.value = demoBundle.value
      actionMessage.value = 'Using demo data while the bundle loads.'
    }
  } catch (err) {
    bundle.value = demoBundle.value
    actionMessage.value = 'Unable to load live data. Showing demo data.'
    console.error('[ClassHub] bundle load failed', err)
  } finally {
    loading.value = false
  }
}

watch(
  () => [studentGroup.value, queryDate.value, queryBlock.value],
  () => {
    loadBundle()
  }
)

onMounted(async () => {
  await loadBundle()
})

function openStudent(student: ClassHubBundle['students'][number]) {
  overlay.open('class-hub-student-context', {
    student: student.student,
    student_name: student.student_name,
    student_group: currentBundle.value.header.student_group,
    lesson_instance: currentBundle.value.session.lesson_instance ?? null,
  })
}

function openFocusStudent(student: ClassHubBundle['focus_students'][number]) {
  openStudent({
    student: student.student,
    student_name: student.student_name,
    evidence_count_today: 0,
    signal: null,
    has_note_today: false,
  })
}

function openFollowUp(item: ClassHubBundle['follow_up_items'][number]) {
  const payload = item.payload || {}
  if (!payload.student) {
    actionMessage.value = 'Unable to open follow-up right now.'
    return
  }
  openStudent({
    student: payload.student,
    student_name: payload.student_name || 'Student',
    evidence_count_today: 0,
    signal: null,
    has_note_today: false,
  })
}

function openTodayItem(item: ClassHubBundle['today_items'][number]) {
  const payload = item.payload || {}
  if (item.overlay === 'QuickCFU') {
    openQuickCFU()
    return
  }
  if (item.overlay === 'QuickEvidence') {
    openQuickEvidence()
    return
  }
  if (item.overlay === 'StudentContext') {
    if (!payload.student) {
      actionMessage.value = 'Select a student before opening context.'
      return
    }
    openStudent({
      student: payload.student,
      student_name: payload.student_name || 'Student',
      evidence_count_today: 0,
      signal: null,
      has_note_today: false,
    })
    return
  }
  if (item.overlay === 'TaskReview') {
    openTask({ id: item.id, title: item.label, status_label: '', overlay: 'TaskReview', payload })
  }
}

function openNote(note: ClassHubBundle['notes_preview'][number]) {
  const match = currentBundle.value.students.find((student) => student.student_name === note.student_name)
  if (!match) {
    actionMessage.value = 'Student not found for that note.'
    return
  }
  openStudent(match)
}

function openTask(task: ClassHubBundle['task_items'][number]) {
  overlay.open('class-hub-task-review', {
    title: task.title,
  })
}

function openQuickEvidence() {
  overlay.open('class-hub-quick-evidence', {
    student_group: currentBundle.value.header.student_group,
    lesson_instance: currentBundle.value.session.lesson_instance ?? null,
    students: currentBundle.value.students.map((student) => ({
      student: student.student,
      student_name: student.student_name,
    })),
  })
}

function openQuickCFU() {
  overlay.open('class-hub-quick-cfu', {
    student_group: currentBundle.value.header.student_group,
    lesson_instance: currentBundle.value.session.lesson_instance ?? null,
    students: currentBundle.value.students.map((student) => ({
      student: student.student,
      student_name: student.student_name,
    })),
  })
}

async function handleStartSession() {
  actionMessage.value = ''
  if (!studentGroup.value) {
    actionMessage.value = 'Select a student group before starting.'
    return
  }
  try {
    const res = await service.startSession({
      student_group: studentGroup.value,
      date: queryDate.value,
      block_number: queryBlock.value,
    })
    bundle.value = {
      ...currentBundle.value,
      session: {
        ...currentBundle.value.session,
        lesson_instance: res.lesson_instance,
        status: 'active',
      },
    }
  } catch (err) {
    actionMessage.value = 'Unable to start session right now.'
    console.error('[ClassHub] startSession failed', err)
  }
}

async function handleEndSession() {
  actionMessage.value = ''
  const lessonInstance = currentBundle.value.session.lesson_instance
  if (!lessonInstance) {
    actionMessage.value = 'Start a session before ending it.'
    return
  }

  try {
    await service.endSession(lessonInstance)
    bundle.value = {
      ...currentBundle.value,
      session: {
        ...currentBundle.value.session,
        status: 'ended',
      },
    }
  } catch (err) {
    actionMessage.value = 'Unable to end session right now.'
    console.error('[ClassHub] endSession failed', err)
  }
}

function buildDemoBundle(studentGroupValue: string): ClassHubBundle {
  const students = Array.from({ length: 20 }).map((_, idx) => ({
    student: `STU-MOCK-${String(idx + 1).padStart(3, '0')}`,
    student_name: `Student ${idx + 1}`,
    evidence_count_today: idx % 4,
    signal: idx % 4 === 0 ? 'Got It' : idx % 3 === 0 ? 'Almost' : null,
    has_note_today: idx % 5 === 0,
  })) as ClassHubBundle['students']

  return {
    header: {
      student_group: studentGroupValue,
      title: `Class Hub - ${studentGroupValue}`,
      academic_year: '2024-2025',
      course: 'Science',
    },
    now: {
      date_label: 'Today',
      rotation_day_label: 'Rotation Day 3',
      block_label: 'Block B',
      time_range: '08:45-09:30',
      location: 'Room 204',
    },
    session: {
      lesson_instance: null,
      status: 'none',
      live_success_criteria: 'Draft a hypothesis using evidence.',
    },
    today_items: [
      {
        id: 'today-1',
        label: 'Quick CFU: Thumbs check',
        overlay: 'QuickCFU',
        payload: {},
      },
      {
        id: 'today-2',
        label: 'Capture evidence for 3 students',
        overlay: 'QuickEvidence',
        payload: {},
      },
      {
        id: 'today-3',
        label: 'Follow up with Student 1',
        overlay: 'StudentContext',
        payload: { student: students[0].student, student_name: students[0].student_name },
      },
    ],
    focus_students: students.slice(0, 3).map((student) => ({
      student: student.student,
      student_name: student.student_name,
    })),
    students,
    notes_preview: [
      {
        id: 'note-1',
        student_name: students[1].student_name,
        preview: 'Needs support with evidence selection.',
        created_at_label: 'Today',
      },
      {
        id: 'note-2',
        student_name: students[2].student_name,
        preview: 'Great use of vocabulary during discussion.',
        created_at_label: 'Today',
      },
      {
        id: 'note-3',
        student_name: students[3].student_name,
        preview: 'Still organizing ideas in the notebook.',
        created_at_label: 'Yesterday',
      },
    ],
    task_items: [
      {
        id: 'task-1',
        title: 'Exit ticket review',
        status_label: '3 submissions pending',
        pending_count: 3,
        overlay: 'TaskReview',
        payload: { title: 'Exit ticket review' },
      },
      {
        id: 'task-2',
        title: 'Lab observation notes',
        status_label: 'Needs quick scan',
        pending_count: 1,
        overlay: 'TaskReview',
        payload: { title: 'Lab observation notes' },
      },
    ],
    pulse_items: [
      {
        id: 'pulse-1',
        label: '3 students marked Not Yet',
        route: { name: 'staff-student-overview' },
      },
      {
        id: 'pulse-2',
        label: '5 students missing evidence today',
        route: { name: 'staff-student-overview' },
      },
    ],
    follow_up_items: [
      {
        id: 'follow-1',
        label: 'Check in with Student 2',
        overlay: 'StudentContext',
        payload: { student: students[1].student, student_name: students[1].student_name },
      },
    ],
  }
}
</script>
