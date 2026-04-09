<!-- ifitwala_ed/ui-spa/src/components/focus/InquiryFollowUpAction.vue -->
<template>
	<div class="space-y-4">
		<div class="card-surface p-4">
			<div class="flex items-start justify-between gap-3">
				<div class="min-w-0">
					<div class="type-body font-medium">
						Inquiry <span v-if="inquiry?.name" class="text-ink/60"> • {{ inquiry?.name }}</span>
					</div>
					<div class="type-meta text-ink/60 mt-1">
						<span>{{ subjectName }}</span>
						<span v-if="inquiry?.school"> • {{ inquiry?.school }}</span>
						<span v-else-if="inquiry?.organization"> • {{ inquiry?.organization }}</span>
					</div>
					<div v-if="inquiry?.type_of_inquiry" class="type-meta text-ink/60 mt-1">
						Type: {{ inquiry?.type_of_inquiry }}
					</div>
					<div v-if="inquiry?.followup_due_on" class="type-meta text-ink/60 mt-1">
						Due: {{ formatLocalizedDate(inquiry?.followup_due_on, { includeWeekday: true }) }}
					</div>
					<div v-if="inquiry?.sla_status" class="type-meta text-ink/60 mt-1">
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

		<div class="card-surface p-4 space-y-4">
			<div class="flex items-start justify-between gap-3">
				<div>
					<div class="type-body font-medium">Inquiry details</div>
					<div class="type-meta text-ink/60 mt-1">
						Review the original inquiry before recording first contact.
					</div>
				</div>
				<div class="shrink-0 flex items-center gap-2">
					<button
						v-if="inquiry?.contact"
						type="button"
						class="btn btn-quiet"
						@click="openContactInDesk(inquiry.contact)"
					>
						Open contact
					</button>
					<button
						v-else
						type="button"
						class="btn btn-quiet"
						:disabled="contactBusy"
						@click="createContact"
					>
						{{ contactBusy ? 'Creating…' : 'Create contact' }}
					</button>
				</div>
			</div>

			<div class="grid gap-4 md:grid-cols-2">
				<div class="space-y-3">
					<div>
						<div class="type-meta text-ink/60">Name</div>
						<div class="type-body mt-1">{{ subjectName }}</div>
					</div>
					<div v-if="inquiry?.email">
						<div class="type-meta text-ink/60">Email</div>
						<a
							:href="`mailto:${inquiry.email}`"
							class="type-body mt-1 inline-flex text-canopy underline-offset-2 hover:underline"
						>
							{{ inquiry.email }}
						</a>
					</div>
					<div v-if="inquiry?.phone_number">
						<div class="type-meta text-ink/60">Phone</div>
						<a
							:href="`tel:${inquiry.phone_number}`"
							class="type-body mt-1 inline-flex text-canopy underline-offset-2 hover:underline"
						>
							{{ inquiry.phone_number }}
						</a>
					</div>
					<div>
						<div class="type-meta text-ink/60">Contact</div>
						<div class="type-body mt-1">
							{{ inquiry?.contact || 'No linked contact yet' }}
						</div>
					</div>
				</div>

				<div class="space-y-2">
					<div class="type-meta text-ink/60">Message</div>
					<div class="rounded-xl border border-ink/10 bg-white px-4 py-3">
						<p v-if="inquiry?.message" class="type-body whitespace-pre-wrap text-ink">
							{{ inquiry.message }}
						</p>
						<p v-else class="type-meta text-ink/60">No message provided.</p>
					</div>
				</div>
			</div>

			<div v-if="contactNotice" class="rounded-xl border border-ink/10 bg-white p-3">
				<p class="type-meta text-ink">{{ contactNotice }}</p>
			</div>

			<div v-if="contactError" class="rounded-xl border border-ink/10 bg-white p-3">
				<p class="type-meta text-ink">{{ contactError }}</p>
			</div>
		</div>

		<div class="card-surface p-4">
			<div class="type-body font-medium">First contact action</div>
			<div class="type-meta text-ink/60 mt-1">
				Mark this inquiry as contacted and close your follow-up ToDo.
			</div>

			<div v-if="!canMarkContacted" class="type-meta text-ink/60 mt-3">
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

import { formatLocalizedDate } from '@/lib/datetime';
import { __ } from '@/lib/i18n';
import { createFocusService } from '@/lib/services/focus/focusService';

import type { Response as GetFocusContextResponse } from '@/types/contracts/focus/get_focus_context';
import type { Request as CreateInquiryContactRequest } from '@/types/contracts/focus/create_inquiry_contact';
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
const contactBusy = ref(false);
const contactError = ref<string | null>(null);
const contactNotice = ref<string | null>(null);

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
		contactBusy.value = false;
		contactError.value = null;
		contactNotice.value = null;
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

function openContactInDesk(name: string) {
	const safeName = String(name || '').trim();
	if (!safeName) return;
	window.open(`/desk/contact/${encodeURIComponent(safeName)}`, '_blank', 'noopener');
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

async function createContact() {
	if (contactBusy.value || inquiry.value?.contact) return;

	contactError.value = null;
	contactNotice.value = null;

	const focusItemId = String(props.focusItemId || '').trim();
	if (!focusItemId) {
		contactError.value = __(
			'Missing focus item. Please close and reopen this item from the Focus list.'
		);
		return;
	}

	contactBusy.value = true;
	try {
		const payload: CreateInquiryContactRequest = {
			focus_item_id: focusItemId,
		};
		const response = await focusService.createInquiryContact(payload);
		if (inquiry.value) {
			inquiry.value = {
				...inquiry.value,
				contact: response.contact_name,
			};
		}
		contactNotice.value =
			response.status === 'already_linked'
				? __('Contact already linked: {0}', [response.contact_name])
				: __('Contact linked: {0}', [response.contact_name]);
		requestRefresh();
	} catch (err: unknown) {
		contactError.value = errorMessage(err);
	} finally {
		contactBusy.value = false;
	}
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
