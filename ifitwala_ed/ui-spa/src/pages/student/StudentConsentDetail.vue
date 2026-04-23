<template>
	<ConsentDetailView
		portal-label="Student Hub"
		title-label="Form detail"
		back-route-name="student-consents"
		:request-key="requestKey"
		:student-id="studentId"
		:load-detail="getStudentConsentDetail"
		:submit-decision="submitStudentConsentDecision"
	/>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRoute } from 'vue-router';

import ConsentDetailView from '@/components/family_consent/ConsentDetailView.vue';
import {
	getStudentConsentDetail,
	submitStudentConsentDecision,
} from '@/lib/services/studentConsent/studentConsentService';

const route = useRoute();
const requestKey = computed(() => String(route.params.request_key || '').trim());
const studentId = computed(() => String(route.params.student_id || '').trim());
</script>
