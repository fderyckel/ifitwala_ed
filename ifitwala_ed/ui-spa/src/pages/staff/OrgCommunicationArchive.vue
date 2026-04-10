<!-- ifitwala_ed/ui-spa/src/pages/staff/OrgCommunicationArchive.vue -->
<template>
	<div class="staff-shell min-w-0 space-y-6">
		<!-- Header -->
		<header class="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
			<div>
				<h1 class="type-h1">Announcement Archive</h1>
				<p class="type-meta text-slate-token/70">
					All communications visible to you across your organisation
				</p>
			</div>

			<!-- Date Range Toggles -->
			<DateRangePills v-model="filters.date_range" :items="DATE_RANGES" />
		</header>

		<!-- Filters Bar -->
		<FiltersBar class="analytics-filters">
			<!-- Organization -->
			<div v-if="organizationOptions.length > 0" class="flex flex-col gap-1">
				<label class="type-label">Organization</label>
				<FormControl
					type="select"
					:options="organizationOptions"
					v-model="filters.organization"
					class="w-44"
				/>
			</div>

			<!-- School -->
			<div v-if="schoolOptions.length > 0" class="flex flex-col gap-1">
				<label class="type-label">School</label>
				<FormControl
					type="select"
					:options="schoolOptions"
					v-model="filters.school"
					class="w-44"
				/>
			</div>

			<!-- Communication Type -->
			<div class="flex flex-col gap-1">
				<label class="type-label">Communication Type</label>
				<FormControl
					type="select"
					:options="communicationTypeOptions"
					v-model="filters.communication_type"
					class="w-44"
				/>
			</div>

			<!-- Student Group -->
			<div v-if="studentGroupOptions.length > 1" class="flex flex-col gap-1">
				<label class="type-label">Student Group</label>
				<FormControl
					type="select"
					:options="studentGroupOptions"
					v-model="filters.student_group"
					class="w-44"
				/>
			</div>

			<!-- Team -->
			<div v-if="hasTeamFilter" class="flex flex-col gap-1">
				<label class="type-label">Team</label>
				<FormControl type="select" :options="teamOptions" v-model="filters.team" class="w-44" />
			</div>

			<!-- With comments -->
			<div class="flex flex-col gap-1">
				<label class="type-label">Interactions</label>
				<label class="flex items-center gap-2 cursor-pointer text-sm text-ink select-none h-9">
					<input
						type="checkbox"
						v-model="filters.only_with_interactions"
						class="rounded border-slate-300 text-jacaranda"
					/>
					<span class="inline-flex items-center gap-1.5">
						<span>With comments</span>
						<FeatherIcon
							name="info"
							class="h-4 w-4 text-slate-token/60 hover:text-slate-token/80"
							tabindex="0"
							title="Shows only announcements that have at least one visible comment."
						/>
					</span>
				</label>
			</div>
		</FiltersBar>

		<!-- Main Content Grid -->
		<div class="org-archive__grid grid grid-cols-1 gap-6 min-h-0">
			<!-- LEFT LIST -->
			<div
				class="org-archive__list flex flex-col min-h-0 h-full bg-surface-glass rounded-2xl border border-line-soft shadow-soft overflow-hidden"
			>
				<div
					class="custom-scrollbar flex-1 overflow-y-auto p-4 space-y-2 bg-sand/20"
					@scroll.passive="onFeedScroll"
				>
					<div
						v-if="feedLoading && !feedItems.length"
						class="py-12 text-center text-slate-token/60"
					>
						<LoadingIndicator />
					</div>

					<div v-else-if="!feedItems.length" class="py-12 text-center">
						<p class="type-h3 text-slate-token/40">No announcements found</p>
						<p class="text-sm text-slate-token/60 mt-1">Try adjusting your filters</p>
					</div>

					<div
						v-for="item in feedItems"
						:key="item.name"
						@click="selectItem(item)"
						class="group relative flex gap-3 px-4 py-3 rounded-lg cursor-pointer transition-all border border-transparent hover:border-line-soft hover:bg-surface-soft hover:shadow-sm"
						:class="
							selectedComm?.name === item.name ? 'bg-surface-soft ring-1 ring-jacaranda/40' : ''
						"
					>
						<!-- Priority Indicator -->
						<div
							class="absolute left-0 top-3 bottom-3 w-1 rounded-r-full"
							:class="getPriorityClass(item.priority)"
						></div>

						<div class="flex-1 pl-3 min-w-0">
							<div class="flex items-start justify-between gap-2">
								<h3
									class="text-sm font-semibold text-ink line-clamp-1 group-hover:text-jacaranda transition-colors"
								>
									{{ item.title }}
								</h3>
								<span
									class="shrink-0 text-[10px] font-medium uppercase tracking-wider text-slate-token/50 bg-slate-100 px-1.5 py-0.5 rounded"
								>
									{{ item.status }}
								</span>
							</div>

							<div class="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-token/60">
								<span class="inline-flex items-center gap-1">
									<FeatherIcon name="calendar" class="h-3 w-3" />
									{{ formatDate(item.publish_from) }}
								</span>
								<span>•</span>
								<span class="bg-slate-100 px-1.5 py-0.5 rounded text-slate-token/70">
									{{ item.communication_type }}
								</span>
								<span
									v-if="item.portal_surface !== 'Everywhere'"
									class="bg-orange-50 text-orange-600 px-1.5 py-0.5 rounded"
								>
									{{ item.portal_surface }}
								</span>
							</div>

							<p class="mt-2 text-xs text-slate-token/80 line-clamp-2 leading-relaxed">
								{{ item.snippet }}
							</p>

							<div class="mt-3 flex items-center gap-4">
								<div class="flex items-center gap-1.5 text-xs text-slate-token/60">
									<FeatherIcon name="users" class="h-3 w-3" />
									<span class="truncate max-w-[150px]">{{ item.audience_label }}</span>
								</div>

								<!-- Interaction Summary -->
								<div class="flex items-center gap-3 ml-auto">
									<div
										v-if="getInteractionFor(item).self"
										class="text-xs text-jacaranda font-medium flex items-center gap-1"
									>
										<FeatherIcon name="check-circle" class="h-3 w-3" />
										You: {{ getInteractionFor(item).self?.intent_type || 'Responded' }}
									</div>
									<div
										class="flex items-center gap-1 text-xs text-slate-token/50 bg-slate-50 px-2 py-1 rounded"
									>
										<span>👍 {{ getInteractionStats(item).reactions_total }}</span>
										<span class="border-l border-slate-200 h-3 mx-1"></span>
										<span
											:title="
												getInteractionStats(item).comments_total > 0
													? 'Has comments'
													: 'No comments'
											"
										>
											💬 {{ getInteractionStats(item).comments_total }}
										</span>
									</div>
								</div>
							</div>
						</div>
					</div>

					<div
						v-if="feedLoading && feedItems.length"
						class="flex items-center justify-center py-3 text-slate-token/60"
					>
						<LoadingIndicator />
					</div>
				</div>
			</div>

			<!-- RIGHT DETAIL -->
			<div
				class="org-archive__detail min-h-0 h-full bg-surface-glass rounded-2xl border border-line-soft shadow-soft overflow-hidden flex flex-col relative"
			>
				<div
					v-if="!selectedComm"
					class="flex flex-col items-center justify-center h-full text-center p-8 text-slate-token/40"
				>
					<FeatherIcon name="inbox" class="h-10 w-10 mb-3 opacity-50" />
					<p class="type-h3">Select an announcement</p>
					<p class="text-sm mt-1">Click on an item from the list to view details</p>
				</div>

				<div v-else class="flex flex-col h-full">
					<!-- Detail Header -->
					<div class="p-6 border-b border-line-soft bg-surface-soft/70">
						<div class="flex flex-col gap-4">
							<div class="flex items-start justify-between gap-4">
								<div class="flex-1 min-w-0">
									<div class="flex items-center gap-2 mb-2">
										<Badge :color="getPriorityColor(selectedComm.priority)" size="sm">
											{{ selectedComm.priority }}
										</Badge>
										<span class="text-xs text-slate-token/50">•</span>
										<span class="text-xs font-medium text-slate-token/70">
											{{ selectedComm.communication_type }}
										</span>
									</div>
									<h2 class="text-xl font-bold text-ink leading-tight">
										{{ selectedComm.title }}
									</h2>
								</div>
							</div>
						</div>

						<div class="mt-4 flex flex-wrap gap-x-6 gap-y-2 text-sm text-slate-token/70">
							<div class="flex items-center gap-2">
								<FeatherIcon name="calendar" class="h-4 w-4 text-slate-token/50" />
								<span>{{ formatDate(selectedComm.publish_from, 'DD MMMM YYYY') }}</span>
								<span v-if="selectedComm.publish_to" class="text-slate-token/40"
									>→ {{ formatDate(selectedComm.publish_to, 'DD MMM') }}</span
								>
							</div>
							<div class="flex items-center gap-2">
								<FeatherIcon name="users" class="h-4 w-4 text-slate-token/50" />
								<span class="font-medium text-slate-token/70">{{
									selectedComm.audience_label
								}}</span>
							</div>
						</div>
					</div>

					<!-- Content -->
					<div class="flex-1 overflow-y-auto p-6 text-sm text-ink leading-relaxed">
						<div
							class="prose prose-slate max-w-none bg-white/80 rounded-2xl border border-line-soft shadow-soft p-6"
						>
							<div v-if="fullContentLoading" class="py-10 text-center"><LoadingIndicator /></div>
							<div
								v-else-if="detailLoadError"
								class="not-prose rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
							>
								<p class="font-medium">Unable to load the full announcement.</p>
								<p class="mt-1 text-amber-800/80">{{ detailLoadError }}</p>
								<Button
									variant="subtle"
									class="mt-3"
									@click="selectedComm && selectItem(selectedComm)"
								>
									Retry
								</Button>
							</div>
							<div
								v-else-if="detailMessageHtml"
								v-html="detailMessageHtml"
								@click="onDetailContentClick"
							></div>
							<p v-else-if="detailSnippetFallback" class="whitespace-pre-line text-slate-token/80">
								{{ detailSnippetFallback }}
							</p>
							<div v-else class="text-slate-token/60">
								No full announcement content is available for this item.
							</div>
						</div>

						<div
							v-if="detailAttachments.length"
							class="mt-4 rounded-2xl border border-line-soft bg-white/80 p-5 shadow-soft"
						>
							<div class="flex items-center gap-2">
								<FeatherIcon name="paperclip" class="h-4 w-4 text-slate-token/60" />
								<h3 class="text-sm font-semibold text-ink">Attachments</h3>
							</div>
							<div class="mt-4 space-y-3">
								<a
									v-for="attachment in detailAttachments"
									:key="attachment.row_name"
									:href="attachment.open_url || attachment.external_url || '#'"
									target="_blank"
									rel="noopener noreferrer"
									class="flex items-center justify-between gap-3 rounded-xl border border-line-soft bg-surface-soft px-4 py-3 transition hover:border-jacaranda/40 hover:bg-white"
								>
									<div class="min-w-0">
										<p class="truncate text-sm font-medium text-ink">
											{{ attachment.title }}
										</p>
										<p class="mt-1 truncate text-xs text-slate-token/60">
											{{ formatAttachmentMeta(attachment) }}
										</p>
									</div>
									<FeatherIcon name="external-link" class="h-4 w-4 shrink-0 text-slate-token/50" />
								</a>
							</div>
						</div>
					</div>

					<!-- Interactions Footer -->
					<div class="p-4 border-t border-line-soft bg-surface-soft/80 z-10 sticky bottom-0">
						<div class="flex items-center justify-between gap-4">
							<InteractionEmojiChips
								v-if="selectedComm"
								:interaction="getInteractionFor(selectedComm)"
								:readonly="!canInteract(selectedComm)"
								:onReact="code => reactTo(selectedComm, code)"
							/>

							<div class="flex items-center gap-3 ml-auto">
								<Button
									variant="subtle"
									color="gray"
									class="gap-2 whitespace-nowrap"
									@click="openThread(selectedComm)"
									:disabled="!canInteract(selectedComm)"
								>
									<FeatherIcon name="message-square" class="h-4 w-4 shrink-0" />

									<span class="inline-flex items-center gap-2 whitespace-nowrap">
										<span>Comments</span>

										<span
											v-if="selectedStats"
											class="text-xs font-semibold tabular-nums"
											:title="selectedStats.comments_total > 0 ? 'Has comments' : 'No comments'"
										>
											{{ selectedStats.comments_total }}
										</span>
									</span>
								</Button>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>

		<CommentThreadDrawer
			:open="showThreadDrawer"
			title="Comments"
			:rows="threadRows"
			:loading="threadLoading"
			v-model:comment="newComment"
			:submit-loading="interactionActionLoading"
			:format-timestamp="value => formatDate(value, 'DD MMM HH:mm')"
			@close="showThreadDrawer = false"
			@submit="submitComment"
		/>
	</div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { Badge, Button, FeatherIcon, FormControl, LoadingIndicator, toast } from 'frappe-ui';
