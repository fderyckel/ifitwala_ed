<!-- ifitwala_ed/ui-spa/src/pages/admissions/ApplicantPolicies.vue -->

<template>
	<div class="admissions-page">
		<header class="page-header">
			<div class="page-header__intro">
				<h1 class="type-h1 text-ink">{{ __('Policies') }}</h1>
				<p class="type-meta text-ink/70">
					{{ __('Review and acknowledge the required policies.') }}
				</p>
			</div>
		</header>

		<div v-if="loading" class="rounded-2xl border border-border/70 bg-surface px-4 py-4">
			<div class="flex items-center gap-3">
				<Spinner class="h-4 w-4" />
				<p class="type-body-strong text-ink">{{ __('Loading policies…') }}</p>
			</div>
		</div>

		<div v-else-if="error" class="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3">
			<p class="type-body-strong text-rose-900">{{ __('Unable to load policies') }}</p>
			<p class="mt-1 type-caption text-rose-900/80 whitespace-pre-wrap">{{ error }}</p>
			<button type="button" class="if-button if-button--secondary mt-3" @click="loadPolicies">
				{{ __('Try again') }}
			</button>
		</div>

		<div v-else class="grid gap-4">
			<div v-if="actionError" class="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3">
				<p class="type-body-strong text-amber-900">{{ __('Notice') }}</p>
				<p class="mt-1 type-caption text-amber-900/80">{{ actionError }}</p>
			</div>
			<div
				v-for="policy in policies"
				:key="policy.policy_version"
				class="rounded-2xl border border-border/70 bg-white px-4 py-4 shadow-soft"
			>
				<div class="flex flex-wrap items-center justify-between gap-3">
					<div>
						<p class="type-body-strong text-ink">{{ policy.name }}</p>
						<p
							class="mt-1 type-caption"
							:class="policy.is_acknowledged ? 'text-leaf' : 'text-clay'"
						>
							{{ policy.is_acknowledged ? __('Acknowledged') : __('Pending acknowledgement') }}
						</p>
					</div>
					<button
						type="button"
						class="if-button if-button--primary"
						:disabled="policy.is_acknowledged || isReadOnly"
						@click="openPolicy(policy)"
					>
						{{ policy.is_acknowledged ? __('Acknowledged') : __('Review & acknowledge') }}
					</button>
				</div>
			</div>

			<div v-if="!policies.length" class="rounded-2xl border border-border/70 bg-white px-4 py-4">
				<p class="type-caption text-ink/60">{{ __('No policies are currently assigned.') }}</p>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { Spinner } from 'frappe-ui';

import { createAdmissionsService } from '@/lib/services/admissions/admissionsService';
import { useAdmissionsSession } from '@/composables/useAdmissionsSession';
import { useOverlayStack } from '@/composables/useOverlayStack';
import { __ } from '@/lib/i18n';
import { uiSignals, SIGNAL_ADMISSIONS_PORTAL_INVALIDATE } from '@/lib/uiSignals';
import type { ApplicantPolicy } from '@/types/contracts/admissions/types';

const service = createAdmissionsService();
const overlay = useOverlayStack();
const { session, currentApplicantName } = useAdmissionsSession();

const policies = ref<ApplicantPolicy[]>([]);
const loading = ref(false);
const error = ref<string | null>(null);
const actionError = ref('');

const isReadOnly = computed(() => Boolean(session.value?.applicant?.is_read_only));

async function loadPolicies() {
	if (!currentApplicantName.value) {
		policies.value = [];
		return;
	}
	loading.value = true;
	error.value = null;
	actionError.value = '';
	try {
		const resp = await service.listPolicies({ student_applicant: currentApplicantName.value });
		policies.value = resp.policies || [];
	} catch (err) {
		const message = err instanceof Error ? err.message : __('Unable to load policies.');
		error.value = message;
	} finally {
		loading.value = false;
	}
}

function openPolicy(policy: ApplicantPolicy) {
	if (isReadOnly.value) {
		actionError.value = __('This application is read-only.');
		return;
	}
	actionError.value = '';
	overlay.open('admissions-policy-ack', {
		policy: {
			name: policy.name,
			policy_version: policy.policy_version,
			content_html: policy.content_html,
			expected_signer_name: policy.expected_signature_name,
			student_applicant: currentApplicantName.value,
			acknowledgement_clauses: policy.acknowledgement_clauses || [],
		},
		readOnly: isReadOnly.value,
	});
}

let unsubscribe: (() => void) | null = null;

onMounted(async () => {
	await loadPolicies();
	unsubscribe = uiSignals.subscribe(SIGNAL_ADMISSIONS_PORTAL_INVALIDATE, () => {
		loadPolicies();
	});
});

onBeforeUnmount(() => {
	if (unsubscribe) unsubscribe();
});
</script>
