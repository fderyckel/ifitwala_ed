<!-- ifitwala_ed/ui-spa/src/pages/staff/StaffPolicies.vue -->
<template>
	<div class="analytics-shell space-y-5">
		<header class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
			<div>
				<h1 class="type-h2 text-canopy">Policy Library</h1>
				<p class="type-caption text-slate-500">
					{{ subtitleText }}
				</p>
			</div>
		</header>

		<FiltersBar class="analytics-filters">
			<div class="flex flex-col gap-1">
				<label class="type-label">Organization</label>
				<select
					v-model="filters.organization"
					class="h-9 min-w-[180px] rounded-md border px-2 text-sm"
					:disabled="loading"
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
					:disabled="loading || !filters.organization"
				>
					<option v-if="canManageAudiences" value="">All schools</option>
					<option v-for="school in options.schools" :key="school" :value="school">
						{{ school }}
					</option>
				</select>
			</div>

			<div v-if="canManageAudiences" class="flex flex-col gap-1">
				<label class="type-label">Audience</label>
				<select
					v-model="filters.audience"
					class="h-9 min-w-[170px] rounded-md border px-2 text-sm"
					:disabled="loading || !filters.organization"
				>
					<option v-for="audience in options.audiences" :key="audience" :value="audience">
						{{ audienceLabel(audience) }}
					</option>
				</select>
			</div>
		</FiltersBar>

		<KpiRow :items="kpis" />

		<div
			v-if="errorMessage"
			class="rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-900"
		>
			{{ errorMessage }}
		</div>

		<div v-else-if="loading && !rows.length" class="py-10 text-center text-sm text-slate-500">
			Loading policy library...
		</div>

		<div
			v-else-if="!rows.length"
			class="rounded-md border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600"
		>
			{{ emptyStateText }}
		</div>

		<section v-else class="grid grid-cols-1 gap-4 xl:grid-cols-2">
			<article v-for="row in rows" :key="row.policy_version" class="analytics-card">
				<div class="flex items-start justify-between gap-3">
					<div class="min-w-0">
						<div class="flex flex-wrap items-center gap-2">
							<p class="type-caption text-slate-500">
								{{ row.policy_category || 'Policy' }}
								<span v-if="row.version_label"> · {{ row.version_label }}</span>
							</p>
							<span
								v-for="token in row.applies_to_tokens"
								:key="`${row.policy_version}_${token}`"
								class="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700"
							>
								{{ audienceLabel(token) }}
							</span>
						</div>
						<h3 class="mt-1 type-h3 text-ink">
							{{ row.policy_title || row.policy_key || row.policy_version }}
						</h3>
						<p class="mt-2 type-meta text-slate-600">
							{{ row.description || 'No summary provided.' }}
						</p>
						<p class="mt-2 type-caption text-slate-500">
							{{ row.policy_organization || '-' }}
							<span v-if="row.policy_school"> · {{ row.policy_school }}</span>
						</p>
					</div>

					<div class="shrink-0 flex flex-col items-end gap-2">
						<span
							class="rounded-full px-2.5 py-1 text-xs font-medium"
							:class="primaryBadgeClass(row)"
						>
							{{ primaryBadgeLabel(row) }}
						</span>
						<span
							v-if="
								showStaffStatusMetrics &&
								row.signature_required &&
								row.acknowledgement_status === 'signed' &&
								row.acknowledged_at
							"
							class="type-caption text-slate-500"
						>
							{{ formatLocalizedDateTime(row.acknowledged_at, { includeWeekday: true }) }}
						</span>
					</div>
				</div>

				<div class="mt-4 flex items-center justify-between gap-3">
					<p class="type-caption text-slate-500">
						<span v-if="row.effective_from"
							>Effective {{ formatLocalizedDate(row.effective_from) }}</span
						>
						<span v-else>Effective date not set</span>
						<span v-if="row.effective_to"> → {{ formatLocalizedDate(row.effective_to) }}</span>
					</p>
					<div class="flex items-center gap-2">
						<button type="button" class="btn btn-quiet" @click="openPolicy(row.policy_version)">
							Open policy
						</button>
						<button
							v-if="canViewPolicySignatureAnalytics"
							type="button"
							class="btn btn-quiet"
							@click="openPolicySignatureAnalytics(row)"
						>
							Open acknowledgement tracking
						</button>
					</div>
				</div>
			</article>
		</section>
	</div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import { useRouter } from 'vue-router';

