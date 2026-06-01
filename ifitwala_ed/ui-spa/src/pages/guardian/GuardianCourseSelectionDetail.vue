<!-- ifitwala_ed/ui-spa/src/pages/guardian/GuardianCourseSelectionDetail.vue -->
<template>
	<SelfEnrollmentEditor
		:payload="payload"
		:loading="loading"
		:saving="saving"
		:submitting="submitting"
		:error-message="errorMessage"
		:back-to="{ name: 'guardian-course-selection' }"
		back-label="Back to Family Board"
		overline="Guardian Course Selection"
		@refresh="loadDetail"
		@save="saveDraft"
		@submit="submitSelection"
	/>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { toast } from 'frappe-ui';
import { useRoute } from 'vue-router';

import SelfEnrollmentEditor from '@/components/self_enrollment/SelfEnrollmentEditor.vue';
import { __ } from '@/lib/i18n';
import {
	getSelfEnrollmentChoiceState,
	saveSelfEnrollmentChoices,
	submitSelfEnrollmentChoices,
} from '@/lib/services/selfEnrollment/selfEnrollmentService';
import type { Response as ChoiceStateResponse } from '@/types/contracts/self_enrollment/get_self_enrollment_choice_state';
import type { Request as SaveChoicesRequest } from '@/types/contracts/self_enrollment/save_self_enrollment_choices';

type SelfEnrollmentSubmitPayload = Pick<SaveChoicesRequest, 'courses' | 'enrollment_intent'>;

const route = useRoute();
const loading = ref<boolean>(true);
const saving = ref<boolean>(false);
const submitting = ref<boolean>(false);
const errorMessage = ref<string>('');
const payload = ref<ChoiceStateResponse | null>(null);

const selectionWindow = String(route.params.selection_window || '');
const studentId = String(route.params.student_id || '');

async function loadDetail() {
	loading.value = true;
	errorMessage.value = '';
	try {
		payload.value = await getSelfEnrollmentChoiceState({
			selection_window: selectionWindow,
			student: studentId,
		});
	} catch (error) {
		errorMessage.value =
			error instanceof Error ? error.message : 'Unable to load course selection.';
	} finally {
		loading.value = false;
	}
}

async function saveDraft(submitPayload: SelfEnrollmentSubmitPayload) {
	saving.value = true;
	try {
		payload.value = await saveSelfEnrollmentChoices({
			selection_window: selectionWindow,
			student: studentId,
			courses: submitPayload.courses,
			enrollment_intent: submitPayload.enrollment_intent,
		});
		toast.success('Course selection draft saved.');
	} catch (error) {
		toast.error(error instanceof Error ? error.message : 'Could not save course selection.');
	} finally {
		saving.value = false;
	}
}

async function submitSelection(submitPayload: SelfEnrollmentSubmitPayload) {
	submitting.value = true;
	try {
		payload.value = await submitSelfEnrollmentChoices({
			selection_window: selectionWindow,
			student: studentId,
			courses: submitPayload.courses,
			enrollment_intent: submitPayload.enrollment_intent,
		});
		toast.success('Course selection response submitted.');
	} catch (error) {
		toast.error(error instanceof Error ? error.message : __('Unable to submit course selection.'));
	} finally {
		submitting.value = false;
	}
}

onMounted(() => {
	void loadDetail();
});
</script>
