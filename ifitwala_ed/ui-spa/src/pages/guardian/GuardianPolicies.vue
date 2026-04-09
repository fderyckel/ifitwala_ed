<!-- ifitwala_ed/ui-spa/src/pages/guardian/GuardianPolicies.vue -->
<template>
	<div class="space-y-6">
		<header class="card-surface p-5 sm:p-6">
			<div class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
				<div>
					<p class="type-overline text-ink/60">Guardian Portal</p>
					<h1 class="type-h1 text-ink">Guardian Policies</h1>
					<p class="type-body text-ink/70">
						Review active guardian policies for your family scope and acknowledge any pending
						items.
					</p>
				</div>
				<button
					type="button"
					class="if-action self-start"
					:disabled="loading"
					@click="loadOverview"
				>
					Refresh
				</button>
			</div>
		</header>

		<section class="grid grid-cols-1 gap-3 sm:grid-cols-3">
			<article class="card-surface p-4">
				<p class="type-caption">Total policies</p>
				<p class="type-h3 text-ink">{{ counts.total_policies }}</p>
			</article>
			<article class="card-surface p-4">
				<p class="type-caption">Acknowledged</p>
				<p class="type-h3 text-ink">{{ counts.acknowledged_policies }}</p>
			</article>
			<article class="card-surface p-4">
				<p class="type-caption">Pending</p>
				<p class="type-h3 text-ink">{{ counts.pending_policies }}</p>
			</article>
		</section>

		<section v-if="loading" class="card-surface p-5">
			<p class="type-body text-ink/70">Loading guardian policies...</p>
		</section>

		<section v-else-if="errorMessage" class="card-surface p-5">
			<p class="type-body-strong text-flame">Could not load guardian policies.</p>
			<p class="type-body text-ink/70">{{ errorMessage }}</p>
		</section>

		<section v-else-if="!rows.length" class="card-surface p-5">
			<p class="type-body-strong text-ink">No active guardian policies in scope.</p>
			<p class="type-body text-ink/70">
				This portal account is linked correctly, but there are no active guardian policy versions
				to review.
			</p>
		</section>

		<section v-else class="space-y-4">
			<article v-for="row in rows" :key="row.policy_version" class="card-surface space-y-4 p-5">
				<div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
					<div class="space-y-1">
						<p class="type-caption text-ink/60">
							{{ row.policy_category }} · {{ row.version_label }}
						</p>
						<h2 class="type-h3 text-ink">{{ row.policy_title }}</h2>
						<p class="type-body text-ink/70">
							{{ row.description || 'No summary provided.' }}
						</p>
						<p class="type-caption text-ink/60">
							{{ row.organization }}<span v-if="row.school"> · {{ row.school }}</span>
						</p>
					</div>
					<div class="flex flex-col items-start gap-2 sm:items-end">
						<p
							class="rounded-full px-3 py-1 type-caption"
							:class="row.is_acknowledged ? 'bg-leaf/15 text-canopy' : 'bg-sand text-clay'"
						>
							{{ row.is_acknowledged ? 'Acknowledged' : 'Pending acknowledgement' }}
						</p>
						<p v-if="row.is_acknowledged" class="type-caption text-ink/60">
							{{ row.acknowledged_at || 'Acknowledged' }}
						</p>
					</div>
				</div>

				<details
					class="rounded-xl border border-line-soft bg-surface-soft p-4"
					:open="!row.is_acknowledged"
				>
					<summary class="cursor-pointer type-body-strong text-ink">Open policy text</summary>
					<div class="mt-3 whitespace-pre-wrap type-body text-ink/80">
						{{ row.policy_text || 'No policy text available.' }}
					</div>
				</details>

				<div
					v-if="!row.is_acknowledged"
					class="rounded-xl border border-line-soft bg-surface-soft p-4 space-y-4"
				>
					<div v-if="row.acknowledgement_clauses.length" class="space-y-3">
						<div>
							<p class="type-body-strong text-ink">Acknowledgement clauses</p>
							<p class="type-caption text-ink/65">
								Check every required clause before signing this policy.
							</p>
						</div>
						<div class="space-y-2">
							<label
								v-for="clause in row.acknowledgement_clauses"
								:key="clause.name"
								class="flex items-start gap-3 rounded-xl border border-line-soft bg-white px-3 py-3"
							>
								<input
									:checked="isClauseChecked(row.policy_version, clause.name)"
									type="checkbox"
									class="mt-1 h-4 w-4"
									:disabled="isRowBusy(row.policy_version)"
									@change="toggleClause(row.policy_version, clause.name, $event)"
								/>
								<span class="type-body text-ink/85">
									{{ clause.clause_text }}
									<span v-if="clause.is_required" class="type-caption text-flame"> *</span>
								</span>
							</label>
						</div>
						<p
							v-if="submitAttempts[row.policy_version] && !hasRequiredClausesChecked(row)"
							class="type-caption text-flame"
						>
							Check every required acknowledgement clause before signing.
						</p>
					</div>

					<div class="space-y-3">
						<div>
							<p class="type-body-strong text-ink">Electronic signature</p>
							<p class="type-caption text-ink/65">
								Type your full name exactly as recorded and confirm the legal attestation.
							</p>
						</div>

						<p class="type-caption text-ink/70">
							Expected signer name:
							<span class="type-body-strong text-ink">{{ row.expected_signature_name }}</span>
						</p>

						<label class="block space-y-1">
							<span class="type-caption text-ink/70">Type full name as electronic signature</span>
							<input
								:value="typedSignatureByVersion[row.policy_version] || ''"
								type="text"
								class="if-input w-full"
								placeholder="Enter your full name"
								:disabled="isRowBusy(row.policy_version)"
								@input="updateTypedSignature(row.policy_version, $event)"
							/>
						</label>

						<p
							v-if="
								(signatureTouched[row.policy_version] || submitAttempts[row.policy_version]) &&
								typedSignatureByVersion[row.policy_version]?.trim() &&
								!isTypedSignatureMatch(row)
							"
							class="type-caption text-flame"
						>
							Typed signature must match exactly: {{ row.expected_signature_name }}
						</p>

						<label class="flex items-start gap-2">
							<input
								:checked="Boolean(attestationByVersion[row.policy_version])"
								type="checkbox"
								class="mt-1 h-4 w-4"
								:disabled="isRowBusy(row.policy_version)"
								@change="toggleAttestation(row.policy_version, $event)"
							/>
							<span class="type-caption text-ink/80">
								I confirm that typing my name is my electronic signature, and I have read,
								acknowledged, and agree to this policy.
							</span>
						</label>

						<p
							v-if="
								submitAttempts[row.policy_version] && !attestationByVersion[row.policy_version]
							"
							class="type-caption text-flame"
						>
							Confirm the legal attestation before signing.
						</p>
					</div>

					<div class="flex justify-end">
						<button
							type="button"
							class="if-action"
							:disabled="isRowBusy(row.policy_version)"
							@click="acknowledgeRow(row)"
						>
							{{ isRowBusy(row.policy_version) ? 'Saving...' : 'Sign and acknowledge policy' }}
						</button>
					</div>
				</div>

				<p v-if="rowErrors[row.policy_version]" class="type-body text-flame">
					{{ rowErrors[row.policy_version] }}
				</p>
			</article>
		</section>
	</div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { toast } from 'frappe-ui';

