import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createApp, defineComponent, h, nextTick, type App } from 'vue';

const MISSING_ACTIVE_PLAN_MESSAGE =
	'This class needs an active Class Teaching Plan before assigned work can be created.';

const {
	routerPushMock,
	toastCreateMock,
	closeMock,
	createNewTaskCalls,
	assignExistingTaskCalls,
	searchReusableTaskCalls,
	getReusableTaskCalls,
	resourceState,
} = vi.hoisted(() => ({
	routerPushMock: vi.fn(),
	toastCreateMock: vi.fn(),
	closeMock: vi.fn(),
	createNewTaskCalls: [] as any[],
	assignExistingTaskCalls: [] as any[],
	searchReusableTaskCalls: [] as any[],
	getReusableTaskCalls: [] as any[],
	resourceState: {
		courseCriteriaRows: [] as any[],
		createNewTaskResult: {
			task: 'TASK-NEW-1',
			task_delivery: 'TDL-NEW-1',
			outcomes_created: 24,
		},
		createNewTaskError: null as any,
		assignExistingTaskResult: {
			task: 'TASK-SHARED-1',
			task_delivery: 'TDL-SHARED-1',
			outcomes_created: 24,
		},
		searchReusableTasksRows: [
			{
				name: 'TASK-SHARED-1',
				title: 'Shared reading response',
				task_type: 'Homework',
				default_course: 'COURSE-1',
				unit_plan: 'UNIT-1',
				owner: 'colleague@example.com',
				is_template: 1,
				modified: '2026-04-05 10:00:00',
				visibility_scope: 'shared',
				visibility_label: 'Shared with course team',
			},
		],
		reusableTaskDetail: {
			name: 'TASK-SHARED-1',
			title: 'Shared reading response',
			instructions: 'Annotate the article and answer the prompts.',
			task_type: 'Homework',
			default_course: 'COURSE-1',
			unit_plan: 'UNIT-1',
			owner: 'colleague@example.com',
			is_template: 1,
			visibility_scope: 'shared',
			default_delivery_mode: 'Collect Work',
			grading_defaults: {
				default_allow_feedback: 1,
				default_grading_mode: 'Completion',
				default_rubric_scoring_strategy: null,
				default_max_points: null,
				default_grade_scale: null,
			},
			criteria_defaults: {
				rubric_scoring_strategy: null,
				criteria_rows: [],
			},
			quiz_defaults: {},
		},
		taskMaterialsRows: [] as any[],
	},
}));

vi.mock('@headlessui/vue', () => {
	const passthrough = (tag = 'div') =>
		defineComponent({
			name: `Stub${tag}`,
			props: ['as', 'show'],
			setup(props, { slots, attrs }) {
				return () => {
					if (props.show === false) return null;
					return h(props.as && props.as !== 'template' ? props.as : tag, attrs, slots.default?.());
				};
			},
		});

	return {
		Dialog: passthrough('div'),
		DialogPanel: passthrough('div'),
		DialogTitle: passthrough('h2'),
		TransitionChild: passthrough('div'),
		TransitionRoot: passthrough('div'),
	};
});

vi.mock('vue-router', () => ({
	useRouter: () => ({
		push: routerPushMock,
	}),
}));

