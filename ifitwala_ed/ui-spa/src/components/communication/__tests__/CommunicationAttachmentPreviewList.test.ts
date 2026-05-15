import { afterEach, describe, expect, it } from 'vitest';
import { createApp, defineComponent, h, nextTick, type App } from 'vue';

import CommunicationAttachmentPreviewList from '@/components/communication/CommunicationAttachmentPreviewList.vue';

const cleanupFns: Array<() => void> = [];

async function flushUi() {
	await Promise.resolve();
	await nextTick();
	await Promise.resolve();
	await nextTick();
}

function buildCommunicationAttachment(overrides: Record<string, unknown> = {}) {
	return {
		id: 'ATT-1',
		surface: 'org_communication.attachment',
		item_id: 'ATT-1',
		owner_doctype: 'Org Communication',
		owner_name: 'COMM-1',
		file_id: 'FILE-1',
		display_name: 'Attachment',
		kind: 'other',
		preview_mode: 'icon_only',
		...overrides,
	};
}

function mountPreviewList(attachments: Array<Record<string, unknown>>) {
	const host = document.createElement('div');
	document.body.appendChild(host);

	const app: App = createApp(
		defineComponent({
			render() {
				return h(CommunicationAttachmentPreviewList, { attachments });
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

describe('CommunicationAttachmentPreviewList', () => {
	it('prefers thumbnail_url for inline image cards when it is available', async () => {
		mountPreviewList([
			{
				row_name: 'ATT-IMG-READY',
				kind: 'file',
				title: 'Event poster',
				file_name: 'poster.jpg',
				attachment: buildCommunicationAttachment({
					item_id: 'ATT-IMG-READY',
					display_name: 'Event poster',
					kind: 'image',
					extension: 'jpg',
					preview_mode: 'thumbnail_image',
					preview_status: 'ready',
					thumbnail_url:
						'/api/method/ifitwala_ed.api.file_access.preview_org_communication_attachment?row_name=ATT-IMG-READY',
					preview_url:
						'/api/method/ifitwala_ed.api.file_access.preview_org_communication_attachment?row_name=ATT-IMG-READY',
					open_url:
						'/api/method/ifitwala_ed.api.file_access.open_org_communication_attachment?row_name=ATT-IMG-READY',
				}),
			},
		]);
		await flushUi();

		const imageLink = document.querySelector(
			'[data-communication-attachment-kind="image"]'
		) as HTMLAnchorElement | null;
		const imagePreview = imageLink?.querySelector('img');

		expect(imagePreview?.getAttribute('src')).toContain('preview_org_communication_attachment');
		expect(imagePreview?.getAttribute('src')).toContain('ATT-IMG-READY');
		expect(imageLink?.getAttribute('href')).toContain('preview_org_communication_attachment');
	});

	it('renders inline image cards from preview_url when the richer preview is ready and no thumbnail exists yet', async () => {
		mountPreviewList([
			{
				row_name: 'ATT-IMG-VIEWER-READY',
				kind: 'file',
				title: 'Campus photo',
				file_name: 'campus.png',
				attachment: buildCommunicationAttachment({
					item_id: 'ATT-IMG-VIEWER-READY',
					display_name: 'Campus photo',
					kind: 'image',
					extension: 'png',
					preview_mode: 'inline_image',
					preview_status: 'ready',
					preview_url:
						'/api/method/ifitwala_ed.api.file_access.preview_org_communication_attachment?row_name=ATT-IMG-VIEWER-READY',
					open_url:
						'/api/method/ifitwala_ed.api.file_access.open_org_communication_attachment?row_name=ATT-IMG-VIEWER-READY',
				}),
			},
		]);
		await flushUi();

		const imagePreview = document.querySelector(
			'[data-communication-attachment-kind="image"] img'
		) as HTMLImageElement | null;
		expect(imagePreview?.getAttribute('src')).toContain('preview_org_communication_attachment');
		expect(imagePreview?.getAttribute('src')).toContain('ATT-IMG-VIEWER-READY');
	});

	it('keeps image attachments action-led when neither a thumbnail nor a ready preview derivative exists', async () => {
		mountPreviewList([
			{
				row_name: 'ATT-IMG-PENDING',
				kind: 'file',
				title: 'Campus photo',
				file_name: 'campus.png',
				attachment: buildCommunicationAttachment({
					item_id: 'ATT-IMG-PENDING',
					display_name: 'Campus photo',
					kind: 'image',
					extension: 'png',
					preview_mode: 'icon_only',
					preview_status: 'pending',
					preview_url: null,
					open_url:
						'/api/method/ifitwala_ed.api.file_access.open_org_communication_attachment?row_name=ATT-IMG-PENDING',
				}),
			},
		]);
		await flushUi();

		expect(document.querySelector('[data-communication-attachment-kind="image"] img')).toBeNull();
		expect(document.body.textContent || '').toContain('Open');
		expect(document.body.textContent || '').not.toContain('Open original');
	});

	it('falls back to action-led image controls when the governed inline preview fails to load', async () => {
		mountPreviewList([
			{
				row_name: 'ATT-IMG-BROKEN',
				kind: 'file',
				title: 'Athletics banner',
				file_name: 'banner.webp',
				attachment: buildCommunicationAttachment({
					item_id: 'ATT-IMG-BROKEN',
					display_name: 'Athletics banner',
					kind: 'image',
					extension: 'webp',
					preview_mode: 'thumbnail_image',
					thumbnail_url:
						'/api/method/ifitwala_ed.api.file_access.preview_org_communication_attachment?row_name=ATT-IMG-BROKEN',
					preview_url:
						'/api/method/ifitwala_ed.api.file_access.preview_org_communication_attachment?row_name=ATT-IMG-BROKEN',
					open_url:
						'/api/method/ifitwala_ed.api.file_access.open_org_communication_attachment?row_name=ATT-IMG-BROKEN',
				}),
			},
		]);
		await flushUi();

		const imagePreview = document.querySelector(
			'[data-communication-attachment-kind="image"] img'
		) as HTMLImageElement | null;
		expect(imagePreview).not.toBeNull();

		imagePreview?.dispatchEvent(new Event('error'));
		await flushUi();

		const retriedImage = document.querySelector(
			'[data-communication-attachment-kind="image"] img'
		) as HTMLImageElement | null;
		expect(retriedImage).toBeNull();
		expect(document.body.textContent || '').toContain('Preview');
		expect(document.body.textContent || '').toContain('Open original');
	});

	it('renders a first-page image preview for PDFs only when the governed preview is ready', async () => {
		mountPreviewList([
			{
				row_name: 'ATT-PDF-READY',
				kind: 'file',
				title: 'Family handbook',
				file_name: 'handbook.pdf',
				attachment: buildCommunicationAttachment({
					item_id: 'ATT-PDF-READY',
					display_name: 'Family handbook',
					kind: 'pdf',
					extension: 'pdf',
					preview_mode: 'pdf_embed',
					preview_status: 'ready',
					preview_url:
						'/api/method/ifitwala_ed.api.file_access.preview_org_communication_attachment?row_name=ATT-PDF-READY',
					open_url:
						'/api/method/ifitwala_ed.api.file_access.open_org_communication_attachment?row_name=ATT-PDF-READY',
				}),
			},
		]);
		await flushUi();

		const pdfPreview = document.querySelector('[data-communication-attachment-kind="pdf"] img');
		expect(pdfPreview?.getAttribute('src')).toContain('ATT-PDF-READY');
		expect(document.body.textContent || '').toContain('Open PDF');
		expect(document.body.textContent || '').toContain('Open preview image');
	});

	it('keeps pending PDFs in a clean fallback state instead of trying to render the original file', async () => {
		mountPreviewList([
			{
				row_name: 'ATT-PDF-PENDING',
				kind: 'file',
				title: 'Policy update',
				file_name: 'policy.pdf',
				attachment: buildCommunicationAttachment({
					item_id: 'ATT-PDF-PENDING',
					display_name: 'Policy update',
					kind: 'pdf',
					extension: 'pdf',
					preview_mode: 'icon_only',
					preview_status: 'pending',
					preview_url: null,
					open_url:
						'/api/method/ifitwala_ed.api.file_access.open_org_communication_attachment?row_name=ATT-PDF-PENDING',
				}),
			},
		]);
		await flushUi();

		expect(document.querySelector('[data-communication-attachment-kind="pdf"] img')).toBeNull();
		expect(document.body.textContent || '').toContain('Preview not available yet');
		expect(document.body.textContent || '').toContain('still processing');

		const actions = Array.from(document.querySelectorAll('a.if-action'));
		expect(actions).toHaveLength(1);
		expect(actions[0]?.textContent?.trim()).toBe('Open PDF');
		expect(actions[0]?.getAttribute('href')).toContain('ATT-PDF-PENDING');
	});
});
