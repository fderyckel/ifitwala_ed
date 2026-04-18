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
	it('renders a first-page image preview for PDFs only when the governed preview is ready', async () => {
		mountPreviewList([
			{
				row_name: 'ATT-PDF-READY',
				kind: 'file',
				title: 'Family handbook',
				file_name: 'handbook.pdf',
				preview_status: 'ready',
				thumbnail_url:
					'/api/method/ifitwala_ed.api.file_access.thumbnail_org_communication_attachment?row_name=ATT-PDF-READY',
				preview_url: '/api/method/ifitwala_ed.api.file_access.preview_org_communication_attachment?row_name=ATT-PDF-READY',
				open_url: '/api/method/ifitwala_ed.api.file_access.open_org_communication_attachment?row_name=ATT-PDF-READY',
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
				preview_status: 'pending',
				thumbnail_url:
					'/api/method/ifitwala_ed.api.file_access.thumbnail_org_communication_attachment?row_name=ATT-PDF-PENDING',
				preview_url: '/api/method/ifitwala_ed.api.file_access.preview_org_communication_attachment?row_name=ATT-PDF-PENDING',
				open_url: '/api/method/ifitwala_ed.api.file_access.open_org_communication_attachment?row_name=ATT-PDF-PENDING',
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
