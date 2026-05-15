import { afterEach, describe, expect, it, vi } from 'vitest';
import { createApp, defineComponent, h, nextTick, type App } from 'vue';

vi.mock('@headlessui/vue', () => {
	const passthrough = (tag = 'div') =>
		defineComponent({
			name: `Stub${tag}`,
			props: ['as', 'show', 'initialFocus'],
			setup(props, { slots, attrs }) {
				return () => {
					if (props.show === false) return null;
					return h(props.as && props.as !== 'template' ? props.as : tag, attrs, slots.default?.());
				};
			},
		});

	return {
		Dialog: passthrough('div'),
		DialogPanel: passthrough('div'),
		DialogTitle: passthrough('h2'),
		TransitionChild: passthrough('div'),
		TransitionRoot: passthrough('div'),
	};
});

vi.mock('frappe-ui', () => ({
	FeatherIcon: defineComponent({
		name: 'FeatherIconStub',
		setup() {
			return () => h('span');
		},
	}),
}));

vi.mock('@/lib/client', () => ({
	api: vi.fn(),
}));

import SchoolEventModal from '@/components/calendar/SchoolEventModal.vue';

const cleanupFns: Array<() => void> = [];

const eventPayload = {
	subject: 'Parent Workshop',
	start: '2026-04-22T08:00:00+07:00',
	end: '2026-04-22T09:00:00+07:00',
	all_day: false,
	timezone: 'Asia/Bangkok',
	location: 'Hall 1',
	school: 'ISS',
	event_category: 'Parent Engagement',
	description: '<p>Workshop presentation</p>',
	reference_type: 'Org Communication',
	reference_name: 'ORG-COMM-26-04-00001',
};

async function flushUi() {
	await Promise.resolve();
	await nextTick();
}

function mountModal(props: Record<string, unknown> = {}) {
	const host = document.createElement('div');
	document.body.appendChild(host);

	const app: App = createApp(
		defineComponent({
			render() {
				return h(SchoolEventModal, {
					open: true,
					event: eventPayload,
					...props,
				});
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

describe('SchoolEventModal reference visibility', () => {
	it('shows the Desk reference link by default', async () => {
		mountModal();
		await flushUi();

		const link = document.querySelector('a[href="/desk/org-communication/ORG-COMM-26-04-00001"]');
		expect(link).not.toBeNull();
		expect(document.body.textContent || '').toContain('View referenced document');
	});

	it('suppresses the Desk reference link when portal surfaces disable it', async () => {
		mountModal({ allowReferenceLink: false });
		await flushUi();

		expect(
			document.querySelector('a[href="/desk/org-communication/ORG-COMM-26-04-00001"]')
		).toBeNull();
		expect(document.body.textContent || '').not.toContain('View referenced document');
		expect(document.body.textContent || '').not.toContain('ORG-COMM-26-04-00001');
	});
});
