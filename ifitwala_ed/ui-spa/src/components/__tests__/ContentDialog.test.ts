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

import ContentDialog from '@/components/ContentDialog.vue';

const cleanupFns: Array<() => void> = [];

async function flushUi() {
	await nextTick();
	await nextTick();
}

function mountDialog(content = '<p>Hello world</p>') {
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
					showInteractions: true,
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
});
