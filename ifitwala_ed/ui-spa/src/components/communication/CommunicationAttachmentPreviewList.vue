<template>
	<div class="grid gap-3 md:grid-cols-2">
		<article
			v-for="attachment in attachments"
			:key="attachment.row_name"
			:class="attachmentCardClasses(attachment)"
		>
			<AttachmentPreviewCard
				v-if="attachment.attachment"
				:attachment="attachment.attachment"
				variant="communication"
				:title="attachmentLabel(attachment)"
				:description="attachment.description"
				:meta-text="attachmentMetaLine(attachment)"
				:chips="attachmentChips(attachment)"
			/>
		</article>
	</div>
</template>

<script setup lang="ts">
import AttachmentPreviewCard from '@/components/attachments/AttachmentPreviewCard.vue';
import type { OrgCommunicationAttachmentRow } from '@/types/contracts/org_communication_attachments/shared';

defineProps<{
	attachments: OrgCommunicationAttachmentRow[];
}>();

function attachmentCardClasses(attachment: OrgCommunicationAttachmentRow): string[] {
	return [
		'rounded-2xl',
		'border',
		'border-line-soft',
		'bg-surface-soft',
		'p-4',
		isWideAttachment(attachment) && 'md:col-span-2',
	].filter(Boolean) as string[];
}

function attachmentLabel(attachment: OrgCommunicationAttachmentRow): string {
	return (
		attachment.title || attachment.file_name || attachment.external_url || attachment.row_name
	);
}

function isWideAttachment(attachment: OrgCommunicationAttachmentRow): boolean {
	const preview = attachment.attachment;
	return preview?.kind === 'image' || preview?.kind === 'pdf';
}

function attachmentChips(attachment: OrgCommunicationAttachmentRow): string[] {
	const preview = attachment.attachment;
	if (!preview) return [];
	if (preview.kind === 'link') {
		return ['Link'];
	}
	const extension = String(preview.extension || '')
		.trim()
		.toUpperCase();
	return extension ? [extension] : [];
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