vi.mock('frappe-ui', async () => {
	const { defineComponent, h } = await import('vue');

	const createResource = (config: {
		url: string;
		onSuccess?: (payload: any) => void;
		onError?: (error: any) => void;
	}) => {
		if (config.url === 'ifitwala_ed.api.quiz.list_question_banks') {
			return {
				loading: false,
				submit: async () => {
					config.onSuccess?.([]);
					return [];
				},
			};
		}
		if (config.url === 'ifitwala_ed.api.task.search_reusable_tasks') {
			return {
				loading: false,
				submit: async (payload: any) => {
					searchReusableTaskCalls.push(payload);
					config.onSuccess?.(resourceState.searchReusableTasksRows);
					return resourceState.searchReusableTasksRows;
				},
			};
		}
		if (config.url === 'ifitwala_ed.api.task.get_task_for_delivery') {
			return {
				loading: false,
				submit: async (payload: any) => {
					getReusableTaskCalls.push(payload);
					config.onSuccess?.(resourceState.reusableTaskDetail);
					return resourceState.reusableTaskDetail;
				},
			};
		}
		if (config.url === 'ifitwala_ed.api.task.list_course_assessment_criteria') {
			return {
				loading: false,
				submit: async () => {
					config.onSuccess?.(resourceState.courseCriteriaRows);
					return resourceState.courseCriteriaRows;
				},
			};
		}
		if (config.url === 'ifitwala_ed.api.task.create_task_delivery') {
			return {
				loading: false,
				submit: async (payload: any) => {
					assignExistingTaskCalls.push(payload);
					config.onSuccess?.(resourceState.assignExistingTaskResult);
					return resourceState.assignExistingTaskResult;
				},
			};
		}
		if (config.url === 'ifitwala_ed.assessment.task_creation_service.create_task_and_delivery') {
			return {
				loading: false,
				submit: async (payload: any) => {
					createNewTaskCalls.push(payload);
					if (resourceState.createNewTaskError) {
						config.onError?.(resourceState.createNewTaskError);
						throw resourceState.createNewTaskError;
					}
					config.onSuccess?.(resourceState.createNewTaskResult);
					return resourceState.createNewTaskResult;
				},
			};
		}
		if (config.url === 'ifitwala_ed.api.materials.list_task_materials') {
			return {
				loading: false,
				submit: async () => {
					config.onSuccess?.({ materials: resourceState.taskMaterialsRows });
					return { materials: resourceState.taskMaterialsRows };
				},
			};
		}
		return {
			loading: false,
			submit: async () => {
				config.onSuccess?.({ materials: [] });
				return { materials: [] };
			},
		};
	};

	return {
		Button: defineComponent({
			name: 'ButtonStub',
			props: ['disabled', 'loading', 'appearance'],
			emits: ['click'],
			setup(props, { slots, emit }) {
				return () =>
					h(
						'button',
						{
							disabled: props.disabled,
							onClick: (event: MouseEvent) => emit('click', event),
						},
						slots.default?.()
					);
			},
		}),
		FormControl: defineComponent({
			name: 'FormControlStub',
			props: {
				modelValue: {
					type: [String, Number, Boolean],
					required: false,
					default: '',
				},
				type: {
					type: String,
					required: false,
					default: 'text',
				},
				options: {
					type: Array,
					required: false,
					default: () => [],
				},
				optionLabel: {
					type: String,
					required: false,
					default: 'label',
				},
				optionValue: {
					type: String,
					required: false,
					default: 'value',
				},
				placeholder: {
					type: String,
					required: false,
					default: '',
				},
				rows: {
					type: Number,
					required: false,
					default: 3,
				},
				disabled: {
					type: Boolean,
					required: false,
					default: false,
				},
			},
			emits: ['update:modelValue'],
			setup(props, { emit }) {
				return () => {
					if (props.type === 'textarea') {
						return h('textarea', {
							value: props.modelValue ?? '',
							placeholder: props.placeholder,
							rows: props.rows,
							onInput: (event: Event) =>
								emit('update:modelValue', (event.target as HTMLTextAreaElement).value),
						});
					}
					if (props.type === 'select') {
						const options = Array.isArray(props.options) ? props.options : [];
						return h(
							'select',
							{
								value: props.modelValue ?? '',
								disabled: props.disabled,
								onChange: (event: Event) =>
									emit('update:modelValue', (event.target as HTMLSelectElement).value),
							},
							[
								h('option', { value: '' }, props.placeholder || ''),
								...options.map((option: any) =>
									h(
										'option',
										{ value: option?.[props.optionValue] ?? option?.value ?? '' },
										String(option?.[props.optionLabel] ?? option?.label ?? option ?? '')
									)
								),
							]
						);
					}
					return h('input', {
						type: props.type === 'number' ? 'number' : 'text',
						value: props.modelValue ?? '',
						placeholder: props.placeholder,
						disabled: props.disabled,
						onInput: (event: Event) =>
							emit('update:modelValue', (event.target as HTMLInputElement).value),
					});
				};
			},
		}),
		FeatherIcon: defineComponent({
			name: 'FeatherIconStub',
			setup() {
				return () => h('span');
			},
		}),
		createResource,
		toast: {
			create: toastCreateMock,
		},
	};
});

