import { afterEach, describe, expect, it, vi } from 'vitest';
import { createApp, defineComponent, h, nextTick, type App } from 'vue';

const {
	routeState,
	replaceMock,
	toastMock,
	fetchSchoolContextMock,
	fetchGroupsMock,
	fetchGroupTasksMock,
	getTaskGradebookMock,
	repairTaskRosterMock,
	updateTaskStudentMock,
} = vi.hoisted(() => ({
	routeState: {
		query: {} as Record<string, unknown>,
	},
	replaceMock: vi.fn(() => Promise.resolve()),
	toastMock: vi.fn(),
	fetchSchoolContextMock: vi.fn(),
	fetchGroupsMock: vi.fn(),
	fetchGroupTasksMock: vi.fn(),
	getTaskGradebookMock: vi.fn(),
	repairTaskRosterMock: vi.fn(),
	updateTaskStudentMock: vi.fn(),
}));

vi.mock('vue-router', () => ({
	useRoute: () => routeState,
	useRouter: () => ({
		replace: replaceMock,
	}),
}));

vi.mock('frappe-ui', () => ({
	Button: defineComponent({
		name: 'ButtonStub',
		props: ['disabled', 'loading', 'type', 'appearance', 'icon'],
		emits: ['click'],
		setup(props, { slots, emit, attrs }) {
			return () =>
				h(
					'button',
					{
						...attrs,
						type: props.type || 'button',
						disabled: props.disabled,
						'data-appearance': props.appearance,
						'data-icon': props.icon,
						onClick: (event: MouseEvent) => emit('click', event),
					},
					slots.default?.()
				);
		},
	}),
	Badge: defineComponent({
		name: 'BadgeStub',
		setup(_props, { slots }) {
			return () => h('span', slots.default?.());
		},
	}),
	FeatherIcon: defineComponent({
		name: 'FeatherIconStub',
		props: ['name'],
		setup(props) {
			return () => h('span', { 'data-feather-icon': props.name });
		},
	}),
	Spinner: defineComponent({
		name: 'SpinnerStub',
		setup() {
			return () => h('span', { 'data-spinner': 'true' });
		},
	}),
	FormControl: defineComponent({
		name: 'FormControlStub',
		props: ['modelValue', 'type', 'options', 'disabled', 'rows', 'placeholder', 'min', 'max', 'step'],
		emits: ['update:modelValue'],
		setup(props, { emit }) {
			const resolveOption = (option: unknown) => {
				if (typeof option === 'string') {
					return { label: option, value: option };
				}
				if (option && typeof option === 'object') {
					const row = option as Record<string, unknown>;
					return {
						label: String(row.label ?? ''),
						value: row.value == null ? '' : String(row.value),
					};
				}
				return { label: '', value: '' };
			};

			return () => {
				if (props.type === 'select') {
					return h(
						'select',
						{
							value: props.modelValue == null ? '' : String(props.modelValue),
							disabled: props.disabled,
							'data-placeholder': props.placeholder || '',
							onChange: (event: Event) => {
								const nextValue = (event.target as HTMLSelectElement).value;
								emit('update:modelValue', nextValue || null);
							},
						},
						(props.options || []).map(option => {
							const resolved = resolveOption(option);
							return h('option', { value: resolved.value }, resolved.label);
						})
					);
				}

				if (props.type === 'checkbox') {
					return h('input', {
						type: 'checkbox',
						checked: Boolean(props.modelValue),
						disabled: props.disabled,
						onChange: (event: Event) =>
							emit('update:modelValue', (event.target as HTMLInputElement).checked),
					});
				}

				if (props.type === 'textarea') {
					return h('textarea', {
						value: props.modelValue ?? '',
						rows: props.rows,
						placeholder: props.placeholder,
						disabled: props.disabled,
						onInput: (event: Event) =>
							emit('update:modelValue', (event.target as HTMLTextAreaElement).value),
					});
				}

				return h('input', {
					type: props.type || 'text',
					value: props.modelValue ?? '',
					placeholder: props.placeholder,
					disabled: props.disabled,
					min: props.min,
					max: props.max,
					step: props.step,
					onInput: (event: Event) =>
						emit('update:modelValue', (event.target as HTMLInputElement).value),
				});
			};
		},
	}),
	toast: toastMock,
}));

