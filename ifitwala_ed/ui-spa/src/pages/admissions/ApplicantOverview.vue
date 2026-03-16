<!-- ifitwala_ed/ui-spa/src/pages/admissions/ApplicantOverview.vue -->

<template>
	<div class="admissions-overview">
		<div class="admissions-overview__header">
			<p class="type-h2 text-ink">{{ __('Overview') }}</p>
			<p class="type-body text-ink/65">
				{{ __('Track your application progress and next steps.') }}
			</p>
		</div>

		<div v-if="loading" class="admissions-overview__state-card">
			<div class="admissions-overview__state-inline">
				<Spinner class="h-4 w-4" />
				<p class="type-body-strong text-ink">{{ __('Loading overview…') }}</p>
			</div>
		</div>

		<div v-else-if="error" class="admissions-overview__error-card">
			<p class="type-body-strong text-rose-900">{{ __('Unable to load overview') }}</p>
			<p class="admissions-overview__error-text type-caption text-rose-900/80 whitespace-pre-wrap">
				{{ error }}
			</p>
			<button type="button" class="admissions-overview__retry-button" @click="loadSnapshot">
				{{ __('Try again') }}
			</button>
		</div>

		<div v-else class="admissions-overview__content">
			<div class="admissions-overview__summary-grid">
				<section class="admissions-overview__panel">
					<div class="admissions-overview__panel-header">
						<p class="type-body-strong text-ink">{{ __('Application details') }}</p>
					</div>
					<div class="admissions-overview__data-rows">
						<div
							v-for="row in applicationRows"
							:key="row.key"
							class="admissions-overview__data-row"
						>
							<p class="admissions-overview__data-label type-caption">{{ row.label }}</p>
							<p class="admissions-overview__data-value type-body">{{ row.value }}</p>
						</div>
					</div>
				</section>

				<section class="admissions-overview__panel">
					<div class="admissions-overview__panel-header">
						<p class="type-body-strong text-ink">{{ __('Profile summary') }}</p>
						<RouterLink
							:to="buildRouteLocation('admissions-profile')"
							class="admissions-overview__open-button"
						>
							{{ __('Open profile') }}
						</RouterLink>
					</div>
					<div class="admissions-overview__data-rows">
						<div v-for="row in profileRows" :key="row.key" class="admissions-overview__data-row">
							<p class="admissions-overview__data-label type-caption">{{ row.label }}</p>
							<p class="admissions-overview__data-value type-body">{{ row.value }}</p>
						</div>
					</div>
				</section>
			</div>

			<section class="admissions-overview__panel admissions-overview__panel--actions">
				<div class="admissions-overview__section-title">
					<p class="type-h3 text-ink">{{ __('Next actions') }}</p>
					<p class="type-caption text-ink/60">
						{{ __('Complete these steps to keep your application moving.') }}
					</p>
				</div>
				<p
					v-if="!snapshot?.next_actions?.length"
					class="admissions-overview__empty-note type-caption"
				>
					{{ __('No outstanding tasks right now.') }}
				</p>
				<div v-else class="admissions-overview__action-list">
					<div
						v-for="action in snapshot.next_actions"
						:key="action.label"
						class="admissions-overview__action-item"
					>
						<div class="admissions-overview__action-copy">
							<p class="type-body text-ink">{{ action.label }}</p>
							<p v-if="action.is_blocking" class="type-caption text-ink/60">
								{{ __('Required before submission.') }}
							</p>
						</div>
						<RouterLink
							:to="buildRouteLocation(action.route_name)"
							class="admissions-overview__open-button"
						>
							{{ __('Open') }}
						</RouterLink>
					</div>
				</div>
			</section>

			<section class="admissions-overview__completion-section">
				<div class="admissions-overview__section-title">
					<p class="type-body-strong text-ink">{{ __('Progress by section') }}</p>
					<p class="type-caption text-ink/60">
						{{ __('Review what is complete and what is still pending.') }}
					</p>
				</div>
				<div class="admissions-overview__completion-grid">
					<div
						v-for="card in completionCards"
						:key="card.key"
						class="admissions-overview__completion-card"
					>
						<p class="type-body-strong text-ink">{{ card.label }}</p>
						<p class="admissions-overview__status-pill type-caption" :class="card.pillClass">
							{{ card.statusLabel }}
						</p>
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
			return 'admissions-overview__status-pill--complete';
		case 'in_progress':
			return 'admissions-overview__status-pill--in-progress';
		case 'optional':
			return 'admissions-overview__status-pill--optional';
		case 'pending':
		default:
			return 'admissions-overview__status-pill--pending';
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
