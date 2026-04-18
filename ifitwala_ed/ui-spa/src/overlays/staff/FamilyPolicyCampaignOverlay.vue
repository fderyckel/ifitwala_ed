<template>
	<TransitionRoot as="template" :show="open" @after-leave="emitAfterLeave">
		<Dialog
			as="div"
			class="if-overlay if-overlay--focus"
			:style="overlayStyle"
			:initialFocus="closeBtnEl"
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
						<div class="flex items-start justify-between gap-4 px-6 pt-6">
							<div class="min-w-0">
								<DialogTitle class="type-h2 text-ink">Family Policy Campaign</DialogTitle>
								<p class="mt-1 type-caption text-ink/60">
									Publish student and guardian portal notices that deep-link to the exact policy
									version they still need to acknowledge. This never creates staff tasks or a
									second compliance record.
								</p>
							</div>
							<button
								ref="closeBtnEl"
								type="button"
								class="if-overlay__icon-button shrink-0"
								@click="emitClose('programmatic')"
								aria-label="Close"
							>
								<FeatherIcon name="x" class="h-4 w-4" />
							</button>
						</div>

						<div class="if-overlay__body space-y-5 px-6 pb-6">
							<div
								v-if="errorMessage"
								class="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 shadow-soft"
								role="alert"
							>
								<p class="type-body-strong text-rose-900">Unable to publish this campaign</p>
								<p class="mt-1 whitespace-pre-wrap type-caption text-rose-900/80">
									{{ errorMessage }}
								</p>
							</div>

							<div
								v-if="successMessage"
								class="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 shadow-soft"
							>
								<p class="type-body-strong text-emerald-900">{{ successMessage }}</p>
								<div v-if="publishedCommunications.length" class="mt-2 space-y-1">
									<p
										v-for="communication in publishedCommunications"
										:key="communication.org_communication"
										class="type-caption text-emerald-900/80"
									>
										{{ communication.audience_label }}: {{ communication.title }}
									</p>
								</div>
							</div>

							<section class="grid gap-4 md:grid-cols-2">
								<div class="flex min-w-0 flex-col gap-1">
									<label for="family-policy-campaign-organization" class="type-label leading-tight"
										>Organization</label
									>
									<select
										id="family-policy-campaign-organization"
										v-model="form.organization"
										class="if-overlay__input"
										:disabled="busyOptions || busyPublish"
									>
										<option value="">Select organization</option>
										<option v-for="org in options.organizations" :key="org" :value="org">
											{{ org }}
										</option>
									</select>
								</div>

								<div class="flex min-w-0 flex-col gap-1">
									<label for="family-policy-campaign-school" class="type-label leading-tight"
										>School (optional)</label
									>
									<select
										id="family-policy-campaign-school"
										v-model="form.school"
										class="if-overlay__input"
										:disabled="busyOptions || busyPublish || !form.organization"
									>
										<option value="">All schools in scope</option>
										<option v-for="school in options.schools" :key="school" :value="school">
											{{ school }}
										</option>
									</select>
								</div>

								<div class="flex min-w-0 flex-col gap-1 md:col-span-2">
									<label
										for="family-policy-campaign-policy-version"
										class="type-label leading-tight"
										>Policy Version</label
									>
									<select
										id="family-policy-campaign-policy-version"
										v-model="form.policy_version"
										class="if-overlay__input"
										:disabled="busyOptions || busyPublish || !form.organization"
									>
										<option value="">Select family policy version</option>
										<option
											v-for="policy in options.policies"
											:key="policy.policy_version"
											:value="policy.policy_version"
										>
											{{ policyLabel(policy) }}
										</option>
									</select>
									<p class="type-caption text-slate-500">
										Only policy versions that apply to students or guardians are shown here.
									</p>
								</div>

								<div class="flex min-w-0 flex-col gap-1">
									<label for="family-policy-campaign-title" class="type-label leading-tight"
										>Headline (optional)</label
									>
									<input
										id="family-policy-campaign-title"
										v-model="form.title"
										type="text"
										class="if-overlay__input"
										:disabled="busyPublish"
										placeholder="Default titles will be generated per audience."
									/>
								</div>

								<div class="flex min-w-0 flex-col gap-1">
									<label for="family-policy-campaign-publish-to" class="type-label leading-tight"
										>Visible Until (optional)</label
									>
									<input
										id="family-policy-campaign-publish-to"
										v-model="form.publish_to"
										type="date"
										class="if-overlay__input"
										:disabled="busyPublish"
									/>
								</div>

								<div class="flex min-w-0 flex-col gap-1 md:col-span-2">
									<label for="family-policy-campaign-message" class="type-label leading-tight"
										>Portal note (optional)</label
									>
									<textarea
										id="family-policy-campaign-message"
										v-model="form.message"
										rows="3"
										class="if-textarea"
										:disabled="busyPublish"
										placeholder="Add a short note above the policy action link."
									/>
								</div>
							</section>

							<section class="rounded-2xl border border-slate-200 bg-white px-4 py-4 shadow-soft">
								<div class="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
									<div>
										<p class="type-body-strong text-ink">Campaign scope</p>
										<p class="mt-1 type-caption text-slate-500">{{ scopeSummary }}</p>
									</div>
									<p v-if="busyOptions" class="type-caption text-slate-500">Refreshing preview…</p>
								</div>

								<div v-if="availableAudiences.length" class="mt-4 flex flex-wrap gap-3">
									<label
										v-for="audience in availableAudiences"
										:key="audience"
										class="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-2 type-caption text-ink"
									>
										<input
											:checked="selectedAudiences.includes(audience)"
											type="checkbox"
											class="h-4 w-4"
											:disabled="busyPublish"
											@change="toggleAudience(audience, $event)"
										/>
										<span>{{ audienceLabel(audience) }}</span>
									</label>
								</div>
								<p
									v-else
									class="mt-4 rounded-xl border border-dashed border-slate-300 px-3 py-4 type-caption text-slate-500"
								>
									Select organization and policy version to preview family audiences.
								</p>

								<div v-if="audiencePreviews.length" class="mt-4 grid gap-3 lg:grid-cols-2">
									<article
										v-for="audience in audiencePreviews"
										:key="audience.audience"
										class="rounded-xl border px-3 py-3"
										:class="
											selectedAudiences.includes(audience.audience)
												? 'border-jacaranda/35 bg-jacaranda/5'
												: 'border-slate-200 bg-slate-50'
										"
									>
										<div class="flex items-start justify-between gap-3">
											<div>
												<p class="type-body-strong text-ink">{{ audience.audience_label }}</p>
												<p class="mt-1 type-caption text-slate-500">
													{{ audience.workflow_description }}
												</p>
											</div>
											<span
												class="rounded-full px-2 py-1 type-caption"
												:class="
													selectedAudiences.includes(audience.audience)
														? 'bg-jacaranda/12 text-jacaranda'
														: 'bg-white text-slate-500'
												"
											>
												{{
													selectedAudiences.includes(audience.audience) ? 'Selected' : 'Optional'
												}}
											</span>
										</div>
										<div class="mt-3 grid grid-cols-2 gap-2">
											<div>
												<p class="type-caption text-slate-500">Eligible</p>
												<p class="type-body-strong text-ink">{{ audience.eligible_targets }}</p>
											</div>
											<div>
												<p class="type-caption text-slate-500">Signed</p>
												<p class="type-body-strong text-ink">{{ audience.signed }}</p>
											</div>
											<div>
												<p class="type-caption text-slate-500">Pending</p>
												<p class="type-body-strong text-ink">{{ audience.pending }}</p>
											</div>
											<div>
												<p class="type-caption text-slate-500">Completion</p>
												<p class="type-body-strong text-ink">{{ audience.completion_pct }}%</p>
											</div>
										</div>
									</article>
								</div>

								<p
									v-if="availableAudiences.length && selectedPendingTotal <= 0"
									class="mt-4 rounded-xl border border-sand/70 bg-sand/30 px-3 py-2 type-caption text-clay"
								>
									Everyone in the selected family scope has already acknowledged this policy.
								</p>
							</section>
						</div>

						<div
							class="if-overlay__footer flex flex-col gap-3 px-6 pb-6 sm:flex-row sm:items-center sm:justify-between"
						>
							<p class="type-caption text-ink/55">
								Selected audiences cover {{ selectedPendingTotal }} pending acknowledgements.
							</p>
							<div
								class="flex w-full flex-col-reverse gap-2 sm:w-auto sm:flex-row sm:items-center"
							>
								<button
									type="button"
									class="w-full rounded-full border border-border/70 bg-white px-4 py-2 type-caption text-ink/70 sm:w-auto"
									@click="emitClose('programmatic')"
								>
									Cancel
								</button>
								<button
									type="button"
									class="w-full rounded-full bg-ink px-5 py-2 type-button-label text-white shadow-soft disabled:opacity-50 sm:w-auto"
									:disabled="!canPublish || busyPublish"
									@click="publishCampaign"
								>
									{{ busyPublish ? 'Publishing…' : 'Publish family campaign' }}
								</button>
							</div>
						</div>
					</DialogPanel>
				</TransitionChild>
			</div>
		</Dialog>
	</TransitionRoot>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue';
