<!-- ifitwala_ed/ui-spa/src/pages/admissions/ApplicantSubmit.vue -->

<template>
	<div class="space-y-6">
		<div>
			<p class="type-h2 text-ink">{{ __('Submit application') }}</p>
			<p class="mt-1 type-caption text-ink/60">
				{{ __('Confirm your application is ready for review.') }}
			</p>
		</div>

		<div v-if="loading" class="rounded-2xl border border-border/70 bg-surface px-4 py-4">
			<div class="flex items-center gap-3">
				<Spinner class="h-4 w-4" />
				<p class="type-body-strong text-ink">{{ __('Checking readiness…') }}</p>
			</div>
		</div>

		<div v-else-if="error" class="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3">
			<p class="type-body-strong text-rose-900">{{ __('Unable to load submission status') }}</p>
			<p class="mt-1 type-caption text-rose-900/80 whitespace-pre-wrap">{{ error }}</p>
			<button
				type="button"
				class="mt-3 rounded-full border border-rose-200 bg-white px-4 py-2 type-caption text-rose-900"
				@click="loadSnapshot"
			>
				{{ __('Try again') }}
			</button>
		</div>

		<div v-else class="space-y-4">
			<div v-if="actionError" class="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3">
				<p class="type-body-strong text-amber-900">{{ __('Notice') }}</p>
				<p class="mt-1 type-caption text-amber-900/80">{{ actionError }}</p>
			</div>
			<div class="rounded-2xl border border-border/70 bg-white px-4 py-4 shadow-soft">
				<p class="type-body-strong text-ink">{{ __('Readiness checklist') }}</p>
				<ul class="mt-3 space-y-2">
					<li v-for="item in readinessItems" :key="item.label" class="flex items-center gap-2">
						<span class="h-2.5 w-2.5 rounded-full" :class="item.dot" />
						<span class="type-caption text-ink/70">{{ item.label }}</span>
					</li>
				</ul>
			</div>

			<div
				v-if="blockingActions.length"
				class="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3"
			>
				<p class="type-body-strong text-amber-900">{{ __('Action required') }}</p>
				<p class="mt-1 type-caption text-amber-900/80">{{ blockingMessage }}</p>
				<div class="mt-3 flex flex-col gap-2">
					<RouterLink
						v-for="action in blockingActions"
						:key="`${action.route_name}:${action.label}`"
						:to="{ name: action.route_name }"
						class="flex items-center justify-between rounded-xl border border-amber-200 bg-white px-3 py-2 type-caption text-amber-900"
					>
						<span>{{ action.label }}</span>
						<span>{{ __('Open') }}</span>
					</RouterLink>
				</div>
			</div>

			<div
				v-if="documentsUnderReview"
				class="rounded-2xl border border-leaf/40 bg-leaf/10 px-4 py-3"
			>
				<p class="type-body-strong text-emerald-900">{{ __('Awaiting admissions review') }}</p>
				<p class="mt-1 type-caption text-emerald-900/80">
					{{
						__(
							'All required documents are uploaded. You can submit now while admissions reviews your files.'
						)
					}}
				</p>
				<RouterLink
					:to="{ name: 'admissions-documents' }"
					class="mt-3 inline-flex rounded-full border border-leaf/40 bg-white px-4 py-2 type-caption text-emerald-900"
				>
					{{ __('View document statuses') }}
				</RouterLink>
			</div>

			<div class="flex flex-wrap items-center gap-3">
				<button
					type="button"
					class="rounded-full bg-ink px-5 py-2 type-caption text-white shadow-soft disabled:opacity-50"
					:disabled="isReadOnly || !isReady"
					@click="openSubmit"
				>
					{{ __('Submit application') }}
				</button>
				<RouterLink
					v-if="!isReady && blockingActions.length"
					:to="{ name: firstBlockingRouteName }"
					class="rounded-full border border-border/70 bg-white px-4 py-2 type-caption text-ink/70"
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
const { session } = useAdmissionsSession();

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
	return __('Complete "{0}" before submitting.').replace('{0}', first.label);
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
				? 'bg-leaf'
				: item.state === 'in_progress'
					? 'bg-sun'
					: 'bg-amber-300',
	}));
});

async function loadSnapshot() {
	loading.value = true;
	error.value = null;
	actionError.value = '';
	try {
		snapshot.value = await service.getSnapshot();
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
	overlay.open('admissions-submit', { readOnly: isReadOnly.value });
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
