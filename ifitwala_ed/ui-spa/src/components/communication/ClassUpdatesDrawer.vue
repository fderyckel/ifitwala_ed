<template>
	<Teleport to="body">
		<TransitionRoot as="template" :show="open">
			<Dialog
				as="div"
				class="if-overlay if-overlay--drawer if-overlay--class-updates z-[95]"
				:initialFocus="closeButtonRef"
				@close="emitClose"
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
					<div class="if-overlay__backdrop" @click="emitClose" />
				</TransitionChild>

				<div class="if-overlay__wrap if-overlay__wrap--drawer" @click.self="emitClose">
					<TransitionChild
						as="template"
						enter="if-overlay__panel-enter"
						enter-from="if-overlay__panel-from"
						enter-to="if-overlay__panel-to"
						leave="if-overlay__panel-leave"
						leave-from="if-overlay__panel-to"
						leave-to="if-overlay__panel-from"
					>
						<DialogPanel
							class="if-overlay__panel if-overlay__panel--drawer-md class-updates__panel"
						>
							<header class="class-updates__header border-b border-border/60 px-4 py-4">
								<div class="flex items-start justify-between gap-3">
									<div class="min-w-0">
										<p class="type-overline text-ink/60">
											{{ selectedCommunication ? 'Class Update' : 'Class Updates' }}
										</p>
										<DialogTitle class="mt-2 type-h3 text-ink">
											{{ headerTitle }}
										</DialogTitle>
										<p v-if="headerSubtitle" class="mt-2 type-caption text-ink/60">
											{{ headerSubtitle }}
										</p>
									</div>
									<div class="flex items-center gap-2">
										<button
											v-if="selectedCommunication"
											type="button"
											class="if-action"
											@click="goBackToList"
										>
											Back to list
										</button>
										<button
											ref="closeButtonRef"
											type="button"
											class="if-overlay__icon-button"
											aria-label="Close class updates"
											@click="emitClose"
										>
											<FeatherIcon name="x" class="h-4 w-4" />
										</button>
									</div>
								</div>

								<div v-if="!selectedCommunication" class="mt-4 flex flex-wrap gap-2">
									<span class="chip">Total {{ drawerSummary.total_count }}</span>
									<span v-if="drawerSummary.unread_count" class="chip">
										New {{ drawerSummary.unread_count }}
									</span>
									<span v-if="drawerSummary.high_priority_count" class="chip">
										Priority {{ drawerSummary.high_priority_count }}
									</span>
								</div>
							</header>

							<section class="if-overlay__body class-updates__body custom-scrollbar px-4 py-4">
								<p v-if="actionError" class="mb-4 type-caption text-flame">{{ actionError }}</p>

								<div v-if="!selectedCommunication">
									<div v-if="loading && !items.length" class="py-8 text-center">
										<LoadingIndicator />
									</div>
									<p v-else-if="errorMessage" class="type-body text-flame">{{ errorMessage }}</p>
									<div
										v-else-if="!items.length"
										class="rounded-2xl border border-dashed border-line-soft p-4"
									>
										<p class="type-body text-ink/70">
											No updates have been shared for this class yet.
										</p>
									</div>
									<ul v-else class="space-y-3">
										<li v-for="item in items" :key="item.item_id">
											<button
												type="button"
												class="class-updates__row w-full rounded-2xl border border-line-soft bg-surface-soft p-4 text-left transition hover:border-jacaranda/35 hover:bg-white"
												@click="openCommunication(item)"
											>
												<div class="flex items-start justify-between gap-3">
													<div class="min-w-0">
														<div class="flex flex-wrap items-center gap-2">
															<p class="type-body-strong text-ink">
																{{ item.org_communication.title }}
															</p>
															<span
																v-if="item.is_unread"
																class="rounded-full bg-jacaranda/10 px-2 py-1 text-[11px] font-semibold text-jacaranda"
															>
																New
															</span>
															<span
																v-if="isHighPriority(item)"
																class="rounded-full bg-flame/10 px-2 py-1 text-[11px] font-semibold text-flame"
															>
																{{ item.org_communication.priority }}
															</span>
														</div>
														<p class="mt-2 type-caption text-ink/60">
															{{ itemMetaLine(item) }}
														</p>
														<p class="mt-3 line-clamp-2 type-body text-ink/80">
															{{ item.org_communication.snippet }}
														</p>
													</div>
													<FeatherIcon
														name="chevron-right"
														class="mt-1 h-4 w-4 shrink-0 text-ink/35"
													/>
												</div>
												<div class="mt-3 flex flex-wrap gap-2">
													<span class="chip">{{ item.org_communication.communication_type }}</span>
													<span
														v-if="interactionFor(item.org_communication.name).comments_total"
														class="chip"
													>
														Comments
														{{ interactionFor(item.org_communication.name).comments_total }}
													</span>
												</div>
											</button>
										</li>
									</ul>
								</div>

								<div v-else>
									<div class="mb-4 flex flex-wrap gap-2">
										<span class="chip">{{
											selectedCommunication.org_communication.communication_type
										}}</span>
										<span class="chip">{{
											selectedCommunication.org_communication.priority
										}}</span>
										<span v-if="selectedCommunication.context_label" class="chip">
											{{ selectedCommunication.context_label }}
										</span>
									</div>
									<p class="mb-4 type-caption text-ink/60">
										{{ itemMetaLine(selectedCommunication) }}
									</p>

									<p
										v-if="detailLoading[selectedCommunication.org_communication.name]"
										class="py-6 text-center"
									>
										<LoadingIndicator />
									</p>
									<p
										v-else-if="detailError[selectedCommunication.org_communication.name]"
										class="type-body text-flame"
									>
										{{ detailError[selectedCommunication.org_communication.name] }}
									</p>
									<div
										v-else-if="communicationDetail(selectedCommunication.org_communication.name)"
									>
										<div
											class="prose prose-slate max-w-none"
											v-html="
												communicationDetail(selectedCommunication.org_communication.name)
													?.message_html || ''
											"
										></div>

										<div
											v-if="
												communicationDetail(selectedCommunication.org_communication.name)
													?.attachments?.length
											"
											class="mt-5 space-y-2"
										>
											<p class="type-body-strong text-ink">Attachments</p>
											<div class="flex flex-wrap gap-2">
												<a
													v-for="attachment in communicationDetail(
														selectedCommunication.org_communication.name
													)?.attachments || []"
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

										<div class="mt-6 flex flex-wrap items-center gap-3">
											<InteractionEmojiChips
												:interaction="interactionFor(selectedCommunication.org_communication.name)"
												:readonly="!canReact(selectedCommunication.org_communication)"
												:onReact="
													code =>
														reactToCommunication(
															selectedCommunication.org_communication.name,
															code
														)
												"
											/>
											<button
												type="button"
												class="if-action"
												:disabled="!canComment(selectedCommunication.org_communication)"
												@click="openThread(selectedCommunication)"
											>
												Comments ({{
													interactionFor(selectedCommunication.org_communication.name)
														.comments_total || 0
												}})
											</button>
										</div>
									</div>
								</div>
							</section>

							<footer
								v-if="!selectedCommunication && hasMore"
								class="if-overlay__footer justify-end"
							>
								<button type="button" class="if-action" :disabled="loadingMore" @click="loadMore">
									{{ loadingMore ? 'Loading…' : 'Load more' }}
								</button>
							</footer>
						</DialogPanel>
					</TransitionChild>
				</div>
			</Dialog>
		</TransitionRoot>
	</Teleport>

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
</template>

