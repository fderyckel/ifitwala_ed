<template>
	<div class="grid gap-3 md:grid-cols-2">
		<article
			v-for="attachment in attachments"
			:key="attachment.row_name"
			:class="attachmentCardClasses(attachment)"
		>
			<div v-if="showInlineImagePreview(attachment)" class="mb-4">
				<a
					:href="attachment.preview_url || attachment.open_url || undefined"
					target="_blank"
					rel="noreferrer"
					class="group block overflow-hidden rounded-2xl border border-line-soft bg-white"
					data-communication-attachment-kind="image"
				>
					<img
						:src="imagePreviewUrl(attachment) || undefined"
						:alt="attachmentLabel(attachment)"
						class="h-40 w-full object-cover transition duration-200 group-hover:scale-[1.01]"
						loading="lazy"
						@error="markImagePreviewFailed(attachment)"
					/>
					<div
						class="flex items-center justify-between border-t border-line-soft bg-white px-4 py-3"
					>
						<div>
							<p class="text-xs font-semibold uppercase tracking-[0.18em] text-ink/45">
								Image preview
							</p>
							<p class="mt-1 text-sm text-ink/80">
								Open the governed preview from this communication.
							</p>
						</div>
						<span class="chip">{{ attachmentExtensionLabel(attachment) }}</span>
					</div>
				</a>
			</div>

			<div
				v-else-if="isPdfAttachment(attachment)"
				class="mb-4"
				data-communication-attachment-kind="pdf"
			>
				<div class="overflow-hidden rounded-2xl border border-line-soft bg-white">
					<div class="flex items-start justify-between gap-3 border-b border-line-soft px-4 py-4">
						<div>
							<p class="text-xs font-semibold uppercase tracking-[0.18em] text-ink/45">
								PDF preview
							</p>
							<p class="mt-2 text-base font-semibold text-ink">
								{{ attachmentLabel(attachment) }}
							</p>
							<p class="mt-2 text-sm text-ink/75">
								{{ pdfPreviewMessage(attachment) }}
							</p>
						</div>
						<div class="rounded-2xl bg-clay/15 px-3 py-2 text-right">
							<p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-clay">
								{{ attachmentExtensionLabel(attachment) }}
							</p>
							<p class="mt-1 text-xs text-ink/60">
								{{ showPdfInlinePreview(attachment) ? 'First page ready' : 'Open original' }}
							</p>
						</div>
					</div>
					<div v-if="showPdfInlinePreview(attachment)" class="bg-surface-soft/60 p-3">
						<img
							:src="attachment.preview_url || undefined"
							:alt="`${attachmentLabel(attachment)} first page preview`"
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
								{{ pdfPreviewFallbackMessage(attachment) }}
							</p>
						</div>
					</div>
				</div>
			</div>

			<div class="min-w-0">
				<div class="flex flex-wrap items-center gap-2">
					<p class="type-body-strong text-ink">{{ attachmentLabel(attachment) }}</p>
					<span v-if="attachment.kind === 'link'" class="chip">Link</span>
					<span v-else-if="attachmentExtensionLabel(attachment) !== 'FILE'" class="chip">
						{{ attachmentExtensionLabel(attachment) }}
					</span>
				</div>
				<p v-if="attachment.description" class="mt-2 type-caption text-ink/70">
					{{ attachment.description }}
				</p>
				<p v-if="attachmentMetaLine(attachment)" class="mt-2 type-caption text-ink/60">
					{{ attachmentMetaLine(attachment) }}
				</p>
			</div>

			<div class="mt-3 flex flex-wrap gap-2">
				<a
					v-if="primaryAttachmentUrl(attachment)"
					:href="primaryAttachmentUrl(attachment) || undefined"
					target="_blank"
					rel="noreferrer"
					class="if-action"
				>
					{{ primaryActionLabel(attachment) }}
				</a>
				<a
					v-if="showOpenPreviewAction(attachment)"
					:href="attachment.preview_url || undefined"
					target="_blank"
					rel="noreferrer"
					class="if-action"
				>
					Open preview image
				</a>
				<a
					v-if="showOpenOriginalAction(attachment)"
					:href="attachment.open_url || undefined"
					target="_blank"
					rel="noreferrer"
					class="if-action"
				>
					Open original
				</a>
			</div>
		</article>
	</div>
</template>

<script setup lang="ts">
import { ref } from 'vue';

import type { OrgCommunicationAttachmentRow } from '@/types/contracts/org_communication_attachments/shared';

defineProps<{
	attachments: OrgCommunicationAttachmentRow[];
}>();

const failedImagePreviewKeys = ref<Record<string, boolean>>({});

function attachmentCardClasses(attachment: OrgCommunicationAttachmentRow): string[] {
	return [
		'rounded-2xl',
		'border',
		'border-line-soft',
		'bg-surface-soft',
		'p-4',
		(isImageAttachment(attachment) || isPdfAttachment(attachment)) && 'md:col-span-2',
	].filter(Boolean) as string[];
}

function attachmentLabel(attachment: OrgCommunicationAttachmentRow): string {
	return (
		attachment.title || attachment.file_name || attachment.external_url || attachment.row_name
	);
}