import { useOverlayStack } from '@/composables/useOverlayStack';
import { formatLocalizedDate, formatLocalizedDateTime } from '@/lib/datetime';
import { createOrgCommunicationArchiveService } from '@/lib/services/orgCommunicationArchive/orgCommunicationArchiveService';
import { createCommunicationInteractionService } from '@/lib/services/communicationInteraction/communicationInteractionService';
import { SIGNAL_ORG_COMMUNICATION_INVALIDATE, uiSignals } from '@/lib/uiSignals';
import {
	COMMUNICATION_TYPES,
	type ArchiveFilters,
	type OrgCommunicationListItem,
} from '@/types/orgCommunication';
import { type InteractionSummary, type InteractionThreadRow } from '@/types/morning_brief';
import {
	extractPolicyInformLinkFromClickEvent,
	type PolicyInformLinkPayload,
} from '@/utils/policyInformLink';
import type { ReactionCode } from '@/types/interactions';
import type { OrgCommunicationAttachmentRow } from '@/types/contracts/org_communication_attachments/shared';
import type { Response as OrgCommunicationItemResponse } from '@/types/contracts/org_communication_archive/get_org_communication_item';
import FiltersBar from '@/components/filters/FiltersBar.vue';
import DateRangePills from '@/components/filters/DateRangePills.vue';
import CommentThreadDrawer from '@/components/CommentThreadDrawer.vue';
import InteractionEmojiChips from '@/components/InteractionEmojiChips.vue';
import { getInteractionStats as buildInteractionStats } from '@/utils/interactionStats';

