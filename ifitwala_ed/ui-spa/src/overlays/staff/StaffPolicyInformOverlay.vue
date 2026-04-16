<!-- ifitwala_ed/ui-spa/src/overlays/staff/StaffPolicyInformOverlay.vue -->
<template>
	<TransitionRoot as="template" :show="open" @after-leave="emitAfterLeave">
		<Dialog
			as="div"
			class="if-overlay if-overlay--focus"
			:style="overlayStyle"
			@close="onDialogClose"
		>
			<TransitionChild
				as="template"
				enter="if-overlay__fade-enter"
				enter-from="if-overlay__fade-from"
				enter-to="if-overlay__fade-to"
				leave="if-overlay__fade-leave"
				leave-from="if-overlay__fade-to"
				leave-to="if-overlay__fade-from"
			>
				<div class="if-overlay__backdrop" @click="emitClose('backdrop')" />
			</TransitionChild>

			<div class="if-overlay__wrap">
				<TransitionChild
					as="template"
					enter="if-overlay__panel-enter"
					enter-from="if-overlay__panel-from"
					enter-to="if-overlay__panel-to"
					leave="if-overlay__panel-leave"
					leave-from="if-overlay__panel-to"
					leave-to="if-overlay__panel-from"
				>
					<DialogPanel class="if-overlay__panel">
						<div class="meeting-modal__header">
							<div class="meeting-modal__headline min-w-0">
								<div class="type-overline">Policy information</div>
								<DialogTitle class="type-h2 text-canopy truncate mt-1">
									{{ policyTitle }}
								</DialogTitle>
								<p v-if="scopeLabel" class="type-caption mt-1 truncate">{{ scopeLabel }}</p>
								<div v-if="audienceChips.length" class="mt-2 flex flex-wrap gap-2">
									<span
										v-for="chip in audienceChips"
										:key="chip"
										class="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700"
									>
										{{ chip }}
									</span>
								</div>
								<div
									v-if="statusLabel"
									class="mt-2 inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium"
									:class="statusClass"
								>
									{{ statusLabel }}
								</div>
							</div>
							<div class="meeting-modal__header-actions">
								<button
									type="button"
									class="if-overlay__icon-button"
									@click="emitClose('programmatic')"
									aria-label="Close"
								>
									<FeatherIcon name="x" class="h-4 w-4" />
								</button>
							</div>
						</div>

						<section class="if-overlay__body custom-scrollbar space-y-4">
							<div v-if="loading" class="py-10 space-y-3">
								<div class="if-skel if-skel--title" />
								<div class="if-skel if-skel--sub" />
								<div class="if-skel h-28 rounded-xl" />
							</div>

							<div v-else-if="errorText" class="card-panel p-5">
								<p class="type-body-strong text-ink">Couldn't open this policy</p>
								<p class="mt-2 type-body text-ink/70">{{ errorText }}</p>
							</div>

							<div v-else-if="policy" class="space-y-4">
								<div class="card-surface p-4">
									<div class="type-meta text-ink/60">
										<span v-if="policy.policy_version"
											>Policy Version: {{ policy.policy_version }}</span
										>
										<span v-if="policy.version_label"> - Version {{ policy.version_label }}</span>
									</div>
									<div
										v-if="policy.signature_required && policy.acknowledgement_status === 'signed'"
										class="type-meta text-ink/60 mt-1"
									>
										Acknowledged
										<span v-if="policy.acknowledged_at">
											on
											{{
												formatLocalizedDateTime(policy.acknowledged_at, { includeWeekday: true })
											}}
										</span>
									</div>
									<div
										v-if="hasChangeSummary || hasChangeStats"
										class="mt-3 rounded-xl border border-ink/10 bg-white p-3"
									>
										<div class="type-caption text-ink/70">What changed</div>
										<div v-if="hasChangeStats" class="mt-2 flex flex-wrap gap-2">
											<span class="type-meta rounded-full border border-ink/10 px-2 py-1">
												Added {{ addedCount }}
											</span>
											<span class="type-meta rounded-full border border-ink/10 px-2 py-1">
												Removed {{ removedCount }}
											</span>
											<span class="type-meta rounded-full border border-ink/10 px-2 py-1">
												Modified {{ modifiedCount }}
											</span>
										</div>
										<p v-if="hasChangeSummary" class="type-meta text-ink mt-2 whitespace-pre-wrap">
											{{ changeSummary }}
										</p>
									</div>
								</div>

								<div class="card-surface p-4">
									<div class="flex items-center justify-end gap-2">
										<button
											type="button"
											class="btn btn-quiet"
											:disabled="activeTab === 'changes' || !hasDiffHtml"
											@click="activeTab = 'changes'"
										>
											Changes
										</button>
										<button
											type="button"
											class="btn btn-quiet"
											:disabled="activeTab === 'full'"
											@click="activeTab = 'full'"
										>
											Full policy
										</button>
									</div>

									<div
										v-if="activeTab === 'changes'"
										class="mt-3 rounded-xl border border-ink/10 bg-white p-3 max-h-96 overflow-auto"
									>
										<div
											v-if="hasDiffHtml"
											class="prose prose-sm max-w-none text-ink"
											v-html="trustedHtml(policy.diff_html || '')"
										/>
										<p v-else class="type-meta text-ink/60">
											No amendment diff is available for this version. Review the full policy text.
										</p>
									</div>

									<div
										v-else
										class="mt-3 rounded-xl border border-ink/10 bg-white p-3 max-h-96 overflow-auto"
									>
										<div
											v-if="policy.policy_text_html"
											class="prose prose-sm max-w-none text-ink"
											v-html="trustedHtml(policy.policy_text_html)"
										/>
										<p v-else class="type-meta text-ink/60">
											No policy text is available for this version.
										</p>
									</div>
								</div>

								<div class="card-surface p-4">
									<div class="type-body font-medium">Version history</div>
									<p class="type-meta text-ink/60 mt-1">
										Latest and previous versions for this policy.
									</p>
									<div class="mt-3 overflow-auto">
										<table class="w-full text-sm">
											<thead>
												<tr class="text-left text-slate-500">
													<th class="pb-2 pr-2">Version</th>
													<th class="pb-2 pr-2">Effective</th>
													<th class="pb-2 pr-2">Approved</th>
													<th class="pb-2">State</th>
												</tr>
											</thead>
											<tbody>
												<tr
													v-for="row in policy.history || []"
													:key="row.policy_version"
													class="border-t border-slate-100"
												>
													<td class="py-2 pr-2">
														{{ row.version_label || row.policy_version }}
													</td>
													<td class="py-2 pr-2">
														<span v-if="row.effective_from">
															{{ formatLocalizedDate(row.effective_from) }}
														</span>
														<span v-else>-</span>
														<span v-if="row.effective_to">
															→ {{ formatLocalizedDate(row.effective_to) }}
														</span>
													</td>
													<td class="py-2 pr-2">
														{{ row.approved_on ? formatLocalizedDate(row.approved_on) : '-' }}
													</td>
													<td class="py-2">
														<span
															class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium"
															:class="
																row.is_active
																	? 'bg-leaf/15 text-canopy'
																	: 'bg-slate-100 text-slate-600'
															"
														>
															{{ row.is_active ? 'Active' : 'Historical' }}
														</span>
													</td>
												</tr>
												<tr v-if="!(policy.history || []).length">
													<td class="py-3 text-slate-500" colspan="4">
														No version history available.
													</td>
												</tr>
											</tbody>
										</table>
									</div>
								</div>
							</div>
						</section>

						<footer class="if-overlay__footer justify-end">
							<button type="button" class="btn btn-quiet" @click="emitClose('programmatic')">
								Close
							</button>
						</footer>
					</DialogPanel>
				</TransitionChild>
			</div>
		</Dialog>
	</TransitionRoot>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue';