import {
	Dialog,
	DialogPanel,
	DialogTitle,
	TransitionChild,
	TransitionRoot,
} from '@headlessui/vue';
import { FeatherIcon } from 'frappe-ui';

import { createPolicySignatureService } from '@/lib/services/policySignature/policySignatureService';

import type { PolicyOption } from '@/types/contracts/policy_signature/get_staff_policy_campaign_options';
import type {
	FamilyAudiencePreview,
	FamilyPolicyCampaignAudience,
} from '@/types/contracts/policy_signature/get_family_policy_campaign_options';
import type { Response as PublishFamilyCampaignResponse } from '@/types/contracts/policy_signature/publish_family_policy_campaign';

type CloseReason = 'backdrop' | 'esc' | 'programmatic';

const props = defineProps<{
	open: boolean;
	zIndex?: number;
	organization?: string;
	school?: string;
	policy_version?: string;
}>();
const emit = defineEmits<{
	(e: 'close', reason: CloseReason): void;
	(e: 'after-leave'): void;
}>();

const service = createPolicySignatureService();

const closeBtnEl = ref<HTMLButtonElement | null>(null);
const busyOptions = ref(false);
const busyPublish = ref(false);
const errorMessage = ref('');
const successMessage = ref('');
const publishedCommunications = ref<PublishFamilyCampaignResponse['communications']>([]);

