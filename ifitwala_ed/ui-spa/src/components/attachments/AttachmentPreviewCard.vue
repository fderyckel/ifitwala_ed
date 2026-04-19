<template>
	<div class="space-y-3">
		<div v-if="showInlineImagePreview" class="mb-1">
			<a
				:href="primaryActionUrl || undefined"
				target="_blank"
				rel="noreferrer"
				class="group block overflow-hidden rounded-2xl border border-line-soft bg-white"
				v-bind="kindDataAttrs('image')"
			>
				<img
					:src="inlineImageUrl || undefined"
					:alt="titleToUse"
					:class="imagePreviewClass"
					loading="lazy"
					@error="handleImagePreviewError"
				/>
				<div
					class="flex items-center justify-between border-t border-line-soft bg-white px-4 py-3"
				>
					<div>
						<p class="text-xs font-semibold uppercase tracking-[0.18em] text-ink/45">
							Image preview
						</p>
						<p class="mt-1 text-sm text-ink/80">
							{{ imagePreviewBody }}
						</p>
					</div>
					<span class="chip">{{ extensionLabel }}</span>
				</div>
			</a>
		</div>

		<div v-else-if="showPdfPreviewSurface" class="mb-1">
			<div
				v-if="variant === 'communication'"
				v-bind="kindDataAttrs('pdf')"
				class="overflow-hidden rounded-2xl border border-line-soft bg-white"
			>
				<div class="flex items-start justify-between gap-3 border-b border-line-soft px-4 py-4">
					<div>
						<p class="text-xs font-semibold uppercase tracking-[0.18em] text-ink/45">
							PDF preview
						</p>
						<p class="mt-2 text-base font-semibold text-ink">
							{{ titleToUse }}
						</p>
						<p class="mt-2 text-sm text-ink/75">
							{{ communicationPdfMessage }}
						</p>
					</div>
					<div class="rounded-2xl bg-clay/15 px-3 py-2 text-right">
						<p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-clay">
							{{ extensionLabel }}
						</p>
						<p class="mt-1 text-xs text-ink/60">
							{{ showCommunicationPdfPreview ? 'First page ready' : 'Open original' }}
						</p>
					</div>
				</div>
				<div v-if="showCommunicationPdfPreview" class="bg-surface-soft/60 p-3">
					<img
						:src="attachment.preview_url || undefined"
						:alt="`${titleToUse} first page preview`"
						class="h-80 w-full rounded-xl bg-white object-contain"
						loading="lazy"
					/>
				</div>
				<div
					v-else
					class="flex min-h-56 items-center justify-center bg-surface-soft/60 px-6 py-10 text-center"
				>
					<div>
						<p class="text-sm font-semibold uppercase tracking-[0.18em] text-ink/45">
							PDF attachment
						</p>
						<p class="mt-3 text-base font-semibold text-ink">Preview not available yet</p>
						<p class="mt-2 text-sm text-ink/70">
							{{ communicationPdfFallbackMessage }}
						</p>
					</div>
				</div>
			</div>

			<a
				v-else
				:href="primaryActionUrl || undefined"
				target="_blank"
				rel="noreferrer"
				class="group block rounded-2xl border border-line-soft bg-white p-4 transition hover:border-jacaranda/30 hover:bg-jacaranda/5"
				v-bind="kindDataAttrs('pdf')"
			>
				<div class="flex items-start justify-between gap-3">
					<div>
						<p class="text-xs font-semibold uppercase tracking-[0.18em] text-ink/45">
							PDF preview
						</p>
						<p class="mt-2 text-base font-semibold text-ink">
							{{ titleToUse }}
						</p>
						<p class="mt-2 text-sm text-ink/75">
							{{ compactPdfBody }}
						</p>
					</div>
					<div class="rounded-2xl bg-clay/15 px-3 py-2 text-right">
						<p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-clay">
							{{ extensionLabel }}
						</p>
						<p class="mt-1 text-xs text-ink/60">Preview ready</p>
					</div>
				</div>
			</a>
		</div>

		<div class="min-w-0">
			<div class="flex flex-wrap items-center gap-2">
				<p class="type-body-strong text-ink">{{ titleToUse }}</p>
				<span v-for="chip in normalizedChips" :key="chip" class="chip">
					{{ chip }}
				</span>
				<slot name="badges" />
			</div>
			<p v-if="descriptionToUse" class="mt-2 type-caption text-ink/70">
				{{ descriptionToUse }}
			</p>
			<p v-if="metaTextToUse" class="mt-2 type-caption text-ink/60">
				{{ metaTextToUse }}
			</p>
		</div>

		<div v-if="hasActionRow" class="mt-3 flex flex-wrap gap-2">
			<a
				v-if="primaryActionUrl"
				:href="primaryActionUrl || undefined"
				target="_blank"
				rel="noreferrer"
				:class="actionClass"
			>
				{{ primaryActionLabel }}
			</a>
			<a
				v-if="showSecondaryPreviewAction"
				:href="attachment.preview_url || undefined"
				target="_blank"
				rel="noreferrer"
				:class="actionClass"
			>
				Open preview image
			</a>
			<a
				v-if="showOpenOriginalAction"
				:href="attachment.open_url || undefined"
				target="_blank"
				rel="noreferrer"
				:class="actionClass"
			>
				{{ openOriginalLabel }}
			</a>
			<slot name="extra-actions" />
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, ref, useSlots, watch } from 'vue';

