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
			</div>

			<GradebookQuizManualReview
				v-else-if="showsQuizManualReview && taskName"
				:task-name="taskName"
			/>

			<div v-else class="grid gap-5 xl:grid-cols-[minmax(17.5rem,19rem)_minmax(0,1fr)]">
				<section class="rounded-2xl border border-border/70 bg-gray-50/40">
					<div class="border-b border-border/60 px-4 py-4">
						<div class="flex flex-wrap items-start justify-between gap-3">
							<div>
								<h3 class="text-sm font-semibold uppercase tracking-[0.16em] text-ink/45">
									{{ hasEvidenceInbox ? 'Evidence Inbox' : 'Student Roster' }}
								</h3>
								<p class="mt-1 text-sm text-ink/60">
									{{ evidenceIntroLabel }}
								</p>
							</div>
							<div class="flex flex-col items-end gap-2">
								<div class="text-right text-xs text-ink/45">
									<p>{{ visibleStudents.length }} shown</p>
									<p v-if="hasEvidenceInbox">{{ gradebook.students.length }} total students</p>
									<p v-if="gradebook.task?.due_date">
										Due {{ formatDate(gradebook.task?.due_date) }}
									</p>
								</div>
								<div class="flex flex-wrap justify-end gap-2">
									<button
										v-if="completionBatchSupported"
										type="button"
										class="if-button if-button--secondary"
										:disabled="batchCompletionBusy || !batchCompletionEligibleStudents.length"
										data-mark-shown-complete
										@click="openBatchCompletionConfirm"
									>
										{{ batchCompletionButtonLabel }}
									</button>
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
						<div
							v-if="batchCompletionConfirmOpen"
							class="mt-4 rounded-xl border border-sand/70 bg-sand/10 px-4 py-3"
						>
							<div class="flex flex-wrap items-center justify-between gap-3">
								<div class="space-y-1">
									<p class="text-sm font-semibold text-ink">
										Mark {{ batchCompletionEligibleStudents.length }} shown students complete?
									</p>
									<p class="text-xs text-ink/60">
										You can still open individual students and mark exceptions incomplete. Released
										outcomes will not be changed.
									</p>
								</div>
								<div class="flex items-center gap-2">
									<button
										type="button"
										class="if-button if-button--quiet"
										:disabled="batchCompletionBusy"
										@click="closeBatchCompletionConfirm"
									>
										Cancel
									</button>
									<button
										type="button"
										class="if-button if-button--primary"
										:disabled="batchCompletionBusy || !batchCompletionEligibleStudents.length"
										data-confirm-mark-shown-complete
										@click="markShownComplete"
									>
										{{ batchCompletionBusy ? 'Marking...' : 'Confirm complete' }}
									</button>
								</div>
							</div>
						</div>
					</div>

					<div v-if="hasEvidenceInbox" class="border-b border-border/60 bg-white/90 px-4 py-3">
						<div class="flex flex-wrap items-center gap-2">
							<button
								v-for="option in evidenceFilterOptions"
								:key="option.id"
								type="button"
								class="rounded-full border px-3 py-1.5 text-sm font-medium transition"
								:class="
									activeEvidenceFilter === option.id
										? 'border-leaf bg-sky/20 text-ink'
										: 'border-border/70 bg-white text-ink/65 hover:border-leaf/40 hover:text-ink'
								"
								:data-evidence-filter="option.id"
								@click="setEvidenceFilter(option.id)"
							>
								{{ option.label }} ({{ option.count }})
							</button>
						</div>
					</div>

					<div class="max-h-[720px] space-y-2 overflow-y-auto p-2.5">
						<div
							v-if="!visibleStudents.length"
							class="rounded-2xl border border-dashed border-border/70 bg-gray-50/40 p-6 text-center text-sm text-ink/60"
						>
							No students match this evidence filter.
						</div>
						<div
							v-for="student in visibleStudents"
							:key="student.task_student"
							class="flex items-start gap-3 rounded-2xl border border-border/70 bg-white px-3.5 py-4 transition hover:border-leaf/40 hover:bg-sky/10"
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
											<p v-if="student.submission_status">
												Submission: {{ student.submission_status }}
											</p>
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
					:feedback-busy="feedbackBusy"
					:comment-bank-busy="commentBankBusy"
					:publication-busy="publicationBusy"
					:thread-busy="threadBusy"
					:submission-seen-busy="submissionSeenBusy"
					:publish-busy="publishBusy"
					:export-busy="exportBusy"
					:moderation-busy="moderationBusy"
					:show-sequence-controls="Boolean(drawer && visibleStudents.length > 1)"
					:can-go-previous="canGoPrevious"
					:can-go-next="canGoNext"
					:sequence-label="sequenceLabel"
					@close="closeDrawer"
					@switch-version="switchSubmissionVersion"
					@save-marking="saveDrawerMarking"
					@save-feedback-draft="saveFeedbackDraft"
					@save-comment-bank-entry="saveFeedbackCommentBankEntry"
					@save-feedback-publication="saveFeedbackPublication"
					@save-feedback-thread-reply="saveFeedbackThreadReply"
					@save-feedback-thread-state="saveFeedbackThreadState"
					@moderator-action="runModeratorAction"
					@mark-submission-seen="markSubmissionSeen"
					@publish="publishOutcome"
					@unpublish="unpublishOutcome"
					@export-feedback-pdf="exportFeedbackPdf"
					@go-previous="openRelativeStudent(-1)"
					@go-next="openRelativeStudent(1)"
				/>
			</div>
		</div>
	</section>
