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
					<Badge v-if="draftAnnotations.length" variant="subtle">
						{{ draftCountLabel }}
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
					v-if="sourcePdfUrl"
					class="if-button if-button--secondary"
					:href="sourcePdfUrl"
					target="_blank"
					rel="noreferrer"
				>
					Open source PDF
				</a>
			</div>
		</div>

		<div class="border-b border-border/60 bg-white px-4 py-3">
			<div class="flex flex-wrap items-center justify-between gap-3">
				<div class="flex flex-wrap items-center gap-2">
					<button
						type="button"
						class="if-button if-button--quiet"
						:disabled="!canGoPreviousPage"
						@click="goToPreviousPage"
					>
						Previous
					</button>
					<button
						type="button"
						class="if-button if-button--quiet"
						:disabled="!canGoNextPage"
						@click="goToNextPage"
					>
						Next
					</button>
					<span class="text-sm font-medium text-ink/70">Page {{ currentPageLabel }}</span>
				</div>

				<div class="flex flex-wrap items-center gap-2">
					<button
						type="button"
						class="if-button if-button--quiet"
						:disabled="!canAdjustZoom"
						@click="zoomOut"
					>
						Zoom out
					</button>
					<button
						type="button"
						class="if-button if-button--quiet"
						:disabled="!canAdjustZoom"
						@click="resetZoom"
					>
						{{ zoomLabel }}
					</button>
					<button
						type="button"
						class="if-button if-button--quiet"
						:disabled="!canAdjustZoom"
						@click="zoomIn"
					>
						Zoom in
					</button>
				</div>
			</div>
		</div>

		<div class="border-b border-border/60 bg-white px-4 py-3">
			<div class="flex flex-wrap items-start justify-between gap-3">
				<div class="min-w-0">
					<p class="text-xs font-semibold uppercase tracking-[0.16em] text-ink/45">
						Draft Overlay
					</p>
					<h4 class="mt-1 text-sm font-semibold text-ink">Session-local annotation drafts</h4>
					<p class="mt-2 text-sm text-ink/70">
						{{ overlayGuidance }}
					</p>
				</div>

				<div class="flex flex-wrap gap-2">
					<button
						type="button"
						class="rounded-full px-3 py-1.5 text-sm font-medium transition"
						:class="toolButtonClass('browse')"
						@click="selectedTool = 'browse'"
					>
						Browse
					</button>
					<button
						type="button"
						class="rounded-full px-3 py-1.5 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50"
						:class="toolButtonClass('point')"
						:disabled="!canAnnotateCurrentPage"
						@click="selectedTool = 'point'"
					>
						Point comment
					</button>
					<button
						type="button"
						class="rounded-full px-3 py-1.5 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50"
						:class="toolButtonClass('rect')"
						:disabled="!canAnnotateCurrentPage"
						@click="selectedTool = 'rect'"
					>
						Area comment
					</button>
					<button
						type="button"
						class="rounded-full px-3 py-1.5 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50"
						:class="pageCommentButtonClass"
						:disabled="!canAnnotateCurrentPage"
						@click="addPageCommentDraft"
					>
						Add page comment
					</button>
				</div>
			</div>
		</div>

		<div class="grid xl:grid-cols-[minmax(0,1fr)_19rem]">
			<div class="relative min-h-[26rem] bg-gray-50/40">
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
						{{ viewerSurfaceLabel }}
					</div>
				</div>

				<div
					v-if="showViewerLoadingBanner"
					class="absolute inset-x-0 top-12 z-10 flex justify-center px-4"
				>
					<div
						class="inline-flex items-center gap-2 rounded-full border border-border/70 bg-white/95 px-4 py-2 text-sm text-ink shadow-sm"
					>
						<Spinner class="h-4 w-4" />
						<span>{{ viewerLoadingLabel }}</span>
					</div>
				</div>

				<div
					v-if="hasRenderedPage"
					ref="viewerHostRef"
					class="overflow-auto p-3 pt-12 md:p-6 md:pt-14"
				>
					<div class="mx-auto flex min-h-[22rem] w-full items-start justify-center">
						<div ref="pageSurfaceRef" class="relative inline-block">
							<canvas
								ref="canvasRef"
								:aria-label="`${attachment.file_name || 'PDF attachment'} PDF page`"
								class="block max-w-full rounded-xl bg-white shadow-sm ring-1 ring-black/5"
							/>

							<div
								class="absolute inset-0"
								:class="overlayCursorClass"
								@click="handleSurfaceClick"
								@pointerdown="handleSurfacePointerDown"
								@pointermove="handleSurfacePointerMove"
								@pointerup="handleSurfacePointerUp"
								@pointercancel="cancelPendingRect"
							>
								<button
									v-for="draft in pointDraftsForCurrentPage"
									:key="draft.id"
									type="button"
									class="absolute flex h-7 w-7 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border border-white bg-canopy text-xs font-semibold text-white shadow-sm ring-2 ring-canopy/20 transition hover:scale-105"
									:class="selectedDraftId === draft.id ? 'ring-4 ring-canopy/30' : ''"
									:style="pointStyle(draft.point)"
									:aria-label="`Select ${kindLabel(draft.kind).toLowerCase()} draft`"
									@click.stop="selectDraft(draft.id)"
									@pointerdown.stop
								>
									{{ draftOrdinal(draft.id) }}
								</button>

								<button
									v-for="draft in rectDraftsForCurrentPage"
									:key="draft.id"
									type="button"
									class="absolute border-2 border-canopy/80 bg-canopy/10 transition hover:bg-canopy/15"
									:class="selectedDraftId === draft.id ? 'ring-4 ring-canopy/20' : ''"
									:style="rectStyle(draft.rect)"
									:aria-label="`Select ${kindLabel(draft.kind).toLowerCase()} draft`"
									@click.stop="selectDraft(draft.id)"
									@pointerdown.stop
								>
									<span
										class="absolute -left-2 -top-2 flex h-6 min-w-6 items-center justify-center rounded-full border border-white bg-canopy px-1 text-xs font-semibold text-white shadow-sm"
									>
										{{ draftOrdinal(draft.id) }}
									</span>
								</button>

								<div
									v-if="pendingRectStyle"
									class="absolute border-2 border-dashed border-canopy/70 bg-canopy/10"
									:style="pendingRectStyle"
								/>
							</div>
						</div>
					</div>
				</div>

				<div v-else-if="showInlinePreviewFallback" class="p-3 pt-12">
					<img
						:src="attachment.preview_url || undefined"
						:alt="`${attachment.file_name || 'PDF attachment'} first-page preview`"
						class="h-72 w-full rounded-xl bg-white object-contain"
						loading="lazy"
					/>
				</div>

				<div v-else class="flex min-h-[22rem] items-center justify-center px-6 py-12 text-center">
					<div>
						<p class="text-sm font-semibold text-ink">{{ viewerEmptyTitle }}</p>
						<p class="mt-2 text-sm text-ink/70">
							{{ fallbackMessage }}
						</p>
					</div>
				</div>
			</div>

			<aside class="border-t border-border/60 bg-white/95 p-4 xl:border-l xl:border-t-0">
				<div class="flex items-start justify-between gap-3">
					<div>
						<p class="text-xs font-semibold uppercase tracking-[0.16em] text-ink/45">
							Draft Annotations
						</p>
						<h4 class="mt-1 text-sm font-semibold text-ink">Local drafts only</h4>
					</div>
					<Badge variant="subtle">{{ draftCountLabel }}</Badge>
				</div>

				<p class="mt-2 text-sm text-ink/70">
					These overlays stay inside this drawer session only until structured feedback records
					land.
				</p>

				<div class="mt-4 space-y-2">
					<button
						v-for="draft in draftAnnotations"
						:key="draft.id"
						type="button"
						class="w-full rounded-2xl border px-3 py-3 text-left transition"
						:class="
							selectedDraftId === draft.id
								? 'border-canopy/40 bg-canopy/5 shadow-sm'
								: 'border-border/70 bg-gray-50/50 hover:border-border hover:bg-gray-100/80'
						"
						@click="selectDraft(draft.id)"
					>
						<div class="flex items-start justify-between gap-3">
							<div class="min-w-0">
								<p class="text-sm font-semibold text-ink">
									{{ kindLabel(draft.kind) }}
								</p>
								<p class="mt-1 text-xs text-ink/55">Page {{ draft.page }}</p>
							</div>
							<div
								class="flex h-6 min-w-6 items-center justify-center rounded-full border border-border/70 bg-white px-1 text-xs font-semibold text-ink/60"
							>
								{{ draftOrdinal(draft.id) }}
							</div>
						</div>
						<p class="mt-2 text-sm text-ink/70">
							{{ draft.comment || draftPlaceholder(draft) }}
						</p>
					</button>

					<div
						v-if="!draftAnnotations.length"
						class="rounded-2xl border border-dashed border-border/70 bg-gray-50/40 px-4 py-5 text-sm text-ink/65"
					>
						{{ emptyDraftMessage }}
					</div>
				</div>

				<div
					v-if="selectedDraft"
					class="mt-4 rounded-2xl border border-border/70 bg-gray-50/50 p-4"
				>
					<div class="flex items-start justify-between gap-3">
						<div>
							<p class="text-xs font-semibold uppercase tracking-[0.16em] text-ink/45">
								Selected Draft
							</p>
							<h4 class="mt-1 text-sm font-semibold text-ink">
								{{ kindLabel(selectedDraft.kind) }} · Page {{ selectedDraft.page }}
							</h4>
						</div>
						<button type="button" class="if-button if-button--quiet" @click="removeSelectedDraft">
							Remove
						</button>
					</div>

					<label
						class="mt-4 block text-xs font-semibold uppercase tracking-[0.16em] text-ink/45"
						for="gradebook-pdf-draft-note"
					>
						Draft note
					</label>
					<textarea
						id="gradebook-pdf-draft-note"
						class="mt-2 min-h-28 w-full rounded-2xl border border-border/70 bg-white px-3 py-3 text-sm text-ink shadow-sm outline-none transition focus:border-canopy/50 focus:ring-2 focus:ring-canopy/20"
						:value="selectedDraft.comment"
						placeholder="Capture the draft teaching note for this local annotation anchor."
						@input="onSelectedDraftCommentChanged"
					/>
					<p class="mt-3 text-xs text-ink/55">
						{{ selectedDraftAnchorSummary }}
					</p>
				</div>
			</aside>
		</div>
	</section>
