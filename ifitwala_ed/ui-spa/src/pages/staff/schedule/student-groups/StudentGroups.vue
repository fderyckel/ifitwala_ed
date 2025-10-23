<!-- ifitwala_ed/ifitwala_ed/ui-spa/src/pages/staff/schedule/studen-groups/StudentGroups.vue -->
<template>
	<!-- Page wrapper -->
	<div class="min-h-full px-4 py-4 md:px-6 lg:px-8">
		<!-- Header -->
		<div class="flex items-center justify-between gap-3">
			<h1 class="text-xl font-semibold tracking-tight">Student Group Cards</h1>
			<div class="flex items-center gap-2">
				<Button appearance="primary" :loading="studentsLoading" @click="reloadStudents" :disabled="!filters.student_group">
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
				:options="groupOptions.value"
				option-label="label"
				option-value="value"
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
      <div v-else-if="studentsLoading" class="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
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
						<div class="mt-2 text-sm font-semibold leading-tight flex items-center gap-2">
							<span class="truncate">{{ stu.student_name }}</span>

							<span
								v-if="hasUpcomingBirthday(stu.birth_date)"
								class="text-amber-500"
								:title="`Birthday on ${birthdayTooltip(stu.birth_date)}`"
							>
								🎂
							</span>

							<button
								v-if="stu.medical_info"
								type="button"
								class="inline-flex items-center rounded-full border border-transparent bg-red-50 p-1 text-red-600 transition hover:border-red-200 hover:bg-red-100"
								:title="'View health note'"
								@click.stop="showMedical(stu)"
							>
								<FeatherIcon name="alert-circle" class="h-4 w-4" />
							</button>

							<button
								v-if="stu.has_ssg"
								type="button"
								class="inline-flex items-center"
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
				<Button appearance="primary" :loading="studentsLoading" @click="loadMore">
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
      <div v-if="ssg.loading" class="space-y-3">
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

	<Dialog v-model="medicalDialog.open" :options="{ title: `Health Note — ${medicalDialog.student}`, size: 'md' }">
		<template #body>
			<p class="text-sm text-slate-600 whitespace-pre-line">
				{{ medicalDialog.note }}
			</p>
		</template>
		<template #footer>
			<div class="flex w-full justify-end">
				<Button appearance="primary" @click="medicalDialog.open = false">Close</Button>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { nextTick } from 'vue'
import { Button, FormControl, Badge, Dialog, FeatherIcon, call, toast } from 'frappe-ui'

type Filters = {
  program: string | null
  course: string | null
  cohort: string | null
  student_group: string | null
}

type StudentEntry = {
  student: string
  student_name: string
  preferred_name?: string
  student_image?: string
  medical_info?: string | null
  birth_date?: string | null
  has_ssg?: boolean
}

type StudentsPayload = {
  students?: StudentEntry[]
  start?: number
  total?: number
  group_info?: { name?: string; program?: string; course?: string; cohort?: string }
}

type SsgEntry = {
  entry_datetime?: string
  status?: string
  assignee?: string
  author_full_name?: string
  summary?: string
  case_name?: string
}

const PAGE_LEN = 25

const filters = reactive<Filters>({
  program: null,
  course: null,
  cohort: null,
  student_group: null,
})

const groups = ref<any[]>([])
const groupsLoading = ref(false)

watch(groups, (newVal) => {
  console.debug('[watch] groups changed:', newVal)
})

const studentsState = reactive({
  students: [] as StudentEntry[],
  total: 0,
  group_info: {} as Record<string, any>,
})
const studentsLoading = ref(false)
const cursor = ref(0)

const groupOptions = computed(() =>
  (groups.value || []).map((row: any) => ({
    label: row.student_group_name || row.name,
    value: row.name,
  }))
)
const groupsEmpty = computed(() => !groupsLoading.value && groups.value.length === 0)

const groupInfo = computed(() => studentsState.group_info ?? {})
const groupSubtitle = computed(() => {
  const g = groupInfo.value
  return [g.program, g.course, g.cohort].filter(Boolean).join(' – ')
})

const showLoadMore = computed(() => studentsState.students.length < (studentsState.total || 0))

const ssg = reactive({
  open: false,
  loading: false,
  title: 'Support Guidance',
  entries: [] as SsgEntry[],
})

