<template>
	<div data-testid="admissions-inbox-page" class="staff-shell admissions-inbox-page">
		<header class="page-header">
			<div class="page-header__intro">
				<h1 class="type-h1 text-ink">Admissions Inbox</h1>
				<p class="type-meta text-slate-token/80">Lead and applicant communication queues</p>
			</div>
			<div class="page-header__actions">
				<p v-if="lastRefreshedLabel" class="type-caption text-slate-token/70">
					Updated {{ lastRefreshedLabel }}
				</p>
				<button
					type="button"
					data-testid="admissions-inbox-refresh"
					class="if-button if-button--quiet"
					:disabled="loading"
					@click="refreshInbox('manual')"
				>
					<FeatherIcon name="refresh-cw" class="h-4 w-4" />
					<span>{{ loading ? 'Refreshing' : 'Refresh' }}</span>
				</button>
			</div>
		</header>

		<section
			v-if="error"
			data-testid="admissions-inbox-error"
			role="alert"
			class="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
		>
			<div class="flex flex-wrap items-center justify-between gap-3">
				<p>{{ error }}</p>
				<button type="button" class="if-button if-button--quiet" @click="refreshInbox('retry')">
					Retry
				</button>
			</div>
		</section>

		<section class="inbox-summary" aria-label="Admissions inbox summary">
			<div class="inbox-summary__tile">
				<span class="type-overline text-slate-token/70">Needs Reply</span>
				<strong>{{ countForQueue('needs_reply') }}</strong>
			</div>
			<div class="inbox-summary__tile">
				<span class="type-overline text-slate-token/70">Unassigned</span>
				<strong>{{ countForQueue('unassigned') }}</strong>
			</div>
			<div class="inbox-summary__tile">
				<span class="type-overline text-slate-token/70">Visible Items</span>
				<strong>{{ totalVisibleRows }}</strong>
			</div>
			<div class="inbox-summary__tile">
				<span class="type-overline text-slate-token/70">CRM Threads</span>
				<strong>{{ sourceCount('crm_conversations') }}</strong>
			</div>
		</section>

		<section class="admissions-inbox-layout">
			<nav class="queue-rail" aria-label="Admissions inbox queues">
				<button
					v-for="queue in queues"
					:key="queue.id"
					type="button"
					:data-testid="`queue-${queue.id}`"
					class="queue-button"
					:class="{ 'queue-button--active': queue.id === activeQueueId }"
					@click="selectQueue(queue.id)"
				>
					<span>{{ queue.label }}</span>
					<strong>{{ queue.count }}</strong>
				</button>
			</nav>

			<section class="queue-panel">
				<header class="queue-panel__header">
					<div>
						<p class="type-overline text-slate-token/70">Queue</p>
						<h2 class="type-h2 text-ink">{{ activeQueue?.label || 'Admissions Inbox' }}</h2>
					</div>
					<span class="queue-panel__count">{{ activeQueue?.count || 0 }}</span>
				</header>

				<div v-if="initialLoading" class="queue-panel__empty">Loading admissions inbox...</div>

				<div v-else-if="!activeRows.length" class="queue-panel__empty">
					No items in this queue.
				</div>

				<div v-else class="queue-rows">
					<article
						v-for="row in activeRows"
						:key="row.id"
						:data-testid="`inbox-row-${row.id}`"
						class="inbox-row-card"
						:class="rowToneClass(row)"
					>
						<header class="inbox-row-card__header">
							<div class="inbox-row-card__title">
								<p class="type-overline text-slate-token/70">{{ rowKindLabel(row) }}</p>
								<h3 class="type-h3 text-ink">{{ row.title || 'Admissions item' }}</h3>
								<p v-if="row.subtitle" class="type-caption text-slate-token/70">
									{{ row.subtitle }}
								</p>
							</div>
							<div class="inbox-row-card__pills">
								<span class="inbox-pill inbox-pill--stage">{{ stageLabel(row.stage) }}</span>
								<span v-if="row.needs_reply" class="inbox-pill inbox-pill--reply"
									>Needs reply</span
								>
								<span v-if="row.unread_count" class="inbox-pill inbox-pill--unread">
									{{ row.unread_count }} unread
								</span>
							</div>
						</header>

						<p v-if="row.last_message_preview" class="inbox-row-card__preview">
							{{ row.last_message_preview }}
						</p>

						<dl class="inbox-row-card__meta">
							<div v-for="item in rowMeta(row)" :key="item.label">
								<dt>{{ item.label }}</dt>
								<dd>{{ item.value }}</dd>
							</div>
						</dl>

						<footer class="inbox-row-card__footer">
							<div class="inbox-row-card__footer-actions">
								<button
									v-if="hasRowActions(row)"
									type="button"
									:data-testid="`inbox-actions-${row.id}`"
									class="if-button if-button--quiet"
									@click="openActionDrawer(row)"
								>
									<FeatherIcon name="sliders" class="h-4 w-4" />
									<span>Actions</span>
								</button>
								<a
									v-if="safeOpenUrl(row)"
									:href="safeOpenUrl(row)"
									target="_blank"
									rel="noopener noreferrer"
									class="if-button if-button--quiet"
								>
									<FeatherIcon name="external-link" class="h-4 w-4" />
									<span>Open</span>
								</a>
							</div>
							<p v-if="!safeOpenUrl(row)" class="type-caption text-slate-token/70">
								Open unavailable: no permitted destination returned. Refresh or ask an admissions
								manager to check access.
							</p>
						</footer>
					</article>
				</div>

				<p v-if="activeQueue?.has_more" class="queue-panel__more type-caption text-slate-token/70">
					More items are available after the current page limit.
				</p>
			</section>
		</section>

		<aside
			v-if="selectedRow"
			data-testid="admissions-inbox-action-drawer"
			class="action-drawer"
			aria-label="Admissions inbox action drawer"
		>
			<header class="action-drawer__header">
				<div class="min-w-0">
					<p class="type-overline text-slate-token/70">Selected item</p>
					<h2 class="type-h2 text-ink">{{ selectedRow.title }}</h2>
					<p v-if="selectedRow.subtitle" class="type-caption text-slate-token/70">
						{{ selectedRow.subtitle }}
					</p>
				</div>
				<button
					type="button"
					data-testid="admissions-inbox-action-close"
					class="if-button if-button--quiet"
					@click="closeActionDrawer"
				>
					<FeatherIcon name="x" class="h-4 w-4" />
					<span>Close</span>
				</button>
			</header>

			<div class="action-drawer__body">
				<section class="action-choice-list" aria-label="Available inbox actions">
					<button
						v-for="action in selectedRowActionStates"
						:key="action.id"
						type="button"
						:data-testid="`inbox-action-${action.id}`"
						class="action-choice"
						:class="{ 'action-choice--active': action.id === activeActionId }"
						:disabled="!action.enabled"
						@click="selectAction(action.id)"
					>
						<span>{{ action.label }}</span>
						<small>{{ action.enabled ? action.description : action.disabledReason }}</small>
					</button>
				</section>

				<p v-if="unsupportedActionLabels.length" class="action-drawer__note">
					Handled from the source record in this phase: {{ unsupportedActionLabels.join(', ') }}.
				</p>

				<div v-if="!activeActionId" class="action-drawer__empty">
					No executable Inbox workflow is available for this item yet. Open the source record to
					continue.
				</div>

				<form v-else class="action-form" @submit.prevent="submitActiveAction">
					<template v-if="isLogAction(activeActionId)">
						<label class="action-field">
							<span>Message</span>
							<textarea
								v-model="actionForm.body"
								data-testid="action-message-body"
								rows="5"
								placeholder="Record the admissions reply or message outcome"
							/>
						</label>
					</template>

					<template v-else-if="activeActionId === 'record_activity'">
						<label class="action-field">
							<span>Activity Type</span>
							<select v-model="actionForm.activity_type" data-testid="action-activity-type">
								<option v-for="type in activityTypes" :key="type" :value="type">{{ type }}</option>
							</select>
						</label>
						<label class="action-field">
							<span>Outcome</span>
							<input v-model="actionForm.outcome" type="text" placeholder="Optional outcome" />
						</label>
						<label class="action-field">
							<span>Next Action On</span>
							<input v-model="actionForm.next_action_on" type="date" />
						</label>
						<label class="action-field">
							<span>Note</span>
							<textarea v-model="actionForm.note" rows="4" placeholder="Structured CRM note" />
						</label>
					</template>

					<template v-else-if="isAssignAction(activeActionId)">
						<label class="action-field">
							<span>Assigned To</span>
							<input
								v-model="actionForm.assigned_to"
								data-testid="action-assigned-to"
								type="text"
								placeholder="Admissions user email"
							/>
						</label>
						<label v-if="selectedRow?.inquiry" class="action-field">
							<span>Assignment Lane</span>
							<select v-model="actionForm.assignment_lane" data-testid="action-assignment-lane">
								<option v-for="lane in assignmentLanes" :key="lane || 'default'" :value="lane">
									{{ lane || 'Default' }}
								</option>
							</select>
						</label>
					</template>

					<template v-else-if="activeActionId === 'create_inquiry'">
						<label class="action-field">
							<span>Type of Inquiry</span>
							<select v-model="actionForm.type_of_inquiry" data-testid="action-inquiry-type">
								<option v-for="type in inquiryTypes" :key="type" :value="type">{{ type }}</option>
							</select>
						</label>
						<label class="action-field">
							<span>Source</span>
							<select v-model="actionForm.inquiry_source" data-testid="action-inquiry-source">
								<option v-for="source in inquirySources" :key="source" :value="source">
									{{ source }}
								</option>
							</select>
						</label>
						<label class="action-field">
							<span>Message</span>
							<textarea
								v-model="actionForm.create_inquiry_message"
								data-testid="action-create-inquiry-message"
								rows="4"
								placeholder="Optional Inquiry message"
							/>
						</label>
					</template>

					<template v-else-if="isArchiveAction(activeActionId)">
						<label class="action-field">
							<span>Reason</span>
							<textarea
								v-model="actionForm.archive_reason"
								data-testid="action-archive-reason"
								rows="4"
								placeholder="Reason for closing this admissions item"
							/>
						</label>
					</template>

					<template v-else-if="activeActionId === 'invite_to_apply'">
						<label class="action-field">
							<span>School</span>
							<input
								v-model="actionForm.invite_school"
								data-testid="action-invite-school"
								type="text"
								placeholder="School document name"
							/>
						</label>
						<label class="action-field">
							<span>Organization</span>
							<input
								v-model="actionForm.invite_organization"
								data-testid="action-invite-organization"
								type="text"
								placeholder="Optional Organization document name"
							/>
						</label>
					</template>

					<template v-else-if="activeActionId === 'link_inquiry'">
						<label class="action-field">
							<span>Inquiry</span>
							<input
								v-model="actionForm.inquiry"
								data-testid="action-link-inquiry"
								type="text"
								placeholder="Inquiry document name"
							/>
						</label>
					</template>

					<template v-else-if="activeActionId === 'link_applicant'">
						<label class="action-field">
							<span>Student Applicant</span>
							<input
								v-model="actionForm.student_applicant"
								data-testid="action-link-applicant"
								type="text"
								placeholder="Student Applicant document name"
							/>
						</label>
					</template>

					<template v-else-if="activeActionId === 'resolve_identity_match'">
						<label class="action-field">
							<span>Match Status</span>
							<select v-model="actionForm.match_status" data-testid="action-match-status">
								<option v-for="status in matchStatuses" :key="status" :value="status">
									{{ status }}
								</option>
							</select>
						</label>
						<div class="action-form__grid">
							<label class="action-field">
								<span>Inquiry</span>
								<input v-model="actionForm.inquiry" type="text" placeholder="Optional Inquiry" />
							</label>
							<label class="action-field">
								<span>Student Applicant</span>
								<input
									v-model="actionForm.student_applicant"
									type="text"
									placeholder="Optional Student Applicant"
								/>
							</label>
							<label class="action-field">
								<span>Contact</span>
								<input v-model="actionForm.contact" type="text" placeholder="Optional Contact" />
							</label>
							<label class="action-field">
								<span>Guardian</span>
								<input v-model="actionForm.guardian" type="text" placeholder="Optional Guardian" />
							</label>
						</div>
					</template>

					<p v-if="actionError" data-testid="admissions-inbox-action-error" class="action-error">
						{{ actionError }}
					</p>
					<p
						v-if="actionSuccess"
						data-testid="admissions-inbox-action-success"
						class="action-success"
					>
						{{ actionSuccess }}
					</p>

					<div class="action-form__footer">
						<button
							type="submit"
							data-testid="action-submit"
							class="if-button if-button--primary"
							:disabled="actionSaving"
						>
							<FeatherIcon name="check" class="h-4 w-4" />
							<span>{{ actionSaving ? 'Saving' : activeActionSubmitLabel }}</span>
						</button>
					</div>
				</form>
			</div>
		</aside>
	</div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { FeatherIcon } from 'frappe-ui';

