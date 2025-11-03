<template>
	<div class="flex w-full flex-col gap-6">
		<div class="flex flex-wrap items-center justify-between gap-3">
			<div>
				<h1 class="text-xl font-semibold tracking-tight text-slate-900">Gradebook</h1>
				<p class="text-sm text-slate-500">Pick a student group, choose a task, and record student outcomes.</p>
			</div>
		</div>

		<div class="grid gap-4 lg:grid-cols-[minmax(18rem,1fr)_minmax(0,2fr)]">
			<div class="flex flex-col gap-4">
				<!-- Student groups -->
				<section class="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
					<div class="flex items-center justify-between gap-2">
						<h2 class="text-sm font-semibold uppercase tracking-wide text-slate-500">Student Groups</h2>
						<Button size="sm" appearance="minimal" :loading="groupsLoading" @click="reloadGroups()">
							Refresh
						</Button>
					</div>

					<FormControl
						type="text"
						placeholder="Search group"
						:model-value="groupSearch"
						@update:modelValue="value => (groupSearch = value)"
					/>

					<div class="flex-1 space-y-2 overflow-y-auto pr-1" style="max-height: 28rem">
						<div v-if="groupsLoading" class="space-y-2">
							<div v-for="n in 6" :key="`group-skeleton-${n}`" class="h-16 animate-pulse rounded-xl bg-slate-100" />
						</div>
						<div v-else-if="!groups.length" class="rounded-xl border border-dashed border-slate-200 p-4 text-sm text-slate-500">
							No student groups found.
						</div>
						<ul v-else class="space-y-2">
							<li v-for="group in groups" :key="group.name">
								<button
									type="button"
									class="w-full rounded-xl border px-3 py-3 text-left transition"
									:class="[
										selectedGroup?.name === group.name
											? 'border-blue-500 bg-blue-50 text-blue-800 shadow-sm'
											: 'border-slate-200 hover:border-blue-200 hover:bg-blue-50/50',
									]"
									@click="selectGroup(group)"
								>
									<div class="flex items-center justify-between gap-2">
										<p class="truncate text-sm font-semibold">{{ group.label }}</p>
										<span
											v-if="group.program || group.course"
											class="inline-flex shrink-0 items-center rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600"
										>
											{{ [group.program, group.course].filter(Boolean).join(' • ') }}
										</span>
									</div>
									<p v-if="group.cohort" class="mt-1 truncate text-xs text-slate-500">Cohort {{ group.cohort }}</p>
								</button>
							</li>
						</ul>
					</div>
				</section>

				<!-- Tasks -->
				<section class="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
					<div class="flex items-center justify-between gap-2">
						<div>
							<h2 class="text-sm font-semibold uppercase tracking-wide text-slate-500">Tasks</h2>
							<p class="text-sm text-slate-500">
								{{ selectedGroup ? selectedGroup.label : 'Select a student group to view its tasks.' }}
							</p>
						</div>
					</div>

					<div v-if="!selectedGroup" class="flex flex-1 items-center justify-center rounded-xl border border-dashed border-slate-200 bg-slate-50/80 p-6 text-center text-sm text-slate-500">
						Choose a student group to load its tasks.
					</div>

					<div v-else class="flex-1 space-y-3 overflow-y-auto pr-1" style="max-height: 28rem">
						<div v-if="tasksLoading" class="space-y-2">
							<div v-for="n in 4" :key="`task-skeleton-${n}`" class="h-20 animate-pulse rounded-xl bg-slate-100" />
						</div>
						<div v-else-if="!taskSummaries.length" class="rounded-xl border border-dashed border-slate-200 bg-slate-50/80 p-6 text-center text-sm text-slate-500">
							This student group has no tasks yet.
						</div>
						<ul v-else class="space-y-2">
							<li v-for="task in taskSummaries" :key="task.name">
								<button
									type="button"
									class="w-full rounded-xl border px-4 py-3 text-left transition"
									:class="[
										selectedTask?.name === task.name
											? 'border-blue-500 bg-blue-50 text-blue-800 shadow-sm'
											: 'border-slate-200 hover:border-blue-200 hover:bg-blue-50/50',
									]"
									@click="selectTask(task)"
								>
									<div class="flex flex-col gap-1">
										<p class="text-sm font-semibold text-slate-900">{{ task.title }}</p>
										<div class="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
											<span>
												Due {{ formatDate(task.due_date) || '—' }}
												<span class="mx-1">•</span>
												Status {{ task.status || '—' }}
											</span>
											<div class="flex flex-wrap items-center gap-2">
												<Badge v-if="task.points" variant="subtle">Points</Badge>
												<Badge v-if="task.binary" variant="subtle">Binary</Badge>
												<Badge v-if="task.criteria" variant="subtle">Criteria</Badge>
												<Badge v-if="task.observations" variant="subtle">Feedback</Badge>
											</div>
										</div>
									</div>
								</button>
							</li>
						</ul>
					</div>
				</section>
			</div>

			<!-- Grade entry -->
			<section class="flex flex-col rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
				<div class="flex flex-wrap items-center justify-between gap-3">
					<h2 class="text-sm font-semibold uppercase tracking-wide text-slate-500">Grade Entry</h2>
					<div class="flex flex-wrap items-center gap-2 text-xs text-slate-500">
						<span v-if="selectedTask">Max Points: <span class="font-semibold text-slate-700">{{ gradebook.task?.max_points || '—' }}</span></span>
						<div v-if="gradebook.students.length" class="flex items-center gap-2">
							<Button size="sm" appearance="minimal" @click="applyVisibilityToAll(true)">
								Show to Everyone
							</Button>
							<Button size="sm" appearance="minimal" @click="applyVisibilityToAll(false)">
								Hide from Everyone
							</Button>
						</div>
					</div>
				</div>

				<div v-if="gradebookLoading" class="mt-6 flex flex-1 items-center justify-center">
					<Spinner class="text-blue-600" />
				</div>

				<div v-else-if="!selectedTask" class="mt-6 flex flex-1 items-center justify-center rounded-xl border border-dashed border-slate-200 bg-slate-50/80 p-8 text-center text-sm text-slate-500">
					Select a task to load its gradebook.
				</div>

				<div v-else-if="!gradebook.students.length" class="mt-6 flex flex-1 items-center justify-center rounded-xl border border-dashed border-slate-200 bg-slate-50/80 p-8 text-center text-sm text-slate-500">
					This task has no assigned students yet.
				</div>

				<div v-else class="mt-6 space-y-4 overflow-y-auto pr-1" style="max-height: 70vh">
					<article
						v-for="student in gradebook.students"
						:key="student.task_student"
						class="rounded-2xl border border-slate-200 p-4 shadow-sm transition hover:border-blue-200"
					>
						<div class="flex flex-wrap items-center justify-between gap-3">
							<div class="flex items-center gap-3">
								<img
									:src="thumb(student.student_image)"
									alt=""
									class="h-12 w-12 rounded-full border border-slate-200 object-cover"
									loading="lazy"
									@error="onImgError"
								/>
								<div>
									<p class="text-sm font-semibold text-slate-900">
										{{ student.student_name }}
										<span v-if="student.student_id" class="ml-2 text-xs font-medium text-slate-500">ID {{ student.student_id }}</span>
									</p>
									<p class="text-xs text-slate-500">
										Status:
										<span class="font-medium text-slate-600">{{ studentStates[student.task_student]?.status || '—' }}</span>
									</p>
								</div>
							</div>
							<div class="flex flex-wrap items-center gap-2 text-xs text-slate-500">
								<span v-if="studentStates[student.task_student]?.complete" class="inline-flex items-center gap-1 rounded-full bg-green-50 px-2 py-1 font-medium text-green-600">
									<FeatherIcon name="check-circle" class="h-3.5 w-3.5" />
									Complete
								</span>
								<span v-else-if="gradebook.task?.binary" class="inline-flex items-center gap-1 rounded-full bg-rose-50 px-2 py-1 font-medium text-rose-600">
									<FeatherIcon name="x-circle" class="h-3.5 w-3.5" />
									Incomplete
								</span>
								<span class="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-1 font-medium text-slate-600">
									<FeatherIcon name="award" class="h-3.5 w-3.5" />
									{{ formatPoints(studentStates[student.task_student]?.total_mark) }}
								</span>
							</div>
						</div>

						<div class="mt-4 grid gap-4 md:grid-cols-2">
							<FormControl
								type="select"
								label="Status"
								:options="statusOptions"
								option-label="label"
								option-value="value"
								placeholder="Select status"
								:model-value="studentStates[student.task_student]?.status || ''"
								@update:modelValue="onStatusChanged(student.task_student, $event)"
							/>

							<div v-if="gradebook.task?.points" class="space-y-1">
								<label class="block text-xs font-medium uppercase tracking-wide text-slate-500">Points Awarded</label>
								<FormControl
									type="number"
									placeholder="Points"
									:step="0.5"
									:min="0"
									:max="gradebook.task?.max_points || undefined"
									:model-value="studentStates[student.task_student]?.mark_awarded"
									@update:modelValue="onPointsChanged(student.task_student, $event)"
								/>
							</div>

							<div v-if="gradebook.task?.binary" class="space-y-1">
								<label class="block text-xs font-medium uppercase tracking-wide text-slate-500">Completion</label>
								<div class="flex gap-2">
									<button
										type="button"
										class="inline-flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium text-white shadow-sm transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
										:class="studentStates[student.task_student]?.complete
											? 'bg-green-600 hover:bg-green-700 focus-visible:outline-green-600'
											: 'bg-rose-600 hover:bg-rose-700 focus-visible:outline-rose-600'"
										@click="toggleComplete(student.task_student)"
									>
										<FeatherIcon
											:name="studentStates[student.task_student]?.complete ? 'check' : 'x'"
											class="h-4 w-4"
										/>
										<span>{{ studentStates[student.task_student]?.complete ? 'Complete' : 'Incomplete' }}</span>
									</button>
								</div>
							</div>

							<div class="flex flex-wrap items-center gap-4">
								<FormControl
									type="checkbox"
									:label="'Visible to Student'"
									class="inline-flex items-center"
									:model-value="Boolean(studentStates[student.task_student]?.visible_to_student)"
									@update:modelValue="value => setVisibility(student.task_student, 'visible_to_student', value)"
								/>
								<FormControl
									type="checkbox"
									:label="'Visible to Guardian'"
									class="inline-flex items-center"
									:model-value="Boolean(studentStates[student.task_student]?.visible_to_guardian)"
									@update:modelValue="value => setVisibility(student.task_student, 'visible_to_guardian', value)"
								/>
							</div>
						</div>

						<div v-if="gradebook.task?.observations" class="mt-4 space-y-1">
							<label class="block text-xs font-medium uppercase tracking-wide text-slate-500">Feedback</label>
							<FormControl
								type="textarea"
								rows="3"
								placeholder="Write feedback..."
								:model-value="studentStates[student.task_student]?.feedback || ''"
								@update:modelValue="onFeedbackChanged(student.task_student, $event)"
							/>
						</div>

						<div v-if="gradebook.task?.criteria && gradebook.criteria.length" class="mt-6 space-y-4 rounded-xl border border-slate-200 bg-slate-50/80 p-4">
							<div class="flex items-center justify-between gap-2">
								<p class="text-sm font-semibold text-slate-700">Criteria Scores</p>
								<Button
									size="sm"
									appearance="minimal"
									:disabled="!studentStates[student.task_student]?.dirtyCriteria"
									:loading="studentStates[student.task_student]?.savingCriteria"
									@click="saveCriteria(student.task_student)"
								>
									Save Criteria Now
								</Button>
							</div>
							<div class="grid gap-4 md:grid-cols-2">
								<div
									v-for="criterion in gradebook.criteria"
									:key="criterion.assessment_criteria"
									class="rounded-lg border border-slate-200 bg-white p-3 shadow-sm"
								>
									<p class="text-sm font-semibold text-slate-800">{{ criterion.criteria_name }}</p>
									<p v-if="criterion.criteria_weighting" class="text-xs text-slate-500">
										Weight {{ criterion.criteria_weighting }}%
									</p>
									<FormControl
										class="mt-2"
										type="select"
										:options="criterion.levels"
										option-label="level"
										option-value="level"
										placeholder="Select level"
										:model-value="getCriterionState(student.task_student, criterion.assessment_criteria)?.level ?? null"
										@update:modelValue="level => onCriterionLevelChanged(student.task_student, criterion, level)"
									/>
									<FormControl
										v-if="hasCriterionFeedback"
										class="mt-2"
										type="textarea"
										rows="2"
										placeholder="Criterion feedback"
										:model-value="getCriterionState(student.task_student, criterion.assessment_criteria)?.feedback || ''"
										@update:modelValue="value => onCriterionFeedbackChanged(student.task_student, criterion.assessment_criteria, value)"
									/>
									<p class="mt-2 text-xs text-slate-500">
										Points:
										<span class="font-semibold text-slate-700">
											{{ formatPoints(getCriterionState(student.task_student, criterion.assessment_criteria)?.level_points) }}
										</span>
									</p>
								</div>
							</div>
						</div>

						<div class="mt-6 flex flex-wrap items-center justify-between gap-3">
							<div class="text-xs text-slate-500">
								Last updated:
								<span class="font-medium text-slate-700">
									{{ formatDateTime(studentStates[student.task_student]?.updated_on) || 'Not yet' }}
								</span>
							</div>
							<div class="flex flex-wrap items-center gap-2">
								<Button
									size="sm"
									appearance="secondary"
									:disabled="!studentStates[student.task_student]?.dirty"
									:loading="studentStates[student.task_student]?.saving"
									@click="saveStudent(student.task_student)"
								>
									Save Now
								</Button>
								<Button
									v-if="gradebook.task?.criteria && gradebook.criteria.length"
									size="sm"
									appearance="minimal"
									:disabled="!studentStates[student.task_student]?.dirtyCriteria"
									:loading="studentStates[student.task_student]?.savingCriteria"
									@click="saveCriteria(student.task_student)"
								>
									Save Criteria Now
								</Button>
							</div>
						</div>
					</article>
				</div>
			</section>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { Button, FormControl, Badge, FeatherIcon, Spinner, call, toast } from 'frappe-ui'

