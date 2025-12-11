<!-- ifitwala_ed/ui-spa/src/pages/staff/analytics/StudentLogAnalytics.vue -->
<script setup lang="ts">
import {
  ref,
  computed,
  watch,
  onMounted,
  defineComponent,
  h,
} from 'vue'
import { createResource } from 'frappe-ui'
import AnalyticsChart from '@/components/analytics/AnalyticsChart.vue'
import StatsTile from '@/components/analytics/StatsTile.vue'
import FiltersBar from '@/components/analytics/FiltersBar.vue'

/* ──────────────────────────────────────────────────────────────
   Shared filters state
   ────────────────────────────────────────────────────────────── */

const filters = ref<{
  school: string | null
  academic_year: string | null
  program: string | null
  author: string | null
  from_date: string | null
  to_date: string | null
  student: string | null
}>({
  school: null,
  academic_year: null,
  program: null,
  author: null,
  from_date: null,
  to_date: null,
  student: null,
})

/* ──────────────────────────────────────────────────────────────
   Zoom / expanded card state
   ────────────────────────────────────────────────────────────── */

const expandedCard = ref<string | null>(null)

function toggleCard(id: string | null) {
  if (id === null) {
    // Clicked on the overlay → always close
    expandedCard.value = null
    return
  }

  // Clicked on a card body/header:
  // - if another card is open, switch to this one
  // - if this one is already open, do nothing
  if (expandedCard.value === id) {
    return
  }

  expandedCard.value = id
}

/* ──────────────────────────────────────────────────────────────
   Filter metadata (schools, AYs, programs)
   ────────────────────────────────────────────────────────────── */

const filterMetaResource = createResource({
  url: 'ifitwala_ed.api.student_log_dashboard.get_filter_meta',
  method: 'GET',
  auto: true,
})

const schools = computed(() => (filterMetaResource.data as any)?.schools || [])
const academicYears = computed(
  () => (filterMetaResource.data as any)?.academic_years || []
)
const allPrograms = computed(
  () => (filterMetaResource.data as any)?.programs || []
)

const filterMeta = computed(() => (filterMetaResource.data as any) || {})

const programsForSchool = computed(() => {
  // For now, no schema assumption – just show all programs.
  // Once we align Program schema, we can filter by school if present.
  return allPrograms.value
})

const authors = computed(
  () => (filterMetaResource.data as any)?.authors || []
)

// Set default school once data arrives
watch(
  filterMeta,
  (data) => {
    if (!data) return
    if (data.default_school && !filters.value.school) {
      filters.value.school = data.default_school
    }
  },
  { immediate: true }
)

/* ──────────────────────────────────────────────────────────────
   Recent logs paging
   ────────────────────────────────────────────────────────────── */

const recentStart = ref(0)
const recentPageLength = 25
const recentRows = ref<any[]>([])

/* ──────────────────────────────────────────────────────────────
   Debounce helper
   ────────────────────────────────────────────────────────────── */

let debounceTimer: number | undefined
function debounce(fn: () => void, delay = 400) {
  window.clearTimeout(debounceTimer)
  debounceTimer = window.setTimeout(fn, delay)
}

/* ──────────────────────────────────────────────────────────────
   Dashboard summary data
   ────────────────────────────────────────────────────────────── */

const dashboardResource = createResource({
  url: 'ifitwala_ed.api.student_log_dashboard.get_dashboard_data',
  method: 'POST',
  params: () => ({
    filters: filters.value,
  }),
  auto: false,
})

const dashboard = computed(() => (dashboardResource.data as any) || {})

/* ──────────────────────────────────────────────────────────────
   Recent logs resource
   ────────────────────────────────────────────────────────────── */

const dashboardResource = createResource({
  url: 'ifitwala_ed.api.student_demographics_dashboard.get_dashboard',
  method: 'POST',
  params: () => ({
    filters: filters.value
  }),
  auto: false,
})

async function loadDashboard() {
  await dashboardResource.fetch()
}

async function loadRecent(reset = false) {
  if (reset) {
    recentStart.value = 0
    recentRows.value = []
  }
  const res = await recentLogsResource.fetch()
  const rows = (res as any) || []
  if (rows.length) {
    recentRows.value = reset ? rows : [...recentRows.value, ...rows]
    recentStart.value += rows.length
  }
}

/* ──────────────────────────────────────────────────────────────
   Watch filters → refresh data (debounced)
   ────────────────────────────────────────────────────────────── */

