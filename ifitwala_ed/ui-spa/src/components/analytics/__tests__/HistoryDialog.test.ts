import { afterEach, describe, expect, it, vi } from 'vitest';
import { createApp, defineComponent, h, nextTick, type App } from 'vue';

const mocks = vi.hoisted(() => ({
	resourceState: {
		loading: false,
		data: null as any,
		error: null as any,
		fetch: vi.fn(),
	},
}));

vi.mock('frappe-ui', async () => {
	const { defineComponent, h } = await import('vue');

	return {
		Avatar: defineComponent({
			name: 'AvatarStub',
			setup() {
				return () => h('div', { 'data-avatar': '1' });
			},
		}),
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
		createResource: () => mocks.resourceState,
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

vi.mock('@/components/analytics/AnalyticsChart.vue', async () => {
	const { defineComponent, h } = await import('vue');
	return {
		default: defineComponent({
			name: 'AnalyticsChartStub',
			setup() {
				return () => h('div', { 'data-analytics-chart': '1' });
			},
		}),
	};
});

vi.mock('@/components/filters/DateRangePills.vue', async () => {
	const { defineComponent, h } = await import('vue');
	return {
		default: defineComponent({
			name: 'DateRangePillsStub',
			setup() {
				return () => h('div', { 'data-range-pills': '1' });
			},
		}),
	};
});

vi.mock('@/lib/i18n', () => ({
	__: (value: string) => value,
}));

import HistoryDialog from '@/components/analytics/HistoryDialog.vue';

const cleanupFns: Array<() => void> = [];

function mountDialog(overrides: Record<string, unknown> = {}) {
	const host = document.createElement('div');
	document.body.appendChild(host);

	const app: App = createApp(
		defineComponent({
			render() {
				return h(HistoryDialog, {
					modelValue: true,
					title: 'Clinic Volume',
					subtitle: 'Student patient visits over time',
					method: 'ifitwala_ed.api.morning_brief.get_clinic_visits_trend',
					...overrides,
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
	while (cleanupFns.length) {
		cleanupFns.pop()?.();
	}
	mocks.resourceState.loading = false;
	mocks.resourceState.data = null;
	mocks.resourceState.error = null;
	mocks.resourceState.fetch.mockReset();
	document.body.innerHTML = '';
});

describe('HistoryDialog', () => {
	it('unwraps frappe method responses nested under message', async () => {
		mocks.resourceState.data = {
			message: {
				school: 'Ifitwala Secondary School + 2 schools',
				data: [
					{ date: '2026-03-09', count: 1 },
					{ date: '2026-03-10', count: 0 },
				],
			},
		};

		mountDialog();
		await nextTick();

		expect(document.body.textContent).toContain('Ifitwala Secondary School + 2 schools');
		expect(document.body.textContent).not.toContain('Loading...');
		expect(document.body.querySelector('[data-analytics-chart="1"]')).not.toBeNull();
	});

	it('preserves the card school context while the history payload is empty', async () => {
		mocks.resourceState.data = {
			message: {
				data: [],
			},
		};

		mountDialog({
			initialSchool: 'Ifitwala Secondary School + 2 schools',
		});
		await nextTick();

		expect(document.body.textContent).toContain('Ifitwala Secondary School + 2 schools');
		expect(document.body.textContent).not.toContain('Loading...');
	});

	it('shows an actionable error when the history fetch fails', async () => {
		mocks.resourceState.error = new Error(
			'Assign a default school or Employee.school before opening clinic volume.'
		);

		mountDialog();
		await nextTick();

		expect(mocks.resourceState.fetch).toHaveBeenCalledTimes(1);
		expect(document.body.textContent).toContain(
			'Assign a default school or Employee.school before opening clinic volume.'
		);
		expect(document.body.textContent).toContain('Unavailable');
		expect(document.body.querySelector('[data-range-pills="1"]')).not.toBeNull();
	});
});