</template>

<script setup lang="ts">
import { Badge, Spinner } from 'frappe-ui';
import {
	computed,
	nextTick,
	onBeforeUnmount,
	onMounted,
	ref,
	watch,
	type CSSProperties,
} from 'vue';
import { GlobalWorkerOptions, getDocument } from 'pdfjs-dist/legacy/build/pdf.mjs';
import pdfWorkerUrl from 'pdfjs-dist/legacy/build/pdf.worker.min.mjs?url';

import type { Response as GetDrawerResponse } from '@/types/contracts/gradebook/get_drawer';

GlobalWorkerOptions.workerSrc = pdfWorkerUrl;

type SubmissionAttachmentRow = NonNullable<
	NonNullable<GetDrawerResponse['selected_submission']>['attachments']
>[number];

type AnnotationReadinessPayload = NonNullable<
	NonNullable<GetDrawerResponse['selected_submission']>['annotation_readiness']
>;

type PdfLoadingTask = ReturnType<typeof getDocument>;
type LoadedPdfDocument = Awaited<PdfLoadingTask['promise']>;
type PdfRenderTaskLike = {
	cancel: () => void;
	promise: Promise<unknown>;
};

type AnnotationTool = 'browse' | 'point' | 'rect';
type AnnotationPoint = {
	x: number;
	y: number;
};
type AnnotationRect = {
	x: number;
	y: number;
	width: number;
	height: number;
};
type DraftAnnotation = {
	id: string;
	kind: 'point' | 'rect' | 'page';
	page: number;
	comment: string;
	point?: AnnotationPoint;
	rect?: AnnotationRect;
};
type PendingRectDraft = {
	start: AnnotationPoint;
	end: AnnotationPoint;
};