const options = reactive<{
	organizations: string[];
	schools: string[];
	policies: PolicyOption[];
}>({
	organizations: [],
	schools: [],
	policies: [],
});

const preview = reactive<{
	family_audiences: FamilyPolicyCampaignAudience[];
	school_target_count: number;
	audience_previews: FamilyAudiencePreview[];
}>({
	family_audiences: [],
	school_target_count: 0,
	audience_previews: [],
});

const form = reactive<{
	organization: string;
	school: string;
	policy_version: string;
	audiences: FamilyPolicyCampaignAudience[];
	title: string;
	message: string;
	publish_to: string;
}>({
	organization: '',
	school: '',
	policy_version: '',
	audiences: [],
	title: '',
	message: '',
	publish_to: '',
});

const overlayStyle = computed(() => ({
	zIndex: props.zIndex || 0,
}));

const availableAudiences = computed(() => preview.family_audiences || []);
const audiencePreviews = computed(() => preview.audience_previews || []);
const selectedAudiences = computed(() => form.audiences || []);
const selectedPendingTotal = computed(() =>
	selectedAudiences.value.reduce((total, audience) => {
		const previewRow = audiencePreviews.value.find(row => row.audience === audience);
		return total + (previewRow?.pending || 0);
	}, 0)
);
const canPublish = computed(() => {
	if (!form.organization || !form.policy_version) return false;
	if (!selectedAudiences.value.length) return false;
	if (selectedPendingTotal.value <= 0) return false;
	return true;
});
const scopeSummary = computed(() => {
	if (!form.organization) return 'Choose an organization before publishing family notices.';
	if (form.school) {
		return `Campaign stays inside ${form.school} and any child schools in that branch.`;
	}
	if (!preview.school_target_count) {
		return 'No schools are available in the selected organization scope yet.';
	}
	if (preview.school_target_count === 1) {
		return 'Campaign reaches 1 school in the selected organization tree.';
	}
	return `Campaign reaches ${preview.school_target_count} schools in the selected organization tree.`;
});

let refreshTimer: ReturnType<typeof setTimeout> | null = null;

function resetFeedback() {
	errorMessage.value = '';
	successMessage.value = '';
	publishedCommunications.value = [];
}

function emitClose(reason: CloseReason = 'programmatic') {
	emit('close', reason);
}

function emitAfterLeave() {
	resetFeedback();
	emit('after-leave');
}

function onDialogClose(_payload: unknown) {
	// no-op by design
}

function policyLabel(policy: PolicyOption) {
	const title =
		(policy.policy_title || '').trim() ||
		(policy.policy_key || '').trim() ||
		policy.policy_version;
	const version = (policy.version_label || '').trim();
	return version ? `${title} (${version})` : title;
}

