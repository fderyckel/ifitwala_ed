<!-- ifitwala_ed/ui-spa/src/components/focus/StaffPolicyAcknowledgeAction.vue -->
<template>
	<div class="space-y-4">
		<div class="card-surface p-4">
			<div class="flex items-start justify-between gap-3">
				<div class="min-w-0">
					<div class="type-body font-medium">
						Policy
						<span v-if="policy?.policy_version" class="text-muted">
							• {{ policy.policy_version }}</span
						>
					</div>
					<div class="type-meta text-muted mt-1">
						<span>{{ policyTitle }}</span>
						<span v-if="policy?.version_label"> • Version {{ policy.version_label }}</span>
					</div>
					<div v-if="scopeLabel" class="type-meta text-muted mt-1">
						{{ scopeLabel }}
					</div>
					<div v-if="policy?.employee_name || policy?.employee" class="type-meta text-muted mt-1">
						Employee: {{ policy?.employee_name || policy?.employee }}
					</div>
					<div v-if="policy?.todo_due_date" class="type-meta text-muted mt-1">
						Due: {{ policy.todo_due_date }}
					</div>
					<div
						v-if="policy?.is_acknowledged && policy?.acknowledged_at"
						class="type-meta text-muted mt-1"
					>
						Already acknowledged on {{ policy.acknowledged_at }}
					</div>
				</div>

				<div class="shrink-0 flex items-center gap-2">
					<button
						v-if="policy?.policy_version"
						type="button"
						class="btn btn-quiet"
						@click="openInDesk(policy.policy_version)"
					>
						Open in Desk
					</button>
					<button type="button" class="btn btn-quiet" @click="requestRefresh">Refresh</button>
				</div>
			</div>
		</div>

		<div class="card-surface p-4">
			<div class="type-body font-medium">Policy text</div>
			<div class="type-meta text-muted mt-1">Review this policy version before acknowledging.</div>

			<div class="mt-3 rounded-xl border border-ink/10 bg-white p-3">
				<div
					v-if="policy?.policy_text_html"
					class="prose prose-sm max-w-none text-ink"
					v-html="trustedHtml(policy.policy_text_html)"
				/>
				<p v-else class="type-meta text-muted">No policy text is available for this version.</p>
			</div>

			<div v-if="actionError" class="mt-3 rounded-xl border border-ink/10 bg-white p-3">
				<p class="type-meta text-ink">{{ actionError }}</p>
			</div>

			<div class="mt-4 flex items-center justify-end gap-2">
				<button type="button" class="btn btn-quiet" @click="emitClose">Close</button>
				<button
					type="button"
					class="btn btn-primary"
					:disabled="busy || submittedOnce || !canAcknowledge"
					@click="acknowledgePolicy"
				>
					{{ busy ? 'Saving…' : 'Acknowledge policy' }}
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
import type { Request as AcknowledgeStaffPolicyRequest } from '@/types/contracts/focus/acknowledge_staff_policy';

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

const policy = ref<GetFocusContextResponse['policy_signature']>(null);
const busy = ref(false);
const submittedOnce = ref(false);
const actionError = ref<string | null>(null);

const policyTitle = computed(() => {
	return (
		(policy.value?.policy_label || '').trim() ||
		(policy.value?.policy_title || '').trim() ||
		(policy.value?.policy_key || '').trim() ||
		(policy.value?.policy_version || '').trim() ||
		__('Policy')
	);
});

const scopeLabel = computed(() => {
	const parts = [];
	const org = (policy.value?.policy_organization || '').trim();
	const school = (policy.value?.policy_school || '').trim();
	if (org) parts.push(`Organization: ${org}`);
	if (school) parts.push(`School: ${school}`);
	return parts.join(' • ');
});

const canAcknowledge = computed(() => {
	return Boolean(policy.value?.policy_version) && !policy.value?.is_acknowledged;
});

watch(
	() => props.context,
	next => {
		policy.value = next.policy_signature ?? null;
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

function trustedHtml(html: string): string {
	return String(html || '');
}

function deskRouteSlug(doctype: string) {
	return String(doctype || '')
		.trim()
		.toLowerCase()
		.replace(/_/g, ' ')
		.replace(/[^a-z0-9]+/g, '-')
		.replace(/^-+|-+$/g, '');
}

function openInDesk(name: string) {
	const safeName = String(name || '').trim();
	if (!safeName) return;
	const routeDoctype = deskRouteSlug('Policy Version');
	window.open(
		`/desk/${encodeURIComponent(routeDoctype)}/${encodeURIComponent(safeName)}`,
		'_blank',
		'noopener'
	);
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

async function acknowledgePolicy() {
	if (busy.value || submittedOnce.value) return;
	actionError.value = null;

	const focusItemId = requireFocusItemId();
	if (!focusItemId) return;

	if (!canAcknowledge.value) {
		actionError.value = policy.value?.is_acknowledged
			? __('This policy has already been acknowledged.')
			: __('Policy acknowledgement is not available for this item.');
		return;
	}

	busy.value = true;
	submittedOnce.value = true;
	try {
		const payload: AcknowledgeStaffPolicyRequest = {
			focus_item_id: focusItemId,
			client_request_id: newClientRequestId('policy_ack'),
		};
		const response = await focusService.acknowledgeStaffPolicy(payload);
		if (!response?.ok) throw new Error(__('Unable to acknowledge policy.'));
		emit('done');
	} catch (err: unknown) {
		submittedOnce.value = false;
		actionError.value = errorMessage(err);
	} finally {
		busy.value = false;
	}
}
</script>
