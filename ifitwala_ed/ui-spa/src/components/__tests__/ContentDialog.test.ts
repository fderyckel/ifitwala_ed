import { afterEach, describe, expect, it, vi } from 'vitest';
import { createApp, defineComponent, h, nextTick, type App } from 'vue';

vi.mock('frappe-ui', async () => {
	const { defineComponent, h } = await import('vue');

	return {
		FeatherIcon: defineComponent({
			name: 'FeatherIconStub',
			props: {
				name: {
					type: String,
					required: false,
					default: '',
				},
			},
			setup(props) {
				return () => h('span', { 'data-feather-icon': props.name });
			},
		}),
	};
});

vi.mock('@headlessui/vue', async () => {
	const { defineComponent, h } = await import('vue');

	const passthrough = (name: string) =>
		defineComponent({
			name,
			props: {
				as: {
					type: [String, Object],
					required: false,
					default: 'div',
				},
				show: {
					type: Boolean,
					required: false,
					default: true,
				},
			},
			setup(props, { slots, attrs }) {
				return () =>
					props.show === false
						? null
						: h(typeof props.as === 'string' ? props.as : 'div', attrs, slots.default?.());
			},
		});

	return {
		Dialog: passthrough('DialogStub'),
		DialogPanel: passthrough('DialogPanelStub'),
		DialogTitle: passthrough('DialogTitleStub'),
		TransitionChild: passthrough('TransitionChildStub'),
		TransitionRoot: passthrough('TransitionRootStub'),
	};
});

vi.mock('@/components/InteractionEmojiChips.vue', () => ({
	default: defineComponent({
		name: 'InteractionEmojiChipsStub',
		setup() {
			return () => h('div', { 'data-testid': 'interaction-chips-stub' });
		},
	}),
}));

vi.mock('@/components/communication/CommunicationAttachmentPreviewList.vue', () => ({
	default: defineComponent({
		name: 'CommunicationAttachmentPreviewListStub',
		props: {
			attachments: {
				type: Array,
				default: () => [],
			},
		},
		setup(props) {
			return () =>
				h(
					'div',
					{ 'data-testid': 'communication-attachment-preview-list-stub' },
					`attachments:${props.attachments.length}`
				);
		},
	}),
}));

import ContentDialog from '@/components/ContentDialog.vue';

const cleanupFns: Array<() => void> = [];

async function flushUi() {
	await nextTick();
	await nextTick();
}

function mountDialog(
	content = '<p>Hello world</p>',
	options: {
		showInteractions?: boolean;
		showComments?: boolean;
		attachments?: Array<Record<string, unknown>>;
		attachmentsLoading?: boolean;
		attachmentsError?: string;
	} = {}
) {
	const host = document.createElement('div');
	document.body.appendChild(host);

	const onUpdateModelValue = vi.fn();
	const app: App = createApp(
		defineComponent({
			render() {
				return h(ContentDialog, {
					modelValue: true,
					title: 'Announcement detail',
					subtitle: 'Wednesday, 18 March 2026',
					content,
					showInteractions: options.showInteractions ?? true,
					showComments: options.showComments,
					attachments: options.attachments || [],
					attachmentsLoading: options.attachmentsLoading ?? false,
					attachmentsError: options.attachmentsError || '',
					interaction: {
						counts: {},
						self: null,
						reaction_counts: {},
						reactions_total: 0,
						comments_total: 0,
					},
					'onUpdate:modelValue': onUpdateModelValue,
				});
			},
		})
	);

	app.mount(host);
	cleanupFns.push(() => {
		app.unmount();
		host.remove();
	});

	return { onUpdateModelValue };
}

afterEach(() => {
	while (cleanupFns.length) {
		cleanupFns.pop()?.();
	}
	document.body.innerHTML = '';
});

describe('ContentDialog', () => {
	it('closes explicitly when the A+ backdrop is clicked', async () => {
		const { onUpdateModelValue } = mountDialog();

		await flushUi();

		const backdrop = document.body.querySelector('.if-overlay__backdrop');
		expect(backdrop).not.toBeNull();

		backdrop?.dispatchEvent(new MouseEvent('click', { bubbles: true }));

		expect(onUpdateModelValue).toHaveBeenCalledWith(false);
	});

	it('replaces policy links with the morning-brief action row', async () => {
		mountDialog('<p><a href="/app/policy-version/POL-0001">Open policy</a></p>');

		await flushUi();

		const policyRow = document.body.querySelector('.if-policy-action-row');
		expect(policyRow).not.toBeNull();
		expect(policyRow?.textContent || '').toContain('Read Policy');
		expect(policyRow?.textContent || '').toContain('Open Policy in Desk');
	});

	it('hides the comments action when the caller disables shared comments', async () => {
		mountDialog('<p>Hello world</p>', { showComments: false });

		await flushUi();

		const text = document.body.textContent || '';
		expect(text).not.toContain('Comments');
		expect(text).toContain('Acknowledge or react without leaving the briefing.');
		expect(document.body.querySelector('[data-testid="interaction-chips-stub"]')).not.toBeNull();
	});

	it('renders governed attachment previews when announcement attachments are provided', async () => {
		mountDialog('<p>Hello world</p>', {
			attachments: [
				{
					row_name: 'row-file',
					kind: 'file',
					title: 'Policy PDF',
					file_name: 'policy.pdf',
					preview_status: 'ready',
					preview_url:
						'/api/method/ifitwala_ed.api.file_access.preview_org_communication_attachment?row_name=row-file',
					open_url:
						'/api/method/ifitwala_ed.api.file_access.open_org_communication_attachment?row_name=row-file',
				},
			],
		});

		await flushUi();

		expect(document.body.textContent || '').toContain('Attachments');
		expect(
			document.body.querySelector('[data-testid="communication-attachment-preview-list-stub"]')
				?.textContent || ''
		).toContain('attachments:1');
	});
});
