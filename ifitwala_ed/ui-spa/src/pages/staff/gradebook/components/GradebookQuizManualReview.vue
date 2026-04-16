<template>
	<section class="space-y-5 rounded-xl border border-border bg-gray-50/30 p-5">
		<div class="flex flex-wrap items-start justify-between gap-4">
			<div class="space-y-1">
				<h3 class="text-lg font-semibold text-ink">Open-ended Quiz Review</h3>
				<p class="max-w-2xl text-sm text-ink/60">
					Score manually graded quiz responses by question or by student. Each save refreshes the
					official quiz attempt and outcome state on the server.
				</p>
			</div>
			<Button
				size="sm"
				appearance="primary"
				:loading="savingVisible"
				:disabled="!visibleDirtyRows.length"
				@click="saveVisibleRows"
			>
				Save Visible
			</Button>
		</div>

		<div class="flex flex-wrap gap-2">
			<Badge variant="subtle">Manual Items {{ review?.summary.manual_item_count || 0 }}</Badge>
			<Badge variant="subtle">Pending {{ review?.summary.pending_item_count || 0 }}</Badge>
			<Badge variant="subtle">Students {{ review?.summary.pending_student_count || 0 }}</Badge>
			<Badge variant="subtle">Attempts {{ review?.summary.pending_attempt_count || 0 }}</Badge>
		</div>

		<div class="grid gap-4 lg:grid-cols-[auto_minmax(0,1fr)]">
			<div class="inline-flex rounded-lg border border-border bg-white p-1 shadow-sm">
				<button
					type="button"
					class="rounded-md px-3 py-2 text-sm font-medium transition-all"
					:class="
						viewMode === 'question' ? 'bg-leaf text-white shadow-sm' : 'text-ink/70 hover:text-ink'
					"
					@click="setViewMode('question')"
				>
					By Question
				</button>
				<button
					type="button"
					class="rounded-md px-3 py-2 text-sm font-medium transition-all"
					:class="
						viewMode === 'student' ? 'bg-leaf text-white shadow-sm' : 'text-ink/70 hover:text-ink'
					"
					@click="setViewMode('student')"
				>
					By Student
				</button>
			</div>

			<div class="w-full">
				<FormControl
					v-if="viewMode === 'question'"
					type="select"
					:options="
						(review?.questions || []).map(question => ({
							label: questionLabel(question),
							value: question.quiz_question,
						}))
					"
					:model-value="selectedQuestion"
					:disabled="loading || !(review?.questions || []).length"
					placeholder="Select question"
					@update:modelValue="onQuestionSelected"
				/>
				<FormControl
					v-else
					type="select"
					:options="
						(review?.students || []).map(student => ({
							label: studentLabel(student),
							value: student.student,
						}))
					"
					:model-value="selectedStudent"
					:disabled="loading || !(review?.students || []).length"
					placeholder="Select student"
					@update:modelValue="onStudentSelected"
				/>
			</div>
		</div>

		<div
			v-if="loading"
			class="flex min-h-[220px] flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-border/70 bg-white/70 p-6 text-center"
		>
			<Spinner class="h-7 w-7 text-canopy" />
			<p class="text-sm text-ink/50">Loading open-ended quiz responses...</p>
		</div>

		<div
			v-else-if="!(review?.rows || []).length"
			class="rounded-lg border border-dashed border-border/70 bg-white/70 p-6 text-center text-sm text-ink/60"
		>
			<p class="font-medium text-ink">No open-ended quiz responses to review.</p>
			<p class="mt-1">
				This assessed quiz does not currently have submitted manual-grading items in the selected
				view.
			</p>
		</div>

		<div v-else class="space-y-4">
			<article
				v-for="row in review?.rows || []"
				:key="row.item_id"
				class="rounded-xl border border-border bg-white p-5 shadow-sm"
			>
				<div
					class="flex flex-wrap items-start justify-between gap-3 border-b border-border/50 pb-4"
				>
					<div class="space-y-1">
						<p class="text-base font-semibold text-ink">{{ row.title }}</p>
						<div class="flex flex-wrap items-center gap-2 text-xs text-ink/55">
							<span>{{ row.student_name }}</span>
							<span v-if="row.student_id">• {{ row.student_id }}</span>
							<span>• Attempt {{ row.attempt_number || '—' }}</span>
							<span>• {{ row.attempt_status || '—' }}</span>
						</div>
					</div>
					<div class="flex flex-wrap items-center gap-2">
						<Badge v-if="row.requires_manual_grading" variant="subtle" theme="orange"
							>Needs Review</Badge
						>
						<Badge v-else variant="subtle" theme="green">Scored</Badge>
						<Badge v-if="row.grading_status" variant="subtle">{{ row.grading_status }}</Badge>
					</div>
				</div>

				<div class="mt-4 grid gap-5 xl:grid-cols-[minmax(0,2fr)_minmax(16rem,1fr)]">
					<div class="space-y-4">
						<div class="space-y-2">
							<p class="text-xs font-semibold uppercase tracking-wide text-ink/45">Prompt</p>
							<div
								class="prose prose-sm max-w-none rounded-lg border border-border/60 bg-gray-50/60 px-4 py-3 text-ink"
								v-html="row.prompt_html || '<p>No prompt available.</p>'"
							/>
						</div>

						<div class="space-y-2">
							<p class="text-xs font-semibold uppercase tracking-wide text-ink/45">
								Student Response
							</p>
							<div class="rounded-lg border border-border/60 bg-white px-4 py-3">
								<pre class="whitespace-pre-wrap text-sm text-ink">{{ responseLabel(row) }}</pre>
							</div>
						</div>
					</div>

					<div class="space-y-4 rounded-lg border border-border/60 bg-gray-50/50 p-4">
						<div class="space-y-1.5">
							<label class="block text-xs font-semibold uppercase tracking-wide text-ink/50">
								Awarded Score
							</label>
							<FormControl
								type="number"
								:min="0"
								:max="1"
								:step="0.1"
								:model-value="rowStates[row.item_id]?.awarded_score"
								@update:modelValue="onScoreChanged(row.item_id, $event)"
							/>
							<p class="text-xs text-ink/50">Use 0 to 1 for each manually graded quiz item.</p>
						</div>

						<div class="space-y-1 text-xs text-ink/55">
							<p>Submitted {{ formatDateTime(row.submitted_on) || '—' }}</p>
							<p>Question #{{ row.position || '—' }}</p>
						</div>

						<div class="flex items-center justify-between border-t border-border/50 pt-3">
							<Badge v-if="rowStates[row.item_id]?.dirty" variant="subtle" theme="orange"
								>Unsaved</Badge
							>
							<span v-else class="text-xs text-ink/40">Saved</span>
							<Button
								size="sm"
								appearance="primary"
								:loading="rowStates[row.item_id]?.saving"
								:disabled="
									!rowStates[row.item_id]?.dirty || rowStates[row.item_id]?.awarded_score === null
								"
								@click="saveRow(row.item_id)"
							>
								Save Score
							</Button>
						</div>
					</div>
				</div>
			</article>
		</div>
	</section>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue';
