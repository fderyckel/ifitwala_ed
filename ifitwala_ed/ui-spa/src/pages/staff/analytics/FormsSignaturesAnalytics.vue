<template>
	<div class="analytics-shell space-y-5">
		<header class="page-header">
			<div class="page-header__intro">
				<h1 class="type-h1 text-canopy">Forms &amp; Signatures</h1>
				<p class="type-meta text-slate-token/80">
					Track operational forms that guardians or adult students complete in portal, while Desk
					remains the place where staff build and publish them.
				</p>
				<div class="mt-2 flex flex-wrap items-center gap-2">
					<span
						class="inline-flex items-center rounded-full border border-slate-200 bg-white px-3 py-1 type-caption text-slate-token/70"
					>
						{{ scopeLabel }}
					</span>
				</div>
			</div>
			<div class="page-header__actions">
				<a href="/app/family-consent-request" class="if-button if-button--primary">
					<FeatherIcon name="external-link" class="h-4 w-4" />
					<span>Open Desk authoring</span>
				</a>
			</div>
		</header>

		<FiltersBar class="analytics-filters !items-start">
			<div class="flex flex-col gap-1">
				<label class="type-label">Organization</label>
				<select
					v-model="filters.organization"
					class="h-9 min-w-[180px] rounded-md border px-2 text-sm"
					:disabled="loadingContext"
					@change="handleOrganizationChange"
				>
					<option value="">All scoped organizations</option>
					<option
						v-for="organization in options.organizations"
						:key="organization"
						:value="organization"
					>
						{{ organization }}
					</option>
				</select>
			</div>

			<div class="flex flex-col gap-1">
				<label class="type-label">School</label>
				<select
					v-model="filters.school"
					class="h-9 min-w-[180px] rounded-md border px-2 text-sm"
					:disabled="loadingContext"
					@change="handleFilterChange"
				>
					<option value="">All schools</option>
					<option v-for="school in options.schools" :key="school" :value="school">
						{{ school }}
					</option>
				</select>
			</div>

			<div class="flex flex-col gap-1">
				<label class="type-label">Request Type</label>
				<select
					v-model="filters.request_type"
					class="h-9 min-w-[210px] rounded-md border px-2 text-sm"
					@change="handleFilterChange"
				>
					<option value="">All request types</option>
					<option
						v-for="requestType in options.request_types"
						:key="requestType"
						:value="requestType"
					>
						{{ requestType }}
					</option>
				</select>
			</div>

			<div class="flex flex-col gap-1">
				<label class="type-label">Status</label>
				<select
					v-model="filters.status"
					class="h-9 min-w-[150px] rounded-md border px-2 text-sm"
					@change="handleFilterChange"
				>
					<option value="">All statuses</option>
					<option v-for="status in options.statuses" :key="status" :value="status">
						{{ status }}
					</option>
				</select>
			</div>

			<div class="flex flex-col gap-1">
				<label class="type-label">Audience</label>
				<select
					v-model="filters.audience_mode"
					class="h-9 min-w-[180px] rounded-md border px-2 text-sm"
					@change="handleFilterChange"
				>
					<option value="">All audiences</option>
					<option
						v-for="audienceMode in options.audience_modes"
						:key="audienceMode"
						:value="audienceMode"
					>
						{{ audienceMode }}
					</option>
				</select>
			</div>

			<div class="flex flex-col gap-1">
				<label class="type-label">Completion Channel</label>
				<select
					v-model="filters.completion_channel_mode"
					class="h-9 min-w-[200px] rounded-md border px-2 text-sm"
					@change="handleFilterChange"
				>
					<option value="">All channels</option>
					<option
						v-for="completionChannelMode in options.completion_channel_modes"
						:key="completionChannelMode"
						:value="completionChannelMode"
					>
						{{ completionChannelMode }}
					</option>
				</select>
			</div>
		</FiltersBar>

		<div v-if="accessDenied" class="rounded-md border border-amber-200 bg-amber-50 px-4 py-3">
			<h2 class="text-sm font-semibold text-amber-900">Access restricted</h2>
			<p class="mt-1 text-xs text-amber-800">
				You do not have permission to view Forms &amp; Signatures analytics.
			</p>
		</div>

		<div
			v-else-if="errorMessage"
			class="rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-900"
		>
			{{ errorMessage }}
		</div>

		<div v-else-if="loadingContext && !dashboard" class="py-10 text-center text-sm text-slate-500">
			Loading forms and signatures analytics...
		</div>

		<div v-else class="space-y-5">
			<section class="analytics-card space-y-3">
				<div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
					<div class="space-y-1">
						<p class="type-caption uppercase tracking-[0.16em] text-slate-500">Workflow split</p>
						<h2 class="type-h3 text-ink">Desk builds. Portal completes. Analytics stay here.</h2>
						<p class="analytics-card__meta">
							Use Desk to create and publish the request. Use this page to monitor portal and paper
							completion without opening the DocType list every time.
						</p>
					</div>
					<div class="flex flex-wrap gap-2">
						<span class="rounded-full bg-slate-100 px-3 py-1 type-caption text-slate-700">
							Portal + paper-aware monitoring
						</span>
						<span class="rounded-full bg-jacaranda/10 px-3 py-1 type-caption text-jacaranda">
							{{ requestCountLabel }}
						</span>
					</div>
				</div>
			</section>

			<KpiRow :items="kpiItems" />

			<section class="grid gap-3 md:grid-cols-3">
				<article
					v-for="card in channelCards"
					:key="card.id"
					class="analytics-card analytics-card--dense"
				>
					<div class="flex items-start justify-between gap-3">
						<p class="type-caption uppercase tracking-[0.14em] text-slate-500">
							{{ card.label }}
						</p>
						<span class="rounded-full px-3 py-1 type-caption" :class="channelBadgeClass(card.id)">
							{{ card.badge }}
						</span>
					</div>
					<p class="text-3xl font-semibold text-ink">{{ card.value }}</p>
					<p class="type-caption text-slate-500">{{ card.meta }}</p>
				</article>
			</section>

			<section
				v-if="showPaperTrackingNote"
				class="rounded-xl border border-sand/70 bg-sand/30 px-4 py-3 text-sm text-clay"
			>
				<span class="font-medium">Paper Only</span> requests stay visible for monitoring here, but
				families cannot submit them from the portal. Staff must capture those approvals in Desk.
			</section>

			<section class="analytics-card space-y-4">
				<div class="flex flex-col gap-2 lg:flex-row lg:items-start lg:justify-between">
					<div>
						<h2 class="type-h3 text-ink">Request tracking</h2>
						<p class="analytics-card__meta">
							Completion counts roll up across each request's targeted students so staff can see
							pending, completed, overdue, and exception states in one board.
						</p>
					</div>
					<p class="type-caption text-slate-500">Updated {{ generatedAtLabel }}</p>
				</div>

				<div
					v-if="loadingDashboard"
					class="rounded-xl border border-slate-200 bg-slate-50 px-4 py-6 text-center text-sm text-slate-500"
				>
					Refreshing request analytics...
				</div>

				<div
					v-else-if="!requestRows.length"
					class="rounded-xl border border-slate-200 bg-slate-50 px-4 py-6 text-center text-sm text-slate-500"
				>
					No requests match the current scope and filters.
				</div>

				<div v-else class="overflow-x-auto">
					<table class="w-full min-w-[1120px] text-sm">
						<thead>
							<tr class="border-b border-slate-200 text-left text-slate-500">
								<th class="pb-3 pr-4 font-medium">Request</th>
								<th class="pb-3 pr-4 font-medium">Audience</th>
								<th class="pb-3 pr-4 font-medium">Channel</th>
								<th class="pb-3 pr-4 font-medium">Scope</th>
								<th class="pb-3 pr-4 font-medium">Due</th>
								<th class="pb-3 pr-4 text-right font-medium">Targets</th>
								<th class="pb-3 pr-4 text-right font-medium">Completed</th>
								<th class="pb-3 pr-4 text-right font-medium">Pending</th>
								<th class="pb-3 pr-4 text-right font-medium">Exceptions</th>
								<th class="pb-3 text-right font-medium">Completion</th>
							</tr>
						</thead>
						<tbody>
							<tr
								v-for="row in requestRows"
								:key="row.family_consent_request"
								class="border-b border-slate-100 align-top last:border-b-0"
							>
								<td class="py-3 pr-4">
									<div class="flex flex-col gap-1">
										<a
											:href="deskRequestUrl(row.family_consent_request)"
											class="font-medium text-canopy hover:underline"
										>
											{{ row.request_title }}
										</a>
										<div class="flex flex-wrap items-center gap-2">
											<span class="type-caption text-slate-500">{{ row.request_key }}</span>
											<span
												class="rounded-full px-2 py-0.5 type-caption"
												:class="statusBadgeClass(row.status)"
											>
												{{ row.status }}
											</span>
										</div>
										<p class="type-caption text-slate-500">{{ row.request_type }}</p>
									</div>
								</td>
								<td class="py-3 pr-4">
									<div class="flex flex-col gap-1">
										<span
											class="inline-flex w-fit items-center rounded-full px-3 py-1 type-caption"
											:class="audienceBadgeClass(row.audience_mode)"
										>
											{{ row.audience_mode }}
										</span>
										<span class="type-caption text-slate-500">{{ row.signer_rule }}</span>
									</div>
								</td>
								<td class="py-3 pr-4">
									<div class="flex flex-col gap-1">
										<span
											class="inline-flex w-fit items-center rounded-full px-3 py-1 type-caption"
											:class="channelBadgeClass(row.completion_channel_mode)"
										>
											{{ row.completion_channel_mode }}
										</span>
										<span class="type-caption text-slate-500">
											{{ channelMeta(row.completion_channel_mode) }}
										</span>
									</div>
								</td>
								<td class="py-3 pr-4">
									<div class="flex flex-col gap-1">
										<span class="text-slate-800">{{ row.organization }}</span>
										<span class="type-caption text-slate-500">
											{{ row.school || 'All schools in scope' }}
										</span>
									</div>
								</td>
								<td class="py-3 pr-4 text-slate-700">
									{{ formatDateValue(row.due_on) }}
								</td>
								<td class="py-3 pr-4 text-right text-slate-800">{{ row.target_count }}</td>
								<td class="py-3 pr-4 text-right text-canopy">{{ row.completed_count }}</td>
								<td class="py-3 pr-4 text-right text-clay">{{ row.pending_count }}</td>
								<td class="py-3 pr-4 text-right text-flame">{{ exceptionCount(row) }}</td>
								<td class="py-3 text-right font-medium text-slate-800">
									{{ completionPercentage(row) }}%
								</td>
							</tr>
						</tbody>
					</table>
				</div>
			</section>
		</div>
	</div>
