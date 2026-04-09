<template>
	<div class="portal-page space-y-6">
		<header class="card-surface p-5 sm:p-6">
			<div class="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
				<div>
					<p class="type-overline text-ink/60">Student Hub</p>
					<h1 class="type-h1 text-ink">Communication Center</h1>
					<p class="type-body text-ink/70">
						See class, activity, pastoral, cohort, and school updates in one place.
					</p>
				</div>
				<div class="flex items-center gap-2">
					<RouterLink :to="{ name: 'student-home' }" class="if-action">Back to Home</RouterLink>
					<button type="button" class="if-action" :disabled="loading" @click="refreshFeed">
						Refresh
					</button>
				</div>
			</div>
		</header>

		<section class="card-surface p-5">
			<div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
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

				<div class="flex flex-wrap gap-2">
					<span class="chip">Total {{ totalCount }}</span>
					<span v-for="chip in summaryChips" :key="chip.label" class="chip">
						{{ chip.label }} {{ chip.count }}
					</span>
				</div>
			</div>
		</section>

		<section
			v-if="errorMessage"
			class="card-surface border border-flame/30 bg-[var(--flame)]/5 p-5"
		>
			<p class="type-body-strong text-flame">Could not load communications.</p>
			<p class="mt-2 type-caption text-ink/70">{{ errorMessage }}</p>
		</section>

		<section v-else-if="loading && !items.length" class="card-surface p-5">
			<p class="type-body text-ink/70">Loading student communications...</p>
		</section>

		<section
			v-else-if="!items.length"
			class="card-surface border border-dashed border-line-soft p-5"
		>
			<p class="type-body text-ink/70">No communications match this view right now.</p>
		</section>

		<section v-else class="space-y-4">
			<article v-for="item in items" :key="item.item_id" class="card-surface p-5">
				<template v-if="item.kind === 'org_communication'">
					<div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
						<div class="min-w-0">
							<div class="flex flex-wrap items-center gap-2">
								<p class="type-caption text-ink/60">{{ item.source_label }}</p>
								<span class="chip">{{ item.org_communication.communication_type }}</span>
								<span class="chip">{{ item.org_communication.priority }}</span>
							</div>
							<h2 class="mt-2 type-h3 text-ink">{{ item.org_communication.title }}</h2>
							<p class="mt-2 type-caption text-ink/60">{{ metaLine(item) }}</p>
							<p class="mt-3 type-body text-ink/80">{{ item.org_communication.snippet }}</p>
						</div>

						<div class="flex flex-wrap gap-2">
							<RouterLink v-if="item.href" :to="item.href" class="if-action">
								{{ item.href_label || 'Open' }}
							</RouterLink>
							<button type="button" class="if-action" @click="toggleOrgCommunication(item)">
								{{ expandedItemId === item.item_id ? 'Hide update' : 'Read update' }}
							</button>
						</div>
					</div>

					<p v-if="actionError" class="mt-4 type-caption text-flame">{{ actionError }}</p>

					<div class="mt-4 flex flex-wrap items-center gap-3">
						<InteractionEmojiChips
							:interaction="interactionFor(item.org_communication.name)"
							:readonly="!canReact(item.org_communication)"
							:onReact="code => reactToCommunication(item.org_communication.name, code)"
						/>
						<button
							type="button"
							class="if-action"
							:disabled="!canComment(item.org_communication)"
							@click="openThread(item)"
						>
							Comments ({{ interactionFor(item.org_communication.name).comments_total || 0 }})
						</button>
					</div>

					<div
						v-if="expandedItemId === item.item_id"
						class="mt-5 rounded-2xl border border-line-soft bg-surface-soft p-5"
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
										:key="attachment.name"
										:href="attachment.open_url"
										target="_blank"
										rel="noreferrer"
										class="inline-flex items-center rounded-full border border-line-soft bg-white px-3 py-1 text-xs font-medium text-ink transition hover:border-jacaranda/40 hover:bg-jacaranda/5"
									>
										{{ attachment.label || attachment.file_name || attachment.name }}
									</a>
								</div>
							</div>
						</div>
					</div>
				</template>

				<template v-else>
					<div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
						<div>
							<div class="flex flex-wrap items-center gap-2">
								<p class="type-caption text-ink/60">{{ item.source_label }}</p>
								<span v-if="item.school_event.event_type" class="chip">
									{{ item.school_event.event_type }}
								</span>
							</div>
							<h2 class="mt-2 type-h3 text-ink">{{ item.school_event.subject }}</h2>
							<p class="mt-2 type-caption text-ink/60">{{ schoolEventMetaLine(item) }}</p>
							<p v-if="item.school_event.snippet" class="mt-3 type-body text-ink/80">
								{{ item.school_event.snippet }}
							</p>
						</div>

						<button type="button" class="if-action" @click="openSchoolEvent(item)">
							View event
						</button>
					</div>
				</template>
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
			:submit-loading="commentSubmitting"
			:submit-disabled="commentSubmitting || !commentValue.trim()"
			@close="closeThread"
			@submit="submitComment"
			@update:comment="onCommentUpdate"
		/>

		<SchoolEventModal
			:open="schoolEventOpen"
			:event="selectedSchoolEventName"
			@close="closeSchoolEvent"
			@after-leave="selectedSchoolEventName = null"
		/>
	</div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { toast } from 'frappe-ui';
