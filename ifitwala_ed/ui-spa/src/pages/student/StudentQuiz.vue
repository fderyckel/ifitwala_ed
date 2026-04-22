<template>
	<div class="portal-page student-hub-page">
		<div>
			<RouterLink
				:to="backRoute"
				class="inline-flex items-center type-body text-ink/70 transition hover:text-ink"
			>
				<span class="mr-2">←</span>
				Back to Course
			</RouterLink>
		</div>

		<section v-if="errorMessage" class="if-banner if-banner--danger">
			<p class="if-banner__title type-body-strong text-flame">Could not open this quiz.</p>
			<p class="if-banner__body mt-2 type-caption">{{ errorMessage }}</p>
		</section>

		<section v-else-if="loading" class="student-hub-section">
			<p class="type-body text-ink/70">Loading quiz...</p>
		</section>

		<template v-else-if="sessionPayload">
			<header class="student-hub-hero">
				<div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
					<div>
						<p class="type-overline text-ink/60">
							{{ isPractice ? 'Practice Quiz' : 'Assessed Quiz' }}
						</p>
						<h1 class="mt-2 type-h1 text-ink">{{ sessionPayload.session.title }}</h1>
						<p class="mt-2 type-body text-ink/70">
							Attempt {{ sessionPayload.session.attempt_number }}
							<span v-if="sessionPayload.session.max_attempts">
								of {{ sessionPayload.session.max_attempts }}
							</span>
						</p>
					</div>
					<div class="flex flex-wrap gap-2">
						<span class="chip chip-focus">{{ sessionPayload.session.status }}</span>
						<span v-if="sessionPayload.session.pass_percentage != null" class="chip chip-warm">
							Pass at {{ sessionPayload.session.pass_percentage }}%
						</span>
						<span v-if="timeRemainingLabel" class="chip chip-warm">{{ timeRemainingLabel }}</span>
					</div>
				</div>
			</header>

			<section
				v-if="sessionPayload.mode === 'attempt'"
				class="student-hub-section student-hub-section--focus"
			>
				<div class="mb-5 flex flex-wrap gap-3">
					<button
						type="button"
						class="if-button if-button--secondary"
						:disabled="saving || submitting"
						@click="saveProgress"
					>
						{{ saving ? 'Saving...' : 'Save Progress' }}
					</button>
					<button
						type="button"
						class="if-button if-button--primary"
						:disabled="submitting || saving"
						@click="submitQuiz"
					>
						{{ submitting ? 'Submitting...' : 'Submit Quiz' }}
					</button>
				</div>

				<p v-if="actionMessage" class="mb-4 type-caption text-ink/70">{{ actionMessage }}</p>

				<div class="space-y-5">
					<article
						v-for="item in sessionPayload.items || []"
						:key="item.item_id"
						class="student-hub-card student-hub-card--neutral p-5"
					>
						<p class="type-overline text-ink/60">Question {{ item.position }}</p>
						<div class="mt-2 type-body text-ink quiz-richtext" v-html="item.prompt_html || ''" />

						<div v-if="isChoiceType(item.question_type)" class="mt-4 space-y-3">
							<label v-for="option in item.options" :key="option.id" class="portal-choice-row">
								<input
									v-if="item.question_type === 'Multiple Answer'"
									type="checkbox"
									:checked="isSelected(item.item_id, option.id)"
									@change="toggleChoice(item.item_id, option.id)"
								/>
								<input
									v-else
									type="radio"
									:name="item.item_id"
									:checked="isSelected(item.item_id, option.id)"
									@change="setSingleChoice(item.item_id, option.id)"
								/>
								<span class="type-body text-ink">{{ option.text }}</span>
							</label>
						</div>

						<div v-else class="mt-4">
							<textarea
								:value="textResponse(item.item_id)"
								rows="4"
								class="if-textarea"
								:placeholder="
									item.question_type === 'Essay'
										? 'Write your response here'
										: 'Type your answer here'
								"
								@input="
									setTextResponse(item.item_id, ($event.target as HTMLTextAreaElement).value)
								"
							/>
						</div>
					</article>
				</div>
			</section>

			<section v-else-if="sessionPayload.review" class="student-hub-section">
				<div class="mb-5 flex flex-wrap gap-2">
					<span class="chip chip-focus">Status {{ sessionPayload.review.attempt.status }}</span>
					<span v-if="sessionPayload.review.attempt.score != null" class="chip">
						Score {{ sessionPayload.review.attempt.score }}
					</span>
					<span v-if="sessionPayload.review.attempt.percentage != null" class="chip">
						{{ sessionPayload.review.attempt.percentage }}%
					</span>
					<span v-if="sessionPayload.review.attempt.requires_manual_review" class="chip chip-warm">
						Awaiting manual review
					</span>
				</div>

				<section class="mb-5 rounded-2xl border border-line-soft bg-surface-soft p-4">
					<div class="flex flex-wrap gap-2">
						<span v-if="releasedResult?.grade_visible" class="chip chip-focus">
							Grade released
						</span>
						<span v-if="releasedResult?.feedback_visible" class="chip chip-warm">
							Feedback released
						</span>
						<span v-if="releasedResult?.feedback?.submission_version" class="chip">
							Feedback on version {{ releasedResult.feedback.submission_version }}
						</span>
					</div>

					<p v-if="releasedResultMessage" class="mt-3 type-body text-ink/70">
						{{ releasedResultMessage }}
					</p>
					<template v-else-if="releasedResult">
						<div class="mt-3 flex flex-wrap gap-2">
							<span v-if="releasedResult.official.grade" class="chip">
								Grade {{ releasedResult.official.grade }}
							</span>
							<span v-if="releasedResult.official.feedback" class="chip"> Teacher feedback </span>
							<RouterLink
								v-if="releasedFeedbackRoute"
								:to="releasedFeedbackRoute"
								class="if-button if-button--secondary"
							>
								Open released feedback
							</RouterLink>
						</div>

						<div
							v-if="
								releasedResult.feedback?.summary.overall ||
								releasedResult.feedback?.summary.strengths ||
								releasedResult.feedback?.summary.improvements ||
								releasedResult.feedback?.summary.next_steps
							"
							class="mt-4 grid gap-3 lg:grid-cols-2"
						>
							<article
								v-if="releasedResult.feedback?.summary.overall"
								class="rounded-2xl border border-line-soft bg-white p-3"
							>
								<p class="type-caption text-ink/60">Overall summary</p>
								<p class="mt-2 type-body text-ink/80">
									{{ releasedResult.feedback?.summary.overall }}
								</p>
							</article>
							<article
								v-if="releasedResult.feedback?.summary.strengths"
								class="rounded-2xl border border-line-soft bg-white p-3"
							>
								<p class="type-caption text-ink/60">Strengths</p>
								<p class="mt-2 type-body text-ink/80">
									{{ releasedResult.feedback?.summary.strengths }}
								</p>
							</article>
							<article
								v-if="releasedResult.feedback?.summary.improvements"
								class="rounded-2xl border border-line-soft bg-white p-3"
							>
								<p class="type-caption text-ink/60">Improvements</p>
								<p class="mt-2 type-body text-ink/80">
									{{ releasedResult.feedback?.summary.improvements }}
								</p>
							</article>
							<article
								v-if="releasedResult.feedback?.summary.next_steps"
								class="rounded-2xl border border-line-soft bg-white p-3"
							>
								<p class="type-caption text-ink/60">Next steps</p>
								<p class="mt-2 type-body text-ink/80">
									{{ releasedResult.feedback?.summary.next_steps }}
								</p>
							</article>
						</div>
					</template>
				</section>

				<div class="space-y-5">
					<article
						v-for="item in sessionPayload.review.items"
						:key="item.item_id"
						class="student-hub-card student-hub-card--neutral p-5"
					>
						<p class="type-overline text-ink/60">Question {{ item.position }}</p>
						<div class="mt-2 type-body text-ink quiz-richtext" v-html="item.prompt_html || ''" />

						<div v-if="item.options.length" class="mt-4 space-y-2">
							<div
								v-for="option in item.options"
								:key="option.id"
								class="portal-choice-row"
								:class="
									item.correct_option_ids.includes(option.id)
										? 'portal-choice-row--success'
										: item.selected_option_ids.includes(option.id)
											? 'portal-choice-row--focus'
											: ''
								"
							>
								<p class="type-body text-ink">{{ option.text }}</p>
							</div>
						</div>

						<div
							v-else-if="item.response_text"
							class="mt-4 student-hub-card student-hub-card--neutral p-4"
						>
							<p class="type-caption text-ink/60">Your response</p>
							<p class="mt-2 type-body text-ink">{{ item.response_text }}</p>
						</div>

						<p class="mt-4 type-caption text-ink/70">
							{{ reviewLine(item) }}
						</p>
						<div
							v-if="item.explanation_html"
							class="mt-4 student-hub-card student-hub-card--focus p-4 type-body text-ink quiz-richtext"
							v-html="item.explanation_html"
						/>
					</article>
				</div>
			</section>
		</template>
	</div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue';
