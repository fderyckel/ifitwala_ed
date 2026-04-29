import { beforeEach, describe, expect, it, vi } from 'vitest';

const { apiMock, emitMock } = vi.hoisted(() => ({
	apiMock: vi.fn(),
	emitMock: vi.fn(),
}));

vi.mock('@/lib/client', () => ({
	api: apiMock,
}));

vi.mock('@/lib/uiSignals', () => ({
	uiSignals: {
		emit: emitMock,
	},
	SIGNAL_ADMISSIONS_INBOX_INVALIDATE: 'admissions_inbox:invalidate',
}));

import {
	assignInquiryFromInbox,
	logAdmissionMessage,
} from '@/lib/services/admissions/admissionsInboxService';

describe('admissionsInboxService', () => {
	beforeEach(() => {
		apiMock.mockReset();
		emitMock.mockReset();
	});

	it('adds an idempotency key and emits inbox invalidation after mutation success', async () => {
		apiMock.mockResolvedValue({ ok: true });

		await logAdmissionMessage({
			conversation: 'AC-0001',
			direction: 'Outbound',
			message_type: 'Text',
			delivery_status: 'Logged',
			body: 'Manual reply',
		});

		expect(apiMock).toHaveBeenCalledTimes(1);
		expect(apiMock).toHaveBeenCalledWith(
			'ifitwala_ed.api.admissions_crm.log_admission_message',
			expect.objectContaining({
				conversation: 'AC-0001',
				direction: 'Outbound',
				message_type: 'Text',
				delivery_status: 'Logged',
				body: 'Manual reply',
				client_request_id: expect.stringMatching(/^admission-message-/),
			})
		);
		expect(emitMock).toHaveBeenCalledWith('admissions_inbox:invalidate');
	});

	it('uses the Inquiry assignment endpoint with an assignment idempotency prefix', async () => {
		apiMock.mockResolvedValue({ ok: true });

		await assignInquiryFromInbox({
			inquiry: 'INQ-0001',
			assigned_to: 'admissions@example.com',
			assignment_lane: 'Admission',
		});

		expect(apiMock).toHaveBeenCalledWith(
			'ifitwala_ed.api.admissions_crm.assign_inquiry_from_inbox',
			expect.objectContaining({
				inquiry: 'INQ-0001',
				assigned_to: 'admissions@example.com',
				assignment_lane: 'Admission',
				client_request_id: expect.stringMatching(/^admission-inquiry-assign-/),
			})
		);
		expect(emitMock).toHaveBeenCalledWith('admissions_inbox:invalidate');
	});
});
