<!-- ifitwala_ed/ui-spa/src/overlays/staff/StaffPolicyCampaignOverlay.vue -->
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
								<DialogTitle class="type-h2 text-ink">Policy Signature Campaign</DialogTitle>
								<p class="mt-1 type-caption text-ink/60">
									Review audience coverage before launch. Staff audiences use internal tasks;
									guardian and student audiences are tracked through their portals.
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

						<div class="if-overlay__body px-6 pb-6 space-y-5">
							<div
								v-if="errorMessage"
								class="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 shadow-soft"
								role="alert"
							>
								<p class="type-body-strong text-rose-900">Unable to process this request</p>
								<p class="mt-1 type-caption text-rose-900/80 whitespace-pre-wrap">
									{{ errorMessage }}
								</p>
							</div>

							<div
								v-if="successMessage"
								class="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 shadow-soft"
							>
								<p class="type-body-strong text-emerald-900">{{ successMessage }}</p>
								<p class="mt-1 type-caption text-emerald-900/80">
									Employees will see this in Focus as a policy acknowledgement action.
								</p>
							</div>

							<section class="grid gap-4 md:grid-cols-2">
								<div class="flex min-w-0 flex-col gap-1">
									<label for="policy-campaign-organization" class="type-label leading-tight"
										>Organization</label
									>
									<select
										id="policy-campaign-organization"
										v-model="form.organization"
										class="if-overlay__input"
										:disabled="busyOptions || busyLaunch"
									>
										<option value="">Select organization</option>
										<option v-for="org in options.organizations" :key="org" :value="org">
											{{ org }}
										</option>
									</select>
								</div>

								<div class="flex min-w-0 flex-col gap-1">
									<label for="policy-campaign-school" class="type-label leading-tight"
										>School (optional)</label
									>
									<select
										id="policy-campaign-school"
										v-model="form.school"
										class="if-overlay__input"
										:disabled="busyOptions || busyLaunch || !form.organization"
									>
										<option value="">All schools in scope</option>
										<option v-for="school in options.schools" :key="school" :value="school">
											{{ school }}
										</option>
									</select>
								</div>

								<div class="flex min-w-0 flex-col gap-1">
									<label for="policy-campaign-employee-group" class="type-label leading-tight"
										>Employee Group (optional)</label
									>
									<select
										id="policy-campaign-employee-group"
										v-model="form.employee_group"
										class="if-overlay__input"
										:disabled="busyOptions || busyLaunch || !form.organization"
									>
										<option value="">All groups</option>
										<option v-for="group in options.employee_groups" :key="group" :value="group">
											{{ group }}
										</option>
									</select>
								</div>

								<div class="flex min-w-0 flex-col gap-1">
									<label for="policy-campaign-policy-version" class="type-label leading-tight"
										>Policy Version</label
									>
									<select
										id="policy-campaign-policy-version"
										v-model="form.policy_version"
										class="if-overlay__input"
										:disabled="busyOptions || busyLaunch || !form.organization"
									>
										<option value="">Select policy version</option>
										<option
											v-for="policy in options.policies"
											:key="policy.policy_version"
											:value="policy.policy_version"
										>
											{{ policyLabel(policy) }}
										</option>
									</select>
								</div>

								<div class="flex min-w-0 flex-col gap-1">
									<label for="policy-campaign-due-date" class="type-label leading-tight"
										>Due Date (optional)</label
									>
									<input
										id="policy-campaign-due-date"
										v-model="form.due_date"
										type="date"
										class="if-overlay__input"
										:disabled="busyLaunch"
									/>
								</div>

								<div class="flex min-w-0 flex-col gap-1 md:col-span-2">
									<label for="policy-campaign-message" class="type-label leading-tight"
										>Assignment Message (optional)</label
									>
									<textarea
										id="policy-campaign-message"
										v-model="form.message"
										rows="3"
										class="if-textarea"
										:disabled="busyLaunch"
										placeholder="Optional note shown in the assigned ToDo."
									/>
								</div>
							</section>

							<section class="rounded-2xl border border-slate-200 bg-white px-4 py-4 shadow-soft">
								<div class="flex items-center justify-between gap-3">
									<p class="type-body-strong text-ink">Audience preview</p>
									<p v-if="busyOptions" class="type-caption text-slate-500">Refreshing preview…</p>
								</div>
								<div v-if="preview.policy_audiences.length" class="mt-3 flex flex-wrap gap-2">
									<span
										v-for="audience in preview.policy_audiences"
										:key="audience"
										class="rounded-full bg-slate-100 px-3 py-1 type-caption text-slate-700"
									>
										{{ audience }}
									</span>
								</div>
								<div class="mt-3 grid gap-3 lg:grid-cols-3">
									<article
										v-for="audience in audiencePreviews"
										:key="audience.audience"
										class="rounded-xl border border-slate-200 bg-slate-50 px-3 py-3"
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
													audience.supports_campaign_launch
														? 'bg-jacaranda/10 text-jacaranda'
														: 'bg-white text-slate-500'
												"
											>
												{{ audience.supports_campaign_launch ? 'Launchable' : 'Tracked only' }}
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
												<p class="type-caption text-slate-500">
													{{ audience.supports_campaign_launch ? 'To create' : 'Skipped' }}
												</p>
												<p class="type-body-strong text-ink">
													{{
														audience.supports_campaign_launch
															? audience.to_create
															: audience.skipped_scope
													}}
												</p>
											</div>
										</div>
									</article>
									<div
										v-if="!audiencePreviews.length"
										class="rounded-xl border border-dashed border-slate-300 px-3 py-4 type-caption text-slate-500"
									>
										Select organization and policy version to preview audience coverage.
									</div>
								</div>
							</section>
						</div>

						<div
							class="if-overlay__footer flex flex-col gap-3 px-6 pb-6 sm:flex-row sm:items-center sm:justify-between"
						>
							<RouterLink
								v-if="canOpenAnalytics"
								:to="analyticsRoute"
								target="_blank"
								rel="noopener"
								class="type-caption text-jacaranda hover:underline"
							>
								Open signature dashboard
							</RouterLink>
							<span v-else class="type-caption text-ink/50"
								>Select organization and policy first.</span
							>

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
									:disabled="!canLaunch || busyLaunch"
									@click="launchCampaign"
								>
									{{ busyLaunch ? 'Creating…' : 'Create staff signature tasks' }}
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
import { RouterLink } from 'vue-router';
import {
	Dialog,
	DialogPanel,
	DialogTitle,
	TransitionChild,
	TransitionRoot,
} from '@headlessui/vue';
import { FeatherIcon } from 'frappe-ui';