</template>

<script setup lang="ts">
import { FeatherIcon } from 'frappe-ui';
import { computed, onMounted, reactive, ref } from 'vue';
import { useRoute } from 'vue-router';

import KpiRow from '@/components/analytics/KpiRow.vue';
import FiltersBar from '@/components/filters/FiltersBar.vue';
import { createFamilyConsentService } from '@/lib/services/familyConsent/familyConsentService';

import type { Response as FamilyConsentDashboardContextResponse } from '@/types/contracts/family_consent/get_family_consent_dashboard_context';
import type {
	FamilyConsentAudienceMode,
	FamilyConsentCompletionChannelMode,
	FamilyConsentDashboardRow,
	FamilyConsentRequestStatus,
	Request as FamilyConsentDashboardRequest,
	Response as FamilyConsentDashboardResponse,
} from '@/types/contracts/family_consent/get_family_consent_dashboard';

const route = useRoute();
const service = createFamilyConsentService();

const loadingContext = ref(false);
const loadingDashboard = ref(false);
const accessDenied = ref(false);
const errorMessage = ref('');
const dashboard = ref<FamilyConsentDashboardResponse | null>(null);

const options = reactive<FamilyConsentDashboardContextResponse['options']>({
	organizations: [],
	schools: [],
	request_types: [],
	statuses: [],
	audience_modes: [],
	completion_channel_modes: [],
});

