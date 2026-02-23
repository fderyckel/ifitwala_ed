<!-- ifitwala_ed/ui-spa/src/pages/admissions/ApplicantOverview.vue -->

<template>
	<div class="space-y-6">
		<div>
			<p class="type-h2 text-ink">{{ __('Overview') }}</p>
			<p class="mt-1 type-caption text-ink/60">
				{{ __('Track your application progress and next steps.') }}
			</p>
		</div>

		<div v-if="loading" class="rounded-2xl border border-border/70 bg-surface px-4 py-4">
			<div class="flex items-center gap-3">
				<Spinner class="h-4 w-4" />
				<p class="type-body-strong text-ink">{{ __('Loading overview…') }}</p>
			</div>
		</div>

		<div v-else-if="error" class="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3">
			<p class="type-body-strong text-rose-900">{{ __('Unable to load overview') }}</p>
			<p class="mt-1 type-caption text-rose-900/80 whitespace-pre-wrap">{{ error }}</p>
			<button
				type="button"
				class="mt-3 rounded-full border border-rose-200 bg-white px-4 py-2 type-caption text-rose-900"
				@click="loadSnapshot"
			>
				{{ __('Try again') }}
			</button>
		</div>

		<div v-else>
			<div class="grid gap-4 md:grid-cols-2">
				<div class="rounded-2xl border border-border/70 bg-white px-4 py-4 shadow-soft">
					<div class="flex items-center justify-between gap-3">
						<p class="type-body-strong text-ink">{{ __('Application details') }}</p>
					</div>
					<div class="mt-3 grid gap-3">
						<div
							v-for="row in applicationRows"
							:key="row.key"
							class="flex items-center justify-between gap-3 rounded-xl border border-border/60 bg-sand/30 px-3 py-2"
						>
							<p class="type-caption text-ink/60">{{ row.label }}</p>
							<p class="type-body text-ink/80 text-right">{{ row.value }}</p>
						</div>
					</div>
				</div>

				<div class="rounded-2xl border border-border/70 bg-white px-4 py-4 shadow-soft">
					<div class="flex items-center justify-between gap-3">
						<p class="type-body-strong text-ink">{{ __('Profile summary') }}</p>
						<RouterLink
							:to="{ name: 'admissions-profile' }"
							class="rounded-full bg-ink px-4 py-2 type-caption text-white"
						>
							{{ __('Open profile') }}
						</RouterLink>
					</div>
					<div class="mt-3 grid gap-3">
						<div
							v-for="row in profileRows"
							:key="row.key"
							class="flex items-center justify-between gap-3 rounded-xl border border-border/60 px-3 py-2"
						>
							<p class="type-caption text-ink/60">{{ row.label }}</p>
							<p class="type-body text-ink/80 text-right">{{ row.value }}</p>
						</div>
					</div>
				</div>
			</div>

			<div class="grid gap-4 md:grid-cols-2">
				<div
					v-for="card in completionCards"
					:key="card.key"
					class="rounded-2xl border border-border/70 bg-white px-4 py-4 shadow-soft"
				>
					<p class="type-body-strong text-ink">{{ card.label }}</p>
					<p class="mt-1 type-caption" :class="card.tone">
						{{ card.statusLabel }}
					</p>
				</div>
			</div>

			<div class="mt-6 rounded-2xl border border-border/70 bg-white px-4 py-4 shadow-soft">
				<p class="type-body-strong text-ink">{{ __('Next actions') }}</p>
				<p v-if="!snapshot?.next_actions?.length" class="mt-2 type-caption text-ink/60">
					{{ __('No outstanding tasks right now.') }}
				</p>
				<div v-else class="mt-3 flex flex-col gap-3">
					<div
						v-for="action in snapshot.next_actions"
						:key="action.label"
						class="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-border/60 bg-sand/40 px-4 py-3"
					>
						<div>
							<p class="type-body text-ink">{{ action.label }}</p>
							<p v-if="action.is_blocking" class="type-caption text-ink/60">
								{{ __('Required before submission.') }}
							</p>
						</div>
						<RouterLink
							:to="{ name: action.route_name }"
							class="rounded-full bg-ink px-4 py-2 type-caption text-white"
						>
							{{ __('Open') }}
						</RouterLink>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { RouterLink } from 'vue-router';