import {
	archiveInquiryFromInbox,
	assignAdmissionConversation,
	assignInquiryFromInbox,
	confirmAdmissionExternalIdentity,
	createInquiryFromAdmissionConversation,
	getAdmissionsInboxContext,
	inviteInquiryToApplyFromInbox,
	linkAdmissionConversation,
	logAdmissionMessage,
	markInquiryContactedFromInbox,
	qualifyInquiryFromInbox,
	recordAdmissionCrmActivity,
	updateAdmissionConversationStatus,
} from '@/lib/services/admissions/admissionsInboxService';
import { SIGNAL_ADMISSIONS_INBOX_INVALIDATE, uiSignals } from '@/lib/uiSignals';
import type {
	AdmissionCrmActivityType,
	AdmissionExternalIdentityMatchStatus,
	AdmissionsInboxContext,
	AdmissionsInboxQueue,
	AdmissionsInboxRow,
} from '@/types/contracts/admissions_inbox/get_admissions_inbox_context';

const DEFAULT_LIMIT = 40;
const SUPPORTED_ACTION_IDS = [
	'log_reply',
	'log_message',
	'record_activity',
	'assign_owner',
	'reassign_owner',
	'archive_conversation',
	'mark_spam',
	'create_inquiry',
	'link_inquiry',
	'link_applicant',
	'resolve_identity_match',
	'archive_inquiry',
	'mark_contacted',
	'qualify',
	'invite_to_apply',
] as const;

