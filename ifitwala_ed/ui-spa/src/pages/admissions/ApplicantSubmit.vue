<!-- ifitwala_ed/ui-spa/src/pages/admissions/ApplicantSubmit.vue -->

<template>
	<div data-testid="admissions-submit-page" class="admissions-page">
		<header class="page-header">
			<div class="page-header__intro">
				<h1 class="type-h1 text-ink">{{ __('Submit application') }}</h1>
				<p class="type-meta text-ink/70">
					{{ __('Confirm your application is ready for review.') }}
				</p>
			</div>
		</header>

		<div v-if="loading" class="admissions-state-card">
			<div class="admissions-state-inline">
				<Spinner class="h-4 w-4" />
				<p class="type-body-strong text-ink">{{ __('Checking readiness…') }}</p>
			</div>
		</div>

		<div v-else-if="error" class="if-banner if-banner--danger">
			<p class="if-banner__title type-body-strong">{{ __('Unable to load submission status') }}</p>
			<p class="if-banner__body mt-1 type-caption whitespace-pre-wrap">{{ error }}</p>
			<button type="button" class="if-button if-button--secondary mt-3" @click="loadSnapshot">
				{{ __('Try again') }}
			</button>
		</div>

		<div v-else class="space-y-4">
			<div v-if="actionError" class="admissions-card admissions-card--warm">
				<p class="type-body-strong text-clay">{{ __('Notice') }}</p>
				<p class="mt-1 type-caption text-clay/85">{{ actionError }}</p>
			</div>
			<div class="admissions-card admissions-card--plain">
				<p class="type-body-strong text-ink">{{ __('Readiness checklist') }}</p>
				<ul class="mt-3 space-y-2">
					<li v-for="item in readinessItems" :key="item.label" class="admissions-checklist-row">
						<span class="admissions-status-dot" :class="item.dot" />
						<span class="type-caption text-ink/70">{{ item.label }}</span>
					</li>
				</ul>
			</div>

			<div
				v-if="blockingActions.length"
				data-testid="admissions-submit-blocked"
				class="admissions-card admissions-card--warm"
			>
				<p class="type-body-strong text-clay">{{ __('Action required') }}</p>
				<p class="mt-1 type-caption text-clay/85">{{ blockingMessage }}</p>
				<div class="admissions-action-list mt-3">
					<RouterLink
						v-for="action in blockingActions"
						:key="`${action.route_name}:${action.label}`"
						:to="buildRouteLocation(action.route_name)"
						class="admissions-action-link type-caption"
					>
						<span>{{ action.label }}</span>
						<span>{{ __('Open') }}</span>
					</RouterLink>
				</div>
			</div>

			<div v-if="documentsUnderReview" class="admissions-card admissions-card--success">
				<p class="type-body-strong text-canopy">{{ __('Awaiting admissions review') }}</p>
				<p class="mt-1 type-caption text-canopy/85">
					{{
						__(
							'All required documents are uploaded. You can submit now while admissions reviews your files.'
						)
					}}
				</p>
				<RouterLink
					:to="buildRouteLocation('admissions-documents')"
					class="if-button if-button--secondary mt-3"
				>
					{{ __('View document statuses') }}
				</RouterLink>
			</div>

			<div class="flex flex-wrap items-center gap-3">
				<button
					data-testid="admissions-submit-open"
					type="button"
					class="if-button if-button--primary"
					:disabled="isReadOnly || !isReady"
					@click="openSubmit"
				>
					{{ __('Submit application') }}
				</button>
				<RouterLink
					v-if="!isReady && blockingActions.length"
					:to="buildRouteLocation(firstBlockingRouteName)"
					class="if-button if-button--secondary"
				>
					{{ __('Open first required step') }}
				</RouterLink>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { RouterLink } from 'vue-router';
import { Spinner } from 'frappe-ui';

import { createAdmissionsService } from '@/lib/services/admissions/admissionsService';
import { useAdmissionsSession } from '@/composables/useAdmissionsSession';
import { useOverlayStack } from '@/composables/useOverlayStack';
import { __ } from '@/lib/i18n';
import { uiSignals, SIGNAL_ADMISSIONS_PORTAL_INVALIDATE } from '@/lib/uiSignals';
import type { Response as ApplicantSnapshot } from '@/types/contracts/admissions/get_applicant_snapshot';
import type { NextAction } from '@/types/contracts/admissions/types';

const service = createAdmissionsService();
const overlay = useOverlayStack();
const { session, currentApplicantName, buildRouteLocation } = useAdmissionsSession();

const snapshot = ref<ApplicantSnapshot | null>(null);
const loading = ref(false);
const error = ref<string | null>(null);
const actionError = ref('');

const isReadOnly = computed(() => Boolean(session.value?.applicant?.is_read_only));

const blockingActions = computed<NextAction[]>(() => {
	const actions = snapshot.value?.next_actions || [];
	return actions.filter(action => action.is_blocking);
});

const documentsUnderReview = computed(() => {
	const actions = snapshot.value?.next_actions || [];
	return actions.some(
		action =>
			action.route_name === 'admissions-documents' &&
			!action.is_blocking &&
			snapshot.value?.completeness?.documents === 'in_progress'
	);
});

const isReady = computed(() => {
	return blockingActions.value.length === 0;
});

const firstBlockingRouteName = computed(() => {
	return blockingActions.value[0]?.route_name || 'admissions-overview';
});

const blockingMessage = computed(() => {
	if (isReady.value) return '';
	const first = blockingActions.value[0];
	if (!first) return __('Complete all required sections before submitting.');
	return __('Complete "{0}" before submitting.', [first.label]);
});

const readinessItems = computed(() => {
	const completeness = snapshot.value?.completeness;
	if (!completeness) return [];
	const items = [
		{ label: __('Profile information'), state: completeness.profile },
		{ label: __('Health information'), state: completeness.health },
		{ label: __('Documents'), state: completeness.documents },
		{ label: __('Policies'), state: completeness.policies },
		{ label: __('Recommendations'), state: completeness.recommendations },
	];
	return items.map(item => ({
		...item,
		dot:
			item.state === 'complete'
				? 'admissions-status-dot--complete'
				: item.state === 'in_progress'
					? 'admissions-status-dot--in-progress'
					: 'admissions-status-dot--pending',
	}));
});

async function loadSnapshot() {
	if (!currentApplicantName.value) {
		snapshot.value = null;
		error.value = null;
		return;
	}
	loading.value = true;
	error.value = null;
	actionError.value = '';
	try {
		snapshot.value = await service.getSnapshot({ student_applicant: currentApplicantName.value });
	} catch (err) {
		const message = err instanceof Error ? err.message : __('Unable to load submission status.');
		error.value = message;
	} finally {
		loading.value = false;
	}
}

function openSubmit() {
	if (isReadOnly.value) {
		actionError.value = __('This application is read-only.');
		return;
	}
	if (!isReady.value) {
		actionError.value =
			blockingMessage.value || __('Complete all required sections before submitting.');
		return;
	}
	actionError.value = '';
	overlay.open('admissions-submit', {
		studentApplicant: currentApplicantName.value,
		readOnly: isReadOnly.value,
	});
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
