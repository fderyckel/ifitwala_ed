import { afterEach, describe, expect, it, vi } from 'vitest';
import { createApp, defineComponent, h, nextTick, type App } from 'vue';

const {
	getStaffClassPlanningSurfaceMock,
	routeState,
	routerReplaceMock,
	routerPushMock,
	overlayOpenMock,
} = vi.hoisted(() => ({
	getStaffClassPlanningSurfaceMock: vi.fn(),
	routeState: {
		params: {
			studentGroup: 'GROUP-1',
		},
		query: {
			class_teaching_plan: 'CLASS-PLAN-1',
		},
	},
	routerReplaceMock: vi.fn(),
	routerPushMock: vi.fn(),
	overlayOpenMock: vi.fn(),
}));

vi.mock('vue-router', async () => {
	const { defineComponent, h } = await import('vue');

	return {
		RouterLink: defineComponent({
			name: 'RouterLinkStub',
			props: {
				to: {
					type: [String, Object],
					required: false,
					default: '',
				},
			},
			setup(props, { slots }) {
				return () => h('a', { 'data-to': JSON.stringify(props.to || null) }, slots.default?.());
			},
		}),
		useRouter: () => ({
			replace: routerReplaceMock,
			push: routerPushMock,
		}),
		useRoute: () => routeState,
	};
});

vi.mock('@/components/planning/PlanningResourcePanel.vue', () => ({
	default: defineComponent({
		name: 'PlanningResourcePanelStub',
		props: [
			'title',
			'anchorDoctype',
			'anchorName',
			'enableAttachmentPreview',
			'canManage',
			'showReadOnlyNotice',
		],
		setup(props) {
			return () =>
				h(
					'div',
					{
						class: 'planning-resource-panel-stub',
						'data-title': String(props.title || ''),
						'data-anchor-doctype': String(props.anchorDoctype || ''),
						'data-anchor-name': String(props.anchorName || ''),
						'data-enable-preview': props.enableAttachmentPreview ? '1' : '0',
						'data-can-manage': props.canManage === false ? '0' : '1',
						'data-show-read-only-notice': props.showReadOnlyNotice === false ? '0' : '1',
					},
					String(props.title || '')
				);
		},
	}),
}));

vi.mock('@/lib/services/staff/staffTeachingService', () => ({
	createClassTeachingPlan: vi.fn(),
	getStaffClassPlanningSurface: getStaffClassPlanningSurfaceMock,
	saveClassSession: vi.fn(),
	saveClassTeachingPlan: vi.fn(),
	saveClassTeachingPlanUnit: vi.fn(),
}));

vi.mock('@/composables/useOverlayStack', () => ({
	useOverlayStack: () => ({
		open: overlayOpenMock,
	}),
}));

vi.mock('@/lib/planning/planningActionGuards', () => ({
	normalizePlanningSurfaceError: (error: unknown) =>
		error instanceof Error ? error.message : 'Unable to load class planning.',
}));

vi.mock('@/lib/uiSignals', () => ({
	SIGNAL_TASK_DELIVERY_CREATED: 'task-delivery-created',
	uiSignals: {
		subscribe: vi.fn(() => vi.fn()),
	},
}));

vi.mock('frappe-ui', () => ({
	toast: {
		success: vi.fn(),
		error: vi.fn(),
	},
}));

import ClassPlanning from '@/pages/staff/ClassPlanning.vue';

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
				return h(ClassPlanning);
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
	getStaffClassPlanningSurfaceMock.mockReset();
	routerReplaceMock.mockReset();
	routerPushMock.mockReset();
	overlayOpenMock.mockReset();
	while (cleanupFns.length) cleanupFns.pop()?.();
	document.body.innerHTML = '';
});

describe('ClassPlanning page', () => {
	it('passes preview mode to the staff resource surfaces', async () => {
		getStaffClassPlanningSurfaceMock.mockResolvedValue({
			meta: {
				generated_at: '2026-04-16 09:00:00',
				student_group: 'GROUP-1',
			},
			group: {
				student_group: 'GROUP-1',
				title: 'Biology A',
				course: 'COURSE-1',
				academic_year: '2026-2027',
			},
			course_plans: [],
			class_teaching_plans: [
				{
					class_teaching_plan: 'CLASS-PLAN-1',
					title: 'Biology A Plan',
					course_plan: 'COURSE-PLAN-1',
					planning_status: 'Active',
				},
			],
			resolved: {
				class_teaching_plan: 'CLASS-PLAN-1',
				course_plan: 'COURSE-PLAN-1',
				can_initialize: 1,
				requires_course_plan_selection: 0,
			},
			teaching_plan: {
				class_teaching_plan: 'CLASS-PLAN-1',
				title: 'Biology A Plan',
				course_plan: 'COURSE-PLAN-1',
				planning_status: 'Active',
				team_note: '',
			},
			resources: {
				shared_resources: [],
				class_resources: [
					{
						material: 'MAT-CLASS-1',
						title: 'Class slide deck',
					},
				],
				general_assigned_work: [],
			},
			curriculum: {
				units: [
					{
						unit_plan: 'UNIT-1',
						title: 'Cells',
						standards: [],
						shared_resources: [
							{
								material: 'MAT-UNIT-1',
								title: 'Unit overview',
							},
						],
						assigned_work: [],
						shared_reflections: [],
						class_reflections: [],
						governed_required: 1,
						sessions: [
							{
								class_session: 'SESSION-1',
								title: 'Lesson 1',
								unit_plan: 'UNIT-1',
								activities: [],
								resources: [
									{
										material: 'MAT-SESSION-1',
										title: 'Lab sheet',
									},
								],
								assigned_work: [],
							},
						],
					},
				],
				session_count: 1,
				assigned_work_count: 0,
			},
		});

		mountPage();
		await flushUi();

		expect(getStaffClassPlanningSurfaceMock).toHaveBeenCalledWith({
			student_group: 'GROUP-1',
			class_teaching_plan: 'CLASS-PLAN-1',
		});

		const panels = Array.from(document.querySelectorAll('.planning-resource-panel-stub'));
		const byTitle = Object.fromEntries(
			panels.map(panel => [panel.getAttribute('data-title') || '', panel])
		);

		expect(byTitle['Shared resources for this unit']?.getAttribute('data-enable-preview')).toBe('1');
		expect(byTitle['Shared resources for this unit']?.getAttribute('data-can-manage')).toBe('0');
		expect(byTitle['Shared resources for this unit']?.getAttribute('data-show-read-only-notice')).toBe('0');
		expect(byTitle['Shared across this class plan']?.getAttribute('data-enable-preview')).toBe('1');
		expect(byTitle['Materials for this class session']?.getAttribute('data-enable-preview')).toBe('1');
	});
});