interface GroupSummary {
	name: string
	label: string
	program?: string | null
	course?: string | null
	cohort?: string | null
	academic_year?: string | null
}

interface TaskSummary {
	name: string
	title: string
	due_date?: string | null
	status?: string | null
	points?: number
	binary?: number
	criteria?: number
	observations?: number
	max_points?: number
}

interface TaskPayload {
	name: string
	title: string
	student_group: string
	due_date?: string | null
	points: number
	binary: number
	criteria: number
	observations: number
	max_points: number
}

interface CriterionPayload {
	assessment_criteria: string
	criteria_name: string
	criteria_weighting: number
	levels: { level: string; points: number }[]
}

interface StudentCriterionState {
	assessment_criteria: string
	level: string | number | null
	level_points: number
	feedback: string
}

interface StudentRow {
	task_student: string
	student: string
	student_name: string
	student_id?: string | null
	student_image?: string | null
	status?: string | null
	complete: number
	mark_awarded: number | null
	total_mark: number | null
	feedback?: string | null
	visible_to_student: number
	visible_to_guardian: number
	updated_on?: string | null
	criteria_scores: {
		assessment_criteria: string
		level: string | number | null
		level_points: number
		feedback?: string | null
	}[]
}

interface StudentState {
	status: string
	mark_awarded: number | null
	total_mark: number | null
	feedback: string
	visible_to_student: boolean
	visible_to_guardian: boolean
	complete: boolean
	criteria: StudentCriterionState[]
	updated_on?: string | null
	dirty: boolean
	dirtyCriteria: boolean
	saving: boolean
	savingCriteria: boolean
}