import { Badge, Button, FormControl, Spinner, toast } from 'frappe-ui';
import { createGradebookService } from '@/lib/services/gradebook/gradebookService';
import type {
	Response as GetTaskQuizManualReviewResponse,
	QuestionOption as QuizManualQuestionOption,
	ReviewRow as QuizManualReviewRow,
	StudentOption as QuizManualStudentOption,
} from '@/types/contracts/gradebook/get_task_quiz_manual_review';
import { formatDateTime } from '../gradebookUtils';

interface QuizManualRowState {
	awarded_score: number | null;
	dirty: boolean;
	saving: boolean;
}

const props = defineProps<{
	taskName: string;
}>();

const gradebookService = createGradebookService();
const loading = ref(false);
const savingVisible = ref(false);
const review = ref<GetTaskQuizManualReviewResponse | null>(null);
const viewMode = ref<'question' | 'student'>('question');
const selectedQuestion = ref<string | null>(null);
const selectedStudent = ref<string | null>(null);
const rowStates = reactive<Record<string, QuizManualRowState>>({});
const loadVersion = ref(0);

const visibleDirtyRows = computed(() => {
	return (review.value?.rows || []).filter(row => {
		const state = rowStates[row.item_id];
		return Boolean(state?.dirty && state.awarded_score !== null);
	});
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

function clearState() {
	review.value = null;
	viewMode.value = 'question';
	selectedQuestion.value = null;
	selectedStudent.value = null;
	savingVisible.value = false;
	for (const key of Object.keys(rowStates)) {
		delete rowStates[key];
	}
}

async function loadReview() {
	if (!props.taskName) {
		clearState();
		return;
	}

	const version = loadVersion.value + 1;
	loadVersion.value = version;
	loading.value = true;
	try {
		const payload = await gradebookService.getTaskQuizManualReview({
			task: props.taskName,
			view_mode: viewMode.value,
			quiz_question: selectedQuestion.value,
			student: selectedStudent.value,
		});
		if (loadVersion.value !== version) {
			return;
		}
		review.value = payload;
		viewMode.value = payload.view_mode;
		selectedQuestion.value = payload.selected_question?.quiz_question || null;
		selectedStudent.value = payload.selected_student?.student || null;
		initializeRowStates();
	} catch (error) {
		console.error('Failed to load quiz manual review', error);
		if (loadVersion.value === version) {
			showDangerToast('Could not load open-ended quiz review');
			clearState();
		}
	} finally {
		if (loadVersion.value === version) {
			loading.value = false;
		}
	}
}

function initializeRowStates() {
	for (const key of Object.keys(rowStates)) {
		delete rowStates[key];
	}
	for (const row of review.value?.rows || []) {
		rowStates[row.item_id] = {
			awarded_score: row.awarded_score,
			dirty: false,
			saving: false,
		};
	}
}

function normalizeScore(value: string | number | null | undefined) {
	if (value === null || value === undefined || value === '') return null;
	const parsed = typeof value === 'number' ? value : Number.parseFloat(String(value));
	return Number.isFinite(parsed) ? parsed : null;
}

function onScoreChanged(itemId: string, value: string | number | null) {
	const state = rowStates[itemId];
	if (!state) return;
	const nextValue = normalizeScore(value);
	if (state.awarded_score === nextValue) return;
	state.awarded_score = nextValue;
	state.dirty = true;
}

function questionLabel(option: QuizManualQuestionOption) {
	return option.pending_item_count
		? `${option.title} (${option.pending_item_count} pending)`
		: option.title;
}

function studentLabel(option: QuizManualStudentOption) {
	const suffix = option.student_id ? ` • ${option.student_id}` : '';
	const pending = option.pending_item_count ? ` (${option.pending_item_count} pending)` : '';
	return `${option.student_name}${suffix}${pending}`;
}

function responseLabel(row: QuizManualReviewRow) {
	const text = (row.response_text || '').trim();
	if (text) return text;
	if (row.selected_option_labels.length) return row.selected_option_labels.join(', ');
	return 'No response submitted.';
}

async function setViewMode(mode: 'question' | 'student') {
	if (viewMode.value === mode) return;
	viewMode.value = mode;
	if (mode === 'question') {
		selectedStudent.value = null;
	} else {
		selectedQuestion.value = null;
	}
	await loadReview();
}

async function onQuestionSelected(value: string | null) {
	selectedQuestion.value = value;
	await loadReview();
}

async function onStudentSelected(value: string | null) {
	selectedStudent.value = value;
	await loadReview();
}

async function saveRows(itemIds: string[]) {
	if (!props.taskName || !itemIds.length) return;

	const grades = itemIds
		.map(itemId => ({
			item_id: itemId,
			awarded_score: rowStates[itemId]?.awarded_score ?? null,
		}))
		.filter(row => row.awarded_score !== null);
	if (!grades.length) return;

	const uniqueIds = new Set(itemIds);
	itemIds.forEach(itemId => {
		const state = rowStates[itemId];
		if (state) {
			state.saving = true;
		}
	});

	try {
		await gradebookService.saveTaskQuizManualReview({
			task: props.taskName,
			grades,
		});
		showSuccessToast(
			uniqueIds.size === 1
				? 'Quiz score saved.'
				: `Saved ${uniqueIds.size} open-ended quiz scores.`
		);
		await loadReview();
	} catch (error) {
		console.error('Failed to save quiz manual review', error);
		showDangerToast('Could not save open-ended quiz scores');
	} finally {
		itemIds.forEach(itemId => {
			const state = rowStates[itemId];
			if (state) {
				state.saving = false;
			}
		});
	}
}

async function saveRow(itemId: string) {
	await saveRows([itemId]);
}

async function saveVisibleRows() {
	const itemIds = visibleDirtyRows.value.map(row => row.item_id);
	if (!itemIds.length) return;
	savingVisible.value = true;
	try {
		await saveRows(itemIds);
	} finally {
		savingVisible.value = false;
	}
}

watch(
	() => props.taskName,
	() => {
		clearState();
		void loadReview();
	},
	{ immediate: true }
);
</script>
