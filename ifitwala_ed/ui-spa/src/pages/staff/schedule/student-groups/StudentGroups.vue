<template>
	<!-- Page wrapper -->
	<div class="min-h-full px-4 py-4 md:px-6 lg:px-8">
		<!-- Header -->
		<div class="flex items-center justify-between gap-3">
			<h1 class="text-xl font-semibold tracking-tight">Student Group Cards</h1>
			<div class="flex items-center gap-2">
				<Button appearance="primary" :loading="studentsResource.loading" @click="reloadStudents" :disabled="!filters.student_group">
					Reload
				</Button>
			</div>
		</div>

		<!-- Filters -->
		<div class="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
			<FormControl v-model="filters.program" type="text" placeholder="Program" @update:modelValue="onFilterChanged" />
			<FormControl v-model="filters.course" type="text" placeholder="Course" @update:modelValue="onFilterChanged" />
			<FormControl v-model="filters.cohort" type="text" placeholder="Cohort" @update:modelValue="onFilterChanged" />

			<!-- Student Group select fed by groupsResource -->
			<FormControl
				type="select"
				:options="groupOptions"
				:loading="groups.loading"
				:disabled="groups.loading || groupsEmpty"
				v-model="filters.student_group"
				placeholder="Student Group"
				@update:modelValue="onGroupPicked"
			/>
		</div>

		<!-- Title / meta -->
		<div class="mt-4">
			<div v-if="groupInfo.name" class="text-sm text-gray-600">
				<span class="font-medium">{{ groupInfo.name }}</span>
				<span v-if="groupSubtitle" class="text-gray-500"> — {{ groupSubtitle }}</span>
			</div>
		</div>

		<!-- Content -->
		<div class="mt-6">
			<div
				v-if="!filters.student_group"
				class="flex flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-slate-200 bg-slate-50/60 px-6 py-12 text-center"
			>
				<FeatherIcon name="users" class="h-12 w-12 text-slate-300" />
				<p class="text-base font-semibold text-slate-700">Select a student group to begin</p>
				<p class="max-w-sm text-sm text-slate-500">
					Filter by Program, Course, or Cohort, then choose a Student Group.
				</p>
			</div>

			<!-- Loading skeletons -->
      <div v-else-if="studentsResource.loading" class="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
        <div
          v-for="n in 12"
          :key="n"
          class="h-44 rounded-2xl bg-slate-100/80 shadow-inner animate-pulse"
        />
      </div>

			<!-- Grid -->
			<div v-else class="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
				<!-- Minimal card; SSG badge is clickable -->
				<div
					v-for="stu in studentsState.students"
					:key="stu.student"
					class="rounded-2xl bg-white p-3 shadow-sm transition hover:-translate-y-0.5"
				>
					<a :href="`/app/student/${stu.student}`" target="_blank" rel="noopener" class="block">
						<img
							:src="thumb(stu.student_image)"
							:alt="`Photo of ${stu.student_name}`"
							loading="lazy"
							class="h-32 w-full rounded-xl object-cover"
							@error="onImgError($event, stu.student_image)"
						/>
						<div class="mt-2 text-sm font-semibold leading-tight flex items-center gap-1">
							<span class="truncate">{{ stu.student_name }}</span>

							<!-- Clickable SSG badge -->
							<button
								v-if="stu.has_ssg"
								type="button"
								class="ml-1 inline-flex items-center"
								:title="'Support guidance available'"
								@click.stop="openSSG(stu)"
							>
								<Badge variant="subtle">SSG</Badge>
							</button>
						</div>
						<div v-if="stu.preferred_name" class="text-xs text-gray-500">
							{{ stu.preferred_name }}
						</div>
					</a>
				</div>
			</div>

			<!-- Load more -->
			<div v-if="showLoadMore" class="mt-6 flex justify-center">
				<Button appearance="primary" :loading="studentsResource.loading" @click="loadMore">
					Load More
				</Button>
			</div>

			<!-- Totals -->
			<div v-if="filters.student_group" class="mt-3 text-xs text-gray-500">
				Showing {{ studentsState.students.length || 0 }} of {{ studentsState.total || 0 }}
			</div>
		</div>
	</div>

	<!-- SSG Dialog -->
	<Dialog v-model="ssg.open" :options="{ title: ssg.title, size: '2xl' }">
		<template #body>
			<!-- Loading state -->
      <div v-if="ssg.resource.loading" class="space-y-3">
        <div class="h-6 rounded bg-slate-200/80 animate-pulse" />
        <div class="h-20 rounded bg-slate-200/80 animate-pulse" />
        <div class="h-20 rounded bg-slate-200/80 animate-pulse" />
      </div>

			<!-- Empty -->
		<div
			v-else-if="(ssg.entries?.length || 0) === 0"
			class="flex flex-col items-center justify-center gap-3 rounded-xl border border-slate-200 bg-slate-50/60 px-6 py-12 text-center"
		>
			<FeatherIcon name="info" class="h-10 w-10 text-slate-300" />
			<p class="text-base font-semibold text-slate-700">No published guidance</p>
			<p class="max-w-sm text-sm text-slate-500">
				There are no published, active support guidance entries for this student.
			</p>
		</div>

			<!-- Entries -->
  <div v-else class="space-y-3">
				<div
					v-for="(item, idx) in ssg.entries"
					:key="idx"
					class="rounded-xl border border-gray-200 bg-white p-4 shadow-sm"
				>
					<!-- Header row: date + status + (optional) view case -->
					<div class="flex items-center justify-between gap-3">
						<div class="text-sm text-gray-600">
              <span class="inline-flex items-center gap-2">
                <FeatherIcon name="calendar" class="h-4 w-4" />
								<strong>{{ neatDate(item.entry_datetime) }}</strong>
							</span>
							<Badge v-if="(item.status || 'Open') === 'In Progress'" class="ml-2" variant="success">In&nbsp;Progress</Badge>
						</div>

            <Button
							v-if="item.case_name"
							size="sm"
							appearance="minimal"
							@click="openCase(item.case_name)"
							:title="'Open Referral Case in Desk'"
						>
							View Case
						</Button>
					</div>

					<!-- Meta row -->
          <div class="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-gray-500">
            <span class="inline-flex items-center gap-1">
              <FeatherIcon name="user" class="h-4 w-4" />
							Assignee:
							<strong class="ml-1">{{ item.assignee || 'All instructors' }}</strong>
						</span>
            <span v-if="item.author_full_name" class="inline-flex items-center gap-1">
              <FeatherIcon name="edit" class="h-4 w-4" />
							Author:
							<strong class="ml-1">{{ item.author_full_name }}</strong>
						</span>
					</div>

					<!-- Summary (server should already sanitize HTML; we render as HTML) -->
					<div class="prose prose-sm mt-3 max-w-none" v-html="item.summary"></div>
				</div>
			</div>
		</template>

		<template #footer>
			<div class="flex w-full justify-end">
				<Button appearance="primary" @click="ssg.open = false">Close</Button>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import {
  Button,
  FormControl,
  Badge,
  Dialog,
  FeatherIcon,
	createResource,
} from 'frappe-ui'

