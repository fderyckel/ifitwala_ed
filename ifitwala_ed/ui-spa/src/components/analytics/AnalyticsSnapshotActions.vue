<!-- ifitwala_ed/ui-spa/src/components/analytics/AnalyticsSnapshotActions.vue -->
<template>
	<div class="analytics-export-actions">
		<button
			type="button"
			class="analytics-export-button"
			:disabled="disabled || busy"
			@click="emit('export-png')"
		>
			{{ exportingPng ? 'Exporting PNG...' : 'Export PNG' }}
		</button>
		<button
			type="button"
			class="analytics-export-button analytics-export-button--secondary"
			:disabled="disabled || busy"
			@click="emit('export-pdf')"
		>
			{{ exportingPdf ? 'Exporting PDF...' : 'Export PDF' }}
		</button>
		<p v-if="message" class="analytics-export-message">
			{{ message }}
		</p>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = withDefaults(
	defineProps<{
		exportingPng?: boolean;
		exportingPdf?: boolean;
		disabled?: boolean;
		message?: string | null;
	}>(),
	{
		exportingPng: false,
		exportingPdf: false,
		disabled: false,
		message: null,
	}
);

const emit = defineEmits<{
	(e: 'export-png'): void;
	(e: 'export-pdf'): void;
}>();

const busy = computed(() => Boolean(props.exportingPng || props.exportingPdf));
</script>
