<template>
	<section
		ref="rootElement"
		class="flex h-fit flex-col overflow-hidden rounded-2xl border border-border bg-white shadow-sm transition-all hover:shadow-md"
	>
		<div class="border-b border-border/50 bg-gray-50/50 px-6 py-4">
			<div class="flex flex-wrap items-center justify-between gap-4">
				<div class="space-y-1">
					<h2 class="text-lg font-semibold text-ink">Task Workspace</h2>
					<p class="max-w-2xl text-sm text-ink/60">
						Open one student at a time in the grading drawer. Evidence review, marking, official
						result, and release stay in one workflow.
					</p>
				</div>

				<div v-if="gradebook.task" class="flex flex-wrap gap-2">
					<Badge v-if="taskModeBadge(gradebook.task)" variant="subtle">
						{{ taskModeBadge(gradebook.task) }}
					</Badge>
					<Badge variant="subtle">Students {{ gradebook.students.length }}</Badge>
					<Badge v-if="newEvidenceCount" variant="subtle" theme="orange">
						New evidence {{ newEvidenceCount }}
					</Badge>
					<Badge v-if="releasedCount" variant="subtle" theme="green">
						Released {{ releasedCount }}
					</Badge>
				</div>
			</div>
		</div>

		<div class="min-h-[420px] flex-1 bg-white p-6">
			<div
				v-if="gradebookLoading"
				class="flex h-full flex-col items-center justify-center gap-3 pt-20"
			>
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
				<p class="max-w-xs text-sm">Choose a task from the left panel to begin grading.</p>
			</div>

			<div
				v-else-if="!gradebook.students.length"
				class="flex h-full flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed border-border/60 bg-gray-50/30 p-12 text-center text-ink/60"
			>
				<p class="text-lg font-medium text-ink">No Students Assigned</p>
				<p class="max-w-xs text-sm">This task has no students in the roster.</p>
				<button
					type="button"
					class="if-button if-button--primary"
					:disabled="rosterSyncing"
					@click="syncRoster"
				>
					{{ rosterSyncing ? 'Syncing roster…' : 'Sync roster' }}
				</button>
			</div>

			<GradebookQuizManualReview
				v-else-if="showsQuizManualReview && taskName"
				:task-name="taskName"
			/>

			<div v-else class="grid gap-5 xl:grid-cols-[minmax(21rem,24rem)_minmax(0,1fr)]">
				<section class="rounded-2xl border border-border/70 bg-gray-50/40">
					<div class="border-b border-border/60 px-5 py-4">
						<div class="flex flex-wrap items-start justify-between gap-3">
							<div>
								<h3 class="text-sm font-semibold uppercase tracking-[0.16em] text-ink/45">
									Student Roster
								</h3>
								<p class="mt-1 text-sm text-ink/60">
									{{ gradebook.task?.title || 'Task' }}
								</p>
							</div>
							<div class="flex flex-col items-end gap-2">
								<div class="text-right text-xs text-ink/45">
									<p>{{ gradebook.students.length }} students</p>
									<p v-if="gradebook.task?.due_date">
										Due {{ formatDate(gradebook.task?.due_date) }}
									</p>
								</div>
								<div class="flex flex-wrap justify-end gap-2">
									<button
										type="button"
										class="if-button if-button--secondary"
										:disabled="publishBusy || !unreleasedOutcomeIds.length"
										data-select-unreleased
										@click="selectAllUnreleased"
									>
										Select unreleased
									</button>
									<button
										v-if="selectedBatchOutcomeIds.length"
										type="button"
										class="if-button if-button--secondary"
										:disabled="publishBusy"
										@click="clearBatchSelection"
									>
										Clear
									</button>
									<button
										type="button"
										class="if-button if-button--primary"
										:disabled="publishBusy || !selectedReleasableOutcomeIds.length"
										data-release-selected
										@click="releaseSelectedOutcomes"
									>
										Release selected
										<span v-if="selectedReleasableOutcomeIds.length">
											({{ selectedReleasableOutcomeIds.length }})
										</span>
									</button>
								</div>
							</div>
						</div>
					</div>

					<div class="max-h-[720px] space-y-2 overflow-y-auto p-3">
						<div
							v-for="student in gradebook.students"
							:key="student.task_student"
							class="flex items-start gap-3 rounded-2xl border border-border/70 bg-white px-4 py-4 transition hover:border-leaf/40 hover:bg-sky/10"
						>
							<div class="pt-1">
								<input
									:checked="isBatchSelected(student.task_student)"
									:data-batch-select-outcome="student.task_student"
									type="checkbox"
									class="h-4 w-4 rounded border-border text-canopy"
									@change="
										toggleBatchSelection(
											student.task_student,
											($event.target as HTMLInputElement).checked
										)
									"
								/>
							</div>
							<button
								type="button"
								class="w-full rounded-xl px-1 text-left transition"
								:data-gradebook-student="student.student"
								:class="selectedOutcomeId === student.task_student ? 'bg-sky/10' : ''"
								@click="openStudent(student)"
							>
								<div class="flex items-start gap-3">
									<img
										:src="student.student_image || DEFAULT_STUDENT_IMAGE"
										alt=""
										class="h-11 w-11 rounded-full border border-white bg-white object-cover shadow-sm"
										loading="lazy"
										@error="onImgError"
									/>
									<div class="min-w-0 flex-1">
										<div class="flex items-start justify-between gap-3">
											<div class="min-w-0">
												<p class="truncate text-sm font-semibold text-ink">
													{{ student.student_name }}
												</p>
												<p class="truncate text-xs text-ink/50">
													{{ student.student_id || student.student }}
												</p>
											</div>
											<FeatherIcon
												name="chevron-right"
												class="mt-0.5 h-4 w-4 shrink-0 text-ink/30"
											/>
										</div>

										<div class="mt-3 grid gap-1 text-sm text-ink/65">
											<p>Status: {{ student.status || '—' }}</p>
											<p v-if="student.procedural_status">
												Procedural: {{ student.procedural_status }}
											</p>
											<p>{{ studentResultSummary(student) }}</p>
										</div>

										<div class="mt-3 flex flex-wrap gap-2">
											<Badge v-if="student.has_new_submission" variant="subtle" theme="orange">
												New evidence
											</Badge>
											<Badge v-if="student.visible_to_student" variant="subtle" theme="green">
												Released
											</Badge>
											<Badge
												v-if="student.has_submission && !student.has_new_submission"
												variant="subtle"
											>
												Evidence linked
											</Badge>
										</div>
									</div>
								</div>
							</button>
						</div>
					</div>
				</section>

				<GradebookStudentDrawer
					:loading="drawerLoading"
					:drawer="drawer"
					:error-message="drawerErrorMessage"
					:marking-busy="markingBusy"
					:submission-seen-busy="submissionSeenBusy"
					:publish-busy="publishBusy"
					@close="closeDrawer"
					@switch-version="switchSubmissionVersion"
					@save-marking="saveDrawerMarking"
					@mark-submission-seen="markSubmissionSeen"
					@publish="publishOutcome"
					@unpublish="unpublishOutcome"
				/>
			</div>
		</div>
	</section>
