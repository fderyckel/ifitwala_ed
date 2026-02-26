// ifitwala_ed/ui-spa/src/composables/useAnalyticsSnapshotExport.ts

import { computed, nextTick, ref } from 'vue';
import { apiMethod } from '@/lib/frappe';

type Primitive = string | number | boolean | null | undefined;
type FilterValue = Primitive | Primitive[];
type FilterRecord = Record<string, FilterValue>;
type FilterRow = { key: string; value: string };

type SnapshotCanvasPayload = {
	canvas: HTMLCanvasElement;
	capturedAt: string;
	timezone: string;
	filters: FilterRow[];
};

export type UseAnalyticsSnapshotExportOptions = {
	dashboardSlug: string;
	dashboardTitle: string;
	getTarget: () => HTMLElement | null;
	getFilters: () => FilterRecord;
};

type ExportDashboardPdfResponse = {
	file_name: string;
	content_base64: string;
};

const MAX_CAPTURE_WIDTH = 2200;
const MAX_CAPTURE_HEIGHT = 4200;
const CAPTURE_SCALE = 1.25;
const CAPTURE_TIMEOUT_MS = 20000;

function resolveSiteTimezone(): string {
	const tzFromBoot =
		(window as any)?.frappe?.boot?.time_zone || (window as any)?.frappe?.boot?.timezone || '';
	const cleaned = String(tzFromBoot || '').trim();
	return cleaned || Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
}

function formatSnapshotTimestamp(value: Date, timezone: string): string {
	return new Intl.DateTimeFormat(undefined, {
		timeZone: timezone,
		year: 'numeric',
		month: 'short',
		day: '2-digit',
		hour: '2-digit',
		minute: '2-digit',
		second: '2-digit',
		hour12: false,
	}).format(value);
}

function formatFileStamp(value: Date, timezone: string): string {
	const parts = new Intl.DateTimeFormat('en-GB', {
		timeZone: timezone,
		year: 'numeric',
		month: '2-digit',
		day: '2-digit',
		hour: '2-digit',
		minute: '2-digit',
		second: '2-digit',
		hour12: false,
	}).formatToParts(value);
	const byType: Record<string, string> = {};
	for (const part of parts) {
		byType[part.type] = part.value;
	}
	const year = byType.year || '0000';
	const month = byType.month || '00';
	const day = byType.day || '00';
	const hour = byType.hour || '00';
	const minute = byType.minute || '00';
	const second = byType.second || '00';
	return `${year}${month}${day}-${hour}${minute}${second}`;
}

function sanitizeForFileName(value: string): string {
	const cleaned = (value || '').trim().toLowerCase().replace(/[^a-z0-9._-]+/g, '-');
	return cleaned.replace(/^-+|-+$/g, '') || 'analytics';
}

function toFilterRows(filters: FilterRecord): FilterRow[] {
	const rows: FilterRow[] = [];

	for (const [key, raw] of Object.entries(filters || {})) {
		if (raw === null || raw === undefined || raw === '') {
			rows.push({ key, value: 'All' });
			continue;
		}

		if (Array.isArray(raw)) {
			const values = raw.filter(value => value !== null && value !== undefined && value !== '');
			rows.push({
				key,
				value: values.length ? values.map(value => String(value)).join(', ') : 'All',
			});
			continue;
		}

		rows.push({ key, value: String(raw) });
	}

	return rows;
}