</template>

<script setup lang="ts">
import { computed, nextTick, reactive, ref, watch } from 'vue';
import { Badge, FeatherIcon, Spinner, toast } from 'frappe-ui';

import { createGradebookService } from '@/lib/services/gradebook/gradebookService';
import type { CommentBankScopeMode } from '@/types/contracts/gradebook/comment_bank';
import type { Response as BatchMarkCompletionResponse } from '@/types/contracts/gradebook/batch_mark_completion';
import type { FeedbackWorkspaceItem } from '@/types/contracts/gradebook/feedback_workspace';
import type { Response as GetDrawerResponse } from '@/types/contracts/gradebook/get_drawer';
import type { Request as ModeratorActionRequest } from '@/types/contracts/gradebook/moderator_action';
import type { Request as SubmitContributionRequest } from '@/types/contracts/gradebook/submit_contribution';
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
	isCollectWorkTask,
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

type EvidenceFilter = 'all' | 'new_evidence' | 'missing' | 'submitted' | 'late';

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
const drawerLoading = ref(false);
const drawerErrorMessage = ref<string | null>(null);
const drawer = ref<GetDrawerResponse | null>(null);
const selectedOutcomeId = ref<string | null>(null);
const selectedStudentId = ref<string | null>(null);
const pendingDrawerOutcomeId = ref<string | null>(null);
const gradebookLoadVersion = ref(0);
const drawerLoadVersion = ref(0);
const markingBusy = ref(false);
const feedbackBusy = ref(false);
const commentBankBusy = ref(false);
const publicationBusy = ref(false);
const threadBusy = ref(false);
const submissionSeenBusy = ref(false);
const publishBusy = ref(false);
const batchCompletionBusy = ref(false);
const batchCompletionConfirmOpen = ref(false);
const exportBusy = ref(false);
const moderationBusy = ref(false);
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
const hasEvidenceInbox = computed(() => isCollectWorkTask(gradebook.task));
const evidenceCounts = computed(() => ({
	all: gradebook.students.length,
	new_evidence: gradebook.students.filter(student => student.has_new_submission).length,
	missing: gradebook.students.filter(student => isMissingEvidence(student)).length,
	submitted: gradebook.students.filter(student => isSubmittedEvidence(student)).length,
	late: gradebook.students.filter(student => isLateEvidence(student)).length,
}));
const activeEvidenceFilter = ref<EvidenceFilter>('all');
const evidenceFilterOptions = computed(() => [
	{ id: 'all' as EvidenceFilter, label: 'All', count: evidenceCounts.value.all },
	{
		id: 'new_evidence' as EvidenceFilter,
		label: 'New Evidence',
		count: evidenceCounts.value.new_evidence,
	},
	{ id: 'missing' as EvidenceFilter, label: 'Missing', count: evidenceCounts.value.missing },
	{
		id: 'submitted' as EvidenceFilter,
		label: 'Submitted',
		count: evidenceCounts.value.submitted,
	},
	{ id: 'late' as EvidenceFilter, label: 'Late', count: evidenceCounts.value.late },
]);
const visibleStudents = computed(() => {
	const rows = [...gradebook.students];
	if (!hasEvidenceInbox.value) {
		return rows;
	}

	const filtered = rows.filter(student =>
		studentMatchesEvidenceFilter(student, activeEvidenceFilter.value)
	);
	return filtered.sort((left, right) => {
		const leftRank = evidencePriority(left);
		const rightRank = evidencePriority(right);
		if (leftRank !== rightRank) return leftRank - rightRank;
		return String(left.student_name || left.student).localeCompare(
			String(right.student_name || right.student)
		);
	});
});
const completionBatchSupported = computed(() => {
	const task = gradebook.task;
	if (!task) return false;
	return (
		task.delivery_type === 'Assign Only' ||
		(task.delivery_type === 'Assess' && task.grading_mode === 'Completion')
	);
});
const batchCompletionEligibleStudents = computed(() => {
	if (!completionBatchSupported.value) return [];
	return visibleStudents.value.filter(
		student => !student.complete && !student.visible_to_student && student.task_student
	);
});
const batchCompletionReleasedBlockedCount = computed(() => {
	if (!completionBatchSupported.value) return 0;
	return visibleStudents.value.filter(student => !student.complete && student.visible_to_student)
		.length;
});
const batchCompletionButtonLabel = computed(() => {
	if (batchCompletionBusy.value) return 'Marking...';
	if (batchCompletionEligibleStudents.value.length) {
		return `Mark shown complete (${batchCompletionEligibleStudents.value.length})`;
	}
	if (batchCompletionReleasedBlockedCount.value) return 'Unrelease to mark complete';
	return 'All shown complete';
});
const unreleasedOutcomeIds = computed(() =>
	gradebook.students
		.filter(student => !student.visible_to_student)
		.map(student => student.task_student)
);
const selectedReleasableOutcomeIds = computed(() => {
	const releasable = new Set(unreleasedOutcomeIds.value);
	return selectedBatchOutcomeIds.value.filter(outcomeId => releasable.has(outcomeId));
});
const selectedVisibleIndex = computed(() =>
	visibleStudents.value.findIndex(student => student.task_student === selectedOutcomeId.value)
);
const canGoPrevious = computed(() => selectedVisibleIndex.value > 0);
const canGoNext = computed(
	() =>
		selectedVisibleIndex.value >= 0 &&
		selectedVisibleIndex.value < visibleStudents.value.length - 1
);
const evidenceIntroLabel = computed(() => {
	if (!gradebook.task?.title) return 'Task';
	if (!hasEvidenceInbox.value) return gradebook.task.title;
	return `${gradebook.task.title} · new evidence first, then late, missing, and submitted work.`;
});
const sequenceLabel = computed(() => {
	if (!drawer.value || selectedVisibleIndex.value < 0 || visibleStudents.value.length < 2) {
		return null;
	}
	if (hasEvidenceInbox.value) {
		return `Inbox ${selectedVisibleIndex.value + 1} of ${visibleStudents.value.length}`;
	}
	return `Student ${selectedVisibleIndex.value + 1} of ${visibleStudents.value.length}`;
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
	activeEvidenceFilter.value = 'all';
	batchCompletionConfirmOpen.value = false;
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
		syncEvidenceFilter();
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

async function loadDrawer(
	outcomeId: string,
	options: { submissionId?: string | null; version?: number | null } = {}
) {
	const version = drawerLoadVersion.value + 1;
	drawerLoadVersion.value = version;
	pendingDrawerOutcomeId.value = outcomeId;
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
			if (pendingDrawerOutcomeId.value === outcomeId) {
				pendingDrawerOutcomeId.value = null;
			}
		}
	}
}