<script setup lang="ts">
import {
	Dialog,
	DialogPanel,
	DialogTitle,
	TransitionChild,
	TransitionRoot,
} from '@headlessui/vue';
import { computed, ref, watch } from 'vue';
import { FeatherIcon, LoadingIndicator, toast } from 'frappe-ui';

import CommentThreadDrawer from '@/components/CommentThreadDrawer.vue';
import InteractionEmojiChips from '@/components/InteractionEmojiChips.vue';
import { formatLocalizedDateTime } from '@/lib/datetime';
import { createCommunicationInteractionService } from '@/lib/services/communicationInteraction/communicationInteractionService';
import { createOrgCommunicationArchiveService } from '@/lib/services/orgCommunicationArchive/orgCommunicationArchiveService';
import { getStudentCourseCommunicationDrawer } from '@/lib/services/student/studentLearningHubService';
import type { Response as GetStudentCourseCommunicationDrawerResponse } from '@/types/contracts/student_communication/get_student_course_communication_drawer';
import type { StudentCourseCommunicationSummary } from '@/types/contracts/student_communication/get_student_course_communication_drawer';
import type { Response as OrgCommunicationDetailResponse } from '@/types/contracts/org_communication_archive/get_org_communication_item';
import type { ReactionCode } from '@/types/interactions';
import type {
	InteractionSummary,
	InteractionSummaryMap,
	InteractionThreadRow,
} from '@/types/morning_brief';
import type { StudentOrgCommunicationCenterItem } from '@/types/studentCommunication';

