<!-- ifitwala_ed/ui-spa/src/components/focus/ApplicantReviewAssignmentAction.vue -->
<template>
	<div class="space-y-4">
		<div class="card-surface p-4">
			<div class="flex items-start justify-between gap-3">
				<div class="min-w-0">
					<div class="type-body font-medium">
						{{ targetLabel }}
						<span v-if="assignment?.name" class="text-muted"> • {{ assignment.name }}</span>
					</div>
					<div class="type-meta text-muted mt-1">
						<span>{{ assignment?.applicant_name || assignment?.student_applicant }}</span>
						<span v-if="assignment?.school"> • {{ assignment.school }}</span>
						<span v-if="assignment?.program_offering"> • {{ assignment.program_offering }}</span>
					</div>
					<div v-if="assignment?.assigned_to_role" class="type-meta text-muted mt-1">
						Assigned role: {{ assignment.assigned_to_role }}
					</div>
				</div>

				<div class="shrink-0 flex items-center gap-2">
					<button v-if="deskUrl" type="button" class="btn btn-quiet" @click="openInDesk">
						Open in Desk
					</button>
					<button type="button" class="btn btn-quiet" @click="requestRefresh">Refresh</button>
				</div>
			</div>
		</div>

		<div v-if="assignment?.preview" class="card-surface p-4">
			<div class="type-body font-medium">Preview</div>
			<div class="mt-2 space-y-2 type-meta text-muted">
				<div v-if="assignment.target_type === 'Applicant Document'">
					<div>
						Document: {{ assignment.preview.document_label || assignment.preview.document_type }}
					</div>
					<div>Current status: {{ assignment.preview.review_status || 'Pending' }}</div>
					<div v-if="assignment.preview.file_url">
						<a :href="assignment.preview.file_url" target="_blank" rel="noopener noreferrer"
							>Open file</a
						>
					</div>
				</div>

				<div v-else-if="assignment.target_type === 'Applicant Health Profile'">
					<div>Current status: {{ assignment.preview.review_status || 'Pending' }}</div>
					<div>
						Declaration: {{ assignment.preview.declared_complete ? 'Complete' : 'Pending' }}
					</div>
				</div>

				<div v-else>
					<div>Application status: {{ assignment.preview.application_status || 'Unknown' }}</div>
				</div>
			</div>
		</div>

		<div class="card-surface p-4">
			<div class="type-body font-medium">Decision</div>
			<div class="mt-3">
				<select v-model="decision" class="if-input w-full" :disabled="busy">
					<option value="">Select a decision</option>
					<option v-for="opt in decisionOptions" :key="opt" :value="opt">{{ opt }}</option>
				</select>
			</div>
			<div class="mt-3">
				<textarea
					v-model="notes"
					class="if-textarea w-full"
					rows="5"
					placeholder="Optional notes"
					:disabled="busy"
				/>
			</div>

			<div v-if="actionError" class="mt-3 rounded-xl border border-ink/10 bg-white p-3">
				<p class="type-meta text-ink">{{ actionError }}</p>
			</div>

			<div class="mt-4 flex items-center justify-end gap-2">
				<button type="button" class="btn btn-quiet" @click="emitClose">Close</button>
				<button
					type="button"
					class="btn btn-primary"
					:disabled="busy || submittedOnce || !canSubmit"
					@click="submitDecision"
				>
					{{ busy ? 'Saving…' : 'Submit decision' }}
				</button>
			</div>
		</div>

		<div v-if="previousReviews.length" class="card-surface p-4">
			<div class="type-body font-medium">Previous reviews</div>
			<div class="mt-3 space-y-2">
				<div
					v-for="row in previousReviews"
					:key="row.assignment"
					class="rounded-xl border border-ink/10 p-3"
				>
					<div class="type-meta text-muted">
						{{ row.reviewer || 'Reviewer' }} • {{ row.decision || '—' }} •
						{{ row.decided_on || '—' }}
					</div>
					<div v-if="row.notes" class="type-body mt-1">{{ row.notes }}</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';

import { __ } from '@/lib/i18n';
import { createFocusService } from '@/lib/services/focus/focusService';

import type { Response as GetFocusContextResponse } from '@/types/contracts/focus/get_focus_context';
import type { Request as SubmitApplicantReviewAssignmentRequest } from '@/types/contracts/focus/submit_applicant_review_assignment';

const props = defineProps<{
	focusItemId?: string | null;
	context: GetFocusContextResponse;
}>();

const emit = defineEmits<{
	(e: 'close'): void;
	(e: 'done'): void;
	(e: 'request-refresh'): void;
}>();

const focusService = createFocusService();

const assignment = ref<GetFocusContextResponse['review_assignment'] | null>(null);
const decision = ref('');
const notes = ref('');
const busy = ref(false);
const submittedOnce = ref(false);
const actionError = ref<string | null>(null);

const targetLabel = computed(() => {
	if (!assignment.value) return __('Applicant review');
	if (assignment.value.target_type === 'Applicant Document')
		return __('Applicant document review');
	if (assignment.value.target_type === 'Applicant Health Profile')
		return __('Applicant health review');
	return __('Overall application review');
});

const decisionOptions = computed(() => assignment.value?.decision_options || []);
const canSubmit = computed(() => Boolean(decision.value && assignment.value?.name));
const previousReviews = computed(() => assignment.value?.previous_reviews || []);

const deskUrl = computed(() => {
	if (!assignment.value) return null;
	if (assignment.value.target_type === 'Applicant Document') {
		return `/desk/applicant-document/${encodeURIComponent(assignment.value.target_name)}`;
	}
	if (assignment.value.target_type === 'Applicant Health Profile') {
		return `/desk/applicant-health-profile/${encodeURIComponent(assignment.value.target_name)}`;
	}
	return `/desk/student-applicant/${encodeURIComponent(assignment.value.student_applicant)}`;
});

watch(
	() => props.context,
	next => {
		assignment.value = next.review_assignment ?? null;
		decision.value = '';
		notes.value = '';
		busy.value = false;
		submittedOnce.value = false;
		actionError.value = null;
	},
	{ immediate: true, deep: false }
);

function emitClose() {
	emit('close');
}

function requestRefresh() {
	emit('request-refresh');
}

function openInDesk() {
	if (!deskUrl.value) return;
	window.open(deskUrl.value, '_blank', 'noopener');
}

function newClientRequestId(prefix = 'applicant_review') {
	return `${prefix}_${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

function errorMessage(err: unknown): string {
	if (err instanceof Error && err.message) return err.message;
	return __('Please try again.');
}

async function submitDecision() {
	if (busy.value || submittedOnce.value) return;

	actionError.value = null;

	if (!assignment.value?.name) {
		actionError.value = __('Missing assignment context. Please reopen from Focus list.');
		return;
	}

	if (!decision.value) {
		actionError.value = __('Please select a decision before submitting.');
		return;
	}

	busy.value = true;
	submittedOnce.value = true;

	try {
		const payload: SubmitApplicantReviewAssignmentRequest = {
			assignment: assignment.value.name,
			decision: decision.value,
			notes: notes.value || null,
			focus_item_id: props.focusItemId || null,
			client_request_id: newClientRequestId(),
		};

		const response = await focusService.submitApplicantReviewAssignment(payload);
		if (!response?.ok) {
			throw new Error(__('Could not submit review decision.'));
		}

		emit('done');
	} catch (err: unknown) {
		submittedOnce.value = false;
		actionError.value = errorMessage(err);
	} finally {
		busy.value = false;
	}
}
</script>