import CreateTaskDeliveryOverlay from '@/components/tasks/CreateTaskDeliveryOverlay.vue';

const cleanupFns: Array<() => void> = [];

async function flushUi() {
	await Promise.resolve();
	await nextTick();
	await Promise.resolve();
	await nextTick();
}

function findButton(text: string) {
	const buttons = Array.from(document.querySelectorAll('button')) as HTMLButtonElement[];
	return (
		buttons.find(button => (button.textContent || '').trim() === text) ||
		buttons.find(button => (button.textContent || '').includes(text))
	);
}

async function clickButton(text: string) {
	const button = findButton(text);
	expect(button).toBeTruthy();
	button!.dispatchEvent(new MouseEvent('click', { bubbles: true }));
	await flushUi();
}

async function setInput(placeholder: string, value: string) {
	const input = document.querySelector(`[placeholder="${placeholder}"]`) as HTMLInputElement | null;
	expect(input).not.toBeNull();
	input!.value = value;
	input!.dispatchEvent(new Event('input', { bubbles: true }));
	await flushUi();
}

async function setSelect(selector: string, value: string) {
	const select = document.querySelector(selector) as HTMLSelectElement | null;
	expect(select).not.toBeNull();
	select!.value = value;
	select!.dispatchEvent(new Event('change', { bubbles: true }));
	await flushUi();
}

