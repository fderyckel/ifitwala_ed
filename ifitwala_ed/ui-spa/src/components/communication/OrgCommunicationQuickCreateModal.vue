<!-- ifitwala_ed/ui-spa/src/components/communication/OrgCommunicationQuickCreateModal.vue -->
<template>
	<TransitionRoot as="template" :show="open" @after-leave="emitAfterLeave">
		<Dialog
			as="div"
			class="if-overlay if-overlay--meeting"
			:style="overlayStyle"
			:initialFocus="initialFocus"
			@close="onDialogClose"
		>
			<TransitionChild
				as="template"
				enter="if-overlay__fade-enter"
				enter-from="if-overlay__fade-from"
				enter-to="if-overlay__fade-to"
				leave="if-overlay__fade-leave"
				leave-from="if-overlay__fade-to"
				leave-to="if-overlay__fade-from"
			>
				<div class="if-overlay__backdrop" @click="handleClose('backdrop')" />
			</TransitionChild>

			<div class="if-overlay__wrap">
				<TransitionChild
					as="template"
					enter="if-overlay__panel-enter"
					enter-from="if-overlay__panel-from"
					enter-to="if-overlay__panel-to"
					leave="if-overlay__panel-leave"
					leave-from="if-overlay__panel-to"
					leave-to="if-overlay__panel-from"
				>
					<DialogPanel class="if-overlay__panel">
						<button
							ref="initialFocus"
							type="button"
							class="sr-only"
							aria-hidden="true"
							tabindex="0"
							@click="handleClose('programmatic')"
						>
							Close
						</button>

						<div class="if-overlay__header px-6 pt-6">
							<div class="min-w-0">
								<p class="type-overline text-ink/55">{{ eyebrow }}</p>
								<DialogTitle class="type-h2 text-ink">{{ overlayTitle }}</DialogTitle>
								<p class="mt-1 type-caption text-ink/65">
									{{ overlayDescription }}
								</p>
							</div>
							<button
								type="button"
								class="if-overlay__close"
								aria-label="Close"
								@click="handleClose('programmatic')"
							>
								<FeatherIcon name="x" class="h-5 w-5" />
							</button>
						</div>

						<div class="if-overlay__body space-y-5 px-6 pb-6">
							<div
								v-if="errorMessage"
								class="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 shadow-soft"
								role="alert"
							>
								<p class="type-body-strong text-rose-900">Action blocked</p>
								<p class="mt-1 whitespace-pre-wrap type-caption text-rose-900/80">
									{{ errorMessage }}
								</p>
							</div>

							<div
								v-if="optionsLoading"
								class="flex items-center gap-2 rounded-2xl border border-border/70 bg-white px-4 py-3 text-ink/70"
							>
								<Spinner class="h-4 w-4" />
								<span class="type-caption">Loading communication options...</span>
							</div>

							<form v-else class="space-y-5" @submit.prevent="submit">
								<input
									ref="attachmentFileInput"
									type="file"
									class="hidden"
									multiple
									@change="onAttachmentFileSelected"
								/>

								<OrgCommunicationQuickCreateClassEventComposer
									v-if="isClassEventMode"
									:class-event-context-cards="classEventContextCards"
									:form="form"
									:submitting="submitting"
									:status-options="statusOptions"
									:message-editor-buttons="messageEditorButtons"
									:class-event-audience-row="classEventAudienceRow"
									:attachment-section="attachmentSectionState"
									@update-message="updateMessage"
									@trigger-file-picker="triggerAttachmentFilePicker"
									@toggle-link-composer="toggleLinkComposer"
									@reset-link-draft="resetLinkDraft"
									@submit-link="submitLinkAttachment"
									@delete-attachment="deleteAttachment"
								/>

								<OrgCommunicationQuickCreateStaffHomeComposer
									v-else
									:form="form"
									:submitting="submitting"
									:communication-type-options="communicationTypeOptions"
									:organization-select-options="organizationSelectOptions"
									:school-select-options="schoolSelectOptions"
									:priority-options="priorityOptions"
									:portal-surface-options="portalSurfaceOptions"
									:interaction-mode-options="interactionModeOptions"
									:audience-presets="audiencePresets"
									:organization-help-text="organizationHelpText"
									:school-help-text="schoolHelpText"
									:issuing-school-selection-locked="issuingSchoolSelectionLocked"
									:audience-school-selection-locked="audienceSchoolSelectionLocked"
									:brief-dates-required="briefDatesRequired"
									:delivery-validation-message="deliveryValidationMessage"
									:audience-validation-message="audienceValidationMessage"
									:publish-action-status="publishActionStatus"
									:private-notes-disabled="privateNotesDisabled"
									:public-thread-disabled="publicThreadDisabled"
									:private-notes-help-text="privateNotesHelpText"
									:public-thread-help-text="publicThreadHelpText"
									:audience-rows="audienceRows"
									:recipient-toggle-definitions="recipientToggleDefinitions"
									:can-target-wide-school-scope="canTargetWideSchoolScope"
									:audience-summary-rows="audienceSummaryRows"
									:get-audience-row-title="getAudienceRowTitle"
									:get-audience-row-description="getAudienceRowDescription"
									:get-audience-search-items="getAudienceSearchItems"
									:summary-title="summaryTitle"
									:summary-subtitle="summarySubtitle"
									:issuing-scope-label="issuingScopeLabel"
									:message-editor-buttons="messageEditorButtons"
									:attachment-section="attachmentSectionState"
									:get-select-option-value="getSelectOptionValue"
									:get-select-option-label="getSelectOptionLabel"
									:add-audience-preset="addAudiencePreset"
									:remove-audience-row="removeAudienceRow"
									:is-recipient-disabled="isRecipientDisabled"
									:toggle-recipient="toggleRecipient"
									:search-audience-targets="searchAudienceTargets"
									:select-audience-search-item="selectAudienceSearchItem"
									:clear-audience-search-selection="clearAudienceSearchSelection"
									:update-message="updateMessage"
									:open-native-date-picker="openNativeDatePicker"
									@trigger-file-picker="triggerAttachmentFilePicker"
									@toggle-link-composer="toggleLinkComposer"
									@reset-link-draft="resetLinkDraft"
									@submit-link="submitLinkAttachment"
									@delete-attachment="deleteAttachment"
								/>

								<footer class="if-overlay__footer flex flex-wrap items-center justify-end gap-2">
									<button
										type="button"
										class="if-button if-button--secondary"
										:disabled="submitting"
										@click="handleClose('programmatic')"
									>
										Cancel
									</button>
									<button
										v-if="!isClassEventMode"
										type="button"
										class="if-button if-button--secondary"
										:disabled="draftSubmitDisabled"
										@click="submitDraft"
									>
										Save as draft
									</button>
									<button
										type="submit"
										class="if-button if-button--primary"
										:disabled="publishSubmitDisabled"
									>
										{{ primarySubmitLabel }}
									</button>
								</footer>
							</form>
						</div>
					</DialogPanel>
				</TransitionChild>
			</div>
		</Dialog>
	</TransitionRoot>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue';
