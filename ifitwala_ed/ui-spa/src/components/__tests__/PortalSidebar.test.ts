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

vi.mock('vue-router', async () => {
	const { defineComponent, h } = await import('vue');

	return {
		RouterLink: defineComponent({
			name: 'RouterLinkStub',
			props: {
				to: {
					type: [String, Object],
					required: false,
					default: '',
				},
			},
			setup(props, { slots, attrs }) {
				const routeName =
					typeof props.to === 'object' && props.to && 'name' in props.to
						? String(props.to.name || '')
						: String(props.to || '');

				return () => h('a', { ...attrs, 'data-route-name': routeName }, slots.default?.());
			},
		}),
	};
});

import PortalSidebar from '@/components/PortalSidebar.vue';

const cleanupFns: Array<() => void> = [];

async function flushUi() {
	await nextTick();
	await nextTick();
}

function mountGuardianSidebar() {
	const host = document.createElement('div');
	document.body.appendChild(host);

	(window as Window & { portalRoles?: string[] }).portalRoles = ['guardian'];

	const app: App = createApp(
		defineComponent({
			render() {
				return h(PortalSidebar, {
					isMobileOpen: false,
					isRailExpanded: true,
					activeSection: 'guardian',
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

function getMenuLabels() {
	return Array.from(document.querySelectorAll('nav[aria-label="Menu"] > a')).map(link =>
		link.querySelector('.portal-sidebar__label')?.textContent?.trim() || ''
	);
}

afterEach(() => {
	delete (window as Window & { portalRoles?: string[] }).portalRoles;
	while (cleanupFns.length) {
		cleanupFns.pop()?.();
	}
	document.body.innerHTML = '';
});

describe('PortalSidebar', () => {
	it('uses Family Snapshot as the guardian home label and preserves the requested rail order', async () => {
		mountGuardianSidebar();
		await flushUi();

		const homeLabel =
			document.querySelector('.portal-sidebar__brand .portal-sidebar__label')?.textContent?.trim() ||
			'';

		expect(homeLabel).toBe('Family Snapshot');
		expect(getMenuLabels()).toEqual([
			'Communications',
			'Attendance',
			'Activities',
			'Monitoring',
			'Finance',
			'Policies',
			'Showcase Portfolio',
		]);
	});
});