</template>

<script setup lang="ts">
import { computed, nextTick, reactive, ref, watch } from 'vue';
import { Badge, FeatherIcon, Spinner, toast } from 'frappe-ui';

import { createGradebookService } from '@/lib/services/gradebook/gradebookService';
import type { Response as GetDrawerResponse } from '@/types/contracts/gradebook/get_drawer';
import type {
	Response as GetTaskGradebookResponse,
	TaskPayload,
	StudentRow,
} from '@/types/contracts/gradebook/get_task_gradebook';
import type { Request as UpdateTaskStudentRequest } from '@/types/contracts/gradebook/update_task_student';
import GradebookQuizManualReview from './GradebookQuizManualReview.vue';
import GradebookStudentDrawer from './GradebookStudentDrawer.vue';
import {
	DEFAULT_STUDENT_IMAGE,
	booleanNegativeLabel,
	booleanPositiveLabel,
	formatDate,
	formatPoints,
	isAssessedQuizTask,
	isCriteriaTask,
	isPointsTask,
	showMaxPointsPill,
	showsBooleanResult,
	taskModeBadge,
} from '../gradebookUtils';

interface TaskGradebookState {
	task: TaskPayload | null;
	students: StudentRow[];
}

const props = defineProps<{
	taskName: string | null;
	focusStudent?: string | null;
}>();

