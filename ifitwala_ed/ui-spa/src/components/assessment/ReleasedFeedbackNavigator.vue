<template>
	<div class="space-y-5">
		<header class="card-surface p-5 sm:p-6">
			<div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
				<div class="min-w-0">
					<p class="type-overline text-ink/60">{{ modeLabel }}</p>
					<h1 class="mt-2 type-h2 text-ink">{{ detail.context.title }}</h1>
					<p v-if="contextLine" class="mt-2 type-caption text-ink/65">{{ contextLine }}</p>
					<p class="mt-3 type-body text-ink/75">
						{{ heroMessage }}
					</p>
				</div>
				<div class="flex flex-wrap gap-2">
					<span v-if="detail.feedback?.submission_version" class="chip">
						Feedback on version {{ detail.feedback.submission_version }}
					</span>
					<span v-if="detail.grade_visible" class="chip chip-focus">Grade released</span>
					<span v-if="detail.feedback_visible" class="chip chip-warm">Feedback released</span>
				</div>
			</div>

			<div class="mt-4 flex flex-wrap gap-2">
				<span v-if="detail.official.score != null" class="chip">
					Score {{ formatScore(detail.official.score) }}
				</span>
				<span v-if="detail.official.grade" class="chip"> Grade {{ detail.official.grade }} </span>
				<button
					v-if="mode === 'student' && detail.feedback_visible"
					type="button"
					class="if-button if-button--secondary"
					:disabled="Boolean(exportBusy)"
					@click="emit('export-feedback-pdf')"
				>
					{{ exportBusy ? 'Preparing…' : exportButtonLabel }}
				</button>
			</div>
		</header>

		<section
			v-if="detail.feedback"
			class="grid gap-5 xl:grid-cols-[minmax(0,1.05fr),minmax(0,0.95fr)]"
		>
			<div class="space-y-5">
				<section class="card-surface p-5">
					<div class="flex items-center justify-between gap-3">
						<div>
							<p class="type-overline text-ink/60">Summary</p>
							<h2 class="mt-2 type-h3 text-ink">What matters most</h2>
						</div>
						<span class="chip">{{ summaryCardCount }}</span>
					</div>
					<div class="mt-4 grid gap-3 md:grid-cols-2">
						<article
							v-for="card in summaryCards"
							:key="card.label"
							class="rounded-2xl border border-line-soft bg-surface-soft p-4"
						>
							<p class="type-caption text-ink/60">{{ card.label }}</p>
							<p class="mt-2 type-body text-ink/80">{{ card.body }}</p>
						</article>
					</div>
				</section>

				<section v-if="detail.feedback.priorities.length" class="card-surface p-5">
					<div class="flex items-center justify-between gap-3">
						<div>
							<p class="type-overline text-ink/60">Priorities</p>
							<h2 class="mt-2 type-h3 text-ink">Start here</h2>
						</div>
						<span class="chip">{{ detail.feedback.priorities.length }}</span>
					</div>

					<div class="mt-4 space-y-3">
						<button
							v-for="priority in detail.feedback.priorities"
							:key="priority.id || priority.title"
							type="button"
							class="w-full rounded-2xl border border-line-soft bg-surface-soft p-4 text-left transition hover:border-jacaranda/30 hover:bg-jacaranda/5"
							@click="focusPriority(priority)"
						>
							<div class="flex items-start justify-between gap-3">
								<div class="min-w-0">
									<p class="type-body-strong text-ink">{{ priority.title }}</p>
									<p v-if="priority.detail" class="mt-2 type-body text-ink/75">
										{{ priority.detail }}
									</p>
								</div>
								<span v-if="priority.feedback_item_id" class="chip chip-focus">Open note</span>
							</div>
						</button>
					</div>
				</section>

				<section v-if="detail.feedback.rubric_snapshot.length" class="card-surface p-5">
					<div class="flex items-center justify-between gap-3">
						<div>
							<p class="type-overline text-ink/60">Rubric Snapshot</p>
							<h2 class="mt-2 type-h3 text-ink">Criterion view</h2>
						</div>
						<span class="chip">{{ detail.feedback.rubric_snapshot.length }}</span>
					</div>

					<div class="mt-4 grid gap-3 lg:grid-cols-2">
						<article
							v-for="row in detail.feedback.rubric_snapshot"
							:key="row.assessment_criteria || row.criteria_name"
							class="rounded-2xl border border-line-soft bg-surface-soft p-4"
						>
							<div class="flex items-start justify-between gap-3">
								<div class="min-w-0">
									<p class="type-body-strong text-ink">{{ row.criteria_name }}</p>
									<p v-if="row.feedback" class="mt-2 type-caption text-ink/70">
										{{ row.feedback }}
									</p>
								</div>
								<div class="flex shrink-0 flex-col items-end gap-1">
									<span v-if="row.level" class="chip">{{ row.level }}</span>
									<span v-if="row.points != null" class="chip chip-focus">{{ row.points }}</span>
								</div>
							</div>
						</article>
					</div>
				</section>
			</div>

			<div class="space-y-5">
				<section class="card-surface p-5">
					<div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
						<div>
							<p class="type-overline text-ink/60">Feedback List</p>
							<h2 class="mt-2 type-h3 text-ink">Review each note</h2>
						</div>
						<nav class="if-segmented overflow-x-auto pb-1">
							<button
								v-for="filter in filterOptions"
								:key="filter.id"
								type="button"
								class="if-segmented__item shrink-0"
								:class="selectedFilter === filter.id ? 'if-segmented__item--active' : ''"
								@click="selectedFilter = filter.id"
							>
								{{ filter.label }}
							</button>
						</nav>
					</div>

					<div class="mt-4 space-y-3">
						<article
							v-for="item in filteredItems"
							:key="item.id || `${item.page}-${item.comment}`"
							class="rounded-2xl border p-4 transition"
							:class="
								selectedItemId === item.id
									? 'border-jacaranda/35 bg-jacaranda/5 shadow-sm'
									: 'border-line-soft bg-surface-soft hover:border-jacaranda/20'
							"
						>
							<button type="button" class="w-full text-left" @click="selectItem(item.id)">
								<div class="flex items-start justify-between gap-3">
									<div class="min-w-0">
										<div class="flex flex-wrap gap-2">
											<span class="chip chip-focus">{{ itemIntentLabel(item.intent) }}</span>
											<span class="chip">Page {{ item.page }}</span>
											<span
												v-if="threadByItemId(item.id)?.learner_state !== 'none'"
												class="chip chip-warm"
											>
												{{ learnerStateLabel(threadByItemId(item.id)?.learner_state || 'none') }}
											</span>
											<span
												v-if="threadByItemId(item.id)?.thread_status === 'resolved'"
												class="chip"
											>
												Resolved
											</span>
										</div>
										<p class="mt-3 type-body text-ink/85">
											{{ item.comment || 'No comment text yet.' }}
										</p>
									</div>
									<span class="chip">{{ itemOrdinal(item.id) }}</span>
								</div>
							</button>

							<div
								v-if="threadByItemId(item.id)?.messages.length"
								class="mt-4 space-y-2 border-t border-line-soft pt-4"
							>
								<div
									v-for="message in threadByItemId(item.id)?.messages || []"
									:key="message.id || `${message.author_role}-${message.created}`"
									class="rounded-2xl px-3 py-3"
									:class="
										message.author_role === 'student'
											? 'bg-jacaranda/6'
											: 'bg-white ring-1 ring-line-soft'
									"
								>
									<div class="flex flex-wrap items-center gap-2">
										<span class="chip">{{
											message.author_role === 'student' ? 'Student' : 'Instructor'
										}}</span>
										<span class="type-caption text-ink/60">{{
											message.message_kind === 'clarification' ? 'Clarification' : 'Reply'
										}}</span>
									</div>
									<p class="mt-2 type-body text-ink/80">{{ message.body }}</p>
								</div>
							</div>

							<div
								v-if="mode === 'student' && detail.allowed_actions.can_set_learner_state"
								class="mt-4 flex flex-wrap gap-2 border-t border-line-soft pt-4"
							>
								<button
									type="button"
									class="if-button if-button--secondary"
									:disabled="stateBusyTarget === item.id"
									@click="emitLearnerState(item.id, 'understood')"
								>
									{{ stateBusyTarget === item.id ? 'Saving...' : 'Mark understood' }}
								</button>
								<button
									type="button"
									class="if-button if-button--secondary"
									:disabled="stateBusyTarget === item.id"
									@click="emitLearnerState(item.id, 'acted_on')"
								>
									{{ stateBusyTarget === item.id ? 'Saving...' : 'Mark acted on' }}
								</button>
							</div>

							<div
								v-if="mode === 'student' && detail.allowed_actions.can_reply"
								class="mt-4 border-t border-line-soft pt-4"
							>
								<textarea
									v-model="replyDraftByItem[item.id || '']"
									rows="3"
									class="if-textarea"
									placeholder="Reply to this note or ask for clarification."
								/>
								<div class="mt-3 flex flex-wrap gap-2">
									<button
										type="button"
										class="if-button if-button--secondary"
										:disabled="
											replyBusyTarget === item.id || !replyDraftByItem[item.id || '']?.trim()
										"
										@click="emitReply(item.id, 'reply')"
									>
										{{ replyBusyTarget === item.id ? 'Sending...' : 'Reply' }}
									</button>
									<button
										type="button"
										class="if-button if-button--primary"
										:disabled="
											replyBusyTarget === item.id || !replyDraftByItem[item.id || '']?.trim()
										"
										@click="emitReply(item.id, 'clarification')"
									>
										{{ replyBusyTarget === item.id ? 'Sending...' : 'Ask for clarification' }}
									</button>
								</div>
							</div>
						</article>

						<div
							v-if="!filteredItems.length"
							class="rounded-2xl border border-dashed border-line-soft p-5"
						>
							<p class="type-body text-ink/70">No feedback notes match this filter yet.</p>
						</div>
					</div>
				</section>

				<ReleasedFeedbackPdfViewer
					v-if="detail.document"
					:document="detail.document"
					:items="detail.feedback.items"
					:selected-item-id="selectedItemId"
					@select-item="selectItem"
				/>
			</div>
		</section>

		<section v-else class="card-surface p-5">
			<p class="type-body text-ink/75">
				Your score or grade is visible here, but detailed feedback has not been released on this
				item.
			</p>
		</section>
	</div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';

