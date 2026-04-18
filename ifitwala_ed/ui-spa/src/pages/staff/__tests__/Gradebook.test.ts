import { afterEach, describe, expect, it, vi } from 'vitest';
import { createApp, defineComponent, h, nextTick, type App } from 'vue';

const {
	routeState,
	replaceMock,
	toastMock,
	fetchSchoolContextMock,
	fetchGroupsMock,
	fetchGroupTasksMock,
	getDrawerMock,
	getGridMock,
	getTaskGradebookMock,
	getTaskQuizManualReviewMock,
	markNewSubmissionSeenMock,
	publishOutcomesMock,
	repairTaskRosterMock,
	saveTaskQuizManualReviewMock,
	unpublishOutcomesMock,
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
	getDrawerMock: vi.fn(),
	getGridMock: vi.fn(),
	getTaskGradebookMock: vi.fn(),
	getTaskQuizManualReviewMock: vi.fn(),
	markNewSubmissionSeenMock: vi.fn(),
	publishOutcomesMock: vi.fn(),
	repairTaskRosterMock: vi.fn(),
	saveTaskQuizManualReviewMock: vi.fn(),
	unpublishOutcomesMock: vi.fn(),
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
		props: [
			'modelValue',
			'type',
			'options',
			'disabled',
			'rows',
			'placeholder',
			'min',
			'max',
			'step',
		],
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
		getDrawer: getDrawerMock,
		getGrid: getGridMock,
		getTaskGradebook: getTaskGradebookMock,
		getTaskQuizManualReview: getTaskQuizManualReviewMock,
		markNewSubmissionSeen: markNewSubmissionSeenMock,
		publishOutcomes: publishOutcomesMock,
		repairTaskRoster: repairTaskRosterMock,
		saveTaskQuizManualReview: saveTaskQuizManualReviewMock,
		unpublishOutcomes: unpublishOutcomesMock,
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
	drawer?: Record<string, unknown>;
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
			procedural_status: null,
			submission_status: null,
			has_submission: 0,
			has_new_submission: 0,
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
				rubric_scoring_strategy: task.rubric_scoring_strategy as
					| 'Sum Total'
					| 'Separate Criteria'
					| null,
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
	getGridMock.mockResolvedValue({ deliveries: [], students: [], cells: [] });
	getTaskGradebookMock.mockResolvedValue({
		task,
		criteria: options?.criteria || [],
		students,
	});
	getDrawerMock.mockResolvedValue({
		delivery: {
			name: String(task.name),
			task: 'TASK-1',
			title: String(task.title),
			task_type: (task.task_type as string | null) || 'Assignment',
			student_group: group.name,
			due_date: task.due_date as string | null,
			delivery_mode: (task.delivery_type as string | null) || 'Assess',
			grading_mode: task.grading_mode as string | null,
			allow_feedback: task.allow_feedback as 0 | 1,
			rubric_scoring_strategy: task.rubric_scoring_strategy as
				| 'Sum Total'
				| 'Separate Criteria'
				| null,
			max_points: task.max_points as number | null,
			criteria:
				(options?.criteria || []).map(criterion => ({
					assessment_criteria: String(criterion.assessment_criteria),
					criteria_name: String(criterion.criteria_name),
					criteria_weighting:
						typeof criterion.criteria_weighting === 'number' ? criterion.criteria_weighting : null,
					levels: Array.isArray(criterion.levels) ? criterion.levels : [],
				})) || [],
		},
		student: {
			student: String(students[0].student),
			student_name: String(students[0].student_name),
			student_id: (students[0].student_id as string | null) || null,
			student_image: (students[0].student_image as string | null) || null,
		},
		outcome: {
			outcome_id: String(students[0].task_student),
			grading_status: (students[0].status as string | null) || 'Not Started',
			procedural_status: (students[0].procedural_status as string | null) || null,
			has_submission: Boolean(students[0].has_submission),
			has_new_submission: Boolean(students[0].has_new_submission),
			is_complete: Boolean(students[0].complete),
			is_published: Boolean(students[0].visible_to_student),
			published_on: null,
			published_by: null,
			official: {
				score: (students[0].mark_awarded as number | null) || null,
				grade: null,
				grade_value: null,
				feedback: (students[0].feedback as string | null) || null,
			},
			criteria: (students[0].criteria_scores as Array<Record<string, unknown>>).map(row => ({
				criteria: String(row.assessment_criteria),
				level: (row.level as string | null) || null,
				points: (row.level_points as number | null) || null,
			})),
		},
		latest_submission: null,
		selected_submission: null,
		submission_versions: [],
		my_contribution: null,
		moderation_history: [],
		allowed_actions: {
			can_edit_marking: true,
			can_mark_submission_seen: true,
			can_publish: true,
			can_unpublish: true,
			can_moderate: false,
			show_review_tab: false,
		},
		submissions: [],
		contributions: [],
		...options?.drawer,
	});
	markNewSubmissionSeenMock.mockResolvedValue({
		ok: true,
		outcome: 'OUT-1',
		has_new_submission: 0,
	});
	publishOutcomesMock.mockResolvedValue({
		outcomes: [
			{ outcome_id: 'OUT-1', is_published: true, published_on: null, published_by: null },
		],
	});
	unpublishOutcomesMock.mockResolvedValue({
		outcomes: [
			{ outcome_id: 'OUT-1', is_published: false, published_on: null, published_by: null },
		],
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

async function openStudentDrawer(studentName = 'Ada Lovelace') {
	const studentButton = Array.from(document.querySelectorAll('button')).find(button =>
		(button.textContent || '').includes(studentName)
	);
	expect(studentButton).not.toBeNull();
	studentButton!.dispatchEvent(new MouseEvent('click', { bubbles: true }));
	await flushUi();
}

async function selectGroup(label: string) {
	const groupButton = Array.from(document.querySelectorAll('button')).find(button =>
		(button.textContent || '').includes(label)
	);
	expect(groupButton).not.toBeNull();
	groupButton!.dispatchEvent(new MouseEvent('click', { bubbles: true }));
	await flushUi();
}

async function switchToOverview() {
	const overviewButton = Array.from(document.querySelectorAll('button')).find(button =>
		(button.textContent || '').includes('Overview')
	);
	expect(overviewButton).not.toBeNull();
	overviewButton!.dispatchEvent(new MouseEvent('click', { bubbles: true }));
	for (let index = 0; index < 10; index += 1) {
		await new Promise(resolve => window.setTimeout(resolve, 10));
		await flushUi();
		if (document.body.textContent?.includes('Class Overview')) {
			break;
		}
	}
}

afterEach(() => {
	routeState.query = {};
	replaceMock.mockClear();
	toastMock.mockClear();
	fetchSchoolContextMock.mockReset();
	fetchGroupsMock.mockReset();
	fetchGroupTasksMock.mockReset();
	getGridMock.mockReset();
	getTaskGradebookMock.mockReset();
	getTaskQuizManualReviewMock.mockReset();
	getDrawerMock.mockReset();
	markNewSubmissionSeenMock.mockReset();
	publishOutcomesMock.mockReset();
	repairTaskRosterMock.mockReset();
	saveTaskQuizManualReviewMock.mockReset();
	unpublishOutcomesMock.mockReset();
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
		getGridMock.mockResolvedValue({ deliveries: [], students: [], cells: [] });
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
		getGridMock.mockResolvedValue({ deliveries: [], students: [], cells: [] });
		getTaskGradebookMock.mockResolvedValue({ task: null, criteria: [], students: [] });

		mountPage();
		await flushUi();

		expect(fetchGroupsMock.mock.calls).toEqual([
			[{ school: 'SCH-1' }],
			[{ search: linkedGroup.name, limit: 20 }],
			[{ school: 'SCH-2' }],
		]);
		expect(fetchGroupTasksMock).toHaveBeenCalledWith({ student_group: linkedGroup.name });

		const schoolSelect = document.querySelector(
			'select[data-placeholder="School"]'
		) as HTMLSelectElement;
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

	it('loads the overview grid only after the teacher switches modes', async () => {
		mockGradebookFlow();
		getGridMock.mockResolvedValue({
			deliveries: [
				{
					delivery_id: 'TDL-1',
					task_title: 'Task 1',
					due_date: '2026-04-03 10:00:00',
					grading_mode: 'Points',
					rubric_scoring_strategy: null,
					delivery_mode: 'Assess',
					allow_feedback: 0,
					max_points: 20,
					task_type: 'Assignment',
				},
			],
			students: [
				{
					student: 'STU-1',
					student_name: 'Ada Lovelace',
					student_id: 'S-001',
					student_image: null,
				},
			],
			cells: [
				{
					outcome_id: 'OUT-1',
					student: 'STU-1',
					delivery_id: 'TDL-1',
					flags: {
						has_submission: false,
						has_new_submission: false,
						grading_status: 'Not Started',
						procedural_status: null,
						is_complete: false,
						is_published: false,
					},
					official: {
						score: null,
						grade: null,
						grade_value: null,
						feedback: null,
						criteria: [],
					},
				},
			],
		});

		mountPage();
		await flushUi();

		expect(getGridMock).not.toHaveBeenCalled();

		await switchToOverview();

		expect(getGridMock).toHaveBeenCalledWith({
			school: 'SCH-1',
			academic_year: '2025-2026',
			student_group: 'SG-1',
			course: 'Math 1',
			task_type: null,
			delivery_mode: null,
			limit: 10,
		});
		expect(document.body.textContent || '').toContain('Class Overview');
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
		await openStudentDrawer();

		const text = document.body.textContent || '';
		expect(getDrawerMock).toHaveBeenCalledWith({
			outcome_id: 'OUT-1',
			submission_id: null,
			version: null,
		});
		expect(text).toContain('Yes/No');
		expect(text).toContain('Yes');
		expect(text).toContain('No');
		expect(text).not.toContain('Points Awarded');
		expect(document.querySelector('textarea')).toBeNull();
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
		await openStudentDrawer();

		const text = document.body.textContent || '';
		expect(text).toContain('Complete');
		expect(text).toContain('Not complete');
		expect(text).not.toContain('Yes / No');
	});

	it('shows release controls inside the official result tab', async () => {
		mockGradebookFlow();

		mountPage();
		await flushUi();
		await openTask('Task 1');
		await openStudentDrawer();

		const officialTab = Array.from(document.querySelectorAll('button')).find(button =>
			(button.textContent || '').includes('Official Result')
		);
		expect(officialTab).toBeTruthy();
		officialTab!.dispatchEvent(new MouseEvent('click', { bubbles: true }));
		await flushUi();

		expect(document.body.textContent || '').toContain('Release');
		expect(document.body.textContent || '').toContain(
			'Current runtime still uses one published state'
		);
	});

	it('shows reduced PDF review state in the evidence tab without guessing file paths', async () => {
		mockGradebookFlow({
			students: [
				{
					task_student: 'OUT-1',
					student: 'STU-1',
					student_name: 'Ada Lovelace',
					student_id: 'S-001',
					student_image: null,
					status: 'Needs Review',
					procedural_status: 'Submitted',
					has_submission: 1,
					has_new_submission: 1,
					complete: 0,
					mark_awarded: 12,
					feedback: null,
					visible_to_student: 0,
					visible_to_guardian: 0,
					updated_on: null,
					criteria_scores: [],
				},
			],
			drawer: {
				latest_submission: {
					submission_id: 'TSU-1',
					version: 2,
					submitted_on: '2026-04-03 10:00:00',
					origin: 'Student Upload',
					is_stub: false,
					is_selected: true,
				},
				selected_submission: {
					submission_id: 'TSU-1',
					version: 2,
					submitted_on: '2026-04-03 10:00:00',
					submitted_by: 'student@example.com',
					origin: 'Student Upload',
					is_stub: false,
					evidence_note: 'Essay PDF',
					is_cloned: false,
					cloned_from: null,
					text_content: null,
					link_url: null,
					attachments: [
						{
							row_name: 'ATT-1',
							kind: 'file',
							file: '/api/method/ifitwala_ed.api.file_access.download_academic_file?file=FILE-TASK-1',
							file_name: 'essay.pdf',
							file_size: 256,
							description: 'Essay PDF',
							preview_status: 'pending',
							preview_url:
								'/api/method/ifitwala_ed.api.file_access.preview_academic_file?file=FILE-TASK-1',
							open_url:
								'/api/method/ifitwala_ed.api.file_access.download_academic_file?file=FILE-TASK-1',
							mime_type: 'application/pdf',
							extension: 'pdf',
						},
					],
					annotation_readiness: {
						mode: 'reduced',
						reason_code: 'pdf_preview_pending',
						title: 'Reduced PDF review mode',
						message:
							'This governed PDF is still generating its preview. Text-anchored annotation is not available in the current runtime yet, so use the source PDF plus drawer marking for now.',
						attachment_row_name: 'ATT-1',
						attachment_file_name: 'essay.pdf',
						preview_status: 'pending',
						preview_url:
							'/api/method/ifitwala_ed.api.file_access.preview_academic_file?file=FILE-TASK-1',
						open_url:
							'/api/method/ifitwala_ed.api.file_access.download_academic_file?file=FILE-TASK-1',
					},
				},
				submission_versions: [
					{
						submission_id: 'TSU-1',
						version: 2,
						submitted_on: '2026-04-03 10:00:00',
						origin: 'Student Upload',
						is_stub: false,
						is_selected: true,
					},
				],
			},
		});

		mountPage();
		await flushUi();
		await openTask('Task 1');
		await openStudentDrawer();

		const evidenceTab = Array.from(document.querySelectorAll('button')).find(button =>
			(button.textContent || '').includes('Evidence')
		);
		expect(evidenceTab).toBeTruthy();
		evidenceTab!.dispatchEvent(new MouseEvent('click', { bubbles: true }));
		await flushUi();

		const text = document.body.textContent || '';
		expect(text).toContain('Annotation Surface');
		expect(text).toContain('PDF Workspace');
		expect(text).toContain('pdf.js surface pending install');
		expect(text).toContain('Reduced mode');
		expect(text).toContain('Source PDF:');
		expect(text).toContain('essay.pdf');
		expect(text).toContain('Preview not available yet');

		const previewLink = Array.from(document.querySelectorAll('a')).find(link =>
			(link.textContent || '').includes('Try preview')
		);
		expect(previewLink?.getAttribute('href')).toContain(
			'/api/method/ifitwala_ed.api.file_access.preview_academic_file'
		);
	});

	it('releases a selected batch of unreleased students from the task workspace', async () => {
		mockGradebookFlow({
			students: [
				{
					task_student: 'OUT-1',
					student: 'STU-1',
					student_name: 'Ada Lovelace',
					student_id: 'S-001',
					student_image: null,
					status: 'Finalized',
					procedural_status: null,
					has_submission: 1,
					has_new_submission: 0,
					complete: 0,
					mark_awarded: 14,
					feedback: null,
					visible_to_student: 0,
					visible_to_guardian: 0,
					updated_on: null,
					criteria_scores: [],
				},
				{
					task_student: 'OUT-2',
					student: 'STU-2',
					student_name: 'Grace Hopper',
					student_id: 'S-002',
					student_image: null,
					status: 'Released',
					procedural_status: null,
					has_submission: 1,
					has_new_submission: 0,
					complete: 0,
					mark_awarded: 18,
					feedback: null,
					visible_to_student: 1,
					visible_to_guardian: 1,
					updated_on: null,
					criteria_scores: [],
				},
			],
		});

		mountPage();
		await flushUi();
		await openTask('Task 1');

		const selectButton = document.querySelector('[data-select-unreleased]');
		expect(selectButton).not.toBeNull();
		selectButton!.dispatchEvent(new MouseEvent('click', { bubbles: true }));
		await flushUi();

		const releaseButton = document.querySelector('[data-release-selected]');
		expect(releaseButton).not.toBeNull();
		releaseButton!.dispatchEvent(new MouseEvent('click', { bubbles: true }));
		await flushUi();

		expect(publishOutcomesMock).toHaveBeenCalledWith({ outcome_ids: ['OUT-1'] });
	});

	it('turns collect-work tasks into an evidence inbox sorted by evidence priority', async () => {
		mockGradebookFlow({
			task: {
				title: 'Science Journal',
				grading_mode: 'None',
				allow_feedback: 1,
				points: 0,
				binary: 0,
				criteria: 0,
				observations: 1,
				max_points: null,
				delivery_type: 'Collect Work',
			},
			students: [
				{
					task_student: 'OUT-4',
					student: 'STU-4',
					student_name: 'Katherine Johnson',
					student_id: 'S-004',
					student_image: null,
					status: 'Not Started',
					procedural_status: 'Submitted',
					submission_status: 'Submitted',
					has_submission: 1,
					has_new_submission: 0,
					complete: 0,
					mark_awarded: null,
					feedback: null,
					visible_to_student: 0,
					visible_to_guardian: 0,
					updated_on: null,
					criteria_scores: [],
				},
				{
					task_student: 'OUT-2',
					student: 'STU-2',
					student_name: 'Grace Hopper',
					student_id: 'S-002',
					student_image: null,
					status: 'Not Started',
					procedural_status: null,
					submission_status: null,
					has_submission: 0,
					has_new_submission: 0,
					complete: 0,
					mark_awarded: null,
					feedback: null,
					visible_to_student: 0,
					visible_to_guardian: 0,
					updated_on: null,
					criteria_scores: [],
				},
				{
					task_student: 'OUT-3',
					student: 'STU-3',
					student_name: 'Alan Turing',
					student_id: 'S-003',
					student_image: null,
					status: 'Needs Review',
					procedural_status: 'Submitted',
					submission_status: 'Late',
					has_submission: 1,
					has_new_submission: 0,
					complete: 0,
					mark_awarded: null,
					feedback: null,
					visible_to_student: 0,
					visible_to_guardian: 0,
					updated_on: null,
					criteria_scores: [],
				},
				{
					task_student: 'OUT-1',
					student: 'STU-1',
					student_name: 'Ada Lovelace',
					student_id: 'S-001',
					student_image: null,
					status: 'Needs Review',
					procedural_status: 'Submitted',
					submission_status: 'Late',
					has_submission: 1,
					has_new_submission: 1,
					complete: 0,
					mark_awarded: null,
					feedback: null,
					visible_to_student: 0,
					visible_to_guardian: 0,
					updated_on: null,
					criteria_scores: [],
				},
			],
		});

		mountPage();
		await flushUi();
		await openTask('Science Journal');

		const text = document.body.textContent || '';
		expect(text).toContain('Evidence Inbox');
		expect(text).toContain('New Evidence (1)');
		expect(text).toContain('Missing (1)');
		expect(text).toContain('Late (2)');

		const studentButtons = Array.from(
			document.querySelectorAll<HTMLElement>('[data-gradebook-student]')
		);
		expect(studentButtons).toHaveLength(4);
		expect(studentButtons.map(button => button.textContent || '')).toEqual([
			expect.stringContaining('Ada Lovelace'),
			expect.stringContaining('Alan Turing'),
			expect.stringContaining('Grace Hopper'),
			expect.stringContaining('Katherine Johnson'),
		]);
		expect(studentButtons[0]?.textContent || '').toContain('Submission: Late');
	});

	it('navigates the collect-work drawer against the current evidence queue order', async () => {
		mockGradebookFlow({
			task: {
				title: 'Reading Log',
				grading_mode: 'None',
				allow_feedback: 1,
				points: 0,
				binary: 0,
				criteria: 0,
				observations: 1,
				max_points: null,
				delivery_type: 'Collect Work',
			},
			students: [
				{
					task_student: 'OUT-3',
					student: 'STU-3',
					student_name: 'Grace Hopper',
					student_id: 'S-003',
					student_image: null,
					status: 'Not Started',
					procedural_status: 'Submitted',
					submission_status: 'Submitted',
					has_submission: 1,
					has_new_submission: 0,
					complete: 0,
					mark_awarded: null,
					feedback: null,
					visible_to_student: 0,
					visible_to_guardian: 0,
					updated_on: null,
					criteria_scores: [],
				},
				{
					task_student: 'OUT-2',
					student: 'STU-2',
					student_name: 'Alan Turing',
					student_id: 'S-002',
					student_image: null,
					status: 'Needs Review',
					procedural_status: 'Submitted',
					submission_status: 'Late',
					has_submission: 1,
					has_new_submission: 0,
					complete: 0,
					mark_awarded: null,
					feedback: null,
					visible_to_student: 0,
					visible_to_guardian: 0,
					updated_on: null,
					criteria_scores: [],
				},
				{
					task_student: 'OUT-1',
					student: 'STU-1',
					student_name: 'Ada Lovelace',
					student_id: 'S-001',
					student_image: null,
					status: 'Needs Review',
					procedural_status: 'Submitted',
					submission_status: 'Late',
					has_submission: 1,
					has_new_submission: 1,
					complete: 0,
					mark_awarded: null,
					feedback: null,
					visible_to_student: 0,
					visible_to_guardian: 0,
					updated_on: null,
					criteria_scores: [],
				},
			],
		});

		mountPage();
		await flushUi();
		await openTask('Reading Log');
		await openStudentDrawer('Ada Lovelace');

		expect(getDrawerMock.mock.calls[0]?.[0]).toEqual({
			outcome_id: 'OUT-1',
			submission_id: null,
			version: null,
		});

		const nextButton = document.querySelector('button[aria-label="Open next student"]');
		expect(nextButton).not.toBeNull();
		nextButton!.dispatchEvent(new MouseEvent('click', { bubbles: true }));
		await flushUi();

		expect(getDrawerMock.mock.calls[1]?.[0]).toEqual({
			outcome_id: 'OUT-2',
			submission_id: null,
			version: null,
		});
		expect(document.body.textContent || '').toContain('Inbox 2 of 3');
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
					procedural_status: null,
					has_submission: 0,
					has_new_submission: 0,
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
		await openStudentDrawer();

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