import {
	Dialog,
	DialogPanel,
	DialogTitle,
	TransitionChild,
	TransitionRoot,
} from '@headlessui/vue';
import { FeatherIcon } from 'frappe-ui';

import { createPolicyInformService } from '@/lib/services/policyInform/policyInformService';
import { formatLocalizedDate, formatLocalizedDateTime } from '@/lib/datetime';
import type { Response as PolicyInformPayload } from '@/types/contracts/policy_communication/get_policy_inform_payload';

type CloseReason = 'backdrop' | 'esc' | 'programmatic';

const props = defineProps<{
	open: boolean;
	zIndex?: number;
	overlayId?: string;
	policyVersion?: string | null;
	orgCommunication?: string | null;
}>();

const emit = defineEmits<{
	(e: 'close', reason: CloseReason): void;
	(e: 'after-leave'): void;
}>();

const service = createPolicyInformService();

const loading = ref(false);
const errorText = ref<string | null>(null);
const policy = ref<PolicyInformPayload | null>(null);
const activeTab = ref<'changes' | 'full'>('changes');

const overlayStyle = computed(() => ({ zIndex: props.zIndex || 0 }));
const policyTitle = computed(() => {
	return (
		(policy.value?.policy_label || '').trim() ||
		(policy.value?.policy_title || '').trim() ||
		(policy.value?.policy_key || '').trim() ||
		(policy.value?.policy_version || '').trim() ||
		'Policy'
	);
});
const scopeLabel = computed(() => {
	const parts = [];
	const org = (policy.value?.policy_organization || '').trim();
	const school = (policy.value?.policy_school || '').trim();
	if (org) parts.push(`Organization: ${org}`);
	if (school) parts.push(`School: ${school}`);
	return parts.join(' - ');
});
const changeSummary = computed(() => (policy.value?.change_summary || '').trim());
const addedCount = computed(() => Number(policy.value?.change_stats?.added || 0));
const removedCount = computed(() => Number(policy.value?.change_stats?.removed || 0));
const modifiedCount = computed(() => Number(policy.value?.change_stats?.modified || 0));
const hasChangeStats = computed(
	() => addedCount.value + removedCount.value + modifiedCount.value > 0
);
const hasChangeSummary = computed(() => Boolean(changeSummary.value));
const hasDiffHtml = computed(() => Boolean((policy.value?.diff_html || '').trim()));
const audienceTokens = computed(() =>
	Array.from(new Set((policy.value?.applies_to_tokens || []).filter(Boolean)))
);
const audienceChips = computed(() => audienceTokens.value.map(audienceLabel));
const hasStaffAudience = computed(() => audienceTokens.value.includes('Staff'));
const workflowLabel = computed(() => {
	if (!audienceTokens.value.length) return null;
	if (audienceTokens.value.length > 1) return 'Cross-audience policy';
	switch (audienceTokens.value[0]) {
		case 'Guardian':
			return 'Guardian portal acknowledgement';
		case 'Student':
			return 'Student hub acknowledgement';
		case 'Staff':
			return 'Staff workspace policy';
		default:
			return 'Policy in scope';
	}
});
const statusLabel = computed(() => {
	if (hasStaffAudience.value && policy.value?.signature_required) {
		switch (policy.value?.acknowledgement_status) {
			case 'signed':
				return 'Signed';
			case 'new_version':
				return 'New version to review';
			case 'pending':
				return 'Signature pending';
			default:
				return 'Signature pending';
		}
	}
	if (hasStaffAudience.value && audienceTokens.value.length === 1) {
		return 'Informational policy (no signature required)';
	}
	return workflowLabel.value;
});
const statusClass = computed(() => {
	if (hasStaffAudience.value && policy.value?.signature_required) {
		switch (policy.value?.acknowledgement_status) {
			case 'signed':
				return 'bg-leaf/15 text-canopy';
			case 'new_version':
				return 'bg-sky/20 text-canopy';
			case 'pending':
				return 'bg-sand text-clay';
			default:
				return 'bg-sand text-clay';
		}
	}
	if (audienceTokens.value.length > 1) return 'bg-jacaranda/10 text-jacaranda';
	if (audienceTokens.value[0] === 'Guardian') return 'bg-sky/20 text-canopy';
	if (audienceTokens.value[0] === 'Student') return 'bg-leaf/15 text-canopy';
	return 'bg-slate-100 text-slate-700';
});

