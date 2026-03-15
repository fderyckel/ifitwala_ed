// ifitwala_ed/ui-spa/src/pages/student/__tests__/CourseDetail.test.ts

import { afterEach, describe, expect, it, vi } from 'vitest';
import { createApp, defineComponent, h, nextTick, type App } from 'vue';

import type { Response as StudentCourseDetailResponse } from '@/types/contracts/student_hub/get_student_course_detail';

const { getStudentCourseDetailMock, routerReplaceMock } = vi.hoisted(() => ({
	getStudentCourseDetailMock: vi.fn(),
	routerReplaceMock: vi.fn(),
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
			setup(_, { slots }) {
				return () => h('a', {}, slots.default?.());
			},
		}),
		useRouter: () => ({
			replace: routerReplaceMock,
		}),
	};
});

vi.mock('frappe-ui', async () => {
	const { defineComponent, h } = await import('vue');

	return {
		FeatherIcon: defineComponent({
			name: 'FeatherIconStub',
			setup() {
				return () => h('svg');
			},
		}),
	};
});

vi.mock('@/lib/services/student/studentLearningHubService', () => ({
	getStudentCourseDetail: getStudentCourseDetailMock,
}));

import CourseDetail from '@/pages/student/CourseDetail.vue';

const cleanupFns: Array<() => void> = [];

function buildPayload(): StudentCourseDetailResponse {
	return {
		meta: {
			generated_at: '2026-03-15T10:00:00',
			course_id: 'COURSE-1',
		},
		course: {
			course: 'COURSE-1',
			course_name: 'Biology',
			course_group: 'Sciences',
			course_image: '/files/biology.jpg',
			description: 'Introductory biology course',
			is_published: 1,
		},
		access: {
			student: 'STU-1',
			academic_years: ['2025-2026'],
			student_groups: [],
		},
		deep_link: {
			requested: {},
			resolved: {
				learning_unit: 'UNIT-1',
				lesson: 'LESSON-1',
				source: 'lesson',
			},
		},
		curriculum: {
			counts: {
				units: 1,
				lessons: 1,
				activities: 0,
				course_tasks: 0,
				unit_tasks: 0,
				lesson_tasks: 0,
				deliveries: 0,
			},
			course_tasks: [],
			units: [
				{
					name: 'UNIT-1',
					unit_name: 'Unit 1',
					unit_order: 1,
					is_published: 1,
					linked_tasks: [],
					lessons: [
						{
							name: 'LESSON-1',
							learning_unit: 'UNIT-1',
							title: 'Lesson 1',
							is_published: 1,
							linked_tasks: [],
							lesson_activities: [],
						},
					],
				},
			],
		},
	};
}

async function flushUi() {
	await Promise.resolve();
	await nextTick();
	await Promise.resolve();
	await nextTick();
}

function mountCourseDetail() {
	const host = document.createElement('div');
	document.body.appendChild(host);

	const app: App = createApp(
		defineComponent({
			render() {
				return h(CourseDetail, { course_id: 'COURSE-1' });
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
	getStudentCourseDetailMock.mockReset();
	routerReplaceMock.mockReset();
	while (cleanupFns.length) {
		cleanupFns.pop()?.();
	}
	document.body.innerHTML = '';
});

describe('CourseDetail', () => {
	it('keeps the course detail shell compact on laptop-sized layouts', async () => {
		getStudentCourseDetailMock.mockResolvedValue(buildPayload());

		mountCourseDetail();
		await flushUi();

		expect(getStudentCourseDetailMock).toHaveBeenCalledWith({
			course_id: 'COURSE-1',
			learning_unit: undefined,
			lesson: undefined,
			lesson_instance: undefined,
		});

		const headerImage = document.querySelector('header img');
		expect(headerImage).toBeTruthy();
		expect(headerImage?.className).toContain('aspect-square');
		expect(headerImage?.parentElement?.className).toContain('max-w-[7.5rem]');

		const contentShell = Array.from(document.querySelectorAll('section')).find(node =>
			node.className.includes('xl:grid-cols-[minmax(0,18rem),minmax(0,1fr)]')
		);
		expect(contentShell).toBeTruthy();

		const sidebar = document.querySelector('aside');
		expect(sidebar).toBeTruthy();
		expect(sidebar?.className).not.toContain('sticky');

		const outlineToggle = Array.from(document.querySelectorAll('button')).find(node =>
			node.textContent?.includes('Show Outline')
		);
		expect(outlineToggle).toBeTruthy();
		expect(outlineToggle?.className).toContain('xl:hidden');

		const outlinePanel = Array.from(document.querySelectorAll('div')).find(node =>
			node.className.includes('hidden xl:block')
		);
		expect(outlinePanel).toBeTruthy();
	});
});