import { createPolicySignatureService } from '@/lib/services/policySignature/policySignatureService';

import type {
	PolicyOption,
	PreviewCounts,
} from '@/types/contracts/policy_signature/get_staff_policy_campaign_options';
import type { Request as LaunchCampaignRequest } from '@/types/contracts/policy_signature/launch_staff_policy_campaign';

type CloseReason = 'backdrop' | 'esc' | 'programmatic';

const props = defineProps<{
	open: boolean;
	zIndex?: number;
	organization?: string;
	school?: string;
	employee_group?: string;
	policy_version?: string;
}>();
const emit = defineEmits<{
	(e: 'close', reason: CloseReason): void;
	(e: 'after-leave'): void;
}>();

const service = createPolicySignatureService();

const closeBtnEl = ref<HTMLButtonElement | null>(null);
const busyOptions = ref(false);
const busyLaunch = ref(false);
const errorMessage = ref('');
const successMessage = ref('');

const options = reactive<{
	organizations: string[];
	schools: string[];
	employee_groups: string[];
	policies: PolicyOption[];
}>({
	organizations: [],
	schools: [],
	employee_groups: [],
	policies: [],
});

const preview = reactive<PreviewCounts>({
	target_employee_rows: 0,
	eligible_users: 0,
	already_signed: 0,
	already_open: 0,
	to_create: 0,
	skipped_scope: 0,
	policy_audiences: [],
	audience_previews: [],
});

const form = reactive({
	organization: '',
	school: '',
	employee_group: '',
	policy_version: '',
	due_date: '',
	message: '',
});

const overlayStyle = computed(() => ({
	zIndex: props.zIndex || 0,
}));

const audiencePreviews = computed(() => preview.audience_previews || []);

const staffAudiencePreview = computed(() => {
	return audiencePreviews.value.find(audience => audience.audience === 'Staff') || null;
});

const canOpenAnalytics = computed(() => {
	return !!form.organization && !!form.policy_version;
});

const analyticsRoute = computed(() => ({
	name: 'staff-policy-signature-analytics',
	query: {
		organization: form.organization || undefined,
		school: form.school || undefined,
		employee_group: form.employee_group || undefined,
		policy_version: form.policy_version || undefined,
	},
}));