import { RouterLink, useRoute, useRouter } from 'vue-router';

import SchoolEventModal from '@/components/calendar/SchoolEventModal.vue';
import CommentThreadDrawer from '@/components/CommentThreadDrawer.vue';
import InteractionEmojiChips from '@/components/InteractionEmojiChips.vue';
import { formatLocalizedDateTime } from '@/lib/datetime';
import { createCommunicationInteractionService } from '@/lib/services/communicationInteraction/communicationInteractionService';
import { createOrgCommunicationArchiveService } from '@/lib/services/orgCommunicationArchive/orgCommunicationArchiveService';
import { getStudentCommunicationCenter } from '@/lib/services/student/studentLearningHubService';
import type { Response as OrgCommunicationDetailResponse } from '@/types/contracts/org_communication_archive/get_org_communication_item';
import type { ReactionCode } from '@/types/interactions';
import type {
	InteractionSummary,
	InteractionSummaryMap,
	InteractionThreadRow,
} from '@/types/morning_brief';
import type {
	StudentCommunicationCenterItem,
	StudentOrgCommunicationCenterItem,
	StudentSchoolEventCenterItem,
} from '@/types/studentCommunication';

type SourceFilter = 'all' | 'course' | 'activity' | 'school' | 'pastoral' | 'cohort';

const route = useRoute();
const router = useRouter();
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

const items = ref<StudentCommunicationCenterItem[]>([]);
const totalCount = ref(0);
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
const threadOpen = ref(false);
const threadLoading = ref(false);
const commentSubmitting = ref(false);
const threadRows = ref<InteractionThreadRow[]>([]);
const commentValue = ref('');
const selectedCommunication = ref<StudentOrgCommunicationCenterItem | null>(null);
const schoolEventOpen = ref(false);
const selectedSchoolEventName = ref<string | null>(null);

const activeSource = computed<SourceFilter>(() => {
	const value =
		typeof route.query.source === 'string' ? route.query.source.trim().toLowerCase() : 'all';
	if (sourceOptions.some(option => option.value === value)) {
		return value as SourceFilter;
	}
	return 'all';
});

const requestedItemId = computed(() =>
	typeof route.query.item === 'string' ? route.query.item.trim() : ''
);

const summaryChips = computed(() =>
	sourceOptions
		.filter(option => option.value !== 'all')
		.map(option => ({
			label: option.label,
			count: summaryCounts.value[option.value] || 0,
		}))
		.filter(chip => chip.count > 0)
);

