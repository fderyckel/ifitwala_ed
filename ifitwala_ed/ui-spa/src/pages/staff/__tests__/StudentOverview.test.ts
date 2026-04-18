import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createApp, defineComponent, h, nextTick, type App } from 'vue';
import studentOverviewSource from '../analytics/StudentOverview.vue?raw';

import { emptySnapshot } from '@/pages/staff/analytics/student-overview/constants';

const {
	filterMetaState,
	studentSearchState,
	snapshotState,
	searchFetchMock,
	snapshotSubmitMock,
} = vi.hoisted(() => ({
	filterMetaState: { current: null as any },
	studentSearchState: { current: [] as any[] },
	snapshotState: { current: null as any },
	searchFetchMock: vi.fn(),
	snapshotSubmitMock: vi.fn(),
}));

vi.mock('frappe-ui', async () => {
	const { reactive } = await import('vue');

	return {
		createResource: ({ url }: { url: string }) => {
			if (url.includes('get_filter_meta')) {
				return reactive({
					loading: false,
					data: filterMetaState.current,
					async fetch() {
						return filterMetaState.current;
					},
					async submit() {
						return filterMetaState.current;
					},
				});
			}

			if (url.includes('search_students')) {
				return reactive({
					loading: false,
					data: null as any,
					async fetch(payload: any) {
						searchFetchMock(payload);
						this.loading = true;
						this.data = studentSearchState.current;
						this.loading = false;
						return this.data;
					},
					async submit(payload: any) {
						return this.fetch(payload);
					},
				});
			}

			if (url.includes('get_student_center_snapshot')) {
				return reactive({
					loading: false,
					data: null as any,
					async submit(payload: any) {
						snapshotSubmitMock(payload);
						this.loading = true;
						this.data = snapshotState.current;
						this.loading = false;
						return this.data;
					},
				});
			}

			return reactive({
				loading: false,
				data: null as any,
				async fetch() {
					return null;
				},
				async submit() {
					return null;
				},
			});
		},
	};
});

vi.mock('@/components/filters/FiltersBar.vue', () => ({
	default: defineComponent({
		name: 'FiltersBarStub',
		setup(_props, { attrs, slots }) {
			return () => h('section', { ...attrs }, slots.default?.());
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

import StudentOverview from '@/pages/staff/analytics/StudentOverview.vue';

const cleanupFns: Array<() => void> = [];

function buildSnapshotResponse() {
	return {
		...emptySnapshot,
		meta: {
			...emptySnapshot.meta,
			student: 'STU-001',
			student_name: 'Theo Moreau',
			school: 'SCH-001',
			program: 'PROG-001',
			current_academic_year: '2025-2026',
			view_mode: 'staff',
		},
		identity: {
			...emptySnapshot.identity,
			student: 'STU-001',
			full_name: 'Theo Moreau',
			program_enrollment: {
				name: 'PE-001',
				program: 'PROG-001',
				academic_year: '2025-2026',
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
				return h(StudentOverview);
			},
		})
	);

	app.mount(host);
	cleanupFns.push(() => {
		app.unmount();
		host.remove();
	});
}

function findButton(label: string) {
	return Array.from(document.querySelectorAll('button')).find(button =>
		button.textContent?.includes(label)
	) as HTMLButtonElement | undefined;
}

beforeEach(() => {
	vi.useFakeTimers();
	filterMetaState.current = {
		default_school: 'SCH-001',
		schools: [
			{ name: 'SCH-001', label: 'Ifitwala International School' },
			{ name: 'SCH-002', label: 'Ifitwala Secondary School' },
		],
		programs: [
			{ name: 'PROG-001', label: 'IB MYP G6' },
			{ name: 'PROG-002', label: 'IB MYP G7' },
		],
	};
	studentSearchState.current = [{ student: 'STU-001', student_full_name: 'Theo Moreau' }];
	snapshotState.current = buildSnapshotResponse();
});

afterEach(() => {
	while (cleanupFns.length) {
		const cleanup = cleanupFns.pop();
		cleanup?.();
	}
	vi.clearAllTimers();
	vi.useRealTimers();
	searchFetchMock.mockReset();
	snapshotSubmitMock.mockReset();
	filterMetaState.current = null;
	studentSearchState.current = [];
	snapshotState.current = null;
});

describe('StudentOverview shell contract', () => {
	it('uses the shared FiltersBar component for the top filter row', () => {
		expect(studentOverviewSource).toContain("import FiltersBar from '@/components/filters/FiltersBar.vue';");
		expect(studentOverviewSource).toContain('<FiltersBar class="analytics-filters"');
	});

	it('submits the flat snapshot payload and clears dependent filters when school changes', async () => {
		mountPage();
		await flushUi();

		const filterBar = document.querySelector('[data-testid="student-overview-filter-bar"]');
		expect(filterBar).not.toBeNull();

		const schoolSelect = document.querySelector(
			'[data-testid="student-overview-school-filter"]'
		) as HTMLSelectElement;
		const programSelect = document.querySelector(
			'[data-testid="student-overview-program-filter"]'
		) as HTMLSelectElement;
		const studentSearch = document.querySelector(
			'[data-testid="student-overview-student-search"]'
		) as HTMLInputElement;

		expect(schoolSelect.value).toBe('SCH-001');
		expect(programSelect.value).toBe('');

		programSelect.value = 'PROG-001';
			programSelect.dispatchEvent(new Event('change', { bubbles: true }));
			await flushUi();

			studentSearch.value = 'Theo';
			studentSearch.dispatchEvent(new Event('input', { bubbles: true }));
			vi.advanceTimersByTime(350);
			await flushUi();

		expect(searchFetchMock).toHaveBeenCalledWith({
			search_text: 'Theo',
			school: 'SCH-001',
			program: 'PROG-001',
		});

			const studentSuggestion = findButton('Theo Moreau');
			expect(studentSuggestion).toBeDefined();
			studentSuggestion?.click();
			await flushUi();

		vi.advanceTimersByTime(350);
		await flushUi();

		expect(snapshotSubmitMock).toHaveBeenCalledTimes(1);
		expect(snapshotSubmitMock).toHaveBeenLastCalledWith({
			student: 'STU-001',
			school: 'SCH-001',
			program: 'PROG-001',
			view_mode: 'staff',
		});

		schoolSelect.value = 'SCH-002';
			schoolSelect.dispatchEvent(new Event('change', { bubbles: true }));
			await flushUi();

		expect(programSelect.value).toBe('');
		expect(studentSearch.value).toBe('');

		vi.advanceTimersByTime(350);
		await flushUi();

		expect(snapshotSubmitMock).toHaveBeenCalledTimes(1);
	});
});
