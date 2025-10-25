<template>
	<div class="flex w-full flex-col gap-6">
		<div class="flex flex-wrap items-center justify-between gap-3">
			<div>
				<h1 class="text-xl font-semibold tracking-tight text-slate-900">Gradebook</h1>
				<p class="text-sm text-slate-500">Pick a student group, choose a task, and record student outcomes.</p>
			</div>
		</div>

		<div class="grid gap-6 lg:grid-cols-[20rem_1fr]">
			<!-- Group picker -->
			<section class="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
				<div class="flex items-center justify-between gap-2">
					<h2 class="text-sm font-semibold uppercase tracking-wide text-slate-500">Student Groups</h2>
					<Button size="sm" appearance="minimal" :loading="groupsResource.loading" @click="groupsResource.reload()">
						Refresh
					</Button>
				</div>

				<FormControl
					type="text"
					placeholder="Search group"
					:model-value="groupSearch"
					@update:modelValue="groupSearch = $event"
				/>

				<div class="flex-1 space-y-2 overflow-y-auto pr-1" style="max-height: 28rem">
					<div v-if="groupsResource.loading" class="space-y-2">
						<div v-for="n in 6" :key="n" class="h-16 animate-pulse rounded-xl bg-slate-100" />
					</div>
					<div v-else-if="!filteredGroups.length" class="rounded-xl border border-dashed border-slate-200 p-4 text-sm text-slate-500">
						No student groups found.
					</div>
					<ul v-else class="space-y-2">
						<li
							v-for="group in filteredGroups"
							:key="group.name"
						>
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

			<!-- Tasks + gradebook -->
			<section class="flex flex-col gap-4">
				<div class="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
					<div class="flex items-center justify-between gap-3">
						<div>
							<h2 class="text-sm font-semibold uppercase tracking-wide text-slate-500">Tasks</h2>
							<p class="text-sm text-slate-500">
								{{ selectedGroup ? selectedGroup.label : 'Select a student group to view its tasks.' }}
							</p>
						</div>
					</div>

					<div v-if="!selectedGroup" class="mt-4 rounded-xl border border-dashed border-slate-200 bg-slate-50/80 p-6 text-center text-sm text-slate-500">
						Choose a student group on the left to load its tasks.
					</div>

					<div v-else class="mt-4 space-y-3">
						<div v-if="tasksLoading" class="space-y-2">
							<div v-for="n in 4" :key="n" class="h-20 animate-pulse rounded-xl bg-slate-100" />
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
									<div class="flex flex-wrap items-center justify-between gap-2">
										<div>
											<p class="text-sm font-semibold">{{ task.title }}</p>
											<p class="text-xs text-slate-500">
												Due {{ formatDate(task.due_date) || '—' }}
												<span class="mx-1">•</span>
												Status {{ task.status || '—' }}
											</p>
										</div>
										<div class="flex flex-wrap items-center gap-2">
											<Badge v-if="task.points" variant="subtle">Points</Badge>
											<Badge v-if="task.binary" variant="subtle">Binary</Badge>
											<Badge v-if="task.criteria" variant="subtle">Criteria</Badge>
											<Badge v-if="task.observations" variant="subtle">Feedback</Badge>
										</div>
									</div>
								</button>
							</li>
						</ul>
					</div>
				</div>

				<div class="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
					<div class="flex items-center justify-between gap-3">
						<h2 class="text-sm font-semibold uppercase tracking-wide text-slate-500">Grade Entry</h2>
						<div v-if="selectedTask" class="flex items-center gap-2 text-xs text-slate-500">
							<span>Max Points:</span>
							<span class="font-semibold text-slate-700">{{ gradebook.task?.max_points || '—' }}</span>
						</div>
					</div>

					<div v-if="gradebookLoading" class="mt-6 flex justify-center">
						<Spinner class="text-blue-600" />
					</div>

					<div v-else-if="!selectedTask" class="mt-6 rounded-xl border border-dashed border-slate-200 bg-slate-50/80 p-8 text-center text-sm text-slate-500">
						Select a task to load its gradebook.
					</div>

					<div v-else-if="!gradebook.students.length" class="mt-6 rounded-xl border border-dashed border-slate-200 bg-slate-50/80 p-8 text-center text-sm text-slate-500">
						This task has no assigned students yet.
					</div>

					<div v-else class="mt-6 space-y-4">
						<article
							v-for="student in gradebook.students"
							:key="student.task_student"
							class="rounded-2xl border border-slate-200 p-4 shadow-sm transition hover:border-blue-200"
						>
							<div class="flex flex-wrap items-center justify-between gap-3">
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
									:placeholder="'Select status'"
									:model-value="studentStates[student.task_student]?.status || ''"
									@update:modelValue="onStatusChanged(student.task_student, $event)"
								/>

								<div v-if="gradebook.task?.points" class="space-y-1">
									<label class="block text-xs font-medium uppercase tracking-wide text-slate-500">Points Awarded</label>
									<FormControl
										type="number"
										:placeholder="'Points'"
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

								<div class="flex flex-col gap-2">
									<FormControl
										type="checkbox"
										:label="'Visible to Student'"
										:model-value="Boolean(studentStates[student.task_student]?.visible_to_student)"
										@update:modelValue="value => setVisibility(student.task_student, 'visible_to_student', value)"
									/>
									<FormControl
										type="checkbox"
										:label="'Visible to Guardian'"
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
									:placeholder="'Write feedback...'"
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
										@click="saveCriteria(student)"
									>
										Save Criteria
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
										@click="saveStudent(student)"
									>
										Save
									</Button>
									<Button
										v-if="gradebook.task?.criteria && gradebook.criteria.length"
										size="sm"
										appearance="minimal"
										:disabled="!studentStates[student.task_student]?.dirtyCriteria"
										:loading="studentStates[student.task_student]?.savingCriteria"
										@click="saveCriteria(student)"
									>
										Save Criteria
									</Button>
								</div>
							</div>
						</article>
					</div>
				</div>
			</section>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { Button, FormControl, Badge, FeatherIcon, Spinner, createResource, call, toast } from 'frappe-ui'

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