import { RouterLink } from 'vue-router';

import {
	openStudentQuizSession,
	saveStudentQuizAttempt,
	submitStudentQuizAttempt,
} from '@/lib/services/student/studentQuizService';
import type {
	Response as OpenStudentQuizSessionResponse,
	StudentQuizItem,
	StudentQuizReviewItem,
} from '@/types/contracts/student_quiz/open_student_quiz_session';
import type { StudentQuizAttemptResponse } from '@/types/contracts/student_quiz/save_student_quiz_attempt';

const props = defineProps<{
	course_id: string;
	task_delivery: string;
	student_group?: string;
	unit_plan?: string;
	class_session?: string;
}>();

const loading = ref(false);
const saving = ref(false);
const submitting = ref(false);
const errorMessage = ref('');
const actionMessage = ref('');
const sessionPayload = ref<OpenStudentQuizSessionResponse | null>(null);
const choiceResponses = ref<Record<string, string[]>>({});
const textResponses = ref<Record<string, string>>({});
const nowMs = ref(Date.now());
let timer: number | null = null;

const backRoute = computed(() => ({
	name: 'student-course-detail',
	params: { course_id: props.course_id },
	query: {
		student_group: props.student_group || undefined,
		unit_plan: props.unit_plan || undefined,
		class_session: props.class_session || undefined,
	},
}));
const releasedFeedbackRoute = computed(() => {
	const outcomeId = sessionPayload.value?.released_result?.outcome_id;
	const hasVisibleRelease =
		sessionPayload.value?.released_result?.feedback_visible ||
		sessionPayload.value?.released_result?.grade_visible;
	if (!outcomeId || !hasVisibleRelease) return null;
	return {
		name: 'student-released-feedback',
		params: {
			course_id: props.course_id,
			task_outcome: outcomeId,
		},
		query: {
			student_group: props.student_group || undefined,
			unit_plan: props.unit_plan || undefined,
			class_session: props.class_session || undefined,
			task_delivery: props.task_delivery,
		},
	};
});