import ReleasedFeedbackPdfViewer from '@/components/assessment/ReleasedFeedbackPdfViewer.vue';
import type { ReleasedFeedbackDetail } from '@/types/contracts/assessment/released_feedback_detail';
import type {
	FeedbackPriority,
	FeedbackThreadLearnerState,
} from '@/types/contracts/gradebook/feedback_workspace';

const props = defineProps<{
	detail: ReleasedFeedbackDetail;
	mode: 'student' | 'guardian';
	replyBusyTarget?: string | null;
	stateBusyTarget?: string | null;
	exportBusy?: boolean;
}>();

const emit = defineEmits<{
	(
		e: 'reply',
		payload: {
			target_feedback_item: string;
			message_kind: 'reply' | 'clarification';
			body: string;
		}
	): void;
	(
		e: 'set-learner-state',
		payload: {
			target_feedback_item: string;
			learner_state: Exclude<FeedbackThreadLearnerState, 'none'> | 'none';
		}
	): void;
	(e: 'export-feedback-pdf'): void;
}>();

const selectedFilter = ref<
	'all' | 'strength' | 'issue' | 'question' | 'next_step' | 'rubric_evidence'
>('all');
const selectedItemId = ref<string | null>(props.detail.feedback?.items[0]?.id || null);
const replyDraftByItem = ref<Record<string, string>>({});