const props = defineProps<{
	attachment: SubmissionAttachmentRow;
	annotationReadiness?: AnnotationReadinessPayload | null;
}>();

const canvasRef = ref<HTMLCanvasElement | null>(null);
const viewerHostRef = ref<HTMLDivElement | null>(null);
const pageSurfaceRef = ref<HTMLDivElement | null>(null);

const currentPage = ref(1);
const pageCount = ref(0);
const zoomFactor = ref(1);
const isDocumentLoading = ref(false);
const isPageRendering = ref(false);
const viewerError = ref('');

const selectedTool = ref<AnnotationTool>('browse');
const draftAnnotations = ref<DraftAnnotation[]>([]);
const selectedDraftId = ref<string | null>(null);
const pendingRect = ref<PendingRectDraft | null>(null);
const draftSequence = ref(0);
const ignoreNextSurfaceClick = ref(false);

const sourcePdfUrl = computed(
	() => props.attachment.open_url || props.annotationReadiness?.open_url || null
);

const showInlinePreviewFallback = computed(
	() =>
		Boolean(props.attachment.preview_url) &&
		props.attachment.preview_status === 'ready' &&
		(pageCount.value === 0 || Boolean(viewerError.value))
);

const hasRenderedPage = computed(() => pageCount.value > 0 && !viewerError.value);
const canAnnotateCurrentPage = computed(() => hasRenderedPage.value && pageCount.value > 0);