const emit = defineEmits<{
	(e: 'select-student', student: string | null): void;
}>();

const gradebookService = createGradebookService();
const rootElement = ref<HTMLElement | null>(null);
const gradebookLoading = ref(false);
const rosterSyncing = ref(false);
const drawerLoading = ref(false);
const drawerErrorMessage = ref<string | null>(null);
const drawer = ref<GetDrawerResponse | null>(null);
const selectedOutcomeId = ref<string | null>(null);
const selectedStudentId = ref<string | null>(null);
const gradebookLoadVersion = ref(0);
const drawerLoadVersion = ref(0);
const markingBusy = ref(false);
const submissionSeenBusy = ref(false);
const publishBusy = ref(false);
const selectedBatchOutcomeIds = ref<string[]>([]);

const gradebook = reactive<TaskGradebookState>({
	task: null,
	students: [],
});

const showsQuizManualReview = computed(() => isAssessedQuizTask(gradebook.task));
const newEvidenceCount = computed(
	() => gradebook.students.filter(student => student.has_new_submission).length
);
const releasedCount = computed(
	() => gradebook.students.filter(student => student.visible_to_student).length
);
const unreleasedOutcomeIds = computed(() =>
	gradebook.students
		.filter(student => !student.visible_to_student)
		.map(student => student.task_student)
);
const selectedReleasableOutcomeIds = computed(() => {
	const releasable = new Set(unreleasedOutcomeIds.value);
	return selectedBatchOutcomeIds.value.filter(outcomeId => releasable.has(outcomeId));
});

function showToast(title: string, appearance: 'danger' | 'success' | 'warning' = 'danger') {
	const toastApi = toast as unknown as
		| ((payload: { title: string; appearance?: string }) => void)
		| {
				error?: (message: string) => void;
				create?: (payload: { title: string; appearance?: string }) => void;
		  };
	if (typeof toastApi === 'function') {
		toastApi({ title, appearance });
		return;
	}
	if (appearance === 'danger' && toastApi && typeof toastApi.error === 'function') {
		toastApi.error(title);
		return;
	}
	if (toastApi && typeof toastApi.create === 'function') {
		toastApi.create({ title, appearance });
	}
}

function showDangerToast(title: string) {
	showToast(title, 'danger');
}

function showSuccessToast(title: string) {
	showToast(title, 'success');
}

function resetGradebook() {
	gradebook.task = null;
	gradebook.students = [];
	selectedBatchOutcomeIds.value = [];
	closeDrawer({ syncParent: true });
}

async function loadGradebook(taskName: string) {
	const version = gradebookLoadVersion.value + 1;
	gradebookLoadVersion.value = version;
	gradebookLoading.value = true;

	try {
		const payload: GetTaskGradebookResponse = await gradebookService.getTaskGradebook({
			task: taskName,
		});
		if (gradebookLoadVersion.value !== version) return;

		gradebook.task = payload.task;
		gradebook.students = payload.students || [];
		const visibleOutcomeIds = new Set(gradebook.students.map(student => student.task_student));
		selectedBatchOutcomeIds.value = selectedBatchOutcomeIds.value.filter(outcomeId =>
			visibleOutcomeIds.has(outcomeId)
		);

		if (selectedOutcomeId.value) {
			const stillVisible = gradebook.students.find(
				student => student.task_student === selectedOutcomeId.value
			);
			if (!stillVisible) {
				closeDrawer({ syncParent: true });
			}
		}

		await applyFocusedStudent();
	} catch (error) {
		console.error('Failed to load gradebook', error);
		if (gradebookLoadVersion.value === version) {
			showDangerToast('Could not load gradebook');
		}
	} finally {
		if (gradebookLoadVersion.value === version) {
			gradebookLoading.value = false;
		}
	}
}