const modeLabel = computed(() =>
	props.mode === 'student' ? 'Released feedback' : 'Guardian view'
);
const contextLine = computed(() => {
	const parts = [props.detail.context.course_name, props.detail.context.task_type].filter(Boolean);
	return parts.join(' · ');
});
const heroMessage = computed(() => {
	if (props.detail.feedback_visible) {
		return 'Start with the summary, then work through the priorities and linked notes one at a time.';
	}
	return 'The result is visible, but detailed feedback has not been released yet.';
});
const exportButtonLabel = computed(() =>
	props.detail.released_feedback_artifact ? 'Open latest feedback PDF' : 'Prepare feedback PDF'
);
const summaryCards = computed(() => {
	const summary = props.detail.feedback?.summary;
	if (!summary) return [];
	return [
		{ label: 'Overall summary', body: summary.overall },
		{ label: 'Strengths', body: summary.strengths },
		{ label: 'Improvements', body: summary.improvements },
		{ label: 'Next steps', body: summary.next_steps },
	].filter(card => card.body);
});
const summaryCardCount = computed(() => summaryCards.value.length);
const filterOptions = computed(() => [
	{ id: 'all' as const, label: 'All' },
	{ id: 'strength' as const, label: 'Strengths' },
	{ id: 'issue' as const, label: 'Issues' },
	{ id: 'question' as const, label: 'Questions' },
	{ id: 'next_step' as const, label: 'Next steps' },
	{ id: 'rubric_evidence' as const, label: 'Rubric evidence' },
]);
const filteredItems = computed(() => {
	const items = props.detail.feedback?.items || [];
	if (selectedFilter.value === 'all') return items;
	return items.filter(item => item.intent === selectedFilter.value);
});
const threadsByItem = computed(() => {
	const map = new Map<
		string,
		NonNullable<ReleasedFeedbackDetail['feedback']>['threads'][number]
	>();
	for (const thread of props.detail.feedback?.threads || []) {
		if (thread.target_feedback_item) {
			map.set(thread.target_feedback_item, thread);
		}
	}
	return map;
});

