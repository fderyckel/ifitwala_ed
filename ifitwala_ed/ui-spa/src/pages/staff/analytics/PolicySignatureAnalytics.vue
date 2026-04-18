<!-- ifitwala_ed/ui-spa/src/pages/staff/analytics/PolicySignatureAnalytics.vue -->
<template>
	<div class="analytics-shell space-y-5">
		<header class="page-header">
			<div class="page-header__intro">
				<h1 class="type-h1 text-canopy">Policy Signatures</h1>
				<p class="type-meta text-slate-token/80">
					Track policy acknowledgement status across staff, guardians, and students from one place.
				</p>
			</div>
			<div v-if="canManageCampaigns" class="page-header__actions">
				<button type="button" class="if-button if-button--secondary" @click="openCampaignOverlay">
					<FeatherIcon name="plus" class="h-4 w-4" />
					<span>Set up staff campaign</span>
				</button>
				<button
					type="button"
					class="if-button if-button--primary"
					@click="openFamilyCampaignOverlay"
				>
					<FeatherIcon name="send" class="h-4 w-4" />
					<span>Publish family campaign</span>
				</button>
			</div>
		</header>

		<FiltersBar class="analytics-filters !items-start">
			<div class="flex flex-col gap-1">
				<label class="type-label">Organization</label>
				<select
					v-model="filters.organization"
					class="h-9 min-w-[180px] rounded-md border px-2 text-sm"
					:disabled="loadingOptions"
					@change="handleOrganizationChange"
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
					@change="handleSchoolChange"
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
				<p class="type-caption text-slate-500">Applies to staff only.</p>
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
			Select a policy version to load acknowledgement status for every applicable audience.
		</div>

		<div v-else-if="loadingDashboard" class="py-10 text-center text-sm text-slate-500">
			Loading policy signature analytics...
		</div>

		<div v-else-if="dashboard" class="space-y-5">
			<section class="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
				<article
					v-for="card in dashboardMetricCards"
					:key="card.id"
					class="rounded-2xl border px-4 py-4"
					:class="metricCardClasses(card.tone)"
				>
					<div class="flex items-start justify-between gap-3">
						<p
							class="type-caption uppercase tracking-[0.14em]"
							:class="metricLabelClasses(card.tone)"
						>
							{{ card.label }}
						</p>
						<p v-if="card.hint" class="type-caption text-slate-500">{{ card.hint }}</p>
					</div>
					<p class="mt-3 text-3xl font-semibold" :class="metricValueClasses(card.tone)">
						{{ card.value }}
					</p>
				</article>
			</section>

			<section class="analytics-card space-y-4">
				<div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
					<div class="space-y-1">
						<p class="type-caption uppercase tracking-[0.16em] text-slate-500">Selected policy</p>
						<h2 class="type-h3 text-ink">{{ selectedPolicyTitle }}</h2>
						<p class="type-caption text-slate-500">
							Version {{ dashboard.summary.version_label || 'Current' }}
							<span v-if="dashboard.summary.policy_key">
								· {{ dashboard.summary.policy_key }}
							</span>
						</p>
					</div>
					<div class="flex flex-wrap gap-2">
						<span
							v-for="audience in dashboard.summary.applies_to_tokens"
							:key="audience"
							class="rounded-full bg-slate-100 px-3 py-1 type-caption text-slate-700"
						>
							{{ audienceLabel(audience) }}
						</span>
					</div>
				</div>

				<p
					v-if="showEmployeeGroupScopeNote"
					class="rounded-xl border border-sand/70 bg-sand/40 px-3 py-2 type-caption text-clay"
				>
					Employee Group filtering narrows staff results only. Guardian and student counts stay
					scoped by organization and school.
				</p>
			</section>

			<section
				v-for="section in audienceSections"
				:key="section.audience"
				class="analytics-card space-y-4"
			>
				<div class="flex flex-col gap-2 lg:flex-row lg:items-start lg:justify-between">
					<div>
						<h3 class="analytics-card__title">{{ section.audience_label }}</h3>
						<p class="analytics-card__meta mt-1">{{ section.workflow_description }}</p>
					</div>
					<div class="flex flex-wrap gap-2">
						<div
							class="inline-flex items-center rounded-full px-3 py-1 type-caption"
							:class="
								section.supports_campaign_launch
									? 'bg-jacaranda/10 text-jacaranda'
									: 'bg-slate-100 text-slate-600'
							"
						>
							{{
								section.supports_campaign_launch
									? 'Staff tasks available'
									: 'Portal acknowledgement flow'
							}}
						</div>
						<div
							v-if="section.supports_campaign_launch"
							class="inline-flex items-center rounded-full bg-sky/20 px-3 py-1 type-caption text-canopy"
						>
							To create {{ section.summary.to_create }}
						</div>
					</div>
				</div>

				<div class="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
					<article
						v-for="card in audienceMetricCards(section)"
						:key="card.id"
						class="rounded-2xl border px-4 py-4"
						:class="metricCardClasses(card.tone)"
					>
						<p
							class="type-caption uppercase tracking-[0.14em]"
							:class="metricLabelClasses(card.tone)"
						>
							{{ card.label }}
						</p>
						<p class="mt-3 text-3xl font-semibold" :class="metricValueClasses(card.tone)">
							{{ card.value }}
						</p>
					</article>
				</div>

				<section class="grid grid-cols-1 gap-4 xl:grid-cols-3">
					<article class="rounded-2xl border border-slate-200 bg-white px-4 py-4 shadow-soft">
						<h4 class="type-body-strong text-ink">By Organization</h4>
						<table class="mt-3 w-full text-sm">
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
									v-for="row in section.breakdowns.by_organization"
									:key="`${section.audience}_org_${row.label}`"
									class="border-t border-slate-100"
								>
									<td class="py-2 pr-2">{{ row.label }}</td>
									<td class="py-2 pr-2">{{ row.signed }}</td>
									<td class="py-2 pr-2">{{ row.pending }}</td>
									<td class="py-2 text-right">{{ row.completion_pct }}%</td>
								</tr>
								<tr v-if="section.breakdowns.by_organization.length === 0">
									<td class="py-3 text-slate-500" colspan="4">No matching records.</td>
								</tr>
							</tbody>
						</table>
					</article>

					<article class="rounded-2xl border border-slate-200 bg-white px-4 py-4 shadow-soft">
						<h4 class="type-body-strong text-ink">By School</h4>
						<table class="mt-3 w-full text-sm">
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
									v-for="row in section.breakdowns.by_school"
									:key="`${section.audience}_school_${row.label}`"
									class="border-t border-slate-100"
								>
									<td class="py-2 pr-2">{{ row.label }}</td>
									<td class="py-2 pr-2">{{ row.signed }}</td>
									<td class="py-2 pr-2">{{ row.pending }}</td>
									<td class="py-2 text-right">{{ row.completion_pct }}%</td>
								</tr>
								<tr v-if="section.breakdowns.by_school.length === 0">
									<td class="py-3 text-slate-500" colspan="4">No matching records.</td>
								</tr>
							</tbody>
						</table>
					</article>

					<article
						v-if="section.breakdowns.by_context.length"
						class="rounded-2xl border border-slate-200 bg-white px-4 py-4 shadow-soft"
					>
						<h4 class="type-body-strong text-ink">
							By {{ section.breakdowns.context_label || 'Context' }}
						</h4>
						<table class="mt-3 w-full text-sm">
							<thead>
								<tr class="text-left text-slate-500">
									<th class="pb-2 pr-2">{{ section.breakdowns.context_label || 'Context' }}</th>
									<th class="pb-2 pr-2">Signed</th>
									<th class="pb-2 pr-2">Pending</th>
									<th class="pb-2 text-right">Completion</th>
								</tr>
							</thead>
							<tbody>
								<tr
									v-for="row in section.breakdowns.by_context"
									:key="`${section.audience}_context_${row.label}`"
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

				<section
					v-if="shouldShowCompactAudienceLists(section)"
					class="grid grid-cols-1 gap-4 xl:grid-cols-2"
				>
					<article class="rounded-2xl border border-slate-200 bg-white px-4 py-4 shadow-soft">
						<h4 class="type-body-strong text-ink">Pending</h4>
						<p class="analytics-card__meta mt-1">
							People who still need to acknowledge this policy.
						</p>
						<div class="mt-3 max-h-[24rem] overflow-auto custom-scrollbar">
							<table class="w-full text-sm">
								<thead>
									<tr class="text-left text-slate-500">
										<th class="pb-2 pr-2">Person</th>
										<th class="pb-2 pr-2">Context</th>
										<th class="pb-2 pr-2">Organization</th>
										<th class="pb-2">School</th>
									</tr>
								</thead>
								<tbody>
									<tr
										v-for="row in section.rows.pending"
										:key="`${section.audience}_pending_${row.record_id}`"
										class="border-t border-slate-100"
									>
										<td class="py-2 pr-2">
											<div class="font-medium text-ink">{{ row.subject_name }}</div>
											<div v-if="row.subject_subtitle" class="type-caption text-slate-500">
												{{ row.subject_subtitle }}
											</div>
										</td>
										<td class="py-2 pr-2">{{ row.context_label || '-' }}</td>
										<td class="py-2 pr-2">{{ row.organization || '-' }}</td>
										<td class="py-2">{{ row.school || '-' }}</td>
									</tr>
									<tr v-if="section.rows.pending.length === 0">
										<td class="py-3 text-slate-500" colspan="4">No pending acknowledgements.</td>
									</tr>
								</tbody>
							</table>
						</div>
					</article>

					<article class="rounded-2xl border border-slate-200 bg-white px-4 py-4 shadow-soft">
						<h4 class="type-body-strong text-ink">Signed</h4>
						<p class="analytics-card__meta mt-1">
							Most recent acknowledgements for this audience.
						</p>
						<div class="mt-3 max-h-[24rem] overflow-auto custom-scrollbar">
							<table class="w-full text-sm">
								<thead>
									<tr class="text-left text-slate-500">
										<th class="pb-2 pr-2">Person</th>
										<th class="pb-2 pr-2">Context</th>
										<th class="pb-2 pr-2">Acknowledged At</th>
										<th class="pb-2">Acknowledged By</th>
									</tr>
								</thead>
								<tbody>
									<tr
										v-for="row in section.rows.signed"
										:key="`${section.audience}_signed_${row.record_id}`"
										class="border-t border-slate-100"
									>
										<td class="py-2 pr-2">
											<div class="font-medium text-ink">{{ row.subject_name }}</div>
											<div v-if="row.subject_subtitle" class="type-caption text-slate-500">
												{{ row.subject_subtitle }}
											</div>
										</td>
										<td class="py-2 pr-2">{{ row.context_label || '-' }}</td>
										<td class="py-2 pr-2">
											{{
												row.acknowledged_at
													? formatLocalizedDateTime(row.acknowledged_at, {
															includeWeekday: true,
														})
													: '-'
											}}
										</td>
										<td class="py-2">{{ row.acknowledged_by || '-' }}</td>
									</tr>
									<tr v-if="section.rows.signed.length === 0">
										<td class="py-3 text-slate-500" colspan="4">No signatures captured yet.</td>
									</tr>
								</tbody>
							</table>
						</div>
					</article>
				</section>

				<article class="rounded-2xl border border-slate-200 bg-white px-4 py-4 shadow-soft">
					<div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
						<div class="space-y-1">
							<h4 class="type-body-strong text-ink">Audience register</h4>
							<p class="analytics-card__meta">
								Search this audience and page through results instead of scanning long lists.
							</p>
						</div>
						<button
							type="button"
							class="inline-flex items-center justify-center rounded-full border border-slate-200 bg-white px-4 py-2 type-button-label text-ink transition hover:border-jacaranda/35 hover:text-jacaranda"
							@click="toggleAudienceRegister(section.audience)"
						>
							{{
								getAudienceRegister(section.audience).isOpen
									? 'Hide register'
									: 'Open searchable register'
							}}
						</button>
					</div>

					<p
						v-if="!shouldShowCompactAudienceLists(section)"
						class="mt-4 rounded-xl border border-sand/70 bg-sand/25 px-3 py-2 type-caption text-clay"
					>
						This audience has {{ section.summary.eligible_targets }} people in scope. Use the
						register to search quickly and move through paginated results.
					</p>

					<div v-if="getAudienceRegister(section.audience).isOpen" class="mt-4 space-y-4">
						<div class="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
							<div class="flex flex-1 flex-col gap-3 sm:flex-row">
								<div class="flex-1">
									<label class="sr-only">Search {{ section.audience_label }}</label>
									<input
										v-model="getAudienceRegister(section.audience).queryInput"
										type="search"
										class="h-10 w-full rounded-xl border border-slate-200 px-3 text-sm text-ink outline-none transition focus:border-jacaranda/40 focus:ring-2 focus:ring-jacaranda/10"
										:placeholder="audienceSearchPlaceholder(section)"
										@keyup.enter="submitAudienceSearch(section.audience)"
									/>
								</div>
								<div class="flex items-center gap-2">
									<button
										type="button"
										class="inline-flex items-center justify-center rounded-full bg-jacaranda px-4 py-2 type-button-label text-white shadow-soft transition hover:bg-jacaranda/90"
										@click="submitAudienceSearch(section.audience)"
									>
										Find
									</button>
									<button
										v-if="
											getAudienceRegister(section.audience).queryInput ||
											getAudienceRegister(section.audience).appliedQuery
										"
										type="button"
										class="inline-flex items-center justify-center rounded-full border border-slate-200 bg-white px-4 py-2 type-button-label text-slate-600 transition hover:border-jacaranda/30 hover:text-jacaranda"
										@click="clearAudienceSearch(section.audience)"
									>
										Clear
									</button>
								</div>
							</div>

							<div class="flex flex-wrap gap-2">
								<button
									v-for="status in registerStatusOptions"
									:key="`${section.audience}_${status}`"
									type="button"
									class="inline-flex items-center rounded-full border px-3 py-1.5 type-caption transition"
									:class="registerStatusButtonClasses(section.audience, status)"
									@click="setAudienceRegisterStatus(section.audience, status)"
								>
									{{ registerStatusLabel(status) }}
								</button>
							</div>
						</div>

						<div
							class="flex flex-col gap-2 text-sm text-slate-500 sm:flex-row sm:items-center sm:justify-between"
						>
							<p>{{ registerRangeLabel(section.audience) }}</p>
							<p v-if="getAudienceRegister(section.audience).appliedQuery" class="type-caption">
								Search: “{{ getAudienceRegister(section.audience).appliedQuery }}”
							</p>
						</div>

						<div
							v-if="getAudienceRegister(section.audience).error"
							class="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-900"
						>
							{{ getAudienceRegister(section.audience).error }}
						</div>

						<div
							v-else-if="getAudienceRegister(section.audience).loading"
							class="rounded-xl border border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-500"
						>
							Loading {{ section.audience_label.toLowerCase() }} register...
						</div>

						<div
							v-else-if="getAudienceRegister(section.audience).rows.length === 0"
							class="rounded-xl border border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-500"
						>
							{{ registerEmptyMessage(section.audience) }}
						</div>

						<div v-else class="space-y-3">
							<div
								class="max-h-[26rem] overflow-auto custom-scrollbar rounded-xl border border-slate-200"
							>
								<table class="w-full min-w-[860px] text-sm">
									<thead class="bg-slate-50 text-left text-slate-500">
										<tr>
											<th class="px-3 py-3 pr-2">Person</th>
											<th class="px-3 py-3 pr-2">Status</th>
											<th class="px-3 py-3 pr-2">Context</th>
											<th class="px-3 py-3 pr-2">Organization</th>
											<th class="px-3 py-3 pr-2">School</th>
											<th class="px-3 py-3">Acknowledged</th>
										</tr>
									</thead>
									<tbody>
										<tr
											v-for="row in getAudienceRegister(section.audience).rows"
											:key="`${section.audience}_register_${row.record_id}`"
											class="border-t border-slate-100 align-top"
										>
											<td class="px-3 py-3 pr-2">
												<div class="font-medium text-ink">{{ row.subject_name }}</div>
												<div v-if="row.subject_subtitle" class="type-caption text-slate-500">
													{{ row.subject_subtitle }}
												</div>
											</td>
											<td class="px-3 py-3 pr-2">
												<span
													class="inline-flex items-center rounded-full px-2.5 py-1 type-caption"
													:class="rowStatusClasses(row.is_signed)"
												>
													{{ row.is_signed ? 'Signed' : 'Pending' }}
												</span>
											</td>
											<td class="px-3 py-3 pr-2">{{ row.context_label || '—' }}</td>
											<td class="px-3 py-3 pr-2">{{ row.organization || '—' }}</td>
											<td class="px-3 py-3 pr-2">{{ row.school || '—' }}</td>
											<td class="px-3 py-3">
												<div v-if="row.is_signed && row.acknowledged_at" class="text-ink">
													{{
														formatLocalizedDateTime(row.acknowledged_at, {
															includeWeekday: true,
														})
													}}
												</div>
												<div
													v-if="row.is_signed && row.acknowledged_by"
													class="type-caption text-slate-500"
												>
													{{ row.acknowledged_by }}
												</div>
												<span v-if="!row.is_signed" class="type-caption text-flame">
													Awaiting signature
												</span>
											</td>
										</tr>
									</tbody>
								</table>
							</div>

							<div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
								<p class="type-caption text-slate-500">
									Page {{ getAudienceRegister(section.audience).page }} of
									{{ getAudienceRegister(section.audience).totalPages }}
								</p>
								<div class="flex items-center gap-2">
									<button
										type="button"
										class="inline-flex items-center justify-center rounded-full border border-slate-200 bg-white px-4 py-2 type-button-label text-slate-600 transition hover:border-jacaranda/30 hover:text-jacaranda disabled:cursor-not-allowed disabled:opacity-50"
										:disabled="getAudienceRegister(section.audience).page <= 1"
										@click="
											goToAudienceRegisterPage(
												section.audience,
												getAudienceRegister(section.audience).page - 1
											)
										"
									>
										Previous
									</button>
									<button
										type="button"
										class="inline-flex items-center justify-center rounded-full border border-slate-200 bg-white px-4 py-2 type-button-label text-slate-600 transition hover:border-jacaranda/30 hover:text-jacaranda disabled:cursor-not-allowed disabled:opacity-50"
										:disabled="
											getAudienceRegister(section.audience).page >=
											getAudienceRegister(section.audience).totalPages
										"
										@click="
											goToAudienceRegisterPage(
												section.audience,
												getAudienceRegister(section.audience).page + 1
											)
										"
									>
										Next
									</button>
								</div>
							</div>
						</div>
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
import { useOverlayStack } from '@/composables/useOverlayStack';
import { formatLocalizedDateTime } from '@/lib/datetime';
import { createPolicySignatureService } from '@/lib/services/policySignature/policySignatureService';
import { getStaffHomeHeader } from '@/lib/services/staff/staffHomeService';

