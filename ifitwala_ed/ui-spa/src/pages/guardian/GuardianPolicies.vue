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
							:class="
								row.is_acknowledged ? 'bg-mint/15 text-forest' : 'bg-warm-amber/15 text-ochre'
							"
						>
							{{ row.is_acknowledged ? 'Acknowledged' : 'Pending acknowledgement' }}
						</p>
						<button
							v-if="!row.is_acknowledged"
							type="button"
							class="if-action"
							:disabled="isRowBusy(row.policy_version)"
							@click="acknowledgeRow(row.policy_version)"
						>
							{{ isRowBusy(row.policy_version) ? 'Saving...' : 'Acknowledge' }}
						</button>
						<p v-else class="type-caption text-ink/60">
							{{ row.acknowledged_at || 'Acknowledged' }}
						</p>
					</div>
				</div>

				<details class="rounded-xl border border-line-soft bg-surface-soft p-4">
					<summary class="cursor-pointer type-body-strong text-ink">Open policy text</summary>
					<div class="mt-3 whitespace-pre-wrap type-body text-ink/80">
						{{ row.policy_text || 'No policy text available.' }}
					</div>
				</details>

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

const counts = computed(
	() =>
		overview.value?.counts ?? {
			total_policies: 0,
			acknowledged_policies: 0,
			pending_policies: 0,
		}
);
const rows = computed<GuardianPolicyRow[]>(() => overview.value?.rows ?? []);

function isRowBusy(policyVersion: string): boolean {
	return Boolean(busyRows.value[policyVersion]);
}

async function loadOverview() {
	loading.value = true;
	errorMessage.value = '';
	try {
		overview.value = await getGuardianPolicyOverview();
	} catch (error) {
		const message = error instanceof Error ? error.message : String(error || '');
		errorMessage.value = message || 'Unknown error';
	} finally {
		loading.value = false;
	}
}

async function acknowledgeRow(policyVersion: string) {
	rowErrors.value = { ...rowErrors.value, [policyVersion]: '' };
	busyRows.value = { ...busyRows.value, [policyVersion]: true };
	try {
		const result = await acknowledgeGuardianPolicy({ policy_version: policyVersion });
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
