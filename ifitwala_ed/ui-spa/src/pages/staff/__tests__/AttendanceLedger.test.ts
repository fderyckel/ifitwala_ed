import { afterEach, describe, expect, it, vi } from 'vitest';
import { createApp, defineComponent, h, nextTick, type App } from 'vue';
import attendanceLedgerSource from '../analytics/AttendanceLedger.vue?raw';

const { fetchAttendanceLedgerContextMock, getLedgerMock } = vi.hoisted(() => ({
	fetchAttendanceLedgerContextMock: vi.fn(),
	getLedgerMock: vi.fn(),
}));

vi.mock('@/lib/services/studentAttendance/studentAttendanceService', () => ({
	createStudentAttendanceService: () => ({
		fetchAttendanceLedgerContext: fetchAttendanceLedgerContextMock,
	}),
}));

vi.mock('@/lib/services/attendance/attendanceAnalyticsService', () => ({
	createAttendanceAnalyticsService: () => ({
		getLedger: getLedgerMock,
	}),
}));

vi.mock('@/components/analytics/AnalyticsCard.vue', () => ({
	default: defineComponent({
		name: 'AnalyticsCardStub',
		props: {
			title: {
				type: String,
				default: '',
			},
		},
		setup(props, { slots }) {
			return () =>
				h('section', [
					h('h2', props.title),
					slots.body?.(),
					slots.default?.(),
				]);
		},
	}),
}));

vi.mock('@/components/filters/FiltersBar.vue', () => ({
	default: defineComponent({
		name: 'FiltersBarStub',
		setup(_, { slots }) {
			return () => h('div', { class: 'filters-bar-stub' }, slots.default?.());
		},
	}),
}));

vi.mock('@/components/filters/DateRangePills.vue', () => ({
	default: defineComponent({
		name: 'DateRangePillsStub',
		setup() {
			return () => h('div', 'DateRangePills');
		},
	}),
}));

import AttendanceLedger from '@/pages/staff/analytics/AttendanceLedger.vue';

const cleanupFns: Array<() => void> = [];

function buildLedgerResponse(page: number, pageLength: number) {
	return {
		meta: {
			role_class: 'admin',
			school_scope: ['SCH-1'],
			date_from: '2026-04-01',
			date_to: '2026-04-30',
			window_source: 'selected_term',
			whole_day: 1,
			activity_only: 0,
		},
		columns: [{ fieldname: 'student_label', label: 'Student', fieldtype: 'Data' }],
		rows: [{ student: `STU-${page}`, student_label: `Student ${page}` }],
		codes: [],
		pagination: {
			page,
			page_length: pageLength,
			total_rows: 120,
			total_pages: pageLength === 80 ? 2 : 3,
		},
		summary: {
			raw_records: 120,
			total_students: 3,
			total_present: 110,
			total_late_present: 7,
			total_attendance: 120,
			percentage_present: 91.7,
			percentage_late: 6.4,
		},
		filter_options: {
			courses: [],
			instructors: [],
			students: [],
		},
	};
}

async function flushUi() {
	await Promise.resolve();
	await nextTick();
	await Promise.resolve();
	await nextTick();
}

async function flushReloadTimer() {
	vi.runOnlyPendingTimers();
	await flushUi();
}

async function waitForEnabled(button: HTMLButtonElement | undefined) {
	for (let index = 0; index < 6 && button?.disabled; index += 1) {
		await flushUi();
	}
}

function mountLedger() {
	const host = document.createElement('div');
	document.body.appendChild(host);

	const app: App = createApp(
		defineComponent({
			render() {
				return h(AttendanceLedger);
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
	vi.clearAllMocks();
	vi.useRealTimers();
});

describe('AttendanceLedger', () => {
	it('does not override the shared analytics shell width', () => {
		expect(attendanceLedgerSource).not.toMatch(/max-width:\s*none\s*;/);
		expect(attendanceLedgerSource).toContain('class="analytics-shell"');
		expect(attendanceLedgerSource).not.toContain('class="analytics-shell attendance-ledger-shell"');
	});

	it('keeps window presets in the page header actions instead of the filter grid', () => {
		expect(attendanceLedgerSource).toMatch(
			/page-header__actions">[\s\S]*<DateRangePills[\s\S]*:model-value="preset"[\s\S]*<\/div>/s
		);
		expect(attendanceLedgerSource).not.toMatch(/<label class="type-label">Window<\/label>/);
		expect(attendanceLedgerSource).not.toMatch(/<DateRangePills[\s\S]*size="sm"/s);
	});

	it('resets to page 1 before reloading when rows per page changes', async () => {
		vi.useFakeTimers();

		fetchAttendanceLedgerContextMock.mockResolvedValue({
			schools: [{ name: 'SCH-1', school_name: 'School 1' }],
			default_school: 'SCH-1',
			programs: [{ name: 'PROG-1', program_name: 'Program 1' }],
			default_program: 'PROG-1',
			academic_years: [{ name: 'AY-2026' }],
			default_academic_year: 'AY-2026',
			terms: [{ name: 'TERM-1' }],
			default_term: 'TERM-1',
			student_groups: [{ name: 'SG-1', student_group_name: 'Group 1' }],
			default_student_group: 'SG-1',
		});
		getLedgerMock.mockImplementation(async (payload: { page?: number; page_length?: number }) =>
			buildLedgerResponse(payload.page ?? 1, payload.page_length ?? 80)
		);

		mountLedger();
		await flushUi();

		expect(getLedgerMock).toHaveBeenNthCalledWith(
			1,
			expect.objectContaining({ page: 1, page_length: 80 })
		);

		const nextButton = Array.from(document.querySelectorAll('button')).find(button =>
			button.textContent?.includes('Next')
		) as HTMLButtonElement | undefined;
		expect(nextButton).toBeTruthy();
		await waitForEnabled(nextButton);
		expect(nextButton?.disabled).toBe(false);

		nextButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
		await flushUi();
		await flushReloadTimer();

		expect(getLedgerMock).toHaveBeenNthCalledWith(
			2,
			expect.objectContaining({ page: 2, page_length: 80 })
		);

		const selects = Array.from(document.querySelectorAll('select'));
		const pageLengthSelect = selects[selects.length - 1] as HTMLSelectElement | undefined;
		expect(pageLengthSelect?.value).toBe('80');

		pageLengthSelect!.value = '50';
		pageLengthSelect!.dispatchEvent(new Event('change'));
		await flushUi();
		await flushReloadTimer();

		expect(getLedgerMock).toHaveBeenLastCalledWith(
			expect.objectContaining({ page: 1, page_length: 50 })
		);
	});
});