import type {
	PolicyOption,
	PolicySignatureAudience,
} from '@/types/contracts/policy_signature/get_staff_policy_campaign_options';
import type {
	PolicySignatureAudienceRow,
	PolicySignatureAudienceSection,
	Response as DashboardResponse,
} from '@/types/contracts/policy_signature/get_staff_policy_signature_dashboard';
import type {
	PolicySignatureRegisterStatus,
	Response as AudienceRowsResponse,
} from '@/types/contracts/policy_signature/get_staff_policy_signature_audience_rows';

const route = useRoute();
const overlay = useOverlayStack();
const policyService = createPolicySignatureService();
const DASHBOARD_PREVIEW_LIMIT = 10;
const AUDIENCE_REGISTER_PAGE_LIMIT = 25;
const LARGE_AUDIENCE_THRESHOLD = 24;
const registerStatusOptions: PolicySignatureRegisterStatus[] = ['all', 'pending', 'signed'];

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
let isBootstrapping = true;

const audienceSections = computed(() => dashboard.value?.audiences || []);

type MetricTone = 'neutral' | 'signed' | 'pending' | 'completion' | 'muted';
type MetricCard = {
	id: string;
	label: string;
	value: number | string;
	hint?: string;
	tone: MetricTone;
};
type AudienceRegisterState = {
	isOpen: boolean;
	loading: boolean;
	loaded: boolean;
	error: string;
	queryInput: string;
	appliedQuery: string;
	status: PolicySignatureRegisterStatus;
	page: number;
	totalRows: number;
	totalPages: number;
	rows: PolicySignatureAudienceRow[];
	requestToken: number;
};

