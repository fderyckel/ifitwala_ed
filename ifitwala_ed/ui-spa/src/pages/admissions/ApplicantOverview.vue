<!-- ifitwala_ed/ui-spa/src/pages/admissions/ApplicantOverview.vue -->

<template>
	<div class="admissions-page">
		<header class="page-header">
			<div class="page-header__intro">
				<h1 class="type-h1 text-ink">{{ __('Overview') }}</h1>
				<p class="type-meta text-ink/70">
					{{ __('Track your application progress and next steps.') }}
				</p>
			</div>
		</header>

		<div v-if="loading" class="admissions-state-card">
			<div class="admissions-state-inline">
				<Spinner class="h-4 w-4" />
				<p class="type-body-strong text-ink">{{ __('Loading overview…') }}</p>
			</div>
		</div>

		<div v-else-if="error" class="if-banner if-banner--danger">
			<p class="if-banner__title type-body-strong">{{ __('Unable to load overview') }}</p>
			<p class="if-banner__body mt-1 type-caption whitespace-pre-wrap">{{ error }}</p>
			<button type="button" class="if-button if-button--secondary mt-3" @click="loadSnapshot">
				{{ __('Try again') }}
			</button>
		</div>

		<div v-else class="space-y-4">
			<div class="grid gap-4 md:grid-cols-2">
				<section class="admissions-card admissions-card--plain">
					<div class="flex items-center justify-between gap-3">
						<p class="type-body-strong text-ink">{{ __('Application details') }}</p>
					</div>
					<div class="admissions-detail-grid mt-3">
						<div
							v-for="row in applicationRows"
							:key="row.key"
							class="admissions-detail-card flex flex-wrap items-center justify-between gap-2"
						>
							<p class="type-caption text-ink/60">{{ row.label }}</p>
							<p class="ml-auto text-right type-body text-ink/80">{{ row.value }}</p>
						</div>
					</div>
				</section>

				<section class="admissions-card admissions-card--plain">
					<div class="flex items-center justify-between gap-3">
						<p class="type-body-strong text-ink">{{ __('Profile summary') }}</p>
						<RouterLink
							:to="buildRouteLocation('admissions-profile')"
							class="if-button if-button--secondary"
						>
							{{ __('Open profile') }}
						</RouterLink>
					</div>
					<div class="admissions-detail-grid mt-3">
						<div
							v-for="row in profileRows"
							:key="row.key"
							class="admissions-detail-card flex flex-wrap items-center justify-between gap-2"
						>
							<p class="type-caption text-ink/60">{{ row.label }}</p>
							<p class="ml-auto text-right type-body text-ink/80">{{ row.value }}</p>
						</div>
					</div>
				</section>
			</div>

			<section class="admissions-card admissions-card--plain">
				<div class="flex flex-col gap-1">
					<p class="type-h3 text-ink">{{ __('Next actions') }}</p>
					<p class="type-caption text-ink/60">
						{{ __('Complete these steps to keep your application moving.') }}
					</p>
				</div>
				<p v-if="!snapshot?.next_actions?.length" class="mt-3 type-caption text-ink/60">
					{{ __('No outstanding tasks right now.') }}
				</p>
				<div v-else class="admissions-action-list mt-3">
					<RouterLink
						v-for="action in snapshot.next_actions"
						:key="action.label"
						:to="buildRouteLocation(action.route_name)"
						class="admissions-action-link"
					>
						<div class="flex min-w-0 flex-col gap-1">
							<p class="type-body">{{ action.label }}</p>
							<p v-if="action.is_blocking" class="type-caption text-clay/80">
								{{ __('Required before submission.') }}
							</p>
						</div>
						<span class="type-caption">{{ __('Open') }}</span>
					</RouterLink>
				</div>
			</section>

			<section class="admissions-card admissions-card--plain">
				<div class="flex flex-col gap-1">
					<p class="type-body-strong text-ink">{{ __('Progress by section') }}</p>
					<p class="type-caption text-ink/60">
						{{ __('Review what is complete and what is still pending.') }}
					</p>
				</div>
				<div class="mt-3 grid gap-3 md:grid-cols-2">
					<div
						v-for="card in completionCards"
						:key="card.key"
						class="admissions-detail-card flex flex-wrap items-center justify-between gap-3"
					>
						<div class="flex items-center gap-2">
							<span class="admissions-status-dot" :class="card.dotClass" />
							<p class="type-body-strong text-ink">{{ card.label }}</p>
						</div>
						<span class="admissions-status-pill type-caption" :class="card.pillClass">
							{{ card.statusLabel }}
						</span>
					</div>
				</div>
			</section>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { RouterLink } from 'vue-router';
import { Spinner } from 'frappe-ui';

import { useAdmissionsSession } from '@/composables/useAdmissionsSession';
import { createAdmissionsService } from '@/lib/services/admissions/admissionsService';
import { __ } from '@/lib/i18n';
import { uiSignals, SIGNAL_ADMISSIONS_PORTAL_INVALIDATE } from '@/lib/uiSignals';
import type { Response as ApplicantSnapshot } from '@/types/contracts/admissions/get_applicant_snapshot';

const service = createAdmissionsService();
const { currentApplicantName, buildRouteLocation } = useAdmissionsSession();

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

function statusPillClass(state: string) {
	switch (state) {
		case 'complete':
			return 'admissions-status-pill--success';
		case 'in_progress':
			return 'admissions-status-pill--warm';
		case 'optional':
			return 'admissions-status-pill--quiet';
		case 'pending':
		default:
			return 'admissions-status-pill--quiet';
	}
}

function statusDotClass(state: string) {
	switch (state) {
		case 'complete':
			return 'admissions-status-dot--complete';
		case 'in_progress':
			return 'admissions-status-dot--in-progress';
		case 'optional':
		case 'pending':
		default:
			return 'admissions-status-dot--pending';
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
		{ key: 'recommendations', label: __('Recommendations'), state: completeness.recommendations },
		{ key: 'interviews', label: __('Interviews'), state: completeness.interviews },
	].map(card => ({
		...card,
		dotClass: statusDotClass(card.state),
		statusLabel: statusLabel(card.state),
		pillClass: statusPillClass(card.state),
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
	if (!currentApplicantName.value) {
		snapshot.value = null;
		return;
	}
	loading.value = true;
	error.value = null;
	try {
		snapshot.value = await service.getSnapshot({ student_applicant: currentApplicantName.value });
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
