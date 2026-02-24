<!-- ifitwala_ed/ui-spa/src/pages/staff/admissions/AdmissionsCockpit.vue -->
<template>
	<div class="flex flex-col gap-6 p-6">
		<header class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
			<div>
				<h1 class="type-h2 text-canopy">Admissions Cockpit</h1>
				<p class="type-caption text-slate-token/80">
					Application progression and blockers (applicant-centered)
				</p>
			</div>
			<button
				class="fui-btn-primary rounded-full px-4 py-1.5 text-sm font-medium transition active:scale-95"
				@click="refreshNow"
			>
				Refresh
			</button>
		</header>

		<FiltersBar class="analytics-filters">
			<div class="flex flex-col gap-1">
				<label class="type-label">Organization</label>
				<select
					v-model="filters.organization"
					class="h-9 min-w-[180px] rounded-md border px-2 text-sm"
				>
					<option value="">All Organizations</option>
					<option v-for="org in organizations" :key="org" :value="org">{{ org }}</option>
				</select>
			</div>

			<div class="flex flex-col gap-1">
				<label class="type-label">School</label>
				<select v-model="filters.school" class="h-9 min-w-[180px] rounded-md border px-2 text-sm">
					<option value="">All Schools</option>
					<option v-for="school in schools" :key="school" :value="school">{{ school }}</option>
				</select>
			</div>

			<div class="flex min-w-[180px] items-end pb-1">
				<label class="inline-flex items-center gap-2 type-label">
					<input v-model="filters.assigned_to_me" type="checkbox" class="h-4 w-4 rounded border" />
					<span>My Assignments Only</span>
				</label>
			</div>
		</FiltersBar>

		<div
			v-if="error"
			class="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
		>
			{{ error }}
		</div>

		<div v-if="loading" class="py-10 text-center text-slate-500">Loading cockpit...</div>

		<template v-else>
			<KpiRow :items="kpiItems" />

			<section class="rounded-xl border border-slate-200 bg-white p-4">
				<h2 class="type-overline mb-3 text-slate-token/70">Top Admission Blockers</h2>
				<div class="flex flex-wrap gap-2">
					<button
						class="rounded-full border px-3 py-1 text-xs font-semibold transition"
						:class="
							activeBlocker
								? 'border-slate-300 text-slate-token hover:border-slate-500'
								: 'border-canopy bg-canopy/10 text-canopy'
						"
						@click="activeBlocker = ''"
					>
						All
					</button>
					<button
						v-for="blocker in blockers"
						:key="blocker.kind"
						class="rounded-full border px-3 py-1 text-xs font-semibold transition"
						:class="
							activeBlocker === blocker.kind
								? 'border-canopy bg-canopy/10 text-canopy'
								: 'border-slate-300 text-slate-token hover:border-slate-500'
						"
						@click="activeBlocker = blocker.kind"
					>
						{{ blocker.label }} · {{ blocker.count }}
					</button>
				</div>
			</section>

			<section class="overflow-x-auto">
				<div class="grid min-w-[1150px] grid-cols-6 gap-4">
					<section
						v-for="column in columns"
						:key="column.id"
						class="flex min-h-[360px] flex-col rounded-xl border border-slate-200 bg-slate-50"
					>
						<header class="flex items-center justify-between border-b border-slate-200 px-3 py-2">
							<h3 class="type-label text-canopy">{{ column.title }}</h3>
							<span
								class="rounded-full bg-white px-2 py-0.5 text-xs font-semibold text-slate-token"
							>
								{{ filteredItems(column.items).length }}
							</span>
						</header>

						<div class="flex flex-1 flex-col gap-3 p-3">
							<article
								v-for="item in filteredItems(column.items)"
								:key="item.name"
								class="rounded-lg border border-slate-200 bg-white p-3 shadow-sm"
							>
								<div class="mb-2 flex items-start justify-between gap-2">
									<div>
										<p class="type-body-strong text-ink">{{ item.display_name }}</p>
										<p class="type-caption text-slate-token/70">{{ item.name }}</p>
									</div>
									<a
										:href="item.open_url"
										target="_blank"
										rel="noopener noreferrer"
										class="rounded-md border border-slate-200 px-2 py-1 text-xs font-semibold text-canopy hover:border-canopy"
									>
										Open
									</a>
								</div>

								<p class="mb-2 type-caption text-slate-token/80">
									{{ item.school }}
									<span v-if="item.program_offering">· {{ item.program_offering }}</span>
								</p>

								<div class="mb-2 flex flex-wrap gap-1">
									<span
										class="rounded-full border border-slate-200 bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-token"
									>
										{{ item.application_status }}
									</span>
									<span :class="pillClass(item.readiness.profile_ok)">Profile</span>
									<span :class="pillClass(item.readiness.documents_ok)">Docs</span>
									<span :class="pillClass(item.readiness.policies_ok)">Policies</span>
									<span :class="pillClass(item.readiness.health_ok)">Health</span>
								</div>

								<div v-if="item.top_blockers.length" class="space-y-1">
									<p class="type-caption text-slate-token/80">Missing / Blocked</p>
									<a
										v-for="issue in item.top_blockers"
										:key="`${item.name}-${issue.kind}-${issue.label}`"
										:href="issue.target_url || item.open_url"
										target="_blank"
										rel="noopener noreferrer"
										class="block text-xs text-red-700 hover:underline"
									>
										{{ issue.label }}
									</a>
								</div>
							</article>

							<div
								v-if="!filteredItems(column.items).length"
								class="flex flex-1 items-center justify-center rounded-lg border border-dashed border-slate-300 bg-white/70 p-4 text-xs text-slate-500"
							>
								No applicants in this stage.
							</div>
						</div>
					</section>
				</div>
			</section>
		</template>
	</div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';

