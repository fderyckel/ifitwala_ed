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

import CriticalIncidentsListOverlay from '@/overlays/morning_brief/CriticalIncidentsListOverlay.vue';

const cleanupFns: Array<() => void> = [];

const item = {
	name: 'SLOG-0001',
	student_name: 'Isla Smith',
	student_image: null,
	log_type: 'Behaviour',
	date: '2026-03-18',
	log: 'Full student log content',
	date_display: '18 Mar 2026',
	snippet: 'Open follow-up still required from the academic team.',
};

function mountOverlay() {
	const host = document.createElement('div');
	document.body.appendChild(host);

	const onClose = vi.fn();
	const onViewLog = vi.fn();

	const app: App = createApp(
		defineComponent({
			render() {
				return h(CriticalIncidentsListOverlay, {
					open: true,
					items: [item],
					onClose,
					onViewLog,
				});
			},
		})
	);

	app.mount(host);
	cleanupFns.push(() => {
		app.unmount();
		host.remove();
	});

	return { onClose, onViewLog };
}

afterEach(() => {
	while (cleanupFns.length) {
		cleanupFns.pop()?.();
	}
	document.body.innerHTML = '';
});

describe('CriticalIncidentsListOverlay', () => {
	it('closes when clicking the empty overlay shell outside the panel', async () => {
		const { onClose } = mountOverlay();

		await nextTick();

		const wrap = document.body.querySelector('.critical-incidents__wrap');
		expect(wrap).not.toBeNull();

		wrap?.dispatchEvent(new MouseEvent('click', { bubbles: true }));

		expect(onClose).toHaveBeenCalledTimes(1);
		expect(onClose).toHaveBeenCalledWith('backdrop');
	});

	it('opens the selected log from the incident card action', async () => {
		const { onViewLog } = mountOverlay();

		await nextTick();

		const button = document.body.querySelector('.critical-incidents__action-button');
		expect(button).not.toBeNull();

		button?.dispatchEvent(new MouseEvent('click', { bubbles: true }));

		expect(onViewLog).toHaveBeenCalledTimes(1);
		expect(onViewLog).toHaveBeenCalledWith(item);
	});
});