function createAudienceRegisterState(): AudienceRegisterState {
	return {
		isOpen: false,
		loading: false,
		loaded: false,
		error: '',
		queryInput: '',
		appliedQuery: '',
		status: 'all',
		page: 1,
		totalRows: 0,
		totalPages: 1,
		rows: [],
		requestToken: 0,
	};
}

const audienceRegisters = reactive<Record<PolicySignatureAudience, AudienceRegisterState>>({
	Staff: createAudienceRegisterState(),
	Guardian: createAudienceRegisterState(),
	Student: createAudienceRegisterState(),
});

const selectedPolicyTitle = computed(() => {
	const policy = options.policies.find(row => row.policy_version === filters.policy_version);
	if (!policy)
		return (
			dashboard.value?.summary.policy_title || dashboard.value?.summary.policy_key || 'Policy'
		);
	return (
		(policy.policy_title || '').trim() ||
		(policy.policy_key || '').trim() ||
		dashboard.value?.summary.policy_title ||
		'Policy'
	);
});

const showEmployeeGroupScopeNote = computed(() => {
	return Boolean(
		filters.employee_group && audienceSections.value.some(section => section.audience !== 'Staff')
	);
});

const dashboardMetricCards = computed<MetricCard[]>(() => {
	const summary = dashboard.value?.summary;
	if (!summary) return [];
	return [
		{
			id: 'eligible_targets',
			label: 'Eligible',
			value: summary.eligible_targets,
			tone: 'neutral',
		},
		{ id: 'signed', label: 'Signed', value: summary.signed, tone: 'signed' },
		{ id: 'pending', label: 'Pending', value: summary.pending, tone: 'pending' },
		{
			id: 'completion_pct',
			label: 'Completion',
			value: `${summary.completion_pct}%`,
			tone: 'completion',
		},
		{
			id: 'skipped_scope',
			label: 'Out of scope',
			value: summary.skipped_scope,
			tone: 'muted',
		},
	];
});