import {
	acknowledgeGuardianPolicy,
	getGuardianPolicyOverview,
} from '@/lib/services/guardianPolicy/guardianPolicyService';

import type {
	GuardianPolicyRow,
	Response as GuardianPolicyOverview,
} from '@/types/contracts/guardian/get_guardian_policy_overview';

const loading = ref(true);
const errorMessage = ref('');
const overview = ref<GuardianPolicyOverview | null>(null);
const busyRows = ref<Record<string, boolean>>({});
const rowErrors = ref<Record<string, string>>({});
const typedSignatureByVersion = ref<Record<string, string>>({});
const attestationByVersion = ref<Record<string, boolean>>({});
const checkedClausesByVersion = ref<Record<string, string[]>>({});
const submitAttempts = ref<Record<string, boolean>>({});
const signatureTouched = ref<Record<string, boolean>>({});

const counts = computed(
	() =>
		overview.value?.counts ?? {
			total_policies: 0,
			acknowledged_policies: 0,
			pending_policies: 0,
		}
);
const rows = computed<GuardianPolicyRow[]>(() => overview.value?.rows ?? []);

function normalizeName(value: string): string {
	return value.trim().replace(/\s+/g, ' ').toLowerCase();
}

function isRowBusy(policyVersion: string): boolean {
	return Boolean(busyRows.value[policyVersion]);
}

function selectedClauseNames(policyVersion: string): string[] {
	return checkedClausesByVersion.value[policyVersion] ?? [];
}

function isClauseChecked(policyVersion: string, clauseName: string): boolean {
	return selectedClauseNames(policyVersion).includes(clauseName);
}