function unwrapMessage<T>(res: any): T | undefined {
	if (res && typeof res === 'object' && 'message' in res) {
		return (res as any).message
	}
	return res as T
}

const statusOptions = [
	{ label: 'Assigned', value: 'Assigned' },
	{ label: 'In Progress', value: 'In Progress' },
	{ label: 'Graded', value: 'Graded' },
	{ label: 'Returned', value: 'Returned' },
	{ label: 'Missed', value: 'Missed' },
]

const groups = ref<GroupSummary[]>([])
const groupsLoading = ref(false)
const groupSearch = ref('')
let groupSearchTimer: ReturnType<typeof setTimeout> | null = null

const selectedGroup = ref<GroupSummary | null>(null)
const taskSummaries = ref<TaskSummary[]>([])
const tasksLoading = ref(false)
const selectedTask = ref<TaskSummary | null>(null)
const gradebookLoading = ref(false)

const gradebook = reactive<{
	task: TaskPayload | null
	criteria: CriterionPayload[]
	students: StudentRow[]
}>({
	task: null,
	criteria: [],
	students: [],
})

const studentStates = reactive<Record<string, StudentState>>({})

const hasCriterionFeedback = computed(() => gradebook.criteria.length > 0)

const DEFAULT_STUDENT_IMAGE = '/assets/ifitwala_ed/images/default_student_image.png'

