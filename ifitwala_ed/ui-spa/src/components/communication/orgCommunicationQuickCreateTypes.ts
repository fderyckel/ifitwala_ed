import type { OrgCommunicationAttachmentRow } from '@/types/contracts/org_communication_attachments/shared';
import type { UploadProgressState } from '@/lib/uploadProgress';

export type QuickCreateSelectOption = string | { label?: string | null; value?: string | null };
export type MessageEditorButton = string | string[];
export type RecipientField = 'to_staff' | 'to_students' | 'to_guardians';
export type AudienceTargetSearchKind = 'team' | 'student_group';

export type AudienceTargetSearchItem = {
	value: string;
	label: string;
	description: string;
};

export type AudienceRowState = {
	id: string;
	preset_key: string;
	target_mode: string;
	school: string;
	team: string;
	team_label: string;
	student_group: string;
	student_group_label: string;
	include_descendants: boolean;
	to_staff: boolean;
	to_students: boolean;
	to_guardians: boolean;
	note: string;
	search_kind: AudienceTargetSearchKind | null;
	search_query: string;
	search_results: AudienceTargetSearchItem[];
	search_loading: boolean;
	search_message: string;
};

export type RecipientToggleDefinition = {
	field: RecipientField;
	label: string;
};

export type ClassEventContextCard = {
	label: string;
	value: string;
};

export type AudienceSummaryRow = {
	id: string;
	scope: string;
	recipients: string;
};

export type LinkDraftState = {
	title: string;
	external_url: string;
};

export type AttachmentSectionState = {
	helpText: string;
	attachmentRows: OrgCommunicationAttachmentRow[];
	attachmentErrorMessage: string;
	attachmentActionsDisabled: boolean;
	removeDisabled: boolean;
	showLinkComposer: boolean;
	linkDraft: LinkDraftState;
	linkDraftReady: boolean;
	uploadProgress: UploadProgressState | null;
	uploadProgressLabel: string;
};
