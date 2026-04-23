<!-- ifitwala_ed/ui-spa/src/components/focus/StudentLogFollowUpAction.vue -->
<!--
  StudentLogFollowUpAction.vue
  Handles the "Follow-up" workflow actions for a Student Log (submit, review, reassign, complete).
  Embedded within the FocusRouterOverlay context.

  Used by:
  - FocusRouterOverlay.vue
-->
<template>
	<div class="space-y-4">
		<!-- ============================================================
         CONTEXT HEADER (small)
         - FocusRouterOverlay owns the main header.
         - This component shows workflow-specific context + actions.
       ============================================================ -->
		<div class="card-surface p-4">
			<div class="flex items-start justify-between gap-3">
				<div class="min-w-0">
					<div class="type-body font-medium">
						Student Log
						<span v-if="log?.name" class="text-ink/60"> • {{ log.name }}</span>
					</div>

					<div class="type-meta text-ink/60 mt-1">
						<span v-if="log?.student_name">{{ log.student_name }}</span>
						<span v-if="log?.log_type"> • {{ log.log_type }}</span>
						<span v-if="logTimestampLabel"> • {{ logTimestampLabel }}</span>
					</div>

					<div v-if="log?.follow_up_status" class="type-meta text-ink/60 mt-1">
						Status: {{ log.follow_up_status }}
					</div>
				</div>

				<div class="shrink-0 flex items-center gap-2">
					<button
						v-if="log?.name"
						type="button"
						class="if-action"
						@click="openInDesk('Student Log', log.name)"
					>
						Open in Desk
					</button>

					<!-- Advisory: does NOT block closing or workflows -->
					<button type="button" class="if-action" @click="requestRefresh">Refresh</button>
				</div>
			</div>

			<div v-if="log?.log_html" class="mt-3">
				<div class="type-meta text-ink/60 mb-1">Log note</div>
				<div class="prose prose-sm max-w-none" v-html="trustedHtml(log.log_html)" />
			</div>
		</div>

		<!-- ============================================================
         FOLLOW-UPS LIST (both modes)
       ============================================================ -->
		<div class="card-surface p-4">
			<div class="type-body font-medium">Follow-ups</div>

			<div v-if="loading" class="type-body text-ink/60 mt-3">Loading…</div>

			<div v-else-if="followUps.length === 0" class="type-body text-ink/60 mt-3">
				No follow-ups yet.
			</div>

			<div v-else class="mt-3 space-y-3">
				<div v-for="fu in followUps" :key="fu.name" class="rounded-xl border border-ink/10 p-3">
					<div class="flex items-start justify-between gap-3">
						<div class="min-w-0">
							<div class="type-meta text-ink/60">
								<span v-if="fu.follow_up_author">{{ fu.follow_up_author }}</span>
								<span v-if="fu.date"> • {{ followUpDateLabel(fu.date) }}</span>
								<span v-if="fu.docstatus === 0"> • Draft</span>
								<span v-else> • Submitted</span>
							</div>
						</div>

						<button
							type="button"
							class="if-action"
							@click="openInDesk('Student Log Follow Up', fu.name)"
						>
							Open
						</button>
					</div>

					<div
						v-if="fu.follow_up_html"
						class="mt-2 prose prose-sm max-w-none"
						v-html="trustedHtml(fu.follow_up_html)"
					/>
				</div>
			</div>
		</div>

		<!-- ============================================================
         MODE: ASSIGNEE (submit follow-up)
       ============================================================ -->
		<div v-if="modeState === 'assignee'" class="card-surface p-4">
			<div class="type-body font-medium">Your follow-up</div>
			<div class="type-meta text-ink/60 mt-1">
				Write what you did, what happened, and any next action.
			</div>

			<div class="mt-3">
				<textarea
					v-model="draftText"
					class="if-textarea w-full"
					rows="8"
					placeholder="Type your follow-up…"
					:disabled="busy"
				/>
				<div class="type-meta text-ink/60 mt-2">
					Keep it factual and actionable. No sensitive details beyond what’s necessary.
				</div>
				<div v-if="draftText.trim().length > 0 && !canSubmit" class="type-meta text-ink/60 mt-2">
					Please write at least 5 characters.
				</div>
			</div>

			<!-- Inline error (A+): overlays/workflow UI do not toast -->
			<div v-if="actionError" class="mt-3 rounded-xl border border-ink/10 bg-white p-3">
				<p class="type-meta text-ink">{{ actionError }}</p>
			</div>

			<div class="mt-4 flex items-center justify-end gap-2">
				<!-- A+: close must NEVER be blocked by busy -->
				<button type="button" class="if-button if-button--quiet" @click="emitClose">Cancel</button>

				<button
					type="button"
					class="if-button if-button--primary"
					:disabled="busy || submittedOnce || !canSubmit"
					@click="submitFollowUp"
				>
					{{ busy ? 'Submitting…' : 'Submit follow-up' }}
				</button>
			</div>
		</div>

		<!-- ============================================================
         MODE: AUTHOR (review outcome)
       ============================================================ -->
		<div v-else-if="modeState === 'author'" class="card-surface p-4">
			<div class="type-body font-medium">Review outcome</div>
			<div class="type-meta text-ink/60 mt-1">
				Decide whether to close the log, or reassign follow-up.
			</div>

			<!-- Reassign -->
			<div class="mt-4">
				<div class="type-meta text-ink/60 mb-1">Reassign to</div>
				<input
					v-model="reassignSearchQuery"
					class="if-input w-full"
					type="text"
					placeholder="Type a full name, user ID, or email"
					:disabled="busy"
				/>
				<div class="type-meta text-ink/60 mt-2">
					Search by the employee's full name, user ID, or email.
				</div>
				<div v-if="reassignSearchLoading" class="type-meta text-ink/60 mt-2">Searching…</div>
				<div
					v-if="reassignSearchQuery.trim().length > 0 && reassignSearchQuery.trim().length < 2"
					class="type-meta text-ink/60 mt-2"
				>
					Type at least 2 letters to search by full name.
				</div>
				<div
					v-else-if="
						reassignSearchQuery.trim().length >= 2 &&
						!reassignSearchLoading &&
						reassignCandidates.length === 0
					"
					class="type-meta text-ink/60 mt-2"
				>
					No matching staff found. Keep typing a name, or enter a full user ID / email.
				</div>
				<div
					v-if="reassignCandidates.length"
					class="mt-3 overflow-hidden rounded-xl border border-ink/10"
				>
					<button
						v-for="candidate in reassignCandidates"
						:key="candidate.value"
						type="button"
						class="flex w-full items-center justify-between gap-3 border-b border-ink/10 px-3 py-3 text-left transition last:border-b-0 hover:bg-surface-soft"
						@click="selectReassignCandidate(candidate.value, candidate.label)"
					>
						<div class="min-w-0">
							<div class="type-body font-medium truncate">{{ candidate.label }}</div>
							<div v-if="candidate.meta" class="type-meta text-ink/60 truncate">
								{{ candidate.meta }}
							</div>
						</div>
						<div
							v-if="resolvedReassignTarget === candidate.value"
							class="type-meta text-ink/60 shrink-0"
						>
							Selected
						</div>
					</button>
				</div>
				<div v-if="reassignSelectedUserId" class="type-meta text-ink/60 mt-2">
					Selected:
					<span class="text-ink">{{ reassignSelectedLabel || reassignSelectedUserId }}</span>
					<span v-if="reassignSelectedLabel && reassignSelectedLabel !== reassignSelectedUserId">
						• {{ reassignSelectedUserId }}
					</span>
				</div>

				<!-- Inline error (A+): overlays/workflow UI do not toast -->
				<div v-if="actionError" class="mt-3 rounded-xl border border-ink/10 bg-white p-3">
					<p class="type-meta text-ink">{{ actionError }}</p>
				</div>

				<div class="mt-3 flex items-center justify-end gap-2">
					<!-- A+: close must NEVER be blocked by busy -->
					<button type="button" class="if-button if-button--quiet" @click="emitClose">
						Close
					</button>

					<button
						type="button"
						class="if-button if-button--primary"
						:disabled="busy || submittedOnce || resolvedReassignTarget.length < 3"
						@click="reassignFollowUp"
					>
						{{ busy ? 'Processing…' : 'Reassign follow-up' }}
					</button>
				</div>
			</div>

			<!-- Complete -->
			<div class="mt-6 border-t border-ink/10 pt-4">
				<div class="type-meta text-ink/60">
					If you’re satisfied with the outcome, complete the log.
				</div>

				<div class="mt-3 flex items-center justify-end gap-2">
					<button
						type="button"
						class="if-button if-button--primary"
						:disabled="busy || submittedOnce || !canComplete"
						@click="completeParentLog"
					>
						{{ busy ? 'Completing…' : 'Complete log' }}
					</button>
				</div>

				<div v-if="!canComplete" class="type-meta text-ink/60 mt-2">
					This is disabled if the log is already Completed.
				</div>
			</div>
		</div>

		<!-- ============================================================
         FALLBACK (unknown mode)
       ============================================================ -->
		<div v-else class="rounded-2xl border border-slate-200 bg-white p-5">
			<p class="type-body-strong text-ink">Not supported yet</p>
			<p class="mt-2 type-body text-slate-token/75">
				Unknown Student Log focus mode: <span class="type-meta">{{ modeState }}</span>
			</p>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';