function drawMetadataHeader(
	canvas: HTMLCanvasElement,
	{
		title,
		capturedAt,
		timezone,
		filters,
	}: {
		title: string;
		capturedAt: string;
		timezone: string;
		filters: FilterRow[];
	}
): void {
	const ctx = canvas.getContext('2d');
	if (!ctx) return;

	const contentFilters = filters.length ? filters : [{ key: 'Filters', value: 'No filters applied' }];
	const headerHeight = 110 + contentFilters.length * 24;
	const fullWidth = canvas.width;

	ctx.fillStyle = '#f8fafc';
	ctx.fillRect(0, 0, fullWidth, headerHeight);

	ctx.strokeStyle = '#dbe4ef';
	ctx.lineWidth = 1;
	ctx.strokeRect(0.5, 0.5, fullWidth - 1, headerHeight - 1);

	ctx.fillStyle = '#0f172a';
	ctx.font = '700 26px "Segoe UI", Arial, sans-serif';
	ctx.fillText(title, 24, 38);

	ctx.font = '500 16px "Segoe UI", Arial, sans-serif';
	ctx.fillStyle = '#334155';
	ctx.fillText(`Snapshot: ${capturedAt} (${timezone})`, 24, 66);

	ctx.font = '600 14px "Segoe UI", Arial, sans-serif';
	ctx.fillStyle = '#0f172a';
	ctx.fillText('Filters', 24, 90);

	ctx.font = '500 13px "Segoe UI", Arial, sans-serif';
	contentFilters.forEach((row, index) => {
		const y = 112 + index * 24;
		ctx.fillStyle = '#334155';
		ctx.fillText(`${row.key}:`, 24, y);
		ctx.fillStyle = '#0f172a';
		ctx.fillText(row.value, 190, y);
	});

}

function triggerDownload(dataUrl: string, filename: string) {
	const link = document.createElement('a');
	link.href = dataUrl;
	link.download = filename;
	link.style.display = 'none';
	document.body.appendChild(link);
	try {
		link.click();
	} finally {
		document.body.removeChild(link);
	}
}

function triggerBlobDownload(blob: Blob, filename: string) {
	const url = URL.createObjectURL(blob);
	const link = document.createElement('a');
	link.href = url;
	link.download = filename;
	link.style.display = 'none';
	document.body.appendChild(link);
	try {
		link.click();
	} finally {
		document.body.removeChild(link);
		window.setTimeout(() => URL.revokeObjectURL(url), 1200);
	}
}

function base64ToBlob(base64Data: string, mimeType: string) {
	const binary = atob(base64Data);
	const bytes = new Uint8Array(binary.length);
	for (let index = 0; index < binary.length; index += 1) {
		bytes[index] = binary.charCodeAt(index);
	}
	return new Blob([bytes], { type: mimeType });
}

function messageForError(error: unknown, fallback: string): string {
	if (error instanceof Error && error.message) return error.message;
	if (typeof error === 'string' && error.trim()) return error.trim();
	return fallback;
}

async function withTimeout<T>(promise: Promise<T>, timeoutMs: number, timeoutMessage: string): Promise<T> {
	let timeoutId = 0;
	try {
		return await Promise.race([
			promise,
			new Promise<T>((_, reject) => {
				timeoutId = window.setTimeout(() => reject(new Error(timeoutMessage)), timeoutMs);
			}),
		]);
	} finally {
		if (timeoutId) window.clearTimeout(timeoutId);
	}
}