import type { AttachmentPreviewItem } from '@/types/contracts/attachments/shared';

type AttachmentPreviewCardVariant = 'communication' | 'planning' | 'learning' | 'evidence';

const props = withDefaults(
	defineProps<{
		attachment: AttachmentPreviewItem;
		variant?: AttachmentPreviewCardVariant;
		title?: string | null;
		description?: string | null;
		metaText?: string | null;
		chips?: string[];
		enablePreviewSurface?: boolean;
	}>(),
	{
		variant: 'planning',
		chips: () => [],
		enablePreviewSurface: true,
	}
);

const slots = useSlots();
const imagePreviewFailed = ref(false);
const imagePreviewUsesFallbackUrl = ref(false);

const titleToUse = computed(() => {
	const explicitTitle = String(props.title || '').trim();
	return explicitTitle || props.attachment.display_name || 'Attachment';
});
const descriptionToUse = computed(() => {
	const explicitDescription = String(props.description || '').trim();
	return explicitDescription || props.attachment.description || null;
});
const metaTextToUse = computed(() => {
	const explicitMeta = String(props.metaText || '').trim();
	if (explicitMeta) return explicitMeta;
	return props.attachment.kind === 'link' ? props.attachment.link_url || null : null;
});
const normalizedChips = computed(() =>
	(props.chips || []).map(chip => String(chip || '').trim()).filter(Boolean)
);
const mediaPreviewEnabled = computed(
	() => props.enablePreviewSurface && props.variant !== 'evidence'
);
const extensionLabel = computed(() => {
	const extension = String(props.attachment.extension || '')
		.trim()
		.toUpperCase();
	return extension || 'FILE';
});
const imagePreviewClass = computed(() =>
	props.variant === 'planning'
		? 'h-44 w-full object-cover transition duration-200 group-hover:scale-[1.01]'
		: 'h-40 w-full object-cover transition duration-200 group-hover:scale-[1.01]'
);
const imagePreviewBody = computed(() => {
	if (props.variant === 'communication') {
		return 'Open the governed preview from this communication.';
	}
	if (props.variant === 'learning') {
		return 'Open the guided preview without leaving this learning space.';
	}
	return 'Open the governed preview without losing planning context.';
});
const compactPdfBody = computed(() => {
	if (props.variant === 'learning') {
		return 'Open a compact preview for this guided resource.';
	}
	return 'Open a compact governed preview for this PDF attachment.';
});
const inlineImageUrl = computed(() => {
	if (props.attachment.kind !== 'image') return null;
	if (imagePreviewUsesFallbackUrl.value && props.attachment.preview_url) {
		return props.attachment.preview_url;
	}
	if (props.attachment.thumbnail_url) {
		return props.attachment.thumbnail_url;
	}
	if (
		props.variant === 'communication' &&
		props.attachment.preview_status === 'ready' &&
		props.attachment.preview_url
	) {
		return props.attachment.preview_url;
	}
	return null;
});
const canRetryInlineImageWithPreview = computed(() => {
	return Boolean(
		props.attachment.kind === 'image' &&
		props.attachment.thumbnail_url &&
		props.attachment.preview_url &&
		props.attachment.preview_url !== props.attachment.thumbnail_url
	);
});
const showInlineImagePreview = computed(() => {
	return Boolean(mediaPreviewEnabled.value && inlineImageUrl.value && !imagePreviewFailed.value);
});
const previewStatusAllowsPdf = computed(() => {
	if (!props.attachment.preview_url) return false;
	if (props.attachment.preview_status && props.attachment.preview_status !== 'ready') {
		return false;
	}
	return true;
});
const showCommunicationPdfPreview = computed(() => {
	return Boolean(
		props.variant === 'communication' &&
		mediaPreviewEnabled.value &&
		props.attachment.kind === 'pdf' &&
		props.attachment.preview_url &&
		props.attachment.preview_status === 'ready'
	);
});
const showPdfPreviewSurface = computed(() => {
	if (!mediaPreviewEnabled.value || props.attachment.kind !== 'pdf') return false;
	if (props.variant === 'communication') return true;
	return previewStatusAllowsPdf.value;
});
const primaryActionUrl = computed(() => {
	if (props.variant === 'communication' && props.attachment.kind === 'pdf') {
		return props.attachment.open_url || props.attachment.preview_url || null;
	}
	return (
		props.attachment.preview_url || props.attachment.open_url || props.attachment.link_url || null
	);
});
const primaryActionLabel = computed(() => {
	if (
		props.variant === 'communication' &&
		props.attachment.kind === 'pdf' &&
		props.attachment.open_url
	) {
		return 'Open PDF';
	}
	if (props.attachment.preview_url) {
		return 'Preview';
	}
	return props.attachment.kind === 'link' ? 'Open link' : 'Open';
});
const showOpenOriginalAction = computed(() => {
	if (!props.attachment.preview_url || !props.attachment.open_url) return false;
	if (props.attachment.open_url === props.attachment.preview_url) return false;
	if (props.variant === 'communication' && props.attachment.kind === 'pdf') return false;
	return true;
});
const showSecondaryPreviewAction = computed(() => {
	return Boolean(
		props.variant === 'communication' &&
		showCommunicationPdfPreview.value &&
		props.attachment.preview_url &&
		props.attachment.open_url &&
		props.attachment.preview_url !== props.attachment.open_url
	);
});
const openOriginalLabel = computed(() =>
	props.variant === 'evidence' ? 'Open' : 'Open original'
);
const actionClass = computed(() =>
	props.variant === 'evidence' ? 'if-button if-button--secondary' : 'if-action'
);
const hasExtraActions = computed(() => Boolean(slots['extra-actions']));
const hasActionRow = computed(() => {
	return Boolean(
		primaryActionUrl.value ||
		showSecondaryPreviewAction.value ||
		showOpenOriginalAction.value ||
		hasExtraActions.value
	);
});
const communicationPdfMessage = computed(() => {
	if (showCommunicationPdfPreview.value) {
		return 'First-page preview from this governed PDF attachment.';
	}
	return 'Open the original PDF from this communication while the preview is unavailable.';
});
const communicationPdfFallbackMessage = computed(() => {
	if (props.attachment.preview_status === 'pending') {
		return 'The first-page preview is still processing. Use Open PDF to review the full document now.';
	}
	if (props.attachment.preview_status === 'failed') {
		return 'The first-page preview could not be generated. Use Open PDF to review the original file.';
	}
	return 'Use Open PDF to review the original file from this communication.';
});
const kindDataAttribute = computed(() => {
	if (props.variant === 'communication') return 'data-communication-attachment-kind';
	if (props.variant === 'learning') return 'data-learning-resource-kind';
	if (props.variant === 'planning') return 'data-resource-preview-kind';
	return null;
});

watch(
	() =>
		`${props.attachment.item_id || props.attachment.file_id || props.attachment.display_name || ''}:${props.attachment.thumbnail_url || ''}:${props.attachment.preview_url || ''}`,
	() => {
		imagePreviewFailed.value = false;
		imagePreviewUsesFallbackUrl.value = false;
	}
);

function kindDataAttrs(kind: 'image' | 'pdf'): Record<string, string> {
	if (!kindDataAttribute.value) return {};
	return {
		[kindDataAttribute.value]: kind,
	};
}

function handleImagePreviewError() {
	if (
		!imagePreviewUsesFallbackUrl.value &&
		props.attachment.thumbnail_url &&
		inlineImageUrl.value === props.attachment.thumbnail_url &&
		canRetryInlineImageWithPreview.value
	) {
		imagePreviewUsesFallbackUrl.value = true;
		return;
	}

	imagePreviewFailed.value = true;
}
</script>
