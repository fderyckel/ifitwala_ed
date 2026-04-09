<!-- ifitwala_ed/ui-spa/src/components/focus/ApplicantReviewAssignmentAction.vue -->
<template>
	<div class="space-y-4">
		<div class="card-surface p-4">
			<div class="flex items-start justify-between gap-3">
				<div class="min-w-0">
					<div class="type-body font-medium">
						{{ targetLabel }}
						<span v-if="assignment?.name" class="text-ink/60"> • {{ assignment.name }}</span>
					</div>
					<div class="type-meta text-ink/60 mt-1">
						<span>{{ assignment?.applicant_name || assignment?.student_applicant }}</span>
						<span v-if="assignment?.school"> • {{ assignment.school }}</span>
						<span v-if="assignment?.program_offering"> • {{ assignment.program_offering }}</span>
					</div>
					<div v-if="assignment?.assigned_to_role" class="type-meta text-ink/60 mt-1">
						Assigned role: {{ assignment.assigned_to_role }}
					</div>
					<div v-if="assignment?.assigned_to_user_name" class="type-meta text-ink/60 mt-1">
						Assigned user: {{ assignment.assigned_to_user_name }}
					</div>
				</div>

				<div class="shrink-0 flex items-center gap-2">
					<button
						v-if="canOpenApplicantWorkspace"
						type="button"
						class="btn btn-quiet"
						@click="openApplicantWorkspace"
					>
						Admissions Workspace
					</button>
					<button v-if="canOpenDesk" type="button" class="btn btn-quiet" @click="openInDesk">
						Open in Desk
					</button>
					<button type="button" class="btn btn-quiet" @click="requestRefresh">Refresh</button>
				</div>
			</div>
		</div>

		<div v-if="assignment?.assigned_to_role" class="card-surface p-4">
			<div class="type-body font-medium">Role queue ownership</div>
			<p class="mt-2 type-meta text-ink/60">
				Any {{ assignment.assigned_to_role }} can complete this review. You can take it or assign
				it.
			</p>
			<div class="mt-3 flex flex-wrap items-center gap-2">
				<button
					type="button"
					class="btn btn-quiet"
					:disabled="busy || !canClaim"
					@click="claimAssignment"
				>
					Take ownership
				</button>
			</div>
			<div class="mt-3 flex flex-wrap items-center gap-2">
				<select
					v-model="reassignToUser"
					class="if-input min-w-[16rem]"
					:disabled="busy || !canReassign"
				>
					<option value="">Assign to user with role</option>
					<option v-for="row in roleCandidates" :key="row.name" :value="row.name">
						{{ row.full_name || row.name }}
					</option>
				</select>
				<button
					type="button"
					class="btn btn-quiet"
					:disabled="busy || !canReassign || !reassignToUser"
					@click="reassignAssignment"
				>
					Assign
				</button>
			</div>
		</div>

		<div v-if="assignment?.preview" class="card-surface p-4">
			<div class="type-body font-medium">Preview</div>
			<div class="mt-2 space-y-2 type-meta text-ink/60">
				<div v-if="assignment.target_type === 'Applicant Document Item'">
					<div>
						Requirement:
						{{ assignment.preview.document_label || assignment.preview.document_type }}
					</div>
					<div v-if="assignment.preview.item_label">
						Submission: {{ assignment.preview.item_label || assignment.preview.item_key }}
					</div>
					<div>Current status: {{ assignment.preview.review_status || 'Pending' }}</div>
					<div v-if="assignment.preview.file_url">
						<button
							type="button"
							class="inline-flex items-center rounded-full border border-slate-200 bg-white px-4 py-2 type-button-label text-ink shadow-sm transition hover:-translate-y-0.5 hover:border-jacaranda hover:text-jacaranda"
							@click="openPreviewFile"
						>
							Open file
						</button>
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
				<label class="block">
					<span class="sr-only">Decision select</span>
					<div
						class="relative rounded-xl border border-line-soft bg-white shadow-sm transition hover:border-jacaranda/60 focus-within:border-jacaranda focus-within:ring-2 focus-within:ring-jacaranda/25"
					>
						<select
							v-model="decision"
							class="w-full appearance-none rounded-xl bg-transparent px-4 py-3 pr-10 text-base text-ink cursor-pointer disabled:cursor-not-allowed disabled:opacity-60"
							:disabled="busy"
						>
							<option value="">Select a decision</option>
							<option v-for="opt in decisionOptions" :key="opt" :value="opt">{{ opt }}</option>
						</select>
						<span
							class="pointer-events-none absolute inset-y-0 right-3 flex items-center text-slate-token/70"
							aria-hidden="true"
						>
							<svg viewBox="0 0 20 20" fill="currentColor" class="h-5 w-5">
								<path
									fill-rule="evenodd"
									d="M5.23 7.21a.75.75 0 0 1 1.06.02L10 11.12l3.71-3.9a.75.75 0 1 1 1.08 1.04l-4.25 4.47a.75.75 0 0 1-1.08 0L5.21 8.27a.75.75 0 0 1 .02-1.06Z"
									clip-rule="evenodd"
								/>
							</svg>
						</span>
					</div>
				</label>
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
					class="inline-flex items-center rounded-full bg-jacaranda px-5 py-2 type-button-label text-white shadow-soft transition hover:-translate-y-0.5 hover:shadow-strong disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0"
					:disabled="busy || submittedOnce"
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
					<div class="type-meta text-ink/60">
						{{ row.reviewer || 'Reviewer' }} • {{ row.decision || '—' }} •
						{{ formatReviewTimestamp(row.decided_on) }}
					</div>
					<div v-if="row.notes" class="type-body mt-1">{{ row.notes }}</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';

