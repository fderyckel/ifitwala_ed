<!-- ifitwala_ed/ui-spa/src/pages/admissions/ApplicantMessages.vue -->

<template>
	<div class="admissions-page">
		<header class="page-header">
			<div class="page-header__intro">
				<h1 class="type-h1 text-ink">{{ __('Messages') }}</h1>
				<p class="type-meta text-ink/70">
					{{ __('Contact admissions directly from your application workspace.') }}
				</p>
			</div>
		</header>

		<div v-if="loading" class="card-panel px-4 py-4">
			<p class="type-caption text-ink/65">{{ __('Loading messages...') }}</p>
		</div>

		<div v-else-if="error" class="if-banner if-banner--danger">
			<p class="if-banner__title type-body-strong">{{ __('Unable to load messages') }}</p>
			<p class="if-banner__body mt-1 whitespace-pre-wrap type-caption">{{ error }}</p>
			<button type="button" class="if-button if-button--secondary mt-3" @click="loadMessages">
				{{ __('Try again') }}
			</button>
		</div>

		<div v-else class="space-y-4">
			<div class="paper-card px-4 py-4">
				<div class="mb-3 flex items-center justify-between">
					<p class="type-body-strong text-ink">{{ __('Conversation') }}</p>
					<p v-if="unreadCount > 0" class="chip chip-warm">
						{{ __('Unread: {0}').replace('{0}', String(unreadCount)) }}
					</p>
				</div>

				<div v-if="!messages.length" class="card-surface-muted rounded-xl border-dashed px-4 py-4">
					<p class="type-caption text-ink/65">
						{{ __('No messages yet. Send a message if you need help from admissions.') }}
					</p>
				</div>

				<div v-else class="space-y-3">
					<article
						v-for="message in messages"
						:key="message.name"
						class="if-feed-card px-3 py-2"
						:class="messageClass(message.direction)"
					>
						<div class="flex items-center justify-between gap-3">
							<p class="type-caption text-ink/65">{{ message.full_name || message.user }}</p>
							<p class="type-caption text-ink/55">{{ formatDate(message.created_at) }}</p>
						</div>
						<p class="mt-1 whitespace-pre-wrap type-body text-ink">
							{{ message.body }}
						</p>
					</article>
				</div>
			</div>

			<div class="paper-card px-4 py-4">
				<p class="type-body-strong text-ink">{{ __('Send a message') }}</p>
				<textarea
					v-model="draftBody"
					rows="4"
					maxlength="300"
					class="mt-2 w-full rounded-xl border border-border/70 px-3 py-2 text-sm text-ink focus:border-canopy focus:outline-none focus:ring-2 focus:ring-canopy/25"
					:placeholder="__('Write your message here...')"
				/>
				<p class="mt-1 type-caption text-ink/55">
					{{ __('{0} / 300').replace('{0}', String(draftBody.length)) }}
				</p>
				<div v-if="sendError" class="if-banner if-banner--danger mt-3">
					<p class="if-banner__body type-caption">{{ sendError }}</p>
				</div>
				<div class="mt-3 flex justify-end">
					<button
						type="button"
						class="if-button if-button--primary"
						:disabled="sending || !canSend"
						@click="sendMessage"
					>
						{{ sending ? __('Sending...') : __('Send') }}
					</button>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';

import { useAdmissionsSession } from '@/composables/useAdmissionsSession';
import { __ } from '@/lib/i18n';
import { createAdmissionsService } from '@/lib/services/admissions/admissionsService';
import { uiSignals, SIGNAL_ADMISSIONS_PORTAL_INVALIDATE } from '@/lib/uiSignals';
import type { ApplicantMessage } from '@/types/contracts/admissions/types';

const { currentApplicantName } = useAdmissionsSession();
const service = createAdmissionsService();

const loading = ref(false);
const error = ref<string | null>(null);
const sendError = ref<string | null>(null);
const sending = ref(false);
const draftBody = ref('');
const messages = ref<ApplicantMessage[]>([]);
const unreadCount = ref(0);

const applicantName = computed(() => currentApplicantName.value || '');
const canSend = computed(() => Boolean(applicantName.value && draftBody.value.trim().length));

function messageClass(direction: ApplicantMessage['direction']) {
	if (direction === 'ApplicantToStaff') {
		return 'border-canopy/40 bg-canopy/5';
	}
	return 'border-border/70 bg-surface/40';
}

function formatDate(value?: string | null) {
	if (!value) return '-';
	const date = new Date(value);
	if (Number.isNaN(date.getTime())) return value;
	return date.toLocaleString();
}

async function loadMessages() {
	if (!applicantName.value) {
		messages.value = [];
		unreadCount.value = 0;
		return;
	}
	loading.value = true;
	error.value = null;
	try {
		const payload = await service.getMessages({
			context_doctype: 'Student Applicant',
			context_name: applicantName.value,
			limit_start: 0,
			limit: 120,
		});
		messages.value = payload.messages || [];
		const unread = Number(payload.unread_count || 0);
		unreadCount.value = unread;
		if (unread > 0) {
			await service.markMessagesRead({
				context_doctype: 'Student Applicant',
				context_name: applicantName.value,
			});
			unreadCount.value = 0;
		}
	} catch (err) {
		error.value = err instanceof Error ? err.message : __('Unable to load messages.');
	} finally {
		loading.value = false;
	}
}

async function sendMessage() {
	if (!applicantName.value) {
		sendError.value = __('Applicant context is unavailable.');
		return;
	}
	const body = draftBody.value.trim();
	if (!body) {
		sendError.value = __('Please write a message before sending.');
		return;
	}

	sendError.value = null;
	sending.value = true;
	try {
		await service.sendMessage({
			context_doctype: 'Student Applicant',
			context_name: applicantName.value,
			body,
			applicant_visible: 1,
			client_request_id: `admissions_message_${Date.now()}_${Math.random().toString(16).slice(2)}`,
		});
		draftBody.value = '';
	} catch (err) {
		sendError.value = err instanceof Error ? err.message : __('Unable to send message.');
	} finally {
		sending.value = false;
	}
}

let unsubscribe: (() => void) | null = null;

onMounted(async () => {
	await loadMessages();
	unsubscribe = uiSignals.subscribe(SIGNAL_ADMISSIONS_PORTAL_INVALIDATE, () => {
		loadMessages();
	});
});

onBeforeUnmount(() => {
	if (unsubscribe) unsubscribe();
});
</script>
