<!-- ifitwala_ed/ui-spa/src/components/activity/ActivityCommunicationPanel.vue -->
<template>
	<section class="card-surface p-5">
		<div class="mb-4 flex items-center justify-between">
			<h3 class="type-h3 text-ink">Activity Updates</h3>
			<button type="button" class="if-action" :disabled="loading" @click="loadFeed">
				Refresh
			</button>
		</div>

		<p v-if="actionError" class="mb-3 type-caption text-flame">{{ actionError }}</p>
		<p v-if="loading" class="type-body text-ink/70">Loading activity updates...</p>
		<p v-else-if="errorMessage" class="type-body text-flame">{{ errorMessage }}</p>
		<p v-else-if="!feedItems.length" class="type-body text-ink/70">No updates for this activity yet.</p>

		<div v-else class="space-y-3">
			<article
				v-for="item in feedItems"
				:key="item.name"
				class="rounded-xl border border-line-soft bg-surface-soft p-4"
			>
				<div class="mb-1 flex items-start justify-between gap-3">
					<div>
						<p class="type-body-strong text-ink">{{ item.title }}</p>
						<p class="type-caption text-ink/60">
							{{ formatDate(item.publish_from) }} · {{ item.communication_type }}
						</p>
					</div>
					<span class="type-caption text-ink/60">{{ item.priority }}</span>
				</div>

				<p class="type-body text-ink/80">{{ item.snippet }}</p>

				<div class="mt-3 flex flex-wrap items-center gap-3">
					<InteractionEmojiChips
						:interaction="interactionFor(item.name)"
						:readonly="!canReact(item)"
						:onReact="(code) => react(item.name, code)"
					/>
					<button
						type="button"
						class="if-action"
						:disabled="!canComment(item)"
						@click="openThread(item)"
					>
						Comments ({{ interactionFor(item.name).comments_total || 0 }})
					</button>
				</div>
			</article>
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
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { toast } from 'frappe-ui'

import InteractionEmojiChips from '@/components/InteractionEmojiChips.vue'
import CommentThreadDrawer from '@/components/CommentThreadDrawer.vue'

import { getActivityCommunications } from '@/lib/services/activityBooking/activityBookingService'
import { createCommunicationInteractionService } from '@/lib/services/communicationInteraction/communicationInteractionService'

import type { OrgCommunicationListItem } from '@/types/orgCommunication'
import type { InteractionSummary, InteractionSummaryMap, InteractionThreadRow } from '@/types/morning_brief'
import type { ReactionCode } from '@/types/interactions'

const props = defineProps<{
	programOffering: string | null
	activeSection?: string | null
}>()

const interactionService = createCommunicationInteractionService()

const loading = ref<boolean>(false)
const errorMessage = ref<string>('')
const actionError = ref<string>('')
const feedItems = ref<OrgCommunicationListItem[]>([])
const summaryMap = ref<InteractionSummaryMap>({})

const threadOpen = ref<boolean>(false)
const threadLoading = ref<boolean>(false)
const commentSubmitting = ref<boolean>(false)
const threadRows = ref<InteractionThreadRow[]>([])
const selectedComm = ref<OrgCommunicationListItem | null>(null)
const commentValue = ref<string>('')

const threadTitle = computed(() =>
	selectedComm.value ? `Comments · ${selectedComm.value.title}` : 'Comments'
)

function emptySummary(): InteractionSummary {
	return {
		counts: {},
		reaction_counts: {},
		reactions_total: 0,
		comments_total: 0,
		self: null,
	}
}

function interactionFor(commName: string): InteractionSummary {
	return summaryMap.value[commName] || emptySummary()
}

function canReact(item: OrgCommunicationListItem): boolean {
	return item.interaction_mode !== 'None'
}

function canComment(item: OrgCommunicationListItem): boolean {
	return canReact(item) && Boolean(item.allow_public_thread)
}

function formatDate(value: string | null | undefined): string {
	if (!value) return 'Date unavailable'
	const date = new Date(value)
	if (Number.isNaN(date.getTime())) return String(value)
	return date.toLocaleDateString()
}

async function loadSummaries(items: OrgCommunicationListItem[]) {
	const names = items.map((row) => row.name).filter(Boolean)
	if (!names.length) {
		summaryMap.value = {}
		return
	}
	summaryMap.value = await interactionService.getOrgCommInteractionSummary({ comm_names: names })
}

async function loadFeed() {
	if (!props.programOffering) {
		feedItems.value = []
		summaryMap.value = {}
		return
	}
	loading.value = true
	errorMessage.value = ''
	actionError.value = ''
	try {
		const response = await getActivityCommunications({
			activity_program_offering: props.programOffering,
			activity_student_group: props.activeSection || null,
			start: 0,
			page_length: 12,
		})
		feedItems.value = response.items || []
		await loadSummaries(feedItems.value)
	} catch (error) {
		const message = error instanceof Error ? error.message : String(error || '')
		errorMessage.value = message || 'Could not load activity updates.'
	} finally {
		loading.value = false
	}
}

async function react(commName: string, code: ReactionCode) {
	actionError.value = ''
	try {
		await interactionService.reactToOrgCommunication({
			org_communication: commName,
			reaction_code: code,
			surface: 'Portal Feed',
		})
		await loadSummaries(feedItems.value)
	} catch (error) {
		const message = error instanceof Error ? error.message : String(error || '')
		actionError.value = message || 'Could not record reaction.'
	}
}

async function openThread(item: OrgCommunicationListItem) {
	actionError.value = ''
	if (!canComment(item)) {
		actionError.value = 'Comments are not enabled for this update.'
		return
	}
	selectedComm.value = item
	threadOpen.value = true
	commentValue.value = ''
	threadRows.value = []
	threadLoading.value = true
	try {
		threadRows.value = await interactionService.getCommunicationThread({
			org_communication: item.name,
			limit_start: 0,
			limit_page_length: 200,
		})
	} catch (error) {
		const message = error instanceof Error ? error.message : String(error || '')
		actionError.value = message || 'Could not load comment thread.'
	} finally {
		threadLoading.value = false
	}
}

function closeThread() {
	threadOpen.value = false
	selectedComm.value = null
	commentValue.value = ''
	threadRows.value = []
}

function onCommentUpdate(value: string) {
	commentValue.value = value
}

async function submitComment() {
	actionError.value = ''
	const comm = selectedComm.value
	if (!comm) {
		actionError.value = 'Select a communication first.'
		return
	}
	const note = commentValue.value.trim()
	if (!note) {
		actionError.value = 'Please add a comment before posting.'
		return
	}
	commentSubmitting.value = true
	try {
		await interactionService.postOrgCommunicationComment({
			org_communication: comm.name,
			note,
			surface: 'Portal Feed',
		})
		commentValue.value = ''
		threadRows.value = await interactionService.getCommunicationThread({
			org_communication: comm.name,
			limit_start: 0,
			limit_page_length: 200,
		})
		await loadSummaries(feedItems.value)
		toast.success('Comment posted.')
	} catch (error) {
		const message = error instanceof Error ? error.message : String(error || '')
		actionError.value = message || 'Could not post comment.'
	} finally {
		commentSubmitting.value = false
	}
}

watch(
	() => [props.programOffering, props.activeSection],
	() => {
		void loadFeed()
	},
	{ immediate: true }
)
</script>
