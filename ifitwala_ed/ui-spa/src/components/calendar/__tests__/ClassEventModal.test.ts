import { afterEach, describe, expect, it, vi } from 'vitest';
import { createApp, defineComponent, h, nextTick, type App } from 'vue';

const { apiMock, replaceTopMock, toastErrorMock } = vi.hoisted(() => ({
	apiMock: vi.fn(),
	replaceTopMock: vi.fn(),
	toastErrorMock: vi.fn(),
}));

vi.mock('@headlessui/vue', async () => {
	const { defineComponent, h } = await import('vue');

	const passthrough = (tag = 'div') =>
		defineComponent({
			name: `Stub${tag}`,
			props: ['as', 'show', 'initialFocus'],
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
		DialogTitle: passthrough('h3'),
		TransitionChild: passthrough('div'),
		TransitionRoot: passthrough('div'),
	};
});

vi.mock('frappe-ui', async () => {
	const { defineComponent, h } = await import('vue');

	return {
		FeatherIcon: defineComponent({
			name: 'FeatherIconStub',
			props: {
				name: {
					type: String,
					default: '',
				},
			},
			setup(props) {
				return () => h('span', { 'data-feather-icon': props.name });
			},
		}),
		toast: {
			error: toastErrorMock,
		},
	};
});

vi.mock('vue-router', async () => {
	const { defineComponent, h } = await import('vue');

	return {
		useRoute: () => ({
			name: 'staff-calendar',
		}),
		RouterLink: defineComponent({
			name: 'RouterLinkStub',
			props: ['to'],
			setup(_props, { slots, attrs }) {
				return () => h('a', attrs, slots.default?.());
			},
		}),
	};
});

vi.mock('@/composables/useOverlayStack', () => ({
	useOverlayStack: () => ({
		replaceTop: replaceTopMock,
	}),
}));

vi.mock('@/lib/client', () => ({
	api: apiMock,
}));

import ClassEventModal from '@/components/calendar/ClassEventModal.vue';

const cleanupFns: Array<() => void> = [];

async function flushUi() {
	await Promise.resolve();
	await nextTick();
	await Promise.resolve();
	await nextTick();
}

function mountModal(props: Record<string, unknown> = {}) {
	const host = document.createElement('div');
	document.body.appendChild(host);

	const app: App = createApp(
		defineComponent({
			render() {
				return h(ClassEventModal, {
					open: true,
					eventId: 'sg::GROUP-1::2026-04-22T08:00:00',
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

afterEach(() => {
	apiMock.mockReset();
	replaceTopMock.mockReset();
	toastErrorMock.mockReset();
	while (cleanupFns.length) cleanupFns.pop()?.();
	document.body.innerHTML = '';
});

describe('ClassEventModal task launch', () => {
	it('passes the resolved active class teaching plan into the task overlay', async () => {
		apiMock.mockResolvedValue({
			id: 'sg::GROUP-1::2026-04-22T08:00:00',
			student_group: 'GROUP-1',
			title: 'Biology A',
			course: 'COURSE-1',
			course_name: 'Biology',
			start: '2026-04-22T08:00:00+07:00',
			end: '2026-04-22T09:00:00+07:00',
			task_creation: {
				status: 'ready',
				class_teaching_plan: 'CLASS-PLAN-1',
			},
		});

		mountModal();
		await flushUi();

		const createTaskButton = Array.from(document.querySelectorAll('button')).find(button =>
			(button.textContent || '').includes('Create Task')
		) as HTMLButtonElement | undefined;
		expect(createTaskButton).toBeTruthy();

		createTaskButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
		await flushUi();

		expect(replaceTopMock).toHaveBeenCalledWith('create-task', {
			prefillStudentGroup: 'GROUP-1',
			prefillCourse: 'COURSE-1',
			prefillClassTeachingPlan: 'CLASS-PLAN-1',
			prefillDueDate: '2026-04-22T09:00:00+07:00',
		});
	});

	it('blocks task launch when the class has no active teaching plan', async () => {
		apiMock.mockResolvedValue({
			id: 'sg::GROUP-1::2026-04-22T08:00:00',
			student_group: 'GROUP-1',
			title: 'Biology A',
			course: 'COURSE-1',
			course_name: 'Biology',
			start: '2026-04-22T08:00:00+07:00',
			end: '2026-04-22T09:00:00+07:00',
			task_creation: {
				status: 'missing_active_plan',
				class_teaching_plan: null,
			},
		});

		mountModal();
		await flushUi();

		const createTaskButton = Array.from(document.querySelectorAll('button')).find(button =>
			(button.textContent || '').includes('Create Task')
		) as HTMLButtonElement | undefined;
		expect(createTaskButton).toBeTruthy();
		expect(createTaskButton?.disabled).toBe(true);
		expect(document.body.textContent || '').toContain(
			'Open Class Planning for this class, create or activate the plan'
		);

		createTaskButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
		await flushUi();

		expect(replaceTopMock).not.toHaveBeenCalled();
	});
});