vi.mock('@/lib/services/gradebook/gradebookService', () => ({
	createGradebookService: () => ({
		fetchGroups: fetchGroupsMock,
		fetchGroupTasks: fetchGroupTasksMock,
		getTaskGradebook: getTaskGradebookMock,
		repairTaskRoster: repairTaskRosterMock,
		updateTaskStudent: updateTaskStudentMock,
	}),
}));

vi.mock('@/lib/services/studentAttendance/studentAttendanceService', () => ({
	createStudentAttendanceService: () => ({
		fetchSchoolContext: fetchSchoolContextMock,
	}),
}));

import Gradebook from '@/pages/staff/gradebook/Gradebook.vue';

const cleanupFns: Array<() => void> = [];

async function flushUi() {
	for (let index = 0; index < 6; index += 1) {
		await Promise.resolve();
		await nextTick();
	}
}

function mountPage() {
	const host = document.createElement('div');
	document.body.appendChild(host);

	const app: App = createApp(
		defineComponent({
			render() {
				return h(Gradebook);
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
	routeState.query = {};
	replaceMock.mockClear();
	toastMock.mockClear();
	fetchSchoolContextMock.mockReset();
	fetchGroupsMock.mockReset();
	fetchGroupTasksMock.mockReset();
	getTaskGradebookMock.mockReset();
	repairTaskRosterMock.mockReset();
	updateTaskStudentMock.mockReset();
	while (cleanupFns.length) cleanupFns.pop()?.();
	document.body.innerHTML = '';
});

describe('Gradebook page', () => {
	it('normalizes school toolbar options to the shared select contract', async () => {
		fetchSchoolContextMock.mockResolvedValue({
			default_school: null,
			schools: [
				{ name: 'SCH-1', school_name: 'Main School' },
				{ name: 'SCH-2', school_name: 'Branch Campus' },
			],
		});
		fetchGroupsMock.mockResolvedValue([]);
		fetchGroupTasksMock.mockResolvedValue({ tasks: [] });
		getTaskGradebookMock.mockResolvedValue({ task: null, criteria: [], students: [] });

		mountPage();
		await flushUi();

		const schoolSelect = document.querySelector('select[data-placeholder="School"]');
		expect(schoolSelect).not.toBeNull();

		const optionTexts = Array.from(schoolSelect?.querySelectorAll('option') || []).map(option =>
			option.textContent?.trim()
		);
		expect(optionTexts).toEqual(['All Schools', 'Main School', 'Branch Campus']);
	});

	it('recovers the linked student group when the default school has no matching groups', async () => {
		const linkedGroup = {
			name: 'SG-2',
			label: 'G6 Math 1 / IIS 2025-2026',
			school: 'SCH-2',
			academic_year: '2025-2026',
			program: 'IIS',
			course: 'Math 1',
			cohort: 'G6',
		};

		routeState.query = { student_group: linkedGroup.name };
		fetchSchoolContextMock.mockResolvedValue({
			default_school: 'SCH-1',
			schools: [
				{ name: 'SCH-1', school_name: 'Default School' },
				{ name: 'SCH-2', school_name: 'KIS Bangkok' },
			],
		});
		fetchGroupsMock.mockImplementation(async (payload?: Record<string, unknown>) => {
			if (payload?.school === 'SCH-1') return [];
			if (payload?.search === linkedGroup.name) return [linkedGroup];
			if (payload?.school === 'SCH-2') return [linkedGroup];
			return [];
		});
		fetchGroupTasksMock.mockResolvedValue({ tasks: [] });
		getTaskGradebookMock.mockResolvedValue({ task: null, criteria: [], students: [] });

		mountPage();
		await flushUi();

		expect(fetchGroupsMock.mock.calls).toEqual([
			[{ school: 'SCH-1' }],
			[{ search: linkedGroup.name, limit: 20 }],
			[{ school: 'SCH-2' }],
		]);
		expect(fetchGroupTasksMock).toHaveBeenCalledWith({ student_group: linkedGroup.name });

		const schoolSelect = document.querySelector('select[data-placeholder="School"]') as HTMLSelectElement;
		const groupSelect = document.querySelector(
			'select[data-placeholder="Select group"]'
		) as HTMLSelectElement;

		expect(schoolSelect.value).toBe('SCH-2');
		expect(groupSelect.value).toBe(linkedGroup.name);
		expect(document.body.textContent || '').toContain(linkedGroup.label);
	});
});
