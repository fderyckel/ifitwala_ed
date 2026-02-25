<!-- ifitwala_ed/ui-spa/src/components/focus/InquiryFollowUpAction.vue -->
<template>
	<div class="space-y-4">
		<div class="card-surface p-4">
			<div class="flex items-start justify-between gap-3">
				<div class="min-w-0">
					<div class="type-body font-medium">
						Inquiry <span v-if="inquiry?.name" class="text-muted"> • {{ inquiry?.name }}</span>
					</div>
					<div class="type-meta text-muted mt-1">
						<span>{{ subjectName }}</span>
						<span v-if="inquiry?.school"> • {{ inquiry?.school }}</span>
						<span v-else-if="inquiry?.organization"> • {{ inquiry?.organization }}</span>
					</div>
					<div v-if="inquiry?.type_of_inquiry" class="type-meta text-muted mt-1">
						Type: {{ inquiry?.type_of_inquiry }}
					</div>
					<div v-if="inquiry?.followup_due_on" class="type-meta text-muted mt-1">
						Due: {{ inquiry?.followup_due_on }}
					</div>
					<div v-if="inquiry?.sla_status" class="type-meta text-muted mt-1">
						SLA: {{ inquiry?.sla_status }}
					</div>
				</div>

				<div class="shrink-0 flex items-center gap-2">
					<button
						v-if="inquiry?.name"
						type="button"
						class="btn btn-quiet"
						@click="openInDesk(inquiry.name)"
					>
						Open in Desk
					</button>
					<button type="button" class="btn btn-quiet" @click="requestRefresh">Refresh</button>
				</div>
			</div>
		</div>

		<div class="card-surface p-4">
			<div class="type-body font-medium">First contact action</div>
			<div class="type-meta text-muted mt-1">
				Mark this inquiry as contacted and close your follow-up ToDo.
			</div>

			<div v-if="!canMarkContacted" class="type-meta text-muted mt-3">
				Only assigned inquiries in state <b>Assigned</b> can be completed from Focus.
			</div>

			<div v-if="actionError" class="mt-3 rounded-xl border border-ink/10 bg-white p-3">
				<p class="type-meta text-ink">{{ actionError }}</p>
			</div>

			<div class="mt-4 flex items-center justify-end gap-2">
				<button type="button" class="btn btn-quiet" @click="emitClose">Close</button>
				<button
					type="button"
					class="btn btn-primary"
					:disabled="busy || submittedOnce || !canMarkContacted"
					@click="markContacted"
				>
					{{ busy ? 'Saving…' : 'Mark contacted' }}
				</button>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';

import { __ } from '@/lib/i18n';
import { createFocusService } from '@/lib/services/focus/focusService';

import type { Response as GetFocusContextResponse } from '@/types/contracts/focus/get_focus_context';
import type { Request as MarkInquiryContactedRequest } from '@/types/contracts/focus/mark_inquiry_contacted';

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

const inquiry = ref<GetFocusContextResponse['inquiry']>(null);
const busy = ref(false);
const submittedOnce = ref(false);
const actionError = ref<string | null>(null);

const subjectName = computed(() => {
	const value = (inquiry.value?.subject_name || '').trim();
	return value || inquiry.value?.name || __('Inquiry');
});

const canMarkContacted = computed(() => {
	return inquiry.value?.workflow_state === 'Assigned';
});

watch(
	() => props.context,
	next => {
		inquiry.value = next.inquiry ?? null;
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

function openInDesk(name: string) {
	const safeName = String(name || '').trim();
	if (!safeName) return;
	window.open(`/desk/inquiry/${encodeURIComponent(safeName)}`, '_blank', 'noopener');
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

function newClientRequestId(prefix = 'req') {
	return `${prefix}_${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

function errorMessage(err: unknown): string {
	if (err instanceof Error && err.message) return err.message;
	return __('Please try again.');
}

async function markContacted() {
	if (busy.value || submittedOnce.value) return;

	actionError.value = null;

	if (!canMarkContacted.value) {
		actionError.value = __('This inquiry cannot be marked as contacted from Focus yet.');
		return;
	}

	const focusItemId = requireFocusItemId();
	if (!focusItemId) return;

	busy.value = true;
	submittedOnce.value = true;

	try {
		const payload: MarkInquiryContactedRequest = {
			focus_item_id: focusItemId,
			complete_todo: 1,
			client_request_id: newClientRequestId('inquiry'),
		};

		const response = await focusService.markInquiryContacted(payload);
		if (!response?.ok) throw new Error(__('Could not update inquiry status.'));

		emit('done');
	} catch (err: unknown) {
		submittedOnce.value = false;
		actionError.value = errorMessage(err);
	} finally {
		busy.value = false;
	}
}
</script>
