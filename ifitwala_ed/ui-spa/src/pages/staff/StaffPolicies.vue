<!-- ifitwala_ed/ui-spa/src/pages/staff/StaffPolicies.vue -->
<template>
	<div class="analytics-shell space-y-5">
		<header class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
			<div>
				<h1 class="type-h2 text-canopy">Staff Policies</h1>
				<p class="type-caption text-slate-500">
					Consult policies in your scope and review what changed across versions.
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
					:disabled="loading || !filters.organization"
				>
					<option value="">All groups</option>
					<option v-for="group in options.employee_groups" :key="group" :value="group">
						{{ group }}
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
			Loading staff policies...
		</div>

		<div
			v-else-if="!rows.length"
			class="rounded-md border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600"
		>
			No active staff policies found for the selected scope.
		</div>

		<section v-else class="grid grid-cols-1 gap-4 xl:grid-cols-2">
			<article v-for="row in rows" :key="row.policy_version" class="analytics-card">
				<div class="flex items-start justify-between gap-3">
					<div class="min-w-0">
						<p class="type-caption text-slate-500">
							{{ row.policy_category || 'Policy' }}
							<span v-if="row.version_label"> · {{ row.version_label }}</span>
						</p>
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
							:class="statusClass(row.acknowledgement_status)"
						>
							{{ statusLabel(row.acknowledgement_status) }}
						</span>
						<span
							v-if="
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
					<button type="button" class="btn btn-quiet" @click="openPolicy(row.policy_version)">
						Open policy
					</button>
				</div>
			</article>
		</section>
	</div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';

import FiltersBar from '@/components/filters/FiltersBar.vue';
import KpiRow from '@/components/analytics/KpiRow.vue';
import { useOverlayStack } from '@/composables/useOverlayStack';
import { formatLocalizedDate, formatLocalizedDateTime } from '@/lib/datetime';
import { createPolicySignatureService } from '@/lib/services/policySignature/policySignatureService';

import type {
	Response as StaffPolicyLibraryResponse,
	StaffPolicyLibraryRow,
} from '@/types/contracts/policy_signature/get_staff_policy_library';

const overlay = useOverlayStack();
const service = createPolicySignatureService();

const loading = ref(false);
const errorMessage = ref('');
const payload = ref<StaffPolicyLibraryResponse | null>(null);
const syncingFromServer = ref(false);

const options = reactive({
	organizations: [] as string[],
	schools: [] as string[],
	employee_groups: [] as string[],
});

const filters = reactive({
	organization: '',
	school: '',
	employee_group: '',
});

const rows = computed<StaffPolicyLibraryRow[]>(() => payload.value?.rows || []);

const kpis = computed(() => {
	const counts = payload.value?.counts;
	if (!counts) return [];
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
});

function statusLabel(status: StaffPolicyLibraryRow['acknowledgement_status']) {
	if (status === 'signed') return 'Signed';
	if (status === 'new_version') return 'New version';
	if (status === 'pending') return 'Signature pending';
	return 'Informational';
}

function statusClass(status: StaffPolicyLibraryRow['acknowledgement_status']) {
	if (status === 'signed') return 'bg-mint/15 text-forest';
	if (status === 'new_version') return 'bg-sky/20 text-canopy';
	if (status === 'pending') return 'bg-warm-amber/15 text-ochre';
	return 'bg-slate-100 text-slate-700';
}

function openPolicy(policyVersion: string) {
	const value = String(policyVersion || '').trim();
	if (!value) return;
	overlay.open('staff-policy-inform', { policyVersion: value });
}

function normalizeFiltersFromPayload(next: StaffPolicyLibraryResponse) {
	syncingFromServer.value = true;
	options.organizations = [...(next.options?.organizations || [])];
	options.schools = [...(next.options?.schools || [])];
	options.employee_groups = [...(next.options?.employee_groups || [])];

	filters.organization = String(next.filters?.organization || '').trim();
	filters.school = String(next.filters?.school || '').trim();
	filters.employee_group = String(next.filters?.employee_group || '').trim();
	syncingFromServer.value = false;
}

async function refreshPolicyLibrary() {
	loading.value = true;
	errorMessage.value = '';
	try {
		const response = await service.getPolicyLibrary({
			organization: filters.organization || null,
			school: filters.school || null,
			employee_group: filters.employee_group || null,
		});
		payload.value = response;
		normalizeFiltersFromPayload(response);
	} catch (err: unknown) {
		const message = err instanceof Error && err.message ? err.message : 'Unable to load policies.';
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
	() => [filters.organization, filters.school, filters.employee_group],
	() => {
		if (syncingFromServer.value) return;
		scheduleRefresh();
	}
);

onMounted(() => {
	refreshPolicyLibrary();
});

onBeforeUnmount(() => {
	if (refreshTimer) clearTimeout(refreshTimer);
});
</script>
