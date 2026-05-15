<template>
	<div class="rounded-2xl border border-line-soft bg-surface-soft p-4">
		<AttachmentPreviewCard
			v-if="resource.attachment_preview"
			:attachment="resource.attachment_preview"
			variant="learning"
			:title="resource.title"
			:description="resource.description || null"
			:meta-text="resourceMetaLine"
			:chips="resourceChips"
		/>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

import AttachmentPreviewCard from '@/components/attachments/AttachmentPreviewCard.vue';
import type { StudentLearningMaterial } from '@/types/contracts/student_learning/get_student_learning_space';

const props = defineProps<{
	resource: StudentLearningMaterial;
}>();

const resourceMetaLine = computed(() => {
	return (
		[props.resource.placement_note, props.resource.file_name || props.resource.reference_url]
			.filter(Boolean)
			.join(' · ') || null
	);
});
const resourceChips = computed(
	() =>
		[props.resource.usage_role || null, props.resource.material_type || null].filter(
			Boolean
		) as string[]
);
</script>