function audienceLabel(audience: PolicySignatureAudience) {
	if (audience === 'Guardian') return 'Guardians';
	if (audience === 'Student') return 'Students';
	return 'Staff';
}

function policyLabel(policy: PolicyOption) {
	const title =
		(policy.policy_title || '').trim() ||
		(policy.policy_key || '').trim() ||
		policy.policy_version;
	const version = (policy.version_label || '').trim();
	return version ? `${title} (${version})` : title;
}

function handleOrganizationChange() {
	if (filters.school) filters.school = '';
	if (filters.employee_group) filters.employee_group = '';
}

function handleSchoolChange() {
	if (filters.employee_group) filters.employee_group = '';
}

function audienceMetricCards(section: PolicySignatureAudienceSection): MetricCard[] {
	return [
		{
			id: `${section.audience}_eligible`,
			label: 'Eligible',
			value: section.summary.eligible_targets,
			tone: 'neutral',
		},
		{
			id: `${section.audience}_signed`,
			label: 'Signed',
			value: section.summary.signed,
			tone: 'signed',
		},
		{
			id: `${section.audience}_pending`,
			label: 'Pending',
			value: section.summary.pending,
			tone: 'pending',
		},
		{
			id: `${section.audience}_completion`,
			label: 'Completion',
			value: `${section.summary.completion_pct}%`,
			tone: 'completion',
		},
		{
			id: `${section.audience}_skipped`,
			label: 'Out of scope',
			value: section.summary.skipped_scope,
			tone: 'muted',
		},
	];
}