const filters = reactive({
	organization: queryValue('organization'),
	school: queryValue('school'),
	request_type: queryValue('request_type'),
	status: queryValue('status'),
	audience_mode: queryValue('audience_mode'),
	completion_channel_mode: queryValue('completion_channel_mode'),
});

const requestRows = computed(() => dashboard.value?.rows || []);

const scopeLabel = computed(() => {
	if (filters.organization && filters.school) {
		return `${filters.organization} · ${filters.school}`;
	}
	if (filters.organization) {
		return filters.organization;
	}
	return 'All scoped organizations';
});

const requestCountLabel = computed(() => {
	const count = dashboard.value?.counts.requests || 0;
	return count === 1 ? '1 request in view' : `${count} requests in view`;
});

const generatedAtLabel = computed(() => {
	return formatDateTimeValue(dashboard.value?.meta.generated_at || '');
});

const kpiItems = computed(() => {
	const counts = dashboard.value?.counts || {
		requests: 0,
		pending: 0,
		completed: 0,
		declined: 0,
		withdrawn: 0,
		expired: 0,
		overdue: 0,
	};
	const exceptionTotal = counts.declined + counts.withdrawn + counts.expired + counts.overdue;

	return [
		{
			id: 'requests',
			label: 'Requests',
			value: counts.requests,
			subLabel: 'Published, closed, and archived requests in current scope',
		},
		{
			id: 'completed',
			label: 'Completed',
			value: counts.completed,
			subLabel: 'Students with a current approved or granted decision',
		},
		{
			id: 'pending',
			label: 'Pending',
			value: counts.pending,
			subLabel: 'Still waiting for portal or paper completion',
		},
		{
			id: 'exceptions',
			label: 'Exceptions',
			value: exceptionTotal,
			subLabel: 'Declined, withdrawn, overdue, or expired targets',
		},
	];
});