/** ---------------- State ---------------- */
type Filters = {
	program: string | null
	course: string | null
	cohort: string | null
	student_group: string | null
}
const filters = reactive<Filters>({
	program: null,
	course: null,
	cohort: null,
	student_group: null,
})

const PAGE_LEN = 25
const start = ref(0)

/** ---------------- Resources (reuse your existing endpoints) ---------------- */
const groups = createResource({
	url: 'api/method/ifitwala_ed.schedule.page.student_group_cards.student_group_cards.fetch_student_groups',
	makeParams: () => ({
		program: filters.program || undefined,
		course: filters.course || undefined,
		cohort: filters.cohort || undefined,
	}),
	auto: false,
	transform: (r: any) => r?.message ?? [],
})

type StudentsPayload = {
	students: any[]
	start: number
	total: number
	group_info: { name?: string; program?: string; course?: string; cohort?: string }
}
const emptyStudents: StudentsPayload = {
	students: [],
	start: 0,
	total: 0,
	group_info: {},
}

const studentsState = reactive<StudentsPayload>({ ...emptyStudents })
const appendMode = ref(false)

const studentsResource = createResource<StudentsPayload>({
	url: 'api/method/ifitwala_ed.schedule.page.student_group_cards.student_group_cards.fetch_students',
	makeParams: () => ({
		student_group: filters.student_group as string,
		start: start.value,
		page_length: PAGE_LEN,
	}),
	auto: false,
	transform: (r: any) => (r?.message as StudentsPayload) ?? { ...emptyStudents },
	onSuccess(data: StudentsPayload) {
		if (appendMode.value) {
			studentsState.students.push(...(data.students || []))
		} else {
			studentsState.students = data.students || []
		}
		studentsState.start = data.start ?? 0
		studentsState.total = data.total ?? 0
		studentsState.group_info = data.group_info || {}
		appendMode.value = false
	},
})

