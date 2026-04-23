<template>
	<section class="overflow-hidden rounded-3xl border border-line-soft bg-white shadow-sm">
		<div class="border-b border-line-soft bg-surface-soft px-4 py-4">
			<div class="flex flex-wrap items-start justify-between gap-3">
				<div class="min-w-0">
					<p class="type-overline text-ink/55">Document Context</p>
					<h3 class="mt-2 type-body-strong text-ink">
						{{
							primaryAttachment?.display_name ||
							props.document?.submission.annotation_readiness?.attachment_file_name ||
							'Submitted evidence'
						}}
					</h3>
					<p class="mt-2 type-caption text-ink/70">
						{{ documentMessage }}
					</p>
				</div>
				<div class="flex flex-wrap gap-2">
					<span
						v-if="props.document?.submission.annotation_readiness?.preview_status"
						class="chip"
					>
						Preview {{ props.document?.submission.annotation_readiness?.preview_status }}
					</span>
					<span v-if="props.document?.submission.version" class="chip chip-focus">
						Version {{ props.document.submission.version }}
					</span>
					<span v-if="currentPageTotalLabel" class="chip">
						{{ currentPageTotalLabel }}
					</span>
				</div>
			</div>

			<div class="mt-4 flex flex-wrap gap-2">
				<a
					v-if="primaryAttachment?.preview_url"
					class="if-button if-button--secondary"
					:href="primaryAttachment.preview_url || undefined"
					target="_blank"
					rel="noreferrer"
				>
					Open preview
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

		<div v-if="hasRenderedPage" class="border-b border-line-soft bg-white px-4 py-3">
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

		<div class="relative min-h-[24rem] bg-gray-50/40">
			<div
				v-if="showViewerLoadingBanner"
				class="absolute inset-x-0 top-3 z-10 flex justify-center px-4"
			>
				<div
					class="inline-flex items-center gap-2 rounded-full border border-line-soft bg-white/95 px-4 py-2 type-caption text-ink shadow-sm"
				>
					<Spinner class="h-4 w-4" />
					<span>{{ viewerLoadingLabel }}</span>
				</div>
			</div>

			<div
				v-if="hasRenderedPage"
				ref="viewerHostRef"
				class="overflow-auto p-4 pt-14 md:p-6 md:pt-16"
			>
				<div class="mx-auto flex min-h-[20rem] w-full items-start justify-center">
					<div ref="pageSurfaceRef" class="relative inline-block">
						<canvas
							ref="canvasRef"
							:aria-label="`${primaryAttachment?.display_name || 'Submission'} PDF page`"
							class="block max-w-full rounded-2xl bg-white shadow-sm ring-1 ring-black/5"
						/>

						<div class="absolute inset-0">
							<button
								v-for="item in pointItemsForCurrentPage"
								:key="item.id || `${item.page}-${item.comment}`"
								type="button"
								class="absolute flex h-7 w-7 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border border-white bg-jacaranda text-xs font-semibold text-white shadow-sm ring-2 ring-jacaranda/20 transition hover:scale-105"
								:class="selectedItemId === item.id ? 'ring-4 ring-jacaranda/30' : ''"
								:style="pointStyle(item.anchor.kind === 'point' ? item.anchor.point : undefined)"
								@click.stop="emitSelect(item.id)"
							>
								{{ itemOrdinal(item.id) }}
							</button>

							<button
								v-for="item in rectItemsForCurrentPage"
								:key="item.id || `${item.page}-${item.comment}`"
								type="button"
								class="absolute border-2 border-jacaranda/80 bg-jacaranda/10 transition hover:bg-jacaranda/15"
								:class="selectedItemId === item.id ? 'ring-4 ring-jacaranda/20' : ''"
								:style="rectStyle(item.anchor.kind === 'rect' ? item.anchor.rect : undefined)"
								@click.stop="emitSelect(item.id)"
							>
								<span
									class="absolute -left-2 -top-2 flex h-6 min-w-6 items-center justify-center rounded-full border border-white bg-jacaranda px-1 text-xs font-semibold text-white shadow-sm"
								>
									{{ itemOrdinal(item.id) }}
								</span>
							</button>
						</div>
					</div>
				</div>

				<div
					v-if="pageItemsForCurrentPage.length"
					class="mx-auto mt-4 max-w-3xl rounded-2xl border border-line-soft bg-white p-4"
				>
					<div class="flex flex-wrap items-center justify-between gap-3">
						<div>
							<p class="type-caption text-ink/60">Page comments on this page</p>
							<p class="mt-1 type-body-strong text-ink">
								{{ pageItemsForCurrentPage.length }} page-level notes
							</p>
						</div>
						<span class="chip">{{ currentPageTotalLabel }}</span>
					</div>
					<div class="mt-3 flex flex-wrap gap-2">
						<button
							v-for="item in pageItemsForCurrentPage"
							:key="item.id || `${item.page}-${item.comment}`"
							type="button"
							class="rounded-full border px-3 py-1.5 type-caption transition"
							:class="
								selectedItemId === item.id
									? 'border-jacaranda/40 bg-jacaranda/10 text-jacaranda'
									: 'border-line-soft bg-surface-soft text-ink/70 hover:border-jacaranda/30 hover:text-ink'
							"
							@click="emitSelect(item.id)"
						>
							{{ item.comment || 'Open page note' }}
						</button>
					</div>
				</div>
			</div>

			<div v-else-if="primaryAttachment?.preview_url" class="p-4 pt-14">
				<AttachmentPreviewCard
					v-if="primaryAttachment"
					:attachment="primaryAttachment"
					variant="evidence"
					:title="primaryAttachment.display_name || 'Submitted evidence'"
					:description="props.document?.submission.annotation_readiness?.message || null"
				/>
			</div>

			<div v-else class="flex min-h-[20rem] items-center justify-center px-6 py-12 text-center">
				<div>
					<p class="type-body-strong text-ink">{{ viewerEmptyTitle }}</p>
					<p class="mt-2 type-body text-ink/70">
						{{ fallbackMessage }}
					</p>
				</div>
			</div>
		</div>
	</section>