import FiltersBar from '@/components/filters/FiltersBar.vue';
import KpiRow from '@/components/analytics/KpiRow.vue';
import { useOverlayStack } from '@/composables/useOverlayStack';
import { formatLocalizedDate, formatLocalizedDateTime } from '@/lib/datetime';
import { createPolicySignatureService } from '@/lib/services/policySignature/policySignatureService';
import { getStaffHomeHeader } from '@/lib/services/staff/staffHomeService';

import type {
	Response as PolicyLibraryResponse,
	PolicyLibraryRow,
} from '@/types/contracts/policy_signature/get_staff_policy_library';

type PolicyLibraryAudience = 'All' | 'Staff' | 'Guardian' | 'Student';
type PolicyLibraryAudienceFilter = PolicyLibraryAudience | '';

const overlay = useOverlayStack();
const router = useRouter();
const service = createPolicySignatureService();

const loading = ref(false);
const errorMessage = ref('');
const payload = ref<PolicyLibraryResponse | null>(null);
const syncingFromServer = ref(false);
const canViewPolicySignatureAnalytics = ref(false);

const options = reactive({
	organizations: [] as string[],
	schools: [] as string[],
	audiences: [] as PolicyLibraryAudience[],
});

const filters = reactive({
	organization: '',
	school: '',
	audience: '' as PolicyLibraryAudienceFilter,
});

const canManageAudiences = computed(() => Boolean(payload.value?.meta?.can_manage_audiences));
const rows = computed<PolicyLibraryRow[]>(() => payload.value?.rows || []);
const currentAudience = computed<PolicyLibraryAudience>(() => {
	const serverAudience = payload.value?.filters?.audience;
	if (serverAudience) return serverAudience;
	if (filters.audience) return filters.audience;
	return canManageAudiences.value ? 'All' : 'Staff';
});
const showStaffStatusMetrics = computed(() => currentAudience.value === 'Staff');

const subtitleText = computed(() => {
	if (canManageAudiences.value) {
		return 'Browse active staff, guardian, and student policies in your organization scope and open acknowledgement tracking where needed.';
	}
	return 'Review staff policies in your current scope and open policy details or acknowledgement tracking.';
});

const emptyStateText = computed(() => {
	if (showStaffStatusMetrics.value) {
		return 'No active staff policies found for the selected scope.';
	}
	return 'No active policies found for the selected organization, school, and audience filters.';
});

const kpis = computed(() => {
	const counts = payload.value?.counts;
	if (!counts) return [];
	if (showStaffStatusMetrics.value) {
		return [
			{ id: 'total', label: 'Policies', value: counts.total_policies },
			{ id: 'informational', label: 'Informational', value: counts.informational },
			{ id: 'signature_required', label: 'Signature Required', value: counts.signature_required },
			{ id: 'signed', label: 'Signed', value: counts.signed },
			{
				id: 'pending',
				label: 'Pending/New Version',
				value: counts.pending + counts.new_version,
				hint: `Pending ${counts.pending} · New ${counts.new_version}`,
			},
		];
	}
	return [
		{ id: 'total', label: 'Policies', value: counts.total_policies },
		{ id: 'organization_scoped', label: 'Organization-wide', value: counts.organization_scoped },
		{ id: 'school_scoped', label: 'School-scoped', value: counts.school_scoped },
		{ id: 'multi_audience', label: 'Multi-audience', value: counts.multi_audience },
	];
});

function audienceLabel(audience: string) {
	if (audience === 'Guardian') return 'Guardians';
	if (audience === 'Student') return 'Students';
	if (audience === 'Staff') return 'Staff';
	return 'All audiences';
}

function statusLabel(status: PolicyLibraryRow['acknowledgement_status']) {
	if (status === 'signed') return 'Signed';
	if (status === 'new_version') return 'New version';
	if (status === 'pending') return 'Signature pending';
	return 'Informational';
}

function statusClass(status: PolicyLibraryRow['acknowledgement_status']) {
	if (status === 'signed') return 'bg-leaf/15 text-canopy';
	if (status === 'new_version') return 'bg-sky/20 text-canopy';
	if (status === 'pending') return 'bg-sand text-clay';
	return 'bg-slate-100 text-slate-700';
}

