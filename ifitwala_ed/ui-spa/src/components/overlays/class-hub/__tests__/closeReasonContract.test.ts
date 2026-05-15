import { afterEach, describe, expect, it, vi } from 'vitest';
import { createApp, defineComponent, h, nextTick, type App } from 'vue';

const closeMock = vi.fn();

vi.mock('@headlessui/vue', () => {
	const passthrough = (tag = 'div') =>
		defineComponent({
			name: `Stub${tag}`,
			props: ['as'],
			setup(props, { slots }) {
				return () => h(props.as && props.as !== 'template' ? props.as : tag, slots.default?.());
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

vi.mock('frappe-ui', () => ({
	FeatherIcon: defineComponent({
		name: 'FeatherIconStub',
		setup() {
			return () => h('span');
		},
	}),
}));

vi.mock('vue-router', () => ({
	RouterLink: defineComponent({
		name: 'RouterLinkStub',
		props: ['to'],
		setup(props, { slots }) {
			return () =>
				h(
					'a',
					{
						'data-router-to': JSON.stringify(props.to ?? null),
					},
					slots.default?.()
				);
		},
	}),
}));

vi.mock('@/lib/classHubService', () => ({
	createClassHubService: () => ({
		saveSignals: vi.fn(),
		quickEvidence: vi.fn(),
	}),
}));

vi.mock('@/composables/useOverlayStack', () => ({
	useOverlayStack: () => ({
		open: vi.fn(),
		replaceTop: vi.fn(),
	}),
}));

import StudentContextOverlay from '@/components/overlays/class-hub/StudentContextOverlay.vue';
import QuickEvidenceOverlay from '@/components/overlays/class-hub/QuickEvidenceOverlay.vue';
import QuickCFUOverlay from '@/components/overlays/class-hub/QuickCFUOverlay.vue';
import TaskReviewOverlay from '@/components/overlays/class-hub/TaskReviewOverlay.vue';

const cleanupFns: Array<() => void> = [];

async function flushUi() {
	await Promise.resolve();
	await nextTick();
	await Promise.resolve();
	await nextTick();
}

function mountOverlay(component: any, props: Record<string, unknown>) {
	const host = document.createElement('div');
	document.body.appendChild(host);

	const app: App = createApp(
		defineComponent({
			render() {
				return h(component, {
					open: true,
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

afterEach(() => {
	closeMock.mockReset();
	while (cleanupFns.length) cleanupFns.pop()?.();
	document.body.innerHTML = '';
});

describe('Class Hub overlay close reason contract', () => {
	it.each([
		[
			StudentContextOverlay,
			{
				student: 'STU-001',
				student_name: 'Amina Dar',
				student_group: 'SG-001',
			},
		],
		[
			QuickEvidenceOverlay,
			{
				student_group: 'SG-001',
				students: [{ student: 'STU-001', student_name: 'Amina Dar' }],
			},
		],
		[
			QuickCFUOverlay,
			{
				student_group: 'SG-001',
				students: [{ student: 'STU-001', student_name: 'Amina Dar' }],
			},
		],
		[
			TaskReviewOverlay,
			{
				title: 'Exit ticket review',
			},
		],
	])('emits programmatic when closed explicitly', async (component, props) => {
		mountOverlay(component, props);
		await flushUi();

		const closeButton = Array.from(document.querySelectorAll('button')).find(button =>
			(button.getAttribute('aria-label') || '').includes('Close')
		);
		closeButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
		await flushUi();

		expect(closeMock).toHaveBeenCalledWith('programmatic');
	});

	it('emits esc for the student context overlay on Escape', async () => {
		mountOverlay(StudentContextOverlay, {
			student: 'STU-001',
			student_name: 'Amina Dar',
			student_group: 'SG-001',
		});
		await flushUi();

		document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
		await flushUi();

		expect(closeMock).toHaveBeenCalledWith('esc');
	});

	it('routes task review to gradebook with prefilled class context', async () => {
		mountOverlay(TaskReviewOverlay, {
			title: 'Exit ticket review',
			gradebookQuery: {
				student_group: 'SG-001',
				task: 'TD-001',
				school: 'SCH-001',
				academic_year: '2025-2026',
				program: 'IIS',
				course: 'Math 1',
			},
		});
		await flushUi();

		const link = Array.from(document.querySelectorAll('a')).find(anchor =>
			(anchor.textContent || '').includes('Go to gradebook')
		) as HTMLAnchorElement | undefined;

		expect(link).toBeDefined();
		expect(link?.dataset.routerTo).toBe(
			JSON.stringify({
				name: 'staff-gradebook',
				query: {
					student_group: 'SG-001',
					task: 'TD-001',
					school: 'SCH-001',
					academic_year: '2025-2026',
					program: 'IIS',
					course: 'Math 1',
				},
			})
		);
	});
});
