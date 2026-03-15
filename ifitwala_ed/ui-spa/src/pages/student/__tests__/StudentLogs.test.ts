// ifitwala_ed/ui-spa/src/pages/student/__tests__/StudentLogs.test.ts

import { afterEach, describe, expect, it, vi } from 'vitest';
import { createApp, defineComponent, h, nextTick, type App } from 'vue';

const { apiMethodMock, toastErrorMock } = vi.hoisted(() => ({
	apiMethodMock: vi.fn(),
	toastErrorMock: vi.fn(),
}));

vi.mock('frappe-ui', () => ({
	toast: {
		error: toastErrorMock,
	},
}));

vi.mock('@/resources/frappe', () => ({
	apiMethod: apiMethodMock,
}));

import StudentLogs from '@/pages/student/StudentLogs.vue';

const cleanupFns: Array<() => void> = [];

class ResizeObserverStub {
	disconnect() {}
	observe() {}
	unobserve() {}
}

vi.stubGlobal('ResizeObserver', ResizeObserverStub);

function makeFetchResponse(payload: unknown) {
	return {
		ok: true,
		json: async () => ({ message: payload }),
	};
}

async function flushUi() {
	await Promise.resolve();
	await nextTick();
	await Promise.resolve();
	await nextTick();
}

function mountStudentLogs() {
	const host = document.createElement('div');
	document.body.appendChild(host);

	const app: App = createApp(
		defineComponent({
			render() {
				return h(StudentLogs);
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
	apiMethodMock.mockReset();
	toastErrorMock.mockReset();
	vi.restoreAllMocks();
	while (cleanupFns.length) {
		cleanupFns.pop()?.();
	}
	document.body.innerHTML = '';
});

describe('StudentLogs', () => {
	it('marks a student log as read through the explicit POST action', async () => {
		vi.spyOn(globalThis, 'fetch')
			.mockResolvedValueOnce(
				makeFetchResponse([
					{
						name: 'LOG-1',
						date: '2026-03-15',
						time: '09:00:00',
						log_type: 'Academic Honesty',
						author_name: 'Teacher Example',
						preview: 'Preview body',
						follow_up_status: 'Completed',
						is_unread: true,
					},
				]) as Response
			)
			.mockResolvedValueOnce(
				makeFetchResponse({
					name: 'LOG-1',
					date: '2026-03-15',
					time: '09:00:00',
					log_type: 'Academic Honesty',
					author_name: 'Teacher Example',
					log: '<p>Detail body</p>',
				}) as Response
			);
		apiMethodMock.mockResolvedValue({
			ok: true,
			student_log: 'LOG-1',
			read_at: '2026-03-15T09:01:00',
		});

		mountStudentLogs();
		await flushUi();

		expect(document.body.textContent || '').toContain('New');

		const logButton = Array.from(document.querySelectorAll('button')).find(node =>
			node.textContent?.includes('Academic Honesty')
		) as HTMLButtonElement | undefined;
		expect(logButton).toBeTruthy();
		logButton?.click();
		await flushUi();

		expect(apiMethodMock).toHaveBeenCalledWith(
			'ifitwala_ed.api.student_log.mark_student_log_read',
			{ log_name: 'LOG-1' }
		);
		expect(document.body.textContent || '').not.toContain('New');
	});
});
