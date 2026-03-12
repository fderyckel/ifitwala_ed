// ifitwala_ed/ui-spa/src/overlays/analytics/__tests__/AnalyticsExpandOverlay.test.ts

import { afterEach, describe, expect, it, vi } from 'vitest';
import { createApp, defineComponent, h, nextTick, type App } from 'vue';

import AnalyticsExpandOverlay from '@/overlays/analytics/AnalyticsExpandOverlay.vue';

const cleanupFns: Array<() => void> = [];

function mountOverlay() {
	const host = document.createElement('div');
	document.body.appendChild(host);

	const onClose = vi.fn();
	const app: App = createApp(
		defineComponent({
			render() {
				return h(AnalyticsExpandOverlay, {
					open: true,
					title: 'Expanded analytics',
					chartOption: {},
					kind: 'table',
					rows: [],
					onClose,
				});
			},
		})
	);

	app.mount(host);
	cleanupFns.push(() => {
		app.unmount();
		host.remove();
	});

	return { onClose };
}

afterEach(() => {
	while (cleanupFns.length) {
		cleanupFns.pop()?.();
	}
	document.body.innerHTML = '';
});

describe('AnalyticsExpandOverlay', () => {
	it('emits close when clicking the empty overlay shell outside the panel', async () => {
		const { onClose } = mountOverlay();

		await nextTick();

		const wrap = document.body.querySelector('.if-overlay__wrap');
		expect(wrap).not.toBeNull();

		wrap?.dispatchEvent(new MouseEvent('click', { bubbles: true }));

		expect(onClose).toHaveBeenCalledTimes(1);
		expect(onClose).toHaveBeenCalledWith('backdrop');
	});

	it('does not emit close when clicking inside the expanded panel', async () => {
		const { onClose } = mountOverlay();

		await nextTick();

		const panel = document.body.querySelector('.if-overlay__panel');
		expect(panel).not.toBeNull();

		panel?.dispatchEvent(new MouseEvent('click', { bubbles: true }));

		expect(onClose).not.toHaveBeenCalled();
	});
});