import { formatHumanDateTimeFields } from '@/lib/datetime';
import { __ } from '@/lib/i18n';
import { createFocusService } from '@/lib/services/focus/focusService';
import { createStudentLogService } from '@/lib/services/studentLog/studentLogService';

import type { Response as GetFocusContextResponse } from '@/types/contracts/focus/get_focus_context';
import type { Request as SubmitStudentLogFollowUpRequest } from '@/types/contracts/focus/submit_student_log_follow_up';
import type { Request as ReviewStudentLogOutcomeRequest } from '@/types/contracts/focus/review_student_log_outcome';
import type { Response as SearchFollowUpUsersResponse } from '@/types/contracts/student_log/search_follow_up_users';

type Mode = 'assignee' | 'author';

type FocusLog = GetFocusContextResponse['log'];
type FocusFollowUp = GetFocusContextResponse['follow_ups'][number];

const props = defineProps<{
	focusItemId?: string | null;
	context: GetFocusContextResponse;
}>();

const emit = defineEmits<{
	(e: 'close'): void;
	(e: 'done'): void;
	(e: 'request-refresh'): void;
}>();

/**
 * Service layer:
 * - owns createResource + dotted endpoints
 * - returns contract payloads (transport unwrapping is in resources/frappe.ts)
 * - owns uiSignals emission (A+)
 */