import { useOverlayStack } from '@/composables/useOverlayStack';
import { __ } from '@/lib/i18n';
import { createFocusService } from '@/lib/services/focus/focusService';

import type { Response as GetFocusContextResponse } from '@/types/contracts/focus/get_focus_context';
import type { Request as SubmitApplicantReviewAssignmentRequest } from '@/types/contracts/focus/submit_applicant_review_assignment';
import type { Request as ClaimApplicantReviewAssignmentRequest } from '@/types/contracts/focus/claim_applicant_review_assignment';
import type { Request as ReassignApplicantReviewAssignmentRequest } from '@/types/contracts/focus/reassign_applicant_review_assignment';

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
const overlay = useOverlayStack();

const assignment = ref<GetFocusContextResponse['review_assignment'] | null>(null);
const decision = ref('');
const notes = ref('');
const busy = ref(false);
const submittedOnce = ref(false);
const actionError = ref<string | null>(null);
const reassignToUser = ref('');

const targetLabel = computed(() => {
	if (!assignment.value) return __('Applicant review');
	if (assignment.value.target_type === 'Applicant Document Item') return __('Evidence review');
	if (assignment.value.target_type === 'Applicant Health Profile')
		return __('Applicant health review');
	return __('Overall application review');
});

const decisionOptions = computed(() => assignment.value?.decision_options || []);
const previousReviews = computed(() => assignment.value?.previous_reviews || []);
const canClaim = computed(() =>
	Boolean(assignment.value?.can_claim && assignment.value?.assigned_to_role)
);
const canReassign = computed(() =>
	Boolean(assignment.value?.can_reassign && assignment.value?.assigned_to_role)
);
const roleCandidates = computed(() => assignment.value?.role_candidates || []);
const canOpenApplicantWorkspace = computed(() => {
	if (!assignment.value) return false;
	return Boolean(assignment.value.student_applicant);
});

const deskUrl = computed(() => {
	if (!assignment.value) return null;
	if (assignment.value.target_type === 'Applicant Document Item') {
		return `/desk/applicant-document-item/${encodeURIComponent(assignment.value.target_name)}`;
	}
	if (assignment.value.target_type === 'Applicant Health Profile') {
		return `/desk/applicant-health-profile/${encodeURIComponent(assignment.value.target_name)}`;
	}
	return `/desk/student-applicant/${encodeURIComponent(assignment.value.student_applicant)}`;
});
const canOpenDesk = computed(() => Boolean(deskUrl.value));