watch(
  filters,
  () => {
    debounce(() => {
      loadDashboard()
      loadRecent(true)
    })
  },
  { deep: true }
)

/* ──────────────────────────────────────────────────────────────
   Student lookup (typeahead) state
   ────────────────────────────────────────────────────────────── */

const studentSearch = ref('')
const studentSuggestions = ref<{ id: string; name: string }[]>([])
const studentDropdownOpen = ref(false)
const studentLoading = ref(false)

async function fetchStudents() {
  const txt = studentSearch.value.trim()
  if (!txt) {
    studentSuggestions.value = []
    studentDropdownOpen.value = false
    return
  }

  studentLoading.value = true
  try {
    const res = await (window as any).frappe.call({
      method: 'ifitwala_ed.api.student_log_dashboard.get_distinct_students',
      args: {
        filters: filters.value,
        search_text: txt,
      },
    })
    const list = (res.message as any[]) || []
    studentSuggestions.value = list.map((s) => ({
      id: s.student,
      name: s.student_full_name,
    }))
    studentDropdownOpen.value = !!studentSuggestions.value.length
  } finally {
    studentLoading.value = false
  }
}

function selectStudent(s: { id: string; name: string }) {
  filters.value.student = s.id
  studentSearch.value = s.name
  studentDropdownOpen.value = false
  loadDashboard()
}

function clearStudent() {
  filters.value.student = null
  studentSearch.value = ''
  studentSuggestions.value = []
  studentDropdownOpen.value = false
}

/* ──────────────────────────────────────────────────────────────
   Derived helpers
   ────────────────────────────────────────────────────────────── */

const openFollowUps = computed<number>(() => dashboard.value.openFollowUps || 0)

const logTypeCount = computed(() => (dashboard.value.logTypeCount as any[]) || [])
const logsByCohort = computed(() => (dashboard.value.logsByCohort as any[]) || [])
const logsByProgram = computed(() => (dashboard.value.logsByProgram as any[]) || [])
const logsByAuthor = computed(() => (dashboard.value.logsByAuthor as any[]) || [])
const nextStepTypes = computed(() => (dashboard.value.nextStepTypes as any[]) || [])
const incidentsOverTime = computed(
  () => (dashboard.value.incidentsOverTime as any[]) || []
)
const studentLogs = computed(() => (dashboard.value.studentLogs as any[]) || [])

/* ──────────────────────────────────────────────────────────────
   ECharts options (using your data from the API)
   ────────────────────────────────────────────────────────────── */

const incidentsOption = computed(() => {
  const data = incidentsOverTime.value
  if (!data.length) return {}

  return {
    tooltip: { trigger: 'axis' },
    grid: { left: '4%', right: '4%', bottom: '8%', containLabel: true },
    xAxis: {
      type: 'category',
      data: data.map((d: any) => d.label),
      axisLabel: { fontSize: 10 },
    },
    yAxis: {
      type: 'value',
    },
    series: [
      {
        type: 'line',
        smooth: true,
        data: data.map((d: any) => d.value),
      },
    ],
  }
})

const logTypeOption = computed(() => {
  const data = logTypeCount.value
  if (!data.length) return {}
  return {
    tooltip: { trigger: 'item' },
    grid: { left: '4%', right: '4%', bottom: '8%', containLabel: true },
    xAxis: {
      type: 'category',
      data: data.map((d: any) => d.label),
      axisLabel: { fontSize: 10, interval: 0, rotate: 30 },
    },
    yAxis: { type: 'value' },
    series: [
      {
        type: 'bar',
        data: data.map((d: any) => d.value),
      },
    ],
  }
})

const nextStepTypesOption = computed(() => {
  const data = nextStepTypes.value
  if (!data.length) return {}
  return {
    tooltip: { trigger: 'item' },
    grid: { left: '4%', right: '4%', bottom: '8%', containLabel: true },
    xAxis: {
      type: 'category',
      data: data.map((d: any) => d.label),
      axisLabel: { fontSize: 10, interval: 0, rotate: 30 },
    },
    yAxis: { type: 'value' },
    series: [
      {
        type: 'bar',
        data: data.map((d: any) => d.value),
      },
    ],
  }
})