async function openStudent(student: StudentRow) {
	selectedOutcomeId.value = student.task_student;
	selectedStudentId.value = student.student;
	pendingDrawerOutcomeId.value = student.task_student;
	emit('select-student', student.student);
	await loadDrawer(student.task_student);
}

async function openRelativeStudent(offset: number) {
	const currentIndex = selectedVisibleIndex.value;
	if (currentIndex < 0) return;
	const target = visibleStudents.value[currentIndex + offset];
	if (!target) return;
	await openStudent(target);
}

function closeDrawer(options: { syncParent?: boolean } = {}) {
	selectedOutcomeId.value = null;
	selectedStudentId.value = null;
	pendingDrawerOutcomeId.value = null;
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

	if (selectedOutcomeId.value === match.task_student) {
		selectedStudentId.value = match.student;
		if (drawer.value && pendingDrawerOutcomeId.value !== match.task_student) {
			await scrollToSelectedStudent(match.student);
			return;
		}
		if (drawerLoading.value || pendingDrawerOutcomeId.value === match.task_student) {
			return;
		}
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
	if (typeof target.scrollIntoView === 'function') {
		target.scrollIntoView({ block: 'center', behavior: 'smooth' });
	}
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

function currentDrawerSelection() {
	return {
		submissionId: drawer.value?.selected_submission?.submission_id ?? null,
		version: drawer.value?.selected_submission?.version ?? null,
	};
}

type StudentRowPatch = {
	status?: string | null;
	procedural_status?: string | null;
	mark_awarded?: number | null;
	feedback?: string | null;
	complete?: boolean | 0 | 1 | null;
	visible_to_student?: boolean | 0 | 1 | null;
	visible_to_guardian?: boolean | 0 | 1 | null;
};

function patchStudentRow(outcomeId: string, patch: StudentRowPatch) {
	const row = gradebook.students.find(student => student.task_student === outcomeId);
	if (!row) return;
	if (Object.prototype.hasOwnProperty.call(patch, 'status')) {
		row.status = patch.status ?? null;
	}
	if (Object.prototype.hasOwnProperty.call(patch, 'procedural_status')) {
		row.procedural_status = patch.procedural_status ?? null;
	}
	if (Object.prototype.hasOwnProperty.call(patch, 'mark_awarded')) {
		row.mark_awarded = patch.mark_awarded ?? null;
	}
	if (Object.prototype.hasOwnProperty.call(patch, 'feedback')) {
		row.feedback = patch.feedback ?? null;
	}
	if (Object.prototype.hasOwnProperty.call(patch, 'complete')) {
		row.complete = patch.complete ? 1 : 0;
	}
	if (Object.prototype.hasOwnProperty.call(patch, 'visible_to_student')) {
		row.visible_to_student = patch.visible_to_student ? 1 : 0;
	}
	if (Object.prototype.hasOwnProperty.call(patch, 'visible_to_guardian')) {
		row.visible_to_guardian = patch.visible_to_guardian ? 1 : 0;
	}
}

function applyOutcomeUpdateToStudentRow(
	outcomeId: string,
	outcomeUpdate: Record<string, unknown> | null | undefined
) {
	if (!outcomeUpdate) return;
	const patch: StudentRowPatch = {};
	if (typeof outcomeUpdate.grading_status === 'string') {
		patch.status = outcomeUpdate.grading_status;
	}
	if (
		typeof outcomeUpdate.procedural_status === 'string' ||
		outcomeUpdate.procedural_status === null
	) {
		patch.procedural_status =
			(outcomeUpdate.procedural_status as string | null | undefined) ?? null;
	}
	if (typeof outcomeUpdate.official_score === 'number' || outcomeUpdate.official_score === null) {
		patch.mark_awarded = (outcomeUpdate.official_score as number | null | undefined) ?? null;
	}
	if (
		typeof outcomeUpdate.official_feedback === 'string' ||
		outcomeUpdate.official_feedback === null
	) {
		patch.feedback = (outcomeUpdate.official_feedback as string | null | undefined) ?? null;
	}
	if (
		typeof outcomeUpdate.is_complete === 'number' ||
		typeof outcomeUpdate.is_complete === 'boolean'
	) {
		patch.complete = Boolean(outcomeUpdate.is_complete);
	}
	if (
		typeof outcomeUpdate.is_published === 'number' ||
		typeof outcomeUpdate.is_published === 'boolean'
	) {
		const isPublished = Boolean(outcomeUpdate.is_published);
		patch.visible_to_student = isPublished;
		patch.visible_to_guardian = isPublished;
	}
	patchStudentRow(outcomeId, patch);
}

function hasOwnUpdateKey<T extends object, K extends keyof T>(value: T, key: K): boolean {
	return Object.prototype.hasOwnProperty.call(value, key);
}

function isAssessedBooleanDelivery(drawerPayload: GetDrawerResponse): boolean {
	return (
		drawerPayload.delivery.delivery_mode === 'Assess' &&
		(drawerPayload.delivery.grading_mode === 'Binary' ||
			drawerPayload.delivery.grading_mode === 'Completion')
	);
}

function buildContributionRequest(
	drawerPayload: GetDrawerResponse,
	updates: UpdateTaskStudentRequest['updates'],
	options: { action?: ModeratorActionRequest['action'] } = {}
): SubmitContributionRequest | ModeratorActionRequest | null {
	const request: Partial<SubmitContributionRequest & ModeratorActionRequest> = {
		task_outcome: drawerPayload.outcome.outcome_id,
	};
	const latestSubmissionId = drawerPayload.latest_submission?.submission_id || null;
	if (latestSubmissionId) {
		request.task_submission = latestSubmissionId;
	}
	if (options.action) {
		request.action = options.action;
	}

	let hasContributionFields = false;
	if (hasOwnUpdateKey(updates, 'mark_awarded')) {
		request.score = updates.mark_awarded ?? null;
		hasContributionFields = true;
	}
	if (hasOwnUpdateKey(updates, 'feedback')) {
		request.feedback = updates.feedback ?? null;
		hasContributionFields = true;
	}
	if (updates.criteria_scores?.length) {
		request.rubric_scores = updates.criteria_scores;
		hasContributionFields = true;
	}
	if (hasOwnUpdateKey(updates, 'complete') && isAssessedBooleanDelivery(drawerPayload)) {
		const isComplete = Boolean(updates.complete);
		request.judgment_code =
			drawerPayload.delivery.grading_mode === 'Completion'
				? isComplete
					? 'complete'
					: 'incomplete'
				: isComplete
					? 'yes'
					: 'no';
		hasContributionFields = true;
	}

	if (!hasContributionFields && !options.action) {
		return null;
	}

	return request as SubmitContributionRequest | ModeratorActionRequest;
}

function buildDirectOutcomeUpdates(
	drawerPayload: GetDrawerResponse,
	updates: UpdateTaskStudentRequest['updates']
): UpdateTaskStudentRequest['updates'] {
	const directUpdates: UpdateTaskStudentRequest['updates'] = {};
	const currentStatus = drawerPayload.outcome.grading_status || 'Not Started';
	if (
		hasOwnUpdateKey(updates, 'status') &&
		drawerPayload.delivery.delivery_mode === 'Assess' &&
		updates.status !== currentStatus
	) {
		directUpdates.status = updates.status ?? null;
	}
	if (
		hasOwnUpdateKey(updates, 'complete') &&
		drawerPayload.delivery.delivery_mode === 'Assign Only' &&
		Boolean(updates.complete) !== Boolean(drawerPayload.outcome.is_complete)
	) {
		directUpdates.complete = updates.complete ?? null;
	}
	return directUpdates;
}

async function saveDrawerMarking(updates: UpdateTaskStudentRequest['updates']) {
	if (!selectedOutcomeId.value || !drawer.value) return;
	markingBusy.value = true;
	try {
		const contributionRequest = buildContributionRequest(drawer.value, updates);
		const directUpdates = buildDirectOutcomeUpdates(drawer.value, updates);
		let contributionResponse: Awaited<
			ReturnType<typeof gradebookService.submitContribution>
		> | null = null;
		if (contributionRequest) {
			contributionResponse = await gradebookService.submitContribution(
				contributionRequest as SubmitContributionRequest
			);
			applyOutcomeUpdateToStudentRow(selectedOutcomeId.value, contributionResponse.outcome_update);
		}
		if (Object.keys(directUpdates).length) {
			await gradebookService.updateTaskStudent({
				task_student: selectedOutcomeId.value,
				updates: directUpdates,
			});
			patchStudentRow(selectedOutcomeId.value, {
				status: directUpdates.status ?? undefined,
				complete:
					typeof directUpdates.complete === 'boolean'
						? directUpdates.complete
						: directUpdates.complete == null
							? undefined
							: Boolean(directUpdates.complete),
			});
		}
		if (hasOwnUpdateKey(updates, 'mark_awarded') || hasOwnUpdateKey(updates, 'feedback')) {
			patchStudentRow(selectedOutcomeId.value, {
				mark_awarded: hasOwnUpdateKey(updates, 'mark_awarded')
					? (updates.mark_awarded ?? null)
					: undefined,
				feedback: hasOwnUpdateKey(updates, 'feedback') ? (updates.feedback ?? null) : undefined,
			});
		}
		showSuccessToast('Marking saved.');
		await loadDrawer(selectedOutcomeId.value, currentDrawerSelection());
	} catch (error) {
		console.error('Failed to save marking', error);
		showDangerToast('Could not save marking changes');
	} finally {
		markingBusy.value = false;
	}
}

async function saveFeedbackDraft(payload: {
	outcome_id: string;
	submission_id: string;
	summary: {
		overall: string;
		strengths: string;
		improvements: string;
		next_steps: string;
	};
	priorities: Array<{
		id?: string | null;
		title: string;
		detail?: string | null;
		feedback_item_id?: string | null;
		assessment_criteria?: string | null;
	}>;
	items: FeedbackWorkspaceItem[];
}) {
	feedbackBusy.value = true;
	try {
		await gradebookService.saveFeedbackDraft(payload);
		showSuccessToast('Feedback draft saved.');
		await refreshCurrentSelection(currentDrawerSelection());
	} catch (error) {
		console.error('Failed to save feedback draft', error);
		showDangerToast('Could not save feedback draft');
	} finally {
		feedbackBusy.value = false;
	}
}

function upsertDrawerThread(thread: GetDrawerResponse['feedback_threads'][number]) {
	if (!drawer.value) return;
	const nextThreads = (drawer.value.feedback_threads || []).filter(
		row => row.thread_id !== thread.thread_id
	);
	nextThreads.push(thread);
	drawer.value.feedback_threads = nextThreads.sort((left, right) =>
		String(left.modified || '').localeCompare(String(right.modified || ''))
	);
}

async function saveFeedbackThreadReply(payload: {
	outcome_id: string;
	thread_id: string;
	body: string;
	thread_status?: 'open' | 'resolved' | null;
}) {
	threadBusy.value = true;
	try {
		const response = await gradebookService.saveFeedbackThreadReply(payload);
		upsertDrawerThread(response.thread);
		showSuccessToast('Reply saved.');
	} catch (error) {
		console.error('Failed to save feedback thread reply', error);
		showDangerToast('Could not save reply');
	} finally {
		threadBusy.value = false;
	}
}

async function saveFeedbackThreadState(payload: {
	outcome_id: string;
	thread_id: string;
	thread_status: 'open' | 'resolved';
}) {
	threadBusy.value = true;
	try {
		const response = await gradebookService.saveFeedbackThreadState(payload);
		upsertDrawerThread(response.thread);
		showSuccessToast(
			payload.thread_status === 'resolved' ? 'Thread resolved.' : 'Thread reopened.'
		);
	} catch (error) {
		console.error('Failed to update feedback thread state', error);
		showDangerToast('Could not update thread state');
	} finally {
		threadBusy.value = false;
	}
}

async function saveFeedbackCommentBankEntry(payload: {
	outcome_id: string;
	body: string;
	feedback_intent: FeedbackWorkspaceItem['intent'];
	assessment_criteria?: string | null;
	scope_mode: CommentBankScopeMode;
}) {
	commentBankBusy.value = true;
	try {
		await gradebookService.saveFeedbackCommentBankEntry(payload);
		showSuccessToast('Reusable comment saved.');
		await refreshCurrentSelection(currentDrawerSelection());
	} catch (error) {
		console.error('Failed to save reusable comment', error);
		showDangerToast('Could not save this reusable comment');
	} finally {
		commentBankBusy.value = false;
	}
}

async function saveFeedbackPublication(payload: {
	outcome_id: string;
	submission_id: string;
	feedback_visibility: 'hidden' | 'student' | 'student_and_guardian';
	grade_visibility: 'hidden' | 'student' | 'student_and_guardian';
}) {
	publicationBusy.value = true;
	try {
		await gradebookService.saveFeedbackPublication(payload);
		showSuccessToast('Publication state saved.');
		await refreshCurrentSelection(currentDrawerSelection());
	} catch (error) {
		console.error('Failed to save feedback publication state', error);
		showDangerToast('Could not save publication state');
	} finally {
		publicationBusy.value = false;
	}
}

async function runModeratorAction(payload: {
	action: ModeratorActionRequest['action'];
	updates: UpdateTaskStudentRequest['updates'];
}) {
	if (!selectedOutcomeId.value || !drawer.value) return;
	const request = buildContributionRequest(drawer.value, payload.updates, {
		action: payload.action,
	}) as ModeratorActionRequest | null;
	if (!request) return;

	moderationBusy.value = true;
	try {
		const response = await gradebookService.moderatorAction(request);
		applyOutcomeUpdateToStudentRow(selectedOutcomeId.value, response.outcome_update);
		if (
			hasOwnUpdateKey(payload.updates, 'mark_awarded') ||
			hasOwnUpdateKey(payload.updates, 'feedback')
		) {
			patchStudentRow(selectedOutcomeId.value, {
				mark_awarded: hasOwnUpdateKey(payload.updates, 'mark_awarded')
					? (payload.updates.mark_awarded ?? null)
					: undefined,
				feedback: hasOwnUpdateKey(payload.updates, 'feedback')
					? (payload.updates.feedback ?? null)
					: undefined,
			});
		}
		const successMessage =
			payload.action === 'Return to Grader'
				? 'Outcome returned to grader.'
				: payload.action === 'Adjust'
					? 'Moderation adjustment applied.'
					: 'Outcome approved by moderator.';
		showSuccessToast(successMessage);
		await loadDrawer(selectedOutcomeId.value, currentDrawerSelection());
	} catch (error) {
		console.error('Failed to apply moderation action', error);
		showDangerToast('Could not apply moderation action');
	} finally {
		moderationBusy.value = false;
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

async function exportFeedbackPdf() {
	if (!selectedOutcomeId.value) return;
	exportBusy.value = true;
	try {
		const currentArtifactUrl =
			drawer.value?.feedback_artifact?.open_url || drawer.value?.feedback_artifact?.preview_url;
		if (currentArtifactUrl) {
			window.open(currentArtifactUrl, '_blank', 'noopener,noreferrer');
			showSuccessToast('Opened the latest feedback PDF.');
			return;
		}
		const response = await gradebookService.exportFeedbackPdf({
			outcome_id: selectedOutcomeId.value,
			submission_id: drawer.value?.selected_submission?.submission_id || undefined,
		});
		const targetUrl = response.artifact?.open_url || response.artifact?.preview_url;
		if (!targetUrl) {
			throw new Error('Missing feedback artifact URL');
		}
		if (drawer.value) {
			drawer.value.feedback_artifact = response.artifact;
		}
		window.open(targetUrl, '_blank', 'noopener,noreferrer');
		showSuccessToast('Feedback PDF prepared.');
	} catch (error) {
		console.error('Failed to export feedback PDF', error);
		showDangerToast('Could not prepare the feedback PDF');
	} finally {
		exportBusy.value = false;
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

function openBatchCompletionConfirm() {
	if (!batchCompletionEligibleStudents.value.length) {
		showToast('No shown incomplete students can be marked complete.', 'warning');
		return;
	}
	batchCompletionConfirmOpen.value = true;
}

function closeBatchCompletionConfirm() {
	batchCompletionConfirmOpen.value = false;
}

function batchCompletionMessage(response: BatchMarkCompletionResponse) {
	const parts = [`Marked ${response.updated_count} complete.`];
	if (response.already_complete_count) {
		parts.push(`${response.already_complete_count} already complete.`);
	}
	if (response.skipped_published_count) {
		parts.push(`${response.skipped_published_count} released unchanged.`);
	}
	return parts.join(' ');
}

async function markShownComplete() {
	const taskName = gradebook.task?.name;
	const outcomeIds = batchCompletionEligibleStudents.value.map(student => student.task_student);
	if (!taskName || !outcomeIds.length) {
		showToast('No shown incomplete students can be marked complete.', 'warning');
		return;
	}

	batchCompletionBusy.value = true;
	try {
		const response = await gradebookService.batchMarkCompletion({
			task_delivery: taskName,
			target_complete: true,
			outcome_ids: outcomeIds,
		});
		const updatedIds = new Set<string>();
		for (const row of response.updated || []) {
			if (!row.outcome) continue;
			updatedIds.add(row.outcome);
			const patch: StudentRowPatch = { complete: true };
			if (Object.prototype.hasOwnProperty.call(row, 'grading_status')) {
				patch.status = row.grading_status ?? null;
			}
			patchStudentRow(row.outcome, patch);
		}
		batchCompletionConfirmOpen.value = false;
		showToast(
			batchCompletionMessage(response),
			response.skipped_published_count ? 'warning' : 'success'
		);
		if (selectedOutcomeId.value && updatedIds.has(selectedOutcomeId.value)) {
			await loadDrawer(selectedOutcomeId.value, currentDrawerSelection());
		}
	} catch (error) {
		console.error('Failed to mark shown students complete', error);
		showDangerToast('Could not mark shown students complete');
	} finally {
		batchCompletionBusy.value = false;
	}
}

function setEvidenceFilter(filter: EvidenceFilter) {
	activeEvidenceFilter.value = filter;
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

function isLateEvidence(student: StudentRow) {
	return student.submission_status === 'Late';
}

function isMissingEvidence(student: StudentRow) {
	return !student.has_submission && !student.complete;
}

function isSubmittedEvidence(student: StudentRow) {
	if (!student.has_submission) return false;
	return !isLateEvidence(student);
}

function studentMatchesEvidenceFilter(student: StudentRow, filter: EvidenceFilter) {
	switch (filter) {
		case 'new_evidence':
			return Boolean(student.has_new_submission);
		case 'missing':
			return isMissingEvidence(student);
		case 'submitted':
			return isSubmittedEvidence(student);
		case 'late':
			return isLateEvidence(student);
		case 'all':
		default:
			return true;
	}
}

function evidencePriority(student: StudentRow) {
	if (student.has_new_submission) return 0;
	if (isLateEvidence(student)) return 1;
	if (isMissingEvidence(student)) return 2;
	if (isSubmittedEvidence(student)) return 3;
	return 4;
}

function pickDefaultEvidenceFilter(): EvidenceFilter {
	if (evidenceCounts.value.new_evidence) return 'new_evidence';
	if (evidenceCounts.value.late) return 'late';
	if (evidenceCounts.value.missing) return 'missing';
	if (evidenceCounts.value.submitted) return 'submitted';
	return 'all';
}

function syncEvidenceFilter() {
	if (!hasEvidenceInbox.value) {
		activeEvidenceFilter.value = 'all';
		return;
	}
	const currentCount = evidenceCounts.value[activeEvidenceFilter.value];
	if (currentCount > 0) {
		return;
	}
	activeEvidenceFilter.value = pickDefaultEvidenceFilter();
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