import {
	Dialog,
	DialogPanel,
	DialogTitle,
	TransitionChild,
	TransitionRoot,
} from '@headlessui/vue';
import { FeatherIcon, Spinner } from 'frappe-ui';

import {
	addOrgCommunicationLink,
	createOrgCommunicationQuick,
	getOrgCommunicationQuickCreateOptions,
	removeOrgCommunicationAttachment,
	searchOrgCommunicationStudentGroups,
	searchOrgCommunicationTeams,
	uploadOrgCommunicationAttachment,
} from '@/lib/services/orgCommunicationQuickCreateService';
import type { OrgCommunicationAttachmentRow } from '@/types/contracts/org_communication_attachments/shared';
import type {
	Request as CreateOrgCommunicationQuickRequest,
	OrgCommunicationQuickAudienceRow,
} from '@/types/contracts/org_communication_quick_create/create_org_communication_quick';
import type {
	OrgCommunicationAudiencePreset,
	OrgCommunicationQuickReferenceStudentGroup,
	OrgCommunicationQuickReferenceTeam,
	Response as OrgCommunicationQuickCreateOptionsResponse,
} from '@/types/contracts/org_communication_quick_create/get_org_communication_quick_create_options';
import OrgCommunicationQuickCreateClassEventComposer from '@/components/communication/OrgCommunicationQuickCreateClassEventComposer.vue';
import OrgCommunicationQuickCreateStaffHomeComposer from '@/components/communication/OrgCommunicationQuickCreateStaffHomeComposer.vue';
import type {
	AttachmentSectionState,
	AudienceRowState,
	AudienceSummaryRow,
	ClassEventContextCard,
	AudienceTargetSearchItem,
	MessageEditorButton,
	RecipientField,
	RecipientToggleDefinition,
} from '@/components/communication/orgCommunicationQuickCreateTypes';

type CloseReason = 'backdrop' | 'esc' | 'programmatic';
type EntryMode = 'staff-home' | 'class-event';
type TopLevelErrorSource = '' | 'load' | 'submit' | 'attachment-precondition';

class AttachmentPreconditionError extends Error {}

const props = defineProps<{
	open: boolean;
	zIndex?: number;
	overlayId?: string;
	entryMode?: EntryMode | null;
	studentGroup?: string | null;
	school?: string | null;
	title?: string | null;
	sessionDate?: string | null;
	sessionTimeLabel?: string | null;
	courseLabel?: string | null;
	sourceLabel?: string | null;
}>();

const emit = defineEmits<{
	(e: 'close', reason: CloseReason): void;
	(e: 'after-leave'): void;
	(e: 'done', payload?: unknown): void;
}>();

const initialFocus = ref<HTMLElement | null>(null);
const attachmentFileInput = ref<HTMLInputElement | null>(null);
const optionsLoading = ref(false);
const submitting = ref(false);
const attachmentSubmitting = ref(false);
const errorMessage = ref('');
const topLevelErrorSource = ref<TopLevelErrorSource>('');
const attachmentErrorMessage = ref('');
const options = ref<OrgCommunicationQuickCreateOptionsResponse | null>(null);
const audienceRows = ref<AudienceRowState[]>([]);
const attachmentRows = ref<OrgCommunicationAttachmentRow[]>([]);
const savedCommunicationName = ref('');
const showLinkComposer = ref(false);

const form = reactive({
	title: '',
	communication_type: '',
	status: '',
	priority: '',
	portal_surface: '',
	publish_from: '',
	publish_to: '',
	brief_start_date: '',
	brief_end_date: '',
	brief_order: '',
	organization: '',
	school: '',
	message: '',
	internal_note: '',
	interaction_mode: '',
	allow_private_notes: true,
	allow_public_thread: false,
});

const linkDraft = reactive({
	title: '',
	external_url: '',
});

function setTopLevelError(message: string, source: Exclude<TopLevelErrorSource, ''>) {
	errorMessage.value = message;
	topLevelErrorSource.value = source;
}

function clearTopLevelError(source?: Exclude<TopLevelErrorSource, ''>) {
	if (source && topLevelErrorSource.value !== source) return;
	errorMessage.value = '';
	topLevelErrorSource.value = '';
}

const overlayStyle = computed(() => ({
	zIndex: props.zIndex ?? 70,
}));

const mode = computed<EntryMode>(() => {
	if (props.entryMode === 'class-event' || props.studentGroup) return 'class-event';
	return 'staff-home';
});

const isClassEventMode = computed(() => mode.value === 'class-event');
const canTargetWideSchoolScope = computed(() =>
	Boolean(options.value?.permissions?.can_target_wide_school_scope)
);
const context = computed(() => options.value?.context ?? null);
const audiencePresets = computed(() => options.value?.audience_presets ?? []);

const organizationSelectOptions = computed(() => {
	const rows = options.value?.references.organizations ?? [];
	return rows.map(row => ({
		label: row.abbr
			? `${row.abbr} · ${row.organization_name || row.name}`
			: row.organization_name || row.name,
		value: row.name,
	}));
});

const schoolSelectOptions = computed(() => {
	const rows = (options.value?.references.schools ?? []).filter(row => {
		if (!form.organization) return true;
		return !row.organization || row.organization === form.organization;
	});
	return rows.map(row => ({
		label: row.abbr ? `${row.abbr} · ${row.school_name || row.name}` : row.school_name || row.name,
		value: row.name,
	}));
});

const communicationTypeOptions = computed(() => options.value?.fields.communication_types ?? []);
const statusOptions = computed(() => options.value?.fields.statuses ?? []);
const priorityOptions = computed(() => options.value?.fields.priorities ?? []);
const portalSurfaceOptions = computed(() => options.value?.fields.portal_surfaces ?? []);
const interactionModeOptions = computed(() => options.value?.fields.interaction_modes ?? []);
const hasOrganizationAudience = computed(() =>
	audienceRows.value.some(row => row.target_mode === 'Organization')
);

