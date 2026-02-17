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
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

import { useAdmissionsSession } from '@/composables/useAdmissionsSession';

const { session } = useAdmissionsSession();

const portalStatus = computed(() => session.value?.applicant?.portal_status || '');
const readOnlyReason = computed(() => session.value?.applicant?.read_only_reason || '');
</script>
