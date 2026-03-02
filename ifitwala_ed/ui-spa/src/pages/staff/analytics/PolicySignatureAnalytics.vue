<!-- ifitwala_ed/ui-spa/src/pages/staff/analytics/PolicySignatureAnalytics.vue -->
<template>
	<div class="analytics-shell space-y-5">
		<header class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
			<div>
				<h1 class="type-h2 text-canopy">Policy Signatures</h1>
				<p class="type-caption text-slate-500">
					Track who has acknowledged each policy version and launch targeted follow-up tasks.
				</p>
			</div>
			<button
				v-if="canManageCampaigns"
				type="button"
				class="inline-flex items-center gap-2 rounded-full bg-ink px-4 py-2 type-button-label text-white shadow-soft disabled:opacity-50"
				@click="openCampaignOverlay"
			>
				<FeatherIcon name="plus" class="h-4 w-4" />
				<span>Create campaign</span>
			</button>
		</header>

		<FiltersBar class="analytics-filters">
			<div class="flex flex-col gap-1">
				<label class="type-label">Organization</label>
				<select
					v-model="filters.organization"
					class="h-9 min-w-[180px] rounded-md border px-2 text-sm"
					:disabled="loadingOptions"
				>
					<option value="">Select organization</option>
					<option v-for="org in options.organizations" :key="org" :value="org">
						{{ org }}
					</option>
				</select>
			</div>

			<div class="flex flex-col gap-1">
				<label class="type-label">School</label>
				<select
					v-model="filters.school"
					class="h-9 min-w-[180px] rounded-md border px-2 text-sm"
					:disabled="loadingOptions || !filters.organization"
				>
					<option value="">All schools</option>
					<option v-for="school in options.schools" :key="school" :value="school">
						{{ school }}
					</option>
				</select>
			</div>

			<div class="flex flex-col gap-1">
				<label class="type-label">Employee Group</label>
				<select
					v-model="filters.employee_group"
					class="h-9 min-w-[170px] rounded-md border px-2 text-sm"
					:disabled="loadingOptions || !filters.organization"
				>
					<option value="">All groups</option>
					<option v-for="group in options.employee_groups" :key="group" :value="group">
						{{ group }}
					</option>
				</select>
			</div>

			<div class="flex flex-col gap-1">
				<label class="type-label">Policy Version</label>
				<select
					v-model="filters.policy_version"
					class="h-9 min-w-[280px] rounded-md border px-2 text-sm"
					:disabled="loadingOptions || !filters.organization"
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
		</FiltersBar>

		<div v-if="accessDenied" class="rounded-md border border-amber-200 bg-amber-50 px-4 py-3">
			<h2 class="text-sm font-semibold text-amber-900">Access restricted</h2>
			<p class="mt-1 text-xs text-amber-800">
				You do not have permission to view policy signature analytics.
			</p>
		</div>

		<div
			v-else-if="errorMessage"
			class="rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-900"
		>
			{{ errorMessage }}
		</div>

		<div
			v-else-if="!filters.policy_version"
			class="rounded-md border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600"
		>
			Select a policy version to load signature status.
		</div>

		<div v-else-if="loadingDashboard" class="py-10 text-center text-sm text-slate-500">
			Loading policy signature analytics...
		</div>

		<div v-else-if="dashboard" class="space-y-5">
			<KpiRow :items="kpis" />

			<section class="grid grid-cols-1 gap-4 xl:grid-cols-3">
				<article class="analytics-card">
					<h3 class="analytics-card__title">By Organization</h3>
					<table class="w-full mt-3 text-sm">
						<thead>
							<tr class="text-left text-slate-500">
								<th class="pb-2 pr-2">Organization</th>
								<th class="pb-2 pr-2">Signed</th>
								<th class="pb-2 pr-2">Pending</th>
								<th class="pb-2 text-right">Completion</th>
							</tr>
						</thead>
						<tbody>
							<tr
								v-for="row in dashboard.breakdowns.by_organization"
								:key="`org_${row.label}`"
								class="border-t border-slate-100"
							>
								<td class="py-2 pr-2">{{ row.label }}</td>
								<td class="py-2 pr-2">{{ row.signed }}</td>
								<td class="py-2 pr-2">{{ row.pending }}</td>
								<td class="py-2 text-right">{{ row.completion_pct }}%</td>
							</tr>
						</tbody>
					</table>
				</article>

				<article class="analytics-card">
					<h3 class="analytics-card__title">By School</h3>
					<table class="w-full mt-3 text-sm">
						<thead>
							<tr class="text-left text-slate-500">
								<th class="pb-2 pr-2">School</th>
								<th class="pb-2 pr-2">Signed</th>
								<th class="pb-2 pr-2">Pending</th>
								<th class="pb-2 text-right">Completion</th>
							</tr>
						</thead>
						<tbody>
							<tr
								v-for="row in dashboard.breakdowns.by_school"
								:key="`school_${row.label}`"
								class="border-t border-slate-100"
							>
								<td class="py-2 pr-2">{{ row.label }}</td>
								<td class="py-2 pr-2">{{ row.signed }}</td>
								<td class="py-2 pr-2">{{ row.pending }}</td>
								<td class="py-2 text-right">{{ row.completion_pct }}%</td>
							</tr>
						</tbody>
					</table>
				</article>

				<article class="analytics-card">
					<h3 class="analytics-card__title">By Employee Group</h3>
					<table class="w-full mt-3 text-sm">
						<thead>
							<tr class="text-left text-slate-500">
								<th class="pb-2 pr-2">Group</th>
								<th class="pb-2 pr-2">Signed</th>
								<th class="pb-2 pr-2">Pending</th>
								<th class="pb-2 text-right">Completion</th>
							</tr>
						</thead>
						<tbody>
							<tr
								v-for="row in dashboard.breakdowns.by_employee_group"
								:key="`group_${row.label}`"
								class="border-t border-slate-100"
							>
								<td class="py-2 pr-2">{{ row.label }}</td>
								<td class="py-2 pr-2">{{ row.signed }}</td>
								<td class="py-2 pr-2">{{ row.pending }}</td>
								<td class="py-2 text-right">{{ row.completion_pct }}%</td>
							</tr>
						</tbody>
					</table>
				</article>
			</section>

			<section class="grid grid-cols-1 gap-4 xl:grid-cols-2">
				<article class="analytics-card">
					<h3 class="analytics-card__title">Pending Signatures</h3>
					<p class="analytics-card__meta mt-1">
						Employees who still need to acknowledge this policy.
					</p>
					<div class="mt-3 overflow-auto">
						<table class="w-full text-sm">
							<thead>
								<tr class="text-left text-slate-500">
									<th class="pb-2 pr-2">Employee</th>
									<th class="pb-2 pr-2">Organization</th>
									<th class="pb-2 pr-2">School</th>
									<th class="pb-2">Group</th>
								</tr>
							</thead>
							<tbody>
								<tr
									v-for="row in dashboard.rows.pending"
									:key="`pending_${row.employee}`"
									class="border-t border-slate-100"
								>
									<td class="py-2 pr-2">{{ row.employee_name }}</td>
									<td class="py-2 pr-2">{{ row.organization || '-' }}</td>
									<td class="py-2 pr-2">{{ row.school || '-' }}</td>
									<td class="py-2">{{ row.employee_group || '-' }}</td>
								</tr>
								<tr v-if="dashboard.rows.pending.length === 0">
									<td class="py-3 text-slate-500" colspan="4">No pending signatures.</td>
								</tr>
							</tbody>
						</table>
					</div>
				</article>

				<article class="analytics-card">
					<h3 class="analytics-card__title">Signed</h3>
					<p class="analytics-card__meta mt-1">
						Most recent acknowledgements for this policy version.
					</p>
					<div class="mt-3 overflow-auto">
						<table class="w-full text-sm">
							<thead>
								<tr class="text-left text-slate-500">
									<th class="pb-2 pr-2">Employee</th>
									<th class="pb-2 pr-2">Acknowledged At</th>
									<th class="pb-2">Acknowledged By</th>
								</tr>
							</thead>
							<tbody>
								<tr
									v-for="row in dashboard.rows.signed"
									:key="`signed_${row.employee}`"
									class="border-t border-slate-100"
								>
									<td class="py-2 pr-2">{{ row.employee_name }}</td>
									<td class="py-2 pr-2">{{ row.acknowledged_at || '-' }}</td>
									<td class="py-2">{{ row.acknowledged_by || '-' }}</td>
								</tr>
								<tr v-if="dashboard.rows.signed.length === 0">
									<td class="py-3 text-slate-500" colspan="3">No signatures captured yet.</td>
								</tr>
							</tbody>
						</table>
					</div>
				</article>
			</section>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { FeatherIcon } from 'frappe-ui';