function slugifyFilename(filename: string) {
	return filename
		.replace(/\.[^.]+$/, '')
		.toLowerCase()
		.replace(/[^a-z0-9]+/g, '_')
		.replace(/^_+|_+$/g, '')
}

function thumb(originalUrl?: string | null) {
	if (!originalUrl) return DEFAULT_STUDENT_IMAGE
	if (originalUrl.startsWith('/files/gallery_resized/student/')) return originalUrl
	if (!originalUrl.startsWith('/files/student/')) return DEFAULT_STUDENT_IMAGE
	const base = slugifyFilename(originalUrl.split('/').pop() || '')
	return `/files/gallery_resized/student/thumb_${base}.webp`
}

function onImgError(event: Event, fallback?: string) {
	const element = event.target as HTMLImageElement
	element.onerror = null
	element.src = fallback || DEFAULT_STUDENT_IMAGE
}

const AUTOSAVE_DELAY = 2500
const studentSaveTimers: Record<string, ReturnType<typeof setTimeout> | null> = {}
const criteriaSaveTimers: Record<string, ReturnType<typeof setTimeout> | null> = {}

async function loadGroups(search?: string) {
	groupsLoading.value = true
	try {
		const payload: Record<string, unknown> = {}
		if (search && search.trim()) {
			payload.search = search.trim()
		}
		const response = await call('ifitwala_ed.api.gradebook.fetch_groups', payload)
		const rows = unwrapMessage<GroupSummary[]>(response) ?? []
		if (selectedGroup.value && selectedGroup.value.name && !rows.find((row) => row.name === selectedGroup.value?.name)) {
			rows.unshift(selectedGroup.value)
		}
		groups.value = rows
	} catch (error) {
		console.error('Failed to load student groups', error)
		toast({
			title: 'Could not load student groups',
			appearance: 'danger',
		})
	} finally {
		groupsLoading.value = false
	}
}