const logsByCohortOption = computed(() => {
  const data = logsByCohort.value
  if (!data.length) return {}
  return {
    tooltip: { trigger: 'item' },
    grid: { left: '4%', right: '4%', bottom: '8%', containLabel: true },
    xAxis: {
      type: 'category',
      data: data.map((d: any) => d.label),
      axisLabel: { fontSize: 10, interval: 0, rotate: 30 },
    },
    yAxis: { type: 'value' },
    series: [
      {
        type: 'bar',
        data: data.map((d: any) => d.value),
      },
    ],
  }
})

const logsByProgramOption = computed(() => {
  const data = logsByProgram.value
  if (!data.length) return {}
  return {
    tooltip: { trigger: 'item' },
    grid: { left: '4%', right: '4%', bottom: '8%', containLabel: true },
    xAxis: {
      type: 'category',
      data: data.map((d: any) => d.label),
      axisLabel: { fontSize: 10, interval: 0, rotate: 30 },
    },
    yAxis: { type: 'value' },
    series: [
      {
        type: 'bar',
        data: data.map((d: any) => d.value),
      },
    ],
  }
})

const logsByAuthorOption = computed(() => {
  const data = logsByAuthor.value
  if (!data.length) return {}
  return {
    tooltip: { trigger: 'item' },
    grid: { left: '4%', right: '4%', bottom: '8%', containLabel: true },
    xAxis: {
      type: 'category',
      data: data.map((d: any) => d.label),
      axisLabel: { fontSize: 10, interval: 0, rotate: 30 },
    },
    yAxis: { type: 'value' },
    series: [
      {
        type: 'bar',
        data: data.map((d: any) => d.value),
      },
    ],
  }
})

/* ──────────────────────────────────────────────────────────────
   Utilities
   ────────────────────────────────────────────────────────────── */

function formatDate(d: string | null | undefined) {
  if (!d) return ''
  return d
}

function stripHtml(html: string): string {
  if (!html) return ''
  return html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()
}

function truncate(text: string, max = 140) {
  if (!text) return ''
  return text.length > max ? text.slice(0, max) + '…' : text
}

/* ──────────────────────────────────────────────────────────────
   Lifecycle
   ────────────────────────────────────────────────────────────── */

onMounted(() => {
  loadDashboard()
  loadRecent(true)
})

/* ──────────────────────────────────────────────────────────────
   Local reusable components
   ────────────────────────────────────────────────────────────── */

const AnalyticsCard = defineComponent({
  name: 'AnalyticsCard',
  props: {
    title: { type: String, required: true },
    expanded: { type: Boolean, default: false },
  },
  emits: ['toggle'],
  setup(props, { slots, emit }) {
    return () =>
      h(
        'div',
        {
          class: [
            'rounded-xl border border-slate-200 bg-white/90 p-3 shadow-sm cursor-pointer transition-transform duration-200',
            props.expanded
              ? 'fixed inset-4 z-40 max-w-5xl mx-auto overflow-auto shadow-2xl'
              : '',
          ],
          onClick: () => emit('toggle'),
        },
        [
          h(
            'div',
            { class: 'mb-2 flex items-center justify-between gap-2' },
            [
              h('div', null, [
                h(
                  'div',
                  {
                    class:
                      'text-[11px] font-semibold uppercase tracking-wide text-slate-600',
                  },
                  props.title
                ),
                slots.subtitle
                  ? h('div', { class: 'mt-0.5' }, slots.subtitle())
                  : null,
              ]),
              slots.badge ? h('div', null, slots.badge()) : null,
            ]
          ),
          h(
            'div',
            { class: 'text-xs text-slate-700' },
            slots.body ? slots.body() : null
          ),
        ]
      )
  },
})

const SimpleList = defineComponent({
  name: 'SimpleList',
  props: {
    items: { type: Array as () => any[], required: true },
    labelKey: { type: String, default: 'label' },
    valueKey: { type: String, default: 'value' },
    emptyLabel: { type: String, default: 'No data.' },
  },
  setup(props) {
    return () => {
      const items = props.items || []
      if (!items.length) {
        return h(
          'div',
          { class: 'py-2 text-xs text-slate-400' },
          props.emptyLabel
        )
      }

      return h(
        'ul',
        { class: 'divide-y divide-slate-100' },
        items.map((item: any) =>
          h(
            'li',
            {
              class: 'flex items-center justify-between py-1',
              key: item[props.labelKey] || String(Math.random()),
            },
            [
              h(
                'span',
                { class: 'mr-2 truncate' },
                item[props.labelKey] as string
              ),
              h(
                'span',
                {
                  class: 'ml-2 shrink-0 font-medium text-slate-800',
                },
                String(item[props.valueKey])
              ),
            ]
          )
        )
      )
    }
  },
})

