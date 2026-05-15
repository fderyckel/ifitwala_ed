// ifitwala_ed/ui-spa/src/overlays/analytics/__tests__/AnalyticsExpandOverlay.test.ts

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

vi.mock('@/components/analytics/AnalyticsChart.vue', () => ({
	default: defineComponent({
		name: 'AnalyticsChartStub',
		setup() {
			return () => h('div', { 'data-testid': 'analytics-chart-stub' });
		},
	}),
}));

import AnalyticsExpandOverlay from '@/overlays/analytics/AnalyticsExpandOverlay.vue';

const cleanupFns: Array<() => void> = [];

function mountOverlay(rows: Record<string, unknown>[] = []) {
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
					rows,
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

	it('renders stacked follow-up detail for student log rows', async () => {
		mountOverlay([
			{
				name: 'SLOG-0001',
				date: '2026-03-10',
				log_type: 'Wellbeing',
				content: 'Needs counselor follow-up.',
				author: 'Teacher One',
				requires_follow_up: 1,
				follow_up_count: 2,
				follow_ups: [
					{
						name: 'SLFU-0001',
						doctype: 'Student Log Follow Up',
						next_step: 'Refer to Counselor',
						responded_in_label: '3h 30m',
						responded_at: '2026-03-10 11:30:00',
						follow_up_author: 'Counselor Jane',
						comment_text: 'Met student and guardian.',
					},
					{
						name: 'SLFU-0002',
						doctype: 'Student Log Follow Up',
						next_step: 'Refer to Counselor',
						responded_in_label: '1d 2h',
						responded_at: '2026-03-11 10:00:00',
						follow_up_author: 'Pastoral Lead',
						comment_text: 'Confirmed next support action.',
					},
				],
			},
		]);

		await nextTick();

		const text = document.body.textContent || '';
		expect(text).toContain('Student Log Follow Up');
		expect(text).toContain('Refer to Counselor');
		expect(text).toContain('Responded in 3h 30m');
		expect(text).toContain('Met student and guardian.');
		expect(text).toContain('Confirmed next support action.');
	});
});