import FiltersBar from '@/components/filters/FiltersBar.vue';
import KpiRow from '@/components/analytics/KpiRow.vue';
import { useOverlayStack } from '@/composables/useOverlayStack';
import { createPolicySignatureService } from '@/lib/services/policySignature/policySignatureService';
import { getStaffHomeHeader } from '@/lib/services/staff/staffHomeService';

import type { PolicyOption } from '@/types/contracts/policy_signature/get_staff_policy_campaign_options';
import type { Response as DashboardResponse } from '@/types/contracts/policy_signature/get_staff_policy_signature_dashboard';

const route = useRoute();
const overlay = useOverlayStack();
const policyService = createPolicySignatureService();

const accessDenied = ref(false);
const loadingOptions = ref(false);
const loadingDashboard = ref(false);
const errorMessage = ref('');
const canManageCampaigns = ref(false);

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

const filters = reactive({
	organization: '',
	school: '',
	employee_group: '',
	policy_version: '',
});

const dashboard = ref<DashboardResponse | null>(null);

let refreshTimer: ReturnType<typeof setTimeout> | null = null;

const kpis = computed(() => {
	const summary = dashboard.value?.summary;
	if (!summary) return [];
	return [
		{ id: 'eligible_users', label: 'Eligible Employees', value: summary.eligible_users },
		{ id: 'signed', label: 'Signed', value: summary.signed },
		{ id: 'pending', label: 'Pending', value: summary.pending },
		{
			id: 'completion_pct',
			label: 'Completion',
			value: `${summary.completion_pct}%`,
			hint: `${summary.skipped_scope} skipped`,
		},
	];
});