const SimpleListPercent = defineComponent({
  name: 'SimpleListPercent',
  props: {
    items: { type: Array as () => any[], required: true },
    emptyLabel: { type: String, default: 'No data.' },
  },
  setup(props) {
    return () => {
      const items = props.items || []
      if (!items.length) {
        return h(
          'div',
          { class: 'py-2 text-xs text-slate-400' },
          props.emptyLabel
        )
      }

      const values = items.map((i: any) => Number(i.value) || 0)
      const total = values.reduce((a, b) => a + b, 0) || 1

      return h(
        'ul',
        { class: 'divide-y divide-slate-100' },
        items.map((item: any, idx: number) => {
          const v = values[idx]
          const pct = Math.round((v / total) * 1000) / 10

          return h(
            'li',
            {
              class: 'flex items-center justify-between py-1',
              key: item.label || String(idx),
            },
            [
              h('span', { class: 'mr-2 truncate' }, item.label as string),
              h(
                'span',
                { class: 'ml-2 shrink-0 text-[11px] text-slate-500' },
                [
                  h(
                    'span',
                    { class: 'font-semibold text-slate-800' },
                    String(v)
                  ),
                  h('span', { class: 'ml-1' }, `(${pct}%)`),
                ]
              ),
            ]
          )
        })
      )
    }
  },
})
</script>