const props = withDefaults(
	defineProps<{
		open: boolean;
		courseId: string;
		courseName?: string | null;
		classLabel?: string | null;
		studentGroup?: string;
		summary: StudentCourseCommunicationSummary;
		requestedCommunication?: string | null;
	}>(),
	{
		courseName: null,
		classLabel: null,
		studentGroup: '',
		requestedCommunication: null,
	}
);

const emit = defineEmits<{
	(e: 'close'): void;
	(e: 'summary-change', value: StudentCourseCommunicationSummary): void;
}>();

const interactionService = createCommunicationInteractionService();
const archiveService = createOrgCommunicationArchiveService();

const closeButtonRef = ref<HTMLButtonElement | null>(null);
const items = ref<StudentOrgCommunicationCenterItem[]>([]);
const drawerSummary = ref<StudentCourseCommunicationSummary>({
	total_count: 0,
	unread_count: 0,
	high_priority_count: 0,
	has_high_priority: 0,
	latest_publish_at: null,
});
const loading = ref(false);
const loadingMore = ref(false);
const hasMore = ref(false);
const errorMessage = ref('');
const actionError = ref('');
const selectedCommunicationName = ref('');
const summaryMap = ref<InteractionSummaryMap>({});
const detailMap = ref<Record<string, OrgCommunicationDetailResponse | null>>({});
const detailLoading = ref<Record<string, boolean>>({});
const detailError = ref<Record<string, string>>({});
const threadOpen = ref(false);
const threadLoading = ref(false);
const commentSubmitting = ref(false);
const threadRows = ref<InteractionThreadRow[]>([]);
const commentValue = ref('');
const markingRead = ref<Record<string, boolean>>({});
const autoOpenedCommunication = ref('');

const selectedCommunication = computed<StudentOrgCommunicationCenterItem | null>(() => {
	return (
		items.value.find(item => item.org_communication.name === selectedCommunicationName.value) ||
		null
	);
});

const headerTitle = computed(() => {
	if (selectedCommunication.value) {
		return selectedCommunication.value.org_communication.title;
	}
	if (props.classLabel && props.courseName) {
		return `${props.courseName} · ${props.classLabel}`;
	}
	return props.courseName || props.classLabel || 'Class updates';
});

const headerSubtitle = computed(() => {
	if (selectedCommunication.value) {
		return props.classLabel || props.courseName || '';
	}
	if (props.classLabel && props.courseName) {
		return 'Open a class message without leaving your learning space.';
	}
	return props.classLabel || props.courseName || '';
});

const threadTitle = computed(() =>
	selectedCommunication.value
		? `Comments · ${selectedCommunication.value.org_communication.title}`
		: 'Comments'
);

function cloneSummary(
	summary: StudentCourseCommunicationSummary
): StudentCourseCommunicationSummary {
	return {
		total_count: Number(summary?.total_count || 0),
		unread_count: Number(summary?.unread_count || 0),
		high_priority_count: Number(summary?.high_priority_count || 0),
		has_high_priority: summary?.has_high_priority ? 1 : 0,
		latest_publish_at: summary?.latest_publish_at || null,
	};
}

function emitClose() {
	emit('close');
}

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