import { Spinner } from 'frappe-ui';

import { createAdmissionsService } from '@/lib/services/admissions/admissionsService';
import { __ } from '@/lib/i18n';
import { uiSignals, SIGNAL_ADMISSIONS_PORTAL_INVALIDATE } from '@/lib/uiSignals';
import type { Response as ApplicantSnapshot } from '@/types/contracts/admissions/get_applicant_snapshot';

const service = createAdmissionsService();

const snapshot = ref<ApplicantSnapshot | null>(null);
const loading = ref(false);
const error = ref<string | null>(null);

function statusLabel(state: string) {
	switch (state) {
		case 'complete':
			return __('Complete');
		case 'in_progress':
			return __('In progress');
		case 'optional':
			return __('Optional');
		case 'pending':
		default:
			return __('Pending');
	}
}

function statusTone(state: string) {
	switch (state) {
		case 'complete':
			return 'text-leaf';
		case 'in_progress':
			return 'text-sun';
		case 'optional':
			return 'text-ink/55';
		case 'pending':
		default:
			return 'text-ink/60';
	}
}

const completionCards = computed(() => {
	const completeness = snapshot.value?.completeness;
	if (!completeness) return [];
	return [
		{ key: 'profile', label: __('Profile information'), state: completeness.profile },
		{ key: 'health', label: __('Health information'), state: completeness.health },
		{ key: 'documents', label: __('Documents'), state: completeness.documents },
		{ key: 'policies', label: __('Policies'), state: completeness.policies },
		{ key: 'interviews', label: __('Interviews'), state: completeness.interviews },
	].map(card => ({
		...card,
		statusLabel: statusLabel(card.state),
		tone: statusTone(card.state),
	}));
});

function displayText(value: unknown): string {
	const text = typeof value === 'string' ? value.trim() : String(value || '').trim();
	return text || __('Not provided');
}

const applicationRows = computed(() => {
	const context = snapshot.value?.application_context;
	if (!context) return [];
	return [
		{ key: 'school', label: __('School'), value: displayText(context.school) },
		{ key: 'organization', label: __('Organization'), value: displayText(context.organization) },
		{
			key: 'academic_year',
			label: __('Academic year'),
			value: displayText(context.academic_year),
		},
		{ key: 'program', label: __('Program'), value: displayText(context.program) },
	];
});

const profileRows = computed(() => {
	const profile = snapshot.value?.profile;
	if (!profile) return [];
	return [
		{
			key: 'preferred_name',
			label: __('Preferred name'),
			value: displayText(profile.student_preferred_name),
		},
		{
			key: 'date_of_birth',
			label: __('Date of birth'),
			value: displayText(profile.student_date_of_birth),
		},
		{
			key: 'nationality',
			label: __('Nationality'),
			value: displayText(profile.student_nationality),
		},
		{
			key: 'first_language',
			label: __('First language'),
			value: displayText(profile.student_first_language),
		},
	];
});

async function loadSnapshot() {
	loading.value = true;
	error.value = null;
	try {
		snapshot.value = await service.getSnapshot();
	} catch (err) {
		const message = err instanceof Error ? err.message : __('Unable to load overview.');
		error.value = message;
	} finally {
		loading.value = false;
	}
}

let unsubscribe: (() => void) | null = null;

onMounted(async () => {
	await loadSnapshot();
	unsubscribe = uiSignals.subscribe(SIGNAL_ADMISSIONS_PORTAL_INVALIDATE, () => {
		loadSnapshot();
	});
});

onBeforeUnmount(() => {
	if (unsubscribe) unsubscribe();
});
</script>