function metricCardClasses(tone: MetricTone) {
	const base = 'bg-[rgb(var(--surface-strong-rgb)/0.98)]';
	if (tone === 'signed') {
		return `${base} border-leaf/34 shadow-[0_16px_30px_rgb(var(--leaf-rgb)/0.08)]`;
	}
	if (tone === 'pending') {
		return `${base} border-flame/34 shadow-[0_16px_30px_rgb(var(--flame-rgb)/0.08)]`;
	}
	if (tone === 'completion') {
		return `${base} border-jacaranda/28 shadow-[0_16px_30px_rgb(var(--jacaranda-rgb)/0.08)]`;
	}
	if (tone === 'muted') {
		return `${base} border-sand/82 shadow-[0_16px_28px_rgb(var(--clay-rgb)/0.06)]`;
	}
	return `${base} border-slate-200 shadow-[0_16px_28px_rgb(var(--ink-rgb)/0.05)]`;
}

function metricLabelClasses(tone: MetricTone) {
	if (tone === 'signed') return 'text-canopy/75';
	if (tone === 'pending') return 'text-flame/75';
	if (tone === 'completion') return 'text-jacaranda/75';
	if (tone === 'muted') return 'text-clay';
	return 'text-slate-500';
}

function metricValueClasses(tone: MetricTone) {
	if (tone === 'signed') return 'text-canopy';
	if (tone === 'pending') return 'text-flame';
	if (tone === 'completion') return 'text-jacaranda';
	if (tone === 'muted') return 'text-clay';
	return 'text-ink';
}

