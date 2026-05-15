<template>
	<div
		class="rounded-2xl border border-sky/25 bg-sky/10 px-4 py-3"
		role="status"
		aria-live="polite"
	>
		<div class="flex items-start justify-between gap-3">
			<div class="min-w-0">
				<p class="type-body-strong text-ink">{{ label }}</p>
				<p class="mt-1 type-caption text-ink/70">
					{{ detailText }}
				</p>
			</div>
			<span v-if="badgeText" class="type-caption text-ink/55">{{ badgeText }}</span>
		</div>

		<div class="mt-3 h-2 overflow-hidden rounded-full bg-sky/15">
			<div
				v-if="showIndeterminate"
				class="if-inline-upload-status__indeterminate h-full rounded-full bg-jacaranda/80"
			/>
			<div
				v-else
				class="h-full rounded-full bg-jacaranda transition-[width] duration-200 ease-out"
				:style="{ width: `${progressWidth}%` }"
			/>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

import type { UploadProgressState } from '@/lib/uploadProgress';

const props = defineProps<{
	label: string;
	progress: UploadProgressState;
}>();

const showIndeterminate = computed(
	() => props.progress.phase !== 'processing' && props.progress.percent === null
);

const progressWidth = computed(() => {
	if (props.progress.phase === 'processing') {
		return 100;
	}
	if (typeof props.progress.percent === 'number') {
		return Math.max(0, Math.min(100, props.progress.percent));
	}
	return 36;
});

const badgeText = computed(() => {
	if (props.progress.phase === 'processing') {
		return 'Finishing...';
	}
	if (typeof props.progress.percent === 'number') {
		return `${props.progress.percent}%`;
	}
	return '';
});

const detailText = computed(() => {
	if (props.progress.phase === 'preparing') {
		return 'Preparing the file in your browser before upload.';
	}
	if (props.progress.phase === 'processing') {
		return 'Upload complete. Finalizing on the server now.';
	}
	return 'Uploading to the server now.';
});
</script>

<style scoped>
.if-inline-upload-status__indeterminate {
	width: 38%;
	animation: inline-upload-progress 1.15s ease-in-out infinite;
}

@keyframes inline-upload-progress {
	0% {
		transform: translateX(-120%);
	}

	100% {
		transform: translateX(260%);
	}
}
</style>
