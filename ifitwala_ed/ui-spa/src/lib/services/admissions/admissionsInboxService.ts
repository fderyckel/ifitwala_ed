import { api } from '@/lib/client';
import {
	SIGNAL_ADMISSIONS_INBOX_INVALIDATE,
	uiSignals,
} from '@/lib/uiSignals';

import type {
	AdmissionsInboxContext,
	AdmissionsInboxRequest,
	AdmissionsInboxMutationResponse,
	ConfirmAdmissionExternalIdentityRequest,
	LinkAdmissionConversationRequest,
	LogAdmissionMessageRequest,
	RecordAdmissionCrmActivityRequest,
} from '@/types/contracts/admissions_inbox/get_admissions_inbox_context';

export async function getAdmissionsInboxContext(
	payload: AdmissionsInboxRequest = {}
): Promise<AdmissionsInboxContext> {
	return api(
		'ifitwala_ed.api.admissions_inbox.get_admissions_inbox_context',
		payload
	) as Promise<AdmissionsInboxContext>;
}

function clientRequestId(prefix: string) {
	const random =
		typeof crypto !== 'undefined' && 'randomUUID' in crypto
			? crypto.randomUUID()
			: `${Date.now()}-${Math.random().toString(36).slice(2)}`;
	return `${prefix}-${random}`;
}

function withClientRequestId<TPayload extends { client_request_id?: string | null }>(
	payload: TPayload,
	prefix: string
) {
	return {
		...payload,
		client_request_id: payload.client_request_id || clientRequestId(prefix),
	};
}

async function submitMutation<TPayload extends { client_request_id?: string | null }>(
	method: string,
	payload: TPayload,
	prefix: string
): Promise<AdmissionsInboxMutationResponse> {
	const response = (await api(method, withClientRequestId(payload, prefix))) as AdmissionsInboxMutationResponse;
	uiSignals.emit(SIGNAL_ADMISSIONS_INBOX_INVALIDATE);
	return response;
}

export function logAdmissionMessage(payload: LogAdmissionMessageRequest) {
	return submitMutation(
		'ifitwala_ed.api.admissions_crm.log_admission_message',
		payload,
		'admission-message'
	);
}

export function recordAdmissionCrmActivity(payload: RecordAdmissionCrmActivityRequest) {
	return submitMutation(
		'ifitwala_ed.api.admissions_crm.record_admission_crm_activity',
		payload,
		'admission-activity'
	);
}

export function linkAdmissionConversation(payload: LinkAdmissionConversationRequest) {
	return submitMutation(
		'ifitwala_ed.api.admissions_crm.link_admission_conversation',
		payload,
		'admission-link'
	);
}

export function confirmAdmissionExternalIdentity(payload: ConfirmAdmissionExternalIdentityRequest) {
	return submitMutation(
		'ifitwala_ed.api.admissions_crm.confirm_admission_external_identity',
		payload,
		'admission-identity'
	);
}