type SupportedActionId = (typeof SUPPORTED_ACTION_IDS)[number];

type ActionForm = {
	body: string;
	activity_type: AdmissionCrmActivityType;
	outcome: string;
	note: string;
	next_action_on: string;
	inquiry: string;
	student_applicant: string;
	contact: string;
	guardian: string;
	match_status: AdmissionExternalIdentityMatchStatus;
	assigned_to: string;
	assignment_lane: '' | 'Admission' | 'Staff';
	archive_reason: string;
	type_of_inquiry: string;
	inquiry_source: string;
	create_inquiry_message: string;
	invite_school: string;
	invite_organization: string;
};

type ActionState = {
	id: SupportedActionId;
	label: string;
	description: string;
	enabled: boolean;
	disabledReason: string;
};

const actionDefinitions: Record<
	SupportedActionId,
	{
		label: string;
		description: string;
		requiresConversation?: boolean;
		requiresExternalIdentity?: boolean;
		requiresInquiry?: boolean;
	}
> = {
	log_reply: {
		label: 'Log reply',
		description: 'Record a staff reply in the CRM conversation.',
	},
	log_message: {
		label: 'Log message',
		description: 'Create or update a CRM conversation with a manual message.',
	},
	record_activity: {
		label: 'Record activity',
		description: 'Add a structured CRM activity outcome.',
		requiresConversation: true,
	},
	assign_owner: {
		label: 'Assign owner',
		description: 'Set the admissions owner for this Inbox item.',
	},
	reassign_owner: {
		label: 'Reassign owner',
		description: 'Move this Inbox item to another admissions owner.',
	},
	archive_conversation: {
		label: 'Archive conversation',
		description: 'Close this CRM conversation and clear reply pressure.',
		requiresConversation: true,
	},
	mark_spam: {
		label: 'Mark spam',
		description: 'Remove this CRM conversation from active admissions queues.',
		requiresConversation: true,
	},
	create_inquiry: {
		label: 'Create Inquiry',
		description: 'Create a controlled Inquiry from this CRM conversation.',
		requiresConversation: true,
	},
	link_inquiry: {
		label: 'Link Inquiry',
		description: 'Attach this CRM conversation to an existing Inquiry.',
		requiresConversation: true,
	},
	link_applicant: {
		label: 'Link Applicant',
		description: 'Attach this CRM conversation to an existing Student Applicant.',
		requiresConversation: true,
	},
	resolve_identity_match: {
		label: 'Resolve identity',
		description: 'Confirm, reject, or update the external identity match status.',
		requiresExternalIdentity: true,
	},
	archive_inquiry: {
		label: 'Archive Inquiry',
		description: 'Archive the linked Inquiry through the approved workflow.',
		requiresInquiry: true,
	},
	mark_contacted: {
		label: 'Mark contacted',
		description: 'Move the linked Inquiry to contacted through the approved workflow.',
		requiresInquiry: true,
	},
	qualify: {
		label: 'Qualify',
		description: 'Move the linked Inquiry to qualified through the approved workflow.',
		requiresInquiry: true,
	},
	invite_to_apply: {
		label: 'Invite to apply',
		description: 'Create or open the applicant from the linked qualified Inquiry.',
		requiresInquiry: true,
	},
};

