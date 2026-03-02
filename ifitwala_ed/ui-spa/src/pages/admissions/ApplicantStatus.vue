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
			<p class="type-body-strong text-ink">{{ __('Recommendation letters') }}</p>
			<p class="mt-1 type-caption text-ink/65">{{ recommendationSummaryLine }}</p>

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

import { useAdmissionsSession } from '@/composables/useAdmissionsSession';
import { createAdmissionsService } from '@/lib/services/admissions/admissionsService';
import { __ } from '@/lib/i18n';
import { uiSignals, SIGNAL_ADMISSIONS_PORTAL_INVALIDATE } from '@/lib/uiSignals';
import type { Response as ApplicantSnapshot } from '@/types/contracts/admissions/get_applicant_snapshot';

const { session } = useAdmissionsSession();
const service = createAdmissionsService();
const snapshot = ref<ApplicantSnapshot | null>(null);
const loading = ref(false);
const error = ref<string | null>(null);

const portalStatus = computed(() => session.value?.applicant?.portal_status || '');
const readOnlyReason = computed(() => session.value?.applicant?.read_only_reason || '');

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
