import { afterEach, describe, expect, it, vi } from 'vitest';
import { createApp, defineComponent, h, nextTick, type App } from 'vue';

const {
	getGuardianPortalChromeMock,
	getStudentPortalChromeMock,
	subscribeMock,
	routeState,
} = vi.hoisted(() => ({
	getGuardianPortalChromeMock: vi.fn(),
	getStudentPortalChromeMock: vi.fn(),
	subscribeMock: vi.fn(),
	routeState: {
		path: '/guardian',
		fullPath: '/guardian',
		name: 'guardian-home',
	},
}));

let orgCommunicationInvalidateHandler: (() => void) | null = null;

vi.mock('vue-router', async () => {
	return {
		useRoute: () => routeState,
	};
});

vi.mock('@/components/PortalNavbar.vue', () => ({
	default: defineComponent({
		name: 'PortalNavbarStub',
		emits: ['toggle-sidebar'],
		setup(_, { emit }) {
			return () =>
				h(
					'button',
					{
						type: 'button',
						onClick: () => emit('toggle-sidebar'),
					},
					'navbar'
				);
		},
	}),
}));

vi.mock('@/components/PortalSidebar.vue', () => ({
	default: defineComponent({
		name: 'PortalSidebarStub',
		props: {
			activeSection: {
				type: String,
				default: '',
			},
			communicationUnreadCount: {
				type: Number,
				default: 0,
			},
		},
		setup(props) {
			return () =>
				h(
					'div',
					{ 'data-testid': 'portal-sidebar-stub' },
					`${props.activeSection}:${props.communicationUnreadCount}`
				);
		},
	}),
}));

vi.mock('@/components/StudentContextSidebar.vue', () => ({
	default: defineComponent({
		name: 'StudentContextSidebarStub',
		setup() {
			return () => h('div', 'student-context');
		},
	}),
}));

vi.mock('@/components/PortalFooter.vue', () => ({
	default: defineComponent({
		name: 'PortalFooterStub',
		setup() {
			return () => h('div', 'footer');
		},
	}),
}));

vi.mock('@/lib/services/portal/portalChromeService', () => ({
	getGuardianPortalChrome: getGuardianPortalChromeMock,
	getStudentPortalChrome: getStudentPortalChromeMock,
}));

vi.mock('@/lib/uiSignals', () => ({
	SIGNAL_ORG_COMMUNICATION_INVALIDATE: 'org_communication:invalidate',
	uiSignals: {
		subscribe: subscribeMock,
	},
}));

import PortalLayout from '@/layouts/PortalLayout.vue';

const cleanupFns: Array<() => void> = [];

async function flushUi() {
	await Promise.resolve();
	await nextTick();
	await Promise.resolve();
	await nextTick();
}

function mountPortalLayout() {
	const host = document.createElement('div');
	document.body.appendChild(host);

	const app: App = createApp(
		defineComponent({
			render() {
				return h(PortalLayout, {}, { default: () => h('div', 'page') });
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
	getGuardianPortalChromeMock.mockReset();
	getStudentPortalChromeMock.mockReset();
	subscribeMock.mockReset();
	orgCommunicationInvalidateHandler = null;
	routeState.path = '/guardian';
	routeState.fullPath = '/guardian';
	routeState.name = 'guardian-home';
	while (cleanupFns.length) {
		cleanupFns.pop()?.();
	}
	document.body.innerHTML = '';
});

describe('PortalLayout', () => {
	it('loads guardian portal chrome counts into the sidebar and refreshes on org communication invalidation', async () => {
		getGuardianPortalChromeMock
			.mockResolvedValueOnce({ counts: { unread_communications: 5 } })
			.mockResolvedValueOnce({ counts: { unread_communications: 4 } });
		getStudentPortalChromeMock.mockResolvedValue({ counts: { unread_communications: 2 } });
		subscribeMock.mockImplementation((name: string, handler: () => void) => {
			if (name === 'org_communication:invalidate') {
				orgCommunicationInvalidateHandler = handler;
			}
			return () => {};
		});

		mountPortalLayout();
		await flushUi();

		expect(getGuardianPortalChromeMock).toHaveBeenCalledTimes(1);
		expect(getStudentPortalChromeMock).not.toHaveBeenCalled();
		expect(document.querySelector('[data-testid="portal-sidebar-stub"]')?.textContent).toBe(
			'guardian:5'
		);

		orgCommunicationInvalidateHandler?.();
		await flushUi();

		expect(getGuardianPortalChromeMock).toHaveBeenCalledTimes(2);
		expect(document.querySelector('[data-testid="portal-sidebar-stub"]')?.textContent).toBe(
			'guardian:4'
		);
	});
});