const PAGE_LENGTH = 10;
const FEED_THROTTLE_MS = 500;
const FEED_SCROLL_THRESHOLD_PX = 180;

const DATE_RANGES = [
	{ label: 'Last 7 Days', value: '7d' },
	{ label: 'Last 30 Days', value: '30d' },
	{ label: 'Last 90 Days', value: '90d' },
	{ label: 'YTD', value: 'year' },
	{ label: 'All Time', value: 'all' },
] as const;

const archiveService = createOrgCommunicationArchiveService();
const interactionService = createCommunicationInteractionService();
const overlay = useOverlayStack();

const filters = ref<ArchiveFilters>({
	search_text: '',
	status: 'PublishedOrArchived',
	priority: 'All',
	portal_surface: 'All',
	communication_type: 'All',
	date_range: '90d',
	only_with_interactions: false,
	team: null,
	student_group: null,
	school: null,
	organization: null,
});

const selectedComm = ref<OrgCommunicationListItem | null>(null);
const showThreadDrawer = ref(false);
const newComment = ref('');
const initialized = ref(false);

const start = ref(0);
const feedItems = ref<OrgCommunicationListItem[]>([]);
const hasMore = ref(false);
const interactionSummaries = ref<Record<string, InteractionSummary>>({});
const fullContent = ref<OrgCommunicationItemResponse | null>(null);
const threadRows = ref<InteractionThreadRow[]>([]);
const detailLoadError = ref<string | null>(null);

