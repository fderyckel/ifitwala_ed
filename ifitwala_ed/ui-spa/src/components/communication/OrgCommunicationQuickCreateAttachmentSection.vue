<template>
	<section class="rounded-[28px] border border-border/70 bg-white p-5 shadow-soft">
		<div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
			<div class="space-y-1">
				<p class="type-overline text-ink/55">Attachments</p>
				<h3 class="type-h3 text-ink">Files and links</h3>
				<p class="type-caption text-ink/65">
					{{ helpText }}
				</p>
			</div>
			<div class="flex flex-wrap gap-2">
				<button
					type="button"
					class="rounded-full border border-border/80 bg-surface px-3 py-1.5 type-button-label text-ink transition hover:border-jacaranda hover:text-jacaranda"
					:disabled="attachmentActionsDisabled"
					@click="emit('trigger-file-picker')"
				>
					Add file
				</button>
				<button
					type="button"
					class="rounded-full border border-border/80 bg-surface px-3 py-1.5 type-button-label text-ink transition hover:border-jacaranda hover:text-jacaranda"
					:disabled="attachmentActionsDisabled"
					@click="emit('toggle-link-composer')"
				>
					{{ showLinkComposer ? 'Close link' : 'Add link' }}
				</button>
			</div>
		</div>

		<div
			v-if="attachmentErrorMessage"
			class="mt-4 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3"
		>
			<p class="type-caption text-rose-900">{{ attachmentErrorMessage }}</p>
		</div>

		<div
			v-if="showLinkComposer"
			class="mt-4 rounded-[24px] border border-border/70 bg-surface-soft/70 p-4"
		>
			<div class="grid grid-cols-1 gap-3">
				<div class="space-y-1">
					<label class="type-label">Link URL</label>
					<FormControl
						v-model="linkDraft.external_url"
						type="text"
						placeholder="https://example.com/resource.pdf"
						:disabled="attachmentActionsDisabled"
					/>
				</div>
				<div class="space-y-1">
					<label class="type-label">Link label</label>
					<FormControl
						v-model="linkDraft.title"
						type="text"
						placeholder="Optional display label"
						:disabled="attachmentActionsDisabled"
					/>
				</div>
			</div>
			<div class="mt-3 flex flex-wrap justify-end gap-2">
				<button
					type="button"
					class="if-button if-button--secondary"
					:disabled="attachmentActionsDisabled"
					@click="emit('reset-link-draft')"
				>
					Cancel
				</button>
				<button
					type="button"
					class="if-button if-button--primary"
					:disabled="attachmentActionsDisabled || !linkDraftReady"
					@click="emit('submit-link')"
				>
					Add link
				</button>
			</div>
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
				No attachments yet. Keep it light: add only the file or link teachers and families actually
				need.
			</p>
		</div>
	</section>
</template>

<script setup lang="ts">
import { FormControl } from 'frappe-ui';

import type { OrgCommunicationAttachmentRow } from '@/types/contracts/org_communication_attachments/shared';

import type { LinkDraftState } from './orgCommunicationQuickCreateTypes';

defineProps<{
	helpText: string;
	attachmentRows: OrgCommunicationAttachmentRow[];
	attachmentErrorMessage: string;
	attachmentActionsDisabled: boolean;
	removeDisabled: boolean;
	showLinkComposer: boolean;
	linkDraft: LinkDraftState;
	linkDraftReady: boolean;
}>();

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