const focusService = createFocusService();
const studentLogService = createStudentLogService();

function emitClose() {
	emit('close');
}

function requestRefresh() {
	emit('request-refresh');
}

/**
 * Local view state (derived from props.context)
 * - no auto-fetch here (router is source of truth)
 */
const modeState = ref<Mode>('assignee');
const log = ref<FocusLog | null>(null);
const followUps = ref<FocusFollowUp[]>([]);
const loading = ref(false); // reserved: router can later drive a prop if desired

// A+ UX guards (NEVER block closing)
const busy = ref(false);
const submittedOnce = ref(false);

const draftText = ref('');
const reassignSearchQuery = ref('');
const reassignSelectedUserId = ref('');
const reassignSelectedLabel = ref('');
const reassignCandidates = ref<SearchFollowUpUsersResponse>([]);
const reassignSearchLoading = ref(false);

// A+ inline errors (no toast)
const actionError = ref<string | null>(null);

const activeStudentLogName = computed(() => log.value?.name || null);
const logTimestampLabel = computed(() =>
	formatHumanDateTimeFields(log.value?.date, log.value?.time, {
		fallback: String(log.value?.date || '').trim(),
	})
);

const canSubmit = computed(() => {
	return !!activeStudentLogName.value && (draftText.value || '').trim().length >= 5;
});