function getSelectOptionValue(option: string | { value?: string | null }) {
	if (typeof option === 'string') return option;
	return String(option?.value ?? '');
}

function getSelectOptionLabel(option: string | { label?: string | null; value?: string | null }) {
	if (typeof option === 'string') return option;
	return String(option?.label ?? option?.value ?? '');
}

function getSchoolOptionLabel(name: string | null | undefined) {
	return (
		schoolSelectOptions.value.find(option => option.value === name)?.label || String(name || '')
	);
}

function getOrganizationOptionLabel(name: string | null | undefined) {
	return (
		organizationSelectOptions.value.find(option => option.value === name)?.label ||
		String(name || '')
	);
}

function buildTeamSearchItem(row: OrgCommunicationQuickReferenceTeam): AudienceTargetSearchItem {
	const label = row.team_code
		? `${row.team_code} · ${row.team_name || row.name}`
		: row.team_name || row.name;
	const description =
		getSchoolOptionLabel(row.school) || getOrganizationOptionLabel(row.organization) || 'Team';
	return {
		value: row.name,
		label,
		description,
	};
}

function buildStudentGroupSearchItem(
	row: OrgCommunicationQuickReferenceStudentGroup
): AudienceTargetSearchItem {
	const label = row.student_group_abbreviation
		? `${row.student_group_abbreviation} · ${row.student_group_name || row.name}`
		: row.student_group_name || row.name;
	const description = getSchoolOptionLabel(row.school) || row.group_based_on || 'Student group';
	return {
		value: row.name,
		label,
		description,
	};
}

const suggestedTeamItems = computed(() =>
	(options.value?.suggested_targets?.teams ?? []).map(buildTeamSearchItem)
);
const suggestedStudentGroupItems = computed(() =>
	(options.value?.suggested_targets?.student_groups ?? []).map(buildStudentGroupSearchItem)
);

const audienceSchoolSelectionLocked = computed(() => {
	if (isClassEventMode.value) return true;
	if (!context.value) return false;
	if (context.value.lock_to_default_school) return true;
	return !context.value.can_select_school;
});
const issuingSchoolSelectionLocked = computed(
	() => hasOrganizationAudience.value || audienceSchoolSelectionLocked.value
);

const recipientToggleDefinitions: RecipientToggleDefinition[] = [
	{ field: 'to_staff', label: 'Staff' },
	{ field: 'to_students', label: 'Students' },
	{ field: 'to_guardians', label: 'Guardians' },
];
const messageEditorButtons: MessageEditorButton[] = [
	'Paragraph',
	['Heading 2', 'Heading 3'],
	'Separator',
	'Bold',
	'Italic',
	'Underline',
	'Separator',
	'Bullet List',
	'Numbered List',
	'Separator',
	'Link',
	'Blockquote',
];

const eyebrow = computed(
	() => props.sourceLabel || (isClassEventMode.value ? 'Class Event' : 'Staff Home')
);
const overlayTitle = computed(() =>
	isClassEventMode.value ? 'Create class announcement' : 'Create org communication'
);
const overlayDescription = computed(() =>
	isClassEventMode.value
		? 'Create an org communication from this class context without leaving the calendar flow.'
		: 'Publish or save a communication for staff, students, guardians, or a student group from Staff Home.'
);
const isFuturePublishFrom = computed(() => {
	if (!form.publish_from) return false;
	return toTimestamp(form.publish_from) > Date.now();
});
const publishActionStatus = computed(() => {
	if (isClassEventMode.value) return form.status || 'Published';
	return isFuturePublishFrom.value ? 'Scheduled' : 'Published';
});
const primarySubmitLabel = computed(() =>
	isClassEventMode.value
		? form.status === 'Draft'
			? 'Save draft'
			: form.status === 'Scheduled'
				? 'Schedule announcement'
				: 'Publish announcement'
		: 'Publish'
);
const summaryTitle = computed(() =>
	form.title.trim() ? form.title.trim() : 'Untitled communication'
);
const summarySubtitle = computed(() => {
	if (isClassEventMode.value) {
		const parts = [props.courseLabel, props.sessionDate].filter(Boolean);
		return parts.length ? parts.join(' · ') : 'Class event communication';
	}
	return 'Check issuing scope, interaction settings, and audience rows before publishing.';
});
const issuingScopeLabel = computed(() => {
	const schoolOption = schoolSelectOptions.value.find(option => option.value === form.school);
	const orgOption = organizationSelectOptions.value.find(
		option => option.value === form.organization
	);
	if (schoolOption) return schoolOption.label;
	if (orgOption) return orgOption.label;
	return 'No issuing scope selected';
});
const briefDatesRequired = computed(() =>
	['Morning Brief', 'Everywhere'].includes(String(form.portal_surface || '').trim())
);
const privateNotesDisabled = computed(
	() => !['Structured Feedback'].includes(String(form.interaction_mode || '').trim())
);
const publicThreadDisabled = computed(
	() =>
		!['Structured Feedback', 'Student Q&A'].includes(String(form.interaction_mode || '').trim())
);
const privateNotesHelpText = computed(() => {
	const mode = String(form.interaction_mode || '').trim();
	if (mode === 'Structured Feedback') {
		return 'Use this when staff may need private follow-up that students or families will not see.';
	}
	if (mode === 'Student Q&A') {
		return 'For Student Q&A, use the setting below to choose shared replies or private staff notes.';
	}
	if (mode === 'Staff Comments') {
		return 'Staff Comments stays inside the staff thread, so this setting is not used.';
	}
	return 'Choose Structured Feedback if you want staff-only notes or questions here.';
});
const publicThreadHelpText = computed(() => {
	const mode = String(form.interaction_mode || '').trim();
	if (mode === 'Student Q&A') {
		return 'Students or families in the selected audience can reply here. Turn this off to keep replies visible only to staff.';
	}
	if (mode === 'Structured Feedback') {
		return 'Use this when recipients should be able to see and respond in the shared thread.';
	}
	if (mode === 'Staff Comments') {
		return 'Staff Comments stays inside the staff thread, so this setting is not used.';
	}
	return 'Choose Student Q&A or Structured Feedback if recipients should reply in a shared thread.';
});
const organizationHelpText = computed(
	() => 'Organization is required and defaults from your user scope.'
);
const schoolHelpText = computed(() => {
	if (!context.value) return 'Loading school scope...';
	if (isClassEventMode.value)
		return 'Class event entry keeps the issuing school aligned to the selected class.';
	if (hasOrganizationAudience.value) {
		return 'Leave Issuing School blank because Organization audience rows are organization-level.';
	}
	if (context.value.lock_to_default_school) {
		return 'Issuing School is fixed to your default school when your school scope is locked.';
	}
	if (context.value.can_select_school || context.value.is_privileged) {
		return context.value.is_privileged
			? 'Optional issuing school within your scope. Leave blank for organization-level communication.'
			: 'Optional issuing school from your organization scope.';
	}
	return 'No issuing school scope is configured. Use organization-level communication or ask admin to configure school scope.';
});
const classEventAudienceRow = computed(() => {
	if (!isClassEventMode.value) return null;
	return audienceRows.value[0] ?? null;
});
const classEventStudentGroupLabel = computed(() => {
	const studentGroupLabel = classEventAudienceRow.value?.student_group_label;
	if (studentGroupLabel) return studentGroupLabel;
	return (
		classEventAudienceRow.value?.student_group || props.studentGroup || 'Selected student group'
	);
});
const classEventScheduleLabel = computed(() => {
	const parts = [props.sessionDate, props.sessionTimeLabel].filter(Boolean);
	return parts.length ? parts.join(' · ') : 'Selected class event';
});
const attachmentSectionHelpText = computed(() =>
	isClassEventMode.value
		? 'Add a governed file or a link without leaving this class flow. The first attachment saves a draft automatically so the communication owns the file history.'
		: 'Add a governed file or a link without leaving Staff Home. The first attachment saves a draft automatically so the communication owns the file history.'
);
const classEventContextCards = computed<ClassEventContextCard[]>(() => [
	{
		label: 'Course',
		value: props.courseLabel || summaryTitle.value,
	},
	{
		label: 'Student group',
		value: classEventStudentGroupLabel.value,
	},
	{
		label: 'Session',
		value: classEventScheduleLabel.value,
	},
	{
		label: 'Issuing scope',
		value: issuingScopeLabel.value,
	},
]);
const linkDraftReady = computed(() => Boolean(linkDraft.external_url.trim()));
const attachmentActionsDisabled = computed(
	() => submitting.value || attachmentSubmitting.value || optionsLoading.value || !options.value
);

