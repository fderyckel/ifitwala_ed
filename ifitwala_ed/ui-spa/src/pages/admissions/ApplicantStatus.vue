<!-- ifitwala_ed/ui-spa/src/pages/admissions/ApplicantStatus.vue -->

<template>
	<div class="space-y-6">
		<div>
			<p class="type-h2 text-ink">{{ __('Application status') }}</p>
			<p class="mt-1 type-caption text-ink/60">
				{{ __('Track the current status of your admissions application.') }}
			</p>
		</div>

		<div class="rounded-2xl border border-border/70 bg-white px-4 py-4 shadow-soft">
			<p class="type-body-strong text-ink">{{ __('Current status') }}</p>
			<p class="mt-2 type-h3 text-ink">{{ portalStatus || __('—') }}</p>
			<p v-if="readOnlyReason" class="mt-2 type-caption text-ink/60">
				{{ readOnlyReason }}
			</p>
		</div>

		<div
			v-if="enrollmentOffer"
			class="rounded-2xl border border-border/70 bg-white px-4 py-4 shadow-soft"
		>
			<div class="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
				<div>
					<p class="type-body-strong text-ink">{{ __('Enrollment offer') }}</p>
					<p class="mt-1 type-caption text-ink/65">
						{{ enrollmentOffer.status || __('Pending') }}
					</p>
				</div>
				<p v-if="enrollmentOffer.offer_expires_on" class="type-caption text-ink/60">
					{{ __('Respond by {0}').replace('{0}', formatDate(enrollmentOffer.offer_expires_on)) }}
				</p>
			</div>

			<div class="mt-3 grid gap-3 sm:grid-cols-2">
				<div class="rounded-xl border border-border/60 bg-surface/40 px-3 py-2">
					<p class="type-caption text-ink/60">{{ __('Program Offering') }}</p>
					<p class="type-body text-ink">{{ enrollmentOffer.program_offering || __('—') }}</p>
				</div>
				<div class="rounded-xl border border-border/60 bg-surface/40 px-3 py-2">
					<p class="type-caption text-ink/60">{{ __('Academic Year') }}</p>
					<p class="type-body text-ink">{{ enrollmentOffer.academic_year || __('—') }}</p>
				</div>
			</div>

			<p
				v-if="enrollmentOffer.offer_message"
				class="mt-3 type-caption text-ink/75 whitespace-pre-wrap"
			>
				{{ enrollmentOffer.offer_message }}
			</p>

			<div
				v-if="enrollmentOffer.course_choices_available"
				class="mt-3 rounded-xl border border-border/60 bg-surface/40 px-3 py-3"
			>
				<div class="flex flex-wrap items-center justify-between gap-3">
					<div>
						<p class="type-body text-ink">{{ __('Course choices') }}</p>
						<p
							class="mt-1 type-caption whitespace-pre-wrap"
							:class="needsCourseChoices ? 'text-amber-800' : 'text-ink/60'"
						>
							{{
								needsCourseChoices
									? courseChoiceBlockingReason
									: __('Your saved course choices are ready.')
							}}
						</p>
					</div>
					<RouterLink
						:to="{ name: 'admissions-course-choices' }"
						class="rounded-full border border-border/70 bg-white px-4 py-2 type-caption text-ink/75"
					>
						{{ needsCourseChoices ? __('Open course choices') : __('View course choices') }}
					</RouterLink>
				</div>
			</div>

			<div
				v-if="enrollmentOffer.can_accept || enrollmentOffer.can_decline"
				class="mt-4 flex flex-wrap gap-3"
			>
				<button
					v-if="enrollmentOffer.can_accept"
					type="button"
					class="rounded-full bg-canopy px-4 py-2 type-caption text-white disabled:opacity-60"
					:disabled="acceptOfferDisabled"
					@click="acceptOffer"
				>
					{{ offerLoading ? __('Working…') : __('Accept Offer') }}
				</button>
				<button
					v-if="enrollmentOffer.can_decline"
					type="button"
					class="rounded-full border border-rose-200 bg-white px-4 py-2 type-caption text-rose-900 disabled:opacity-60"
					:disabled="offerLoading"
					@click="declineOffer"
				>
					{{ offerLoading ? __('Working…') : __('Decline Offer') }}
				</button>
			</div>

			<p v-if="offerError" class="mt-3 type-caption text-rose-800 whitespace-pre-wrap">
				{{ offerError }}
			</p>
		</div>

		<div v-if="loading" class="rounded-2xl border border-border/70 bg-surface px-4 py-4">
			<p class="type-caption text-ink/65">{{ __('Loading recommendation status…') }}</p>
		</div>

		<div v-else-if="error" class="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3">
			<p class="type-body-strong text-rose-900">
				{{ __('Unable to load recommendation status') }}
			</p>
			<p class="mt-1 type-caption text-rose-900/80 whitespace-pre-wrap">{{ error }}</p>
			<button
				type="button"
				class="mt-3 rounded-full border border-rose-200 bg-white px-4 py-2 type-caption text-rose-900"
				@click="loadSnapshot"
			>
				{{ __('Try again') }}
			</button>
		</div>

		<div v-else class="rounded-2xl border border-border/70 bg-white px-4 py-4 shadow-soft">
			<p class="type-body-strong text-ink">{{ __('Recommendations') }}</p>
			<p class="mt-1 type-caption text-ink/65">{{ recommendationSummaryLine }}</p>
			<p class="mt-2 type-caption text-ink/55">
				{{
					__(
						'Your school contacts referees directly. You can track whether recommendations were received here, but you cannot open the submission or any attached file.'
					)
				}}
			</p>

			<div v-if="recommendationRows.length" class="mt-3 space-y-2">
				<div
					v-for="row in recommendationRows"
					:key="row.recommendation_template"
					class="rounded-xl border border-border/60 bg-surface/40 px-3 py-2"
				>
					<p class="type-body text-ink">{{ row.template_name }}</p>
					<p class="type-caption text-ink/60">
						{{
							__('Received {0} of required {1}')
								.replace('{0}', String(row.submitted_count))
								.replace('{1}', String(row.minimum_required))
						}}
					</p>
				</div>
			</div>

			<p v-if="missingTemplates.length" class="mt-3 type-caption text-amber-800">
				{{ __('Still pending: {0}').replace('{0}', missingTemplates.join(', ')) }}
			</p>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { RouterLink } from 'vue-router';