const canComplete = computed(() => {
	const s = String(log.value?.follow_up_status || '').toLowerCase();
	return !!activeStudentLogName.value && s !== 'completed';
});

const resolvedReassignTarget = computed(() => {
	return (reassignSelectedUserId.value || reassignSearchQuery.value || '').trim();
});

let reassignSearchRequestSeq = 0;

function applyContext(ctx: GetFocusContextResponse) {
	log.value = ctx.log;
	followUps.value = ctx.follow_ups;
	modeState.value = ctx.mode;
}

watch(
	() => props.context,
	next => {
		// reset action inputs on context change (prevents stale drafts)
		draftText.value = '';
		reassignSearchQuery.value = '';
		reassignSelectedUserId.value = '';
		reassignSelectedLabel.value = '';
		reassignCandidates.value = [];
		reassignSearchLoading.value = false;
		submittedOnce.value = false;
		actionError.value = null;
		applyContext(next);
		if (next.mode === 'author') {
			void loadReassignCandidates('');
		}
	},
	{ immediate: true, deep: false }
);

watch(reassignSearchQuery, nextValue => {
	const query = String(nextValue || '').trim();
	if (
		reassignSelectedUserId.value &&
		query &&
		query === String(reassignSelectedLabel.value || reassignSelectedUserId.value).trim()
	) {
		reassignCandidates.value = [];
		reassignSearchLoading.value = false;
		return;
	}

	reassignSelectedUserId.value = '';
	reassignSelectedLabel.value = '';

	if (!query) {
		void loadReassignCandidates('');
		return;
	}
	if (query.length < 2) {
		reassignCandidates.value = [];
		reassignSearchLoading.value = false;
		return;
	}
	void loadReassignCandidates(query);
});

