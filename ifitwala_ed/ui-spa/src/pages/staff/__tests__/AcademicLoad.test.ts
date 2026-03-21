// ifitwala_ed/ui-spa/src/pages/staff/__tests__/AcademicLoad.test.ts

import { afterEach, describe, expect, it, vi } from 'vitest';
import { createApp, defineComponent, h, nextTick, type App } from 'vue';

const {
	filterMetaSubmitMock,
	dashboardSubmitMock,
	detailSubmitMock,
	coverSubmitMock,
	toastErrorMock,
} = vi.hoisted(() => ({
	filterMetaSubmitMock: vi.fn(),
	dashboardSubmitMock: vi.fn(),
	detailSubmitMock: vi.fn(),
	coverSubmitMock: vi.fn(),
	toastErrorMock: vi.fn(),
}));

vi.mock('frappe-ui', () => ({
	createResource: ({ url }: { url: string }) => {
		if (url.includes('get_academic_load_filter_meta')) return { submit: filterMetaSubmitMock };
		if (url.includes('get_academic_load_dashboard')) return { submit: dashboardSubmitMock };
		if (url.includes('get_academic_load_staff_detail')) return { submit: detailSubmitMock };
		if (url.includes('get_academic_load_cover_candidates')) return { submit: coverSubmitMock };
		return { submit: vi.fn() };
	},
	toast: { error: toastErrorMock },
}));

vi.mock('@/components/filters/FiltersBar.vue', () => ({
	default: defineComponent({
		name: 'FiltersBarStub',
		setup(_props, { slots }) {
			return () => h('div', { 'data-testid': 'filters-bar' }, slots.default?.());
		},
	}),
}));

vi.mock('@/components/analytics/KpiRow.vue', () => ({
	default: defineComponent({
		name: 'KpiRowStub',
		props: { items: { type: Array, required: false, default: () => [] } },
		setup(props) {
			return () =>
				h(
					'div',
					{ 'data-testid': 'kpi-row' },
					(Array.isArray(props.items) ? props.items : []).map((item: any) =>
						h('span', { class: 'kpi-item' }, String(item?.label || ''))
					)
				);
		},
	}),
}));

vi.mock('@/components/analytics/AnalyticsChart.vue', () => ({
	default: defineComponent({
		name: 'AnalyticsChartStub',
		setup() {
			return () => h('div', { 'data-testid': 'analytics-chart' });
		},
	}),
}));

import AcademicLoad from '@/pages/staff/analytics/AcademicLoad.vue';
import router from '@/router';

const cleanupFns: Array<() => void> = [];

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
				return h(AcademicLoad);
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
	filterMetaSubmitMock.mockReset();
	dashboardSubmitMock.mockReset();
	detailSubmitMock.mockReset();
	coverSubmitMock.mockReset();
	toastErrorMock.mockReset();
	while (cleanupFns.length) cleanupFns.pop()?.();
	document.body.innerHTML = '';
});

describe('AcademicLoad route', () => {
	it('registers the canonical academic load analytics route', () => {
		const route = router.getRoutes().find(route => route.name === 'staff-academic-load');
		expect(route?.path).toBe('/staff/analytics/academic-load');
	});
});

describe('AcademicLoad page', () => {
	it('uses FiltersBar and opens the detail drawer from a row click', async () => {
		filterMetaSubmitMock.mockResolvedValue({
			schools: [{ name: 'SCH-1', label: 'School One' }],
			default_school: 'SCH-1',
			academic_years: [{ name: 'AY-1', label: '2026' }],
			default_academic_year: 'AY-1',
			time_modes: [{ value: 'current_week', label: 'Current Week' }],
			staff_roles: [{ value: 'Academic Staff', label: 'Academic Staff' }],
			student_groups: [{ name: 'SG-1', label: 'Physics 8A' }],
			policy: {
				name: 'POL-1',
				school: 'SCH-1',
				meeting_window_days: 30,
				future_horizon_days: 14,
				meeting_blend_mode: 'Blended Past + Future',
				is_system_default: 1,
				was_customized: 0,
			},
		});
		dashboardSubmitMock.mockResolvedValue({
			policy: {
				name: 'POL-1',
				school: 'SCH-1',
				meeting_window_days: 30,
				future_horizon_days: 14,
				meeting_blend_mode: 'Blended Past + Future',
				is_system_default: 1,
				was_customized: 0,
			},
			kpis: [{ id: 'staff_count', label: 'Staff in Scope', value: 1 }],
			rows: [
				{
					educator: { employee: 'EMP-1', full_name: 'Ada Staff', school: 'SCH-1' },
					facts: {
						teaching_hours: 12,
						students_taught: 18,
						activity_hours: 2,
						meeting_weekly_avg_hours: 1,
						event_weekly_avg_hours: 0.5,
						free_blocks_count: 3,
					},
					scores: { total_load_score: 20, teaching_units: 12, non_teaching_units: 3.5 },
					bands: { load_band: 'Normal' },
					availability: { free_blocks_count: 3 },
				},
			],
			fairness: { distribution: [], scatter: [], ranked: [] },
		});
		detailSubmitMock.mockResolvedValue({
			educator: { full_name: 'Ada Staff' },
			facts: {
				teaching_hours: 12,
				students_taught: 18,
				activity_hours: 2,
				meeting_weekly_avg_hours: 1,
				event_weekly_avg_hours: 0.5,
				free_blocks_count: 3,
			},
			scores: { total_load_score: 20 },
			bands: { load_band: 'Normal' },
			breakdown: {
				teaching: [],
				activities: [],
				meetings: [],
				events: [],
				timeline: [],
				assignment_notes: ['Use current load as the tie-breaker.'],
			},
		});

		mountPage();
		await flushUi();

		expect(filterMetaSubmitMock).toHaveBeenCalledTimes(1);
		expect(dashboardSubmitMock).toHaveBeenCalledTimes(1);
		expect(document.querySelector('[data-testid="filters-bar"]')).not.toBeNull();
		expect(document.body.textContent || '').toContain('Academic Load');
		expect(document.body.textContent || '').toContain('Ada Staff');

		const row = Array.from(document.querySelectorAll('tbody tr')).find(element =>
			(element.textContent || '').includes('Ada Staff')
		);
		row?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
		await flushUi();

		expect(detailSubmitMock).toHaveBeenCalledTimes(1);
		expect(document.body.textContent || '').toContain('Academic Load Detail');
	});
});