const activityTypes: AdmissionCrmActivityType[] = [
	'Call Attempt',
	'Reached',
	'No Answer',
	'Qualified',
	'Not Interested',
	'Booked Tour',
	'Attended Tour',
	'Follow-up Scheduled',
	'Archived',
	'Note',
];

const matchStatuses: AdmissionExternalIdentityMatchStatus[] = [
	'Confirmed',
	'Rejected',
	'Suggested',
	'Unmatched',
];
const assignmentLanes: ActionForm['assignment_lane'][] = ['', 'Admission', 'Staff'];
const inquiryTypes = [
	'Admission',
	'Current Family',
	'General Inquiry',
	'Partnership / Agent',
	'Other',
];
const inquirySources = [
	'Website',
	'WhatsApp',
	'Line',
	'Facebook',
	'Open Day',
	'Referral',
	'Agent',
	'Other',
];

const context = ref<AdmissionsInboxContext | null>(null);
const loading = ref(false);
const error = ref<string | null>(null);
const activeQueueId = ref('needs_reply');
const selectedRow = ref<AdmissionsInboxRow | null>(null);
const activeActionId = ref<SupportedActionId | ''>('');
const actionForm = ref<ActionForm>(createActionForm());
const actionSaving = ref(false);
const actionError = ref<string | null>(null);
const actionSuccess = ref<string | null>(null);

let refreshSequence = 0;
let disposeInboxInvalidate: (() => void) | null = null;

const queues = computed<AdmissionsInboxQueue[]>(() => context.value?.queues || []);
const activeQueue = computed<AdmissionsInboxQueue | null>(() => {
	return queues.value.find(queue => queue.id === activeQueueId.value) || queues.value[0] || null;
});
const activeRows = computed<AdmissionsInboxRow[]>(() => activeQueue.value?.rows || []);
const initialLoading = computed(() => loading.value && !context.value);
const totalVisibleRows = computed(() =>
	queues.value.reduce((total, queue) => total + queue.rows.length, 0)
);
const lastRefreshedLabel = computed(() => formatDateTime(context.value?.generated_at || null));
const selectedRowActionStates = computed<ActionState[]>(() =>
	selectedRow.value ? rowActionStates(selectedRow.value) : []
);
const unsupportedActionLabels = computed(() => {
	const row = selectedRow.value;
	if (!row) return [];
	return row.actions
		.filter(action => !isSupportedActionId(action.id))
		.map(action => actionLabel(action.id));
});
const activeActionSubmitLabel = computed(() => {
	if (!activeActionId.value) return 'Save';
	return actionDefinitions[activeActionId.value].label;
});

async function refreshInbox(reason: string) {
	const sequence = ++refreshSequence;
	loading.value = true;
	error.value = null;

	try {
		const response = await getAdmissionsInboxContext({ limit: DEFAULT_LIMIT });
		if (sequence !== refreshSequence) return;
		context.value = response;
		if (!response.queues.some(queue => queue.id === activeQueueId.value)) {
			activeQueueId.value = response.queues[0]?.id || 'needs_reply';
		}
	} catch (err) {
		if (sequence !== refreshSequence) return;
		error.value = errorMessage(err, reason);
	} finally {
		if (sequence === refreshSequence) {
			loading.value = false;
		}
	}
}

function errorMessage(err: unknown, reason: string) {
	const message = err instanceof Error ? err.message : String(err || '');
	const prefix = reason === 'retry' ? 'Retry failed' : 'Admissions Inbox could not load';
	return message ? `${prefix}: ${message}` : `${prefix}.`;
}

function selectQueue(queueId: string) {
	activeQueueId.value = queueId;
}

function createActionForm(row?: AdmissionsInboxRow): ActionForm {
	return {
		body: '',
		activity_type: 'Note',
		outcome: '',
		note: '',
		next_action_on: '',
		inquiry: String(row?.inquiry || ''),
		student_applicant: String(row?.student_applicant || ''),
		contact: '',
		guardian: '',
		match_status: 'Confirmed',
		assigned_to: String(row?.owner || ''),
		assignment_lane: '',
		archive_reason: '',
		type_of_inquiry: 'Admission',
		inquiry_source: defaultInquirySource(row),
		create_inquiry_message: String(row?.last_message_preview || ''),
		invite_school: String(row?.school || ''),
		invite_organization: String(row?.organization || ''),
	};
}

function hasRowActions(row: AdmissionsInboxRow) {
	return row.actions.length > 0;
}

function isSupportedActionId(actionId: string): actionId is SupportedActionId {
	return SUPPORTED_ACTION_IDS.includes(actionId as SupportedActionId);
}

function actionLabel(actionId: string) {
	if (isSupportedActionId(actionId)) return actionDefinitions[actionId].label;
	return actionId
		.split('_')
		.map(part => part.charAt(0).toUpperCase() + part.slice(1))
		.join(' ');
}

