<template>
	<div class="portal-page student-hub-page">
		<div>
			<RouterLink
				:to="backRoute"
				class="inline-flex items-center gap-2 type-body text-ink/70 transition hover:text-ink"
			>
				<span>←</span>
				<span>Back to Monitoring</span>
			</RouterLink>
		</div>

		<section v-if="errorMessage" class="if-banner if-banner--danger">
			<p class="if-banner__title type-body-strong text-flame">Could not load released feedback.</p>
			<p class="if-banner__body mt-2 type-caption">{{ errorMessage }}</p>
		</section>

		<section v-else-if="loading" class="student-hub-section">
			<p class="type-body text-ink/70">Loading released feedback...</p>
		</section>

		<ReleasedFeedbackNavigator v-else-if="detail" :detail="detail" mode="guardian" />
	</div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { RouterLink } from 'vue-router';

import ReleasedFeedbackNavigator from '@/components/assessment/ReleasedFeedbackNavigator.vue';
import { getGuardianReleasedFeedbackDetail } from '@/lib/services/assessment/releasedFeedbackService';
import type { ReleasedFeedbackDetail } from '@/types/contracts/assessment/released_feedback_detail';

const props = defineProps<{
	student_id: string;
	task_outcome: string;
}>();

const loading = ref(false);
const errorMessage = ref('');
const detail = ref<ReleasedFeedbackDetail | null>(null);

const backRoute = computed(() => ({
	name: 'guardian-monitoring',
}));

async function loadDetail() {
	loading.value = true;
	errorMessage.value = '';
	try {
		detail.value = await getGuardianReleasedFeedbackDetail({ outcome_id: props.task_outcome });
	} catch (error: unknown) {
		detail.value = null;
		errorMessage.value = error instanceof Error && error.message ? error.message : 'Unknown error';
	} finally {
		loading.value = false;
	}
}

watch(
	() => props.task_outcome,
	() => {
		void loadDetail();
	},
	{ immediate: true }
);
</script>
