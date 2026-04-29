import { afterEach, describe, expect, it, vi } from 'vitest';
import { createApp, defineComponent, h, nextTick, type App } from 'vue';

import type {
	AdmissionsInboxContext,
	AdmissionsInboxQueue,
	AdmissionsInboxRow,
} from '@/types/contracts/admissions_inbox/get_admissions_inbox_context';

const {
	getAdmissionsInboxContextMock,
	logAdmissionMessageMock,
	recordAdmissionCrmActivityMock,
	linkAdmissionConversationMock,
	confirmAdmissionExternalIdentityMock,
	assignAdmissionConversationMock,
	updateAdmissionConversationStatusMock,
	createInquiryFromAdmissionConversationMock,
	assignInquiryFromInboxMock,
	archiveInquiryFromInboxMock,
	markInquiryContactedFromInboxMock,
	qualifyInquiryFromInboxMock,
	inviteInquiryToApplyFromInboxMock,
} = vi.hoisted(() => ({
	getAdmissionsInboxContextMock: vi.fn(),
	logAdmissionMessageMock: vi.fn(),
	recordAdmissionCrmActivityMock: vi.fn(),
	linkAdmissionConversationMock: vi.fn(),
	confirmAdmissionExternalIdentityMock: vi.fn(),
	assignAdmissionConversationMock: vi.fn(),
	updateAdmissionConversationStatusMock: vi.fn(),
	createInquiryFromAdmissionConversationMock: vi.fn(),
	assignInquiryFromInboxMock: vi.fn(),
	archiveInquiryFromInboxMock: vi.fn(),
	markInquiryContactedFromInboxMock: vi.fn(),
	qualifyInquiryFromInboxMock: vi.fn(),
	inviteInquiryToApplyFromInboxMock: vi.fn(),
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
	logAdmissionMessage: logAdmissionMessageMock,
	recordAdmissionCrmActivity: recordAdmissionCrmActivityMock,
	linkAdmissionConversation: linkAdmissionConversationMock,
	confirmAdmissionExternalIdentity: confirmAdmissionExternalIdentityMock,
	assignAdmissionConversation: assignAdmissionConversationMock,
	updateAdmissionConversationStatus: updateAdmissionConversationStatusMock,
	createInquiryFromAdmissionConversation: createInquiryFromAdmissionConversationMock,
	assignInquiryFromInbox: assignInquiryFromInboxMock,
	archiveInquiryFromInbox: archiveInquiryFromInboxMock,
	markInquiryContactedFromInbox: markInquiryContactedFromInboxMock,
	qualifyInquiryFromInbox: qualifyInquiryFromInboxMock,
	inviteInquiryToApplyFromInbox: inviteInquiryToApplyFromInboxMock,
}));

import { SIGNAL_ADMISSIONS_INBOX_INVALIDATE, uiSignals } from '@/lib/uiSignals';
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
		external_identity: 'EXT-0001',
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
		actions: [
			{ id: 'log_reply', enabled: true },
			{ id: 'record_activity', enabled: true },
			{ id: 'reassign_owner', enabled: true },
			{ id: 'archive_conversation', enabled: true },
			{ id: 'mark_spam', enabled: true },
			{ id: 'create_inquiry', enabled: true },
			{ id: 'link_inquiry', enabled: true },
			{ id: 'link_applicant', enabled: true },
			{ id: 'resolve_identity_match', enabled: true },
		],
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
						actions: [
							{ id: 'assign_owner', enabled: true },
							{ id: 'mark_contacted', enabled: true },
							{ id: 'archive_inquiry', enabled: true },
							{ id: 'qualify', enabled: true },
							{ id: 'invite_to_apply', enabled: true },
						],
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

function clickByTestId(testId: string) {
	const element = document.querySelector(`[data-testid="${testId}"]`) as HTMLElement | null;
	expect(element).toBeTruthy();
	element?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
}