/** ---------------- Derived ---------------- */
const groupOptions = computed(() => {
	const rows = groups.data || []
	return rows.map((r: any) => ({
		label: r.student_group_name || r.name,
		value: r.name,
	}))
})
const groupsEmpty = computed(() => (groups.data?.length ?? 0) === 0)

const groupInfo = computed(() => studentsState.group_info ?? {})
const groupSubtitle = computed(() => {
	const g = groupInfo.value
	return [g.program, g.course, g.cohort].filter(Boolean).join(' – ')
})

const showLoadMore = computed(() => {
	return studentsState.start < (studentsState.total || 0)
})

/** ---------------- Handlers ---------------- */
function onFilterChanged() {
	filters.student_group = null
	resetStudentsData()
	groups.reload()
}

function onGroupPicked() {
	if (!filters.student_group) {
		resetStudentsData()
		return
	}
	start.value = 0
	appendMode.value = false
	studentsResource.fetch().finally(() => {
		appendMode.value = false
	})
}

function loadMore() {
	if (!filters.student_group) return
	const next = studentsState.start ?? start.value + PAGE_LEN
	start.value = next
	appendMode.value = true
	studentsResource.fetch().finally(() => {
		appendMode.value = false
	})
}

function reloadStudents() {
	if (!filters.student_group) return
	start.value = 0
	studentsState.students = []
	appendMode.value = false
	studentsResource.fetch().finally(() => {
		appendMode.value = false
	})
}

function resetStudentsData() {
	start.value = 0
	studentsState.students = []
	studentsState.start = 0
	studentsState.total = 0
	studentsState.group_info = {}
}

/** ---------------- Image helpers (thumbnail fallback) ---------------- */
const DEFAULT_IMG = '/assets/ifitwala_ed/images/default_student_image.png'
function slugify(filename: string) {
	return filename
		.replace(/\.[^.]+$/, '')
		.toLowerCase()
		.replace(/[^a-z0-9]+/g, '_')
		.replace(/^_+|_+$/g, '')
}
function thumb(original_url?: string) {
	if (!original_url) return DEFAULT_IMG
	if (original_url.startsWith('/files/gallery_resized/student/')) return original_url
	if (!original_url.startsWith('/files/student/')) return DEFAULT_IMG
	const base = slugify(original_url.split('/').pop() || '')
	return `/files/gallery_resized/student/thumb_${base}.webp`
}
function onImgError(e: Event, fallback?: string) {
	const el = e.target as HTMLImageElement
	el.onerror = null
	el.src = fallback || DEFAULT_IMG
}

/** ---------------- SSG Dialog ---------------- */
type SsgEntry = {
	entry_datetime?: string
	status?: string
	assignee?: string
	author_full_name?: string
	summary?: string // assumed sanitized HTML from server
	case_name?: string
}
const ssg = reactive<{
	open: boolean
	studentId: string | null
	studentName: string | null
	title: string
	resource: ReturnType<typeof createResource>
	entries: SsgEntry[] | null
}>({
	open: false,
	studentId: null,
	studentName: null,
	title: 'Support Guidance',
	resource: createResource({
		url: 'api/method/ifitwala_ed.students.doctype.referral_case.referral_case.get_student_support_guidance',
		makeParams: () => (ssg.studentId ? { student: ssg.studentId } : {}),
		auto: false,
		transform: (r: any) => r?.message ?? [],
	}),
	entries: null,
})

function openSSG(stu: any) {
	ssg.studentId = stu.student
	ssg.studentName = stu.student_name
	ssg.title = `Support Guidance — ${stu.student_name}`
	ssg.open = true
	// fetch
	ssg.entries = null
	ssg.resource.reload().then(() => {
		ssg.entries = ssg.resource.data || []
	})
}

function openCase(caseName: string) {
	// open the Desk form in a new tab
	window.open(`/app/Referral%20Case/${encodeURIComponent(caseName)}`, '_blank', 'noopener')
}

function neatDate(dt?: string) {
	if (!dt) return ''
	try {
		const d = new Date(dt)
		return d.toLocaleDateString(undefined, { day: '2-digit', month: 'long', year: 'numeric' })
	} catch {
		return dt
	}
}

/** ---------------- Init & watchers ---------------- */
onMounted(() => {
	groups.reload()
})

watch(
	() => filters.student_group,
	(val) => {
		if (!val) resetStudentsData()
	}
)
</script>

<style scoped>
/* Optional: compact prose for SSG summaries */
.prose :where(p):not(:where(.not-prose *)) {
	margin-top: 0.25rem;
	margin-bottom: 0.25rem;
}
</style>