function shouldShowCompactAudienceLists(section: PolicySignatureAudienceSection) {
	return (section.summary.eligible_targets || 0) <= LARGE_AUDIENCE_THRESHOLD;
}

function getAudienceRegister(audience: PolicySignatureAudience) {
	return audienceRegisters[audience];
}

function resetAudienceRegister(audience: PolicySignatureAudience) {
	const state = audienceRegisters[audience];
	const nextToken = state.requestToken + 1;
	Object.assign(state, createAudienceRegisterState(), { requestToken: nextToken });
}

function resetAudienceRegisters() {
	resetAudienceRegister('Staff');
	resetAudienceRegister('Guardian');
	resetAudienceRegister('Student');
}

function registerStatusLabel(status: PolicySignatureRegisterStatus) {
	if (status === 'pending') return 'Pending';
	if (status === 'signed') return 'Signed';
	return 'All';
}

function registerStatusButtonClasses(
	audience: PolicySignatureAudience,
	status: PolicySignatureRegisterStatus
) {
	const isActive = getAudienceRegister(audience).status === status;
	if (isActive) return 'border-jacaranda bg-jacaranda/10 text-jacaranda shadow-soft';
	return 'border-slate-200 bg-white text-slate-600 hover:border-jacaranda/30 hover:text-jacaranda';
}