function policyLabel(policy: PolicyOption) {
	const title =
		(policy.policy_title || '').trim() ||
		(policy.policy_key || '').trim() ||
		policy.policy_version;
	const version = (policy.version_label || '').trim();
	return version ? `${title} (v${version})` : title;
}

function normalizeSelection() {
	if (filters.school && !options.schools.includes(filters.school)) filters.school = '';
	if (filters.employee_group && !options.employee_groups.includes(filters.employee_group)) {
		filters.employee_group = '';
	}
	if (
		filters.policy_version &&
		!options.policies.some(policy => policy.policy_version === filters.policy_version)
	) {
		filters.policy_version = '';
	}
}

function prefillFromRoute() {
	filters.organization = String(route.query.organization || '').trim();
	filters.school = String(route.query.school || '').trim();
	filters.employee_group = String(route.query.employee_group || '').trim();
	filters.policy_version = String(route.query.policy_version || '').trim();
}

async function loadCapabilities() {
	try {
		const header = await getStaffHomeHeader();
		canManageCampaigns.value = Boolean(header?.capabilities?.manage_policy_signatures);
	} catch {
		canManageCampaigns.value = false;
	}
}

async function refreshOptions() {
	loadingOptions.value = true;
	errorMessage.value = '';
	try {
		const response = await policyService.getCampaignOptions({
			organization: filters.organization || null,
			school: filters.school || null,
			employee_group: filters.employee_group || null,
			policy_version: filters.policy_version || null,
		});
		options.organizations = [...(response.options?.organizations || [])];
		options.schools = [...(response.options?.schools || [])];
		options.employee_groups = [...(response.options?.employee_groups || [])];
		options.policies = [...(response.options?.policies || [])];

		if (!filters.organization && options.organizations.length === 1) {
			filters.organization = options.organizations[0];
		}

		normalizeSelection();
		accessDenied.value = false;
	} catch (err: unknown) {
		const message = err instanceof Error && err.message ? err.message : 'Unable to load filters.';
		errorMessage.value = message;
		accessDenied.value = true;
	} finally {
		loadingOptions.value = false;
	}
}

async function loadDashboard() {
	if (!filters.policy_version) {
		dashboard.value = null;
		return;
	}

	loadingDashboard.value = true;
	errorMessage.value = '';
	try {
		const response = await policyService.getDashboard({
			policy_version: filters.policy_version,
			organization: filters.organization || null,
			school: filters.school || null,
			employee_group: filters.employee_group || null,
			limit: 200,
		});
		dashboard.value = response;
		accessDenied.value = false;
	} catch (err: unknown) {
		dashboard.value = null;
		const message =
			err instanceof Error && err.message ? err.message : 'Unable to load dashboard.';
		errorMessage.value = message;
	} finally {
		loadingDashboard.value = false;
	}
}

function scheduleRefresh() {
	if (refreshTimer) clearTimeout(refreshTimer);
	refreshTimer = setTimeout(async () => {
		await refreshOptions();
		await loadDashboard();
	}, 220);
}

function openCampaignOverlay() {
	overlay.open('staff-policy-signature-campaign', {});
}

watch(
	() => [filters.organization, filters.school, filters.employee_group, filters.policy_version],
	() => {
		scheduleRefresh();
	}
);

onMounted(async () => {
	prefillFromRoute();
	await Promise.all([loadCapabilities(), refreshOptions()]);
	await loadDashboard();
});

onBeforeUnmount(() => {
	if (refreshTimer) clearTimeout(refreshTimer);
});
</script>
