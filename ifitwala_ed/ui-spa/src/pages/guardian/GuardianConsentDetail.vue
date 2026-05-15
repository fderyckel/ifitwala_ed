<template>
	<ConsentDetailView
		portal-label="Guardian Portal"
		title-label="Form detail"
		back-route-name="guardian-consents"
		:request-key="requestKey"
		:student-id="studentId"
		:load-detail="getGuardianConsentDetail"
		:submit-decision="submitGuardianConsentDecision"
	/>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRoute } from 'vue-router';

import ConsentDetailView from '@/components/family_consent/ConsentDetailView.vue';
import {
	getGuardianConsentDetail,
	submitGuardianConsentDecision,
} from '@/lib/services/guardianConsent/guardianConsentService';

const route = useRoute();
const requestKey = computed(() => String(route.params.request_key || '').trim());
const studentId = computed(() => String(route.params.student_id || '').trim());
</script>