const previewActionLabel = computed(() =>
	props.attachment.preview_status === 'ready' ? 'Open preview' : 'Try preview'
);

const currentPageLabel = computed(() => {
	if (!pageCount.value) return '1 of —';
	return `${currentPage.value} of ${pageCount.value}`;
});

const zoomLabel = computed(() => `${Math.round(zoomFactor.value * 100)}%`);

const canGoPreviousPage = computed(
	() => pageCount.value > 0 && currentPage.value > 1 && !isDocumentLoading.value
);

const canGoNextPage = computed(
	() => pageCount.value > 0 && currentPage.value < pageCount.value && !isDocumentLoading.value
);

const canAdjustZoom = computed(() => pageCount.value > 0 && !isDocumentLoading.value);

const selectedDraft = computed(
	() => draftAnnotations.value.find(draft => draft.id === selectedDraftId.value) || null
);

const draftCountLabel = computed(() => {
	const count = draftAnnotations.value.length;
	return count === 1 ? '1 draft' : `${count} drafts`;
});

const pointDraftsForCurrentPage = computed(() =>
	draftAnnotations.value.filter(
		draft => draft.page === currentPage.value && draft.kind === 'point' && Boolean(draft.point)
	)
);

const rectDraftsForCurrentPage = computed(() =>
	draftAnnotations.value.filter(
		draft => draft.page === currentPage.value && draft.kind === 'rect' && Boolean(draft.rect)
	)
);

const pendingRectStyle = computed(() => {
	if (!pendingRect.value) return null;
	return rectStyle(
		enforceMinimumRect(normalizeRect(pendingRect.value.start, pendingRect.value.end)),
		true
	);
});

const viewerSurfaceLabel = computed(() => {
	if (viewerError.value) {
		return showInlinePreviewFallback.value ? 'Preview fallback' : 'Source PDF fallback';
	}
	if (isDocumentLoading.value) return 'Loading PDF';
	if (draftAnnotations.value.length) return 'Draft overlay active';
	if (hasRenderedPage.value) return 'Read-only pdf.js viewer';
	return 'Governed PDF viewer';
});

const viewerLoadingLabel = computed(() => {
	if (isDocumentLoading.value) return 'Loading governed source PDF...';
	return 'Rendering PDF page...';
});

const showViewerLoadingBanner = computed(
	() => isDocumentLoading.value || (isPageRendering.value && hasRenderedPage.value)
);

const workspaceMessage = computed(() => {
	if (draftAnnotations.value.length) {
		return `Session-local point, area, and page draft annotations are available for this governed PDF. ${draftCountLabel.value} currently active.`;
	}
	if (props.annotationReadiness?.message) {
		return props.annotationReadiness.message;
	}
	if (hasRenderedPage.value) {
		return 'Read-only pdf.js rendering is ready for this governed PDF evidence.';
	}
	if (showInlinePreviewFallback.value) {
		return 'The drawer is showing the governed preview derivative while the source PDF viewer is unavailable.';
	}
	return 'Open the governed source PDF while inline rendering is unavailable.';
});