const audienceSummaryRows = computed<AudienceSummaryRow[]>(() =>
	audienceRows.value.map(row => {
		let scope = row.target_mode;
		if (row.target_mode === 'School Scope') {
			scope = getSchoolOptionLabel(row.school) || row.school || 'School scope';
		} else if (row.target_mode === 'Team') {
			scope = row.team_label || row.team || 'Team';
		} else if (row.target_mode === 'Organization') {
			scope = getOrganizationOptionLabel(form.organization) || form.organization || 'Organization';
		} else if (row.target_mode === 'Student Group') {
			scope = row.student_group_label || row.student_group || 'Student group';
		}
		const recipients = recipientToggleDefinitions
			.filter(recipient => Boolean(row[recipient.field]))
			.map(recipient => recipient.label)
			.join(', ');
		return {
			id: row.id,
			scope,
			recipients: recipients || 'No recipients selected',
		};
	})
);

const attachmentSectionState = computed<AttachmentSectionState>(() => ({
	helpText: attachmentSectionHelpText.value,
	attachmentRows: attachmentRows.value,
	attachmentErrorMessage: attachmentErrorMessage.value,
	attachmentActionsDisabled: attachmentActionsDisabled.value,
	removeDisabled: submitting.value || attachmentSubmitting.value,
	showLinkComposer: showLinkComposer.value,
	linkDraft,
	linkDraftReady: linkDraftReady.value,
}));

function getValidationMessage(draftMode = false) {
	if (!form.title.trim()) return 'Title is required.';
	if (!form.communication_type) return 'Communication type is required.';
	if (!draftMode && !form.status) return 'Status is required.';
	if (!form.organization) return 'Organization is required.';
	if (!draftMode && briefDatesRequired.value && !form.brief_start_date) {
		return 'Brief Start Date is required when Portal Surface is Morning Brief or Everywhere.';
	}
	if (
		form.brief_start_date &&
		form.brief_end_date &&
		form.brief_end_date < form.brief_start_date
	) {
		return 'Brief End Date cannot be before Brief Start Date.';
	}
	if (
		form.publish_from &&
		form.publish_to &&
		toTimestamp(form.publish_to) < toTimestamp(form.publish_from)
	) {
		return 'Publish Until cannot be earlier than Publish From.';
	}
	if (!draftMode && form.status === 'Scheduled' && !form.publish_from) {
		return "Scheduled communications must have a 'Publish From' datetime.";
	}
	if (
		!draftMode &&
		form.status === 'Scheduled' &&
		form.publish_from &&
		toTimestamp(form.publish_from) <= Date.now()
	) {
		return 'Publish From for a Scheduled communication must be in the future.';
	}
	if (draftMode) return '';
	if (!audienceRows.value.length)
		return 'Please add at least one Audience for this communication.';
	for (const row of audienceRows.value) {
		if (!row.target_mode) return 'Target Mode is required for each Audience row.';
		if (row.target_mode === 'School Scope' && !row.school) {
			return 'Audience row for School Scope must specify a School.';
		}
		if (row.target_mode === 'Team' && !row.team) {
			return 'Audience row for Team must specify a Team.';
		}
		if (row.target_mode === 'Student Group' && !row.student_group) {
			return 'Audience row for Student Group must specify a Student Group.';
		}
		if (!recipientToggleDefinitions.some(recipient => Boolean(row[recipient.field]))) {
			return 'Audience row must include at least one Recipient toggle.';
		}
		if (!canTargetWideSchoolScope.value && row.target_mode === 'School Scope' && row.to_staff) {
			return 'You are not allowed to target Staff at School Scope from your current role.';
		}
		if (!canTargetWideSchoolScope.value && row.target_mode === 'Organization') {
			return 'You are not allowed to target Organization audiences from your current role.';
		}
	}
	return '';
}

const publishValidationMessage = computed(() => getValidationMessage(false));
const draftValidationMessage = computed(() => getValidationMessage(true));

const deliveryValidationMessage = computed(() => {
	const message = publishValidationMessage.value;
	if (!message) return '';
	if (
		message.startsWith('Brief Start Date') ||
		message.startsWith('Brief End Date') ||
		message.startsWith('Publish Until') ||
		message.startsWith('Publish From') ||
		message.startsWith('Scheduled communications')
	) {
		return message;
	}
	return '';
});