function toggleClause(policyVersion: string, clauseName: string, event: Event) {
	const checked = (event.target as HTMLInputElement).checked;
	const selected = new Set(selectedClauseNames(policyVersion));
	if (checked) selected.add(clauseName);
	else selected.delete(clauseName);
	checkedClausesByVersion.value = {
		...checkedClausesByVersion.value,
		[policyVersion]: Array.from(selected),
	};
}

function updateTypedSignature(policyVersion: string, event: Event) {
	typedSignatureByVersion.value = {
		...typedSignatureByVersion.value,
		[policyVersion]: (event.target as HTMLInputElement).value,
	};
	signatureTouched.value = {
		...signatureTouched.value,
		[policyVersion]: true,
	};
}

function toggleAttestation(policyVersion: string, event: Event) {
	attestationByVersion.value = {
		...attestationByVersion.value,
		[policyVersion]: (event.target as HTMLInputElement).checked,
	};
}

function isTypedSignatureMatch(row: GuardianPolicyRow): boolean {
	const typed = normalizeName(typedSignatureByVersion.value[row.policy_version] || '');
	if (!typed) return false;
	const expected = normalizeName(row.expected_signature_name || '');
	return expected ? typed === expected : true;
}

function hasRequiredClausesChecked(row: GuardianPolicyRow): boolean {
	const selected = new Set(selectedClauseNames(row.policy_version));
	return row.acknowledgement_clauses.every(
		clause => !clause.is_required || selected.has(clause.name)
	);
}

function resetRowState() {
	busyRows.value = {};
	rowErrors.value = {};
	typedSignatureByVersion.value = {};
	attestationByVersion.value = {};
	checkedClausesByVersion.value = {};
	submitAttempts.value = {};
	signatureTouched.value = {};
}

async function loadOverview() {
	loading.value = true;
	errorMessage.value = '';
	try {
		overview.value = await getGuardianPolicyOverview();
		resetRowState();
	} catch (error) {
		const message = error instanceof Error ? error.message : String(error || '');
		errorMessage.value = message || 'Unknown error';
	} finally {
		loading.value = false;
	}
}

async function acknowledgeRow(row: GuardianPolicyRow) {
	const policyVersion = row.policy_version;
	submitAttempts.value = { ...submitAttempts.value, [policyVersion]: true };
	signatureTouched.value = { ...signatureTouched.value, [policyVersion]: true };
	rowErrors.value = { ...rowErrors.value, [policyVersion]: '' };

	if (!typedSignatureByVersion.value[policyVersion]?.trim()) {
		const message = 'Type your full name to provide your electronic signature.';
		rowErrors.value = { ...rowErrors.value, [policyVersion]: message };
		toast.error(message);
		return;
	}
	if (!hasRequiredClausesChecked(row)) {
		const message = 'Check every required acknowledgement clause before signing.';
		rowErrors.value = { ...rowErrors.value, [policyVersion]: message };
		toast.error(message);
		return;
	}
	if (!isTypedSignatureMatch(row)) {
		const message = `Typed signature must match exactly: ${row.expected_signature_name}`;
		rowErrors.value = { ...rowErrors.value, [policyVersion]: message };
		toast.error(message);
		return;
	}
	if (!attestationByVersion.value[policyVersion]) {
		const message = 'Confirm the legal attestation before signing.';
		rowErrors.value = { ...rowErrors.value, [policyVersion]: message };
		toast.error(message);
		return;
	}

	busyRows.value = { ...busyRows.value, [policyVersion]: true };
	try {
		const result = await acknowledgeGuardianPolicy({
			policy_version: policyVersion,
			typed_signature_name: typedSignatureByVersion.value[policyVersion].trim(),
			attestation_confirmed: attestationByVersion.value[policyVersion] ? 1 : 0,
			checked_clause_names: selectedClauseNames(policyVersion),
		});
		toast.success(
			result.status === 'already_acknowledged'
				? 'Policy was already acknowledged.'
				: 'Policy acknowledged.'
		);
		await loadOverview();
	} catch (error) {
		const message = error instanceof Error ? error.message : String(error || '');
		rowErrors.value = {
			...rowErrors.value,
			[policyVersion]: message || 'Could not acknowledge this policy.',
		};
		toast.error(message || 'Could not acknowledge this policy.');
	} finally {
		busyRows.value = { ...busyRows.value, [policyVersion]: false };
	}
}

onMounted(() => {
	void loadOverview();
});
</script>
