<template>
	<div data-testid="guardian-communication-center" class="portal-page student-hub-page">
		<header class="student-hub-hero">
			<div class="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
				<div>
					<p class="type-overline text-ink/60">Guardian Portal</p>
					<h1 class="type-h1 text-ink">Communication Center</h1>
					<p class="type-body text-ink/70">
						See school, class, activity, pastoral, and cohort updates for your family in one place,
						then filter by child when needed.
					</p>
				</div>
				<div class="flex items-center gap-2">
					<RouterLink :to="{ name: 'guardian-home' }" class="if-action">Back to Home</RouterLink>
					<button type="button" class="if-action" :disabled="loading" @click="refreshFeed">
						Refresh
					</button>
				</div>
			</div>
		</header>

		<section class="student-hub-section student-hub-section--warm">
			<div class="grid gap-4 xl:grid-cols-[minmax(0,220px)_1fr_auto] xl:items-center">
				<label class="space-y-1">
					<span class="type-caption text-ink/60">Child filter</span>
					<select
						v-model="selectedStudent"
						class="w-full rounded-xl border border-line-soft bg-white px-3 py-2 type-body text-ink"
					>
						<option value="">All linked children</option>
						<option v-for="child in children" :key="child.student" :value="child.student">
							{{ child.full_name }}
						</option>
					</select>
				</label>

				<div class="flex flex-wrap gap-2">
					<button
						v-for="option in sourceOptions"
						:key="option.value"
						type="button"
						class="rounded-full border px-4 py-2 text-sm font-semibold transition"
						:class="
							activeSource === option.value
								? 'border-jacaranda bg-jacaranda/10 text-jacaranda'
								: 'border-line-soft bg-white text-ink/70 hover:border-jacaranda/30 hover:text-ink'
						"
						@click="selectSource(option.value)"
					>
						{{ option.label }}
					</button>
				</div>

				<div class="flex flex-wrap gap-2 xl:justify-end">
					<span class="chip">Total {{ totalCount }}</span>
					<span class="chip">Unread {{ unreadCount }}</span>
					<span v-for="chip in summaryChips" :key="chip.label" class="chip">
						{{ chip.label }} {{ chip.count }}
					</span>
				</div>
			</div>
		</section>

		<section
			v-if="errorMessage"
			class="student-hub-section border border-flame/30 bg-[var(--flame)]/5"
		>
			<p class="type-body-strong text-flame">Could not load communications.</p>
			<p class="mt-2 type-caption text-ink/70">{{ errorMessage }}</p>
		</section>

		<section v-else-if="loading && !items.length" class="student-hub-section">
			<p class="type-body text-ink/70">Loading guardian communications...</p>
		</section>

		<section v-else-if="!items.length" class="student-hub-empty">
			<p class="type-body text-ink/70">
				{{
					selectedStudent
						? 'No communications match this child filter right now.'
						: 'No communications match this view right now.'
				}}
			</p>
		</section>

		<section v-else class="space-y-4">
			<article
				v-for="item in items"
				:key="item.item_id"
				class="student-hub-section student-hub-section--warm"
			>
				<div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
					<div class="min-w-0">
						<div class="flex flex-wrap items-center gap-2">
							<p class="type-caption text-ink/60">{{ item.source_label }}</p>
							<span class="chip">{{ item.org_communication.communication_type }}</span>
							<span class="chip">{{ item.org_communication.priority }}</span>
							<span
								class="rounded-full px-3 py-1 text-xs font-semibold"
								:class="item.is_unread ? 'bg-flame/15 text-flame' : 'bg-leaf/15 text-canopy'"
							>
								{{ item.is_unread ? 'Unread' : 'Seen' }}
							</span>
						</div>

						<h2 class="mt-2 type-h3 text-ink">{{ item.org_communication.title }}</h2>
						<p class="mt-2 type-caption text-ink/60">{{ metaLine(item) }}</p>
						<p class="mt-3 type-body text-ink/80">{{ item.org_communication.snippet }}</p>

						<div class="mt-4 flex flex-wrap gap-2">
							<span
								v-for="child in item.matched_children"
								:key="`${item.item_id}-${child.student}`"
								class="chip"
							>
								{{ child.full_name }}
							</span>
						</div>
					</div>

					<div class="flex flex-wrap gap-2">
						<button type="button" class="if-action" @click="toggleOrgCommunication(item)">
							{{ expandedItemId === item.item_id ? 'Hide update' : 'Read update' }}
						</button>
					</div>
				</div>

				<p v-if="actionError" class="mt-4 type-caption text-flame">{{ actionError }}</p>

				<div
					v-if="hasVisibleInteractionActions(item.org_communication)"
					class="mt-4 flex flex-wrap items-center gap-3"
				>
					<InteractionEmojiChips
						v-if="canReact(item.org_communication)"
						:interaction="interactionFor(item.org_communication.name)"
						:readonly="false"
						:onReact="code => reactToCommunication(item.org_communication, code)"
					/>
					<button
						v-if="canComment(item.org_communication)"
						type="button"
						class="if-action"
						@click="openThread(item)"
					>
						{{ commentUiFor(item.org_communication).actionLabel }}
						({{ interactionFor(item.org_communication.name).comments_total || 0 }})
					</button>
				</div>

				<div
					v-if="expandedItemId === item.item_id"
					class="mt-5 student-hub-card student-hub-card--warm"
				>
					<p v-if="detailLoading[item.org_communication.name]" class="type-body text-ink/70">
						Loading full update...
					</p>
					<p v-else-if="detailError[item.org_communication.name]" class="type-body text-flame">
						{{ detailError[item.org_communication.name] }}
					</p>
					<div v-else-if="communicationDetail(item.org_communication.name)">
						<div
							class="prose prose-slate max-w-none"
							v-html="communicationDetail(item.org_communication.name)?.message_html || ''"
						></div>

						<div
							v-if="communicationDetail(item.org_communication.name)?.attachments?.length"
							class="mt-5 space-y-2"
						>
							<p class="type-body-strong text-ink">Attachments</p>
							<div class="flex flex-wrap gap-2">
								<a
									v-for="attachment in communicationDetail(item.org_communication.name)
										?.attachments || []"
									:key="attachment.row_name"
									:href="attachment.preview_url || attachment.open_url"
									target="_blank"
									rel="noreferrer"
									class="inline-flex items-center rounded-full border border-line-soft bg-white px-3 py-1 text-xs font-medium text-ink transition hover:border-jacaranda/40 hover:bg-jacaranda/5"
								>
									{{ attachment.title || attachment.file_name || attachment.row_name }}
								</a>
							</div>
						</div>
					</div>
				</div>
			</article>

			<div v-if="hasMore" class="flex justify-center">
				<button type="button" class="if-action" :disabled="loadingMore" @click="loadMore">
					{{ loadingMore ? 'Loading…' : 'Load more' }}
				</button>
			</div>
		</section>

		<CommentThreadDrawer
			:open="threadOpen"
			:title="threadTitle"
			:rows="threadRows"
			:loading="threadLoading"
			:comment="commentValue"
			:submit-label="activeCommentUi.submitLabel"
			:submit-loading="commentSubmitting"
			:submit-disabled="commentSubmitting || !commentValue.trim()"
			:placeholder="activeCommentUi.placeholder"
			:empty-message="activeCommentUi.emptyMessage"
			@close="closeThread"
			@submit="submitComment"
			@update:comment="onCommentUpdate"
		/>
	</div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { toast } from 'frappe-ui';