function attachmentExtension(attachment: OrgCommunicationAttachmentRow): string {
	const rawName = String(attachment.file_name || '').trim();
	const lastDot = rawName.lastIndexOf('.');
	if (!rawName || lastDot < 0 || lastDot === rawName.length - 1) {
		return '';
	}
	return rawName.slice(lastDot + 1).toLowerCase();
}

function attachmentExtensionLabel(attachment: OrgCommunicationAttachmentRow): string {
	return attachmentExtension(attachment) ? attachmentExtension(attachment).toUpperCase() : 'FILE';
}

function isImageAttachment(attachment: OrgCommunicationAttachmentRow): boolean {
	return (
		attachment.kind === 'file' &&
		['jpg', 'jpeg', 'png', 'webp'].includes(attachmentExtension(attachment))
	);
}

function isPdfAttachment(attachment: OrgCommunicationAttachmentRow): boolean {
	return attachment.kind === 'file' && attachmentExtension(attachment) === 'pdf';
}

function previewStatus(
	attachment: OrgCommunicationAttachmentRow
): OrgCommunicationAttachmentRow['preview_status'] {
	return attachment.preview_status || null;
}

function imagePreviewKey(attachment: OrgCommunicationAttachmentRow): string {
	return `${attachment.row_name}:${imagePreviewUrl(attachment) || ''}`;
}

function markImagePreviewFailed(attachment: OrgCommunicationAttachmentRow): void {
	failedImagePreviewKeys.value = {
		...failedImagePreviewKeys.value,
		[imagePreviewKey(attachment)]: true,
	};
}

function hasImagePreviewFailure(attachment: OrgCommunicationAttachmentRow): boolean {
	return Boolean(failedImagePreviewKeys.value[imagePreviewKey(attachment)]);
}

function primaryAttachmentUrl(attachment: OrgCommunicationAttachmentRow): string | null {
	if (isPdfAttachment(attachment)) {
		return attachment.open_url || attachment.preview_url || null;
	}
	return attachment.preview_url || attachment.open_url || attachment.external_url || null;
}

function imagePreviewUrl(attachment: OrgCommunicationAttachmentRow): string | null {
	if (attachment.thumbnail_url) {
		return attachment.thumbnail_url;
	}
	if (previewStatus(attachment) === 'ready' && attachment.preview_url) {
		return attachment.preview_url;
	}
	return null;
}

function showInlineImagePreview(attachment: OrgCommunicationAttachmentRow): boolean {
	return Boolean(
		imagePreviewUrl(attachment) &&
		isImageAttachment(attachment) &&
		!hasImagePreviewFailure(attachment)
	);
}

function showPdfInlinePreview(attachment: OrgCommunicationAttachmentRow): boolean {
	return Boolean(
		attachment.preview_url && isPdfAttachment(attachment) && previewStatus(attachment) === 'ready'
	);
}

function primaryActionLabel(attachment: OrgCommunicationAttachmentRow): string {
	if (isPdfAttachment(attachment) && attachment.open_url) {
		return 'Open PDF';
	}
	if (attachment.preview_url) {
		return 'Preview';
	}
	return attachment.kind === 'link' ? 'Open link' : 'Open';
}

function showOpenOriginalAction(attachment: OrgCommunicationAttachmentRow): boolean {
	return Boolean(
		attachment.kind === 'file' &&
		!isPdfAttachment(attachment) &&
		attachment.preview_url &&
		attachment.open_url &&
		attachment.open_url !== attachment.preview_url
	);
}

function showOpenPreviewAction(attachment: OrgCommunicationAttachmentRow): boolean {
	return Boolean(
		isPdfAttachment(attachment) &&
		showPdfInlinePreview(attachment) &&
		attachment.preview_url &&
		attachment.open_url &&
		attachment.open_url !== attachment.preview_url
	);
}

function pdfPreviewMessage(attachment: OrgCommunicationAttachmentRow): string {
	if (showPdfInlinePreview(attachment)) {
		return 'First-page preview from this governed PDF attachment.';
	}
	return 'Open the original PDF from this communication while the preview is unavailable.';
}

function pdfPreviewFallbackMessage(attachment: OrgCommunicationAttachmentRow): string {
	if (previewStatus(attachment) === 'pending') {
		return 'The first-page preview is still processing. Use Open PDF to review the full document now.';
	}
	if (previewStatus(attachment) === 'failed') {
		return 'The first-page preview could not be generated. Use Open PDF to review the original file.';
	}
	return 'Use Open PDF to review the original file from this communication.';
}

function attachmentMetaLine(attachment: OrgCommunicationAttachmentRow): string | null {
	if (attachment.kind === 'link') {
		return attachment.external_url || null;
	}
	const parts = [
		attachment.file_name,
		attachment.file_size ? formatFileSize(attachment.file_size) : null,
	].filter(Boolean);
	return parts.length ? parts.join(' · ') : null;
}

function formatFileSize(value: number | string): string {
	const size = typeof value === 'number' ? value : Number(value || 0);
	if (!Number.isFinite(size) || size <= 0) {
		return String(value);
	}
	if (size < 1024) {
		return `${size} B`;
	}
	if (size < 1024 * 1024) {
		return `${(size / 1024).toFixed(1)} KB`;
	}
	return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}
</script>