async function syncRoster() {
	if (!props.taskName) {
		showToast('Select a task first.', 'warning');
		return;
	}

	rosterSyncing.value = true;
	try {
		const payload = await gradebookService.repairTaskRoster({ task: props.taskName });
		showSuccessToast(payload.message || 'Roster synced.');
		await loadGradebook(props.taskName);
	} catch (error) {
		console.error('Failed to sync task roster', error);
		showDangerToast('Could not sync the task roster');
	} finally {
		rosterSyncing.value = false;
	}
}

async function loadDrawer(
	outcomeId: string,
	options: { submissionId?: string | null; version?: number | null } = {}
) {
	const version = drawerLoadVersion.value + 1;
	drawerLoadVersion.value = version;
	drawerLoading.value = true;
	drawerErrorMessage.value = null;

	try {
		const payload = await gradebookService.getDrawer({
			outcome_id: outcomeId,
			submission_id: options.submissionId ?? null,
			version: options.version ?? null,
		});
		if (drawerLoadVersion.value !== version) return;
		drawer.value = payload;
		selectedOutcomeId.value = outcomeId;
		await scrollToSelectedStudent();
	} catch (error) {
		console.error('Failed to load drawer', error);
		if (drawerLoadVersion.value === version) {
			drawer.value = null;
			drawerErrorMessage.value = 'Could not load grading details for this student.';
		}
	} finally {
		if (drawerLoadVersion.value === version) {
			drawerLoading.value = false;
		}
	}
}

async function openStudent(student: StudentRow) {
	selectedOutcomeId.value = student.task_student;
	selectedStudentId.value = student.student;
	emit('select-student', student.student);
	await loadDrawer(student.task_student);
}

function closeDrawer(options: { syncParent?: boolean } = {}) {
	selectedOutcomeId.value = null;
	selectedStudentId.value = null;
	drawer.value = null;
	drawerErrorMessage.value = null;
	if (options.syncParent !== false) {
		emit('select-student', null);
	}
}

async function applyFocusedStudent() {
	if (!props.focusStudent) {
		if (selectedStudentId.value) {
			closeDrawer({ syncParent: false });
		}
		return;
	}

	const match = gradebook.students.find(student => student.student === props.focusStudent);
	if (!match) {
		await scrollToSelectedStudent(props.focusStudent);
		return;
	}

	if (selectedOutcomeId.value === match.task_student && drawer.value) {
		await scrollToSelectedStudent(match.student);
		return;
	}

	selectedStudentId.value = match.student;
	await loadDrawer(match.task_student);
}

async function scrollToSelectedStudent(targetStudent = selectedStudentId.value) {
	if (!targetStudent || !rootElement.value) return;
	await nextTick();
	const target = rootElement.value.querySelector<HTMLElement>(
		`[data-gradebook-student="${targetStudent}"]`
	);
	if (!target) return;
	target.scrollIntoView({ block: 'center', behavior: 'smooth' });
}

async function refreshCurrentSelection(
	options: { submissionId?: string | null; version?: number | null } = {}
) {
	const currentOutcomeId = selectedOutcomeId.value;
	if (!props.taskName || !currentOutcomeId) return;
	await loadGradebook(props.taskName);
	const nextOutcomeId = selectedOutcomeId.value || currentOutcomeId;
	if (!nextOutcomeId) return;
	await loadDrawer(nextOutcomeId, options);
}

async function saveDrawerMarking(updates: UpdateTaskStudentRequest['updates']) {
	if (!selectedOutcomeId.value) return;
	markingBusy.value = true;
	try {
		await gradebookService.updateTaskStudent({
			task_student: selectedOutcomeId.value,
			updates,
		});
		showSuccessToast('Marking saved.');
		await refreshCurrentSelection();
	} catch (error) {
		console.error('Failed to save marking', error);
		showDangerToast('Could not save marking changes');
	} finally {
		markingBusy.value = false;
	}
}

async function switchSubmissionVersion(payload: {
	submissionId?: string | null;
	version?: number | null;
}) {
	if (!selectedOutcomeId.value) return;
	await loadDrawer(selectedOutcomeId.value, {
		submissionId: payload.submissionId ?? null,
		version: payload.version ?? null,
	});
}