const contextLoading = ref(false);
const feedLoading = ref(false);
const fullContentLoading = ref(false);
const threadLoading = ref(false);
const interactionActionLoading = ref(false);

const selectedStats = computed(() => {
	if (!selectedComm.value) return null;
	return buildInteractionStats(getInteractionFor(selectedComm.value));
});

const detailMessageHtml = computed(() => {
	if (!fullContent.value || typeof fullContent.value.message_html !== 'string') return '';
	return fullContent.value.message_html.trim();
});

const detailSnippetFallback = computed(() => {
	if (detailMessageHtml.value) return '';
	const snippet =
		typeof selectedComm.value?.snippet === 'string' ? selectedComm.value.snippet : '';
	return snippet.trim();
});

const detailAttachments = computed(() => fullContent.value?.attachments || []);

function formatAttachmentMeta(attachment: OrgCommunicationAttachmentRow) {
	if (attachment.kind === 'link') {
		return attachment.external_url || 'External link';
	}
	const parts = [attachment.file_name];
	if (attachment.file_size) {
		parts.push(formatFileSize(attachment.file_size));
	}
	return parts.filter(Boolean).join(' · ') || 'Governed file';
}

function formatFileSize(value: number | string | null | undefined) {
	const size = typeof value === 'number' ? value : Number(value || 0);
	if (!Number.isFinite(size) || size <= 0) return '';
	if (size < 1024) return `${size} B`;
	if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
	return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

// User Context for Filters
const myTeams = ref<Array<{ label: string; value: string }>>([]);
const myStudentGroups = ref<Array<{ label: string; value: string; school?: string | null }>>([]);
const orgChoices = ref<Array<{ label: string; value: string }>>([]);
const schoolChoices = ref<Array<{ label: string; value: string; organization?: string | null }>>(
	[]
);

const hasTeamFilter = computed(() => myTeams.value.length > 0);

const organizationOptions = computed(() => [
	{ label: 'All organisations', value: null },
	...orgChoices.value,
]);

const schoolOptions = computed(() => {
	const org = filters.value.organization;
	const scoped = org
		? schoolChoices.value.filter(s => s.organization === org)
		: schoolChoices.value;
	return [{ label: 'All schools', value: null }, ...scoped];
});

const communicationTypeOptions = computed(() => [
	{ label: 'All types', value: 'All' },
	...COMMUNICATION_TYPES.map(value => ({
		label: value,
		value,
	})),
]);

const teamOptions = computed(() => [{ label: 'All teams', value: null }, ...myTeams.value]);

const studentGroupOptions = computed(() => [
	{ label: 'All groups', value: null },
	...myStudentGroups.value,
]);

let reloadTimer: number | null = null;
let feedThrottleTimer: number | null = null;
let feedInFlight: Promise<void> | null = null;
let feedQueued = false;
let feedQueuedReset = false;
let lastFeedRun = 0;
let disposeOrgCommInvalidate: (() => void) | null = null;

function queueReload() {
	if (typeof window === 'undefined') {
		requestFeedLoad(true);
		return;
	}
	if (reloadTimer) window.clearTimeout(reloadTimer);
	reloadTimer = window.setTimeout(() => {
		requestFeedLoad(true);
	}, 350);
}

function requestFeedLoad(reset: boolean) {
	if (!initialized.value) return;

	if (feedInFlight) {
		feedQueued = true;
		feedQueuedReset = feedQueuedReset || reset;
		return;
	}

	const now = Date.now();
	const waitMs = FEED_THROTTLE_MS - (now - lastFeedRun);
	if (waitMs > 0 && typeof window !== 'undefined') {
		if (feedThrottleTimer) window.clearTimeout(feedThrottleTimer);
		feedThrottleTimer = window.setTimeout(() => {
			feedThrottleTimer = null;
			requestFeedLoad(reset);
		}, waitMs);
		return;
	}

	feedInFlight = loadFeed(reset);
	feedInFlight.finally(() => {
		feedInFlight = null;
		lastFeedRun = Date.now();
		if (feedQueued) {
			const nextReset = feedQueuedReset;
			feedQueued = false;
			feedQueuedReset = false;
			requestFeedLoad(nextReset);
		}
	});
}

async function loadArchiveContext() {
	if (contextLoading.value) return;
	contextLoading.value = true;

	try {
		const data = await archiveService.getArchiveContext({});

		myTeams.value = Array.isArray(data.my_teams) ? data.my_teams : [];
		myStudentGroups.value = Array.isArray(data.my_groups) ? data.my_groups : [];

		orgChoices.value = (data.organizations || []).map(o => ({
			label: (o.abbr ? `${o.abbr} — ` : '') + (o.organization_name || o.name),
			value: o.name,
		}));

		schoolChoices.value = (data.schools || []).map(s => ({
			label: (s.abbr ? `${s.abbr} — ` : '') + (s.school_name || s.name),
			value: s.name,
			organization: s.organization || null,
		}));

		if (data.defaults) {
			filters.value.organization = data.defaults.organization || null;
			filters.value.school = data.defaults.school || null;
			filters.value.team = data.defaults.team || null;
		}
	} catch (err) {
		toast({
			title: 'Unable to load archive',
			text: 'Please refresh and try again.',
			icon: 'alert-circle',
			appearance: 'danger',
		});
	} finally {
		contextLoading.value = false;
		if (!initialized.value) {
			initialized.value = true;
			requestFeedLoad(true);
		}
	}
}

watch(
	filters,
	() => {
		if (!initialized.value) return;
		selectedComm.value = null;
		fullContent.value = null;
		detailLoadError.value = null;
		queueReload();
	},
	{ deep: true }
);

/**
 * MUTUAL EXCLUSION: Team ↔ Student Group
 * - If team becomes non-null → student_group = null
 * - If student_group becomes non-null → team = null
 *
 * Guard with `if (val)` so selecting "All" (null) doesn't wipe the other filter.
 */
watch(
	() => filters.value.team,
	val => {
		if (!initialized.value) return;
		if (val) {
			filters.value.student_group = null;
		}
	}
);

watch(
	() => filters.value.student_group,
	val => {
		if (!initialized.value) return;
		if (val) {
			filters.value.team = null;
		}
	}
);

/**
 * ORGANIZATION CHANGE
 * Rule: If organization changes → set school = null, team = null, student_group = null
 *
 * We do it strictly (your rule), and we do it only when org actually changes.
 * Note: This will also trigger the school watcher, but that's fine.
 */
watch(
	() => filters.value.organization,
	(newOrg, oldOrg) => {
		if (!initialized.value) return;
		if (newOrg === oldOrg) return;

		filters.value.school = null;
		filters.value.team = null;
		filters.value.student_group = null;
	}
);

/**
 * SCHOOL CHANGE
 * Rule: If school changes → set team = null and student_group = null (safety)
 *
 * Do it only when school actually changes.
 */
watch(
	() => filters.value.school,
	(newSchool, oldSchool) => {
		if (!initialized.value) return;
		if (newSchool === oldSchool) return;

		filters.value.team = null;
		filters.value.student_group = null;
	}
);

/**
 * VALIDITY GUARD (keep)
 * If schoolOptions changes (because org scope changes, or context loaded),
 * ensure current school is still selectable.
 *
 * With the strict org-change rule above, this will *usually* be redundant,
 * but it's still a good safety net (and harmless).
 */
watch(
	schoolOptions,
	options => {
		const allowed = options.map(o => o.value);
		if (filters.value.school && !allowed.includes(filters.value.school)) {
			filters.value.school = null;
		}
	},
	{ deep: true }
);

function normalizeArchiveFilters(f: ArchiveFilters): ArchiveFilters {
	const cleanLink = (v: any) => {
		if (!v) return null;
		if (typeof v === 'string') return v.trim() || null;
		if (typeof v === 'object' && typeof v.value === 'string') return v.value.trim() || null;
		return null;
	};

	return {
		...f,
		search_text: typeof f.search_text === 'string' ? f.search_text.trim() || null : null,
		team: cleanLink((f as any).team),
		student_group: cleanLink((f as any).student_group),
		school: cleanLink((f as any).school),
		organization: cleanLink((f as any).organization),
	};
}

async function loadFeed(reset = false) {
	if (!initialized.value) return;
	feedLoading.value = true;

	if (reset) {
		start.value = 0;
		feedItems.value = [];
		hasMore.value = false;
		interactionSummaries.value = {};
		selectedComm.value = null;
		fullContent.value = null;
		detailLoadError.value = null;
		threadRows.value = [];
		showThreadDrawer.value = false;
	}

	try {
		const payload = await archiveService.getOrgCommunicationFeed({
			filters: normalizeArchiveFilters(filters.value),
			start: start.value,
			page_length: PAGE_LENGTH,
		});

		const items = Array.isArray(payload.items) ? payload.items : [];

		feedItems.value = reset ? items : [...feedItems.value, ...items];
		hasMore.value = !!payload.has_more;

		const responseStart = typeof payload.start === 'number' ? payload.start : start.value;
		start.value = responseStart + items.length;

		if (items.length) {
			const commNames = items
				.map((i: OrgCommunicationListItem) => i?.name)
				.filter((name): name is string => typeof name === 'string' && !!name.trim());

			if (commNames.length) {
				void refreshSummary(commNames);
			}
		}

		if (!selectedComm.value && feedItems.value.length) {
			void selectItem(feedItems.value[0], { silent: true });
		}
	} catch (err) {
		toast({
			title: 'Unable to load announcements',
			text: 'Please try again.',
			icon: 'alert-circle',
			appearance: 'danger',
		});
	} finally {
		feedLoading.value = false;
	}
}

function loadMore() {
	if (feedLoading.value || !hasMore.value) return;
	requestFeedLoad(false);
}

function onFeedScroll(event: Event) {
	const target = event.target as HTMLElement | null;
	if (!target || feedLoading.value || !hasMore.value) return;

	const remaining = target.scrollHeight - target.scrollTop - target.clientHeight;
	if (remaining <= FEED_SCROLL_THRESHOLD_PX) {
		loadMore();
	}
}

async function selectItem(item: OrgCommunicationListItem, opts?: { silent?: boolean }) {
	if (!item?.name) {
		if (!opts?.silent) {
			toast({
				title: 'Unable to open announcement',
				text: 'Please try again.',
				icon: 'alert-circle',
				appearance: 'danger',
			});
		}
		return;
	}

	selectedComm.value = item;
	fullContent.value = null;
	detailLoadError.value = null;
	fullContentLoading.value = true;

	try {
		fullContent.value = await archiveService.getOrgCommunicationItem({ name: item.name });
	} catch (err) {
		const message = err instanceof Error ? err.message : 'Please try again.';
		detailLoadError.value = message || 'Please try again.';
		if (!opts?.silent) {
			toast({
				title: 'Unable to load announcement',
				text: detailLoadError.value,
				icon: 'alert-circle',
				appearance: 'danger',
			});
		}
	} finally {
		fullContentLoading.value = false;
	}
}

function getInteractionFor(item: OrgCommunicationListItem): InteractionSummary {
	if (!item) return { counts: {}, self: null };
	return interactionSummaries.value[item.name] ?? { counts: {}, self: null };
}

function getInteractionStats(item: OrgCommunicationListItem) {
	return buildInteractionStats(getInteractionFor(item));
}

function canInteract(item: OrgCommunicationListItem) {
	return item.interaction_mode !== 'None';
}

async function refreshSummary(names: string[]) {
	const commNames = names.filter(name => typeof name === 'string' && !!name.trim());
	if (!commNames.length) return;

	try {
		const data = await interactionService.getOrgCommInteractionSummary({ comm_names: commNames });
		if (data) {
			interactionSummaries.value = { ...interactionSummaries.value, ...data };
		}
	} catch (err) {
		// Best-effort refresh; no user action required.
	}
}

async function refreshThread(orgCommunication: string, opts?: { silent?: boolean }) {
	if (!orgCommunication) return;

	threadLoading.value = true;
	try {
		threadRows.value = await interactionService.getCommunicationThread({
			org_communication: orgCommunication,
		});
	} catch (err) {
		if (!opts?.silent) {
			toast({
				title: 'Unable to load comments',
				text: 'Please try again.',
				icon: 'alert-circle',
				appearance: 'danger',
			});
		}
	} finally {
		threadLoading.value = false;
	}
}

function onOrgCommInvalidated(payload?: { names?: string[] }) {
	const names = (payload?.names || []).filter(name => typeof name === 'string' && !!name.trim());
	const selectedName = selectedComm.value?.name || null;

	// Always do the cheap, best-effort refreshes first (counts + thread)
	if (names.length) {
		void refreshSummary(names);

		if (showThreadDrawer.value && selectedName && names.includes(selectedName)) {
			void refreshThread(selectedName, { silent: true });
		}
	} else {
		const fallbackNames = feedItems.value.map(item => item.name).filter(Boolean);
		if (fallbackNames.length) {
			void refreshSummary(fallbackNames);
		}

		if (showThreadDrawer.value && selectedName) {
			void refreshThread(selectedName, { silent: true });
		}
	}

	/**
	 * Refresh-owner rule (A+):
	 * If an interaction can change list membership under current filters,
	 * we must refetch the feed (not just patch counts).
	 *
	 * Currently: only_with_interactions depends on comments existing.
	 * A new comment can cause an item to ENTER the list (or visibility to change),
	 * so we reload the feed in that filter mode.
	 */
	if (filters.value.only_with_interactions) {
		requestFeedLoad(true);
	}
}

function notifyInteractionsDisabled() {
	toast({
		title: 'Interactions disabled',
		text: 'Comments and reactions are turned off for this announcement.',
		icon: 'info',
	});
}

/**
 * Interaction workflow
 * --------------------------------------------------
 * Used by: OrgCommunicationArchive.vue (Staff)
 *
 * Use ONLY semantic service methods (A+):
 * - interactionService.reactToOrgCommunication()
 * - interactionService.postOrgCommunicationComment()
 *
 * Service responsibility:
 * - craft mutation payload (surface, intent_type)
 * - emit SIGNAL_ORG_COMMUNICATION_INVALIDATE on success
 *
 * Page responsibility:
 * - call semantic intent methods
 * - refresh owned data when signal fires
 */
async function reactTo(item: OrgCommunicationListItem, code: ReactionCode) {
	if (!item?.name) {
		toast({
			title: 'Unable to save reaction',
			text: 'Please try again.',
			icon: 'alert-circle',
			appearance: 'danger',
		});
		return;
	}
	if (!canInteract(item)) {
		notifyInteractionsDisabled();
		return;
	}

	try {
		await interactionService.reactToOrgCommunication({
			org_communication: item.name,
			reaction_code: code,
		});
	} catch (err) {
		toast({
			title: 'Unable to save reaction',
			text: 'Please try again.',
			icon: 'alert-circle',
			appearance: 'danger',
		});
	}
}

async function openThread(item: OrgCommunicationListItem) {
	if (!item?.name) {
		toast({
			title: 'Unable to open comments',
			text: 'Please try again.',
			icon: 'alert-circle',
			appearance: 'danger',
		});
		return;
	}
	if (!canInteract(item)) {
		notifyInteractionsDisabled();
		return;
	}
	selectedComm.value = item;
	showThreadDrawer.value = true;
	await refreshThread(item.name);
}

async function submitComment() {
	if (!selectedComm.value?.name) {
		toast({
			title: 'Select an announcement',
			text: 'Choose an announcement before posting a comment.',
			icon: 'info',
		});
		return;
	}
	if (!canInteract(selectedComm.value)) {
		notifyInteractionsDisabled();
		return;
	}

	const note = newComment.value.trim();
	if (!note) {
		toast({
			title: 'Comment required',
			text: 'Write a comment before posting.',
			icon: 'info',
		});
		return;
	}

	interactionActionLoading.value = true;
	try {
		await interactionService.postOrgCommunicationComment({
			org_communication: selectedComm.value.name,
			note,
		});
		newComment.value = '';
	} catch (err) {
		toast({
			title: 'Unable to post comment',
			text: 'Please try again.',
			icon: 'alert-circle',
			appearance: 'danger',
		});
	} finally {
		interactionActionLoading.value = false;
	}
}

onMounted(() => {
	loadArchiveContext();
	disposeOrgCommInvalidate = uiSignals.subscribe(
		SIGNAL_ORG_COMMUNICATION_INVALIDATE,
		onOrgCommInvalidated
	);
});

onBeforeUnmount(() => {
	if (reloadTimer && typeof window !== 'undefined') window.clearTimeout(reloadTimer);
	if (feedThrottleTimer && typeof window !== 'undefined') window.clearTimeout(feedThrottleTimer);
	if (disposeOrgCommInvalidate) disposeOrgCommInvalidate();
});

function formatDate(date: string | null, fmt = 'DD MMM') {
	if (!date) return '';
	if (fmt === 'DD MMM') {
		return formatLocalizedDate(date, { day: '2-digit', month: 'short', fallback: '' });
	}
	if (fmt === 'DD MMMM YYYY') {
		return formatLocalizedDate(date, {
			day: '2-digit',
			month: 'long',
			includeYear: true,
			fallback: '',
		});
	}
	if (fmt === 'DD MMM HH:mm') {
		return formatLocalizedDateTime(date, {
			day: '2-digit',
			month: 'short',
			fallback: '',
		});
	}

	return formatLocalizedDate(date, { day: '2-digit', month: 'short', fallback: '' });
}

function getPriorityClass(priority: string) {
	switch (priority) {
		case 'Critical':
			return 'bg-flame';
		case 'High':
			return 'bg-jacaranda';
		case 'Normal':
			return 'bg-blue-400';
		case 'Low':
			return 'bg-slate-300';
		default:
			return 'bg-slate-200';
	}
}

function getPriorityColor(priority: string) {
	switch (priority) {
		case 'Critical':
			return 'red';
		case 'High':
			return 'purple';
		case 'Normal':
			return 'blue';
		default:
			return 'gray';
	}
}

function onDetailContentClick(event: MouseEvent) {
	const payload: PolicyInformLinkPayload | null = extractPolicyInformLinkFromClickEvent(event);
	if (!payload) return;
	event.preventDefault();

	const policyVersion = String(payload.policyVersion || '').trim();
	if (!policyVersion) return;
	const orgCommunication =
		String(payload.orgCommunication || '').trim() ||
		String(selectedComm.value?.name || '').trim() ||
		null;

	overlay.open('staff-policy-inform', {
		policyVersion,
		orgCommunication,
	});
}
</script>

<style scoped>
.org-archive__grid {
	min-height: 0;
}

@media (min-width: 900px) {
	.org-archive__grid {
		display: grid;
		grid-template-columns: minmax(0, 4fr) minmax(0, 6fr);
		height: calc(100vh - 16rem);
	}

	.org-archive__list,
	.org-archive__detail {
		min-width: 0;
	}
}
</style>
