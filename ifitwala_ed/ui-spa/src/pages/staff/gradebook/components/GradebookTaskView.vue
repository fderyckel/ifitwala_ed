<template>
	<section
		ref="rootElement"
		class="flex h-fit flex-col overflow-hidden rounded-2xl border border-border bg-white shadow-sm transition-all hover:shadow-md"
	>
		<div class="border-b border-border/50 bg-gray-50/50 px-6 py-4">
			<div class="flex flex-wrap items-center justify-between gap-4">
				<div class="flex items-center gap-3">
					<h2 class="text-lg font-semibold text-ink">Grade Entry</h2>
					<div
						v-if="showMaxPointsPill(gradebook.task)"
						class="flex items-center gap-2 rounded-full border border-border/50 bg-white px-2 py-0.5 text-xs text-ink/60 shadow-sm"
					>
						<span class="font-medium">Max Points:</span>
						<span class="font-bold text-ink">{{ gradebook.task?.max_points || '—' }}</span>
					</div>
				</div>

				<div v-if="gradebook.students.length" class="flex flex-wrap items-center gap-2">
					<span class="text-xs font-medium uppercase tracking-wider text-ink/50">Visible to all:</span>
					<Button
						size="sm"
						appearance="minimal"
						:class="
							allStudentsVisible ? 'bg-sky/30 text-ink font-semibold' : 'text-ink/60 hover:text-ink'
						"
						@click="toggleVisibilityGroup('student')"
					>
						Students
					</Button>
					<Button
						size="sm"
						appearance="minimal"
						:class="
							allGuardiansVisible ? 'bg-sky/30 text-ink font-semibold' : 'text-ink/60 hover:text-ink'
						"
						@click="toggleVisibilityGroup('guardian')"
					>
						Guardians
					</Button>
				</div>
			</div>
		</div>

		<div class="min-h-[400px] flex-1 bg-white p-6">
			<div v-if="gradebookLoading" class="flex h-full flex-col items-center justify-center gap-3 pt-20">
				<Spinner class="h-8 w-8 text-canopy" />
				<p class="text-sm text-ink/50">Loading gradebook...</p>
			</div>

			<div
				v-else-if="!taskName"
				class="flex h-full flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed border-border/60 bg-gray-50/30 p-12 text-center text-ink/60"
			>
				<div class="rounded-full bg-gray-100 p-4">
					<FeatherIcon name="check-square" class="h-8 w-8 text-ink/30" />
				</div>
				<p class="text-lg font-medium text-ink">No Task Selected</p>
				<p class="max-w-xs text-sm">Choose a task from the left panel to begin entering grades.</p>
			</div>

			<div
				v-else-if="!gradebook.students.length"
				class="flex h-full flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed border-border/60 bg-gray-50/30 p-12 text-center text-ink/60"
			>
				<p class="text-lg font-medium text-ink">No Students Assigned</p>
				<p class="max-w-xs text-sm">This task has no students in the roster.</p>
				<Button size="md" appearance="primary" :loading="rosterSyncing" @click="syncRoster">Sync roster</Button>
			</div>

			<div v-else class="space-y-6">
				<GradebookQuizManualReview v-if="showsQuizManualReview && taskName" :task-name="taskName" />

				<template v-else>
					<article
						v-for="student in gradebook.students"
						:key="student.task_student"
						:data-gradebook-student="student.student"
						class="group relative rounded-xl border p-5 transition-all hover:bg-white hover:shadow-md"
						:class="
							focusStudent === student.student
								? 'border-leaf/60 bg-sky/10 shadow-sm ring-1 ring-leaf/20'
								: 'border-border bg-gray-50/30'
						"
					>
						<div class="mb-4 flex flex-wrap items-start justify-between gap-4 border-b border-border/40 pb-4">
							<div class="flex min-w-0 flex-1 items-center gap-4">
								<img
									:src="student.student_image || DEFAULT_STUDENT_IMAGE"
									alt=""
									class="h-12 w-12 rounded-full border border-white bg-white object-cover shadow-sm"
									loading="lazy"
									@error="onImgError"
								/>
								<div class="min-w-0 flex-1">
									<div class="flex flex-wrap items-center gap-x-4 gap-y-2">
										<p class="text-base font-bold text-ink transition-colors hover:text-leaf">
											{{ student.student_name }}
										</p>
										<div class="gradebook-student-visibility grid grid-cols-2 gap-x-4 gap-y-2">
											<label class="inline-flex cursor-pointer items-center gap-2 text-sm text-ink/70">
												<input
													type="checkbox"
													class="h-4 w-4 rounded border-border/70 text-leaf focus:ring-[rgb(var(--leaf-rgb)/0.35)]"
													:checked="Boolean(studentStates[student.task_student]?.visible_to_student)"
													@change="
														onVisibilityInputChange(student.task_student, 'visible_to_student', $event)
													"
												/>
												<span>Visible to Student</span>
											</label>
											<label class="inline-flex cursor-pointer items-center gap-2 text-sm text-ink/70">
												<input
													type="checkbox"
													class="h-4 w-4 rounded border-border/70 text-leaf focus:ring-[rgb(var(--leaf-rgb)/0.35)]"
													:checked="Boolean(studentStates[student.task_student]?.visible_to_guardian)"
													@change="
														onVisibilityInputChange(student.task_student, 'visible_to_guardian', $event)
													"
												/>
												<span>Visible to Guardian</span>
											</label>
										</div>
									</div>
									<div class="flex items-center gap-2 text-xs text-ink/50">
										<span v-if="student.student_id" class="font-mono">{{ student.student_id }}</span>
										<span>•</span>
										<span
											:class="{
												'text-leaf font-medium':
													studentStates[student.task_student]?.status === 'Finalized' ||
													studentStates[student.task_student]?.status === 'Released',
											}"
										>
											{{ studentStates[student.task_student]?.status || '—' }}
										</span>
									</div>
								</div>
							</div>

							<div class="flex flex-wrap items-center gap-2">
								<Badge
									v-if="showsBooleanResult(gradebook.task)"
									:variant="studentStates[student.task_student]?.complete ? 'subtle' : 'outline'"
									:theme="studentStates[student.task_student]?.complete ? 'green' : 'gray'"
									:class="studentStates[student.task_student]?.complete ? '!bg-leaf/10 !text-leaf' : ''"
								>
									<FeatherIcon
										:name="studentStates[student.task_student]?.complete ? 'check' : 'minus-circle'"
										class="mr-1 h-3 w-3"
									/>
									{{ booleanResultLabel(student.task_student) }}
								</Badge>

								<div
									v-if="showsScoreSummary(gradebook.task)"
									class="flex items-center rounded-lg border border-border/40 bg-white px-3 py-1.5 shadow-sm"
								>
									<span class="mr-2 text-xs font-medium uppercase tracking-wider text-ink/40">
										{{ scoreSummaryLabel(gradebook.task) }}
									</span>
									<span class="text-lg font-bold text-ink">
										{{ formatPoints(studentStates[student.task_student]?.mark_awarded) }}
									</span>
								</div>
							</div>
						</div>

						<div class="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
							<div class="space-y-4">
								<FormControl
									v-if="showsStatusControl(gradebook.task)"
									type="select"
									label="Status"
									:options="statusOptions"
									option-label="label"
									option-value="value"
									placeholder="Select status"
									:model-value="studentStates[student.task_student]?.status || ''"
									@update:modelValue="onStatusChanged(student.task_student, $event)"
								/>

								<div v-if="isPointsTask(gradebook.task)" class="space-y-1.5">
									<label class="block text-xs font-semibold uppercase tracking-wide text-ink/50">
										Points Awarded
									</label>
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

								<div v-if="showsBooleanResult(gradebook.task)" class="space-y-1.5">
									<label class="block text-xs font-semibold uppercase tracking-wide text-ink/50">
										{{ booleanControlLabel(gradebook.task) }}
									</label>
									<div class="grid grid-cols-2 gap-2">
										<button
											type="button"
											class="rounded-md border px-4 py-2 text-sm font-medium transition-all"
											:class="
												studentStates[student.task_student]?.complete
													? '!border-leaf !bg-leaf !text-white'
													: 'border-border/60 bg-white text-ink/70 hover:border-leaf/60 hover:text-leaf'
											"
											@click="setBooleanState(student.task_student, true)"
										>
											{{ booleanPositiveLabel(gradebook.task) }}
										</button>
										<button
											type="button"
											class="rounded-md border px-4 py-2 text-sm font-medium transition-all"
											:class="
												!studentStates[student.task_student]?.complete
													? 'border-slate-300 bg-slate-100 text-ink'
													: 'border-border/60 bg-white text-ink/70 hover:border-leaf/60 hover:text-leaf'
											"
											@click="setBooleanState(student.task_student, false)"
										>
											{{ booleanNegativeLabel(gradebook.task) }}
										</button>
									</div>
								</div>
							</div>

							<div v-if="supportsFeedback(gradebook.task)" class="space-y-1.5 md:col-span-1 lg:col-span-2">
								<label class="block text-xs font-semibold uppercase tracking-wide text-ink/50">Comment</label>
								<FormControl
									type="textarea"
									rows="5"
									placeholder="Add a comment for this student..."
									class="!h-full"
									:model-value="studentStates[student.task_student]?.feedback || ''"
									@update:modelValue="onFeedbackChanged(student.task_student, $event)"
								/>
							</div>
						</div>

						<div
							v-if="gradebook.task?.criteria && gradebook.criteria.length"
							class="mt-6 rounded-lg border border-border/60 bg-white p-4 shadow-sm"
						>
							<div class="mb-4 flex items-center justify-between">
								<h4 class="text-sm font-bold text-ink">Criteria Breakdown</h4>
								<Badge v-if="studentStates[student.task_student]?.dirtyCriteria" variant="subtle" theme="orange">
									Unsaved Changes
								</Badge>
							</div>
							<div class="grid gap-4 md:grid-cols-2">
								<div
									v-for="criterion in gradebook.criteria"
									:key="criterion.assessment_criteria"
									class="space-y-2 rounded-md bg-gray-50/50 p-3 ring-1 ring-border/40"
								>
									<div class="flex justify-between">
										<span class="text-sm font-medium text-ink">{{ criterion.criteria_name }}</span>
										<span v-if="criterion.criteria_weighting" class="text-xs text-ink/50">
											{{ criterion.criteria_weighting }}%
										</span>
									</div>
									<FormControl
										v-if="criterion.levels && criterion.levels.length"
										type="select"
										size="sm"
										:options="criterionLevelOptions(criterion)"
										placeholder="Level Achieved"
										:model-value="getCriterionState(student.task_student, criterion.assessment_criteria)?.level ?? null"
										@update:modelValue="level => onCriterionLevelChanged(student.task_student, criterion, level)"
									/>
									<FormControl
										v-else
										type="text"
										size="sm"
										placeholder="Level"
										:model-value="getCriterionState(student.task_student, criterion.assessment_criteria)?.level ?? ''"
										@update:modelValue="level => onCriterionLevelChanged(student.task_student, criterion, level)"
									/>
									<FormControl
										type="number"
										size="sm"
										:step="0.1"
										:min="0"
										placeholder="Points"
										:model-value="
											getCriterionState(student.task_student, criterion.assessment_criteria)?.level_points ?? 0
										"
										@update:modelValue="
											value =>
												onCriterionPointsChanged(student.task_student, criterion.assessment_criteria, value)
										"
									/>
									<FormControl
										v-if="supportsFeedback(gradebook.task)"
										type="textarea"
										rows="2"
										size="sm"
										placeholder="Criterion feedback"
										:model-value="
											getCriterionState(student.task_student, criterion.assessment_criteria)?.feedback || ''
										"
										@update:modelValue="
											value =>
												onCriterionFeedbackChanged(student.task_student, criterion.assessment_criteria, value)
										"
									/>
									<div class="flex items-center justify-between text-xs">
										<span class="text-ink/60">Score:</span>
										<span class="font-bold text-ink">
											{{
												formatPoints(
													getCriterionState(student.task_student, criterion.assessment_criteria)?.level_points
												)
											}}
										</span>
									</div>
								</div>
							</div>
						</div>

						<div class="mt-4 flex items-center justify-between border-t border-border/40 pt-4">
							<p class="text-xs text-ink/40">
								Last updated {{ formatDateTime(studentStates[student.task_student]?.updated_on) || 'Never' }}
							</p>
							<div class="flex gap-2">
								<Button
									v-if="gradebook.task?.criteria && gradebook.criteria.length"
									size="sm"
									appearance="white"
									:loading="studentStates[student.task_student]?.savingCriteria"
									:disabled="!studentStates[student.task_student]?.dirtyCriteria"
									@click="saveCriteria(student.task_student)"
								>
									Save Criteria
								</Button>
								<Button
									size="sm"
									appearance="primary"
									:loading="studentStates[student.task_student]?.saving"
									:disabled="!studentStates[student.task_student]?.dirty"
									@click="saveStudent(student.task_student)"
								>
									Save
								</Button>
							</div>
						</div>
					</article>
				</template>
			</div>
		</div>
	</section>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { Badge, Button, FeatherIcon, FormControl, Spinner, toast } from 'frappe-ui'
