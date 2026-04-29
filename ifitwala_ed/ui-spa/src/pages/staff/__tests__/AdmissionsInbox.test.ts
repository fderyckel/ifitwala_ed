import { afterEach, describe, expect, it, vi } from 'vitest';
import { createApp, defineComponent, h, nextTick, type App } from 'vue';

import type {
	AdmissionsInboxContext,
	AdmissionsInboxQueue,
	AdmissionsInboxRow,
} from '@/types/contracts/admissions_inbox/get_admissions_inbox_context';

const { getAdmissionsInboxContextMock } = vi.hoisted(() => ({
	getAdmissionsInboxContextMock: vi.fn(),
}));

vi.mock('frappe-ui', () => ({
	FeatherIcon: defineComponent({
		name: 'FeatherIconStub',
		props: {
			name: { type: String, required: true },
		},
		setup(props) {
			return () => h('span', { 'data-icon': props.name });
		},
	}),
}));

vi.mock('@/lib/services/admissions/admissionsInboxService', () => ({
	getAdmissionsInboxContext: getAdmissionsInboxContextMock,
}));

import AdmissionsInbox from '@/pages/staff/admissions/AdmissionsInbox.vue';

const cleanupFns: Array<() => void> = [];

function row(overrides: Partial<AdmissionsInboxRow>): AdmissionsInboxRow {
	return {
		id: 'conversation:AC-0001',
		kind: 'conversation',
		stage: 'pre_applicant',
		title: 'Ada Parent',
		subtitle: 'WhatsApp • Open',
		organization: 'ORG-1',
		school: 'SCH-1',
		inquiry: null,
		student_applicant: null,
		conversation: 'AC-0001',
		open_url: '/desk/admission-conversation/AC-0001',
		external_identity: null,
		channel_type: 'WhatsApp',
		channel_account: null,
		owner: 'admissions@example.com',
		sla_state: null,
		last_activity_at: '2026-04-28T08:00:00',
		last_message_preview: 'Can someone call me about admissions?',
		needs_reply: true,
		unread_count: 0,
		next_action_on: null,
		permissions: { can_open: true },
		actions: [{ id: 'log_reply', enabled: true }],
		...overrides,
	};
}

function queue(overrides: Partial<AdmissionsInboxQueue>): AdmissionsInboxQueue {
	return {
		id: 'needs_reply',
		label: 'Needs Reply',
		count: 1,
		rows: [row({})],
		has_more: false,
		...overrides,
	};
}

function context(overrides: Partial<AdmissionsInboxContext> = {}): AdmissionsInboxContext {
	return {
		ok: true,
		generated_at: '2026-04-28T08:15:00',
		filters: {
			organization: null,
			school: null,
			limit: 40,
		},
		queues: [
			queue({}),
			queue({
				id: 'unassigned',
				label: 'Unassigned',
				count: 1,
				rows: [
					row({
						id: 'inquiry:INQ-0001',
						kind: 'inquiry',
						stage: 'inquiry',
						title: 'Bea Lead',
						subtitle: 'Admission • Website',
						inquiry: 'INQ-0001',
						conversation: null,
						open_url: '/desk/inquiry/INQ-0001',
						channel_type: null,
						owner: null,
						last_message_preview: 'Interested in Grade 4.',
						needs_reply: false,
						actions: [{ id: 'mark_contacted', enabled: true }],
					}),
				],
			}),
		],
		sources: {
			crm_conversations: 1,
			inquiries: 1,
			student_applicants: 0,
		},
		...overrides,
	};
}

async function flushUi() {
	await Promise.resolve();
	await nextTick();
	await Promise.resolve();
	await nextTick();
}

function mountAdmissionsInbox() {
	const host = document.createElement('div');
	document.body.appendChild(host);

	const app: App = createApp(
		defineComponent({
			render() {
				return h(AdmissionsInbox);
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
	getAdmissionsInboxContextMock.mockReset();
	while (cleanupFns.length) {
		cleanupFns.pop()?.();
	}
	document.body.innerHTML = '';
});

describe('AdmissionsInbox', () => {
	it('loads the context once and renders the default queue', async () => {
		getAdmissionsInboxContextMock.mockResolvedValue(context());

		mountAdmissionsInbox();
		await flushUi();

		expect(getAdmissionsInboxContextMock).toHaveBeenCalledTimes(1);
		expect(getAdmissionsInboxContextMock).toHaveBeenCalledWith({ limit: 40 });
		expect(document.body.textContent || '').toContain('Admissions Inbox');
		expect(document.body.textContent || '').toContain('Ada Parent');
		expect(document.body.textContent || '').toContain('Can someone call me about admissions?');
		expect(document.querySelector('a[href="/desk/admission-conversation/AC-0001"]')).toBeTruthy();
	});

	it('switches queues without another API request', async () => {
		getAdmissionsInboxContextMock.mockResolvedValue(context());

		mountAdmissionsInbox();
		await flushUi();

		const unassigned = document.querySelector(
			'[data-testid="queue-unassigned"]'
		) as HTMLButtonElement | null;
		expect(unassigned).toBeTruthy();
		unassigned?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
		await flushUi();

		expect(document.body.textContent || '').toContain('Bea Lead');
		expect(document.body.textContent || '').not.toContain('Ada Parent');
		expect(getAdmissionsInboxContextMock).toHaveBeenCalledTimes(1);
	});

	it('refreshes from the page-owned refresh button', async () => {
		getAdmissionsInboxContextMock
			.mockResolvedValueOnce(context())
			.mockResolvedValueOnce(
				context({
					queues: [queue({ rows: [row({ title: 'Chris Parent' })] })],
					sources: { crm_conversations: 1 },
				})
			);

		mountAdmissionsInbox();
		await flushUi();

		const refresh = document.querySelector(
			'[data-testid="admissions-inbox-refresh"]'
		) as HTMLButtonElement | null;
		expect(refresh).toBeTruthy();
		refresh?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
		await flushUi();

		expect(getAdmissionsInboxContextMock).toHaveBeenCalledTimes(2);
		expect(document.body.textContent || '').toContain('Chris Parent');
	});

	it('shows an inline error and retries explicitly', async () => {
		getAdmissionsInboxContextMock
			.mockRejectedValueOnce(new Error('Permission denied'))
			.mockResolvedValueOnce(context());

		mountAdmissionsInbox();
		await flushUi();

		expect(document.querySelector('[data-testid="admissions-inbox-error"]')).toBeTruthy();
		expect(document.body.textContent || '').toContain(
			'Admissions Inbox could not load: Permission denied'
		);

		const retry = Array.from(document.querySelectorAll('button')).find(button =>
			(button.textContent || '').includes('Retry')
		);
		expect(retry).toBeTruthy();
		retry?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
		await flushUi();

		expect(getAdmissionsInboxContextMock).toHaveBeenCalledTimes(2);
		expect(document.body.textContent || '').toContain('Ada Parent');
	});
});