function reloadGroups() {
	void loadGroups(groupSearch.value)
}

function clearAllAutosaveTimers() {
	for (const key of Object.keys(studentSaveTimers)) {
		const handle = studentSaveTimers[key]
		if (handle) {
			clearTimeout(handle)
		}
		delete studentSaveTimers[key]
	}
	for (const key of Object.keys(criteriaSaveTimers)) {
		const handle = criteriaSaveTimers[key]
		if (handle) {
			clearTimeout(handle)
		}
		delete criteriaSaveTimers[key]
	}
}

function scheduleStudentSave(taskStudent: string) {
	const state = studentStates[taskStudent]
	if (!state) return

	const existing = studentSaveTimers[taskStudent]
	if (existing) {
		clearTimeout(existing)
	}

	studentSaveTimers[taskStudent] = window.setTimeout(() => {
		studentSaveTimers[taskStudent] = null
		if (!state.dirty) {
			return
		}
		if (state.saving) {
			scheduleStudentSave(taskStudent)
			return
		}
		void saveStudent(taskStudent)
	}, AUTOSAVE_DELAY)
}

function scheduleCriteriaSave(taskStudent: string) {
	const state = studentStates[taskStudent]
	if (!state) return

	const existing = criteriaSaveTimers[taskStudent]
	if (existing) {
		clearTimeout(existing)
	}

	criteriaSaveTimers[taskStudent] = window.setTimeout(() => {
		criteriaSaveTimers[taskStudent] = null
		if (!state.dirtyCriteria) {
			return
		}
		if (state.savingCriteria) {
			scheduleCriteriaSave(taskStudent)
			return
		}
		void saveCriteria(taskStudent)
	}, AUTOSAVE_DELAY)
}

