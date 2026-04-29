import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createApp, defineComponent, h, nextTick, type App } from 'vue';

const MISSING_ACTIVE_PLAN_MESSAGE =
	'This class needs an active Class Teaching Plan before assigned work can be created.';

const {
	routerPushMock,
	apiUploadMock,
	emitTaskDeliveryCreatedSignalMock,
	closeMock,
	createNewTaskCalls,
	createTaskReferenceMaterialCalls,
	assignExistingTaskCalls,
	uploadedTaskMaterialCalls,
	searchReusableTaskCalls,
	getReusableTaskCalls,
	assessmentSetupCalls,
	resourceState,
} = vi.hoisted(() => ({
	routerPushMock: vi.fn(),
	apiUploadMock: vi.fn(),
	emitTaskDeliveryCreatedSignalMock: vi.fn(),
	closeMock: vi.fn(),
	createNewTaskCalls: [] as any[],
	createTaskReferenceMaterialCalls: [] as any[],
	assignExistingTaskCalls: [] as any[],
	uploadedTaskMaterialCalls: [] as any[],
	searchReusableTaskCalls: [] as any[],
	getReusableTaskCalls: [] as any[],
	assessmentSetupCalls: [] as any[],
	resourceState: {
		courseCriteriaRows: [] as any[],
		assessmentSetup: {
			course: 'COURSE-1',
			school: 'SCH-1',
			academic_year: 'AY-2025-2026',
			program: 'PROG-1',
			assessment_scheme: null,
			scheme_name: null,
			calculation_method: null,
			assessment_category_visible: false,
			assessment_category_required: false,
			reporting_weight_visible: false,
			categories: [],
		} as any,
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
			default_requires_submission: 1,
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

function buildTaskMaterialAttachment(overrides: Record<string, unknown> = {}) {
	return {
		id: 'PLACEMENT-1',
		surface: 'task.material',
		item_id: 'PLACEMENT-1',
		owner_doctype: 'Material Placement',
		owner_name: 'PLACEMENT-1',
		file_id: 'FILE-1',
		display_name: 'Attachment',
		kind: 'other',
		preview_mode: 'icon_only',
		...overrides,
	};
}

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

vi.mock('@/lib/services/tasks/taskDeliveryWorkflowService', () => ({
	emitTaskDeliveryCreatedSignal: emitTaskDeliveryCreatedSignalMock,
}));

vi.mock('@/lib/client', () => ({
	apiUpload: apiUploadMock,
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
		if (config.url === 'ifitwala_ed.api.task.get_assessment_setup_for_delivery') {
			return {
				loading: false,
				submit: async (payload: any) => {
					assessmentSetupCalls.push(payload);
					config.onSuccess?.(resourceState.assessmentSetup);
					return resourceState.assessmentSetup;
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
		if (config.url === 'ifitwala_ed.api.materials.create_task_reference_material') {
			return {
				loading: false,
				submit: async (payload: any) => {
					createTaskReferenceMaterialCalls.push(payload);
					config.onSuccess?.(payload);
					return payload;
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
		TextEditor: defineComponent({
			name: 'TextEditorStub',
			props: ['content', 'placeholder', 'editable', 'editorClass'],
			emits: ['change'],
			setup(props, { emit }) {
				return () =>
					h('textarea', {
						value: props.content ?? '',
						placeholder: props.placeholder,
						disabled: props.editable === false,
						'data-text-editor': 'true',
						class: props.editorClass,
						onInput: (event: Event) =>
							emit('change', (event.target as HTMLTextAreaElement).value),
					});
			},
		}),
			FeatherIcon: defineComponent({
				name: 'FeatherIconStub',
				setup() {
					return () => h('span');
				},
			}),
			createResource,
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

async function setTextEditor(value: string) {
	const editor = document.querySelector('[data-text-editor="true"]') as HTMLTextAreaElement | null;
	expect(editor).not.toBeNull();
	editor!.value = value;
	editor!.dispatchEvent(new Event('input', { bubbles: true }));
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
	createTaskReferenceMaterialCalls.length = 0;
	assignExistingTaskCalls.length = 0;
	uploadedTaskMaterialCalls.length = 0;
	searchReusableTaskCalls.length = 0;
	getReusableTaskCalls.length = 0;
	assessmentSetupCalls.length = 0;
	apiUploadMock.mockReset();
	apiUploadMock.mockImplementation(async (url: string, formData: FormData) => {
		uploadedTaskMaterialCalls.push({ url, formData });
		return {
			placement: 'PLACEMENT-UPLOADED-1',
			material: 'MAT-UPLOADED-1',
			title: String(formData.get('title') || ''),
			material_type: 'File',
			file_name: 'lab-guide.pdf',
		};
	});
	resourceState.createNewTaskResult = {
		task: 'TASK-NEW-1',
		task_delivery: 'TDL-NEW-1',
		outcomes_created: 24,
	};
	resourceState.createNewTaskError = null;
	resourceState.assessmentSetup = {
		course: 'COURSE-1',
		school: 'SCH-1',
		academic_year: 'AY-2025-2026',
		program: 'PROG-1',
		assessment_scheme: null,
		scheme_name: null,
		calculation_method: null,
		assessment_category_visible: false,
		assessment_category_required: false,
		reporting_weight_visible: false,
		categories: [],
	};
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
		default_requires_submission: 1,
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
	apiUploadMock.mockReset();
	emitTaskDeliveryCreatedSignalMock.mockReset();
	closeMock.mockReset();
	while (cleanupFns.length) cleanupFns.pop()?.();
	document.body.innerHTML = '';
});

describe('CreateTaskDeliveryOverlay', () => {
	it('shows marking controls only for marked work choices', async () => {
		mountOverlay();
		await flushUi();

		let text = document.body.textContent || '';
		expect(text).not.toContain('Allow comment in gradebook?');

		await clickButton('Collect and mark');

		text = document.body.textContent || '';
		expect(text).toContain('Allow comment in gradebook?');
		expect(text).toContain('Comments stay separate from points, criteria, or completion.');
	});

	it('maps teacher workflow choices to delivery mode and student hand-in flags', async () => {
		mountOverlay();
		await flushUi();

		await setInput('Assignment title', 'Shared reading');
		await clickButton('Create');
		expect(createNewTaskCalls[0]).toMatchObject({
			delivery_mode: 'Assign Only',
			requires_submission: 0,
			grading_mode: 'None',
		});

		while (cleanupFns.length) cleanupFns.pop()?.();
		document.body.innerHTML = '';
		createNewTaskCalls.length = 0;
		mountOverlay();
		await flushUi();
		await setInput('Assignment title', 'Notebook check');
		await clickButton('Collect work');
		await clickButton('Create');
		expect(createNewTaskCalls[0]).toMatchObject({
			delivery_mode: 'Collect Work',
			requires_submission: 1,
			grading_mode: 'None',
		});

		while (cleanupFns.length) cleanupFns.pop()?.();
		document.body.innerHTML = '';
		createNewTaskCalls.length = 0;
		mountOverlay();
		await flushUi();
		await setInput('Assignment title', 'Essay checkpoint');
		await clickButton('Collect and mark');
		await clickButton('Points');
		await setInput('Enter max points', '10');
		await clickButton('Create');
		expect(createNewTaskCalls[0]).toMatchObject({
			delivery_mode: 'Assess',
			requires_submission: 1,
			grading_mode: 'Points',
			max_points: '10',
		});

		while (cleanupFns.length) cleanupFns.pop()?.();
		document.body.innerHTML = '';
		createNewTaskCalls.length = 0;
		mountOverlay();
		await flushUi();
		await setInput('Assignment title', 'Midterm exam');
		await clickButton('Mark class work');
		await clickButton('Points');
		await setInput('Enter max points', '100');
		await clickButton('Create');
		expect(createNewTaskCalls[0]).toMatchObject({
			delivery_mode: 'Assess',
			requires_submission: 0,
			grading_mode: 'Points',
			max_points: '100',
		});
	});

	it('submits resolved assessment category and task weight for assessed work', async () => {
		resourceState.assessmentSetup = {
			course: 'COURSE-1',
			school: 'SCH-1',
			academic_year: 'AY-2025-2026',
			program: 'PROG-1',
			assessment_scheme: 'ASC-1',
			scheme_name: 'Senior School Assessment',
			calculation_method: 'Category + Task Weight Hybrid',
			assessment_category_visible: true,
			assessment_category_required: true,
			reporting_weight_visible: true,
			categories: [
				{
					assessment_category: 'Summative',
					label: 'Summative Evidence',
					weight: 70,
					include_in_final_grade: true,
				},
			],
		};

		mountOverlay();
		await flushUi();

		await setInput('Assignment title', 'Lab practical');
		await clickButton('Collect and mark');
		await clickButton('Points');
		await setInput('Enter max points', '20');

		expect(assessmentSetupCalls).toEqual([{ student_group: 'GRP-1' }]);
		expect(document.body.textContent || '').toContain('Senior School Assessment');

		await setSelect('[data-assessment-category-select="true"]', 'Summative');
		await setInput('Default 1', '2');
		await clickButton('Create');

		expect(createNewTaskCalls).toHaveLength(1);
		expect(createNewTaskCalls[0]).toMatchObject({
			title: 'Lab practical',
			delivery_mode: 'Assess',
			requires_submission: 1,
			grading_mode: 'Points',
			max_points: '20',
			assessment_category: 'Summative',
			reporting_weight: '2',
		});
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

	it('submits rich-text task instructions from Step 1', async () => {
		mountOverlay();
		await flushUi();

		await setInput('Assignment title', 'Microscope reflection');
		await setTextEditor('<p>Bring <strong>two observations</strong> and one question.</p>');
		await clickButton('Create');

		expect(createNewTaskCalls).toHaveLength(1);
		expect(createNewTaskCalls[0]).toMatchObject({
			title: 'Microscope reflection',
			instructions: '<p>Bring <strong>two observations</strong> and one question.</p>',
		});
		expect(emitTaskDeliveryCreatedSignalMock).toHaveBeenCalledWith({
			task: 'TASK-NEW-1',
			task_delivery: 'TDL-NEW-1',
			student_group: 'GRP-1',
			class_teaching_plan: null,
			unit_plan: null,
			class_session: null,
		});
		expect(closeMock).toHaveBeenCalledWith('programmatic');
	});

	it('shows the attachment composer inside the main create step', async () => {
		mountOverlay();
		await flushUi();

		const text = document.body.textContent || '';
		expect(text).toContain('Include files or links with this task');
		expect(text).toContain('Queue file or image');
		expect(text).toContain('Attachments saved with this task');
	});

	it('assigns an existing reusable task and closes immediately after success', async () => {
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
			requires_submission: 1,
			grading_mode: 'None',
			allow_feedback: 0,
		});
		expect(createNewTaskCalls).toHaveLength(0);
		expect(closeMock).toHaveBeenCalledWith('programmatic');
		expect(emitTaskDeliveryCreatedSignalMock).toHaveBeenCalledWith({
			task: 'TASK-SHARED-1',
			task_delivery: 'TDL-SHARED-1',
			student_group: 'GRP-1',
			class_teaching_plan: null,
			unit_plan: null,
			class_session: null,
		});
	});

	it('renders reusable-task instructions without exposing literal html tags', async () => {
		resourceState.reusableTaskDetail = {
			...resourceState.reusableTaskDetail,
			instructions: '<p>Annotate the article.</p><ul><li>Quote evidence</li></ul>',
		};

		mountOverlay();
		await flushUi();

		await clickButton('Reuse existing task');
		await clickButton('Shared reading response');

		const text = document.body.textContent || '';
		expect(text).toContain('Annotate the article.');
		expect(text).toContain('Quote evidence');
		expect(text).not.toContain('<p>');
		expect(text).not.toContain('<li>');
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
		await clickButton('Collect and mark');
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
			requires_submission: 1,
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
			default_requires_submission: 1,
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
			requires_submission: 1,
			grading_mode: 'Criteria',
			rubric_scoring_strategy: 'Separate Criteria',
		});
		expect(closeMock).toHaveBeenCalledWith('programmatic');
	});

	it('uploads queued file attachments as part of the create flow', async () => {
		mountOverlay();
		await flushUi();

		await clickButton('Queue file or image');

		const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement | null;
		expect(fileInput).not.toBeNull();
		const file = new File(['pdf-bytes'], 'lab-guide.pdf', { type: 'application/pdf' });
		Object.defineProperty(fileInput!, 'files', {
			value: [file],
			configurable: true,
		});
		fileInput!.dispatchEvent(new Event('change', { bubbles: true }));
		await flushUi();
		await clickButton('Queue attachment');

		await setInput('Assignment title', 'Microscope reflection');
		await clickButton('Create');

		expect(createNewTaskCalls).toHaveLength(1);
		expect(apiUploadMock).toHaveBeenCalledTimes(1);
		expect(uploadedTaskMaterialCalls[0].url).toBe(
			'ifitwala_ed.api.materials.upload_task_material_file'
		);
		expect(uploadedTaskMaterialCalls[0].formData.get('task')).toBe('TASK-NEW-1');
		expect(uploadedTaskMaterialCalls[0].formData.get('title')).toBe('lab-guide.pdf');
		expect(closeMock).toHaveBeenCalledWith('programmatic');
	});

	it('renders task materials from the top-level governed attachment row', async () => {
		resourceState.taskMaterialsRows = [
			{
				placement: 'PLACEMENT-1',
				material: 'MAT-1',
				title: 'Lab guide',
				material_type: 'File',
				file_name: 'lab-guide.pdf',
				attachment: buildTaskMaterialAttachment({
					id: 'PLACEMENT-1',
					item_id: 'PLACEMENT-1',
					display_name: 'Lab guide',
					kind: 'pdf',
					extension: 'pdf',
					preview_mode: 'pdf_embed',
					preview_url:
						'/api/method/ifitwala_ed.api.file_access.preview_academic_file?file=FILE-1',
					open_url:
						'/api/method/ifitwala_ed.api.file_access.download_academic_file?file=FILE-1',
				}),
			},
		];
		apiUploadMock.mockImplementationOnce(async (url: string, formData: FormData) => {
			uploadedTaskMaterialCalls.push({ url, formData });
			throw new Error('Upload failed');
		});

		mountOverlay();
		await flushUi();

		await clickButton('Queue file or image');
		const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement | null;
		const file = new File(['pdf-bytes'], 'lab-guide.pdf', { type: 'application/pdf' });
		Object.defineProperty(fileInput!, 'files', {
			value: [file],
			configurable: true,
		});
		fileInput!.dispatchEvent(new Event('change', { bubbles: true }));
		await flushUi();
		await clickButton('Queue attachment');

		await setInput('Assignment title', 'Microscope reflection');
		await clickButton('Create');
		await flushUi();

		const actions = Array.from(document.querySelectorAll('a.if-action'));
		expect(actions[0]?.textContent?.trim()).toBe('Preview');
		expect(actions[0]?.getAttribute('href')).toBe(
			'/api/method/ifitwala_ed.api.file_access.preview_academic_file?file=FILE-1'
		);
		expect(actions[1]?.textContent?.trim()).toBe('Open original');
		expect(actions[1]?.getAttribute('href')).toBe(
			'/api/method/ifitwala_ed.api.file_access.download_academic_file?file=FILE-1'
		);
		expect(closeMock).not.toHaveBeenCalled();
	});

	it('closes immediately after creating the task when nothing is queued', async () => {
		mountOverlay();
		await flushUi();

		await setInput('Assignment title', 'Microscope reflection');
		await clickButton('Create');

		expect(createNewTaskCalls).toHaveLength(1);
		expect(emitTaskDeliveryCreatedSignalMock).toHaveBeenCalledWith({
			task: 'TASK-NEW-1',
			task_delivery: 'TDL-NEW-1',
			student_group: 'GRP-1',
			class_teaching_plan: null,
			unit_plan: null,
			class_session: null,
		});
		expect(closeMock).toHaveBeenCalledWith('programmatic');
	});
});