import { RouterLink } from 'vue-router';

import CommentThreadDrawer from '@/components/CommentThreadDrawer.vue';
import InteractionEmojiChips from '@/components/InteractionEmojiChips.vue';
import { formatLocalizedDateTime } from '@/lib/datetime';
import { createCommunicationInteractionService } from '@/lib/services/communicationInteraction/communicationInteractionService';
import { getGuardianCommunicationCenter } from '@/lib/services/guardianCommunication/guardianCommunicationService';
import { createOrgCommunicationArchiveService } from '@/lib/services/orgCommunicationArchive/orgCommunicationArchiveService';
import type { Response as OrgCommunicationDetailResponse } from '@/types/contracts/org_communication_archive/get_org_communication_item';
import type {
	GuardianCommunicationCenterItem,
	GuardianCommunicationSource,
	Response as GuardianCommunicationCenterResponse,
} from '@/types/contracts/guardian/get_guardian_communication_center';
import type { ReactionCode } from '@/types/interactions';
import type {
	InteractionSummary,
	InteractionSummaryMap,
	InteractionThreadRow,
} from '@/types/morning_brief';
import {
	getAudienceInteractionCapabilities,
	getInteractionCommentUi,
	ORG_COMMUNICATION_VIEWERS,
} from '@/utils/orgCommunication';

type SourceFilter = 'all' | GuardianCommunicationSource;

const interactionService = createCommunicationInteractionService();
const archiveService = createOrgCommunicationArchiveService();

const sourceOptions: Array<{ value: SourceFilter; label: string }> = [
	{ value: 'all', label: 'All' },
	{ value: 'course', label: 'Classes' },
	{ value: 'activity', label: 'Activities' },
	{ value: 'school', label: 'School' },
	{ value: 'pastoral', label: 'Pastoral' },
	{ value: 'cohort', label: 'Cohort' },
];