const overlayGuidance = computed(() => {
	if (!canAnnotateCurrentPage.value) {
		return 'The source PDF viewer must finish loading before local point, area, or page drafts are available.';
	}
	if (selectedTool.value === 'point') {
		return 'Click once on the page to drop a draft point comment anchor.';
	}
	if (selectedTool.value === 'rect') {
		return 'Drag on the page to create a draft area comment anchor.';
	}
	if (draftAnnotations.value.length) {
		return 'Select a draft on the page or from the right panel to keep refining its note.';
	}
	return 'Use point, area, or page comments to draft local annotation anchors before structured feedback persistence lands.';
});

const overlayCursorClass = computed(() => {
	if (selectedTool.value === 'point' || selectedTool.value === 'rect') {
		return 'cursor-crosshair';
	}
	return 'cursor-default';
});

const pageCommentButtonClass = computed(() =>
	canAnnotateCurrentPage.value
		? 'bg-gray-100 text-ink/65 hover:bg-gray-200 hover:text-ink'
		: 'bg-gray-100 text-ink/40'
);

const viewerEmptyTitle = computed(() =>
	viewerError.value ? 'Source PDF viewer unavailable' : 'Preparing PDF workspace'
);

const emptyDraftMessage = computed(() => {
	if (!canAnnotateCurrentPage.value) {
		return 'Draft annotations unlock after the governed PDF finishes loading in the drawer.';
	}
	return 'Choose Point comment, Area comment, or Add page comment to start a session-local draft.';
});

const selectedDraftAnchorSummary = computed(() => {
	if (!selectedDraft.value) return '';
	if (selectedDraft.value.kind === 'point' && selectedDraft.value.point) {
		return `Point anchor at ${formatPercent(selectedDraft.value.point.x)} across and ${formatPercent(selectedDraft.value.point.y)} down the current page.`;
	}
	if (selectedDraft.value.kind === 'rect' && selectedDraft.value.rect) {
		return `Area anchor starts ${formatPercent(selectedDraft.value.rect.x)} across and ${formatPercent(selectedDraft.value.rect.y)} down the page, spanning ${formatPercent(selectedDraft.value.rect.width)} by ${formatPercent(selectedDraft.value.rect.height)}.`;
	}
	return 'Page-level draft with no local coordinate anchor yet.';
});