const canLaunch = computed(() => {
	if (!form.organization || !form.policy_version) return false;
	if (!staffAudiencePreview.value?.supports_campaign_launch) return false;
	if (preview.to_create <= 0) return false;
	return true;
});

let refreshTimer: ReturnType<typeof setTimeout> | null = null;

function resetFeedback() {
	errorMessage.value = '';
	successMessage.value = '';
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
	return version ? `${title} (v${version})` : title;
}

function normalizeSelection() {
	if (form.school && !options.schools.includes(form.school)) form.school = '';
	if (form.employee_group && !options.employee_groups.includes(form.employee_group)) {
		form.employee_group = '';
	}
	if (
		form.policy_version &&
		!options.policies.some(p => p.policy_version === form.policy_version)
	) {
		form.policy_version = '';
	}
}

function applyInitialContext() {
	form.organization = (props.organization || '').trim();
	form.school = (props.school || '').trim();
	form.employee_group = (props.employee_group || '').trim();
	form.policy_version = (props.policy_version || '').trim();
	form.due_date = '';
	form.message = '';
}

async function refreshOptions() {
	if (!props.open) return;

	busyOptions.value = true;
	errorMessage.value = '';
	try {
		const response = await service.getCampaignOptions({
			organization: form.organization || null,
			school: form.school || null,
			employee_group: form.employee_group || null,
			policy_version: form.policy_version || null,
		});

		options.organizations = [...(response.options?.organizations || [])];
		options.schools = [...(response.options?.schools || [])];
		options.employee_groups = [...(response.options?.employee_groups || [])];
		options.policies = [...(response.options?.policies || [])];
		preview.target_employee_rows = response.preview?.target_employee_rows || 0;
		preview.eligible_users = response.preview?.eligible_users || 0;
		preview.already_signed = response.preview?.already_signed || 0;
		preview.already_open = response.preview?.already_open || 0;
		preview.to_create = response.preview?.to_create || 0;
		preview.skipped_scope = response.preview?.skipped_scope || 0;
		preview.policy_audiences = [...(response.preview?.policy_audiences || [])];
		preview.audience_previews = [...(response.preview?.audience_previews || [])];

		if (!form.organization && options.organizations.length === 1) {
			form.organization = options.organizations[0];
		}

		normalizeSelection();
	} catch (err: unknown) {
		errorMessage.value =
			err instanceof Error && err.message ? err.message : 'Unable to load options.';
	} finally {
		busyOptions.value = false;
	}
}

function scheduleRefresh() {
	if (refreshTimer) clearTimeout(refreshTimer);
	refreshTimer = setTimeout(() => {
		refreshOptions();
	}, 220);
}

function newClientRequestId(prefix = 'req') {
	return `${prefix}_${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

async function launchCampaign() {
	if (busyLaunch.value) return;

	resetFeedback();

	if (!form.organization) {
		errorMessage.value = 'Organization is required.';
		return;
	}
	if (!form.policy_version) {
		errorMessage.value = 'Policy Version is required.';
		return;
	}
	if (preview.to_create <= 0) {
		errorMessage.value = 'No eligible employees need new tasks for this scope.';
		return;
	}

	busyLaunch.value = true;
	try {
		const payload: LaunchCampaignRequest = {
			organization: form.organization,
			policy_version: form.policy_version,
			school: form.school || null,
			employee_group: form.employee_group || null,
			due_date: form.due_date || null,
			message: form.message?.trim() ? form.message.trim() : null,
			client_request_id: newClientRequestId('policy_campaign'),
		};
		const response = await service.launchCampaign(payload);
		const created = response.counts?.created || 0;
		successMessage.value =
			created > 0
				? `Created ${created} signature tasks successfully.`
				: 'No new tasks were created because everyone is already signed or already assigned.';
		await refreshOptions();
	} catch (err: unknown) {
		errorMessage.value =
			err instanceof Error && err.message ? err.message : 'Unable to launch campaign.';
	} finally {
		busyLaunch.value = false;
	}
}

watch(
	() => props.open,
	next => {
		if (!next) return;
		applyInitialContext();
		resetFeedback();
		refreshOptions();
	},
	{ immediate: true }
);

watch(
	() => [form.organization, form.school, form.employee_group, form.policy_version],
	() => {
		if (!props.open) return;
		scheduleRefresh();
	}
);

onBeforeUnmount(() => {
	if (refreshTimer) clearTimeout(refreshTimer);
});
</script>
