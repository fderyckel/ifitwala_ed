<template>
	<div class="rounded-2xl border border-line-soft bg-surface-soft p-4">
		<div v-if="showInlineImagePreview" class="mb-4">
			<a
				:href="primaryResourceUrl || undefined"
				target="_blank"
				rel="noreferrer"
				class="group block overflow-hidden rounded-2xl border border-line-soft bg-white"
				data-learning-resource-kind="image"
			>
				<img
					:src="primaryResourceUrl || undefined"
					:alt="resource.title"
					class="h-40 w-full object-cover transition duration-200 group-hover:scale-[1.01]"
					loading="lazy"
				/>
				<div
					class="flex items-center justify-between border-t border-line-soft bg-white px-4 py-3"
				>
					<div>
						<p class="text-xs font-semibold uppercase tracking-[0.18em] text-ink/45">
							Image preview
						</p>
						<p class="mt-1 text-sm text-ink/80">
							Open the guided preview without leaving this learning space.
						</p>
					</div>
					<span class="chip">{{ resourceExtensionLabel }}</span>
				</div>
			</a>
		</div>

		<div v-else-if="showPdfPreviewTile" class="mb-4">
			<a
				:href="primaryResourceUrl || undefined"
				target="_blank"
				rel="noreferrer"
				class="group block rounded-2xl border border-line-soft bg-white p-4 transition hover:border-jacaranda/30 hover:bg-jacaranda/5"
				data-learning-resource-kind="pdf"
			>
				<div class="flex items-start justify-between gap-3">
					<div>
						<p class="text-xs font-semibold uppercase tracking-[0.18em] text-ink/45">
							PDF preview
						</p>
						<p class="mt-2 text-base font-semibold text-ink">
							{{ resource.title }}
						</p>
						<p class="mt-2 text-sm text-ink/75">
							Open a compact preview for this guided resource.
						</p>
					</div>
					<div class="rounded-2xl bg-clay/15 px-3 py-2 text-right">
						<p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-clay">
							{{ resourceExtensionLabel }}
						</p>
						<p class="mt-1 text-xs text-ink/60">Preview ready</p>
					</div>
				</div>
			</a>
		</div>

		<div class="min-w-0">
			<div class="flex flex-wrap items-center gap-2">
				<p class="type-body-strong text-ink">{{ resource.title }}</p>
				<span v-if="resource.usage_role" class="chip">{{ resource.usage_role }}</span>
				<span v-if="resource.material_type" class="chip">{{ resource.material_type }}</span>
			</div>
			<p v-if="resource.description" class="mt-2 type-caption text-ink/70">
				{{ resource.description }}
			</p>
			<p v-if="resource.placement_note" class="mt-2 type-caption text-ink/60">
				{{ resource.placement_note }}
			</p>
			<p v-if="resource.file_name || resource.reference_url" class="mt-2 type-caption text-ink/60">
				{{ resource.file_name || resource.reference_url }}
			</p>
		</div>

		<div class="mt-3 flex flex-wrap gap-2">
			<a
				v-if="primaryResourceUrl"
				:href="primaryResourceUrl"
				target="_blank"
				rel="noreferrer"
				class="if-action"
			>
				{{ primaryActionLabel }}
			</a>
			<a
				v-if="showOpenOriginalAction"
				:href="resource.open_url || undefined"
				target="_blank"
				rel="noreferrer"
				class="if-action"
			>
				Open original
			</a>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

import type { StudentLearningMaterial } from '@/types/contracts/student_learning/get_student_learning_space';

const props = defineProps<{
	resource: StudentLearningMaterial;
}>();

const primaryResourceUrl = computed(
	() => props.resource.preview_url || props.resource.open_url || null
);
const primaryActionLabel = computed(() => (props.resource.preview_url ? 'Preview' : 'Open'));
const showOpenOriginalAction = computed(() =>
	Boolean(
		props.resource.preview_url &&
		props.resource.open_url &&
		props.resource.open_url !== props.resource.preview_url
	)
);

const resourceExtension = computed(() => {
	const rawName = String(props.resource.file_name || '').trim();
	const lastDot = rawName.lastIndexOf('.');
	if (!rawName || lastDot < 0 || lastDot === rawName.length - 1) {
		return '';
	}
	return rawName.slice(lastDot + 1).toLowerCase();
});

const resourceExtensionLabel = computed(() => {
	return resourceExtension.value ? resourceExtension.value.toUpperCase() : 'FILE';
});

const showInlineImagePreview = computed(() => {
	return Boolean(
		primaryResourceUrl.value && ['jpg', 'jpeg', 'png', 'webp'].includes(resourceExtension.value)
	);
});

const showPdfPreviewTile = computed(() => {
	return Boolean(primaryResourceUrl.value && resourceExtension.value === 'pdf');
});
</script>