</template>

<script setup lang="ts">
import {
	computed,
	nextTick,
	onBeforeUnmount,
	onMounted,
	ref,
	watch,
	type CSSProperties,
} from 'vue';
import { Spinner } from 'frappe-ui';
import { GlobalWorkerOptions, getDocument } from 'pdfjs-dist/legacy/build/pdf.mjs';
import pdfWorkerUrl from 'pdfjs-dist/legacy/build/pdf.worker.min.mjs?url';

import AttachmentPreviewCard from '@/components/attachments/AttachmentPreviewCard.vue';
import type { ReleasedFeedbackDetail } from '@/types/contracts/assessment/released_feedback_detail';
import type { FeedbackWorkspaceItem } from '@/types/contracts/gradebook/feedback_workspace';

GlobalWorkerOptions.workerSrc = pdfWorkerUrl;

type PdfLoadingTask = ReturnType<typeof getDocument>;
type LoadedPdfDocument = Awaited<PdfLoadingTask['promise']>;
type PdfRenderTaskLike = {
	cancel: () => void;
	promise: Promise<unknown>;
};

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

const props = defineProps<{
	document?: ReleasedFeedbackDetail['document'] | null;
	items?: FeedbackWorkspaceItem[];
	selectedItemId?: string | null;
}>();

