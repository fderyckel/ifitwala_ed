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
						Signer: {{ expectedSignerLabel }}
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
			<div class="type-meta text-muted mt-1">
				Review this policy version carefully before signing.
			</div>

			<div class="mt-3 rounded-xl border border-ink/10 bg-white p-3 max-h-80 overflow-auto">
				<div
					v-if="policy?.policy_text_html"
					class="prose prose-sm max-w-none text-ink"
					v-html="trustedHtml(policy.policy_text_html)"
				/>
				<p v-else class="type-meta text-muted">No policy text is available for this version.</p>
			</div>
		</div>

		<div class="card-surface p-4">
			<div class="type-body font-medium">Electronic signature</div>
			<p class="type-meta text-muted mt-1">
				To sign, type your full name exactly as recorded and confirm the legal attestation.
			</p>

			<div class="mt-3 rounded-xl border border-ink/10 bg-white p-3 space-y-3">
				<div class="type-caption text-ink/70">
					Expected signer name:
					<span class="type-body-strong text-ink">{{ expectedSignerLabel }}</span>
				</div>

				<label class="block space-y-1">
					<span class="type-caption text-ink/70">Type full name as electronic signature</span>
					<input
						v-model="typedSignatureName"
						type="text"
						class="if-input w-full"
						placeholder="Enter your full name"
						:disabled="busy || policy?.is_acknowledged"
						@input="signatureTouched = true"
					/>
				</label>

				<p
					v-if="signatureTouched && typedSignatureName.trim() && !isTypedSignatureMatch"
					class="type-meta text-ink"
				>
					Typed signature must match exactly: {{ expectedSignerLabel }}
				</p>

				<label class="flex items-start gap-2">
					<input
						v-model="attestationConfirmed"
						type="checkbox"
						class="mt-1 h-4 w-4"
						:disabled="busy || policy?.is_acknowledged"
					/>
					<span class="type-meta text-ink/80">
						I acknowledge that typing my full name is my electronic signature and I agree to this
						policy.
					</span>
				</label>

				<div class="rounded-lg border border-ink/10 bg-surface-soft px-3 py-2">
					<div class="type-caption text-ink/60">Signature preview</div>
					<div class="type-body-strong text-ink mt-1">
						{{ typedSignatureName.trim() || 'Not signed' }}
					</div>
					<div class="type-meta text-ink/60 mt-1">Timestamp on submit: {{ nowLabel }}</div>
				</div>
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
					{{ busy ? 'Signing…' : 'Sign and acknowledge policy' }}
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
const typedSignatureName = ref('');
const attestationConfirmed = ref(false);
const signatureTouched = ref(false);

const nowLabel = computed(() => new Date().toLocaleString());

const policyTitle = computed(() => {
	return (
		(policy.value?.policy_label || '').trim() ||
		(policy.value?.policy_title || '').trim() ||
		(policy.value?.policy_key || '').trim() ||
		(policy.value?.policy_version || '').trim() ||
		__('Policy')
	);
});

const expectedSignerLabel = computed(() => {
	return (
		(policy.value?.employee_name || '').trim() ||
		(policy.value?.employee || '').trim() ||
		__('Employee record')
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

function normalizeName(value: string): string {
	return value.trim().replace(/\s+/g, ' ').toLowerCase();
}

const isTypedSignatureMatch = computed(() => {
	const typed = normalizeName(typedSignatureName.value || '');
	if (!typed) return false;
	const expected = normalizeName(expectedSignerLabel.value || '');
	return expected ? typed === expected : true;
});

const canAcknowledge = computed(() => {
	return (
		Boolean(policy.value?.policy_version) &&
		!policy.value?.is_acknowledged &&
		isTypedSignatureMatch.value &&
		attestationConfirmed.value
	);
});

watch(
	() => props.context,
	next => {
		policy.value = next.policy_signature ?? null;
		busy.value = false;
		submittedOnce.value = false;
		actionError.value = null;
		typedSignatureName.value = '';
		attestationConfirmed.value = false;
		signatureTouched.value = false;
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
	signatureTouched.value = true;

	const focusItemId = requireFocusItemId();
	if (!focusItemId) return;

	if (policy.value?.is_acknowledged) {
		actionError.value = __('This policy has already been acknowledged.');
		return;
	}
	if (!typedSignatureName.value.trim()) {
		actionError.value = __('Type your full name to provide your electronic signature.');
		return;
	}
	if (!isTypedSignatureMatch.value) {
		actionError.value = `${__('Typed signature must match exactly:')} ${expectedSignerLabel.value}`;
		return;
	}
	if (!attestationConfirmed.value) {
		actionError.value = __('Confirm the legal attestation before signing.');
		return;
	}

	busy.value = true;
	submittedOnce.value = true;
	try {
		const payload: AcknowledgeStaffPolicyRequest = {
			focus_item_id: focusItemId,
			client_request_id: newClientRequestId('policy_ack'),
			typed_signature_name: typedSignatureName.value.trim(),
			attestation_confirmed: attestationConfirmed.value ? 1 : 0,
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
