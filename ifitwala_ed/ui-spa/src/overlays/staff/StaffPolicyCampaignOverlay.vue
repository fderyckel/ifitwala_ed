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
						<div class="if-overlay__header px-6 pt-6">
							<div class="min-w-0">
								<DialogTitle class="type-h2 text-ink">Policy Signature Campaign</DialogTitle>
								<p class="mt-1 type-caption text-ink/60">
									Create internal signature tasks by organization, school, and employee group.
								</p>
							</div>
							<button
								ref="closeBtnEl"
								type="button"
								class="if-overlay__close"
								@click="emitClose('programmatic')"
								aria-label="Close"
							>
								<FeatherIcon name="x" class="h-5 w-5" />
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

							<section class="grid grid-cols-1 gap-4 md:grid-cols-2">
								<label class="space-y-1">
									<span class="type-label">Organization</span>
									<select
										v-model="form.organization"
										class="h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-sm"
										:disabled="busyOptions || busyLaunch"
									>
										<option value="">Select organization</option>
										<option v-for="org in options.organizations" :key="org" :value="org">
											{{ org }}
										</option>
									</select>
								</label>

								<label class="space-y-1">
									<span class="type-label">School (optional)</span>
									<select
										v-model="form.school"
										class="h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-sm"
										:disabled="busyOptions || busyLaunch || !form.organization"
									>
										<option value="">All schools in scope</option>
										<option v-for="school in options.schools" :key="school" :value="school">
											{{ school }}
										</option>
									</select>
								</label>

								<label class="space-y-1">
									<span class="type-label">Employee Group (optional)</span>
									<select
										v-model="form.employee_group"
										class="h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-sm"
										:disabled="busyOptions || busyLaunch || !form.organization"
									>
										<option value="">All groups</option>
										<option v-for="group in options.employee_groups" :key="group" :value="group">
											{{ group }}
										</option>
									</select>
								</label>

								<label class="space-y-1">
									<span class="type-label">Policy Version</span>
									<select
										v-model="form.policy_version"
										class="h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-sm"
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
								</label>

								<label class="space-y-1">
									<span class="type-label">Due Date (optional)</span>
									<input
										v-model="form.due_date"
										type="date"
										class="h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-sm"
										:disabled="busyLaunch"
									/>
								</label>

								<label class="space-y-1 md:col-span-2">
									<span class="type-label">Assignment Message (optional)</span>
									<textarea
										v-model="form.message"
										rows="3"
										class="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm"
										:disabled="busyLaunch"
										placeholder="Optional note shown in the assigned ToDo."
									/>
								</label>
							</section>

							<section class="rounded-2xl border border-slate-200 bg-white px-4 py-4 shadow-soft">
								<div class="flex items-center justify-between gap-3">
									<p class="type-body-strong text-ink">Campaign preview</p>
									<p v-if="busyOptions" class="type-caption text-slate-500">Refreshing preview…</p>
								</div>
								<div class="mt-3 grid grid-cols-2 gap-3 md:grid-cols-3">
									<div class="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2">
										<p class="type-caption text-slate-500">Targets</p>
										<p class="type-body-strong text-ink">{{ preview.target_employee_rows }}</p>
									</div>
									<div class="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2">
										<p class="type-caption text-slate-500">Eligible</p>
										<p class="type-body-strong text-ink">{{ preview.eligible_users }}</p>
									</div>
									<div class="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2">
										<p class="type-caption text-slate-500">To create</p>
										<p class="type-body-strong text-ink">{{ preview.to_create }}</p>
									</div>
									<div class="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2">
										<p class="type-caption text-slate-500">Already signed</p>
										<p class="type-body-strong text-ink">{{ preview.already_signed }}</p>
									</div>
									<div class="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2">
										<p class="type-caption text-slate-500">Already open</p>
										<p class="type-body-strong text-ink">{{ preview.already_open }}</p>
									</div>
									<div class="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2">
										<p class="type-caption text-slate-500">Out of scope</p>
										<p class="type-body-strong text-ink">{{ preview.skipped_scope }}</p>
									</div>
								</div>
							</section>
						</div>

						<div class="if-overlay__footer px-6 pb-6 flex items-center justify-between gap-3">
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

							<div class="flex items-center gap-2">
								<button
									type="button"
									class="rounded-full border border-border/70 bg-white px-4 py-2 type-caption text-ink/70"
									@click="emitClose('programmatic')"
								>
									Cancel
								</button>
								<button
									type="button"
									class="rounded-full bg-ink px-5 py-2 type-caption text-white shadow-soft disabled:opacity-50"
									:disabled="!canLaunch || busyLaunch"
									@click="launchCampaign"
								>
									{{ busyLaunch ? 'Creating…' : 'Create signature tasks' }}
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
