import { afterEach, describe, expect, it, vi } from 'vitest';
import { createApp, defineComponent, h, nextTick, type App } from 'vue';

const { dashboardState, dashboardSubmitMock, drilldownSubmitMock } = vi.hoisted(() => ({
	dashboardState: { current: null as any },
	dashboardSubmitMock: vi.fn(),
	drilldownSubmitMock: vi.fn(),
}));

vi.mock('frappe-ui', async () => {
	const { defineComponent, h, reactive } = await import('vue');

	function createMockResource(responseSource: () => any, submitMock: ReturnType<typeof vi.fn>) {
		const state = reactive({
			loading: false,
			data: null as any,
			async submit(payload: any) {
				submitMock(payload);
				state.loading = true;
				const response = responseSource();
				state.data = response;
				state.loading = false;
				return response;
			},
		});
		return state;
	}

	return {
		createResource: ({ url }: { url: string }) => {
			if (url.includes('get_enrollment_dashboard')) {
				return createMockResource(() => ({ message: dashboardState.current }), dashboardSubmitMock);
			}
			if (url.includes('get_enrollment_drilldown')) {
				return createMockResource(() => ({ message: { rows: [], total_count: 0 } }), drilldownSubmitMock);
			}
			return createMockResource(() => ({}), vi.fn());
		},
		FormControl: defineComponent({
			name: 'FormControlStub',
			props: {
				type: { type: String, default: 'text' },
				modelValue: { type: [String, Number, Boolean, Object, Array], default: '' },
				options: { type: Array, default: () => [] },
				disabled: { type: Boolean, default: false },
			},
			emits: ['update:modelValue'],
			setup(props, { attrs, emit }) {
				return () => {
					if (props.type === 'select') {
						return h(
							'select',
							{
								...attrs,
								disabled: props.disabled,
								value: props.modelValue ?? '',
								onChange: (event: Event) => {
									const target = event.target as HTMLSelectElement;
									const rawValue = target.value;
									const options = Array.isArray(props.options) ? props.options : [];
									const matched = options.find((option: any) => {
										const value =
											option && typeof option === 'object' && 'value' in option ? option.value : option;
										return String(value ?? '') === rawValue;
									});
									if (matched && typeof matched === 'object' && 'value' in matched) {
										emit('update:modelValue', matched.value);
										return;
									}
									emit('update:modelValue', rawValue);
								},
							},
							(Array.isArray(props.options) ? props.options : []).map((option: any) => {
								const value =
									option && typeof option === 'object' && 'value' in option ? option.value : option;
								const label =
									option && typeof option === 'object' && 'label' in option ? option.label : option;
								return h('option', { value: value ?? '' }, String(label ?? value ?? ''));
							})
						);
					}

					return h('input', {
						...attrs,
						disabled: props.disabled,
						value: props.modelValue ?? '',
						onInput: (event: Event) =>
							emit('update:modelValue', (event.target as HTMLInputElement).value),
					});
				};
			},
		}),
	};
});

vi.mock('@/components/filters/FiltersBar.vue', () => ({
	default: defineComponent({
		name: 'FiltersBarStub',
		setup(_props, { slots }) {
			return () => h('section', { 'data-testid': 'filters-bar' }, slots.default?.());
		},
	}),
}));

vi.mock('@/components/analytics/KpiRow.vue', () => ({
	default: defineComponent({
		name: 'KpiRowStub',
		setup() {
			return () => h('div', { 'data-testid': 'kpi-row' });
		},
	}),
}));

vi.mock('@/components/analytics/StackedBarChart.vue', () => ({
	default: defineComponent({
		name: 'StackedBarChartStub',
		setup() {
			return () => h('div', { 'data-testid': 'stacked-chart' });
		},
	}),
}));

vi.mock('@/components/analytics/HorizontalBarTopN.vue', () => ({
	default: defineComponent({
		name: 'HorizontalBarTopNStub',
		setup() {
			return () => h('div', { 'data-testid': 'topn-chart' });
		},
	}),
}));

vi.mock('@/components/analytics/SideDrawerList.vue', () => ({
	default: defineComponent({
		name: 'SideDrawerListStub',
		setup() {
			return () => h('div', { 'data-testid': 'side-drawer-list' });
		},
	}),
}));

import EnrollmentAnalytics from '@/pages/staff/analytics/EnrollmentAnalytics.vue';

const cleanupFns: Array<() => void> = [];

