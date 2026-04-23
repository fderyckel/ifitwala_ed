<template>
	<section
		class="if-org-communication-attachment-section rounded-[28px] border border-border/70 bg-white p-5 shadow-soft"
	>
		<OrgCommunicationQuickCreateAttachmentActions
			v-if="showActions"
			:help-text="helpText"
			:attachment-error-message="attachmentErrorMessage"
			:attachment-actions-disabled="attachmentActionsDisabled"
			:show-link-composer="showLinkComposer"
			:link-draft="linkDraft"
			:link-draft-ready="linkDraftReady"
			:upload-progress="uploadProgress"
			:upload-progress-label="uploadProgressLabel"
			@trigger-file-picker="emit('trigger-file-picker')"
			@toggle-link-composer="emit('toggle-link-composer')"
			@reset-link-draft="emit('reset-link-draft')"
			@submit-link="emit('submit-link')"
		/>

		<div v-else class="space-y-1">
			<p class="type-overline text-ink/55">Attachments</p>
			<h3 class="type-h3 text-ink">Files and links</h3>
			<p class="type-caption text-ink/65">
				Review the files and links already attached to this communication.
			</p>
		</div>

		<div class="mt-4 space-y-3">
			<div
				v-for="attachment in attachmentRows"
				:key="attachment.row_name"
				class="flex flex-col gap-3 rounded-2xl border border-border/70 bg-surface-soft/70 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
			>
				<div class="min-w-0">
					<p class="type-body-strong text-ink">{{ attachment.title }}</p>
					<p class="mt-1 truncate type-caption text-ink/60">
						{{ formatAttachmentMeta(attachment) }}
					</p>
				</div>
				<div class="flex flex-wrap gap-2">
					<a
						v-if="attachment.preview_url || attachment.open_url"
						:href="attachment.preview_url || attachment.open_url"
						target="_blank"
						rel="noopener noreferrer"
						class="rounded-full border border-border/80 bg-white px-3 py-1.5 type-button-label text-ink transition hover:border-jacaranda hover:text-jacaranda"
					>
						Open
					</a>
					<button
						type="button"
						class="rounded-full border border-border/80 bg-white px-3 py-1.5 type-button-label text-slate-token transition hover:border-rose-300 hover:text-rose-700"
						:disabled="removeDisabled"
						@click="emit('delete-attachment', attachment)"
					>
						Remove
					</button>
				</div>
			</div>
			<p v-if="!attachmentRows.length" class="type-caption text-ink/60">
				{{
					showActions
						? 'No attachments yet. Keep it light: add only the file or link teachers and families actually need.'
						: 'No attachments yet. Add a file or link from the message section above when this communication needs one.'
				}}
			</p>
		</div>
	</section>
</template>

<script setup lang="ts">
import type { OrgCommunicationAttachmentRow } from '@/types/contracts/org_communication_attachments/shared';
import type { UploadProgressState } from '@/lib/uploadProgress';

import OrgCommunicationQuickCreateAttachmentActions from './OrgCommunicationQuickCreateAttachmentActions.vue';
import type { LinkDraftState } from './orgCommunicationQuickCreateTypes';

withDefaults(
	defineProps<{
		helpText: string;
		attachmentRows: OrgCommunicationAttachmentRow[];
		attachmentErrorMessage: string;
		attachmentActionsDisabled: boolean;
		removeDisabled: boolean;
		showLinkComposer: boolean;
		linkDraft: LinkDraftState;
		linkDraftReady: boolean;
		uploadProgress: UploadProgressState | null;
		uploadProgressLabel: string;
		showActions?: boolean;
	}>(),
	{
		showActions: true,
	}
);

const emit = defineEmits<{
	(e: 'trigger-file-picker'): void;
	(e: 'toggle-link-composer'): void;
	(e: 'reset-link-draft'): void;
	(e: 'submit-link'): void;
	(e: 'delete-attachment', attachment: OrgCommunicationAttachmentRow): void;
}>();

function formatAttachmentMeta(attachment: OrgCommunicationAttachmentRow) {
	if (attachment.kind === 'link') {
		return attachment.external_url || 'External link';
	}
	const parts = [attachment.file_name];
	if (attachment.file_size) {
		parts.push(formatFileSize(attachment.file_size));
	}
	return parts.filter(Boolean).join(' · ') || 'Governed file';
}

function formatFileSize(value: number | string | null | undefined) {
	const size = typeof value === 'number' ? value : Number(value || 0);
	if (!Number.isFinite(size) || size <= 0) return '';
	if (size < 1024) return `${size} B`;
	if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
	return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}
</script>