import { createGradebookService } from '@/lib/services/gradebook/gradebookService'
import type { CriterionPayload, TaskPayload } from '@/types/contracts/gradebook/get_task_gradebook'
import type { Response as UpdateTaskStudentResponse } from '@/types/contracts/gradebook/update_task_student'
import GradebookQuizManualReview from './GradebookQuizManualReview.vue'
import {
	DEFAULT_STUDENT_IMAGE,
	booleanControlLabel,
	booleanNegativeLabel,
	booleanPositiveLabel,
	formatDateTime,
	formatPoints,
	isAssessedQuizTask,
	isPointsTask,
	normalizeFeedback,
	scoreSummaryLabel,
	showMaxPointsPill,
	showsBooleanResult,
	showsScoreSummary,
	showsStatusControl,
	supportsFeedback,
} from '../gradebookUtils'

interface StudentCriterionState {
	assessment_criteria: string
	level: string | number | null
	level_points: number
	feedback: string
}

interface StudentState {
	status: string
	mark_awarded: number | null
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

interface TaskGradebookState {
	task: TaskPayload | null
	criteria: CriterionPayload[]
	students: Array<{
		task_student: string
		student: string
		student_name: string
		student_id?: string | null
		student_image?: string | null
		status?: string | null
		complete: 0 | 1
		mark_awarded: number | null
		feedback?: string | null
		visible_to_student: 0 | 1
		visible_to_guardian: 0 | 1
		updated_on?: string | null
		criteria_scores: Array<{
			assessment_criteria: string
			level: string | number | null
			level_points: number | null
			feedback?: string | null
		}>
	}>
}

const props = defineProps<{
	taskName: string | null
	focusStudent?: string | null
}>()

const gradebookService = createGradebookService()
const rootElement = ref<HTMLElement | null>(null)
const gradebookLoading = ref(false)
const rosterSyncing = ref(false)

const gradebook = reactive<TaskGradebookState>({
	task: null,
	criteria: [],
	students: [],
})

const studentStates = reactive<Record<string, StudentState>>({})
const loadVersion = ref(0)

const statusOptions = [
	{ label: 'Not Started', value: 'Not Started' },
	{ label: 'In Progress', value: 'In Progress' },
	{ label: 'Needs Review', value: 'Needs Review' },
	{ label: 'Moderated', value: 'Moderated' },
	{ label: 'Finalized', value: 'Finalized' },
	{ label: 'Released', value: 'Released' },
	{ label: 'Not Applicable', value: 'Not Applicable' },
]

const AUTOSAVE_DELAY = 2500
const studentSaveTimers: Record<string, ReturnType<typeof setTimeout> | null> = {}
const criteriaSaveTimers: Record<string, ReturnType<typeof setTimeout> | null> = {}

const showsQuizManualReview = computed(() => isAssessedQuizTask(gradebook.task))

const allStudentsVisible = computed(() => {
	if (!gradebook.students.length) return false
	return gradebook.students.every(student => Boolean(studentStates[student.task_student]?.visible_to_student))
})

const allGuardiansVisible = computed(() => {
	if (!gradebook.students.length) return false
	return gradebook.students.every(student => Boolean(studentStates[student.task_student]?.visible_to_guardian))
})

function showToast(title: string, appearance: 'danger' | 'success' | 'warning' = 'danger') {
	const toastApi = toast as unknown as
		| ((payload: { title: string; appearance?: string }) => void)
		| {
				error?: (message: string) => void
				create?: (payload: { title: string; appearance?: string }) => void
		  }
	if (typeof toastApi === 'function') {
		toastApi({ title, appearance })
		return
	}
	if (appearance === 'danger' && toastApi && typeof toastApi.error === 'function') {
		toastApi.error(title)
		return
	}
	if (toastApi && typeof toastApi.create === 'function') {
		toastApi.create({ title, appearance })
	}
}

function showDangerToast(title: string) {
	showToast(title, 'danger')
}

function showSuccessToast(title: string) {
	showToast(title, 'success')
}

function resetGradebook() {
	gradebook.task = null
	gradebook.criteria = []
	gradebook.students = []
	clearAllAutosaveTimers()
	for (const key of Object.keys(studentStates)) {
		delete studentStates[key]
	}
}

async function loadGradebook(taskName: string) {
	const version = loadVersion.value + 1
	loadVersion.value = version
	gradebookLoading.value = true
	try {
		const payload = await gradebookService.getTaskGradebook({ task: taskName })
		if (loadVersion.value !== version) {
			return
		}
		gradebook.task = payload.task
		gradebook.criteria = payload.criteria || []
		gradebook.students = payload.students || []
		initializeStudentStates()
		await scrollToFocusedStudent()
	} catch (error) {
		console.error('Failed to load gradebook', error)
		if (loadVersion.value === version) {
			showDangerToast('Could not load gradebook')
		}
	} finally {
		if (loadVersion.value === version) {
			gradebookLoading.value = false
		}
	}
}

async function syncRoster() {
	if (!props.taskName) {
		showToast('Select a task first.', 'warning')
		return
	}

	rosterSyncing.value = true
	try {
		const payload = await gradebookService.repairTaskRoster({ task: props.taskName })
		showSuccessToast(payload.message || 'Roster synced.')
		await loadGradebook(props.taskName)
	} catch (error) {
		console.error('Failed to sync task roster', error)
		showDangerToast('Could not sync the task roster')
	} finally {
		rosterSyncing.value = false
	}
}

function criterionLevelOptions(criterion: CriterionPayload) {
	return (criterion.levels || []).map(level => ({
		label: level.level,
		value: level.level,
	}))
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

function initializeStudentStates() {
	clearAllAutosaveTimers()
	for (const key of Object.keys(studentStates)) {
		delete studentStates[key]
	}

	for (const student of gradebook.students) {
		studentStates[student.task_student] = {
			status: student.status || 'Not Started',
			mark_awarded: student.mark_awarded,
			feedback: normalizeFeedback(student.feedback),
			visible_to_student: Boolean(student.visible_to_student),
			visible_to_guardian: Boolean(student.visible_to_guardian),
			complete: Boolean(student.complete),
			updated_on: student.updated_on,
			dirty: false,
			dirtyCriteria: false,
			saving: false,
			savingCriteria: false,
			criteria: student.criteria_scores.map(item => ({
				assessment_criteria: item.assessment_criteria,
				level: item.level,
				level_points: item.level_points ?? 0,
				feedback: normalizeFeedback(item.feedback),
			})),
		}
	}
}

function scheduleStudentSave(taskStudent: string) {
	const state = studentStates[taskStudent]
	if (!state) return

	const existing = studentSaveTimers[taskStudent]
	if (existing) {
		clearTimeout(existing)
	}

	studentSaveTimers[taskStudent] = setTimeout(() => {
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

	criteriaSaveTimers[taskStudent] = setTimeout(() => {
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

function onStatusChanged(taskStudent: string, value: string) {
	const state = studentStates[taskStudent]
	if (!state || state.status === value) return
	state.status = value
	state.dirty = true
	scheduleStudentSave(taskStudent)
}

function onPointsChanged(taskStudent: string, value: number | null) {
	const state = studentStates[taskStudent]
	if (!state || state.mark_awarded === value) return
	state.mark_awarded = value
	state.dirty = true
	scheduleStudentSave(taskStudent)
}

function setBooleanState(taskStudent: string, value: boolean) {
	const state = studentStates[taskStudent]
	if (!state || state.complete === value) return
	state.complete = value
	state.dirty = true
	scheduleStudentSave(taskStudent)
}

function setVisibility(taskStudent: string, field: 'visible_to_student' | 'visible_to_guardian', value: boolean) {
	const state = studentStates[taskStudent]
	if (!state || state[field] === value) return
	state[field] = value
	state.dirty = true
	scheduleStudentSave(taskStudent)
}

function onVisibilityInputChange(
	taskStudent: string,
	field: 'visible_to_student' | 'visible_to_guardian',
	event: Event
) {
	const target = event.target as HTMLInputElement | null
	setVisibility(taskStudent, field, Boolean(target?.checked))
}

function onFeedbackChanged(taskStudent: string, value: string) {
	const state = studentStates[taskStudent]
	if (!state || state.feedback === value) return
	state.feedback = value
	state.dirty = true
	scheduleStudentSave(taskStudent)
}

function getCriterionState(taskStudent: string, criteriaName: string) {
	const state = studentStates[taskStudent]
	return state?.criteria.find(criteria => criteria.assessment_criteria === criteriaName)
}

function onCriterionLevelChanged(taskStudent: string, criterionRow: CriterionPayload, levelValue: string | number | null) {
	const state = studentStates[taskStudent]
	if (!state) return
	const item = state.criteria.find(criteria => criteria.assessment_criteria === criterionRow.assessment_criteria)
	if (!item || item.level === levelValue) return

	const levelDef = criterionRow.levels.find(level => level.level === levelValue)
	item.level = levelValue
	item.level_points = levelDef ? levelDef.points : item.level_points
	state.dirtyCriteria = true
	scheduleCriteriaSave(taskStudent)
	if (state.dirty) {
		scheduleStudentSave(taskStudent)
	}
}

function onCriterionPointsChanged(taskStudent: string, criteriaName: string, value: number | null) {
	const state = studentStates[taskStudent]
	if (!state) return
	const item = state.criteria.find(criteria => criteria.assessment_criteria === criteriaName)
	if (!item) return

	const nextValue = typeof value === 'number' ? value : 0
	if (item.level_points === nextValue) return
	item.level_points = nextValue
	state.dirtyCriteria = true
	scheduleCriteriaSave(taskStudent)
	if (state.dirty) {
		scheduleStudentSave(taskStudent)
	}
}

function onCriterionFeedbackChanged(taskStudent: string, criteriaName: string, value: string) {
	const state = studentStates[taskStudent]
	if (!state) return
	const item = state.criteria.find(criteria => criteria.assessment_criteria === criteriaName)
	if (!item || item.feedback === value) return
	item.feedback = value
	state.dirtyCriteria = true
	scheduleCriteriaSave(taskStudent)
	if (state.dirty) {
		scheduleStudentSave(taskStudent)
	}
}

async function saveStudent(taskStudent: string) {
	const state = studentStates[taskStudent]
	if (!state) return

	state.saving = true
	try {
		const payload: Record<string, string | number | boolean | null> = {
			status: state.status,
			visible_to_student: state.visible_to_student,
			visible_to_guardian: state.visible_to_guardian,
		}
		if (isPointsTask(gradebook.task)) {
			payload.mark_awarded = state.mark_awarded
		}
		if (showsBooleanResult(gradebook.task)) {
			payload.complete = state.complete
		}
		if (supportsFeedback(gradebook.task)) {
			payload.feedback = state.feedback
		}
		const doc: UpdateTaskStudentResponse = await gradebookService.updateTaskStudent({
			task_student: taskStudent,
			updates: payload,
		})
		state.dirty = false
		state.updated_on = doc.updated_on
	} catch (error) {
		console.error('Save failed', error)
		showDangerToast('Failed to save changes')
	} finally {
		state.saving = false
		if (state.dirty) {
			scheduleStudentSave(taskStudent)
		}
	}
}

async function saveCriteria(taskStudent: string) {
	const state = studentStates[taskStudent]
	if (!state) return
	state.savingCriteria = true
	try {
		const criteriaScores = state.criteria
			.map(criteria => ({
				assessment_criteria: criteria.assessment_criteria,
				level: criteria.level,
				level_points: criteria.level_points ?? 0,
				feedback: criteria.feedback,
			}))
			.filter(row => row.assessment_criteria && row.level !== null && row.level !== '')

		if (criteriaScores.length) {
			const doc: UpdateTaskStudentResponse = await gradebookService.updateTaskStudent({
				task_student: taskStudent,
				updates: {
					criteria_scores: criteriaScores,
					...(supportsFeedback(gradebook.task) ? { feedback: state.feedback } : {}),
				},
			})
			if (doc?.updated_on) {
				state.updated_on = doc.updated_on
			}
		}
		state.dirtyCriteria = false
	} catch (error) {
		console.error(error)
		showDangerToast('Error saving criteria')
	} finally {
		state.savingCriteria = false
	}
}

function toggleVisibilityGroup(type: 'student' | 'guardian') {
	const field = type === 'student' ? 'visible_to_student' : 'visible_to_guardian'
	const targetValue = type === 'student' ? !allStudentsVisible.value : !allGuardiansVisible.value

	gradebook.students.forEach(student => {
		setVisibility(student.task_student, field, targetValue)
	})
}

function booleanResultLabel(taskStudent: string) {
	const state = studentStates[taskStudent]
	if (!state) return '—'
	return state.complete ? booleanPositiveLabel(gradebook.task) : booleanNegativeLabel(gradebook.task)
}

function onImgError(event: Event, fallback?: string) {
	const element = event.target as HTMLImageElement
	element.onerror = null
	element.src = fallback || DEFAULT_STUDENT_IMAGE
}

async function scrollToFocusedStudent() {
	if (!props.focusStudent || !rootElement.value) return
	await nextTick()
	const target = rootElement.value.querySelector<HTMLElement>(`[data-gradebook-student="${props.focusStudent}"]`)
	if (!target) return
	target.scrollIntoView({ block: 'center', behavior: 'smooth' })
}

watch(
	() => props.taskName,
	taskName => {
		resetGradebook()
		if (taskName) {
			void loadGradebook(taskName)
		}
	},
	{ immediate: true }
)

watch(
	() => props.focusStudent,
	() => {
		void scrollToFocusedStudent()
	}
)

onBeforeUnmount(() => {
	clearAllAutosaveTimers()
})
</script>
