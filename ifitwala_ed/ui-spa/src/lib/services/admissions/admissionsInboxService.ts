import { api } from '@/lib/client';
import {
	SIGNAL_ADMISSIONS_INBOX_INVALIDATE,
	uiSignals,
} from '@/lib/uiSignals';

import type {
	AdmissionsInboxContext,
	AdmissionsInboxRequest,
	AdmissionsInboxMutationResponse,
	ArchiveInquiryFromInboxRequest,
	AssignAdmissionConversationRequest,
	AssignInquiryFromInboxRequest,
	ConfirmAdmissionExternalIdentityRequest,
	CreateAdmissionsIntakeRequest,
	CreateInquiryFromAdmissionConversationRequest,
	InviteInquiryToApplyFromInboxRequest,
	LinkAdmissionConversationRequest,
	LogAdmissionMessageRequest,
	MarkInquiryContactedFromInboxRequest,
	QualifyInquiryFromInboxRequest,
	RecordAdmissionCrmActivityRequest,
	SendAdmissionsCaseMessageFromInboxRequest,
	UpdateAdmissionConversationStatusRequest,
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

export function assignAdmissionConversation(payload: AssignAdmissionConversationRequest) {
	return submitMutation(
		'ifitwala_ed.api.admissions_crm.assign_admission_conversation',
		payload,
		'admission-conversation-assign'
	);
}

export function updateAdmissionConversationStatus(
	payload: UpdateAdmissionConversationStatusRequest
) {
	return submitMutation(
		'ifitwala_ed.api.admissions_crm.update_admission_conversation_status',
		payload,
		'admission-conversation-status'
	);
}

export function createInquiryFromAdmissionConversation(
	payload: CreateInquiryFromAdmissionConversationRequest
) {
	return submitMutation(
		'ifitwala_ed.api.admissions_crm.create_inquiry_from_admission_conversation',
		payload,
		'admission-create-inquiry'
	);
}

export function assignInquiryFromInbox(payload: AssignInquiryFromInboxRequest) {
	return submitMutation(
		'ifitwala_ed.api.admissions_crm.assign_inquiry_from_inbox',
		payload,
		'admission-inquiry-assign'
	);
}

export function archiveInquiryFromInbox(payload: ArchiveInquiryFromInboxRequest) {
	return submitMutation(
		'ifitwala_ed.api.admissions_crm.archive_inquiry_from_inbox',
		payload,
		'admission-inquiry-archive'
	);
}

export function markInquiryContactedFromInbox(payload: MarkInquiryContactedFromInboxRequest) {
	return submitMutation(
		'ifitwala_ed.api.admissions_crm.mark_inquiry_contacted_from_inbox',
		payload,
		'admission-inquiry-contacted'
	);
}

export function qualifyInquiryFromInbox(payload: QualifyInquiryFromInboxRequest) {
	return submitMutation(
		'ifitwala_ed.api.admissions_crm.qualify_inquiry_from_inbox',
		payload,
		'admission-inquiry-qualify'
	);
}

export function inviteInquiryToApplyFromInbox(payload: InviteInquiryToApplyFromInboxRequest) {
	return submitMutation(
		'ifitwala_ed.api.admissions_crm.invite_inquiry_to_apply_from_inbox',
		payload,
		'admission-inquiry-invite'
	);
}

export function createAdmissionsIntake(payload: CreateAdmissionsIntakeRequest) {
	return submitMutation(
		'ifitwala_ed.api.admissions_crm.create_admissions_intake',
		payload,
		'admission-intake'
	);
}

export function sendAdmissionsCaseMessageFromInbox(
	payload: SendAdmissionsCaseMessageFromInboxRequest
) {
	return submitMutation(
		'ifitwala_ed.api.admissions_communication.send_admissions_case_message',
		payload,
		'admission-case-message'
	);
}
