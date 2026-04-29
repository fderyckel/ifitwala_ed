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
							<p v-else class="type-caption text-slate-token/70">
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
	</div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { FeatherIcon } from 'frappe-ui';

import { getAdmissionsInboxContext } from '@/lib/services/admissions/admissionsInboxService';
import { SIGNAL_ADMISSIONS_INBOX_INVALIDATE, uiSignals } from '@/lib/uiSignals';
import type {
	AdmissionsInboxContext,
	AdmissionsInboxQueue,
	AdmissionsInboxRow,
} from '@/types/contracts/admissions_inbox/get_admissions_inbox_context';

const DEFAULT_LIMIT = 40;

const context = ref<AdmissionsInboxContext | null>(null);
const loading = ref(false);
const error = ref<string | null>(null);
const activeQueueId = ref('needs_reply');

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
}
</style>