const snapshot = ref<GuardianCommunicationCenterResponse | null>(null);
const items = ref<GuardianCommunicationCenterItem[]>([]);
const totalCount = ref(0);
const unreadCount = ref(0);
const hasMore = ref(false);
const loading = ref(false);
const loadingMore = ref(false);
const errorMessage = ref('');
const actionError = ref('');
const summaryCounts = ref<Record<string, number>>({});
const expandedItemId = ref('');
const summaryMap = ref<InteractionSummaryMap>({});
const detailMap = ref<Record<string, OrgCommunicationDetailResponse | null>>({});
const detailLoading = ref<Record<string, boolean>>({});
const detailError = ref<Record<string, string>>({});
const readMarking = ref<Record<string, boolean>>({});
const selectedStudent = ref('');
const activeSource = ref<SourceFilter>('all');
const threadOpen = ref(false);
const threadLoading = ref(false);
const commentSubmitting = ref(false);
const threadRows = ref<InteractionThreadRow[]>([]);
const commentValue = ref('');
const selectedCommunication = ref<GuardianCommunicationCenterItem | null>(null);

const children = computed(() => snapshot.value?.family.children ?? []);

const summaryChips = computed(() =>
	activeSource.value !== 'all'
		? []
		: sourceOptions
				.filter(option => option.value !== 'all')
				.map(option => ({
					label: option.label,
					count: summaryCounts.value[option.value] || 0,
				}))
				.filter(chip => chip.count > 0)
);

function emptySummary(): InteractionSummary {
	return {
		counts: {},
		reaction_counts: {},
		reactions_total: 0,
		comments_total: 0,
		self: null,
	};
}

function interactionFor(commName: string): InteractionSummary {
	return summaryMap.value[commName] || emptySummary();
}

function getInteractionCapabilities(
	item:
		| { interaction_mode?: string | null; allow_public_thread?: 0 | 1 | boolean | string | null }
		| null
		| undefined
) {
	return getAudienceInteractionCapabilities(item, {
		viewer: ORG_COMMUNICATION_VIEWERS.RECIPIENT,
	});
}

function canReact(
	item:
		| { interaction_mode?: string | null; allow_public_thread?: 0 | 1 | boolean | string | null }
		| null
		| undefined
) {
	return getInteractionCapabilities(item).canReact;
}

function canComment(
	item:
		| { interaction_mode?: string | null; allow_public_thread?: 0 | 1 | boolean | string | null }
		| null
		| undefined
) {
	return getInteractionCapabilities(item).canComment;
}

function hasVisibleInteractionActions(
	item:
		| { interaction_mode?: string | null; allow_public_thread?: 0 | 1 | boolean | string | null }
		| null
		| undefined
) {
	return getInteractionCapabilities(item).hasVisibleActions;
}

function commentUiFor(
	item:
		| { interaction_mode?: string | null; allow_public_thread?: 0 | 1 | boolean | string | null }
		| null
		| undefined
) {
	return getInteractionCommentUi(getInteractionCapabilities(item).commentMode);
}

const activeCommentUi = computed(() =>
	commentUiFor(selectedCommunication.value?.org_communication)
);

const threadTitle = computed(() =>
	selectedCommunication.value
		? `${activeCommentUi.value.titleLabel} · ${selectedCommunication.value.org_communication.title}`
		: activeCommentUi.value.titleLabel
);

function childSummary(item: GuardianCommunicationCenterItem): string {
	const names = item.matched_children.map(child => child.full_name).filter(Boolean);
	if (names.length <= 2) {
		return names.join(', ');
	}
	return `${names.slice(0, 2).join(', ')} +${names.length - 2} more`;
}

function metaLine(item: GuardianCommunicationCenterItem) {
	const parts = [
		childSummary(item),
		item.context_label || '',
		item.sort_at ? formatLocalizedDateTime(item.sort_at, { fallback: item.sort_at }) : '',
	].filter(Boolean);
	return parts.join(' · ');
}

function communicationDetail(name: string) {
	return detailMap.value[name] || null;
}

async function loadSummaries() {
	const names = items.value.map(item => item.org_communication.name).filter(Boolean);
	if (!names.length) {
		summaryMap.value = {};
		return;
	}
	summaryMap.value = await interactionService.getOrgCommInteractionSummary({
		comm_names: names,
	});
}

async function loadFeed(reset = true) {
	if (reset) {
		loading.value = true;
		items.value = [];
		expandedItemId.value = '';
	} else {
		loadingMore.value = true;
	}
	errorMessage.value = '';
	actionError.value = '';
	try {
		const response = await getGuardianCommunicationCenter({
			source: activeSource.value,
			student: selectedStudent.value || undefined,
			start: reset ? 0 : items.value.length,
			page_length: 24,
		});
		snapshot.value = response;
		summaryCounts.value = response.summary.source_counts || {};
		totalCount.value = response.total_count || 0;
		unreadCount.value = response.summary.unread_items || 0;
		hasMore.value = Boolean(response.has_more);
		items.value = reset ? response.items || [] : [...items.value, ...(response.items || [])];
		await loadSummaries();
	} catch (error) {
		const message = error instanceof Error ? error.message : String(error || '');
		errorMessage.value = message || 'Could not load communications.';
	} finally {
		loading.value = false;
		loadingMore.value = false;
	}
}

