<!-- ifitwala_ed/ui-spa/src/components/focus/ApplicantInterviewFeedbackAction.vue -->
<template>
	<div class="space-y-4">
		<div class="card-surface p-4">
			<div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
				<div class="min-w-0">
					<div class="type-body font-medium text-ink">
						{{
							interviewPayload?.applicant_name ||
							interviewPayload?.student_applicant ||
							__('Applicant')
						}}
					</div>
					<div class="type-meta text-ink/60 mt-1">
						<span v-if="interviewPayload?.interview_type">{{
							interviewPayload.interview_type
						}}</span>
						<span v-if="scheduledLabel"> • {{ scheduledLabel }}</span>
						<span v-if="interviewPayload?.school"> • {{ interviewPayload.school }}</span>
					</div>
					<div v-if="feedbackStatusLabel" class="type-meta text-ink/60 mt-1">
						{{ feedbackStatusLabel }}
					</div>
				</div>

				<button type="button" class="if-button if-button--primary" @click="openInterviewWorkspace">
					{{ __('Open interview workspace') }}
				</button>
			</div>
		</div>

		<div v-if="actionError" class="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2">
			<p class="type-caption text-rose-900">{{ actionError }}</p>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';

import { useOverlayStack } from '@/composables/useOverlayStack';
import { __ } from '@/lib/i18n';

import type { Response as GetFocusContextResponse } from '@/types/contracts/focus/get_focus_context';

const props = defineProps<{
	context: GetFocusContextResponse;
}>();

const overlay = useOverlayStack();
const actionError = ref<string | null>(null);

const interviewPayload = computed(() => props.context?.interview_feedback || null);

const scheduledLabel = computed(() => {
	const start = String(interviewPayload.value?.interview_start || '').trim();
	if (start) return start;
	return String(interviewPayload.value?.interview_date || '').trim();
});

const feedbackStatusLabel = computed(() => {
	const status = String(interviewPayload.value?.feedback_status || '').trim();
	if (!status || status === 'Submitted') return null;
	return status === 'Draft' ? __('Draft feedback saved') : __('Feedback pending');
});

function openInterviewWorkspace() {
	actionError.value = null;
	const interview = String(
		interviewPayload.value?.interview || props.context.reference_name || ''
	).trim();
	if (!interview) {
		actionError.value = __(
			'Interview reference is missing. Reopen this item from the Focus list.'
		);
		return;
	}

	overlay.replaceTop('admissions-workspace', {
		mode: 'interview',
		interview,
		schoolEvent: interviewPayload.value?.school_event || null,
	});
}
</script>
