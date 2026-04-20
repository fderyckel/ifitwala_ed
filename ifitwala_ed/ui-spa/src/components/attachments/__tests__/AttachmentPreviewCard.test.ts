import { afterEach, describe, expect, it } from 'vitest';
import { createApp, defineComponent, h, nextTick, type App } from 'vue';

import AttachmentPreviewCard from '@/components/attachments/AttachmentPreviewCard.vue';

const cleanupFns: Array<() => void> = [];

async function flushUi() {
	await Promise.resolve();
	await nextTick();
	await Promise.resolve();
	await nextTick();
}

function mountCard(props: Record<string, unknown>) {
	const host = document.createElement('div');
	document.body.appendChild(host);

	const app: App = createApp(
		defineComponent({
			render() {
				return h(AttachmentPreviewCard, props);
			},
		})
	);

	app.mount(host);
	cleanupFns.push(() => {
		app.unmount();
		host.remove();
	});
}

afterEach(() => {
	while (cleanupFns.length) cleanupFns.pop()?.();
	document.body.innerHTML = '';
});

describe('AttachmentPreviewCard', () => {
	it('renders planning image previews from thumbnail_url', async () => {
		mountCard({
			variant: 'planning',
			title: 'Lab setup photo',
			attachment: {
				item_id: 'ATT-IMG-1',
				kind: 'image',
				preview_mode: 'thumbnail_image',
				extension: 'webp',
				thumbnail_url:
					'/api/method/ifitwala_ed.api.file_access.thumbnail_academic_file?file=FILE-IMG-1',
				preview_url:
					'/api/method/ifitwala_ed.api.file_access.preview_academic_file?file=FILE-IMG-1',
				open_url:
					'/api/method/ifitwala_ed.api.file_access.download_academic_file?file=FILE-IMG-1',
			},
		});
		await flushUi();

		const previewSurface = document.querySelector('[data-resource-preview-kind="image"]');
		expect(previewSurface).not.toBeNull();
		expect(previewSurface?.querySelector('img')?.getAttribute('src')).toContain(
			'thumbnail_academic_file'
		);
		expect(document.body.textContent || '').toContain('Open original');
	});

	it('retries planning image previews with preview_url when the thumbnail fails', async () => {
		mountCard({
			variant: 'planning',
			title: 'Lab setup photo',
			attachment: {
				item_id: 'ATT-IMG-2',
				kind: 'image',
				preview_mode: 'thumbnail_image',
				extension: 'webp',
				thumbnail_url:
					'/api/method/ifitwala_ed.api.file_access.thumbnail_academic_file?file=FILE-IMG-2',
				preview_url:
					'/api/method/ifitwala_ed.api.file_access.preview_academic_file?file=FILE-IMG-2',
				open_url:
					'/api/method/ifitwala_ed.api.file_access.download_academic_file?file=FILE-IMG-2',
			},
		});
		await flushUi();

		const previewImage = document.querySelector(
			'[data-resource-preview-kind="image"] img'
		) as HTMLImageElement | null;
		expect(previewImage?.getAttribute('src')).toContain('thumbnail_academic_file');

		previewImage?.dispatchEvent(new Event('error'));
		await flushUi();

		const retriedImage = document.querySelector(
			'[data-resource-preview-kind="image"] img'
		) as HTMLImageElement | null;
		expect(retriedImage?.getAttribute('src')).toContain('preview_academic_file');
		expect(document.body.textContent || '').toContain('Open original');
	});

	it('renders planning image previews from preview_url when no thumbnail is available', async () => {
		mountCard({
			variant: 'planning',
			title: 'Lab setup photo',
			attachment: {
				item_id: 'ATT-IMG-3',
				kind: 'image',
				preview_mode: 'inline_image',
				extension: 'png',
				preview_url:
					'/api/method/ifitwala_ed.api.file_access.preview_academic_file?file=FILE-IMG-3',
				open_url:
					'/api/method/ifitwala_ed.api.file_access.download_academic_file?file=FILE-IMG-3',
			},
		});
		await flushUi();

		const previewSurface = document.querySelector('[data-resource-preview-kind="image"]');
		expect(previewSurface).not.toBeNull();
		expect(previewSurface?.querySelector('img')?.getAttribute('src')).toContain(
			'preview_academic_file'
		);
	});

	it('keeps communication pdf behavior on the full preview surface', async () => {
		mountCard({
			variant: 'communication',
			title: 'Family handbook',
			attachment: {
				item_id: 'ATT-PDF-1',
				kind: 'pdf',
				preview_mode: 'pdf_embed',
				preview_status: 'ready',
				extension: 'pdf',
				thumbnail_url:
					'/api/method/ifitwala_ed.api.file_access.preview_org_communication_attachment?row_name=ATT-PDF-1',
				preview_url:
					'/api/method/ifitwala_ed.api.file_access.preview_org_communication_attachment?row_name=ATT-PDF-1',
				open_url:
					'/api/method/ifitwala_ed.api.file_access.open_org_communication_attachment?row_name=ATT-PDF-1',
			},
		});
		await flushUi();

		const pdfSurface = document.querySelector('[data-communication-attachment-kind="pdf"]');
		expect(pdfSurface?.querySelector('img')?.getAttribute('src')).toContain(
			'preview_org_communication_attachment'
		);
		expect(document.body.textContent || '').toContain('Open PDF');
		expect(document.body.textContent || '').toContain('Open preview image');
	});

	it('renders planning pdf previews inline from the governed thumbnail image when available', async () => {
		mountCard({
			variant: 'planning',
			title: 'Family handbook',
			attachment: {
				item_id: 'ATT-PDF-PLAN-1',
				kind: 'pdf',
				preview_mode: 'pdf_embed',
				preview_status: 'ready',
				extension: 'pdf',
				thumbnail_url:
					'/api/method/ifitwala_ed.api.file_access.thumbnail_academic_file?file=FILE-PDF-1',
				preview_url:
					'/api/method/ifitwala_ed.api.file_access.preview_academic_file?file=FILE-PDF-1',
				open_url:
					'/api/method/ifitwala_ed.api.file_access.download_academic_file?file=FILE-PDF-1',
			},
		});
		await flushUi();

		const pdfSurface = document.querySelector('[data-resource-preview-kind="pdf"]');
		expect(pdfSurface?.querySelector('img')?.getAttribute('src')).toContain(
			'thumbnail_academic_file'
		);
		expect(document.body.textContent || '').toContain('Open original');
	});

	it('shows preview and download actions for learning attachments', async () => {
		mountCard({
			variant: 'learning',
			title: 'Lab guide',
			attachment: {
				item_id: 'ATT-LEARNING-PDF-1',
				kind: 'pdf',
				preview_mode: 'pdf_embed',
				preview_status: 'ready',
				extension: 'pdf',
				preview_url: '/preview/learning-pdf-1',
				open_url: '/open/learning-pdf-1',
				download_url: '/download/learning-pdf-1',
			},
		});
		await flushUi();

		const actions = Array.from(document.querySelectorAll('a.if-action'));
		expect(actions.map(action => action.textContent?.trim())).toContain('Preview');
		expect(actions.map(action => action.textContent?.trim())).toContain('Download');
		expect(actions.find(action => action.textContent?.trim() === 'Download')?.getAttribute('href')).toBe(
			'/download/learning-pdf-1'
		);
	});

	it('uses button-style preview and open actions for evidence cards', async () => {
		mountCard({
			variant: 'evidence',
			title: 'Draft notes',
			attachment: {
				item_id: 'ATT-EVIDENCE-1',
				kind: 'other',
				preview_mode: 'icon_only',
				preview_url: '/preview/evidence-1',
				open_url: '/open/evidence-1',
			},
		});
		await flushUi();

		const actions = Array.from(document.querySelectorAll('a.if-button.if-button--secondary'));
		expect(actions).toHaveLength(2);
		expect(actions[0]?.textContent?.trim()).toBe('Preview');
		expect(actions[1]?.textContent?.trim()).toBe('Open');
	});
});