function workflowLabel(row: PolicyLibraryRow) {
	const tokens = Array.from(new Set(row.applies_to_tokens || []));
	if (tokens.length > 1) return `${tokens.length} audiences`;
	if (!tokens.length) return 'Policy in scope';
	if (tokens[0] === 'Guardian') return 'Guardian Portal';
	if (tokens[0] === 'Student') return 'Student Hub';
	return 'Staff Workspace';
}

function workflowClass(row: PolicyLibraryRow) {
	const tokens = Array.from(new Set(row.applies_to_tokens || []));
	if (tokens.length > 1) return 'bg-jacaranda/10 text-jacaranda';
	if (!tokens.length) return 'bg-slate-100 text-slate-700';
	if (tokens[0] === 'Guardian') return 'bg-sky/20 text-canopy';
	if (tokens[0] === 'Student') return 'bg-leaf/15 text-canopy';
	return 'bg-slate-100 text-slate-700';
}

function primaryBadgeLabel(row: PolicyLibraryRow) {
	if (showStaffStatusMetrics.value) {
		return statusLabel(row.acknowledgement_status);
	}
	return workflowLabel(row);
}

function primaryBadgeClass(row: PolicyLibraryRow) {
	if (showStaffStatusMetrics.value) {
		return statusClass(row.acknowledgement_status);
	}
	return workflowClass(row);
}

function openPolicy(policyVersion: string) {
	const value = String(policyVersion || '').trim();
	if (!value) return;
	overlay.open('staff-policy-inform', { policyVersion: value });
}

function openPolicySignatureAnalytics(row: PolicyLibraryRow) {
	if (!canViewPolicySignatureAnalytics.value) return;
	const policyVersion = String(row.policy_version || '').trim();
	if (!policyVersion) return;

	const organization = String(filters.organization || '').trim();
	const school = String(filters.school || '').trim();
	const query: Record<string, string> = { policy_version: policyVersion };
	if (organization) query.organization = organization;
	if (school) query.school = school;

	router.push({
		name: 'staff-policy-signature-analytics',
		query,
	});
}

async function loadCapabilities() {
	try {
		const header = await getStaffHomeHeader();
		canViewPolicySignatureAnalytics.value = Boolean(
			header?.capabilities?.analytics_policy_signatures
		);
	} catch {
		canViewPolicySignatureAnalytics.value = false;
	}
}

function normalizeFiltersFromPayload(next: PolicyLibraryResponse) {
	syncingFromServer.value = true;
	options.organizations = [...(next.options?.organizations || [])];
	options.schools = [...(next.options?.schools || [])];
	options.audiences = [...(next.options?.audiences || [])];

	filters.organization = String(next.filters?.organization || '').trim();
	filters.school = String(next.filters?.school || '').trim();
	filters.audience =
		(next.filters?.audience as PolicyLibraryAudience | undefined) ||
		(next.meta?.can_manage_audiences ? 'All' : 'Staff');
	syncingFromServer.value = false;
}

async function refreshPolicyLibrary() {
	loading.value = true;
	errorMessage.value = '';
	try {
		const response = await service.getPolicyLibrary({
			organization: filters.organization || null,
			school: filters.school || null,
			audience: filters.audience || null,
		});
		payload.value = response;
		normalizeFiltersFromPayload(response);
	} catch (err: unknown) {
		const message =
			err instanceof Error && err.message ? err.message : 'Unable to load policy library.';
		errorMessage.value = message;
	} finally {
		loading.value = false;
	}
}

let refreshTimer: ReturnType<typeof setTimeout> | null = null;
function scheduleRefresh() {
	if (refreshTimer) clearTimeout(refreshTimer);
	refreshTimer = setTimeout(() => {
		refreshPolicyLibrary();
	}, 220);
}

watch(
	() => [filters.organization, filters.school, filters.audience],
	() => {
		if (syncingFromServer.value) return;
		scheduleRefresh();
	}
);

onMounted(async () => {
	await Promise.all([loadCapabilities(), refreshPolicyLibrary()]);
});

onBeforeUnmount(() => {
	if (refreshTimer) clearTimeout(refreshTimer);
});
</script>
