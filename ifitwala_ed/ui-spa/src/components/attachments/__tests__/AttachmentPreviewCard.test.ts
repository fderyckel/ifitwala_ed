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
				preview_url:
					'/api/method/ifitwala_ed.api.file_access.preview_org_communication_attachment?row_name=ATT-PDF-1',
				open_url:
					'/api/method/ifitwala_ed.api.file_access.open_org_communication_attachment?row_name=ATT-PDF-1',
			},
		});
		await flushUi();

		const pdfSurface = document.querySelector('[data-communication-attachment-kind="pdf"]');
		expect(pdfSurface?.querySelector('img')?.getAttribute('src')).toContain('ATT-PDF-1');
		expect(document.body.textContent || '').toContain('Open PDF');
		expect(document.body.textContent || '').toContain('Open preview image');
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
