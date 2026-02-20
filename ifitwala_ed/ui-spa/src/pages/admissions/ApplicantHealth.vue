<!-- ifitwala_ed/ui-spa/src/pages/admissions/ApplicantHealth.vue -->

<template>
	<div class="space-y-6">
		<div class="flex flex-wrap items-start justify-between gap-4">
			<div>
				<p class="type-h2 text-ink">{{ __('Health information') }}</p>
				<p class="mt-1 type-caption text-ink/60">
					{{ __('Share any medical details or accommodations needed.') }}
				</p>
			</div>
			<button
				type="button"
				class="rounded-full bg-ink px-4 py-2 type-caption text-white shadow-soft disabled:opacity-50"
				:disabled="isReadOnly || loading"
				@click="openEdit"
			>
				{{ __('Edit') }}
			</button>
		</div>

		<div v-if="loading" class="rounded-2xl border border-border/70 bg-surface px-4 py-4">
			<div class="flex items-center gap-3">
				<Spinner class="h-4 w-4" />
				<p class="type-body-strong text-ink">{{ __('Loading health details…') }}</p>
			</div>
		</div>

		<div v-else-if="error" class="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3">
			<p class="type-body-strong text-rose-900">{{ __('Unable to load health information') }}</p>
			<p class="mt-1 type-caption text-rose-900/80 whitespace-pre-wrap">{{ error }}</p>
			<button
				type="button"
				class="mt-3 rounded-full border border-rose-200 bg-white px-4 py-2 type-caption text-rose-900"
				@click="loadHealth"
			>
				{{ __('Try again') }}
			</button>
		</div>

		<div v-else class="grid gap-4">
			<div v-if="actionError" class="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3">
				<p class="type-body-strong text-amber-900">{{ __('Notice') }}</p>
				<p class="mt-1 type-caption text-amber-900/80">{{ actionError }}</p>
			</div>
			<div class="rounded-2xl border border-border/70 bg-white px-4 py-4 shadow-soft">
				<p class="type-body-strong text-ink">{{ __('Health summary') }}</p>
				<p class="mt-2 type-body text-ink/70 whitespace-pre-wrap">
					{{ health?.health_summary || __('No summary provided.') }}
				</p>
			</div>

			<div class="rounded-2xl border border-border/70 bg-white px-4 py-4 shadow-soft">
				<p class="type-body-strong text-ink">{{ __('Medical conditions') }}</p>
				<p class="mt-2 type-body text-ink/70 whitespace-pre-wrap">
					{{ health?.medical_conditions || __('No conditions listed.') }}
				</p>
			</div>

			<div class="rounded-2xl border border-border/70 bg-white px-4 py-4 shadow-soft">
				<p class="type-body-strong text-ink">{{ __('Allergies') }}</p>
				<p class="mt-2 type-body text-ink/70 whitespace-pre-wrap">
					{{ health?.allergies || __('No allergies listed.') }}
				</p>
			</div>

			<div class="rounded-2xl border border-border/70 bg-white px-4 py-4 shadow-soft">
				<p class="type-body-strong text-ink">{{ __('Medications') }}</p>
				<p class="mt-2 type-body text-ink/70 whitespace-pre-wrap">
					{{ health?.medications || __('No medications listed.') }}
				</p>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { Spinner } from 'frappe-ui';

import { createAdmissionsService } from '@/lib/services/admissions/admissionsService';
import { useOverlayStack } from '@/composables/useOverlayStack';
import { useAdmissionsSession } from '@/composables/useAdmissionsSession';
import { __ } from '@/lib/i18n';
import { uiSignals, SIGNAL_ADMISSIONS_PORTAL_INVALIDATE } from '@/lib/uiSignals';
import type { Response as HealthResponse } from '@/types/contracts/admissions/get_applicant_health';

const service = createAdmissionsService();
const overlay = useOverlayStack();
const { session } = useAdmissionsSession();

const health = ref<HealthResponse | null>(null);
const loading = ref(false);
const error = ref<string | null>(null);
const actionError = ref('');

const isReadOnly = computed(() => Boolean(session.value?.applicant?.is_read_only));

async function loadHealth() {
	loading.value = true;
	error.value = null;
	actionError.value = '';
	try {
		health.value = await service.getHealth();
	} catch (err) {
		const message = err instanceof Error ? err.message : __('Unable to load health information.');
		error.value = message;
	} finally {
		loading.value = false;
	}
}

function openEdit() {
	if (isReadOnly.value) {
		actionError.value = __('This application is read-only.');
		return;
	}
	actionError.value = '';
	overlay.open('admissions-health', {
		initial: health.value || {
			health_summary: '',
			medical_conditions: '',
			allergies: '',
			medications: '',
		},
		readOnly: isReadOnly.value,
	});
}

let unsubscribe: (() => void) | null = null;

onMounted(async () => {
	await loadHealth();
	unsubscribe = uiSignals.subscribe(SIGNAL_ADMISSIONS_PORTAL_INVALIDATE, () => {
		loadHealth();
	});
});

onBeforeUnmount(() => {
	if (unsubscribe) unsubscribe();
});
</script>