<template>
  <div class="min-h-full px-4 py-4 md:px-6 lg:px-8">
    <!-- Overlay when a card is expanded (click outside to close) -->
    <div
      v-if="expandedCard"
      class="fixed inset-0 z-30 bg-slate-900/40"
      @click="toggleCard(null)"
    />

    <!-- Header -->
    <header class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-base font-semibold tracking-tight text-slate-900">
          Student Log Analytics
        </h1>
        <p class="mt-0.5 text-xs text-slate-500">
          Trends and follow-ups for the students you have access to.
        </p>
      </div>

      <StatsTile
        :value="openFollowUps"
        label="open follow-ups"
        tone="warning"
      />
    </header>

    <!-- Filter bar -->
    <FiltersBar>
      <!-- School -->
      <div class="flex flex-col gap-1 w-40">
        <label class="text-[0.65rem] font-medium uppercase tracking-wide text-slate-500">
          School
        </label>
        <select
          v-model="filters.school"
          class="h-8 rounded-md border border-slate-200 px-2 text-xs"
        >
          <option value="">
            All
          </option>
          <option
            v-for="s in schools"
            :key="s.name"
            :value="s.name"
          >
            {{ s.label || s.name }}
          </option>
        </select>
      </div>

      <!-- Academic Year -->
      <div class="flex flex-col gap-1 w-40">
        <label class="text-[0.65rem] font-medium uppercase tracking-wide text-slate-500">
          Academic Year
        </label>
        <select
          v-model="filters.academic_year"
          class="h-8 rounded-md border border-slate-200 px-2 text-xs"
        >
          <option value="">
            All
          </option>
					<option
						v-for="ay in academicYears"
						:key="ay.name"
						:value="ay.name"
					>
						{{ ay.label || ay.name }}
					</option>
        </select>
      </div>

      <!-- Program -->
      <div class="flex flex-col gap-1 w-48">
        <label class="text-[0.65rem] font-medium uppercase tracking-wide text-slate-500">
          Program
        </label>
        <select
          v-model="filters.program"
          class="h-8 rounded-md border border-slate-200 px-2 text-xs"
        >
          <option value="">
            All
          </option>
          <option
            v-for="p in programsForSchool"
            :key="p.name"
            :value="p.name"
          >
            {{ p.label || p.name }}
          </option>
        </select>
      </div>

      <!-- Author (Academic Staff list) -->
      <div class="flex flex-col gap-1 w-48">
        <label class="text-[0.65rem] font-medium uppercase tracking-wide text-slate-500">
          Author
        </label>
        <select
          v-model="filters.author"
          class="h-8 rounded-md border border-slate-200 px-2 text-xs"
        >
          <option value="">
            All
          </option>
          <option
            v-for="a in authors"
            :key="a.user_id"
            :value="a.label"
          >
            {{ a.label }}
          </option>
        </select>
      </div>

      <!-- From / To -->
      <div class="flex flex-col gap-1 w-32">
        <label class="text-[0.65rem] font-medium uppercase tracking-wide text-slate-500">
          From
        </label>
        <input
          v-model="filters.from_date"
          type="date"
          class="h-8 rounded-md border border-slate-200 px-2 text-xs"
        />
      </div>

      <div class="flex flex-col gap-1 w-32">
        <label class="text-[0.65rem] font-medium uppercase tracking-wide text-slate-500">
          To
        </label>
        <input
          v-model="filters.to_date"
          type="date"
          class="h-8 rounded-md border border-slate-200 px-2 text-xs"
        />
      </div>
      <!-- (Student filter removed: last card handles per-student detail) -->
    </FiltersBar>

    <!-- Main layout: always max 2 cards per row -->
    <section class="mt-4 grid gap-4 md:grid-cols-2">
      <!-- Logs over time: full-width (no zoom) -->
      <AnalyticsCard
        class="md:col-span-2"
        title="Logs Over Time"
      >
        <template #body>
          <AnalyticsChart
            v-if="incidentsOverTime.length"
            :option="incidentsOption"
          />
          <div
            v-else
            class="py-2 text-xs text-slate-400"
          >
            No logs for this period.
          </div>
        </template>
      </AnalyticsCard>

      <!-- Log Types -->
      <AnalyticsCard
        title="Log Types"
        :expanded="expandedCard === 'log-types'"
        @toggle="toggleCard('log-types')"
      >
        <template #body>
          <AnalyticsChart
            v-if="logTypeCount.length"
            :option="logTypeOption"
            :class="{ 'analytics-chart--expanded': expandedCard === 'log-types' }"
          />
          <div
            v-else
            class="py-2 text-xs text-slate-400"
          >
            No logs found.
          </div>
        </template>
      </AnalyticsCard>

      <!-- Next Step Types -->
      <AnalyticsCard
        title="Next Step Types"
        :expanded="expandedCard === 'next-steps'"
        @toggle="toggleCard('next-steps')"
      >
        <template #body>
          <AnalyticsChart
            v-if="nextStepTypes.length"
            :option="nextStepTypesOption"
            :class="{ 'analytics-chart--expanded': expandedCard === 'next-steps' }"
          />
          <div
            v-else
            class="py-2 text-xs text-slate-400"
          >
            No next steps recorded.
          </div>
        </template>
      </AnalyticsCard>

      <!-- Logs by Cohort -->
      <AnalyticsCard
        title="Logs by Cohort"
        :expanded="expandedCard === 'cohort'"
        @toggle="toggleCard('cohort')"
      >
        <template #body>
          <AnalyticsChart
            v-if="logsByCohort.length"
            :option="logsByCohortOption"
            :class="{ 'analytics-chart--expanded': expandedCard === 'cohort' }"
          />
          <div
            v-else
            class="py-2 text-xs text-slate-400"
          >
            No cohorts found.
          </div>
        </template>
      </AnalyticsCard>

      <!-- Logs by Program -->
      <AnalyticsCard
        title="Logs by Program"
        :expanded="expandedCard === 'program'"
        @toggle="toggleCard('program')"
      >
        <template #body>
          <AnalyticsChart
            v-if="logsByProgram.length"
            :option="logsByProgramOption"
            :class="{ 'analytics-chart--expanded': expandedCard === 'program' }"
          />
          <div
            v-else
            class="py-2 text-xs text-slate-400"
          >
            No programs found.
          </div>
        </template>
      </AnalyticsCard>

      <!-- Logs by Author -->
      <AnalyticsCard
        title="Logs by Author"
        :expanded="expandedCard === 'author'"
        @toggle="toggleCard('author')"
      >
        <template #body>
          <AnalyticsChart
            v-if="logsByAuthor.length"
            :option="logsByAuthorOption"
            :class="{ 'analytics-chart--expanded': expandedCard === 'author' }"
          />
          <div
            v-else
            class="py-2 text-xs text-slate-400"
          >
            No authors found.
          </div>
        </template>
      </AnalyticsCard>

      <!-- Recent Student Logs -->
      <AnalyticsCard
        title="Recent Student Logs"
        :expanded="expandedCard === 'recent'"
        @toggle="toggleCard('recent')"
      >
        <template #body>
          <div class="max-h-[320px] overflow-auto">
            <table class="min-w-full border-collapse text-[11px]">
              <thead>
                <tr
                  class="border-b border-slate-200 bg-slate-50 text-[10px] uppercase tracking-wide text-slate-500"
                >
                  <th class="px-2 py-1 text-left">Date</th>
                  <th class="px-2 py-1 text-left">Student</th>
                  <th class="px-2 py-1 text-left">Program</th>
                  <th class="px-2 py-1 text-left w-[7rem]">
                    Type
                  </th>
                  <th class="px-2 py-1 text-left w-[45%]">
                    Log
                  </th>
                  <th class="px-2 py-1 text-left">Author</th>
                  <th class="px-2 py-1 text-center">FU</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="row in recentRows"
                  :key="`${row.date}-${row.student}-${row.log_type}-${row.author}-${row.program}`"
                  class="border-b border-slate-100 hover:bg-slate-50"
                >
                  <td class="px-2 py-1 align-top whitespace-nowrap">
                    {{ formatDate(row.date) }}
                  </td>
                  <td class="px-2 py-1 align-top whitespace-nowrap">
                    {{ row.student }}
                  </td>
                  <td class="px-2 py-1 align-top whitespace-nowrap">
                    {{ row.program }}
                  </td>
                  <td class="px-2 py-1 align-top whitespace-nowrap">
                    {{ row.log_type }}
                  </td>
                  <td
                    class="px-2 py-1 align-top"
                    :title="stripHtml(row.content || '')"
                  >
                    {{ truncate(stripHtml(row.content || '')) }}
                  </td>
                  <td class="px-2 py-1 align-top whitespace-nowrap">
                    {{ row.author }}
                  </td>
                  <td class="px-2 py-1 align-top text-center">
                    <span
                      v-if="row.requires_follow_up"
                      class="inline-flex h-4 w-4 items-center justify-center rounded-full bg-amber-100 text-[9px] font-bold text-amber-700"
                    >
                      ✓
                    </span>
                  </td>
                </tr>
                <tr v-if="!recentRows.length">
                  <td
                    colspan="7"
                    class="px-2 py-3 text-center text-xs text-slate-400"
                  >
                    No logs in this period.
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="mt-2 flex justify-center">
            <button
              type="button"
              class="inline-flex items-center justify-center rounded-full border border-slate-200 px-3 py-1 text-[11px] text-slate-600 hover:bg-slate-50"
              @click.stop="loadRecent(false)"
            >
              Load more
            </button>
          </div>
        </template>
      </AnalyticsCard>

      <!-- Selected Student Logs -->
      <AnalyticsCard
        title="Selected Student Logs"
        :expanded="expandedCard === 'student-detail'"
        @toggle="toggleCard('student-detail')"
      >
        <template #subtitle>
          <span v-if="filters.student" class="text-xs text-slate-500">
            {{ studentSearch || filters.student }}
          </span>
          <span v-else class="text-xs text-slate-400">
            Choose a student (from the table) to see their logs.
          </span>
        </template>

        <template #body>
          <div class="max-h-[260px] overflow-auto">
            <table class="min-w-full border-collapse text-[11px]">
              <thead>
                <tr
                  class="border-b border-slate-200 bg-slate-50 text-[10px] uppercase tracking-wide text-slate-500"
                >
                  <th class="px-2 py-1 text-left">Date</th>
                  <th class="px-2 py-1 text-left w-[7rem]">
                    Type
                  </th>
                  <th class="px-2 py-1 text-left w-[55%]">
                    Log
                  </th>
                  <th class="px-2 py-1 text-left">Author</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="row in studentLogs"
                  :key="`${row.date}-${row.log_type}-${row.author}`"
                  class="border-b border-slate-100 hover:bg-slate-50"
                >
                  <td class="px-2 py-1 align-top whitespace-nowrap">
                    {{ formatDate(row.date) }}
                  </td>
                  <td class="px-2 py-1 align-top whitespace-nowrap">
                    {{ row.log_type }}
                  </td>
                  <td
                    class="px-2 py-1 align-top"
                    :title="stripHtml(row.content || '')"
                  >
                    {{ truncate(stripHtml(row.content || ''), 200) }}
                  </td>
                  <td class="px-2 py-1 align-top whitespace-nowrap">
                    {{ row.author }}
                  </td>
                </tr>
                <tr v-if="!studentLogs.length">
                  <td
                    colspan="4"
                    class="px-2 py-3 text-center text-xs text-slate-400"
                  >
                    No logs to show yet.
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>
      </AnalyticsCard>
    </section>
  </div>
</template>