function rowActionStates(row: AdmissionsInboxRow): ActionState[] {
	return SUPPORTED_ACTION_IDS.map(actionId => {
		const serverAction = row.actions.find(action => action.id === actionId);
		if (!serverAction) return null;

		const definition = actionDefinitions[actionId];
		let enabled = Boolean(serverAction.enabled);
		let disabledReason = serverAction.disabled_reason || '';
		if (enabled && definition.requiresConversation && !row.conversation) {
			enabled = false;
			disabledReason =
				'This action requires an admissions CRM conversation. Open the source record or link one first.';
		}
		if (enabled && definition.requiresExternalIdentity && !row.external_identity) {
			enabled = false;
			disabledReason = 'This action requires an external identity from a CRM conversation.';
		}
		if (enabled && definition.requiresInquiry && !row.inquiry) {
			enabled = false;
			disabledReason =
				'This action requires a linked Inquiry. Create or link an Inquiry before continuing.';
		}

		return {
			id: actionId,
			label: definition.label,
			description: definition.description,
			enabled,
			disabledReason: disabledReason || 'The server did not allow this action.',
		};
	}).filter((action): action is ActionState => Boolean(action));
}

function openActionDrawer(row: AdmissionsInboxRow) {
	selectedRow.value = row;
	actionForm.value = createActionForm(row);
	actionError.value = null;
	actionSuccess.value = null;
	activeActionId.value = rowActionStates(row).find(action => action.enabled)?.id || '';
}

function closeActionDrawer() {
	selectedRow.value = null;
	activeActionId.value = '';
	actionError.value = null;
	actionSuccess.value = null;
	actionSaving.value = false;
}

function selectAction(actionId: SupportedActionId) {
	const state = selectedRowActionStates.value.find(action => action.id === actionId);
	if (!state?.enabled) return;
	activeActionId.value = actionId;
	actionError.value = null;
	actionSuccess.value = null;
}

function isLogAction(actionId: SupportedActionId | '') {
	return actionId === 'log_reply' || actionId === 'log_message';
}

function isAssignAction(actionId: SupportedActionId | '') {
	return actionId === 'assign_owner' || actionId === 'reassign_owner';
}

function isArchiveAction(actionId: SupportedActionId | '') {
	return (
		actionId === 'archive_conversation' ||
		actionId === 'mark_spam' ||
		actionId === 'archive_inquiry'
	);
}

function defaultInquirySource(row?: AdmissionsInboxRow) {
	const channel = String(row?.channel_type || '').trim();
	if (channel === 'WhatsApp') return 'WhatsApp';
	if (channel === 'Line') return 'Line';
	if (channel === 'Facebook Messenger' || channel === 'Instagram DM') return 'Facebook';
	return 'Other';
}

function countForQueue(queueId: string) {
	return queues.value.find(queue => queue.id === queueId)?.count || 0;
}

function sourceCount(key: string) {
	return Number(context.value?.sources?.[key] || 0);
}

function rowKindLabel(row: AdmissionsInboxRow) {
	if (row.kind === 'conversation') return 'CRM Conversation';
	if (row.kind === 'inquiry') return 'Inquiry';
	if (row.kind === 'student_applicant') return 'Applicant';
	return row.kind || 'Admissions';
}

function stageLabel(stage: string) {
	const normalized = String(stage || '').trim();
	if (normalized === 'pre_applicant') return 'Pre-applicant';
	if (normalized === 'student_applicant') return 'Applicant';
	if (!normalized) return 'Admissions';
	return normalized
		.split('_')
		.map(part => part.charAt(0).toUpperCase() + part.slice(1))
		.join(' ');
}

function rowToneClass(row: AdmissionsInboxRow) {
	if (row.needs_reply) return 'inbox-row-card--needs-reply';
	if (row.kind === 'student_applicant') return 'inbox-row-card--applicant';
	if (row.kind === 'inquiry') return 'inbox-row-card--inquiry';
	return 'inbox-row-card--neutral';
}

function rowMeta(row: AdmissionsInboxRow) {
	const items = [
		{ label: 'Owner', value: row.owner || 'Unassigned' },
		{ label: 'School', value: row.school || row.organization || '' },
		{ label: 'Channel', value: row.channel_type || row.channel_account || '' },
		{ label: 'SLA', value: row.sla_state || '' },
		{ label: 'Last activity', value: formatDateTime(row.last_activity_at || null) },
		{ label: 'Next action', value: formatDate(row.next_action_on || null) },
	];

	return items.filter(item => Boolean(item.value));
}

function safeOpenUrl(row: AdmissionsInboxRow) {
	const url = String(row.open_url || '').trim();
	if (!url || row.permissions?.can_open === false) return '';
	if (url.startsWith('/private/')) return '';
	return url;
}

function formatDateTime(value: string | null) {
	if (!value) return '';
	const parsed = new Date(value);
	if (Number.isNaN(parsed.getTime())) return value;
	return new Intl.DateTimeFormat(undefined, {
		month: 'short',
		day: 'numeric',
		hour: '2-digit',
		minute: '2-digit',
	}).format(parsed);
}

function formatDate(value: string | null) {
	if (!value) return '';
	const parsed = new Date(value);
	if (Number.isNaN(parsed.getTime())) return value;
	return new Intl.DateTimeFormat(undefined, {
		month: 'short',
		day: 'numeric',
	}).format(parsed);
}

function blankToNull(value: string) {
	const text = String(value || '').trim();
	return text || null;
}

function requireConversation(row: AdmissionsInboxRow) {
	const conversation = blankToNull(String(row.conversation || ''));
	if (!conversation) {
		actionError.value =
			'This action requires an admissions CRM conversation. Open the source record or link one first.';
		return null;
	}
	return conversation;
}

function requireExternalIdentity(row: AdmissionsInboxRow) {
	const externalIdentity = blankToNull(String(row.external_identity || ''));
	if (!externalIdentity) {
		actionError.value = 'This action requires an external identity from a CRM conversation.';
		return null;
	}
	return externalIdentity;
}