function audienceLabel(audience: FamilyPolicyCampaignAudience) {
	return audience === 'Guardian' ? 'Guardians' : 'Students';
}

function applyInitialContext() {
	form.organization = (props.organization || '').trim();
	form.school = (props.school || '').trim();
	form.policy_version = (props.policy_version || '').trim();
	form.audiences = [];
	form.title = '';
	form.message = '';
	form.publish_to = '';
}

function normalizeSelection() {
	if (form.school && !options.schools.includes(form.school)) form.school = '';
	if (
		form.policy_version &&
		!options.policies.some(policy => policy.policy_version === form.policy_version)
	) {
		form.policy_version = '';
	}

	const available = new Set(availableAudiences.value);
	form.audiences = form.audiences.filter(audience => available.has(audience));
	if (!form.audiences.length && availableAudiences.value.length) {
		form.audiences = [...availableAudiences.value];
	}
}

async function refreshOptions() {
	if (!props.open) return;

	busyOptions.value = true;
	errorMessage.value = '';
	try {
		const response = await service.getFamilyCampaignOptions({
			organization: form.organization || null,
			school: form.school || null,
			policy_version: form.policy_version || null,
		});

		options.organizations = [...(response.options?.organizations || [])];
		options.schools = [...(response.options?.schools || [])];
		options.policies = [...(response.options?.policies || [])];
		preview.family_audiences = [...(response.preview?.family_audiences || [])];
		preview.school_target_count = response.preview?.school_target_count || 0;
		preview.audience_previews = [...(response.preview?.audience_previews || [])];

		if (!form.organization && options.organizations.length === 1) {
			form.organization = options.organizations[0];
		}

		normalizeSelection();
	} catch (err: unknown) {
		errorMessage.value =
			err instanceof Error && err.message
				? err.message
				: 'Unable to load family campaign options.';
	} finally {
		busyOptions.value = false;
	}
}

function scheduleRefresh() {
	if (refreshTimer) clearTimeout(refreshTimer);
	refreshTimer = setTimeout(() => {
		void refreshOptions();
	}, 220);
}

function newClientRequestId(prefix = 'req') {
	return `${prefix}_${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

function toggleAudience(audience: FamilyPolicyCampaignAudience, event: Event) {
	const checked = (event.target as HTMLInputElement).checked;
	const next = new Set(form.audiences);
	if (checked) next.add(audience);
	else next.delete(audience);
	form.audiences = Array.from(next);
}

async function publishCampaign() {
	if (busyPublish.value) return;

	resetFeedback();

	if (!form.organization) {
		errorMessage.value = 'Organization is required.';
		return;
	}
	if (!form.policy_version) {
		errorMessage.value = 'Policy Version is required.';
		return;
	}
	if (!form.audiences.length) {
		errorMessage.value = 'Select at least one family audience.';
		return;
	}
	if (selectedPendingTotal.value <= 0) {
		errorMessage.value =
			'There are no pending acknowledgements left in the selected family scope.';
		return;
	}

	busyPublish.value = true;
	try {
		const response = await service.publishFamilyCampaign({
			organization: form.organization,
			school: form.school || null,
			policy_version: form.policy_version,
			audiences: [...form.audiences],
			title: form.title.trim() ? form.title.trim() : null,
			message: form.message.trim() ? form.message.trim() : null,
			publish_to: form.publish_to || null,
			client_request_id: newClientRequestId('family_policy_campaign'),
		});
		publishedCommunications.value = [...(response.communications || [])];
		successMessage.value =
			response.counts?.published === 1
				? `Published 1 family campaign communication for ${response.counts.pending} pending acknowledgement${response.counts.pending === 1 ? '' : 's'}.`
				: `Published ${response.counts?.published || 0} family campaign communications for ${response.counts?.pending || 0} pending acknowledgements.`;
		await refreshOptions();
	} catch (err: unknown) {
		errorMessage.value =
			err instanceof Error && err.message ? err.message : 'Unable to publish the family campaign.';
	} finally {
		busyPublish.value = false;
	}
}

watch(
	() => props.open,
	next => {
		if (!next) return;
		applyInitialContext();
		resetFeedback();
		void refreshOptions();
	},
	{ immediate: true }
);

watch(
	() => [form.organization, form.school, form.policy_version],
	() => {
		if (!props.open) return;
		scheduleRefresh();
	}
);

onBeforeUnmount(() => {
	if (refreshTimer) clearTimeout(refreshTimer);
});
</script>