function audienceLabel(audience: string): string {
	if (audience === 'Guardian') return 'Guardians';
	if (audience === 'Student') return 'Students';
	if (audience === 'Staff') return 'Staff';
	return audience;
}

function trustedHtml(html: string): string {
	return String(html || '');
}

function normalizeError(err: unknown): string {
	if (err instanceof Error && err.message) return err.message;
	return 'Please try again.';
}

function resetState() {
	loading.value = false;
	errorText.value = null;
	policy.value = null;
	activeTab.value = 'changes';
}

async function loadPolicy() {
	const policyVersion = String(props.policyVersion || '').trim();
	if (!policyVersion) {
		errorText.value = 'Missing policy version.';
		policy.value = null;
		return;
	}

	loading.value = true;
	errorText.value = null;
	policy.value = null;
	try {
		const result = await service.getPolicyInformPayload({
			policy_version: policyVersion,
			org_communication: props.orgCommunication || null,
		});
		policy.value = result || null;
		activeTab.value = (result?.diff_html || '').trim() ? 'changes' : 'full';
	} catch (err: unknown) {
		errorText.value = normalizeError(err);
		policy.value = null;
	} finally {
		loading.value = false;
	}
}

function emitClose(reason: CloseReason) {
	emit('close', reason);
}

function emitAfterLeave() {
	resetState();
	emit('after-leave');
}