function formatScore(value: number | string) {
	return typeof value === 'number' ? value.toString() : String(value);
}

function threadByItemId(itemId?: string | null) {
	if (!itemId) return null;
	return threadsByItem.value.get(itemId) || null;
}

function itemIntentLabel(intent: string) {
	if (intent === 'strength') return 'Strength';
	if (intent === 'question') return 'Question';
	if (intent === 'next_step') return 'Next step';
	if (intent === 'rubric_evidence') return 'Rubric evidence';
	return 'Issue';
}

function learnerStateLabel(state: FeedbackThreadLearnerState) {
	if (state === 'understood') return 'Understood';
	if (state === 'acted_on') return 'Acted on';
	return 'Open';
}

function itemOrdinal(itemId?: string | null) {
	if (!itemId) return '•';
	return (props.detail.feedback?.items || []).findIndex(item => item.id === itemId) + 1;
}

function selectItem(itemId: string | null) {
	selectedItemId.value = itemId;
}

function focusPriority(priority: FeedbackPriority) {
	if (!priority.feedback_item_id) return;
	selectedItemId.value = priority.feedback_item_id;
}

function emitReply(itemId: string | undefined | null, messageKind: 'reply' | 'clarification') {
	if (!itemId) return;
	const body = replyDraftByItem.value[itemId]?.trim();
	if (!body) return;
	emit('reply', {
		target_feedback_item: itemId,
		message_kind: messageKind,
		body,
	});
	replyDraftByItem.value[itemId] = '';
}

function emitLearnerState(
	itemId: string | undefined | null,
	learnerState: Exclude<FeedbackThreadLearnerState, 'none'>
) {
	if (!itemId) return;
	emit('set-learner-state', {
		target_feedback_item: itemId,
		learner_state: learnerState,
	});
}

watch(
	() => props.detail.feedback?.items,
	items => {
		const firstId = items?.[0]?.id || null;
		if (!selectedItemId.value || !(items || []).some(item => item.id === selectedItemId.value)) {
			selectedItemId.value = firstId;
		}
	},
	{ immediate: true, deep: true }
);
</script>
