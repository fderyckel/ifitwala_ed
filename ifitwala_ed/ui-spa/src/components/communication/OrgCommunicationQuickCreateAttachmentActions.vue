<template>
	<div class="space-y-4">
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
			class="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3"
		>
			<p class="type-caption text-rose-900">{{ attachmentErrorMessage }}</p>
		</div>

		<InlineUploadStatus
			v-if="uploadProgress"
			:label="uploadProgressLabel"
			:progress="uploadProgress"
		/>

		<div
			v-if="showLinkComposer"
			class="rounded-[24px] border border-border/70 bg-surface-soft/70 p-4"
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
	</div>
</template>

<script setup lang="ts">
import { FormControl } from 'frappe-ui';

import InlineUploadStatus from '@/components/feedback/InlineUploadStatus.vue';
import type { UploadProgressState } from '@/lib/uploadProgress';
import type { LinkDraftState } from './orgCommunicationQuickCreateTypes';

defineProps<{
	helpText: string;
	attachmentErrorMessage: string;
	attachmentActionsDisabled: boolean;
	showLinkComposer: boolean;
	linkDraft: LinkDraftState;
	linkDraftReady: boolean;
	uploadProgress: UploadProgressState | null;
	uploadProgressLabel: string;
}>();

const emit = defineEmits<{
	(e: 'trigger-file-picker'): void;
	(e: 'toggle-link-composer'): void;
	(e: 'reset-link-draft'): void;
	(e: 'submit-link'): void;
}>();
</script>