import FiltersBar from '@/components/filters/FiltersBar.vue';
import KpiRow from '@/components/analytics/KpiRow.vue';
import { getAdmissionsCockpitData } from '@/lib/admission';

type CockpitCounts = {
	active_applications: number;
	blocked_applications: number;
	ready_for_decision: number;
	accepted_pending_promotion: number;
	my_open_assignments: number;
};

type CockpitBlocker = {
	kind: string;
	label: string;
	count: number;
};

type CockpitCard = {
	name: string;
	display_name: string;
	application_status: string;
	school: string;
	program_offering?: string;
	top_blockers: {
		kind: string;
		label: string;
		target_url?: string;
		target_label?: string;
	}[];
	readiness: {
		profile_ok: boolean;
		documents_ok: boolean;
		policies_ok: boolean;
		health_ok: boolean;
	};
	open_url: string;
	blockers: {
		kind: string;
		target_url?: string;
		target_label?: string;
	}[];
};

type CockpitColumn = {
	id: string;
	title: string;
	items: CockpitCard[];
};

type CockpitPayload = {
	config?: {
		organizations?: string[];
		schools?: string[];
	};
	counts?: CockpitCounts;
	blockers?: CockpitBlocker[];
	columns?: CockpitColumn[];
};

const loading = ref(false);
const error = ref('');
const data = ref<CockpitPayload | null>(null);
const activeBlocker = ref('');

const filters = ref({
	organization: '',
	school: '',
	assigned_to_me: true,
});

let refreshTimer: ReturnType<typeof setTimeout> | null = null;
let requestToken = 0;

const organizations = computed(() => data.value?.config?.organizations || []);
const schools = computed(() => data.value?.config?.schools || []);
const blockers = computed(() => data.value?.blockers || []);
const columns = computed(() => data.value?.columns || []);

const kpiItems = computed(() => {
	const counts = data.value?.counts || {
		active_applications: 0,
		blocked_applications: 0,
		ready_for_decision: 0,
		accepted_pending_promotion: 0,
		my_open_assignments: 0,
	};
	return [
		{ id: 'active', label: 'Active Applications', value: counts.active_applications },
		{ id: 'blocked', label: 'Blocked', value: counts.blocked_applications, hint: 'Action Needed' },
		{ id: 'decision', label: 'Ready for Decision', value: counts.ready_for_decision },
		{
			id: 'promotion',
			label: 'Accepted Pending Promotion',
			value: counts.accepted_pending_promotion,
		},
		{ id: 'assignments', label: 'My Open Assignments', value: counts.my_open_assignments },
	];
});

function pillClass(ok: boolean) {
	return ok
		? 'rounded-full border border-emerald-300 bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-700'
		: 'rounded-full border border-amber-300 bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-800';
}

function filteredItems(items: CockpitCard[]) {
	if (!activeBlocker.value) {
		return items;
	}
	return (items || []).filter(item =>
		(item.blockers || []).some(row => row.kind === activeBlocker.value)
	);
}

function queueRefresh() {
	if (refreshTimer) {
		clearTimeout(refreshTimer);
	}
	refreshTimer = setTimeout(() => {
		void refreshNow();
	}, 300);
}

async function refreshNow() {
	const token = ++requestToken;
	loading.value = true;
	error.value = '';
	try {
		const payload = await getAdmissionsCockpitData({
			organization: filters.value.organization || undefined,
			school: filters.value.school || undefined,
			assigned_to_me: filters.value.assigned_to_me ? 1 : 0,
			limit: 120,
		});
		if (token !== requestToken) {
			return;
		}
		data.value = payload;

		if (filters.value.school && !schools.value.includes(filters.value.school)) {
			filters.value.school = '';
		}
	} catch (err: any) {
		if (token !== requestToken) {
			return;
		}
		error.value = err?.message || 'Could not load admissions cockpit.';
	} finally {
		if (token === requestToken) {
			loading.value = false;
		}
	}
}

watch(
	() => [filters.value.organization, filters.value.school, filters.value.assigned_to_me],
	() => {
		queueRefresh();
	}
);

onMounted(() => {
	void refreshNow();
});
</script>
