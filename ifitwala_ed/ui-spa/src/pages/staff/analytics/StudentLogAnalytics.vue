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

const recentLogsResource = createResource({
	url: 'ifitwala_ed.api.student_log_dashboard.get_recent_logs',
	method: 'POST',
	params: () => ({
		filters: filters.value,
		start: recentStart.value,
		page_length: recentPageLength,
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
		// You can later swap this to frappeRequest if you prefer
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
const incidentsOverTime = computed(() => (dashboard.value.incidentsOverTime as any[]) || [])
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
   Local reusable components (same as before, kept here)
   ────────────────────────────────────────────────────────────── */

const AnalyticsCard = defineComponent({
  name: 'AnalyticsCard',
  props: {
    title: { type: String, required: true },
  },
  setup(props, { slots }) {
    return () =>
      h(
        'div',
        { class: 'rounded-xl border border-slate-200 bg-white/90 p-3 shadow-sm' },
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

			<div
				class="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1 text-xs shadow-sm"
			>
				<span class="h-2 w-2 rounded-full bg-amber-500"></span>
				<span class="font-medium">{{ openFollowUps }}</span>
				<span class="text-slate-500">open follow-ups</span>
			</div>
		</header>

		<!-- Filter bar -->
		<section
			class="mt-4 flex flex-wrap items-end gap-3 rounded-xl border border-slate-200 bg-white/80 px-3 py-3 shadow-sm"
		>
			<!-- School -->
			<div class="flex flex-col gap-1 w-40">
				<label class="text-[0.65rem] font-medium uppercase tracking-wide text-slate-500">
					School
				</label>
				<input
					v-model="filters.school"
					type="text"
					class="h-8 rounded-md border border-slate-200 px-2 text-xs"
					placeholder="Optional"
				/>
			</div>

			<!-- Academic Year -->
			<div class="flex flex-col gap-1 w-40">
				<label class="text-[0.65rem] font-medium uppercase tracking-wide text-slate-500">
					Academic Year
				</label>
				<input
					v-model="filters.academic_year"
					type="text"
					class="h-8 rounded-md border border-slate-200 px-2 text-xs"
					placeholder="Optional"
				/>
			</div>

			<!-- Program -->
			<div class="flex flex-col gap-1 w-48">
				<label class="text-[0.65rem] font-medium uppercase tracking-wide text-slate-500">
					Program
				</label>
				<input
					v-model="filters.program"
					type="text"
					class="h-8 rounded-md border border-slate-200 px-2 text-xs"
					placeholder="Optional"
				/>
			</div>

			<!-- Author -->
			<div class="flex flex-col gap-1 w-40">
				<label class="text-[0.65rem] font-medium uppercase tracking-wide text-slate-500">
					Author
				</label>
				<input
					v-model="filters.author"
					type="text"
					class="h-8 rounded-md border border-slate-200 px-2 text-xs"
					placeholder="Employee"
				/>
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

			<!-- Student lookup -->
			<div class="ml-auto flex flex-col gap-1 w-64 relative">
				<label class="text-[0.65rem] font-medium uppercase tracking-wide text-slate-500">
					Student
				</label>
				<div class="relative">
					<input
						v-model="studentSearch"
						type="text"
						class="h-8 w-full rounded-md border border-slate-200 px-2 pr-6 text-xs"
						placeholder="Type to search"
						@input="debounce(fetchStudents, 300)"
						@focus="studentSearch && fetchStudents()"
					/>
					<button
						v-if="filters.student"
						class="absolute inset-y-0 right-0 flex items-center pr-2 text-[10px] text-slate-400 hover:text-slate-600"
						@click="clearStudent"
						type="button"
					>
						✕
					</button>
				</div>

				<!-- Suggestions dropdown -->
				<div
					v-if="studentDropdownOpen"
					class="absolute top-full z-20 mt-1 max-h-56 w-full overflow-auto rounded-md border border-slate-200 bg-white text-xs shadow-lg"
				>
					<div
						v-if="studentLoading"
						class="px-2 py-2 text-slate-400"
					>
						Searching…
					</div>
					<template v-else>
						<button
							v-for="s in studentSuggestions"
							:key="s.id"
							class="flex w-full items-center justify-between px-2 py-1.5 text-left hover:bg-slate-50"
							type="button"
							@click="selectStudent(s)"
						>
							<span class="truncate">{{ s.name }}</span>
							<span class="ml-2 shrink-0 text-[0.65rem] text-slate-400">
								{{ s.id }}
							</span>
						</button>
						<div
							v-if="!studentSuggestions.length"
							class="px-2 py-2 text-slate-400"
						>
							No matches.
						</div>
					</template>
				</div>
			</div>
		</section>

		<!-- Main layout: charts on the left, tables on the right -->
		<section class="mt-4 grid gap-4 xl:grid-cols-[2fr,1.6fr]">
			<!-- Left column: trends & breakdowns (now with charts) -->
			<div class="flex flex-col gap-4">
				<!-- Incidents over time: line chart -->
				<AnalyticsCard title="Incidents Over Time">
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

				<!-- Log type + next step types (bar charts) -->
				<div class="grid gap-4 md:grid-cols-2">
					<AnalyticsCard title="Log Types">
						<template #body>
							<AnalyticsChart
								v-if="logTypeCount.length"
								:option="logTypeOption"
							/>
							<div
								v-else
								class="py-2 text-xs text-slate-400"
							>
								No logs found.
							</div>
						</template>
					</AnalyticsCard>

					<AnalyticsCard title="Next Step Types">
						<template #body>
							<AnalyticsChart
								v-if="nextStepTypes.length"
								:option="nextStepTypesOption"
							/>
							<div
								v-else
								class="py-2 text-xs text-slate-400"
							>
								No next steps recorded.
							</div>
						</template>
					</AnalyticsCard>
				</div>

				<!-- Cohort & program -->
				<div class="grid gap-4 md:grid-cols-2">
					<AnalyticsCard title="Logs by Cohort">
						<template #body>
							<AnalyticsChart
								v-if="logsByCohort.length"
								:option="logsByCohortOption"
							/>
							<div
								v-else
								class="py-2 text-xs text-slate-400"
							>
								No cohorts found.
							</div>
						</template>
					</AnalyticsCard>

					<AnalyticsCard title="Logs by Program">
						<template #body>
							<AnalyticsChart
								v-if="logsByProgram.length"
								:option="logsByProgramOption"
							/>
							<div
								v-else
								class="py-2 text-xs text-slate-400"
							>
								No programs found.
							</div>
						</template>
					</AnalyticsCard>
				</div>

				<!-- Logs by author -->
				<AnalyticsCard title="Logs by Author">
					<template #body>
						<AnalyticsChart
							v-if="logsByAuthor.length"
							:option="logsByAuthorOption"
						/>
						<div
							v-else
							class="py-2 text-xs text-slate-400"
						>
							No authors found.
						</div>
					</template>
				</AnalyticsCard>
			</div>

			<!-- Right column: recent logs + per-student detail -->
			<div class="flex flex-col gap-4">
				<AnalyticsCard title="Recent Student Logs">
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
										<th class="px-2 py-1 text-left">Type</th>
										<th class="px-2 py-1 text-left">Log</th>
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
										<td class="px-2 py-1 align-top">
											{{ truncate(row.content || '') }}
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
								@click="loadRecent(false)"
							>
								Load more
							</button>
						</div>
					</template>
				</AnalyticsCard>

				<AnalyticsCard title="Selected Student Logs">
					<template #subtitle>
						<span v-if="filters.student" class="text-xs text-slate-500">
							{{ studentSearch || filters.student }}
						</span>
						<span v-else class="text-xs text-slate-400">
							Choose a student above to see their logs.
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
										<th class="px-2 py-1 text-left">Type</th>
										<th class="px-2 py-1 text-left">Log</th>
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
										<td class="px-2 py-1 align-top">
											{{ truncate(row.content || '', 200) }}
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
			</div>
		</section>
	</div>
</template>