const isPractice = computed(() => Boolean(sessionPayload.value?.session.is_practice));
const releasedResult = computed(() => sessionPayload.value?.released_result || null);
const releasedResultMessage = computed(() => {
	if (isPractice.value) return '';
	if (sessionPayload.value?.review?.attempt.requires_manual_review) {
		return 'This quiz is still being reviewed. Released scores and feedback will appear here after grading is complete.';
	}
	if (!releasedResult.value) {
		return 'Results and feedback will appear here after your teacher releases them.';
	}
	if (!releasedResult.value.grade_visible && !releasedResult.value.feedback_visible) {
		return 'Results and feedback will appear here after your teacher releases them.';
	}
	return '';
});

const timeRemainingLabel = computed(() => {
	const expiresOn = sessionPayload.value?.session.expires_on;
	if (!expiresOn || sessionPayload.value?.mode !== 'attempt') return '';
	const remainingMs = new Date(expiresOn).getTime() - nowMs.value;
	if (Number.isNaN(remainingMs) || remainingMs <= 0) return 'Time expired';
	const totalMinutes = Math.floor(remainingMs / 60000);
	const hours = Math.floor(totalMinutes / 60);
	const minutes = totalMinutes % 60;
	if (hours > 0) return `${hours}h ${minutes}m remaining`;
	return `${minutes}m remaining`;
});

function startTimer() {
	stopTimer();
	timer = window.setInterval(() => {
		nowMs.value = Date.now();
	}, 30000);
}

function stopTimer() {
	if (timer != null) {
		window.clearInterval(timer);
		timer = null;
	}
}

async function loadSession() {
	loading.value = true;
	errorMessage.value = '';
	actionMessage.value = '';
	try {
		const payload = await openStudentQuizSession({ task_delivery: props.task_delivery });
		sessionPayload.value = payload;
		hydrateResponses(payload);
		if (payload.mode === 'attempt' && payload.session.expires_on) {
			startTimer();
		} else {
			stopTimer();
		}
	} catch (error: unknown) {
		sessionPayload.value = null;
		stopTimer();
		if (error instanceof Error && error.message) {
			errorMessage.value = error.message;
		} else if (typeof error === 'string' && error) {
			errorMessage.value = error;
		} else {
			errorMessage.value = 'Unable to open this quiz.';
		}
	} finally {
		loading.value = false;
	}
}