const channelCards = computed(() => {
	const rows = requestRows.value;
	return [
		{
			id: 'Portal Only' as FamilyConsentCompletionChannelMode,
			label: 'Portal only',
			value: rows.filter(row => row.completion_channel_mode === 'Portal Only').length,
			badge: 'Online',
			meta: 'Families complete these entirely in portal.',
		},
		{
			id: 'Portal Or Paper' as FamilyConsentCompletionChannelMode,
			label: 'Portal or paper',
			value: rows.filter(row => row.completion_channel_mode === 'Portal Or Paper').length,
			badge: 'Mixed',
			meta: 'Either portal completion or staff-recorded paper capture is valid.',
		},
		{
			id: 'Paper Only' as FamilyConsentCompletionChannelMode,
			label: 'Paper only',
			value: rows.filter(row => row.completion_channel_mode === 'Paper Only').length,
			badge: 'Offline',
			meta: 'Portal shows status only; staff record collected approvals in Desk.',
		},
	];
});

const showPaperTrackingNote = computed(() =>
	requestRows.value.some(row => row.completion_channel_mode === 'Paper Only')
);

function queryValue(key: string) {
	const value = route.query[key];
	return typeof value === 'string' ? value.trim() : '';
}

function normalizeNullable(value: string) {
	const normalized = String(value || '').trim();
	return normalized || null;
}

function setErrorState(err: unknown, fallbackMessage: string) {
	const message = err instanceof Error && err.message ? err.message : fallbackMessage;
	errorMessage.value = message;
	accessDenied.value = /permission|access/i.test(message);
}

function clearErrorState() {
	errorMessage.value = '';
	accessDenied.value = false;
}

function syncFilterToOptions<T extends string>(value: string, validValues: T[]) {
	if (value && !validValues.includes(value as T)) {
		return '';
	}
	return value;
}

function applyContextOptions(response: FamilyConsentDashboardContextResponse) {
	options.organizations = [...(response.options.organizations || [])];
	options.schools = [...(response.options.schools || [])];
	options.request_types = [...(response.options.request_types || [])];
	options.statuses = [...(response.options.statuses || [])];
	options.audience_modes = [...(response.options.audience_modes || [])];
	options.completion_channel_modes = [...(response.options.completion_channel_modes || [])];

	filters.organization = syncFilterToOptions(filters.organization, options.organizations);
	filters.school = syncFilterToOptions(filters.school, options.schools);
	filters.request_type = syncFilterToOptions(filters.request_type, options.request_types);
	filters.status = syncFilterToOptions(filters.status, options.statuses);
	filters.audience_mode = syncFilterToOptions(filters.audience_mode, options.audience_modes);
	filters.completion_channel_mode = syncFilterToOptions(
		filters.completion_channel_mode,
		options.completion_channel_modes
	);
}