watch(
	() => groupSearch.value,
	(value) => {
		if (groupSearchTimer) {
			clearTimeout(groupSearchTimer)
		}
		groupSearchTimer = window.setTimeout(() => {
			groupSearchTimer = null
			void loadGroups(value)
		}, 400)
	},
)

watch(
	() => selectedGroup.value?.name,
	(groupName) => {
		taskSummaries.value = []
		selectedTask.value = null
		gradebook.task = null
		gradebook.criteria = []
		gradebook.students = []
		if (groupName) {
			void loadTasks(groupName)
		}
	},
)

watch(
	() => selectedTask.value?.name,
	(taskName) => {
		gradebook.task = null
		gradebook.criteria = []
		gradebook.students = []
		if (taskName) {
			void loadGradebook(taskName)
		}
	},
)

function selectGroup(group: GroupSummary) {
	selectedGroup.value = group
}

onMounted(() => {
	void loadGroups()
})

onBeforeUnmount(() => {
	clearAllAutosaveTimers()
	if (groupSearchTimer) {
		clearTimeout(groupSearchTimer)
		groupSearchTimer = null
	}
})

async function loadTasks(groupName: string) {
	tasksLoading.value = true
	try {
		const response = await call('ifitwala_ed.api.gradebook.fetch_group_tasks', {
			student_group: groupName,
		})
		const payload = unwrapMessage<{ tasks: TaskSummary[] }>(response)
		taskSummaries.value = payload?.tasks ?? []
	} catch (error) {
		console.error('Failed to load tasks', error)
		toast({
			title: 'Could not load tasks',
			appearance: 'danger',
		})
	} finally {
		tasksLoading.value = false
	}
}

function selectTask(task: TaskSummary) {
	selectedTask.value = task
}

async function loadGradebook(taskName: string) {
	gradebookLoading.value = true
	try {
		const response = await call('ifitwala_ed.api.gradebook.get_task_gradebook', { task: taskName })
		const payload = unwrapMessage<{ task: TaskPayload; criteria: CriterionPayload[]; students: StudentRow[] }>(response)
		if (payload) {
			gradebook.task = payload.task
			gradebook.criteria = payload.criteria || []
			gradebook.students = payload.students || []
			initializeStudentStates()
		}
	} catch (error) {
		console.error('Failed to load gradebook', error)
		toast({
			title: 'Could not load gradebook',
			appearance: 'danger',
		})
	} finally {
		gradebookLoading.value = false
	}
}