function onDialogClose(_payload: unknown) {
	// no-op by OverlayHost contract
}

function onKeydown(event: KeyboardEvent) {
	if (!props.open) return;
	if (event.key === 'Escape') emitClose('esc');
}

watch(
	() => props.open,
	next => {
		if (next) {
			document.addEventListener('keydown', onKeydown, true);
			loadPolicy();
			return;
		}
		document.removeEventListener('keydown', onKeydown, true);
	},
	{ immediate: true }
);

watch(
	() => [props.policyVersion, props.orgCommunication],
	(next, prev) => {
		if (!props.open) return;
		const nextVersion = String(next[0] || '').trim();
		const prevVersion = String(prev?.[0] || '').trim();
		const nextComm = String(next[1] || '').trim();
		const prevComm = String(prev?.[1] || '').trim();
		if (nextVersion !== prevVersion || nextComm !== prevComm) {
			loadPolicy();
		}
	}
);

onBeforeUnmount(() => {
	document.removeEventListener('keydown', onKeydown, true);
});
</script>

<style scoped>
:deep(.policy-diff) {
	display: flex;
	flex-direction: column;
	gap: 0.75rem;
}

:deep(.policy-diff-block) {
	border: 1px solid rgb(var(--ink-rgb) / 0.1);
	border-radius: 0.75rem;
	padding: 0.75rem;
	background: #fff;
}

:deep(.policy-diff-label) {
	font-size: 0.75rem;
	color: rgb(var(--ink-rgb) / 0.65);
	margin-bottom: 0.375rem;
}

:deep(.policy-diff-block--added ins),
:deep(.policy-diff-body-new ins) {
	background: rgba(14, 165, 166, 0.12);
	text-decoration: none;
	padding: 0.05rem 0.2rem;
	border-radius: 0.2rem;
}

:deep(.policy-diff-block--removed summary),
:deep(.policy-diff-previous summary) {
	cursor: pointer;
	font-size: 0.75rem;
	color: rgb(var(--ink-rgb) / 0.7);
}

:deep(.policy-diff-block--removed del),
:deep(.policy-diff-body-old del) {
	background: rgba(148, 163, 184, 0.16);
	padding: 0.05rem 0.2rem;
	border-radius: 0.2rem;
}
</style>
