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
	getTaskQuizManualReviewMock,
	repairTaskRosterMock,
	saveTaskQuizManualReviewMock,
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
	getTaskQuizManualReviewMock: vi.fn(),
	repairTaskRosterMock: vi.fn(),
	saveTaskQuizManualReviewMock: vi.fn(),
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
		getTaskQuizManualReview: getTaskQuizManualReviewMock,
		repairTaskRoster: repairTaskRosterMock,
		saveTaskQuizManualReview: saveTaskQuizManualReviewMock,
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

function mockGradebookFlow(options?: {
	task?: Record<string, unknown>;
	students?: Array<Record<string, unknown>>;
	criteria?: Array<Record<string, unknown>>;
}) {
	const group = {
		name: 'SG-1',
		label: 'G6 Math',
		school: 'SCH-1',
		academic_year: '2025-2026',
		program: 'IIS',
		course: 'Math 1',
		cohort: 'G6',
	};

	const task = {
		name: 'TDL-1',
		title: 'Task 1',
		student_group: group.name,
		due_date: '2026-04-03 10:00:00',
		grading_mode: 'Points',
		allow_feedback: 0,
		rubric_scoring_strategy: null,
		points: 1,
		binary: 0,
		criteria: 0,
		observations: 0,
		max_points: 20,
		task_type: 'Assignment',
		delivery_type: 'Assess',
		...options?.task,
	};

	const students = options?.students || [
		{
			task_student: 'OUT-1',
			student: 'STU-1',
			student_name: 'Ada Lovelace',
			student_id: 'S-001',
			student_image: null,
			status: 'Not Started',
			complete: 0,
			mark_awarded: null,
			feedback: null,
			visible_to_student: 0,
			visible_to_guardian: 0,
			updated_on: null,
			criteria_scores: [],
		},
	];

	routeState.query = { student_group: group.name };
	fetchSchoolContextMock.mockResolvedValue({
		default_school: 'SCH-1',
		schools: [{ name: 'SCH-1', school_name: 'Main School' }],
	});
	fetchGroupsMock.mockResolvedValue([group]);
	fetchGroupTasksMock.mockResolvedValue({
		tasks: [
			{
				name: String(task.name),
				title: String(task.title),
				due_date: task.due_date as string | null,
				status: null,
				grading_mode: task.grading_mode as string | null,
				allow_feedback: task.allow_feedback as 0 | 1,
				rubric_scoring_strategy: task.rubric_scoring_strategy as 'Sum Total' | 'Separate Criteria' | null,
				points: task.points as 0 | 1,
				binary: task.binary as 0 | 1,
				criteria: task.criteria as 0 | 1,
				observations: task.observations as 0 | 1,
				max_points: task.max_points as number | null,
				task_type: task.task_type as string | null,
				delivery_type: task.delivery_type as string | null,
			},
		],
	});
	getTaskGradebookMock.mockResolvedValue({
		task,
		criteria: options?.criteria || [],
		students,
	});

	return { group, task };
}

async function openTask(title: string) {
	const taskButton = Array.from(document.querySelectorAll('button')).find(button =>
		(button.textContent || '').includes(title)
	);
	expect(taskButton).not.toBeNull();
	taskButton!.dispatchEvent(new MouseEvent('click', { bubbles: true }));
	await flushUi();
}