function requireInquiry(row: AdmissionsInboxRow) {
	const inquiry = blankToNull(String(row.inquiry || ''));
	if (!inquiry) {
		actionError.value =
			'This action requires a linked Inquiry. Create or link an Inquiry before continuing.';
		return null;
	}
	return inquiry;
}

async function submitActiveAction() {
	const row = selectedRow.value;
	const actionId = activeActionId.value;
	if (!row || !actionId || actionSaving.value) return;

	actionError.value = null;
	actionSuccess.value = null;
	actionSaving.value = true;

	try {
		if (isLogAction(actionId)) {
			await submitLogAction(row);
		} else if (actionId === 'record_activity') {
			await submitRecordActivity(row);
		} else if (isAssignAction(actionId)) {
			await submitAssignOwner(row);
		} else if (actionId === 'archive_conversation') {
			await submitConversationStatus(row, 'Archived');
		} else if (actionId === 'mark_spam') {
			await submitConversationStatus(row, 'Spam');
		} else if (actionId === 'create_inquiry') {
			await submitCreateInquiry(row);
		} else if (actionId === 'link_inquiry') {
			await submitLinkInquiry(row);
		} else if (actionId === 'link_applicant') {
			await submitLinkApplicant(row);
		} else if (actionId === 'resolve_identity_match') {
			await submitResolveIdentity(row);
		} else if (actionId === 'archive_inquiry') {
			await submitArchiveInquiry(row);
		} else if (actionId === 'mark_contacted') {
			await submitMarkInquiryContacted(row);
		} else if (actionId === 'qualify') {
			await submitQualifyInquiry(row);
		} else if (actionId === 'invite_to_apply') {
			await submitInviteInquiry(row);
		}

		if (!actionError.value) {
			actionSuccess.value = 'Saved. Refreshing queue.';
		}
	} catch (err) {
		actionError.value = err instanceof Error ? err.message : String(err || 'Action failed.');
	} finally {
		actionSaving.value = false;
	}
}

async function submitLogAction(row: AdmissionsInboxRow) {
	const body = blankToNull(actionForm.value.body);
	if (!body) {
		actionError.value = 'Message is required.';
		return;
	}

	await logAdmissionMessage({
		conversation: blankToNull(String(row.conversation || '')),
		inquiry: blankToNull(String(row.inquiry || '')),
		student_applicant: blankToNull(String(row.student_applicant || '')),
		external_identity: blankToNull(String(row.external_identity || '')),
		channel_account: blankToNull(String(row.channel_account || '')),
		organization: blankToNull(String(row.organization || '')),
		school: blankToNull(String(row.school || '')),
		assigned_to: blankToNull(String(row.owner || '')),
		direction: 'Outbound',
		message_type: 'Text',
		delivery_status: 'Logged',
		body,
	});
	actionForm.value.body = '';
}

async function submitRecordActivity(row: AdmissionsInboxRow) {
	const conversation = requireConversation(row);
	if (!conversation) return;

	await recordAdmissionCrmActivity({
		conversation,
		activity_type: actionForm.value.activity_type,
		outcome: blankToNull(actionForm.value.outcome),
		note: blankToNull(actionForm.value.note),
		next_action_on: blankToNull(actionForm.value.next_action_on),
	});
	actionForm.value.outcome = '';
	actionForm.value.note = '';
}

async function submitAssignOwner(row: AdmissionsInboxRow) {
	const assignedTo = blankToNull(actionForm.value.assigned_to);
	if (!assignedTo) {
		actionError.value = 'Assigned To is required.';
		return;
	}

	if (row.conversation && row.kind === 'conversation') {
		await assignAdmissionConversation({
			conversation: row.conversation,
			assigned_to: assignedTo,
		});
		return;
	}

	const inquiry = requireInquiry(row);
	if (!inquiry) return;
	await assignInquiryFromInbox({
		inquiry,
		assigned_to: assignedTo,
		assignment_lane: actionForm.value.assignment_lane || null,
	});
}

async function submitConversationStatus(row: AdmissionsInboxRow, status: 'Archived' | 'Spam') {
	const conversation = requireConversation(row);
	if (!conversation) return;
	const reason = blankToNull(actionForm.value.archive_reason);
	if (!reason) {
		actionError.value = 'Reason is required.';
		return;
	}

	await updateAdmissionConversationStatus({
		conversation,
		status,
		note: reason,
	});
}

async function submitCreateInquiry(row: AdmissionsInboxRow) {
	const conversation = requireConversation(row);
	if (!conversation) return;

	await createInquiryFromAdmissionConversation({
		conversation,
		type_of_inquiry: blankToNull(actionForm.value.type_of_inquiry),
		source: blankToNull(actionForm.value.inquiry_source),
		message: blankToNull(actionForm.value.create_inquiry_message),
	});
}

async function submitLinkInquiry(row: AdmissionsInboxRow) {
	const conversation = requireConversation(row);
	if (!conversation) return;
	const inquiry = blankToNull(actionForm.value.inquiry);
	if (!inquiry) {
		actionError.value = 'Inquiry is required.';
		return;
	}

	await linkAdmissionConversation({
		conversation,
		inquiry,
	});
}

async function submitLinkApplicant(row: AdmissionsInboxRow) {
	const conversation = requireConversation(row);
	if (!conversation) return;
	const studentApplicant = blankToNull(actionForm.value.student_applicant);
	if (!studentApplicant) {
		actionError.value = 'Student Applicant is required.';
		return;
	}

	await linkAdmissionConversation({
		conversation,
		student_applicant: studentApplicant,
	});
}

async function submitResolveIdentity(row: AdmissionsInboxRow) {
	const externalIdentity = requireExternalIdentity(row);
	if (!externalIdentity) return;

	await confirmAdmissionExternalIdentity({
		external_identity: externalIdentity,
		match_status: actionForm.value.match_status,
		contact: blankToNull(actionForm.value.contact),
		guardian: blankToNull(actionForm.value.guardian),
		inquiry: blankToNull(actionForm.value.inquiry),
		student_applicant: blankToNull(actionForm.value.student_applicant),
	});
}