import { useAdmissionsSession } from '@/composables/useAdmissionsSession';
import { createAdmissionsService } from '@/lib/services/admissions/admissionsService';
import { __ } from '@/lib/i18n';
import { uiSignals, SIGNAL_ADMISSIONS_PORTAL_INVALIDATE } from '@/lib/uiSignals';
import type { Response as ApplicantSnapshot } from '@/types/contracts/admissions/get_applicant_snapshot';

const { session, refresh } = useAdmissionsSession();
const service = createAdmissionsService();
const snapshot = ref<ApplicantSnapshot | null>(null);
const loading = ref(false);
const error = ref<string | null>(null);
const offerLoading = ref(false);
const offerError = ref<string | null>(null);

const portalStatus = computed(() => session.value?.applicant?.portal_status || '');
const readOnlyReason = computed(() => session.value?.applicant?.read_only_reason || '');
const enrollmentOffer = computed(
	() => snapshot.value?.enrollment_offer || session.value?.enrollment_offer || null
);
const needsCourseChoices = computed(
	() =>
		Boolean(enrollmentOffer.value?.course_choices_available) &&
		!Boolean(enrollmentOffer.value?.course_choices_ready)
);
const courseChoiceBlockingReason = computed(() => {
	const reasons = enrollmentOffer.value?.course_choice_blocking_reasons || [];
	return reasons[0] || __('Complete your course choices before accepting the offer.');
});
const acceptOfferDisabled = computed(() => offerLoading.value || needsCourseChoices.value);

const recommendationSummaryLine = computed(() => {
	const summary = snapshot.value?.recommendations_summary;
	if (!summary) return __('No recommendation requirements are configured.');
	const required = Number(summary.required_total || 0);
	const received = Number(summary.received_total || 0);
	if (required <= 0) return __('No recommendation requirements are configured.');
	return __('Received {0} of required {1}')
		.replace('{0}', String(received))
		.replace('{1}', String(required));
});

const recommendationRows = computed(() => snapshot.value?.recommendations_summary?.rows || []);
const missingTemplates = computed(() => snapshot.value?.recommendations_summary?.missing || []);

async function loadSnapshot() {
	loading.value = true;
	error.value = null;
	try {
		snapshot.value = await service.getSnapshot();
	} catch (err) {
		error.value = err instanceof Error ? err.message : __('Unable to load recommendation status.');
	} finally {
		loading.value = false;
	}
}

function formatDate(value?: string | null) {
	if (!value) return '—';
	const date = new Date(value);
	if (Number.isNaN(date.getTime())) return value;
	return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(date);
}

async function acceptOffer() {
	if (needsCourseChoices.value) {
		offerError.value = courseChoiceBlockingReason.value;
		return;
	}
	offerLoading.value = true;
	offerError.value = null;
	try {
		await service.acceptEnrollmentOffer();
		await Promise.all([refresh(), loadSnapshot()]);
	} catch (err) {
		offerError.value = err instanceof Error ? err.message : __('Unable to accept the offer.');
	} finally {
		offerLoading.value = false;
	}
}

async function declineOffer() {
	offerLoading.value = true;
	offerError.value = null;
	try {
		await service.declineEnrollmentOffer();
		await Promise.all([refresh(), loadSnapshot()]);
	} catch (err) {
		offerError.value = err instanceof Error ? err.message : __('Unable to decline the offer.');
	} finally {
		offerLoading.value = false;
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