function initializeStudentStates() {
	clearAllAutosaveTimers()
	for (const key of Object.keys(studentStates)) {
		delete studentStates[key]
	}
	for (const student of gradebook.students) {
		studentStates[student.task_student] = {
			status: student.status || '',
			mark_awarded: student.mark_awarded,
			total_mark: student.total_mark,
			feedback: student.feedback || '',
			visible_to_student: Boolean(student.visible_to_student),
			visible_to_guardian: Boolean(student.visible_to_guardian),
			complete: Boolean(student.complete),
			criteria: student.criteria_scores.map((score) => ({
				assessment_criteria: score.assessment_criteria,
				level: score.level ?? null,
				level_points: score.level_points || 0,
				feedback: score.feedback || '',
			})),
			updated_on: student.updated_on || undefined,
			dirty: false,
			dirtyCriteria: false,
			saving: false,
			savingCriteria: false,
		}
	}
}

function onStatusChanged(taskStudent: string, value: string) {
	const state = studentStates[taskStudent]
	if (!state) return
	state.status = value
	state.dirty = true
	scheduleStudentSave(taskStudent)
}

function onPointsChanged(taskStudent: string, value: string | number | null) {
	const state = studentStates[taskStudent]
	if (!state) return
	const numberValue = value === '' || value === null ? null : Number(value)
	state.mark_awarded = numberValue
	state.total_mark = numberValue
	state.dirty = true
	scheduleStudentSave(taskStudent)
}

function toggleComplete(taskStudent: string) {
	const state = studentStates[taskStudent]
	if (!state) return
	state.complete = !state.complete
	state.dirty = true
	if (state.complete && !state.status) {
		state.status = 'Graded'
	}
	scheduleStudentSave(taskStudent)
}

function setVisibility(taskStudent: string, target: 'visible_to_student' | 'visible_to_guardian', value: boolean) {
	const state = studentStates[taskStudent]
	if (!state) return
	state[target] = value
	state.dirty = true
	scheduleStudentSave(taskStudent)
}

function onFeedbackChanged(taskStudent: string, value: string) {
	const state = studentStates[taskStudent]
	if (!state) return
	state.feedback = value
	state.dirty = true
	scheduleStudentSave(taskStudent)
}

function getCriterionState(taskStudent: string, assessmentCriteria: string) {
	const state = studentStates[taskStudent]
	if (!state) return undefined
	return state.criteria.find((item) => item.assessment_criteria === assessmentCriteria)
}

function onCriterionLevelChanged(taskStudent: string, criterion: CriterionPayload, level: string | number | null) {
	const state = studentStates[taskStudent]
	if (!state) return
	const target = state.criteria.find((item) => item.assessment_criteria === criterion.assessment_criteria)
	if (!target) return
	target.level = level
	const levelEntry = criterion.levels.find((entry) => entry.level === level)
	target.level_points = levelEntry ? levelEntry.points : 0
	state.dirtyCriteria = true
	scheduleCriteriaSave(taskStudent)
}

function onCriterionFeedbackChanged(taskStudent: string, assessmentCriteria: string, value: string) {
	const state = studentStates[taskStudent]
	if (!state) return
	const target = state.criteria.find((item) => item.assessment_criteria === assessmentCriteria)
	if (!target) return
	target.feedback = value
	state.dirtyCriteria = true
	scheduleCriteriaSave(taskStudent)
}

function formatDate(value?: string | null) {
	if (!value) return ''
	const date = new Date(value)
	if (Number.isNaN(date.getTime())) return value
	return date.toLocaleDateString()
}

function formatDateTime(value?: string | null) {
	if (!value) return ''
	const date = new Date(value)
	if (Number.isNaN(date.getTime())) return value
	return date.toLocaleString()
}

function formatPoints(value?: number | null) {
	if (value === undefined || value === null) return '—'
	return Number(value).toFixed(2).replace(/\.00$/, '')
}