const emit = defineEmits<{
	(e: 'select-item', itemId: string | null): void;
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

const primaryAttachment = computed(
	() => props.document?.primary_attachment?.attachment_preview || null
);
const sourcePdfUrl = computed(
	() =>
		props.document?.primary_attachment?.open_url ||
		primaryAttachment.value?.open_url ||
		props.document?.submission.annotation_readiness?.open_url ||
		null
);
const visualItems = computed(() =>
	(props.items || []).filter(
		item => item.kind === 'point' || item.kind === 'rect' || item.kind === 'page'
	)
);
const selectedItem = computed(
	() => visualItems.value.find(item => item.id === props.selectedItemId) || null
);

const pointItemsForCurrentPage = computed(() =>
	visualItems.value.filter(
		item =>
			item.page === currentPage.value && item.kind === 'point' && item.anchor.kind === 'point'
	)
);
const rectItemsForCurrentPage = computed(() =>
	visualItems.value.filter(
		item => item.page === currentPage.value && item.kind === 'rect' && item.anchor.kind === 'rect'
	)
);
const pageItemsForCurrentPage = computed(() =>
	visualItems.value.filter(item => item.page === currentPage.value && item.kind === 'page')
);

const hasRenderedPage = computed(() => pageCount.value > 0 && !viewerError.value);
const currentPageTotalLabel = computed(() =>
	pageCount.value ? `Page ${currentPage.value} of ${pageCount.value}` : ''
);
const canGoPreviousPage = computed(
	() => pageCount.value > 0 && currentPage.value > 1 && !isDocumentLoading.value
);
const canGoNextPage = computed(
	() => pageCount.value > 0 && currentPage.value < pageCount.value && !isDocumentLoading.value
);
const canAdjustZoom = computed(() => pageCount.value > 0 && !isDocumentLoading.value);
const zoomLabel = computed(() => `${Math.round(zoomFactor.value * 100)}%`);
const showViewerLoadingBanner = computed(
	() => isDocumentLoading.value || (isPageRendering.value && hasRenderedPage.value)
);
const viewerLoadingLabel = computed(() =>
	isDocumentLoading.value ? 'Loading source PDF...' : 'Rendering page...'
);
const viewerEmptyTitle = computed(() =>
	viewerError.value ? 'Document viewer unavailable' : 'Document viewer not available'
);
const fallbackMessage = computed(
	() =>
		viewerError.value ||
		props.document?.submission.annotation_readiness?.message ||
		'Open the source document when preview is available.'
);
const documentMessage = computed(() => {
	if (hasRenderedPage.value) {
		return 'The original submitted PDF is shown here with released feedback anchors layered on top.';
	}
	return (
		props.document?.submission.annotation_readiness?.message ||
		'Open the released evidence context from the source PDF when needed.'
	);
});

let activeLoadGeneration = 0;
let activeAbortController: AbortController | null = null;
let activePdfLoadingTask: PdfLoadingTask | null = null;
let activePdfDocument: LoadedPdfDocument | null = null;
let activeRenderTask: PdfRenderTaskLike | null = null;

function emitSelect(itemId: string | null | undefined) {
	emit('select-item', itemId || null);
}

function goToPreviousPage() {
	if (canGoPreviousPage.value) currentPage.value -= 1;
}

function goToNextPage() {
	if (canGoNextPage.value) currentPage.value += 1;
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

function pointStyle(point?: AnnotationPoint): CSSProperties {
	if (!point) return {};
	return {
		left: `${point.x * 100}%`,
		top: `${point.y * 100}%`,
	};
}

function rectStyle(rect?: AnnotationRect): CSSProperties {
	if (!rect) return {};
	return {
		left: `${rect.x * 100}%`,
		top: `${rect.y * 100}%`,
		width: `${rect.width * 100}%`,
		height: `${rect.height * 100}%`,
	};
}

function itemOrdinal(itemId?: string | null) {
	if (!itemId) return '•';
	return visualItems.value.findIndex(item => item.id === itemId) + 1;
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
	return 'The submitted PDF could not be loaded for inline reading.';
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
			throw new Error(`The source PDF request failed with status ${response.status}.`);
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
		currentPage.value = selectedItem.value?.page || 1;

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
	() => sourcePdfUrl.value,
	() => {
		zoomFactor.value = 1;
		void loadPdfDocument();
	},
	{ immediate: true }
);

watch(
	() => props.selectedItemId,
	() => {
		const targetPage = selectedItem.value?.page;
		if (!targetPage || targetPage === currentPage.value || targetPage > pageCount.value) return;
		currentPage.value = targetPage;
	}
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