const audienceValidationMessage = computed(() => {
	const message = draftValidationMessage.value || publishValidationMessage.value;
	if (!message) return '';
	if (
		message.startsWith('Please add at least one Audience') ||
		message.startsWith('Target Mode') ||
		message.startsWith('Audience row') ||
		message.startsWith('You are not allowed to target Staff')
	) {
		return message;
	}
	return '';
});

const draftSubmitDisabled = computed(
	() =>
		submitting.value ||
		optionsLoading.value ||
		!options.value ||
		Boolean(draftValidationMessage.value)
);

const publishSubmitDisabled = computed(
	() =>
		submitting.value ||
		optionsLoading.value ||
		!options.value ||
		Boolean(publishValidationMessage.value)
);

function emitAfterLeave() {
	emit('after-leave');
}

function handleClose(reason: CloseReason = 'programmatic') {
	emit('close', reason);
}

function onDialogClose(_payload: unknown) {
	// no-op by design
}

function onKeydown(event: KeyboardEvent) {
	if (!props.open) return;
	if (event.key === 'Escape') handleClose('esc');
}

watch(
	() => props.open,
	open => {
		if (open) document.addEventListener('keydown', onKeydown, true);
		else document.removeEventListener('keydown', onKeydown, true);
	},
	{ immediate: true }
);

watch(
	() => props.open,
	async open => {
		if (!open) return;
		clearTopLevelError();
		await bootstrap();
	},
	{ immediate: true }
);

watch(
	[
		() => form.title,
		() => form.communication_type,
		() => form.organization,
		() => form.publish_from,
		() => form.publish_to,
		() => form.brief_start_date,
		() => form.brief_end_date,
	],
	() => {
		clearTopLevelError('attachment-precondition');
	}
);

watch(
	() => form.organization,
	organization => {
		if (!organization) return;
		if (!issuingSchoolSelectionLocked.value) {
			const currentSchoolAllowed = schoolSelectOptions.value.some(
				option => option.value === form.school
			);
			if (!currentSchoolAllowed) {
				form.school = '';
			}
		}
		for (const row of audienceRows.value) {
			if (row.target_mode !== 'School Scope') continue;
			const rowSchoolAllowed = schoolSelectOptions.value.some(
				option => option.value === row.school
			);
			if (!rowSchoolAllowed) row.school = form.school;
		}
	}
);

watch(
	hasOrganizationAudience,
	hasOrganizationTarget => {
		if (hasOrganizationTarget) {
			form.school = '';
			return;
		}
		if (form.school || audienceSchoolSelectionLocked.value) return;
		const defaultSchool =
			(isClassEventMode.value ? '' : context.value?.default_school) ||
			(schoolSelectOptions.value.length === 1 ? schoolSelectOptions.value[0]?.value : '') ||
			'';
		if (defaultSchool) {
			form.school = defaultSchool;
		}
	},
	{ immediate: true }
);

watch(
	() => form.interaction_mode,
	modeValue => {
		const mode = String(modeValue || '').trim();
		if (mode === 'None') {
			form.allow_public_thread = false;
			form.allow_private_notes = false;
			return;
		}
		if (mode !== 'Structured Feedback') {
			form.allow_private_notes = false;
		}
		if (!['Structured Feedback', 'Student Q&A'].includes(mode)) {
			form.allow_public_thread = false;
		}
	}
);

onBeforeUnmount(() => {
	document.removeEventListener('keydown', onKeydown, true);
});

async function bootstrap() {
	await loadOptions();
	if (options.value) initializeForm();
}

async function loadOptions() {
	if (optionsLoading.value) return;
	optionsLoading.value = true;
	try {
		options.value = await getOrgCommunicationQuickCreateOptions({
			prefill_student_group: props.studentGroup || null,
		});
	} catch (error) {
		setTopLevelError(
			error instanceof Error ? error.message : 'Unable to load communication options.',
			'load'
		);
	} finally {
		optionsLoading.value = false;
	}
}

function initializeForm() {
	const defaults = options.value?.defaults;
	if (!defaults) return;

	const matchedSchool = props.school
		? (options.value?.references.schools ?? []).find(row => row.name === props.school)
		: null;
	const defaultOrganization =
		matchedSchool?.organization || context.value?.default_organization || '';
	const schoolCandidates = (options.value?.references.schools ?? []).filter(row => {
		if (!defaultOrganization) return true;
		return !row.organization || row.organization === defaultOrganization;
	});
	const defaultSchool =
		props.school ||
		(isClassEventMode.value ? '' : context.value?.default_school) ||
		(schoolCandidates.length === 1 ? schoolCandidates[0]?.name : '') ||
		'';

	form.title = props.title || '';
	form.communication_type = isClassEventMode.value
		? 'Class Announcement'
		: defaults.communication_type;
	form.status = isClassEventMode.value ? 'Published' : defaults.status;
	form.priority = defaults.priority;
	form.portal_surface = isClassEventMode.value ? 'Everywhere' : defaults.portal_surface;
	form.publish_from = formatDateTimeInput(new Date());
	form.publish_to = '';
	form.brief_start_date = props.sessionDate || '';
	form.brief_end_date = props.sessionDate || '';
	form.brief_order = '';
	form.organization = defaultOrganization;
	form.school = defaultSchool;
	form.message = '';
	form.internal_note = '';
	form.interaction_mode = isClassEventMode.value ? 'None' : defaults.interaction_mode;
	form.allow_private_notes = isClassEventMode.value
		? false
		: defaults.interaction_mode === 'None'
			? false
			: Boolean(defaults.allow_private_notes);
	form.allow_public_thread = isClassEventMode.value
		? false
		: defaults.interaction_mode === 'None'
			? false
			: Boolean(defaults.allow_public_thread);
	savedCommunicationName.value = '';
	attachmentRows.value = [];
	attachmentErrorMessage.value = '';
	showLinkComposer.value = false;
	linkDraft.title = '';
	linkDraft.external_url = '';

	if (isClassEventMode.value) {
		const classEventTarget = (options.value?.suggested_targets?.student_groups ?? []).find(
			row => row.name === props.studentGroup
		);
		audienceRows.value = [
			createAudienceRow({
				preset_key: 'class_event',
				target_mode: 'Student Group',
				student_group: props.studentGroup || '',
				student_group_label: classEventTarget
					? buildStudentGroupSearchItem(classEventTarget).label
					: props.studentGroup || '',
				to_students: true,
				to_guardians: false,
				to_staff: false,
			}),
		];
		return;
	}

	audienceRows.value = [];
}