function mountOverlay(props: Record<string, unknown> = {}) {
	const host = document.createElement('div');
	document.body.appendChild(host);

	const app: App = createApp(
		defineComponent({
			render() {
				return h(CreateTaskDeliveryOverlay, {
					open: true,
					prefillStudentGroup: 'GRP-1',
					onClose: closeMock,
					...props,
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

beforeEach(() => {
	createNewTaskCalls.length = 0;
	assignExistingTaskCalls.length = 0;
	searchReusableTaskCalls.length = 0;
	getReusableTaskCalls.length = 0;
	resourceState.createNewTaskResult = {
		task: 'TASK-NEW-1',
		task_delivery: 'TDL-NEW-1',
		outcomes_created: 24,
	};
	resourceState.createNewTaskError = null;
	resourceState.assignExistingTaskResult = {
		task: 'TASK-SHARED-1',
		task_delivery: 'TDL-SHARED-1',
		outcomes_created: 24,
	};
	resourceState.searchReusableTasksRows = [
		{
			name: 'TASK-SHARED-1',
			title: 'Shared reading response',
			task_type: 'Homework',
			default_course: 'COURSE-1',
			unit_plan: 'UNIT-1',
			owner: 'colleague@example.com',
			is_template: 1,
			modified: '2026-04-05 10:00:00',
			visibility_scope: 'shared',
			visibility_label: 'Shared with course team',
		},
	];
	resourceState.reusableTaskDetail = {
		name: 'TASK-SHARED-1',
		title: 'Shared reading response',
		instructions: 'Annotate the article and answer the prompts.',
		task_type: 'Homework',
		default_course: 'COURSE-1',
		unit_plan: 'UNIT-1',
		owner: 'colleague@example.com',
		is_template: 1,
		visibility_scope: 'shared',
		default_delivery_mode: 'Collect Work',
		grading_defaults: {
			default_allow_feedback: 1,
			default_grading_mode: 'Completion',
			default_rubric_scoring_strategy: null,
			default_max_points: null,
			default_grade_scale: null,
		},
		criteria_defaults: {
			rubric_scoring_strategy: null,
			criteria_rows: [],
		},
		quiz_defaults: {},
	};
	resourceState.courseCriteriaRows = [];
	resourceState.taskMaterialsRows = [];
});

afterEach(() => {
	routerPushMock.mockReset();
	toastCreateMock.mockReset();
	closeMock.mockReset();
	while (cleanupFns.length) cleanupFns.pop()?.();
	document.body.innerHTML = '';
});

describe('CreateTaskDeliveryOverlay', () => {
	it('explains that comments are an additive gradebook option', async () => {
		mountOverlay();
		await flushUi();

		const text = document.body.textContent || '';
		expect(text).toContain('Allow comment in gradebook?');
		expect(text).toContain('Comments stay separate from points, criteria, or completion.');
	});

	it('shows the explicit share-with-course-team choice for new tasks', async () => {
		mountOverlay();
		await flushUi();

		const text = document.body.textContent || '';
		expect(text).toContain('Share this task with other teachers on this course');
		expect(text).toContain('You can still reuse it across your own groups and future school years.');
	});

	it('turns missing class planning validation into an actionable recovery path', async () => {
		resourceState.createNewTaskError = {
			message: '/api/method/ifitwala_ed.assessment.task_creation_service.create_task_and_delivery ValidationError',
			response: {
				_server_messages: JSON.stringify([JSON.stringify({ message: MISSING_ACTIVE_PLAN_MESSAGE })]),
			},
		};

		mountOverlay();
		await flushUi();

		await setInput('Assignment title', 'Microscope reflection');
		await clickButton('Create');

		const text = document.body.textContent || '';
		expect(text).toContain('Open Class Planning for this class, create or activate the plan');
		expect(text).toContain('Open class planning');

		await clickButton('Open class planning');

		expect(closeMock).toHaveBeenCalledWith('programmatic');
		expect(routerPushMock).toHaveBeenCalledWith({
			name: 'staff-class-planning',
			params: { studentGroup: 'GRP-1' },
		});
	});

	it('assigns an existing reusable task without reopening the task-material editor', async () => {
		mountOverlay();
		await flushUi();

		await clickButton('Reuse existing task');

		expect(searchReusableTaskCalls).toHaveLength(1);
		expect(searchReusableTaskCalls[0]).toMatchObject({
			student_group: 'GRP-1',
			scope: 'all',
		});

		const text = document.body.textContent || '';
		expect(text).toContain('Shared reading response');
		expect(text).toContain('Shared with course team');

		await clickButton('Shared reading response');

		expect(getReusableTaskCalls).toHaveLength(1);
		expect(getReusableTaskCalls[0]).toEqual({
			task: 'TASK-SHARED-1',
			student_group: 'GRP-1',
		});

		await clickButton('Assign existing task');

		expect(assignExistingTaskCalls).toHaveLength(1);
		expect(assignExistingTaskCalls[0]).toMatchObject({
			task: 'TASK-SHARED-1',
			student_group: 'GRP-1',
			delivery_mode: 'Collect Work',
			grading_mode: 'Completion',
			allow_feedback: 1,
		});
		expect(createNewTaskCalls).toHaveLength(0);

		const successText = document.body.textContent || '';
		expect(successText).toContain('Assigned work ready');
		expect(successText).not.toContain('Add task materials');
		expect(successText).toContain('Add any class-specific resources in Class Planning');
	});

	it('creates a criteria task with course criteria and a local rubric strategy', async () => {
		resourceState.courseCriteriaRows = [
			{
				assessment_criteria: 'CRIT-ANALYSIS',
				criteria_name: 'Analysis',
				criteria_weighting: 40,
				criteria_max_points: 8,
				levels: [{ level: '1' }, { level: '2' }, { level: '3' }, { level: '4' }],
			},
			{
				assessment_criteria: 'CRIT-COMMUNICATION',
				criteria_name: 'Communication',
				criteria_weighting: 60,
				criteria_max_points: 10,
				levels: [{ level: '1' }, { level: '2' }, { level: '3' }, { level: '4' }],
			},
		];

		mountOverlay();
		await flushUi();

		await setInput('Assignment title', 'Essay checkpoint');
		await clickButton('Collect and assess');
		await clickButton('Yes');
		await clickButton('Criteria');
		await setSelect('[data-rubric-strategy-select="true"]', 'Sum Total');
		await setSelect('[data-criteria-library-select="true"]', 'CRIT-ANALYSIS');
		await clickButton('Add criterion');
		await setSelect('[data-criteria-library-select="true"]', 'CRIT-COMMUNICATION');
		await clickButton('Add criterion');
		await clickButton('Create');

		expect(createNewTaskCalls).toHaveLength(1);
		expect(createNewTaskCalls[0]).toMatchObject({
			title: 'Essay checkpoint',
			student_group: 'GRP-1',
			delivery_mode: 'Assess',
			grading_mode: 'Criteria',
			rubric_scoring_strategy: 'Sum Total',
			criteria_rows: [
				{
					assessment_criteria: 'CRIT-ANALYSIS',
					criteria_weighting: 40,
					criteria_max_points: 8,
				},
				{
					assessment_criteria: 'CRIT-COMMUNICATION',
					criteria_weighting: 60,
					criteria_max_points: 10,
				},
			],
		});
	});

	it('reuses criteria tasks while allowing only the local delivery strategy to change', async () => {
		resourceState.reusableTaskDetail = {
			name: 'TASK-SHARED-1',
			title: 'Shared essay rubric',
			instructions: 'Write and justify your position.',
			task_type: 'Assignment',
			default_course: 'COURSE-1',
			unit_plan: 'UNIT-1',
			owner: 'colleague@example.com',
			is_template: 1,
			visibility_scope: 'shared',
			default_delivery_mode: 'Assess',
			grading_defaults: {
				default_allow_feedback: 1,
				default_grading_mode: 'Criteria',
				default_rubric_scoring_strategy: 'Sum Total',
				default_max_points: null,
				default_grade_scale: null,
			},
			criteria_defaults: {
				rubric_scoring_strategy: 'Sum Total',
				criteria_rows: [
					{
						assessment_criteria: 'CRIT-ANALYSIS',
						criteria_name: 'Analysis',
						criteria_weighting: 40,
						criteria_max_points: 8,
						levels: [{ level: '1' }, { level: '2' }, { level: '3' }, { level: '4' }],
					},
				],
			},
			quiz_defaults: {},
		};

		mountOverlay();
		await flushUi();

		await clickButton('Reuse existing task');
		await clickButton('Shared reading response');
		await setSelect('[data-rubric-strategy-select="true"]', 'Separate Criteria');
		await clickButton('Assign existing task');

		expect(assignExistingTaskCalls).toHaveLength(1);
		expect(assignExistingTaskCalls[0]).toMatchObject({
			task: 'TASK-SHARED-1',
			student_group: 'GRP-1',
			delivery_mode: 'Assess',
			grading_mode: 'Criteria',
			rubric_scoring_strategy: 'Separate Criteria',
		});

		const text = document.body.textContent || '';
		expect(text).toContain('Reusable task criteria');
		expect(text).toContain('change only the delivery strategy for this class');
	});

	it('renders governed preview actions for current task materials after task creation', async () => {
		resourceState.taskMaterialsRows = [
			{
				placement: 'PLACEMENT-IMG',
				material: 'MAT-IMG',
				title: 'Specimen photo',
				material_type: 'File',
				file_name: 'specimen-photo.png',
				file_size: 4096,
				preview_url: '/api/method/ifitwala_ed.api.file_access.preview_academic_file?file=FILE-IMG',
				open_url: '/api/method/ifitwala_ed.api.file_access.download_academic_file?file=FILE-IMG',
			},
			{
				placement: 'PLACEMENT-PDF',
				material: 'MAT-PDF',
				title: 'Lab guide',
				material_type: 'File',
				file_name: 'lab-guide.pdf',
				file_size: 8192,
				preview_url: '/api/method/ifitwala_ed.api.file_access.preview_academic_file?file=FILE-PDF',
				open_url: '/api/method/ifitwala_ed.api.file_access.download_academic_file?file=FILE-PDF',
			},
		];

		mountOverlay();
		await flushUi();

		await setInput('Assignment title', 'Microscope reflection');
		await clickButton('Create');

		expect(document.body.textContent || '').toContain('Current task materials');
		const imagePreview = document.querySelector('[data-task-material-preview-kind="image"] img');
		expect(imagePreview?.getAttribute('src')).toBe(
			'/api/method/ifitwala_ed.api.file_access.preview_academic_file?file=FILE-IMG'
		);

		const pdfPreview = document.querySelector('[data-task-material-preview-kind="pdf"]');
		expect(pdfPreview?.getAttribute('href')).toBe(
			'/api/method/ifitwala_ed.api.file_access.preview_academic_file?file=FILE-PDF'
		);

		const openOriginalLinks = Array.from(document.querySelectorAll('a')).filter(anchor =>
			(anchor.textContent || '').includes('Open original')
		);
		expect(openOriginalLinks.length).toBeGreaterThan(0);
		expect(openOriginalLinks[0]?.getAttribute('href')).toContain(
			'/api/method/ifitwala_ed.api.file_access.download_academic_file?file='
		);
	});
});
