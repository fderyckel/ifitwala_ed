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
					<span class="text-sm font-medium text-ink/70"> Page {{ currentPageLabel }} </span>
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
					<canvas
						ref="canvasRef"
						:aria-label="`${attachment.file_name || 'PDF attachment'} PDF page`"
						class="max-w-full rounded-xl bg-white shadow-sm ring-1 ring-black/5"
					/>
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
	</section>
</template>

<script setup lang="ts">
import { Badge, Spinner } from 'frappe-ui';
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
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

const props = defineProps<{
	attachment: SubmissionAttachmentRow;
	annotationReadiness?: AnnotationReadinessPayload | null;
}>();

const canvasRef = ref<HTMLCanvasElement | null>(null);
const viewerHostRef = ref<HTMLDivElement | null>(null);

const currentPage = ref(1);
const pageCount = ref(0);
const zoomFactor = ref(1);
const isDocumentLoading = ref(false);
const isPageRendering = ref(false);
const viewerError = ref('');

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

const viewerSurfaceLabel = computed(() => {
	if (viewerError.value) {
		return showInlinePreviewFallback.value ? 'Preview fallback' : 'Source PDF fallback';
	}
	if (isDocumentLoading.value) return 'Loading PDF';
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

const viewerEmptyTitle = computed(() =>
	viewerError.value ? 'Source PDF viewer unavailable' : 'Preparing PDF workspace'
);

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