export function useAnalyticsSnapshotExport(options: UseAnalyticsSnapshotExportOptions) {
	const exportingPng = ref(false);
	const exportingPdf = ref(false);
	const exportLock = ref(false);
	const actionMessage = ref<string | null>(null);
	const isBusy = computed(() => exportingPng.value || exportingPdf.value);

	async function buildSnapshotCanvas(): Promise<SnapshotCanvasPayload> {
		const target = options.getTarget();
		if (!target) {
			throw new Error('No dashboard surface is available for export.');
		}

		const html2canvas = (await import('html2canvas')).default;
		const timezone = resolveSiteTimezone();
		const capturedAtDate = new Date();
		const capturedAt = formatSnapshotTimestamp(capturedAtDate, timezone);
		const filters = toFilterRows(options.getFilters());

		// Keep capture bounded to avoid browser memory pressure on long dashboards.
		const width = Math.min(
			Math.max(Math.ceil(target.getBoundingClientRect().width), Math.min(window.innerWidth, 1024)),
			MAX_CAPTURE_WIDTH
		);
		const measuredHeight = Math.max(
			Math.ceil(target.getBoundingClientRect().height),
			Math.min(window.innerHeight, 900)
		);
		const height = Math.min(measuredHeight, MAX_CAPTURE_HEIGHT);

		if (measuredHeight > MAX_CAPTURE_HEIGHT) {
			actionMessage.value =
				'Large dashboard detected. Export includes the first visible sections up to a safe height.';
		}

		await nextTick();
		const screenshot = await withTimeout(
			html2canvas(target, {
				backgroundColor: '#ffffff',
				scale: CAPTURE_SCALE,
				useCORS: true,
				width,
				height,
				windowWidth: width,
				windowHeight: height,
				scrollX: 0,
				scrollY: 0,
			}),
			CAPTURE_TIMEOUT_MS,
			'Snapshot capture timed out. Narrow filters or reduce the visible dashboard and retry.'
		);

		const composed = document.createElement('canvas');
		const metadataHeight = 110 + Math.max(filters.length, 1) * 24;
		composed.width = screenshot.width;
		composed.height = screenshot.height + metadataHeight;

		const ctx = composed.getContext('2d');
		if (!ctx) {
			throw new Error('Unable to prepare export image.');
		}

		drawMetadataHeader(composed, {
			title: options.dashboardTitle,
			capturedAt,
			timezone,
			filters,
		});
		ctx.drawImage(screenshot, 0, metadataHeight);

		return {
			canvas: composed,
			capturedAt,
			timezone,
			filters,
		};
	}

	async function exportPng() {
		if (isBusy.value || exportLock.value) return;
		exportingPng.value = true;
		exportLock.value = true;
		actionMessage.value = null;

		try {
			const snapshot = await buildSnapshotCanvas();
			const fileStamp = formatFileStamp(new Date(), snapshot.timezone);
			const slug = sanitizeForFileName(options.dashboardSlug);
			const dataUrl = snapshot.canvas.toDataURL('image/png');
			triggerDownload(dataUrl, `${slug}-${fileStamp}.png`);
			actionMessage.value = `PNG exported (${snapshot.capturedAt} ${snapshot.timezone}).`;
		} catch (error) {
			actionMessage.value = messageForError(
				error,
				'PNG export failed. Try reducing on-screen content and retry.'
			);
		} finally {
			exportingPng.value = false;
			exportLock.value = false;
		}
	}

	async function exportPdf() {
		if (isBusy.value || exportLock.value) return;
		exportingPdf.value = true;
		exportLock.value = true;
		actionMessage.value = null;

		try {
			const snapshot = await buildSnapshotCanvas();
			const fileStamp = formatFileStamp(new Date(), snapshot.timezone);
			const slug = sanitizeForFileName(options.dashboardSlug);
			const fileName = `${slug}-${fileStamp}.pdf`;
			const imageDataUrl = snapshot.canvas.toDataURL('image/png');

			const response = await apiMethod<ExportDashboardPdfResponse>(
				'ifitwala_ed.api.analytics_snapshot.export_dashboard_pdf',
				{
					payload: {
						title: options.dashboardTitle,
						file_name: fileName,
						captured_at: snapshot.capturedAt,
						timezone: snapshot.timezone,
						filters: snapshot.filters,
						image_data_url: imageDataUrl,
					},
				}
			);

			if (!response?.content_base64 || !response?.file_name) {
				throw new Error('PDF export returned an invalid response.');
			}

			const blob = base64ToBlob(response.content_base64, 'application/pdf');
			triggerBlobDownload(blob, response.file_name);
			actionMessage.value = `PDF exported (${snapshot.capturedAt} ${snapshot.timezone}).`;
		} catch (error) {
			actionMessage.value = messageForError(
				error,
				'PDF export failed. Try reducing on-screen content and retry.'
			);
		} finally {
			exportingPdf.value = false;
			exportLock.value = false;
		}
	}

	return {
		exportingPng,
		exportingPdf,
		actionMessage,
		isBusy,
		exportPng,
		exportPdf,
	};
}