async function markSubmissionSeen() {
	if (!selectedOutcomeId.value) return;
	submissionSeenBusy.value = true;
	try {
		await gradebookService.markNewSubmissionSeen({ outcome: selectedOutcomeId.value });
		showSuccessToast('New evidence badge cleared.');
		await refreshCurrentSelection();
	} catch (error) {
		console.error('Failed to mark new submission seen', error);
		showDangerToast('Could not update new evidence state');
	} finally {
		submissionSeenBusy.value = false;
	}
}

async function publishOutcome() {
	if (!selectedOutcomeId.value) return;
	publishBusy.value = true;
	try {
		await gradebookService.publishOutcomes({ outcome_ids: [selectedOutcomeId.value] });
		showSuccessToast('Outcome released.');
		await refreshCurrentSelection();
	} catch (error) {
		console.error('Failed to publish outcome', error);
		showDangerToast('Could not release this outcome');
	} finally {
		publishBusy.value = false;
	}
}

async function unpublishOutcome() {
	if (!selectedOutcomeId.value) return;
	publishBusy.value = true;
	try {
		await gradebookService.unpublishOutcomes({ outcome_ids: [selectedOutcomeId.value] });
		showSuccessToast('Outcome unreleased.');
		await refreshCurrentSelection();
	} catch (error) {
		console.error('Failed to unpublish outcome', error);
		showDangerToast('Could not unrelease this outcome');
	} finally {
		publishBusy.value = false;
	}
}

function isBatchSelected(outcomeId: string) {
	return selectedBatchOutcomeIds.value.includes(outcomeId);
}

function toggleBatchSelection(outcomeId: string, checked: boolean) {
	if (!outcomeId) return;
	const next = new Set(selectedBatchOutcomeIds.value);
	if (checked) {
		next.add(outcomeId);
	} else {
		next.delete(outcomeId);
	}
	selectedBatchOutcomeIds.value = Array.from(next);
}

function clearBatchSelection() {
	selectedBatchOutcomeIds.value = [];
}

function selectAllUnreleased() {
	selectedBatchOutcomeIds.value = [...unreleasedOutcomeIds.value];
}

async function releaseSelectedOutcomes() {
	const outcomeIds = selectedReleasableOutcomeIds.value;
	if (!outcomeIds.length) {
		showToast('Select at least one unreleased student.', 'warning');
		return;
	}

	publishBusy.value = true;
	try {
		await gradebookService.publishOutcomes({ outcome_ids: outcomeIds });
		showSuccessToast(
			outcomeIds.length === 1
				? 'Selected outcome released.'
				: `Released ${outcomeIds.length} outcomes.`
		);
		clearBatchSelection();
		if (!props.taskName) return;
		await loadGradebook(props.taskName);
		if (selectedOutcomeId.value && outcomeIds.includes(selectedOutcomeId.value)) {
			await loadDrawer(selectedOutcomeId.value);
		}
	} catch (error) {
		console.error('Failed to release selected outcomes', error);
		showDangerToast('Could not release the selected outcomes');
	} finally {
		publishBusy.value = false;
	}
}

function studentResultSummary(student: StudentRow) {
	if (isPointsTask(gradebook.task)) {
		return `Score ${formatPoints(student.mark_awarded)}`;
	}
	if (showsBooleanResult(gradebook.task)) {
		return student.complete
			? booleanPositiveLabel(gradebook.task)
			: booleanNegativeLabel(gradebook.task);
	}
	if (isCriteriaTask(gradebook.task)) {
		if (gradebook.task?.rubric_scoring_strategy === 'Separate Criteria') {
			return `${student.criteria_scores.length} criteria tracked`;
		}
		return `Total ${formatPoints(student.mark_awarded)}`;
	}
	if (showMaxPointsPill(gradebook.task)) {
		return `Score ${formatPoints(student.mark_awarded)}`;
	}
	return student.feedback ? 'Comment saved' : 'No result yet';
}

function onImgError(event: Event) {
	const element = event.target as HTMLImageElement;
	element.onerror = null;
	element.src = DEFAULT_STUDENT_IMAGE;
}

watch(
	() => props.taskName,
	taskName => {
		resetGradebook();
		if (taskName) {
			void loadGradebook(taskName);
		}
	},
	{ immediate: true }
);

watch(
	() => props.focusStudent,
	() => {
		void applyFocusedStudent();
	}
);
</script>