async function refreshFeed() {
	await loadFeed(true);
}

async function loadMore() {
	await loadFeed(false);
}

function selectSource(source: SourceFilter) {
	activeSource.value = source;
}

async function loadCommunicationDetail(name: string) {
	if (detailMap.value[name] || detailLoading.value[name]) {
		return;
	}
	detailLoading.value[name] = true;
	detailError.value[name] = '';
	try {
		detailMap.value[name] = await archiveService.getOrgCommunicationItem({ name });
	} catch (error) {
		const message = error instanceof Error ? error.message : String(error || '');
		detailError.value[name] = message || 'Could not load this update.';
	} finally {
		detailLoading.value[name] = false;
	}
}

async function markCommunicationRead(item: GuardianCommunicationCenterItem) {
	const commName = item.org_communication.name;
	if (!item.is_unread || readMarking.value[commName]) {
		return;
	}
	readMarking.value[commName] = true;
	try {
		await interactionService.markOrgCommunicationRead({ org_communication: commName });
		item.is_unread = false;
		unreadCount.value = Math.max(0, unreadCount.value - 1);
	} catch (error) {
		const message = error instanceof Error ? error.message : String(error || '');
		toast.error(message || 'Could not mark this update as read.');
	} finally {
		readMarking.value[commName] = false;
	}
}

async function toggleOrgCommunication(item: GuardianCommunicationCenterItem) {
	actionError.value = '';
	if (expandedItemId.value === item.item_id) {
		expandedItemId.value = '';
		return;
	}
	expandedItemId.value = item.item_id;
	await loadCommunicationDetail(item.org_communication.name);
	await markCommunicationRead(item);
}

async function reactToCommunication(
	comm: {
		name: string;
		interaction_mode?: string | null;
		allow_public_thread?: 0 | 1 | boolean | string | null;
	},
	code: ReactionCode
) {
	actionError.value = '';
	if (!canReact(comm)) {
		actionError.value = 'Reactions are not enabled for this update.';
		return;
	}
	try {
		await interactionService.reactToOrgCommunication({
			org_communication: comm.name,
			reaction_code: code,
			surface: 'Guardian Portal',
		});
		await loadSummaries();
	} catch (error) {
		const message = error instanceof Error ? error.message : String(error || '');
		actionError.value = message || 'Could not record reaction.';
	}
}

async function openThread(item: GuardianCommunicationCenterItem) {
	actionError.value = '';
	if (!canComment(item.org_communication)) {
		actionError.value = commentUiFor(item.org_communication).unavailableMessage;
		return;
	}
	selectedCommunication.value = item;
	threadOpen.value = true;
	commentValue.value = '';
	threadRows.value = [];
	threadLoading.value = true;
	try {
		threadRows.value = await interactionService.getCommunicationThread({
			org_communication: item.org_communication.name,
			limit_start: 0,
			limit: 200,
		});
	} catch (error) {
		const message = error instanceof Error ? error.message : String(error || '');
		actionError.value = message || commentUiFor(item.org_communication).loadErrorMessage;
	} finally {
		threadLoading.value = false;
	}
}

function closeThread() {
	threadOpen.value = false;
	selectedCommunication.value = null;
	commentValue.value = '';
	threadRows.value = [];
}

function onCommentUpdate(value: string) {
	commentValue.value = value;
}

async function submitComment() {
	actionError.value = '';
	const comm = selectedCommunication.value?.org_communication;
	if (!comm) {
		actionError.value = 'Select an update first.';
		return;
	}
	if (!canComment(comm)) {
		actionError.value = commentUiFor(comm).unavailableMessage;
		return;
	}
	const note = commentValue.value.trim();
	if (!note) {
		actionError.value = commentUiFor(comm).requiredMessage;
		return;
	}
	commentSubmitting.value = true;
	try {
		await interactionService.postOrgCommunicationComment({
			org_communication: comm.name,
			note,
			surface: 'Guardian Portal',
		});
		commentValue.value = '';
		threadRows.value = await interactionService.getCommunicationThread({
			org_communication: comm.name,
			limit_start: 0,
			limit: 200,
		});
		await loadSummaries();
		toast.success(commentUiFor(comm).postSuccessMessage);
	} catch (error) {
		const message = error instanceof Error ? error.message : String(error || '');
		actionError.value = message || commentUiFor(comm).postErrorMessage;
	} finally {
		commentSubmitting.value = false;
	}
}

watch([selectedStudent, activeSource], () => {
	void loadFeed(true);
});

onMounted(() => {
	void loadFeed(true);
});
</script>