async function refreshContext() {
	loadingContext.value = true;
	clearErrorState();
	try {
		const response = await service.getDashboardContext({
			organization: normalizeNullable(filters.organization),
		});
		applyContextOptions(response);
	} catch (err: unknown) {
		setErrorState(err, 'Unable to load forms and signatures filter options.');
	} finally {
		loadingContext.value = false;
	}
}

async function refreshDashboard() {
	loadingDashboard.value = true;
	clearErrorState();
	try {
		dashboard.value = await service.getDashboard({
			organization: normalizeNullable(filters.organization),
			school: normalizeNullable(filters.school),
			request_type: normalizeNullable(
				filters.request_type
			) as FamilyConsentDashboardRequest['request_type'],
			status: normalizeNullable(filters.status) as FamilyConsentDashboardRequest['status'],
			audience_mode: normalizeNullable(
				filters.audience_mode
			) as FamilyConsentDashboardRequest['audience_mode'],
			completion_channel_mode: normalizeNullable(
				filters.completion_channel_mode
			) as FamilyConsentDashboardRequest['completion_channel_mode'],
		});
	} catch (err: unknown) {
		dashboard.value = null;
		setErrorState(err, 'Unable to load forms and signatures analytics.');
	} finally {
		loadingDashboard.value = false;
	}
}

async function loadPage() {
	await refreshContext();
	if (errorMessage.value) return;
	await refreshDashboard();
}

async function handleOrganizationChange() {
	filters.school = '';
	await refreshContext();
	if (errorMessage.value) return;
	await refreshDashboard();
}

async function handleFilterChange() {
	await refreshDashboard();
}

function formatDateValue(value?: string | null) {
	const normalized = String(value || '').trim();
	if (!normalized) return 'No due date';
	const parsed = new Date(`${normalized}T00:00:00`);
	if (Number.isNaN(parsed.getTime())) return normalized;
	return new Intl.DateTimeFormat(undefined, {
		month: 'short',
		day: 'numeric',
		year: 'numeric',
	}).format(parsed);
}

function formatDateTimeValue(value: string) {
	const normalized = String(value || '').trim();
	if (!normalized) return 'just now';
	const parsed = new Date(normalized);
	if (Number.isNaN(parsed.getTime())) return normalized;
	return new Intl.DateTimeFormat(undefined, {
		month: 'short',
		day: 'numeric',
		year: 'numeric',
		hour: 'numeric',
		minute: '2-digit',
	}).format(parsed);
}

function deskRequestUrl(requestName: string) {
	return `/app/family-consent-request/${encodeURIComponent(requestName)}`;
}

function exceptionCount(row: FamilyConsentDashboardRow) {
	return row.declined_count + row.withdrawn_count + row.expired_count + row.overdue_count;
}

function completionPercentage(row: FamilyConsentDashboardRow) {
	if (!row.target_count) return 0;
	return Math.round((row.completed_count / row.target_count) * 100);
}

function statusBadgeClass(status: FamilyConsentRequestStatus) {
	if (status === 'Published') return 'bg-leaf/15 text-canopy';
	if (status === 'Draft') return 'bg-sand/60 text-clay';
	if (status === 'Closed') return 'bg-slate-100 text-slate-700';
	return 'bg-slate-200 text-slate-600';
}

function audienceBadgeClass(audienceMode: FamilyConsentAudienceMode) {
	if (audienceMode === 'Guardian') return 'bg-sky/20 text-canopy';
	if (audienceMode === 'Student') return 'bg-leaf/15 text-canopy';
	return 'bg-jacaranda/10 text-jacaranda';
}

function channelBadgeClass(channel: FamilyConsentCompletionChannelMode) {
	if (channel === 'Portal Only') return 'bg-sky/20 text-canopy';
	if (channel === 'Portal Or Paper') return 'bg-jacaranda/10 text-jacaranda';
	return 'bg-sand/60 text-clay';
}

function channelMeta(channel: FamilyConsentCompletionChannelMode) {
	if (channel === 'Portal Only') return 'Portal submission required';
	if (channel === 'Portal Or Paper') return 'Portal or paper accepted';
	return 'Paper completion only';
}

onMounted(() => {
	void loadPage();
});
</script>