watch(
	() => props.context,
	next => {
		assignment.value = next.review_assignment ?? null;
		decision.value = '';
		notes.value = '';
		busy.value = false;
		submittedOnce.value = false;
		actionError.value = null;
		reassignToUser.value = '';
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

function openApplicantWorkspace() {
	const studentApplicant = String(assignment.value?.student_applicant || '').trim();
	if (!studentApplicant) return;
	overlay.open('admissions-workspace', {
		mode: 'applicant',
		studentApplicant,
	});
}

function openPreviewFile() {
	const fileUrl = assignment.value?.preview?.file_url;
	if (!fileUrl) return;
	window.open(fileUrl, '_blank', 'noopener');
}

function newClientRequestId(prefix = 'applicant_review') {
	return `${prefix}_${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

function errorMessage(err: unknown): string {
	if (err instanceof Error && err.message) return err.message;
	return __('Please try again.');
}

function resolveAppLocale(): string | undefined {
	if (typeof window === 'undefined') return undefined;
	const globalAny = window as unknown as Record<string, any>;
	const bootLang = String(globalAny.frappe?.boot?.lang || '').trim();
	if (bootLang) return bootLang.replace('_', '-');
	const htmlLang = document.documentElement.lang?.trim();
	if (htmlLang) return htmlLang.replace('_', '-');
	return navigator.languages?.[0] || navigator.language || undefined;
}

function resolveSiteTimeZone(): string | undefined {
	if (typeof window === 'undefined') return undefined;
	const globalAny = window as unknown as Record<string, any>;
	const siteTz = String(globalAny.frappe?.boot?.sysdefaults?.time_zone || '').trim();
	return siteTz || undefined;
}

function parseDateTime(value: string): Date | null {
	const raw = String(value || '').trim();
	if (!raw) return null;
	const normalized = raw.includes('T') ? raw : raw.replace(' ', 'T');
	const parsed = new Date(normalized);
	if (!Number.isNaN(parsed.getTime())) return parsed;
	const fallback = new Date(raw);
	return Number.isNaN(fallback.getTime()) ? null : fallback;
}

function formatReviewTimestamp(value?: string | null): string {
	if (!value) return '—';
	const parsed = parseDateTime(value);
	if (!parsed) return value;

	try {
		const formatter = new Intl.DateTimeFormat(resolveAppLocale(), {
			weekday: 'short',
			day: 'numeric',
			month: 'short',
			hour: '2-digit',
			minute: '2-digit',
			hour12: false,
			timeZone: resolveSiteTimeZone(),
		});
		const parts = formatter.formatToParts(parsed);
		const weekday = parts.find(part => part.type === 'weekday')?.value;
		const day = parts.find(part => part.type === 'day')?.value;
		const month = parts.find(part => part.type === 'month')?.value;
		const hour = parts.find(part => part.type === 'hour')?.value;
		const minute = parts.find(part => part.type === 'minute')?.value;
		if (weekday && day && month && hour && minute) {
			return `${weekday} ${day} ${month} ${hour}:${minute}`;
		}
		return formatter.format(parsed);
	} catch {
		return value;
	}
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

async function claimAssignment() {
	if (busy.value) return;
	actionError.value = null;

	if (!assignment.value?.name) {
		actionError.value = __('Missing assignment context. Please reopen from Focus list.');
		return;
	}
	if (!assignment.value?.assigned_to_role) {
		actionError.value = __('This review is already assigned to a specific user.');
		return;
	}
	if (!canClaim.value) {
		actionError.value = __('You are not allowed to claim this review.');
		return;
	}

	busy.value = true;
	try {
		const payload: ClaimApplicantReviewAssignmentRequest = {
			assignment: assignment.value.name,
			focus_item_id: props.focusItemId || null,
			client_request_id: newClientRequestId('applicant_review_claim'),
		};
		const response = await focusService.claimApplicantReviewAssignment(payload);
		if (!response?.ok) {
			throw new Error(__('Could not claim this review.'));
		}
		requestRefresh();
	} catch (err: unknown) {
		actionError.value = errorMessage(err);
	} finally {
		busy.value = false;
	}
}

async function reassignAssignment() {
	if (busy.value) return;
	actionError.value = null;

	if (!assignment.value?.name) {
		actionError.value = __('Missing assignment context. Please reopen from Focus list.');
		return;
	}
	if (!assignment.value?.assigned_to_role) {
		actionError.value = __('Only role-queue reviews can be reassigned here.');
		return;
	}
	if (!canReassign.value) {
		actionError.value = __('You are not allowed to reassign this review.');
		return;
	}
	if (!reassignToUser.value) {
		actionError.value = __('Select a user before assigning.');
		return;
	}

	busy.value = true;
	try {
		const payload: ReassignApplicantReviewAssignmentRequest = {
			assignment: assignment.value.name,
			reassign_to_user: reassignToUser.value,
			focus_item_id: props.focusItemId || null,
			client_request_id: newClientRequestId('applicant_review_reassign'),
		};
		const response = await focusService.reassignApplicantReviewAssignment(payload);
		if (!response?.ok) {
			throw new Error(__('Could not reassign this review.'));
		}
		reassignToUser.value = '';
		emit('done');
	} catch (err: unknown) {
		actionError.value = errorMessage(err);
	} finally {
		busy.value = false;
	}
}
</script>