function setControlValue(testId: string, value: string) {
	const element = document.querySelector(`[data-testid="${testId}"]`) as
		| HTMLInputElement
		| HTMLTextAreaElement
		| HTMLSelectElement
		| null;
	expect(element).toBeTruthy();
	if (!element) return;
	element.value = value;
	element.dispatchEvent(new Event('input', { bubbles: true }));
	element.dispatchEvent(new Event('change', { bubbles: true }));
}

afterEach(() => {
	getAdmissionsInboxContextMock.mockReset();
	logAdmissionMessageMock.mockReset();
	recordAdmissionCrmActivityMock.mockReset();
	linkAdmissionConversationMock.mockReset();
	confirmAdmissionExternalIdentityMock.mockReset();
	assignAdmissionConversationMock.mockReset();
	updateAdmissionConversationStatusMock.mockReset();
	createInquiryFromAdmissionConversationMock.mockReset();
	assignInquiryFromInboxMock.mockReset();
	archiveInquiryFromInboxMock.mockReset();
	markInquiryContactedFromInboxMock.mockReset();
	qualifyInquiryFromInboxMock.mockReset();
	inviteInquiryToApplyFromInboxMock.mockReset();
	uiSignals._clearAllForTests();
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

	it('submits a log reply with the controlled CRM message payload and refreshes on signal', async () => {
		getAdmissionsInboxContextMock
			.mockResolvedValueOnce(context())
			.mockResolvedValueOnce(context({ queues: [queue({ rows: [row({ title: 'Ada Parent Updated' })] })] }));
		logAdmissionMessageMock.mockImplementation(async () => {
			uiSignals.emit(SIGNAL_ADMISSIONS_INBOX_INVALIDATE);
			return { ok: true };
		});

		mountAdmissionsInbox();
		await flushUi();

		clickByTestId('inbox-actions-conversation:AC-0001');
		await flushUi();
		setControlValue('action-message-body', 'Called parent and confirmed interest.');
		clickByTestId('action-submit');
		await flushUi();

		expect(logAdmissionMessageMock).toHaveBeenCalledWith({
			conversation: 'AC-0001',
			inquiry: null,
			student_applicant: null,
			external_identity: 'EXT-0001',
			channel_account: null,
			organization: 'ORG-1',
			school: 'SCH-1',
			assigned_to: 'admissions@example.com',
			direction: 'Outbound',
			message_type: 'Text',
			delivery_status: 'Logged',
			body: 'Called parent and confirmed interest.',
		});
		expect(getAdmissionsInboxContextMock).toHaveBeenCalledTimes(2);
		expect(document.body.textContent || '').toContain('Saved. Refreshing queue.');
	});

	it('submits a link applicant action with only the approved link payload', async () => {
		getAdmissionsInboxContextMock.mockResolvedValue(context());
		linkAdmissionConversationMock.mockResolvedValue({ ok: true });

		mountAdmissionsInbox();
		await flushUi();

		clickByTestId('inbox-actions-conversation:AC-0001');
		await flushUi();
		clickByTestId('inbox-action-link_applicant');
		await flushUi();
		setControlValue('action-link-applicant', 'APP-0001');
		clickByTestId('action-submit');
		await flushUi();

		expect(linkAdmissionConversationMock).toHaveBeenCalledWith({
			conversation: 'AC-0001',
			student_applicant: 'APP-0001',
		});
		expect(document.body.textContent || '').toContain('Saved. Refreshing queue.');
	});

	it('submits conversation ownership changes through the CRM assignment endpoint', async () => {
		getAdmissionsInboxContextMock.mockResolvedValue(context());
		assignAdmissionConversationMock.mockResolvedValue({ ok: true });

		mountAdmissionsInbox();
		await flushUi();

		clickByTestId('inbox-actions-conversation:AC-0001');
		await flushUi();
		clickByTestId('inbox-action-reassign_owner');
		await flushUi();
		setControlValue('action-assigned-to', 'new.owner@example.com');
		clickByTestId('action-submit');
		await flushUi();

		expect(assignAdmissionConversationMock).toHaveBeenCalledWith({
			conversation: 'AC-0001',
			assigned_to: 'new.owner@example.com',
		});
		expect(document.body.textContent || '').toContain('Saved. Refreshing queue.');
	});

	it('creates an Inquiry from a CRM conversation without client-side schema assembly', async () => {
		getAdmissionsInboxContextMock.mockResolvedValue(context());
		createInquiryFromAdmissionConversationMock.mockResolvedValue({ ok: true });

		mountAdmissionsInbox();
		await flushUi();

		clickByTestId('inbox-actions-conversation:AC-0001');
		await flushUi();
		clickByTestId('inbox-action-create_inquiry');
		await flushUi();
		setControlValue('action-create-inquiry-message', 'Family is interested in Grade 4 admission.');
		clickByTestId('action-submit');
		await flushUi();

		expect(createInquiryFromAdmissionConversationMock).toHaveBeenCalledWith({
			conversation: 'AC-0001',
			type_of_inquiry: 'Admission',
			source: 'WhatsApp',
			message: 'Family is interested in Grade 4 admission.',
		});
		expect(document.body.textContent || '').toContain('Saved. Refreshing queue.');
	});

	it('submits Inquiry ownership and workflow actions through approved Inquiry endpoints', async () => {
		getAdmissionsInboxContextMock.mockResolvedValue(context());
		assignInquiryFromInboxMock.mockResolvedValue({ ok: true });
		markInquiryContactedFromInboxMock.mockResolvedValue({ ok: true });

		mountAdmissionsInbox();
		await flushUi();

		clickByTestId('queue-unassigned');
		await flushUi();
		clickByTestId('inbox-actions-inquiry:INQ-0001');
		await flushUi();
		clickByTestId('inbox-action-assign_owner');
		await flushUi();
		setControlValue('action-assigned-to', 'admissions.owner@example.com');
		setControlValue('action-assignment-lane', 'Admission');
		clickByTestId('action-submit');
		await flushUi();

		expect(assignInquiryFromInboxMock).toHaveBeenCalledWith({
			inquiry: 'INQ-0001',
			assigned_to: 'admissions.owner@example.com',
			assignment_lane: 'Admission',
		});

		clickByTestId('inbox-action-mark_contacted');
		await flushUi();
		clickByTestId('action-submit');
		await flushUi();

		expect(markInquiryContactedFromInboxMock).toHaveBeenCalledWith({
			inquiry: 'INQ-0001',
			complete_todo: 0,
		});
	});

	it('shows inline mutation errors without hiding the drawer', async () => {
		getAdmissionsInboxContextMock.mockResolvedValue(context());
		logAdmissionMessageMock.mockRejectedValue(new Error('Message body rejected'));

		mountAdmissionsInbox();
		await flushUi();

		clickByTestId('inbox-actions-conversation:AC-0001');
		await flushUi();
		setControlValue('action-message-body', 'Follow-up note');
		clickByTestId('action-submit');
		await flushUi();

		expect(document.querySelector('[data-testid="admissions-inbox-action-drawer"]')).toBeTruthy();
		expect(document.querySelector('[data-testid="admissions-inbox-action-error"]')).toBeTruthy();
		expect(document.body.textContent || '').toContain('Message body rejected');
	});

	it('lists unsupported server actions as source-record workflows instead of executable buttons', async () => {
		getAdmissionsInboxContextMock.mockResolvedValue(
			context({
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
								inquiry: 'INQ-0001',
								conversation: null,
								actions: [{ id: 'legacy_action', enabled: true }],
							}),
						],
					}),
				],
			})
		);

		mountAdmissionsInbox();
		await flushUi();

		clickByTestId('queue-unassigned');
		await flushUi();
		clickByTestId('inbox-actions-inquiry:INQ-0001');
		await flushUi();

		expect(document.body.textContent || '').toContain(
			'Handled from the source record in this phase: Legacy Action.'
		);
		expect(document.body.textContent || '').toContain(
			'No executable Inbox workflow is available for this item yet.'
		);
		expect(document.querySelector('[data-testid="inbox-action-legacy_action"]')).toBeFalsy();
	});
});