function createAudienceRow(seed: Partial<AudienceRowState> = {}): AudienceRowState {
	const targetMode = seed.target_mode || 'School Scope';
	const row: AudienceRowState = {
		id: `aud_${Date.now()}_${Math.random().toString(16).slice(2)}`,
		preset_key: seed.preset_key || '',
		target_mode: targetMode,
		school: seed.school || '',
		team: seed.team || '',
		team_label: seed.team_label || '',
		student_group: seed.student_group || '',
		student_group_label: seed.student_group_label || '',
		include_descendants:
			targetMode === 'School Scope' ? Boolean(seed.include_descendants ?? true) : false,
		to_staff: Boolean(seed.to_staff ?? false),
		to_students: Boolean(seed.to_students ?? false),
		to_guardians: Boolean(seed.to_guardians ?? false),
		note: seed.note || '',
		search_kind:
			seed.search_kind ??
			(targetMode === 'Team' ? 'team' : targetMode === 'Student Group' ? 'student_group' : null),
		search_query: seed.search_query || '',
		search_results: seed.search_results ? [...seed.search_results] : [],
		search_loading: Boolean(seed.search_loading ?? false),
		search_message: seed.search_message || '',
	};
	applyAudienceDefaults(row);
	return row;
}

function removeAudienceRow(rowId: string) {
	audienceRows.value = audienceRows.value.filter(row => row.id !== rowId);
}

function allowedRecipientFields(targetMode: string): RecipientField[] {
	return (options.value?.recipient_rules?.[targetMode]?.allowed_fields ?? []) as RecipientField[];
}

function applyAudienceDefaults(row: AudienceRowState) {
	const allowed = new Set(allowedRecipientFields(row.target_mode));
	row.include_descendants =
		row.target_mode === 'School Scope' ? Boolean(row.include_descendants) : false;

	for (const recipient of recipientToggleDefinitions) {
		if (!allowed.has(recipient.field)) {
			row[recipient.field] = false;
		}
	}

	if (row.target_mode === 'Team') {
		row.to_staff = true;
		return;
	}

	if (row.target_mode === 'Organization') {
		if (!row.to_staff && !row.to_guardians) {
			row.to_staff = true;
		}
		return;
	}

	if (row.target_mode === 'Student Group') {
		if (isClassEventMode.value) {
			row.to_staff = false;
			row.to_students = true;
			return;
		}
		if (!row.to_staff && !row.to_students && !row.to_guardians) {
			row.to_students = true;
			row.to_guardians = true;
		}
		return;
	}

	if (row.target_mode === 'School Scope' && !row.school && form.school) {
		row.school = form.school;
	}
}

function applyAudiencePreset(row: AudienceRowState, preset: OrgCommunicationAudiencePreset) {
	row.preset_key = preset.key;
	for (const recipient of recipientToggleDefinitions) {
		row[recipient.field] = preset.default_fields.includes(recipient.field);
	}
	applyAudienceDefaults(row);
	if (row.search_kind === 'team') {
		row.search_results = suggestedTeamItems.value.slice(0, 8);
		row.search_message = row.search_results.length
			? 'Choose a suggested team or search by name.'
			: 'Search for the team you want to reach.';
	}
	if (row.search_kind === 'student_group') {
		row.search_results = suggestedStudentGroupItems.value.slice(0, 8);
		row.search_message = row.search_results.length
			? 'Choose a suggested class or search by name.'
			: 'Search for the class or student group you want to reach.';
	}
}

function addAudiencePreset(presetKey: string) {
	const preset = audiencePresets.value.find(option => option.key === presetKey);
	if (!preset) return;
	const row = createAudienceRow({
		preset_key: preset.key,
		target_mode: preset.target_mode,
		school: preset.target_mode === 'School Scope' ? form.school : '',
		include_descendants: preset.target_mode === 'School Scope',
	});
	applyAudiencePreset(row, preset);
	audienceRows.value.push(row);
}

function isRecipientDisabled(row: AudienceRowState, field: RecipientField) {
	const allowed = new Set(allowedRecipientFields(row.target_mode));
	if (!allowed.has(field)) return true;
	if (
		row.target_mode === 'School Scope' &&
		!canTargetWideSchoolScope.value &&
		field === 'to_staff'
	) {
		return true;
	}
	if (row.target_mode === 'Team' && field === 'to_staff') return true;
	if (isClassEventMode.value && row.target_mode === 'Student Group' && field === 'to_students')
		return true;
	return false;
}

function toggleRecipient(row: AudienceRowState, field: RecipientField, event: Event) {
	const target = event.target as HTMLInputElement | null;
	if (!target) return;
	row[field] = target.checked;
	applyAudienceDefaults(row);
}

function getAudienceSearchItems(row: AudienceRowState) {
	if (row.search_query.trim().length >= 2) {
		return row.search_results;
	}
	if (row.search_kind === 'team')
		return row.search_results.length ? row.search_results : suggestedTeamItems.value;
	if (row.search_kind === 'student_group') {
		return row.search_results.length ? row.search_results : suggestedStudentGroupItems.value;
	}
	return [];
}

function getAudiencePreset(row: AudienceRowState) {
	return audiencePresets.value.find(option => option.key === row.preset_key) || null;
}

function getAudienceRecipientSummary(row: AudienceRowState) {
	return recipientToggleDefinitions
		.filter(recipient => Boolean(row[recipient.field]))
		.map(recipient => recipient.label)
		.join(', ');
}

function getAudienceRowTitle(row: AudienceRowState) {
	return (
		getAudiencePreset(row)?.label ||
		(row.target_mode === 'Team'
			? 'Team audience'
			: row.target_mode === 'Student Group'
				? 'Class or student group'
				: row.target_mode === 'Organization'
					? 'Organization-wide'
					: 'School audience')
	);
}

function getAudienceRowDescription(row: AudienceRowState) {
	if (row.target_mode === 'School Scope') {
		const schoolLabel = getSchoolOptionLabel(row.school) || 'selected school scope';
		const recipients = getAudienceRecipientSummary(row) || 'Choose recipients';
		return `${schoolLabel} · ${recipients}`;
	}
	if (row.target_mode === 'Team') {
		const teamLabel = row.team_label || 'Choose a team';
		return `${teamLabel} · Staff`;
	}
	if (row.target_mode === 'Student Group') {
		const studentGroupLabel = row.student_group_label || 'Choose a class or student group';
		const recipients = getAudienceRecipientSummary(row) || 'Choose recipients';
		return `${studentGroupLabel} · ${recipients}`;
	}
	const recipients = getAudienceRecipientSummary(row) || 'Choose recipients';
	return `${getOrganizationOptionLabel(form.organization) || form.organization || 'Organization'} · ${recipients}`;
}