function hydrateResponses(payload: OpenStudentQuizSessionResponse) {
	choiceResponses.value = {};
	textResponses.value = {};
	if (payload.mode !== 'attempt') return;
	for (const item of payload.items || []) {
		if (isChoiceType(item.question_type)) {
			choiceResponses.value[item.item_id] = [...(item.selected_option_ids || [])];
		} else {
			textResponses.value[item.item_id] = item.response_text || '';
		}
	}
}

function isChoiceType(questionType: string): boolean {
	return ['Single Choice', 'Multiple Answer', 'True / False'].includes(questionType);
}

function isSelected(itemId: string, optionId: string): boolean {
	return (choiceResponses.value[itemId] || []).includes(optionId);
}

function setSingleChoice(itemId: string, optionId: string) {
	choiceResponses.value[itemId] = [optionId];
}

function toggleChoice(itemId: string, optionId: string) {
	const current = new Set(choiceResponses.value[itemId] || []);
	if (current.has(optionId)) {
		current.delete(optionId);
	} else {
		current.add(optionId);
	}
	choiceResponses.value[itemId] = Array.from(current);
}

function textResponse(itemId: string): string {
	return textResponses.value[itemId] || '';
}

function setTextResponse(itemId: string, value: string) {
	textResponses.value[itemId] = value;
}

function buildResponses(): StudentQuizAttemptResponse[] {
	const payload = sessionPayload.value;
	if (!payload || payload.mode !== 'attempt') return [];
	return (payload.items || []).map((item: StudentQuizItem) => {
		if (isChoiceType(item.question_type)) {
			return {
				item_id: item.item_id,
				selected_option_ids: choiceResponses.value[item.item_id] || [],
			};
		}
		return {
			item_id: item.item_id,
			response_text: textResponses.value[item.item_id] || '',
		};
	});
}

async function saveProgress() {
	if (!sessionPayload.value || sessionPayload.value.mode !== 'attempt') return;
	saving.value = true;
	actionMessage.value = '';
	try {
		await saveStudentQuizAttempt({
			attempt_id: sessionPayload.value.session.attempt_id,
			responses: buildResponses(),
		});
		actionMessage.value = 'Progress saved.';
	} catch (error: unknown) {
		actionMessage.value =
			error instanceof Error && error.message ? error.message : 'Could not save progress.';
	} finally {
		saving.value = false;
	}
}

async function submitQuiz() {
	if (!sessionPayload.value || sessionPayload.value.mode !== 'attempt') return;
	submitting.value = true;
	actionMessage.value = '';
	try {
		const result = await submitStudentQuizAttempt({
			attempt_id: sessionPayload.value.session.attempt_id,
			responses: buildResponses(),
		});
		sessionPayload.value = {
			mode: 'review',
			session: {
				...sessionPayload.value.session,
				status: result.attempt.status,
				submitted_on: result.attempt.submitted_on || null,
				score: result.attempt.score ?? null,
				percentage: result.attempt.percentage ?? null,
				passed: result.attempt.passed,
				requires_manual_review: result.attempt.requires_manual_review,
			},
			review: result.review,
			released_result: result.released_result ?? null,
		};
		stopTimer();
	} catch (error: unknown) {
		actionMessage.value =
			error instanceof Error && error.message ? error.message : 'Could not submit this quiz.';
	} finally {
		submitting.value = false;
	}
}

function reviewLine(item: StudentQuizReviewItem): string {
	if (item.requires_manual_grading) return 'Awaiting manual review.';
	if (!isPractice.value && !releasedResult.value?.feedback_visible) return 'Response recorded.';
	if (item.awarded_score != null) return `Score ${item.awarded_score}.`;
	return item.is_correct ? 'Correct.' : 'Incorrect.';
}

watch(
	() => props.task_delivery,
	() => {
		void loadSession();
	},
	{ immediate: true }
);

onBeforeUnmount(() => {
	stopTimer();
});
</script>

<style scoped>
.quiz-richtext :deep(p + p) {
	margin-top: 0.75rem;
}
</style>