const medicalDialog = reactive({
  open: false,
  student: '' as string,
  note: '' as string,
})

function handleError(error: any, fallback: string) {
  console.error(fallback, error)
  const message = typeof error === 'string' ? error : error?.message || fallback
  toast({ appearance: 'danger', message })
}

async function fetchGroups() {
  groupsLoading.value = true;
  try {
    // Build the payload without undefined values
    const payload: any = {};
    if (filters.program) payload.program = filters.program;
    if (filters.course) payload.course = filters.course;
    if (filters.cohort) payload.cohort = filters.cohort;

    console.debug('Fetching groups with payload:', payload);

    const { message } = await call(
      'ifitwala_ed.api.student_groups.fetch_groups',
      payload,
    );

    groups.value = Array.isArray(message) ? message : [];
  } catch (error) {
    handleError(error, 'Unable to fetch student groups');
  } finally {
    groupsLoading.value = false;
  }
}

async function fetchStudents(options: { reset?: boolean; append?: boolean } = {}) {
  if (!filters.student_group) return;

  const { reset = false, append = false } = options;
  if (reset) resetStudentsData();

  studentsLoading.value = true;
  try {
    const payload: any = {
      student_group: filters.student_group,
      start: cursor.value,
      page_length: PAGE_LEN,
    };

    console.debug('Fetching students with payload:', payload);

    const { message } = await call(
      'ifitwala_ed.api.student_groups.fetch_group_students',
      payload,
    );

    // … update studentsState …
  } catch (error) {
    handleError(error, 'Unable to load students');
  } finally {
    studentsLoading.value = false;
  }
}


function onFilterChanged() {
  filters.student_group = null
  resetStudentsData()
  fetchGroups()
}

function onGroupPicked() {
  if (!filters.student_group) {
    resetStudentsData()
    return
  }
  fetchStudents({ reset: true })
}

function loadMore() {
  if (!filters.student_group || studentsLoading.value) return
  fetchStudents({ append: true })
}

function reloadStudents() {
  if (!filters.student_group || studentsLoading.value) return
  fetchStudents({ reset: true })
}

function resetStudentsData() {
  cursor.value = 0
  studentsState.students = []
  studentsState.total = 0
  studentsState.group_info = {}
}

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

function birthdayTooltip(birthDate?: string | null) {
  if (!birthDate) return ''
  try {
    const today = new Date()
    const target = new Date(birthDate)
    const thisYear = new Date(today.getFullYear(), target.getMonth(), target.getDate())
    const diffDays = Math.round((thisYear.getTime() - today.getTime()) / 86400000)
    if (Math.abs(diffDays) <= 5) {
      return thisYear.toLocaleDateString(undefined, {
        weekday: 'long',
        month: 'long',
        day: 'numeric',
      })
    }
  } catch (error) {
    console.warn('Failed to parse birth date', birthDate, error)
  }
  return ''
}

function hasUpcomingBirthday(birthDate?: string | null) {
  return !!birthdayTooltip(birthDate)
}

async function openSSG(stu: StudentEntry) {
  ssg.open = true
  ssg.loading = true
  ssg.title = `Support Guidance — ${stu.student_name}`
  ssg.entries = []
  try {
    const { message } = await call(
      'ifitwala_ed.students.doctype.referral_case.referral_case.get_student_support_guidance',
      { student: stu.student },
    )
    ssg.entries = message ?? []
  } catch (error) {
    handleError(error, 'Unable to load support guidance')
  } finally {
    ssg.loading = false
  }
}

function openCase(caseName: string) {
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

function showMedical(stu: StudentEntry) {
  if (!stu.medical_info) return
  medicalDialog.student = stu.student_name
  medicalDialog.note = stu.medical_info
  medicalDialog.open = true
}

onMounted(async () => {
  await nextTick()
  console.debug('[mounted] calling fetchGroups()...')
  await fetchGroups()
  console.debug('[mounted] groups fetched:', groups.value)
})
</script>

<style scoped>
/* Optional: compact prose for SSG summaries */
.prose :where(p):not(:where(.not-prose *)) {
	margin-top: 0.25rem;
	margin-bottom: 0.25rem;
}
</style>
