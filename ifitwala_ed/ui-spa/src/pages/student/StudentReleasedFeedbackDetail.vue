<template>
	<div class="portal-page student-hub-page">
		<div>
			<RouterLink
				:to="backRoute"
				class="inline-flex items-center gap-2 type-body text-ink/70 transition hover:text-ink"
			>
				<span>←</span>
				<span>Back to Course</span>
			</RouterLink>
		</div>

		<section v-if="errorMessage" class="if-banner if-banner--danger">
			<p class="if-banner__title type-body-strong text-flame">Could not load released feedback.</p>
			<p class="if-banner__body mt-2 type-caption">{{ errorMessage }}</p>
		</section>

		<section v-else-if="loading" class="student-hub-section">
			<p class="type-body text-ink/70">Loading released feedback...</p>
		</section>

		<ReleasedFeedbackNavigator
			v-else-if="detail"
			:detail="detail"
			mode="student"
			:reply-busy-target="replyBusyTarget"
			:state-busy-target="stateBusyTarget"
			:export-busy="exportBusy"
			@reply="handleReply"
			@set-learner-state="handleLearnerState"
			@export-feedback-pdf="handleExportFeedbackPdf"
		/>
	</div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { RouterLink } from 'vue-router';
import { toast } from 'frappe-ui';

import ReleasedFeedbackNavigator from '@/components/assessment/ReleasedFeedbackNavigator.vue';
import {
	exportStudentReleasedFeedbackPdf,
	getStudentReleasedFeedbackDetail,
	saveStudentFeedbackReply,
	saveStudentFeedbackThreadState,
} from '@/lib/services/assessment/releasedFeedbackService';
import type { ReleasedFeedbackDetail } from '@/types/contracts/assessment/released_feedback_detail';
import type { FeedbackThread } from '@/types/contracts/gradebook/feedback_workspace';

const props = defineProps<{
	course_id: string;
	task_outcome: string;
	student_group?: string;
	unit_plan?: string;
	class_session?: string;
	task_delivery?: string;
}>();

const loading = ref(false);
const errorMessage = ref('');
const detail = ref<ReleasedFeedbackDetail | null>(null);
const replyBusyTarget = ref<string | null>(null);
const stateBusyTarget = ref<string | null>(null);
const exportBusy = ref(false);

const backRoute = computed(() => ({
	name: 'student-course-detail',
	params: { course_id: props.course_id },
	query: {
		student_group: props.student_group || undefined,
		unit_plan: props.unit_plan || undefined,
		class_session: props.class_session || undefined,
		task_delivery: props.task_delivery || undefined,
	},
}));

function upsertThread(nextThread: FeedbackThread) {
	if (!detail.value?.feedback) return;
	const current = detail.value.feedback.threads || [];
	const next = current.filter(thread => thread.thread_id !== nextThread.thread_id);
	detail.value.feedback.threads = [...next, nextThread];
}

async function loadDetail() {
	loading.value = true;
	errorMessage.value = '';
	try {
		detail.value = await getStudentReleasedFeedbackDetail({ outcome_id: props.task_outcome });
	} catch (error: unknown) {
		detail.value = null;
		errorMessage.value = error instanceof Error && error.message ? error.message : 'Unknown error';
	} finally {
		loading.value = false;
	}
}

async function handleReply(payload: {
	target_feedback_item: string;
	message_kind: 'reply' | 'clarification';
	body: string;
}) {
	replyBusyTarget.value = payload.target_feedback_item;
	try {
		const response = await saveStudentFeedbackReply({
			outcome_id: props.task_outcome,
			submission_id: detail.value?.task_submission || undefined,
			target_type: 'feedback_item',
			target_feedback_item: payload.target_feedback_item,
			message_kind: payload.message_kind,
			body: payload.body,
		});
		upsertThread(response.thread);
		toast.success?.('Reply saved.');
	} catch (error: unknown) {
		toast.error?.(
			error instanceof Error && error.message ? error.message : 'Could not save reply.'
		);
	} finally {
		replyBusyTarget.value = null;
	}
}

async function handleLearnerState(payload: {
	target_feedback_item: string;
	learner_state: 'understood' | 'acted_on' | 'none';
}) {
	stateBusyTarget.value = payload.target_feedback_item;
	try {
		const response = await saveStudentFeedbackThreadState({
			outcome_id: props.task_outcome,
			submission_id: detail.value?.task_submission || undefined,
			target_type: 'feedback_item',
			target_feedback_item: payload.target_feedback_item,
			learner_state: payload.learner_state,
		});
		upsertThread(response.thread);
		toast.success?.('Feedback state updated.');
	} catch (error: unknown) {
		toast.error?.(
			error instanceof Error && error.message ? error.message : 'Could not update feedback state.'
		);
	} finally {
		stateBusyTarget.value = null;
	}
}

async function handleExportFeedbackPdf() {
	exportBusy.value = true;
	try {
		const currentArtifactUrl =
			detail.value?.released_feedback_artifact?.open_url ||
			detail.value?.released_feedback_artifact?.preview_url;
		if (currentArtifactUrl) {
			window.open(currentArtifactUrl, '_blank', 'noopener,noreferrer');
			toast.success?.('Opened the latest feedback PDF.');
			return;
		}
		const response = await exportStudentReleasedFeedbackPdf({ outcome_id: props.task_outcome });
		const targetUrl = response.artifact?.open_url || response.artifact?.preview_url;
		if (!targetUrl) {
			throw new Error('Missing feedback artifact URL');
		}
		if (detail.value) {
			detail.value.released_feedback_artifact = response.artifact;
		}
		window.open(targetUrl, '_blank', 'noopener,noreferrer');
		toast.success?.('Feedback PDF prepared.');
	} catch (error: unknown) {
		toast.error?.(
			error instanceof Error && error.message
				? error.message
				: 'Could not prepare the feedback PDF.'
		);
	} finally {
		exportBusy.value = false;
	}
}

watch(
	() => props.task_outcome,
	() => {
		void loadDetail();
	},
	{ immediate: true }
);
</script>
