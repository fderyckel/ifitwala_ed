<!-- ifitwala_ed/ui-spa/src/pages/guardian/GuardianPolicies.vue -->
<template>
	<div class="portal-page">
		<header class="card-surface policy-hero p-5 sm:p-6">
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

		<section class="policy-summary" aria-label="Guardian policy summary">
			<article class="card-surface policy-metric-card policy-metric-card--total p-4">
				<div class="policy-metric-card__row">
					<div>
						<p class="type-caption text-ink/65">Total policies</p>
						<p class="type-caption text-ink/50">Current family policy scope</p>
					</div>
					<p class="type-h2 text-ink">{{ counts.total_policies }}</p>
				</div>
			</article>
			<article class="card-surface policy-metric-card policy-metric-card--acknowledged p-4">
				<div class="policy-metric-card__row">
					<div>
						<p class="type-caption text-ink/65">Acknowledged</p>
						<p class="type-caption text-ink/50">Already signed for this family</p>
					</div>
					<p class="type-h2 text-canopy">{{ counts.acknowledged_policies }}</p>
				</div>
			</article>
			<article class="card-surface policy-metric-card policy-metric-card--pending p-4">
				<div class="policy-metric-card__row">
					<div>
						<p class="type-caption text-ink/65">Pending</p>
						<p class="type-caption text-ink/50">Still needs guardian action</p>
					</div>
					<p class="type-h2 text-clay">{{ counts.pending_policies }}</p>
				</div>
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

		<section v-else class="policy-list space-y-4">
			<div class="card-surface policy-list-hero p-5">
				<div class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
					<div>
						<p class="type-overline text-canopy/75">Family Policy Progress</p>
						<h2 class="type-h3 text-ink">Review and sign pending policy versions</h2>
						<p class="type-caption text-ink/65">
							Each card keeps the policy text, signature requirements, and current status in one
							place so guardians do not have to jump between views.
						</p>
					</div>
					<div class="flex flex-wrap gap-2">
						<span class="chip">Total {{ counts.total_policies }}</span>
						<span class="rounded-full bg-leaf/12 px-3 py-1 type-caption text-canopy">
							Acknowledged {{ counts.acknowledged_policies }}
						</span>
						<span class="rounded-full bg-sand px-3 py-1 type-caption text-clay">
							Pending {{ counts.pending_policies }}
						</span>
					</div>
				</div>
			</div>

			<article
				v-for="row in rows"
				:key="row.policy_version"
				class="card-surface policy-card space-y-4 p-5"
				:class="[
					row.is_acknowledged ? 'policy-card--acknowledged' : 'policy-card--pending',
					isFocusedPolicy(row.policy_version) ? 'ring-2 ring-jacaranda/35 shadow-soft' : '',
				]"
				:data-policy-version="row.policy_version"
				:data-policy-focused="isFocusedPolicy(row.policy_version) ? 'true' : 'false'"
			>
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
							class="policy-status-pill rounded-full px-3 py-1 type-caption"
							:class="
								row.is_acknowledged
									? 'policy-status-pill--acknowledged'
									: 'policy-status-pill--pending'
							"
						>
							{{ row.is_acknowledged ? 'Acknowledged' : 'Pending acknowledgement' }}
						</p>
						<p v-if="row.is_acknowledged" class="type-caption text-canopy/75">
							{{ row.acknowledged_at || 'Acknowledged' }}
						</p>
					</div>
				</div>

				<details
					class="policy-detail-panel rounded-xl border border-line-soft bg-surface-soft p-4"
					:open="!row.is_acknowledged || isFocusedPolicy(row.policy_version)"
				>
					<summary class="cursor-pointer type-body-strong text-ink">Open policy text</summary>
					<div
						v-if="row.policy_text"
						class="policy-richtext prose prose-sm mt-3 max-w-none text-ink/80"
						v-html="trustedHtml(row.policy_text)"
					/>
					<p v-else class="mt-3 type-body text-ink/70">No policy text available.</p>
				</details>

				<div
					v-if="!row.is_acknowledged"
					class="policy-action-panel rounded-xl border border-line-soft bg-surface-soft p-4 space-y-4"
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
								class="policy-clause-row flex items-start gap-3 rounded-xl border border-line-soft bg-white px-3 py-3"
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
							class="if-action policy-action-button"
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
import { computed, nextTick, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
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
const route = useRoute();

const counts = computed(
	() =>
		overview.value?.counts ?? {
			total_policies: 0,
			acknowledged_policies: 0,
			pending_policies: 0,
		}
);
const rows = computed<GuardianPolicyRow[]>(() => overview.value?.rows ?? []);
const focusedPolicyVersion = computed(() =>
	typeof route.query.policy_version === 'string' ? route.query.policy_version.trim() : ''
);

function normalizeName(value: string): string {
	return value.trim().replace(/\s+/g, ' ').toLowerCase();
}

function trustedHtml(html: string): string {
	return String(html || '');
}

function isRowBusy(policyVersion: string): boolean {
	return Boolean(busyRows.value[policyVersion]);
}

function isFocusedPolicy(policyVersion: string): boolean {
	return Boolean(focusedPolicyVersion.value && focusedPolicyVersion.value === policyVersion);
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

async function focusRequestedPolicy() {
	if (!focusedPolicyVersion.value) return;
	await nextTick();
	const target = Array.from(document.querySelectorAll<HTMLElement>('[data-policy-version]')).find(
		element => element.dataset.policyVersion === focusedPolicyVersion.value
	);
	if (!target || typeof target.scrollIntoView !== 'function') return;
	target.scrollIntoView({ block: 'start', behavior: 'smooth' });
}

async function loadOverview() {
	loading.value = true;
	errorMessage.value = '';
	try {
		overview.value = await getGuardianPolicyOverview();
		resetRowState();
		await focusRequestedPolicy();
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

<style scoped>
.policy-hero {
	position: relative;
	overflow: hidden;
	border-color: rgb(var(--sand-rgb) / 0.8);
	background:
		radial-gradient(circle at 0% 0%, rgb(var(--sand-rgb) / 0.72), transparent 38%),
		radial-gradient(circle at 100% 0%, rgb(var(--jacaranda-rgb) / 0.16), transparent 40%),
		radial-gradient(circle at 100% 100%, rgb(var(--leaf-rgb) / 0.12), transparent 42%),
		linear-gradient(180deg, rgb(var(--surface-strong-rgb) / 0.98), rgb(var(--sky-rgb) / 0.84));
	box-shadow: 0 16px 36px rgb(var(--ink-rgb) / 0.06);
}

.policy-summary {
	display: grid;
	grid-auto-flow: column;
	grid-auto-columns: minmax(16rem, 1fr);
	gap: 0.75rem;
	overflow-x: auto;
	padding-bottom: 0.25rem;
}

.policy-metric-card {
	position: relative;
	overflow: hidden;
	min-width: 0;
	border-color: rgb(var(--border-rgb) / 0.78);
	background: linear-gradient(
		180deg,
		rgb(var(--surface-strong-rgb) / 0.98),
		rgb(var(--surface-rgb) / 0.94)
	);
}

.policy-metric-card::before {
	content: '';
	position: absolute;
	inset: 0 auto auto 0;
	height: 0.3rem;
	width: 100%;
}

.policy-metric-card--total::before {
	background: linear-gradient(90deg, rgb(var(--sand-rgb) / 1), rgb(var(--clay-rgb) / 0.78));
}

.policy-metric-card--acknowledged::before {
	background: linear-gradient(90deg, rgb(var(--leaf-rgb) / 0.88), rgb(var(--canopy-rgb) / 0.82));
}

.policy-metric-card--pending::before {
	background: linear-gradient(90deg, rgb(var(--clay-rgb) / 0.92), rgb(var(--flame-rgb) / 0.82));
}

.policy-metric-card__row {
	display: flex;
	align-items: flex-end;
	justify-content: space-between;
	gap: 1rem;
}

.policy-list-hero {
	position: relative;
	overflow: hidden;
	border-color: rgb(var(--sand-rgb) / 0.74);
	background:
		radial-gradient(circle at 100% 0%, rgb(var(--sand-rgb) / 0.64), transparent 34%),
		linear-gradient(180deg, rgb(var(--surface-strong-rgb) / 0.98), rgb(var(--surface-rgb) / 0.94));
}

.policy-card {
	position: relative;
	overflow: hidden;
	transition:
		border-color 120ms ease,
		transform 120ms ease,
		box-shadow 120ms ease;
}

.policy-card::before {
	content: '';
	position: absolute;
	inset: 0 auto 0 0;
	width: 0.35rem;
}

.policy-card:hover {
	transform: translateY(-1px);
	box-shadow: var(--shadow-soft);
}

.policy-card--acknowledged {
	border-color: rgb(var(--leaf-rgb) / 0.16);
	background:
		radial-gradient(circle at 100% 0%, rgb(var(--leaf-rgb) / 0.08), transparent 36%),
		rgb(var(--surface-rgb) / 0.95);
}

.policy-card--acknowledged::before {
	background: linear-gradient(180deg, rgb(var(--leaf-rgb) / 0.84), rgb(var(--canopy-rgb) / 0.8));
}

.policy-card--acknowledged:hover {
	border-color: rgb(var(--leaf-rgb) / 0.26);
}

.policy-card--pending {
	border-color: rgb(var(--sand-rgb) / 0.94);
	background:
		radial-gradient(circle at 100% 0%, rgb(var(--sand-rgb) / 0.88), transparent 38%),
		rgb(var(--surface-rgb) / 0.96);
}

.policy-card--pending::before {
	background: linear-gradient(180deg, rgb(var(--clay-rgb) / 0.82), rgb(var(--flame-rgb) / 0.72));
}

.policy-card--pending:hover {
	border-color: rgb(var(--clay-rgb) / 0.26);
}

.policy-status-pill--acknowledged {
	background: rgb(var(--leaf-rgb) / 0.12);
	color: rgb(var(--canopy-rgb) / 1);
}

.policy-status-pill--pending {
	background: rgb(var(--sand-rgb) / 0.95);
	color: rgb(var(--clay-rgb) / 1);
}

.policy-detail-panel {
	background: linear-gradient(
		180deg,
		rgb(var(--surface-rgb) / 0.88),
		rgb(var(--surface-strong-rgb) / 0.96)
	);
}

.policy-action-panel {
	border-color: rgb(var(--sand-rgb) / 0.9);
	background:
		radial-gradient(circle at 100% 0%, rgb(var(--sand-rgb) / 0.72), transparent 34%),
		linear-gradient(180deg, rgb(var(--surface-strong-rgb) / 0.98), rgb(var(--surface-rgb) / 0.96));
}

.policy-clause-row {
	transition:
		border-color 120ms ease,
		background-color 120ms ease,
		transform 120ms ease;
}

.policy-clause-row:hover {
	transform: translateY(-1px);
	border-color: rgb(var(--clay-rgb) / 0.18);
	background-color: rgb(var(--sand-rgb) / 0.22);
}

.policy-action-button {
	border-color: rgb(var(--clay-rgb) / 0.2);
	background-color: rgb(var(--surface-strong-rgb) / 0.96);
}

.policy-richtext :deep(.ql-editor) {
	padding: 0;
}

.policy-richtext :deep(p + p) {
	margin-top: 0.75rem;
}

.policy-richtext :deep(ul) {
	list-style-type: disc;
	padding-inline-start: 1.5rem;
}

.policy-richtext :deep(ol) {
	list-style-type: decimal;
	padding-inline-start: 1.5rem;
}

.policy-richtext :deep(li) {
	margin: 0.25rem 0;
}

.policy-richtext :deep(a) {
	color: rgb(var(--jacaranda-rgb) / 1);
	text-decoration: underline;
	text-underline-offset: 0.14em;
}

.policy-richtext :deep(u) {
	text-decoration: underline;
	text-underline-offset: 0.14em;
}

.policy-richtext :deep(h2) {
	font-size: 1.25rem;
	font-weight: 600;
	line-height: 1.35;
}

.policy-richtext :deep(h3) {
	font-size: 1.125rem;
	font-weight: 600;
	line-height: 1.4;
}

@media (min-width: 640px) {
	.policy-summary {
		grid-auto-flow: initial;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		overflow: visible;
		padding-bottom: 0;
	}
}
</style>