function clearAudienceSearchSelection(row: AudienceRowState) {
	if (row.search_kind === 'team') {
		row.team = '';
		row.team_label = '';
		row.search_results = suggestedTeamItems.value.slice(0, 8);
		row.search_message = row.search_results.length
			? 'Choose a suggested team or search by name.'
			: 'Search for the team you want to reach.';
		return;
	}
	if (row.search_kind === 'student_group') {
		row.student_group = '';
		row.student_group_label = '';
		row.search_results = suggestedStudentGroupItems.value.slice(0, 8);
		row.search_message = row.search_results.length
			? 'Choose a suggested class or search by name.'
			: 'Search for the class or student group you want to reach.';
	}
}

function selectAudienceSearchItem(row: AudienceRowState, item: AudienceTargetSearchItem) {
	if (row.search_kind === 'team') {
		row.team = item.value;
		row.team_label = item.label;
	}
	if (row.search_kind === 'student_group') {
		row.student_group = item.value;
		row.student_group_label = item.label;
	}
	row.search_message = `${item.label} selected.`;
}

async function searchAudienceTargets(row: AudienceRowState) {
	if (row.search_loading) return;
	const query = row.search_query.trim();
	if (row.search_kind === 'team') {
		if (query.length < 2) {
			row.search_results = suggestedTeamItems.value.slice(0, 8);
			row.search_message = row.search_results.length
				? 'Choose a suggested team or type at least 2 characters to search.'
				: 'Type at least 2 characters to search teams.';
			return;
		}
		row.search_loading = true;
		row.search_message = '';
		try {
			const response = await searchOrgCommunicationTeams({
				query,
				organization: form.organization || null,
				school: form.school || null,
				limit: 8,
			});
			row.search_results = (response.results || []).map(buildTeamSearchItem);
			row.search_message = row.search_results.length ? '' : 'No teams match that search yet.';
		} catch (error) {
			row.search_results = [];
			row.search_message = error instanceof Error ? error.message : 'Unable to search teams.';
		} finally {
			row.search_loading = false;
		}
		return;
	}
	if (row.search_kind === 'student_group') {
		if (query.length < 2) {
			row.search_results = suggestedStudentGroupItems.value.slice(0, 8);
			row.search_message = row.search_results.length
				? 'Choose a suggested class or type at least 2 characters to search.'
				: 'Type at least 2 characters to search classes.';
			return;
		}
		row.search_loading = true;
		row.search_message = '';
		try {
			const response = await searchOrgCommunicationStudentGroups({
				query,
				organization: form.organization || null,
				school: form.school || null,
				limit: 8,
			});
			row.search_results = (response.results || []).map(buildStudentGroupSearchItem);
			row.search_message = row.search_results.length
				? ''
				: 'No classes or student groups match that search yet.';
		} catch (error) {
			row.search_results = [];
			row.search_message =
				error instanceof Error ? error.message : 'Unable to search classes or student groups.';
		} finally {
			row.search_loading = false;
		}
	}
}

function updateMessage(content: string) {
	form.message = content;
}

function openNativeDatePicker(event: Event) {
	const input = event.currentTarget as HTMLInputElement | null;
	if (!input || input.disabled) return;

	const pickerInput = input as HTMLInputElement & { showPicker?: () => void };
	if (typeof pickerInput.showPicker === 'function') {
		try {
			pickerInput.showPicker();
			return;
		} catch {
			// Ignore browsers that expose the method but reject imperative open calls.
		}
	}

	input.focus();
}

function toFrappeDatetime(value: string) {
	if (!value) return null;
	if (value.includes('T')) {
		const [date, timeRaw] = value.split('T');
		const [hour = '00', minute = '00', second = '00'] = timeRaw.split(':');
		return `${date} ${hour}:${minute}:${second}`;
	}
	return value;
}

function formatDateInput(date: Date) {
	const year = date.getFullYear();
	const month = String(date.getMonth() + 1).padStart(2, '0');
	const day = String(date.getDate()).padStart(2, '0');
	return `${year}-${month}-${day}`;
}

function formatDateTimeInput(date: Date) {
	const hours = String(date.getHours()).padStart(2, '0');
	const minutes = String(date.getMinutes()).padStart(2, '0');
	return `${formatDateInput(date)}T${hours}:${minutes}`;
}

function toTimestamp(value: string) {
	const normalized = value.includes('T') ? value : value.replace(' ', 'T');
	const timestamp = new Date(normalized).getTime();
	return Number.isNaN(timestamp) ? 0 : timestamp;
}

function buildAudiencePayload(): OrgCommunicationQuickAudienceRow[] {
	if (isClassEventMode.value) {
		const row = classEventAudienceRow.value;
		return [
			{
				target_mode: 'Student Group',
				school: null,
				team: null,
				student_group: row?.student_group || props.studentGroup || null,
				include_descendants: 0,
				to_staff: 0,
				to_students: 1,
				to_guardians: row?.to_guardians ? 1 : 0,
				note: null,
			},
		];
	}
	return audienceRows.value.map(row => {
		const targetMode = row.target_mode;
		return {
			target_mode: targetMode,
			school: targetMode === 'School Scope' ? row.school || null : null,
			team: targetMode === 'Team' ? row.team || null : null,
			student_group: targetMode === 'Student Group' ? row.student_group || null : null,
			include_descendants: targetMode === 'School Scope' && row.include_descendants ? 1 : 0,
			to_staff: row.to_staff ? 1 : 0,
			to_students: row.to_students ? 1 : 0,
			to_guardians: row.to_guardians ? 1 : 0,
			note: row.note.trim() || null,
		};
	});
}