const groupsResource = createResource({
	url: 'ifitwala_ed.api.gradebook.fetch_groups',
	auto: true,
	transform: (res: unknown) => unwrapMessage<GroupSummary[]>(res) ?? [],
})

const groupSearch = ref('')
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

const groups = computed(() => (groupsResource.data as GroupSummary[]) || [])

const filteredGroups = computed(() => {
	if (!groupSearch.value) {
		return groups.value
	}
	const term = groupSearch.value.toLowerCase()
	return groups.value.filter(
		(group) =>
			group.label.toLowerCase().includes(term) ||
			(group.name && group.name.toLowerCase().includes(term)) ||
			(group.course && group.course.toLowerCase().includes(term)),
	)
})

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
}

function onPointsChanged(taskStudent: string, value: string | number | null) {
	const state = studentStates[taskStudent]
	if (!state) return
	const numberValue = value === '' || value === null ? null : Number(value)
	state.mark_awarded = numberValue
	state.total_mark = numberValue
	state.dirty = true
}

function toggleComplete(taskStudent: string) {
	const state = studentStates[taskStudent]
	if (!state) return
	state.complete = !state.complete
	state.dirty = true
	if (state.complete && !state.status) {
		state.status = 'Graded'
	}
}

function setVisibility(taskStudent: string, target: 'visible_to_student' | 'visible_to_guardian', value: boolean) {
	const state = studentStates[taskStudent]
	if (!state) return
	state[target] = value
	state.dirty = true
}

function onFeedbackChanged(taskStudent: string, value: string) {
	const state = studentStates[taskStudent]
	if (!state) return
	state.feedback = value
	state.dirty = true
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
}

function onCriterionFeedbackChanged(taskStudent: string, assessmentCriteria: string, value: string) {
	const state = studentStates[taskStudent]
	if (!state) return
	const target = state.criteria.find((item) => item.assessment_criteria === assessmentCriteria)
	if (!target) return
	target.feedback = value
	state.dirtyCriteria = true
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

async function saveStudent(student: StudentRow) {
	const state = studentStates[student.task_student]
	if (!state || !state.dirty) return
	if (!gradebook.task) return

	state.saving = true
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
		state.mark_awarded = result.mark_awarded ?? state.mark_awarded
		state.total_mark = result.total_mark ?? state.total_mark
		state.updated_on = result.updated_on ?? state.updated_on
		state.dirty = false
	} catch (error) {
		console.error('Failed to save student row', error)
		toast({
			title: 'Could not save student entry',
			appearance: 'danger',
		})
	} finally {
		state.saving = false
	}
}

async function saveCriteria(student: StudentRow) {
	const state = studentStates[student.task_student]
	if (!state || !state.dirtyCriteria) return
	if (!gradebook.task || !gradebook.task.criteria) return

	if (!student.student) {
		toast({
			title: 'Missing student identifier',
			appearance: 'danger',
		})
		return
	}
	state.savingCriteria = true
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
		if (payload && typeof payload.suggestion === 'number') {
			state.total_mark = payload.suggestion
			state.mark_awarded = payload.suggestion
		}
		state.dirtyCriteria = false
		state.updated_on = new Date().toISOString()
	} catch (error) {
		console.error('Failed to save criteria scores', error)
		toast({
			title: 'Could not save criteria scores',
			appearance: 'danger',
		})
	} finally {
		state.savingCriteria = false
	}
}
</script>