function isHighPriority(item: StudentOrgCommunicationCenterItem) {
	return ['High', 'Critical'].includes(String(item.org_communication.priority || '').trim());
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

function itemMetaLine(item: StudentOrgCommunicationCenterItem) {
	const parts = [
		item.context_label || '',
		item.sort_at ? formatLocalizedDateTime(item.sort_at, { fallback: item.sort_at }) : '',
	].filter(Boolean);
	return parts.join(' · ');
}

function communicationDetail(name: string) {
	return detailMap.value[name] || null;
}

function mergeUniqueItems(nextItems: StudentOrgCommunicationCenterItem[]) {
	const merged = new Map<string, StudentOrgCommunicationCenterItem>();
	for (const item of [...items.value, ...nextItems]) {
		merged.set(item.item_id, item);
	}
	items.value = Array.from(merged.values());
}

async function loadInteractionSummaries(rows: StudentOrgCommunicationCenterItem[]) {
	const names = rows.map(row => row.org_communication.name).filter(Boolean);
	if (!names.length) {
		summaryMap.value = {};
		return;
	}
	summaryMap.value = await interactionService.getOrgCommInteractionSummary({ comm_names: names });
}

function applySummary(summary: StudentCourseCommunicationSummary) {
	drawerSummary.value = cloneSummary(summary);
	emit('summary-change', drawerSummary.value);
}

async function loadFeed(reset = true) {
	if (!props.open) return;
	if (reset) {
		loading.value = true;
		errorMessage.value = '';
		actionError.value = '';
		items.value = [];
		selectedCommunicationName.value = '';
	} else {
		loadingMore.value = true;
	}

	try {
		const response: GetStudentCourseCommunicationDrawerResponse =
			await getStudentCourseCommunicationDrawer({
				course_id: props.courseId,
				student_group: props.studentGroup || undefined,
				focus_communication: reset ? props.requestedCommunication || undefined : undefined,
				start: reset ? 0 : items.value.length,
				page_length: 18,
			});

		if (reset) {
			items.value = response.items || [];
		} else {
			mergeUniqueItems(response.items || []);
		}
		hasMore.value = Boolean(response.has_more);
		applySummary(response.summary);
		await loadInteractionSummaries(items.value);
	} catch (error) {
		const message = error instanceof Error ? error.message : String(error || '');
		errorMessage.value = message || 'Could not load class updates.';
	} finally {
		loading.value = false;
		loadingMore.value = false;
	}
}

async function loadMore() {
	await loadFeed(false);
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

function markReadLocally(name: string) {
	let decremented = false;
	items.value = items.value.map(item => {
		if (item.org_communication.name !== name || !item.is_unread) {
			return item;
		}
		decremented = true;
		return {
			...item,
			is_unread: false,
		};
	});
	if (decremented) {
		applySummary({
			...drawerSummary.value,
			unread_count: Math.max(0, Number(drawerSummary.value.unread_count || 0) - 1),
		});
	}
}

async function markCommunicationRead(item: StudentOrgCommunicationCenterItem) {
	if (!item.is_unread || markingRead.value[item.org_communication.name]) {
		return;
	}
	markingRead.value[item.org_communication.name] = true;
	try {
		await interactionService.markOrgCommunicationRead({
			org_communication: item.org_communication.name,
		});
		markReadLocally(item.org_communication.name);
	} catch (error) {
		const message = error instanceof Error ? error.message : String(error || '');
		actionError.value = message || 'Could not update read state.';
	} finally {
		markingRead.value[item.org_communication.name] = false;
	}
}

async function openCommunication(item: StudentOrgCommunicationCenterItem) {
	selectedCommunicationName.value = item.org_communication.name;
	actionError.value = '';
	await loadCommunicationDetail(item.org_communication.name);
	await markCommunicationRead(item);
}

function goBackToList() {
	selectedCommunicationName.value = '';
}

async function reactToCommunication(commName: string, code: ReactionCode) {
	actionError.value = '';
	try {
		await interactionService.reactToOrgCommunication({
			org_communication: commName,
			reaction_code: code,
			surface: 'Portal Feed',
		});
		await loadInteractionSummaries(items.value);
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
		await loadInteractionSummaries(items.value);
		toast.success('Comment posted.');
	} catch (error) {
		const message = error instanceof Error ? error.message : String(error || '');
		actionError.value = message || 'Could not post comment.';
	} finally {
		commentSubmitting.value = false;
	}
}

watch(
	() => props.summary,
	summary => {
		if (!props.open) {
			drawerSummary.value = cloneSummary(summary);
		}
	},
	{ immediate: true, deep: true }
);

watch(
	() => [props.open, props.courseId, props.studentGroup] as const,
	([isOpen]) => {
		if (!isOpen) return;
		void loadFeed(true);
	}
);

watch(
	() =>
		[
			props.open,
			props.requestedCommunication,
			items.value.map(item => item.org_communication.name).join('|'),
		] as const,
	([isOpen, requestedCommunication]) => {
		const targetName = String(requestedCommunication || '').trim();
		if (!isOpen || !targetName || autoOpenedCommunication.value === targetName) {
			return;
		}
		const target = items.value.find(item => item.org_communication.name === targetName);
		if (!target) return;
		autoOpenedCommunication.value = targetName;
		void openCommunication(target);
	},
	{ immediate: true }
);

watch(
	() => props.open,
	isOpen => {
		if (isOpen) return;
		selectedCommunicationName.value = '';
		errorMessage.value = '';
		actionError.value = '';
		autoOpenedCommunication.value = '';
	}
);
</script>

<style scoped>
.class-updates__panel {
	background: rgb(var(--surface-strong-rgb) / 1);
	border-left: 1px solid rgb(var(--border-rgb) / 0.9);
	box-shadow: var(--shadow-overlay);
}

.class-updates__header,
.class-updates__body {
	background: rgb(var(--surface-strong-rgb) / 1);
}

.class-updates__row:focus-visible {
	outline: 2px solid rgb(var(--accent-rgb) / 0.45);
	outline-offset: 2px;
}
</style>