function buildPayload(statusOverride?: string): CreateOrgCommunicationQuickRequest {
	const briefStartDate = form.brief_start_date || null;
	const briefEndDate = form.brief_end_date || briefStartDate;
	const classEventMode = isClassEventMode.value;
	return {
		name: savedCommunicationName.value || null,
		title: form.title.trim(),
		communication_type: classEventMode ? 'Class Announcement' : form.communication_type,
		status: statusOverride || form.status,
		priority: form.priority,
		portal_surface: classEventMode ? 'Everywhere' : form.portal_surface,
		publish_from: toFrappeDatetime(form.publish_from),
		publish_to: toFrappeDatetime(form.publish_to),
		brief_start_date: briefStartDate,
		brief_end_date: briefEndDate,
		brief_order: form.brief_order ? Number(form.brief_order) : null,
		organization: form.organization || null,
		school: form.school || null,
		message: form.message || null,
		internal_note: form.internal_note || null,
		interaction_mode: classEventMode ? 'None' : form.interaction_mode || null,
		allow_private_notes: classEventMode ? 0 : form.allow_private_notes ? 1 : 0,
		allow_public_thread: classEventMode ? 0 : form.allow_public_thread ? 1 : 0,
		audiences: buildAudiencePayload(),
		client_request_id: `org_comm_${Date.now()}_${Math.random().toString(16).slice(2)}`,
	};
}

function upsertAttachmentRow(attachment: OrgCommunicationAttachmentRow) {
	const index = attachmentRows.value.findIndex(row => row.row_name === attachment.row_name);
	if (index >= 0) {
		attachmentRows.value.splice(index, 1, attachment);
		return;
	}
	attachmentRows.value.push(attachment);
}

function removeAttachmentRow(rowName: string) {
	attachmentRows.value = attachmentRows.value.filter(row => row.row_name !== rowName);
}

function toggleLinkComposer() {
	showLinkComposer.value = !showLinkComposer.value;
}

function resetLinkDraft() {
	linkDraft.title = '';
	linkDraft.external_url = '';
	showLinkComposer.value = false;
}

async function ensureSavedDraft() {
	if (savedCommunicationName.value) return savedCommunicationName.value;
	const draftValidationError = getAttachmentDraftBlocker();
	if (draftValidationError) {
		throw new AttachmentPreconditionError(draftValidationError);
	}
	try {
		const response = await createOrgCommunicationQuick(buildPayload('Draft'));
		savedCommunicationName.value = response.name;
		return response.name;
	} catch (error) {
		throw new AttachmentPreconditionError(
			error instanceof Error
				? error.message
				: 'Unable to save the draft before adding attachments.'
		);
	}
}

function triggerAttachmentFilePicker() {
	if (attachmentActionsDisabled.value) return;
	attachmentErrorMessage.value = '';
	const draftValidationError = getAttachmentDraftBlocker();
	if (draftValidationError) {
		setTopLevelError(draftValidationError, 'attachment-precondition');
		return;
	}
	clearTopLevelError('attachment-precondition');
	attachmentFileInput.value?.click();
}

async function onAttachmentFileSelected(event: Event) {
	const target = event.target as HTMLInputElement | null;
	const files = Array.from(target?.files || []);
	if (!files.length) return;

	attachmentSubmitting.value = true;
	attachmentErrorMessage.value = '';
	try {
		const orgCommunication = await ensureSavedDraft();
		clearTopLevelError('attachment-precondition');
		for (const file of files) {
			const response = await uploadOrgCommunicationAttachment({
				org_communication: orgCommunication,
				file,
			});
			upsertAttachmentRow(response.attachment);
		}
	} catch (error) {
		if (error instanceof AttachmentPreconditionError) {
			setTopLevelError(error.message, 'attachment-precondition');
		} else {
			attachmentErrorMessage.value =
				error instanceof Error ? error.message : 'Unable to upload the attachment.';
		}
	} finally {
		attachmentSubmitting.value = false;
		if (target) target.value = '';
	}
}

async function submitLinkAttachment() {
	if (!linkDraftReady.value) {
		attachmentErrorMessage.value = 'A valid https link is required.';
		return;
	}

	attachmentSubmitting.value = true;
	attachmentErrorMessage.value = '';
	try {
		const orgCommunication = await ensureSavedDraft();
		clearTopLevelError('attachment-precondition');
		const response = await addOrgCommunicationLink({
			org_communication: orgCommunication,
			title: linkDraft.title.trim() || null,
			external_url: linkDraft.external_url.trim(),
		});
		upsertAttachmentRow(response.attachment);
		resetLinkDraft();
	} catch (error) {
		if (error instanceof AttachmentPreconditionError) {
			setTopLevelError(error.message, 'attachment-precondition');
		} else {
			attachmentErrorMessage.value =
				error instanceof Error ? error.message : 'Unable to add the link.';
		}
	} finally {
		attachmentSubmitting.value = false;
	}
}

async function deleteAttachment(attachment: OrgCommunicationAttachmentRow) {
	if (!savedCommunicationName.value) return;
	attachmentSubmitting.value = true;
	attachmentErrorMessage.value = '';
	try {
		await removeOrgCommunicationAttachment({
			org_communication: savedCommunicationName.value,
			row_name: attachment.row_name,
		});
		removeAttachmentRow(attachment.row_name);
	} catch (error) {
		attachmentErrorMessage.value =
			error instanceof Error ? error.message : 'Unable to remove the attachment.';
	} finally {
		attachmentSubmitting.value = false;
	}
}

function isMessageEditorToolbarSubmitter(target: EventTarget | null) {
	if (!(target instanceof HTMLElement)) return false;
	return Boolean(target.closest('.if-org-communication-message-editor button'));
}

async function submit(event?: SubmitEvent) {
	if (isMessageEditorToolbarSubmitter(event?.submitter ?? null)) return;
	if (!isClassEventMode.value) {
		await submitPublish();
		return;
	}
	await submitWithStatus(form.status);
}

async function submitDraft() {
	await submitWithStatus('Draft');
}

async function submitPublish() {
	await submitWithStatus(isFuturePublishFrom.value ? 'Scheduled' : 'Published');
}

async function submitWithStatus(statusOverride: string) {
	const validationError =
		statusOverride === 'Draft' ? draftValidationMessage.value : publishValidationMessage.value;
	if (validationError) {
		setTopLevelError(validationError, 'submit');
		return;
	}

	clearTopLevelError();
	submitting.value = true;

	try {
		const response = await createOrgCommunicationQuick(buildPayload(statusOverride));
		savedCommunicationName.value = response.name;
		emit('close', 'programmatic');
		emit('done', response);
	} catch (error) {
		setTopLevelError(
			error instanceof Error ? error.message : 'Unable to create communication.',
			'submit'
		);
	} finally {
		submitting.value = false;
	}
}

function getAttachmentDraftBlocker() {
	if (savedCommunicationName.value) return '';
	if (optionsLoading.value || !options.value) {
		return 'Communication options are still loading. Wait a moment, then try again.';
	}
	return draftValidationMessage.value;
}
</script>