async function saveStudent(taskStudent: string) {
	const state = studentStates[taskStudent]
	if (!state || !gradebook.task) return
	const student = gradebook.students.find((row) => row.task_student === taskStudent)
	if (!student) return

	const pendingTimer = studentSaveTimers[taskStudent]
	if (pendingTimer) {
		clearTimeout(pendingTimer)
		studentSaveTimers[taskStudent] = null
	}

	state.saving = true
	const previousDirty = state.dirty
	state.dirty = false
	try {
		const payload: Record<string, any> = {
			status: state.status,
			visible_to_student: state.visible_to_student ? 1 : 0,
			visible_to_guardian: state.visible_to_guardian ? 1 : 0,
			complete: state.complete ? 1 : 0,
		}

		if (gradebook.task.points) {
			payload.mark_awarded = state.mark_awarded
			payload.total_mark = state.total_mark
		}

		if (gradebook.task.observations !== 0) {
			payload.feedback = state.feedback
		}

		const response = await call('ifitwala_ed.api.gradebook.update_task_student', {
			task_student: student.task_student,
			updates: payload,
		})
		const result = unwrapMessage<any>(response) || {}
		if (!state.dirty) {
			if (result.mark_awarded !== undefined) {
				state.mark_awarded = result.mark_awarded
				state.total_mark = result.total_mark ?? result.mark_awarded ?? state.total_mark
			} else if (result.total_mark !== undefined) {
				state.total_mark = result.total_mark
			}
			state.updated_on = result.updated_on ?? state.updated_on ?? new Date().toISOString()
		}
	} catch (error) {
		console.error('Failed to save student row', error)
		toast({
			title: 'Could not save student entry',
			appearance: 'danger',
		})
		state.dirty = previousDirty || state.dirty
	} finally {
		state.saving = false
		if (state.dirty) {
			scheduleStudentSave(taskStudent)
		}
	}
}

async function saveCriteria(taskStudent: string) {
	const state = studentStates[taskStudent]
	if (!state || !gradebook.task || !gradebook.task.criteria) return
	const student = gradebook.students.find((row) => row.task_student === taskStudent)
	if (!student) return

	if (!student.student) {
		toast({
			title: 'Missing student identifier',
			appearance: 'danger',
		})
		return
	}
	const pendingTimer = criteriaSaveTimers[taskStudent]
	if (pendingTimer) {
		clearTimeout(pendingTimer)
		criteriaSaveTimers[taskStudent] = null
	}

	state.savingCriteria = true
	const previousDirty = state.dirtyCriteria
	state.dirtyCriteria = false
	try {
		const rows = state.criteria.map((item) => ({
			assessment_criteria: item.assessment_criteria,
			level: item.level,
			level_points: item.level_points,
			feedback: item.feedback,
		}))

		const response = await call('ifitwala_ed.assessment.gradebook_utils.upsert_task_criterion_scores', {
			task: gradebook.task.name,
			student: student.student,
			rows,
		})
		const payload = unwrapMessage<{ suggestion: number }>(response)
		if (!state.dirtyCriteria && payload && typeof payload.suggestion === 'number') {
			state.total_mark = payload.suggestion
			state.mark_awarded = payload.suggestion
			state.dirty = true
			scheduleStudentSave(taskStudent)
		}
	} catch (error) {
		console.error('Failed to save criteria scores', error)
		toast({
			title: 'Could not save criteria scores',
			appearance: 'danger',
		})
		state.dirtyCriteria = previousDirty || state.dirtyCriteria
	} finally {
		state.savingCriteria = false
		if (!state.dirtyCriteria) {
			state.updated_on = new Date().toISOString()
		}
		if (state.dirtyCriteria) {
			scheduleCriteriaSave(taskStudent)
		}
	}
}

function applyVisibilityToAll(value: boolean) {
	if (!gradebook.students.length) return
	let touched = false
	for (const student of gradebook.students) {
		const state = studentStates[student.task_student]
		if (!state) continue
		const already =
			state.visible_to_student === value &&
			state.visible_to_guardian === value
		if (already) continue
		state.visible_to_student = value
		state.visible_to_guardian = value
		state.dirty = true
		scheduleStudentSave(student.task_student)
		touched = true
	}
	if (touched) {
		toast({
			title: value ? 'Visibility enabled for everyone' : 'Visibility cleared for everyone',
			appearance: 'success',
		})
	}
}
</script>