const fallbackMessage = computed(() => {
	if (viewerError.value) {
		return viewerError.value;
	}
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

let activeLoadGeneration = 0;
let activeAbortController: AbortController | null = null;
let activePdfLoadingTask: PdfLoadingTask | null = null;
let activePdfDocument: LoadedPdfDocument | null = null;
let activeRenderTask: PdfRenderTaskLike | null = null;

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

function formatPercent(value: number) {
	return `${Math.round(value * 100)}%`;
}

function toolButtonClass(tool: AnnotationTool) {
	if (selectedTool.value === tool) {
		return 'bg-canopy text-white shadow-sm';
	}
	return 'bg-gray-100 text-ink/65 hover:bg-gray-200 hover:text-ink';
}

function kindLabel(kind: DraftAnnotation['kind']) {
	if (kind === 'point') return 'Point comment';
	if (kind === 'rect') return 'Area comment';
	return 'Page comment';
}

function draftPlaceholder(draft: DraftAnnotation) {
	if (draft.kind === 'point') return 'Add the draft teaching note for this point anchor.';
	if (draft.kind === 'rect') return 'Describe what this draft area comment should call out.';
	return 'Add the draft page-level note for this page.';
}

function goToPreviousPage() {
	if (!canGoPreviousPage.value) return;
	currentPage.value -= 1;
}

function goToNextPage() {
	if (!canGoNextPage.value) return;
	currentPage.value += 1;
}

function zoomOut() {
	if (!canAdjustZoom.value) return;
	zoomFactor.value = Math.max(0.75, Number((zoomFactor.value - 0.1).toFixed(2)));
}

function zoomIn() {
	if (!canAdjustZoom.value) return;
	zoomFactor.value = Math.min(2.5, Number((zoomFactor.value + 0.1).toFixed(2)));
}

function resetZoom() {
	if (!canAdjustZoom.value) return;
	zoomFactor.value = 1;
}

function clearCanvas() {
	const canvas = canvasRef.value;
	if (!canvas) return;
	const context = canvas.getContext('2d');
	if (!context) return;
	context.setTransform(1, 0, 0, 1, 0, 0);
	context.clearRect(0, 0, canvas.width, canvas.height);
	canvas.width = 0;
	canvas.height = 0;
	canvas.style.width = '0px';
	canvas.style.height = '0px';
}

function resetDraftState() {
	selectedTool.value = 'browse';
	draftAnnotations.value = [];
	selectedDraftId.value = null;
	pendingRect.value = null;
	draftSequence.value = 0;
	ignoreNextSurfaceClick.value = false;
}

function cancelActivePdfWork() {
	activeAbortController?.abort();
	activeAbortController = null;
	activeRenderTask?.cancel();
	activeRenderTask = null;
	activePdfLoadingTask?.destroy?.();
	activePdfLoadingTask = null;
	if (activePdfDocument) {
		void activePdfDocument.destroy();
		activePdfDocument = null;
	}
	clearCanvas();
	isPageRendering.value = false;
}

function isCancellationError(error: unknown): boolean {
	return (
		error instanceof Error &&
		(error.name === 'AbortError' || error.name === 'RenderingCancelledException')
	);
}

function formatErrorMessage(error: unknown): string {
	if (error instanceof Error && error.message) return error.message;
	return 'The governed PDF could not be loaded in the drawer. Open the source PDF to continue review.';
}

function clampUnit(value: number) {
	return Math.min(1, Math.max(0, value));
}

function normalizePointerPosition(event: MouseEvent | PointerEvent): AnnotationPoint | null {
	const rect = pageSurfaceRef.value?.getBoundingClientRect();
	if (!rect || rect.width <= 0 || rect.height <= 0) return null;
	return {
		x: clampUnit((event.clientX - rect.left) / rect.width),
		y: clampUnit((event.clientY - rect.top) / rect.height),
	};
}

function normalizeRect(start: AnnotationPoint, end: AnnotationPoint): AnnotationRect {
	const left = Math.min(start.x, end.x);
	const top = Math.min(start.y, end.y);
	const right = Math.max(start.x, end.x);
	const bottom = Math.max(start.y, end.y);
	return {
		x: left,
		y: top,
		width: right - left,
		height: bottom - top,
	};
}

function enforceMinimumRect(rect: AnnotationRect, minimum = 0.08): AnnotationRect {
	let width = Math.max(rect.width, minimum);
	let height = Math.max(rect.height, minimum);
	const centerX = rect.x + rect.width / 2;
	const centerY = rect.y + rect.height / 2;
	let x = clampUnit(centerX - width / 2);
	let y = clampUnit(centerY - height / 2);
	if (x + width > 1) x = Math.max(0, 1 - width);
	if (y + height > 1) y = Math.max(0, 1 - height);
	width = Math.min(width, 1);
	height = Math.min(height, 1);
	return { x, y, width, height };
}

function pointStyle(point?: AnnotationPoint): CSSProperties {
	if (!point) return {};
	return {
		left: `${point.x * 100}%`,
		top: `${point.y * 100}%`,
	};
}

function rectStyle(rect?: AnnotationRect, dashed = false): CSSProperties {
	if (!rect) return {};
	return {
		left: `${rect.x * 100}%`,
		top: `${rect.y * 100}%`,
		width: `${rect.width * 100}%`,
		height: `${rect.height * 100}%`,
		borderStyle: dashed ? 'dashed' : 'solid',
	};
}

function nextDraftId() {
	draftSequence.value += 1;
	return `draft-${draftSequence.value}`;
}

function draftOrdinal(draftId: string) {
	return draftAnnotations.value.findIndex(draft => draft.id === draftId) + 1;
}

function selectDraft(draftId: string) {
	const draft = draftAnnotations.value.find(row => row.id === draftId);
	if (!draft) return;
	selectedDraftId.value = draft.id;
	selectedTool.value = 'browse';
	if (draft.page !== currentPage.value && draft.page <= pageCount.value) {
		currentPage.value = draft.page;
	}
}

function addDraft(draft: Omit<DraftAnnotation, 'id'>) {
	const nextDraft: DraftAnnotation = {
		id: nextDraftId(),
		...draft,
	};
	draftAnnotations.value = [...draftAnnotations.value, nextDraft];
	selectedDraftId.value = nextDraft.id;
	selectedTool.value = 'browse';
}

function addPageCommentDraft() {
	if (!canAnnotateCurrentPage.value) return;
	addDraft({
		kind: 'page',
		page: currentPage.value,
		comment: '',
	});
}

function handleSurfaceClick(event: MouseEvent) {
	if (!canAnnotateCurrentPage.value) return;
	if (ignoreNextSurfaceClick.value) {
		ignoreNextSurfaceClick.value = false;
		return;
	}
	if (selectedTool.value === 'browse') {
		selectedDraftId.value = null;
		return;
	}
	if (selectedTool.value !== 'point') return;
	const point = normalizePointerPosition(event);
	if (!point) return;
	addDraft({
		kind: 'point',
		page: currentPage.value,
		point,
		comment: '',
	});
}

function handleSurfacePointerDown(event: PointerEvent) {
	if (!canAnnotateCurrentPage.value || selectedTool.value !== 'rect') return;
	const startPoint = normalizePointerPosition(event);
	if (!startPoint) return;
	pendingRect.value = {
		start: startPoint,
		end: startPoint,
	};
	const target = event.currentTarget as HTMLElement | null;
	target?.setPointerCapture?.(event.pointerId);
	event.preventDefault();
}

function handleSurfacePointerMove(event: PointerEvent) {
	if (!pendingRect.value) return;
	const nextPoint = normalizePointerPosition(event);
	if (!nextPoint) return;
	pendingRect.value = {
		...pendingRect.value,
		end: nextPoint,
	};
}

function handleSurfacePointerUp(event: PointerEvent) {
	if (!pendingRect.value) return;
	const target = event.currentTarget as HTMLElement | null;
	target?.releasePointerCapture?.(event.pointerId);
	const nextPoint = normalizePointerPosition(event) || pendingRect.value.end;
	const nextRect = enforceMinimumRect(normalizeRect(pendingRect.value.start, nextPoint));
	pendingRect.value = null;
	ignoreNextSurfaceClick.value = true;
	addDraft({
		kind: 'rect',
		page: currentPage.value,
		rect: nextRect,
		comment: '',
	});
}

function cancelPendingRect() {
	pendingRect.value = null;
}

function onSelectedDraftCommentChanged(event: Event) {
	if (!selectedDraft.value) return;
	const nextComment = (event.target as HTMLTextAreaElement).value;
	draftAnnotations.value = draftAnnotations.value.map(draft =>
		draft.id === selectedDraft.value?.id ? { ...draft, comment: nextComment } : draft
	);
}

function removeSelectedDraft() {
	if (!selectedDraft.value) return;
	const removedId = selectedDraft.value.id;
	draftAnnotations.value = draftAnnotations.value.filter(draft => draft.id !== removedId);
	selectedDraftId.value = draftAnnotations.value[0]?.id || null;
	selectedTool.value = 'browse';
}

async function loadPdfDocument() {
	const sourceUrl = sourcePdfUrl.value;
	const loadGeneration = activeLoadGeneration + 1;
	activeLoadGeneration = loadGeneration;

	cancelActivePdfWork();
	viewerError.value = '';
	pageCount.value = 0;
	currentPage.value = 1;
	isDocumentLoading.value = Boolean(sourceUrl);

	if (!sourceUrl) {
		viewerError.value =
			'This governed PDF does not currently expose a source-file route. Open the preview if available.';
		isDocumentLoading.value = false;
		return;
	}

	const abortController = new AbortController();
	activeAbortController = abortController;

	try {
		const response = await fetch(sourceUrl, {
			credentials: 'include',
			signal: abortController.signal,
		});
		if (!response.ok) {
			throw new Error(`The governed PDF request failed with status ${response.status}.`);
		}
		const pdfBytes = new Uint8Array(await response.arrayBuffer());
		if (loadGeneration !== activeLoadGeneration) return;

		const loadingTask = getDocument({ data: pdfBytes });
		activePdfLoadingTask = loadingTask;

		const pdfDocument = await loadingTask.promise;
		if (loadGeneration !== activeLoadGeneration) {
			void pdfDocument.destroy();
			return;
		}

		activePdfDocument = pdfDocument;
		activePdfLoadingTask = null;
		pageCount.value = pdfDocument.numPages;
		currentPage.value = 1;

		await nextTick();
		await renderCurrentPage(loadGeneration);
	} catch (error) {
		if (loadGeneration !== activeLoadGeneration || isCancellationError(error)) return;
		viewerError.value = formatErrorMessage(error);
		pageCount.value = 0;
		clearCanvas();
	} finally {
		if (loadGeneration === activeLoadGeneration) {
			isDocumentLoading.value = false;
		}
		if (activeAbortController === abortController) {
			activeAbortController = null;
		}
	}
}

async function renderCurrentPage(loadGeneration = activeLoadGeneration) {
	if (!activePdfDocument || !canvasRef.value || !viewerHostRef.value) return;

	activeRenderTask?.cancel();
	activeRenderTask = null;
	isPageRendering.value = true;

	try {
		const page = await activePdfDocument.getPage(currentPage.value);
		if (loadGeneration !== activeLoadGeneration) return;

		const baseViewport = page.getViewport({ scale: 1 });
		const hostWidth = Math.max((viewerHostRef.value.clientWidth || baseViewport.width) - 32, 240);
		const fitScale = hostWidth / baseViewport.width;
		const renderScale = Math.max(0.5, fitScale * zoomFactor.value);
		const viewport = page.getViewport({ scale: renderScale });

		const canvas = canvasRef.value;
		const canvasContext = canvas.getContext('2d');
		if (!canvasContext) {
			throw new Error('Canvas rendering is unavailable in this browser context.');
		}

		const pixelRatio = typeof window !== 'undefined' ? window.devicePixelRatio || 1 : 1;
		canvas.width = Math.floor(viewport.width * pixelRatio);
		canvas.height = Math.floor(viewport.height * pixelRatio);
		canvas.style.width = `${viewport.width}px`;
		canvas.style.height = `${viewport.height}px`;

		canvasContext.setTransform(1, 0, 0, 1, 0, 0);
		canvasContext.clearRect(0, 0, canvas.width, canvas.height);
		canvasContext.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);

		const renderTask = page.render({
			canvas,
			canvasContext,
			viewport,
		}) as PdfRenderTaskLike;
		activeRenderTask = renderTask;
		await renderTask.promise;
		if (loadGeneration !== activeLoadGeneration) return;

		viewerError.value = '';
	} catch (error) {
		if (loadGeneration !== activeLoadGeneration || isCancellationError(error)) return;
		viewerError.value = formatErrorMessage(error);
		pageCount.value = 0;
		clearCanvas();
	} finally {
		if (loadGeneration === activeLoadGeneration) {
			isPageRendering.value = false;
		}
		if (activeRenderTask) {
			activeRenderTask = null;
		}
	}
}

function handleWindowResize() {
	if (!activePdfDocument || !pageCount.value || isDocumentLoading.value) return;
	void renderCurrentPage();
}

watch(
	[() => props.attachment.row_name ?? null, sourcePdfUrl],
	() => {
		resetDraftState();
		zoomFactor.value = 1;
		void loadPdfDocument();
	},
	{ immediate: true }
);

watch([currentPage, zoomFactor], () => {
	if (!activePdfDocument || !pageCount.value || isDocumentLoading.value) return;
	void renderCurrentPage();
});

onMounted(() => {
	window.addEventListener('resize', handleWindowResize);
});

onBeforeUnmount(() => {
	activeLoadGeneration += 1;
	window.removeEventListener('resize', handleWindowResize);
	cancelActivePdfWork();
});
</script>