function buildDashboardResponse(overrides?: {
	trendEnabled?: boolean;
	defaultOrganization?: string;
	defaultSchool?: string;
	defaultYears?: string[];
}) {
	const trendEnabled = overrides?.trendEnabled ?? false;
	const defaultOrganization = overrides?.defaultOrganization ?? 'ORG-1';
	const defaultSchool = overrides?.defaultSchool ?? 'SCH-1';
	const defaultYears = overrides?.defaultYears ?? ['AY-2025', 'AY-2026'];

	return {
		kpis: {
			active: 5,
			new_in_period: 0,
			drops_in_period: 0,
			net_change: 0,
			archived: 0,
		},
		stacked_chart: { series: [], rows: [] },
		topn: { cohorts: [], programs: [] },
		meta: {
			trend_enabled: trendEnabled,
			options: {
				organizations: [
					{ name: 'ORG-1', organization_name: 'Ifitwala Roots Campus', abbr: 'IRC' },
					{ name: 'ORG-2', organization_name: 'Ifitwala City Campus', abbr: 'ICC' },
				],
				schools: [
					{
						name: 'SCH-1',
						school_name: 'Ifitwala Secondary School',
						abbr: 'ISS',
						organization: 'ORG-1',
					},
					{
						name: 'SCH-2',
						school_name: 'Ifitwala Middle School',
						abbr: 'IMS',
						organization: 'ORG-2',
					},
				],
				academic_years: [
					{
						name: 'AY-2025',
						label: '2025/2026',
						year_start_date: '2025-08-01',
						year_end_date: '2026-06-30',
						school: 'SCH-1',
						school_label: 'Ifitwala Secondary School',
					},
					{
						name: 'AY-2026',
						label: '2026/2027',
						year_start_date: '2026-08-01',
						year_end_date: '2027-06-30',
						school: 'SCH-1',
						school_label: 'Ifitwala Secondary School',
					},
					{
						name: 'AY-2027',
						label: '2027/2028',
						year_start_date: '2027-08-01',
						year_end_date: '2028-06-30',
						school: 'SCH-2',
						school_label: 'Ifitwala Middle School',
					},
				],
			},
			defaults: {
				organization: defaultOrganization,
				school: defaultSchool,
				academic_years: defaultYears,
				compare_dimension: 'school',
				chart_mode: 'snapshot',
				as_of_date: '2026-03-29',
				top_n: 8,
			},
		},
	};
}

async function flushUi() {
	await Promise.resolve();
	await nextTick();
	await Promise.resolve();
	await nextTick();
}

function mountPage() {
	const host = document.createElement('div');
	document.body.appendChild(host);

	const app: App = createApp(
		defineComponent({
			render() {
				return h(EnrollmentAnalytics);
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
	dashboardState.current = null;
	dashboardSubmitMock.mockReset();
	drilldownSubmitMock.mockReset();
	while (cleanupFns.length) cleanupFns.pop()?.();
	document.body.innerHTML = '';
});

describe('EnrollmentAnalytics page', () => {
	it('hides the chart mode filter when the backend disables trend mode and resets dependent filters on org changes', async () => {
		dashboardState.current = buildDashboardResponse({ trendEnabled: false });

		mountPage();
		await flushUi();

		expect(dashboardSubmitMock).toHaveBeenCalledTimes(1);
		expect(document.querySelector('[data-testid="filters-bar"]')).not.toBeNull();
		expect(document.querySelector('[data-testid="enrollment-filter-grid"]')).not.toBeNull();
		expect(document.querySelector('[data-testid="enrollment-chart-mode-filter"]')).toBeNull();

		const organizationSelect = document.querySelector(
			'[data-testid="enrollment-organization-filter"]'
		) as HTMLSelectElement | null;
		const schoolSelect = document.querySelector(
			'[data-testid="enrollment-school-filter"]'
		) as HTMLSelectElement | null;
		const startYearSelect = document.querySelector(
			'[data-testid="enrollment-year-range-start"]'
		) as HTMLSelectElement | null;
		const endYearSelect = document.querySelector(
			'[data-testid="enrollment-year-range-end"]'
		) as HTMLSelectElement | null;

		expect(organizationSelect?.value).toBe('ORG-1');
		expect(schoolSelect?.value).toBe('SCH-1');
		expect(startYearSelect?.selectedIndex).toBe(1);
		expect(endYearSelect?.selectedIndex).toBe(2);

		organizationSelect!.value = 'ORG-2';
		organizationSelect!.dispatchEvent(new Event('change', { bubbles: true }));
		await flushUi();

		expect(schoolSelect?.value).toBe('');
		expect(startYearSelect?.selectedIndex).toBe(0);
		expect(endYearSelect?.selectedIndex).toBe(0);
	});

	it('shows chart mode only when the backend enables trend mode and hides the as-of date outside snapshot mode', async () => {
		dashboardState.current = buildDashboardResponse({ trendEnabled: true });

		mountPage();
		await flushUi();

		const chartModeSelect = document.querySelector(
			'[data-testid="enrollment-chart-mode-filter"]'
		) as HTMLSelectElement | null;
		expect(chartModeSelect).not.toBeNull();
		expect(document.querySelector('[data-testid="enrollment-as-of-date"]')).not.toBeNull();

		chartModeSelect!.value = 'trend';
		chartModeSelect!.dispatchEvent(new Event('change', { bubbles: true }));
		await flushUi();

		expect(document.querySelector('[data-testid="enrollment-as-of-date"]')).toBeNull();
	});
});