async function submitArchiveInquiry(row: AdmissionsInboxRow) {
	const inquiry = requireInquiry(row);
	if (!inquiry) return;
	const reason = blankToNull(actionForm.value.archive_reason);
	if (!reason) {
		actionError.value = 'Reason is required.';
		return;
	}

	await archiveInquiryFromInbox({
		inquiry,
		reason,
	});
}

async function submitMarkInquiryContacted(row: AdmissionsInboxRow) {
	const inquiry = requireInquiry(row);
	if (!inquiry) return;

	await markInquiryContactedFromInbox({
		inquiry,
		complete_todo: 0,
	});
}

async function submitQualifyInquiry(row: AdmissionsInboxRow) {
	const inquiry = requireInquiry(row);
	if (!inquiry) return;

	await qualifyInquiryFromInbox({ inquiry });
}

async function submitInviteInquiry(row: AdmissionsInboxRow) {
	const inquiry = requireInquiry(row);
	if (!inquiry) return;
	const school = blankToNull(actionForm.value.invite_school);
	if (!school) {
		actionError.value = 'School is required.';
		return;
	}

	await inviteInquiryToApplyFromInbox({
		inquiry,
		school,
		organization: blankToNull(actionForm.value.invite_organization),
	});
}

function onInboxInvalidated() {
	refreshInbox('signal');
}

onMounted(() => {
	disposeInboxInvalidate = uiSignals.subscribe(
		SIGNAL_ADMISSIONS_INBOX_INVALIDATE,
		onInboxInvalidated
	);
	refreshInbox('mount');
});

onBeforeUnmount(() => {
	if (disposeInboxInvalidate) disposeInboxInvalidate();
});
</script>

<style scoped>
.admissions-inbox-page {
	--inbox-border: rgb(var(--sand-rgb) / 0.38);
	--inbox-muted: rgb(248 250 252);
	--inbox-card: rgb(255 255 255);
}

.inbox-summary {
	display: grid;
	grid-template-columns: repeat(4, minmax(0, 1fr));
	gap: 0.75rem;
}

.inbox-summary__tile {
	display: flex;
	min-width: 0;
	flex-direction: column;
	gap: 0.35rem;
	border: 1px solid var(--inbox-border);
	border-radius: 0.5rem;
	background: var(--inbox-card);
	padding: 0.9rem 1rem;
}

.inbox-summary__tile strong {
	color: rgb(var(--ink-rgb));
	font-size: 1.45rem;
	line-height: 1.2;
}

.admissions-inbox-layout {
	display: grid;
	grid-template-columns: minmax(14rem, 18rem) minmax(0, 1fr);
	gap: 1rem;
	align-items: start;
}

.queue-rail,
.queue-panel {
	border: 1px solid var(--inbox-border);
	border-radius: 0.625rem;
	background: var(--inbox-card);
}

.queue-rail {
	display: grid;
	gap: 0.25rem;
	padding: 0.5rem;
}

.queue-button {
	display: flex;
	min-width: 0;
	align-items: center;
	justify-content: space-between;
	gap: 0.75rem;
	border-radius: 0.5rem;
	padding: 0.65rem 0.75rem;
	color: rgb(var(--slate-rgb));
	text-align: left;
	transition:
		background 0.15s ease,
		color 0.15s ease;
}

.queue-button span {
	min-width: 0;
	overflow-wrap: anywhere;
	font-size: 0.875rem;
	font-weight: 650;
}

.queue-button strong {
	border-radius: 999px;
	background: rgb(241 245 249);
	padding: 0.15rem 0.5rem;
	font-size: 0.75rem;
	line-height: 1.4;
}

.queue-button:hover,
.queue-button--active {
	background: rgb(var(--sky-rgb) / 0.18);
	color: rgb(var(--canopy-rgb));
}

.queue-button--active strong {
	background: rgb(var(--canopy-rgb));
	color: white;
}

.queue-panel {
	min-width: 0;
	overflow: hidden;
}

.queue-panel__header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 1rem;
	border-bottom: 1px solid var(--inbox-border);
	padding: 1rem;
}

.queue-panel__count {
	border-radius: 999px;
	background: rgb(var(--flame-rgb) / 0.14);
	color: rgb(var(--flame-rgb));
	font-size: 0.82rem;
	font-weight: 750;
	padding: 0.25rem 0.65rem;
}

.queue-panel__empty,
.queue-panel__more {
	padding: 1.5rem 1rem;
}

.queue-rows {
	display: grid;
	gap: 0.75rem;
	padding: 1rem;
}

.inbox-row-card {
	min-width: 0;
	border: 1px solid rgb(226 232 240);
	border-left-width: 0.35rem;
	border-radius: 0.5rem;
	background: white;
	padding: 1rem;
}

.inbox-row-card--needs-reply {
	border-left-color: rgb(var(--flame-rgb));
}

.inbox-row-card--applicant {
	border-left-color: rgb(var(--jacaranda-rgb));
}

.inbox-row-card--inquiry {
	border-left-color: rgb(var(--canopy-rgb));
}

.inbox-row-card--neutral {
	border-left-color: rgb(var(--sky-rgb));
}

.inbox-row-card__header,
.inbox-row-card__footer {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: 0.85rem;
}

.inbox-row-card__title {
	min-width: 0;
}

.inbox-row-card__title h3,
.inbox-row-card__title p,
.inbox-row-card__preview,
.inbox-row-card__meta dd {
	overflow-wrap: anywhere;
}

.inbox-row-card__pills {
	display: flex;
	flex-wrap: wrap;
	justify-content: flex-end;
	gap: 0.35rem;
}

