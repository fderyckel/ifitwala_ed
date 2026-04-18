<template>
	<section class="overflow-hidden rounded-2xl border border-border/70 bg-white">
		<div class="border-b border-border/60 bg-gray-50/60 px-4 py-4">
			<div class="flex flex-wrap items-start justify-between gap-3">
				<div class="min-w-0">
					<p class="text-xs font-semibold uppercase tracking-[0.16em] text-ink/45">
						PDF Workspace
					</p>
					<h3 class="mt-2 text-sm font-semibold text-ink">
						{{ attachment.file_name || 'PDF attachment' }}
					</h3>
					<p class="mt-2 text-sm text-ink/70">
						{{ workspaceMessage }}
					</p>
				</div>
				<div class="flex flex-wrap gap-2">
					<Badge v-if="annotationReadiness" variant="subtle">
						{{ annotationModeLabel(annotationReadiness) }}
					</Badge>
					<Badge v-if="attachment.preview_status" variant="subtle">
						Preview {{ attachment.preview_status }}
					</Badge>
					<Badge v-if="attachment.file_size" variant="subtle">
						{{ formatBytes(attachment.file_size) }}
					</Badge>
				</div>
			</div>

			<p v-if="annotationReadiness" class="mt-3 text-sm text-ink/60">
				{{ annotationReadiness.title }}
			</p>

			<div class="mt-4 flex flex-wrap gap-2">
				<a
					v-if="attachment.preview_url"
					class="if-button if-button--secondary"
					:href="attachment.preview_url || undefined"
					target="_blank"
					rel="noreferrer"
				>
					{{ previewActionLabel }}
				</a>
				<a
					v-if="attachment.open_url"
					class="if-button if-button--secondary"
					:href="attachment.open_url || undefined"
					target="_blank"
					rel="noreferrer"
				>
					Open source PDF
				</a>
			</div>
		</div>

		<div class="relative bg-gray-50/40">
			<div
				class="pointer-events-none absolute inset-x-0 top-0 flex items-center justify-between px-4 py-3"
			>
				<div
					class="rounded-full border border-white/70 bg-white/90 px-3 py-1 text-xs font-medium text-ink/55 shadow-sm"
				>
					Ifitwala-owned viewer shell
				</div>
				<div
					class="rounded-full border border-white/70 bg-white/90 px-3 py-1 text-xs font-medium text-ink/55 shadow-sm"
				>
					pdf.js surface pending install
				</div>
			</div>

			<div v-if="showInlinePreview" class="p-3 pt-12">
				<img
					:src="attachment.preview_url || undefined"
					:alt="`${attachment.file_name || 'PDF attachment'} first-page preview`"
					class="h-72 w-full rounded-xl bg-white object-contain"
					loading="lazy"
				/>
			</div>
			<div v-else class="flex min-h-56 items-center justify-center px-6 py-12 text-center">
				<div>
					<p class="text-sm font-semibold text-ink">Preview not available yet</p>
					<p class="mt-2 text-sm text-ink/70">
						{{ fallbackMessage }}
					</p>
				</div>
			</div>
		</div>
	</section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { Badge } from 'frappe-ui';

import type { Response as GetDrawerResponse } from '@/types/contracts/gradebook/get_drawer';

type SubmissionAttachmentRow = NonNullable<
	NonNullable<GetDrawerResponse['selected_submission']>['attachments']
>[number];

type AnnotationReadinessPayload = NonNullable<
	NonNullable<GetDrawerResponse['selected_submission']>['annotation_readiness']
>;

const props = defineProps<{
	attachment: SubmissionAttachmentRow;
	annotationReadiness?: AnnotationReadinessPayload | null;
}>();

const showInlinePreview = computed(
	() => props.attachment.preview_status === 'ready' && Boolean(props.attachment.preview_url)
);

const previewActionLabel = computed(() =>
	props.attachment.preview_status === 'ready' ? 'Open preview' : 'Try preview'
);

const workspaceMessage = computed(() => {
	if (props.annotationReadiness?.message) {
		return props.annotationReadiness.message;
	}
	if (showInlinePreview.value) {
		return 'Governed first-page preview is ready for this PDF evidence.';
	}
	return 'Open the governed source PDF while inline preview is unavailable.';
});

const fallbackMessage = computed(() => {
	if (props.attachment.preview_status === 'pending') {
		return 'Preview generation is still processing. Open the source PDF to review the full document now.';
	}
	if (props.attachment.preview_status === 'failed') {
		return 'Preview generation failed for this PDF. Open the source PDF to continue review.';
	}
	if (props.attachment.preview_status === 'not_applicable') {
		return 'This PDF does not currently expose a preview derivative. Open the source PDF to continue review.';
	}
	return 'Open the source PDF to continue review from this drawer.';
});

function annotationModeLabel(readiness: AnnotationReadinessPayload): string {
	if (readiness.mode === 'reduced') return 'Reduced mode';
	if (readiness.mode === 'unavailable') return 'Preview fallback';
	return 'Not applicable';
}

function formatBytes(value?: number | null) {
	if (!value) return '0 B';
	if (value < 1024) return `${value} B`;
	const kb = value / 1024;
	if (kb < 1024) return `${kb.toFixed(1)} KB`;
	return `${(kb / 1024).toFixed(1)} MB`;
}
</script>