function rowStatusClasses(isSigned: boolean) {
	return isSigned ? 'bg-leaf/15 text-canopy' : 'bg-flame/10 text-flame';
}

function registerRangeLabel(audience: PolicySignatureAudience) {
	const state = getAudienceRegister(audience);
	if (!state.totalRows) return 'No matching people';
	const start = (state.page - 1) * AUDIENCE_REGISTER_PAGE_LIMIT + 1;
	const end = Math.min(start + state.rows.length - 1, state.totalRows);
	return `Showing ${start}-${end} of ${state.totalRows}`;
}

function registerEmptyMessage(audience: PolicySignatureAudience) {
	const state = getAudienceRegister(audience);
	if (state.appliedQuery) return 'No people matched this search in the current scope.';
	if (state.status === 'signed') return 'No signed acknowledgements matched this scope.';
	if (state.status === 'pending') return 'No pending acknowledgements matched this scope.';
	return 'No audience rows matched this scope.';
}

function audienceSearchPlaceholder(section: PolicySignatureAudienceSection) {
	if (section.audience === 'Staff') return 'Search staff by name, group, organization, or school';
	if (section.audience === 'Guardian')
		return 'Search guardians by name, email, linked students, organization, or school';
	return 'Search students by name, email, organization, or school';
}

async function loadAudienceRegister(audience: PolicySignatureAudience) {
	if (!filters.policy_version) return;

	const state = getAudienceRegister(audience);
	const requestToken = state.requestToken + 1;
	state.requestToken = requestToken;
	state.loading = true;
	state.error = '';

	try {
		const response: AudienceRowsResponse = await policyService.getAudienceRows({
			policy_version: filters.policy_version,
			audience,
			organization: filters.organization || null,
			school: filters.school || null,
			employee_group: filters.employee_group || null,
			status: state.status,
			query: state.appliedQuery || null,
			page: state.page,
			limit: AUDIENCE_REGISTER_PAGE_LIMIT,
		});
		if (requestToken !== state.requestToken) return;

		state.rows = [...(response.rows || [])];
		state.page = response.pagination?.page || 1;
		state.totalRows = response.pagination?.total_rows || 0;
		state.totalPages = response.pagination?.total_pages || 1;
		state.loaded = true;
		state.error = '';
	} catch (err: unknown) {
		if (requestToken !== state.requestToken) return;
		state.rows = [];
		state.totalRows = 0;
		state.totalPages = 1;
		state.loaded = false;
		state.error =
			err instanceof Error && err.message ? err.message : 'Unable to load this audience register.';
	} finally {
		if (requestToken === state.requestToken) {
			state.loading = false;
		}
	}
}