const threadTitle = computed(() =>
	selectedCommunication.value
		? `Comments · ${selectedCommunication.value.org_communication.title}`
		: 'Comments'
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

function canReact(item: { interaction_mode?: string | null }) {
	return item.interaction_mode !== 'None';
}

function canComment(item: {
	interaction_mode?: string | null;
	allow_public_thread?: 0 | 1 | boolean;
}) {
	return canReact(item) && Boolean(item.allow_public_thread);
}

function metaLine(item: StudentOrgCommunicationCenterItem) {
	const parts = [
		item.context_label || '',
		item.sort_at ? formatLocalizedDateTime(item.sort_at, { fallback: item.sort_at }) : '',
	].filter(Boolean);
	return parts.join(' · ');
}

function schoolEventMetaLine(item: StudentSchoolEventCenterItem) {
	const parts = [
		item.school_event.location || '',
		item.school_event.starts_on
			? formatLocalizedDateTime(item.school_event.starts_on, {
					fallback: item.school_event.starts_on,
				})
			: '',
	].filter(Boolean);
	return parts.join(' · ');
}

function communicationDetail(name: string) {
	return detailMap.value[name] || null;
}

async function loadSummaries() {
	const names = items.value
		.filter((item): item is StudentOrgCommunicationCenterItem => item.kind === 'org_communication')
		.map(item => item.org_communication.name)
		.filter(Boolean);
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
	} else {
		loadingMore.value = true;
	}
	errorMessage.value = '';
	try {
		const response = await getStudentCommunicationCenter({
			source: activeSource.value,
			start: reset ? 0 : items.value.length,
			page_length: 24,
		});
		summaryCounts.value = response.summary.source_counts || {};
		totalCount.value = response.total_count || 0;
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

async function selectSource(source: SourceFilter) {
	await router.replace({
		query: {
			...route.query,
			source: source === 'all' ? undefined : source,
			item: undefined,
		},
	});
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

async function toggleOrgCommunication(item: StudentOrgCommunicationCenterItem) {
	actionError.value = '';
	if (expandedItemId.value === item.item_id) {
		expandedItemId.value = '';
		return;
	}
	expandedItemId.value = item.item_id;
	await loadCommunicationDetail(item.org_communication.name);
}

async function reactToCommunication(commName: string, code: ReactionCode) {
	actionError.value = '';
	try {
		await interactionService.reactToOrgCommunication({
			org_communication: commName,
			reaction_code: code,
			surface: 'Portal Feed',
		});
		await loadSummaries();
	} catch (error) {
		const message = error instanceof Error ? error.message : String(error || '');
		actionError.value = message || 'Could not record reaction.';
	}
}

async function openThread(item: StudentOrgCommunicationCenterItem) {
	actionError.value = '';
	if (!canComment(item.org_communication)) {
		actionError.value = 'Comments are not enabled for this update.';
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
		actionError.value = message || 'Could not load comment thread.';
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
	const note = commentValue.value.trim();
	if (!note) {
		actionError.value = 'Please add a comment before posting.';
		return;
	}
	commentSubmitting.value = true;
	try {
		await interactionService.postOrgCommunicationComment({
			org_communication: comm.name,
			note,
			surface: 'Portal Feed',
		});
		commentValue.value = '';
		threadRows.value = await interactionService.getCommunicationThread({
			org_communication: comm.name,
			limit_start: 0,
			limit: 200,
		});
		await loadSummaries();
		toast.success('Comment posted.');
	} catch (error) {
		const message = error instanceof Error ? error.message : String(error || '');
		actionError.value = message || 'Could not post comment.';
	} finally {
		commentSubmitting.value = false;
	}
}

function openSchoolEvent(item: StudentSchoolEventCenterItem) {
	selectedSchoolEventName.value = item.school_event.name;
	schoolEventOpen.value = true;
}

function closeSchoolEvent() {
	schoolEventOpen.value = false;
}

watch(
	() => activeSource.value,
	() => {
		void loadFeed(true);
	},
	{ immediate: true }
);

watch(
	() => [requestedItemId.value, items.value.map(item => item.item_id).join('|')] as const,
	async ([itemId]) => {
		if (!itemId) return;
		const target = items.value.find(item => item.item_id === itemId);
		if (!target) return;
		if (target.kind === 'org_communication') {
			expandedItemId.value = target.item_id;
			await loadCommunicationDetail(target.org_communication.name);
			return;
		}
		openSchoolEvent(target);
	},
	{ immediate: true }
);
</script>