afterEach(() => {
	routeState.query = {};
	replaceMock.mockClear();
	toastMock.mockClear();
	fetchSchoolContextMock.mockReset();
	fetchGroupsMock.mockReset();
	fetchGroupTasksMock.mockReset();
	getTaskGradebookMock.mockReset();
	getTaskQuizManualReviewMock.mockReset();
	repairTaskRosterMock.mockReset();
	saveTaskQuizManualReviewMock.mockReset();
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

	it('preselects the linked assigned work when a task query is provided', async () => {
		const { task } = mockGradebookFlow();
		routeState.query = { student_group: 'SG-1', task: task.name };

		mountPage();
		await flushUi();

		expect(fetchGroupTasksMock).toHaveBeenCalledWith({ student_group: 'SG-1' });
		expect(getTaskGradebookMock).toHaveBeenCalledWith({ task: task.name });
		expect(document.body.textContent || '').toContain('Ada Lovelace');
	});

	it('renders binary grading without points or comment controls when comments are disabled', async () => {
		mockGradebookFlow({
			task: {
				title: 'Binary check',
				grading_mode: 'Binary',
				allow_feedback: 0,
				points: 0,
				binary: 1,
				criteria: 0,
				max_points: null,
			},
		});

		mountPage();
		await flushUi();
		await openTask('Binary check');

		const text = document.body.textContent || '';
		expect(text).toContain('Yes / No');
		expect(text).toContain('Yes');
		expect(text).toContain('No');
		expect(text).not.toContain('Points Awarded');
		expect(text).not.toContain('Comment');
	});

	it('renders completion grading with complete copy instead of yes/no copy', async () => {
		mockGradebookFlow({
			task: {
				title: 'Completion check',
				grading_mode: 'Completion',
				allow_feedback: 0,
				points: 0,
				binary: 1,
				criteria: 0,
				max_points: null,
			},
		});

		mountPage();
		await flushUi();
		await openTask('Completion check');

		const text = document.body.textContent || '';
		expect(text).toContain('Complete');
		expect(text).toContain('Not complete');
		expect(text).not.toContain('Yes / No');
	});

	it('renders student visibility checkboxes inline in the student header', async () => {
		mockGradebookFlow();

		mountPage();
		await flushUi();
		await openTask('Task 1');

		const studentName = Array.from(document.querySelectorAll('p')).find(node =>
			(node.textContent || '').includes('Ada Lovelace')
		);
		expect(studentName).not.toBeNull();

		const studentHeader = studentName?.closest('div.border-b');
		expect(studentHeader).not.toBeNull();

		const visibilityRow = studentHeader?.querySelector('.gradebook-student-visibility');
		expect(visibilityRow).not.toBeNull();
		expect(visibilityRow?.textContent || '').toContain('Visible to Student');
		expect(visibilityRow?.textContent || '').toContain('Visible to Guardian');
		expect(visibilityRow?.querySelectorAll('input[type="checkbox"]').length).toBe(2);
		expect(document.body.textContent || '').not.toContain('Visibility');
	});

	it('renders criteria grading with criteria controls and comment box only when enabled', async () => {
		mockGradebookFlow({
			task: {
				title: 'Rubric task',
				grading_mode: 'Criteria',
				allow_feedback: 1,
				rubric_scoring_strategy: 'Separate Criteria',
				points: 0,
				binary: 0,
				criteria: 1,
				max_points: null,
			},
			criteria: [
				{
					assessment_criteria: 'CRIT-1',
					criteria_name: 'Clarity',
					criteria_weighting: 50,
					levels: [{ level: 'Secure', points: 4 }],
				},
			],
			students: [
				{
					task_student: 'OUT-1',
					student: 'STU-1',
					student_name: 'Ada Lovelace',
					student_id: 'S-001',
					student_image: null,
					status: 'Not Started',
					complete: 0,
					mark_awarded: null,
					feedback: 'Strong reflection.',
					visible_to_student: 0,
					visible_to_guardian: 0,
					updated_on: null,
					criteria_scores: [
						{
							assessment_criteria: 'CRIT-1',
							level: 'Secure',
							level_points: 4,
							feedback: null,
						},
					],
				},
			],
		});

		mountPage();
		await flushUi();
		await openTask('Rubric task');

		const text = document.body.textContent || '';
		expect(text).toContain('Criteria Breakdown');
		expect(text).toContain('Comment');
		expect(text).not.toContain('Points Awarded');
		expect(text).not.toContain('Max Points:');
	});

	it('routes assessed quiz tasks into the open-ended review panel', async () => {
		mockGradebookFlow({
			task: {
				title: 'Quiz reflection',
				task_type: 'Quiz',
				grading_mode: 'Points',
				points: 1,
				binary: 0,
				criteria: 0,
				max_points: 4,
				delivery_type: 'Assess',
			},
		});
		getTaskQuizManualReviewMock.mockResolvedValue({
			task: {
				name: 'TDL-1',
				title: 'Quiz reflection',
				student_group: 'SG-1',
				max_points: 4,
				pass_percentage: 70,
			},
			summary: {
				manual_item_count: 1,
				pending_item_count: 1,
				pending_student_count: 1,
				pending_attempt_count: 1,
			},
			view_mode: 'question',
			questions: [
				{
					quiz_question: 'QQ-1',
					title: 'Explain the strategy',
					manual_item_count: 1,
					pending_item_count: 1,
				},
			],
			students: [
				{
					student: 'STU-1',
					student_name: 'Ada Lovelace',
					student_id: 'S-001',
					student_image: null,
					manual_item_count: 1,
					pending_item_count: 1,
				},
			],
			selected_question: {
				quiz_question: 'QQ-1',
				title: 'Explain the strategy',
			},
			selected_student: null,
			rows: [
				{
					item_id: 'QAI-1',
					quiz_attempt: 'QAT-1',
					task_outcome: 'OUT-1',
					attempt_number: 1,
					attempt_status: 'Needs Review',
					submitted_on: '2026-04-08 11:00:00',
					student: 'STU-1',
					student_name: 'Ada Lovelace',
					student_id: 'S-001',
					student_image: null,
					grading_status: 'Needs Review',
					quiz_question: 'QQ-1',
					title: 'Explain the strategy',
					position: 1,
					question_type: 'Essay',
					prompt_html: '<p>Explain the strategy.</p>',
					response_text: 'I compared both approaches.',
					selected_option_ids: [],
					selected_option_labels: [],
					awarded_score: null,
					requires_manual_grading: 1,
				},
			],
		});

		mountPage();
		await flushUi();
		await openTask('Quiz reflection');

		expect(getTaskQuizManualReviewMock).toHaveBeenCalledWith({
			task: 'TDL-1',
			view_mode: 'question',
			quiz_question: null,
			student: null,
		});
		expect(document.body.textContent || '').toContain('Open-ended Quiz Review');
		expect(document.body.textContent || '').toContain('Save Score');
		expect(document.body.textContent || '').toContain('Ada Lovelace');
	});
});