/* Helpers ------------------------------------------------------ */
function newClientRequestId(prefix = 'req') {
	return `${prefix}_${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

function deskRouteSlug(doctype: string) {
	return String(doctype || '')
		.trim()
		.toLowerCase()
		.replace(/_/g, ' ')
		.replace(/[^a-z0-9]+/g, '-')
		.replace(/^-+|-+$/g, '');
}

function openInDesk(doctype: string, name: string) {
	// leaving SPA intentionally (Desk route)
	const safeDoctype = String(doctype || '').trim();
	const safeName = String(name || '').trim();
	const routeDoctype = deskRouteSlug(safeDoctype);
	if (!routeDoctype || !safeName) return;

	// Desk v16 route shape is /desk/<doctype-slug>/<name>.
	window.open(
		`/desk/${encodeURIComponent(routeDoctype)}/${encodeURIComponent(safeName)}`,
		'_blank',
		'noopener'
	);
}

function trustedHtml(html: string) {
	return html || '';
}

function followUpDateLabel(dateValue?: string | null) {
	return formatHumanDateTimeFields(dateValue, null, {
		fallback: String(dateValue || '').trim(),
	});
}

function requireFocusItemId(): string | null {
	const id = String(props.focusItemId || '').trim();
	if (!id) {
		actionError.value = __(
			'Missing focus item. Please close and reopen this item from the Focus list.'
		);
		return null;
	}
	return id;
}

/**
 * Advisory signal for router:
 * - Router owns closing the overlay.
 * - This component must not toast / signal / refetch.
 */
function aPlusSuccessDoneOnly() {
	try {
		emit('done');
	} catch {
		// never block UX
	}
}

function errorMessage(err: unknown): string {
	if (err instanceof Error && err.message) return err.message;
	return __('Please try again.');
}

async function loadReassignCandidates(query: string) {
	const student = String(log.value?.student || '').trim();
	const nextStep = String(log.value?.next_step || '').trim();
	if (modeState.value !== 'author' || !student || !nextStep) {
		reassignCandidates.value = [];
		reassignSearchLoading.value = false;
		return;
	}

	const requestSeq = ++reassignSearchRequestSeq;
	reassignSearchLoading.value = true;
	actionError.value = null;

	try {
		const candidates = await studentLogService.searchFollowUpUsers({
			next_step: nextStep,
			student,
			query,
			limit: 20,
		});
		if (requestSeq !== reassignSearchRequestSeq) return;
		reassignCandidates.value = candidates || [];
	} catch (err: unknown) {
		if (requestSeq !== reassignSearchRequestSeq) return;
		reassignCandidates.value = [];
		actionError.value =
			err instanceof Error && err.message
				? err.message
				: __('Could not search staff. Try typing a full user ID / email instead.');
	} finally {
		if (requestSeq === reassignSearchRequestSeq) {
			reassignSearchLoading.value = false;
		}
	}
}

function selectReassignCandidate(userId: string, label: string) {
	actionError.value = null;
	reassignSelectedUserId.value = String(userId || '').trim();
	reassignSelectedLabel.value = String(label || userId || '').trim();
	reassignCandidates.value = [];
	reassignSearchQuery.value = reassignSelectedLabel.value || reassignSelectedUserId.value;
}

/* Actions ------------------------------------------------------ */
async function submitFollowUp() {
	if (busy.value || submittedOnce.value) return;
	if (modeState.value !== 'assignee') return;
	if (!canSubmit.value) return;

	actionError.value = null;

	const focusItemId = requireFocusItemId();
	if (!focusItemId) return;

	const followUpText = (draftText.value || '').trim();
	if (followUpText.length < 5) return;

	busy.value = true;
	submittedOnce.value = true;

	try {
		const payload: SubmitStudentLogFollowUpRequest = {
			focus_item_id: focusItemId,
			follow_up: followUpText,
			client_request_id: newClientRequestId('fu'),
		};

		const msg = await focusService.submitStudentLogFollowUp(payload);
		if (!msg?.ok) throw new Error(__('Submit failed.'));

		// A+ success: overlay closes immediately (via router)
		aPlusSuccessDoneOnly();
	} catch (e: unknown) {
		submittedOnce.value = false;
		actionError.value = errorMessage(e);
	} finally {
		busy.value = false;
	}
}

async function reassignFollowUp() {
	if (busy.value || submittedOnce.value) return;
	if (modeState.value !== 'author') return;

	actionError.value = null;

	const focusItemId = requireFocusItemId();
	if (!focusItemId) return;

	const target = resolvedReassignTarget.value;
	if (target.length < 3) {
		actionError.value = __('Please select a valid staff member or enter a full user ID / email.');
		return;
	}

	busy.value = true;
	submittedOnce.value = true;

	try {
		const payload: ReviewStudentLogOutcomeRequest = {
			focus_item_id: focusItemId,
			decision: 'reassign',
			follow_up_person: target,
			client_request_id: newClientRequestId('rvw'),
		};

		const msg = await focusService.reviewStudentLogOutcome(payload);
		if (!msg?.ok) throw new Error(__('Reassign failed.'));

		// A+ success: overlay closes immediately (via router)
		aPlusSuccessDoneOnly();
	} catch (e: unknown) {
		submittedOnce.value = false;
		actionError.value = errorMessage(e);
	} finally {
		busy.value = false;
	}
}

async function completeParentLog() {
	if (busy.value || submittedOnce.value) return;
	if (modeState.value !== 'author') return;
	if (!canComplete.value) return;

	actionError.value = null;

	const focusItemId = requireFocusItemId();
	if (!focusItemId) return;

	busy.value = true;
	submittedOnce.value = true;

	try {
		const payload: ReviewStudentLogOutcomeRequest = {
			focus_item_id: focusItemId,
			decision: 'complete',
			client_request_id: newClientRequestId('rvw'),
		};

		const msg = await focusService.reviewStudentLogOutcome(payload);
		if (!msg?.ok) throw new Error(__('Complete failed.'));

		// A+ success: overlay closes immediately (via router)
		aPlusSuccessDoneOnly();
	} catch (e: unknown) {
		submittedOnce.value = false;
		actionError.value = errorMessage(e);
	} finally {
		busy.value = false;
	}
}
</script>