function toggleAudienceRegister(audience: PolicySignatureAudience) {
	const state = getAudienceRegister(audience);
	state.isOpen = !state.isOpen;
	if (state.isOpen && !state.loaded && !state.loading) {
		void loadAudienceRegister(audience);
	}
}

function submitAudienceSearch(audience: PolicySignatureAudience) {
	const state = getAudienceRegister(audience);
	state.appliedQuery = state.queryInput.trim();
	state.page = 1;
	if (!state.isOpen) state.isOpen = true;
	void loadAudienceRegister(audience);
}

function clearAudienceSearch(audience: PolicySignatureAudience) {
	const state = getAudienceRegister(audience);
	state.queryInput = '';
	state.appliedQuery = '';
	state.page = 1;
	if (!state.isOpen) state.isOpen = true;
	void loadAudienceRegister(audience);
}

function setAudienceRegisterStatus(
	audience: PolicySignatureAudience,
	status: PolicySignatureRegisterStatus
) {
	const state = getAudienceRegister(audience);
	if (state.status === status && state.loaded) return;
	state.status = status;
	state.page = 1;
	if (!state.isOpen) state.isOpen = true;
	void loadAudienceRegister(audience);
}

function goToAudienceRegisterPage(audience: PolicySignatureAudience, page: number) {
	const state = getAudienceRegister(audience);
	if (page < 1 || page > state.totalPages || page === state.page) return;
	state.page = page;
	void loadAudienceRegister(audience);
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
		accessDenied.value = /permission|not permitted|not have permission/i.test(message);
	} finally {
		loadingOptions.value = false;
	}
}

async function loadDashboard() {
	resetAudienceRegisters();

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
			limit: DASHBOARD_PREVIEW_LIMIT,
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
	overlay.open('staff-policy-signature-campaign', {
		organization: filters.organization || '',
		school: filters.school || '',
		employee_group: filters.employee_group || '',
		policy_version: filters.policy_version || '',
	});
}

function openFamilyCampaignOverlay() {
	overlay.open('staff-family-policy-campaign', {
		organization: filters.organization || '',
		school: filters.school || '',
		policy_version: filters.policy_version || '',
	});
}

watch(
	() => [filters.organization, filters.school, filters.employee_group, filters.policy_version],
	() => {
		if (isBootstrapping) return;
		scheduleRefresh();
	}
);

onMounted(async () => {
	prefillFromRoute();
	await Promise.all([loadCapabilities(), refreshOptions()]);
	await loadDashboard();
	isBootstrapping = false;
});

onBeforeUnmount(() => {
	if (refreshTimer) clearTimeout(refreshTimer);
});
</script>