.inbox-pill {
	border-radius: 999px;
	border: 1px solid rgb(226 232 240);
	background: rgb(248 250 252);
	color: rgb(var(--slate-rgb));
	font-size: 0.72rem;
	font-weight: 700;
	line-height: 1.3;
	padding: 0.2rem 0.5rem;
	white-space: nowrap;
}

.inbox-pill--reply {
	border-color: rgb(var(--flame-rgb) / 0.35);
	background: rgb(var(--flame-rgb) / 0.1);
	color: rgb(var(--flame-rgb));
}

.inbox-pill--unread {
	border-color: rgb(var(--jacaranda-rgb) / 0.35);
	background: rgb(var(--jacaranda-rgb) / 0.1);
	color: rgb(var(--jacaranda-rgb));
}

.inbox-row-card__preview {
	margin-top: 0.75rem;
	border-radius: 0.45rem;
	background: var(--inbox-muted);
	color: rgb(var(--slate-rgb));
	font-size: 0.875rem;
	line-height: 1.45;
	padding: 0.65rem 0.75rem;
}

.inbox-row-card__meta {
	display: grid;
	grid-template-columns: repeat(3, minmax(0, 1fr));
	gap: 0.75rem;
	margin-top: 0.85rem;
}

.inbox-row-card__meta dt {
	color: rgb(var(--slate-rgb) / 0.68);
	font-size: 0.68rem;
	font-weight: 750;
	letter-spacing: 0;
	text-transform: uppercase;
}

.inbox-row-card__meta dd {
	color: rgb(var(--ink-rgb));
	font-size: 0.84rem;
	font-weight: 650;
	margin: 0.15rem 0 0;
}

.inbox-row-card__footer {
	margin-top: 1rem;
	align-items: center;
}

.inbox-row-card__footer-actions {
	display: flex;
	flex-wrap: wrap;
	gap: 0.5rem;
}

.action-drawer {
	position: fixed;
	inset-block: 0;
	inset-inline-end: 0;
	z-index: 40;
	display: flex;
	width: min(30rem, calc(100vw - 1rem));
	flex-direction: column;
	border-left: 1px solid var(--inbox-border);
	background: white;
	box-shadow: -18px 0 42px rgb(15 23 42 / 0.18);
}

.action-drawer__header {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: 1rem;
	border-bottom: 1px solid var(--inbox-border);
	padding: 1rem;
}

.action-drawer__body {
	display: grid;
	gap: 1rem;
	overflow-y: auto;
	padding: 1rem;
}

.action-choice-list {
	display: grid;
	gap: 0.5rem;
}

.action-choice {
	display: grid;
	gap: 0.2rem;
	border: 1px solid rgb(226 232 240);
	border-radius: 0.5rem;
	background: rgb(248 250 252);
	padding: 0.75rem;
	text-align: left;
	transition:
		background 0.15s ease,
		border-color 0.15s ease;
}

.action-choice span {
	color: rgb(var(--ink-rgb));
	font-size: 0.9rem;
	font-weight: 750;
	overflow-wrap: anywhere;
}

.action-choice small {
	color: rgb(var(--slate-rgb) / 0.72);
	font-size: 0.78rem;
	line-height: 1.35;
	overflow-wrap: anywhere;
}

.action-choice:hover:not(:disabled),
.action-choice--active {
	border-color: rgb(var(--canopy-rgb) / 0.55);
	background: rgb(var(--sky-rgb) / 0.16);
}

.action-choice:disabled {
	cursor: not-allowed;
	opacity: 0.72;
}

.action-drawer__note,
.action-drawer__empty,
.action-error,
.action-success {
	border-radius: 0.5rem;
	font-size: 0.84rem;
	line-height: 1.45;
	padding: 0.75rem;
}

.action-drawer__note,
.action-drawer__empty {
	background: rgb(248 250 252);
	color: rgb(var(--slate-rgb));
}

.action-form {
	display: grid;
	gap: 0.85rem;
}

.action-form__grid {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 0.75rem;
}

.action-field {
	display: grid;
	gap: 0.35rem;
}

.action-field span {
	color: rgb(var(--slate-rgb) / 0.76);
	font-size: 0.72rem;
	font-weight: 750;
	letter-spacing: 0;
	text-transform: uppercase;
}

.action-field input,
.action-field select,
.action-field textarea {
	min-width: 0;
	width: 100%;
	border: 1px solid rgb(203 213 225);
	border-radius: 0.5rem;
	background: white;
	color: rgb(var(--ink-rgb));
	font-size: 0.9rem;
	line-height: 1.4;
	padding: 0.6rem 0.7rem;
}

.action-field textarea {
	resize: vertical;
}

.action-error {
	border: 1px solid rgb(252 165 165);
	background: rgb(254 242 242);
	color: rgb(185 28 28);
}

.action-success {
	border: 1px solid rgb(var(--canopy-rgb) / 0.3);
	background: rgb(var(--canopy-rgb) / 0.1);
	color: rgb(var(--canopy-rgb));
}

.action-form__footer {
	display: flex;
	justify-content: flex-end;
}

@media (max-width: 980px) {
	.inbox-summary,
	.admissions-inbox-layout {
		grid-template-columns: 1fr;
	}

	.queue-rail {
		grid-template-columns: repeat(2, minmax(0, 1fr));
	}
}

@media (max-width: 640px) {
	.queue-rail,
	.inbox-row-card__meta {
		grid-template-columns: 1fr;
	}

	.inbox-row-card__header,
	.inbox-row-card__footer {
		flex-direction: column;
		align-items: stretch;
	}

	.inbox-row-card__pills {
		justify-content: flex-start;
	}

	.action-form__grid {
		grid-template-columns: 1fr;
	}
}
</style>
