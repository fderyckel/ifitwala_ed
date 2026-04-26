// ifitwala_ed/ui-spa/src/lib/admission.ts

import { api } from './client';

export const ADMISSION_API = {
	dashboard: 'ifitwala_ed.api.inquiry.get_dashboard_data',
	admissionsCockpit: 'ifitwala_ed.api.admission_cockpit.get_admissions_cockpit_data',
	admissionsCockpitSendOffer: 'ifitwala_ed.api.admission_cockpit.send_admissions_cockpit_offer',
	admissionsCockpitHydrateRequest:
		'ifitwala_ed.api.admission_cockpit.hydrate_admissions_cockpit_request',
	admissionsCockpitGenerateDepositInvoice:
		'ifitwala_ed.api.admission_cockpit.generate_admissions_cockpit_deposit_invoice',
	admissionsCaseThread: 'ifitwala_ed.api.admissions_communication.get_admissions_case_thread',
	admissionsCaseMessageSend:
		'ifitwala_ed.api.admissions_communication.send_admissions_case_message',
	admissionsCaseMarkRead:
		'ifitwala_ed.api.admissions_communication.mark_admissions_case_thread_read',
	inquiryTypes: 'ifitwala_ed.api.inquiry.get_inquiry_types',
	inquirySources: 'ifitwala_ed.api.inquiry.get_inquiry_sources',
	organizations: 'ifitwala_ed.api.inquiry.get_inquiry_organizations',
	schools: 'ifitwala_ed.api.inquiry.get_inquiry_schools',
	// Reusing the existing link query if needed, though often we just want a simple list for dropdowns
	academicYears: 'ifitwala_ed.api.inquiry.academic_year_link_query',
	users: 'ifitwala_ed.api.inquiry.admission_user_link_query',
};

export type DashboardFilters = {
	date_mode?: 'preset' | 'custom' | 'academic_year';
	date_preset?: string;
	from_date?: string;
	to_date?: string;
	academic_year?: string;
	type_of_inquiry?: string;
	source?: string;
	assigned_to?: string;
	assignment_lane?: 'Admission' | 'Staff' | '';
	sla_status?: string; // 'Overdue', 'Due Today', 'Upcoming'
	organization?: string;
	school?: string;
};

export function getInquiryDashboardData(filters: DashboardFilters = {}) {
	return api(ADMISSION_API.dashboard, { filters });
}

export type AdmissionsCockpitFilters = {
	organization?: string;
	school?: string;
	assigned_to_me?: number;
	include_terminal?: number;
	application_statuses?: string[];
	limit?: number;
};

export function getAdmissionsCockpitData(filters: AdmissionsCockpitFilters = {}) {
	return api(ADMISSION_API.admissionsCockpit, { filters });
}

export type AdmissionsCockpitAepActionRequest = {
	applicant_enrollment_plan: string;
};

export type AdmissionsCockpitAepActionResponse = {
	ok: boolean;
	applicant_enrollment_plan: string;
	status?: string;
	open_url?: string | null;
	program_enrollment_request?: string | null;
	program_enrollment_request_url?: string | null;
	created?: boolean;
	deposit?: Record<string, unknown>;
	invoice?: Record<string, unknown>;
};

export function sendAdmissionsCockpitOffer(payload: AdmissionsCockpitAepActionRequest) {
	return api(
		ADMISSION_API.admissionsCockpitSendOffer,
		payload
	) as Promise<AdmissionsCockpitAepActionResponse>;
}

export function hydrateAdmissionsCockpitRequest(payload: AdmissionsCockpitAepActionRequest) {
	return api(
		ADMISSION_API.admissionsCockpitHydrateRequest,
		payload
	) as Promise<AdmissionsCockpitAepActionResponse>;
}

export function generateAdmissionsCockpitDepositInvoice(payload: AdmissionsCockpitAepActionRequest) {
	return api(
		ADMISSION_API.admissionsCockpitGenerateDepositInvoice,
		payload
	) as Promise<AdmissionsCockpitAepActionResponse>;
}

export type AdmissionsCaseThreadRequest = {
	context_doctype: 'Student Applicant';
	context_name: string;
	limit_start?: number;
	limit?: number;
};

export type AdmissionsCaseMessage = {
	name: string;
	user: string;
	full_name: string;
	body: string;
	direction: 'ApplicantToStaff' | 'StaffToApplicant' | 'Internal';
	visibility: string;
	applicant_visible: boolean;
	created_at?: string | null;
	modified_at?: string | null;
};

export type AdmissionsCaseThreadResponse = {
	thread_name?: string | null;
	messages: AdmissionsCaseMessage[];
	unread_count: number;
};

export function getAdmissionsCaseThread(payload: AdmissionsCaseThreadRequest) {
	return api(ADMISSION_API.admissionsCaseThread, payload) as Promise<AdmissionsCaseThreadResponse>;
}

export type SendAdmissionsCaseMessageRequest = {
	context_doctype: 'Student Applicant';
	context_name: string;
	body: string;
	applicant_visible?: number;
	client_request_id?: string;
};

export type SendAdmissionsCaseMessageResponse = {
	thread_name: string;
	message: AdmissionsCaseMessage;
};

export function sendAdmissionsCaseMessage(payload: SendAdmissionsCaseMessageRequest) {
	return api(
		ADMISSION_API.admissionsCaseMessageSend,
		payload
	) as Promise<SendAdmissionsCaseMessageResponse>;
}

export function markAdmissionsCaseRead(payload: {
	context_doctype: 'Student Applicant';
	context_name: string;
}) {
	return api(ADMISSION_API.admissionsCaseMarkRead, payload) as Promise<{
		ok: boolean;
		thread_name?: string | null;
	}>;
}

export function getInquiryTypes() {
	return api(ADMISSION_API.inquiryTypes);
}

export function getInquirySources() {
	return api(ADMISSION_API.inquirySources);
}

export function searchAcademicYears(txt: string) {
	return api(ADMISSION_API.academicYears, {
		doctype: 'Academic Year',
		txt,
		searchfield: 'name',
		start: 0,
		page_len: 20,
		filters: {},
	});
}

export function searchAdmissionUsers(txt: string) {
	return api(ADMISSION_API.users, {
		doctype: 'User',
		txt,
		searchfield: 'full_name',
		start: 0,
		page_len: 20,
		filters: {},
	});
}

export function getInquiryOrganizations() {
	return api(ADMISSION_API.organizations);
}

export function getInquirySchools() {
	return api(ADMISSION_API.schools);
}
