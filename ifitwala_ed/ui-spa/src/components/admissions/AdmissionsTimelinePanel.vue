<template>
	<section
		class="admissions-timeline-panel"
		data-testid="admissions-timeline-panel"
		:aria-label="__('Admissions timeline')"
	>
		<header class="admissions-timeline-panel__header">
			<div class="min-w-0">
				<p class="type-overline text-slate-token/70">{{ __('Timeline') }}</p>
				<h3 class="type-h3 text-ink">
					{{ timeline?.context?.label || __('Admissions relationship') }}
				</h3>
				<p v-if="latestLabel" class="type-caption text-slate-token/70">
					{{ __('Latest {0}', [latestLabel]) }}
				</p>
			</div>
			<div class="admissions-timeline-panel__header-actions">
				<span
					v-if="timeline?.summary?.needs_reply"
					class="admissions-timeline-pill admissions-timeline-pill--reply"
				>
					{{ __('Needs reply') }}
				</span>
				<button
					type="button"
					class="if-button if-button--quiet"
					:disabled="loading"
					@click="emit('refresh')"
				>
					{{ loading ? __('Loading…') : __('Refresh') }}
				</button>
			</div>
		</header>

		<div v-if="error" role="alert" class="admissions-timeline-panel__error">
			{{ error }}
		</div>

		<div v-if="loading && !timeline" class="admissions-timeline-panel__empty">
			{{ __('Loading admissions timeline…') }}
		</div>

		<template v-else-if="timeline">
			<div v-if="ladderSteps.length" class="admissions-timeline-ladder">
				<div
					v-for="step in ladderSteps"
					:key="step.id"
					class="admissions-timeline-ladder__step"
					:class="`admissions-timeline-ladder__step--${step.state}`"
				>
					<span class="admissions-timeline-ladder__dot" />
					<span>{{ step.label }}</span>
				</div>
			</div>

			<div v-if="timeline.actions?.length" class="admissions-timeline-actions">
				<button
					v-for="action in timeline.actions"
					:key="`${action.id}-${action.target || 'context'}`"
					type="button"
					:data-testid="`admissions-timeline-action-${action.id}`"
					class="admissions-timeline-action"
					:class="{ 'admissions-timeline-action--disabled': !action.enabled }"
					:disabled="!action.enabled"
					:title="
						action.enabled
							? actionLabel(action.id)
							: action.disabled_reason || actionLabel(action.id)
					"
					@click="emit('action', action)"
				>
					<span>{{ action.label || actionLabel(action.id) }}</span>
					<small v-if="!action.enabled && action.disabled_reason">{{
						action.disabled_reason
					}}</small>
				</button>
			</div>

			<ol v-if="timeline.items?.length" class="admissions-timeline-items">
				<li v-for="item in timeline.items" :key="item.id" class="admissions-timeline-item">
					<div
						class="admissions-timeline-item__marker"
						:class="`admissions-timeline-item__marker--${item.kind}`"
					/>
					<div class="admissions-timeline-item__body">
						<div class="admissions-timeline-item__heading">
							<div class="min-w-0">
								<p class="type-overline text-slate-token/70">{{ kindLabel(item.kind) }}</p>
								<h4 class="type-body-strong text-ink">{{ item.title }}</h4>
							</div>
							<time v-if="item.occurred_at" class="type-caption text-slate-token/70">
								{{ formatDateTime(item.occurred_at) }}
							</time>
						</div>
						<p v-if="item.summary" class="admissions-timeline-item__summary">{{ item.summary }}</p>
						<div class="admissions-timeline-item__footer">
							<span v-if="item.actor" class="type-caption text-slate-token/70">
								{{ actorLabel(item.actor) }}
							</span>
							<button
								v-if="safeOpenUrl(item.open_url)"
								type="button"
								:data-testid="`admissions-timeline-open-${item.id}`"
								class="admissions-timeline-item__open"
								@click="emit('open', item)"
							>
								{{ __('Open') }}
							</button>
						</div>
					</div>
				</li>
			</ol>

			<div v-else class="admissions-timeline-panel__empty">
				{{ __('No admissions timeline items yet.') }}
			</div>

			<p v-if="timeline.has_more" class="type-caption text-slate-token/70">
				{{ __('More timeline items are available after the current page limit.') }}
			</p>
		</template>
	</section>
</template>

<script setup lang="ts">
import { computed } from 'vue';

import { __ } from '@/lib/i18n';
import type {
	AdmissionsTimelineAction,
	AdmissionsTimelineContext,
	AdmissionsTimelineItem,
} from '@/types/contracts/admissions_timeline/get_admissions_timeline_context';

const props = defineProps<{
	timeline?: AdmissionsTimelineContext | null;
	loading?: boolean;
	error?: string | null;
}>();

const emit = defineEmits<{
	(e: 'refresh'): void;
	(e: 'action', action: AdmissionsTimelineAction): void;
	(e: 'open', item: AdmissionsTimelineItem): void;
}>();

const ladderSteps = computed(() => props.timeline?.summary?.completion_ladder || []);
const latestLabel = computed(() => formatDateTime(props.timeline?.summary?.latest_at || null));

function actionLabel(actionId: string) {
	return String(actionId || '')
		.split('_')
		.filter(Boolean)
		.map(part => part.charAt(0).toUpperCase() + part.slice(1))
		.join(' ');
}

function kindLabel(kind: string) {
	const value = String(kind || '').trim();
	if (value === 'intake') return __('Intake');
	if (value === 'message') return __('Message');
	if (value === 'touchpoint') return __('Touchpoint');
	if (value === 'visit') return __('Visit');
	if (value === 'applicant') return __('Applicant');
	if (value === 'offer') return __('Offer');
	if (value === 'deposit') return __('Deposit');
	if (value === 'enrollment') return __('Enrollment');
	if (!value) return __('Admissions');
	return actionLabel(value);
}

function actorLabel(actor: string) {
	const value = String(actor || '').trim();
	if (value === 'Inbound') return __('Family');
	if (value === 'Outbound') return __('Staff');
	if (value === 'System') return __('System');
	if (value === 'applicant') return __('Applicant');
	if (value === 'staff') return __('Staff');
	return value;
}

function formatDateTime(value?: string | null) {
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

function safeOpenUrl(url?: string | null) {
	const value = String(url || '').trim();
	if (!value || value.startsWith('/private/')) return '';
	return value;
}
</script>

<style scoped>
.admissions-timeline-panel {
	display: grid;
	gap: 1rem;
	min-width: 0;
}

.admissions-timeline-panel__header {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: 1rem;
}

.admissions-timeline-panel__header h3,
.admissions-timeline-item h4,
.admissions-timeline-item__summary {
	overflow-wrap: anywhere;
}

.admissions-timeline-panel__header-actions {
	display: flex;
	flex-wrap: wrap;
	justify-content: flex-end;
	gap: 0.5rem;
}

.admissions-timeline-pill,
.admissions-timeline-action {
	border: 1px solid rgb(226 232 240);
	border-radius: 999px;
	background: rgb(248 250 252);
	color: rgb(var(--slate-rgb));
	font-size: 0.75rem;
	font-weight: 750;
	line-height: 1.25;
	padding: 0.3rem 0.65rem;
}

.admissions-timeline-pill--reply {
	border-color: rgb(var(--flame-rgb) / 0.35);
	background: rgb(var(--flame-rgb) / 0.1);
	color: rgb(var(--flame-rgb));
}

.admissions-timeline-panel__error,
.admissions-timeline-panel__empty {
	border-radius: 0.5rem;
	font-size: 0.875rem;
	line-height: 1.45;
	padding: 0.75rem;
}

.admissions-timeline-panel__error {
	border: 1px solid rgb(252 165 165);
	background: rgb(254 242 242);
	color: rgb(185 28 28);
}

.admissions-timeline-panel__empty {
	border: 1px dashed rgb(203 213 225);
	background: rgb(248 250 252);
	color: rgb(var(--slate-rgb));
}

.admissions-timeline-ladder {
	display: flex;
	gap: 0.45rem;
	overflow-x: auto;
	padding-bottom: 0.15rem;
}

.admissions-timeline-ladder__step {
	display: inline-flex;
	flex: 0 0 auto;
	align-items: center;
	gap: 0.35rem;
	border: 1px solid rgb(226 232 240);
	border-radius: 999px;
	background: white;
	color: rgb(var(--slate-rgb));
	font-size: 0.72rem;
	font-weight: 750;
	line-height: 1.2;
	padding: 0.35rem 0.6rem;
}

.admissions-timeline-ladder__dot {
	width: 0.45rem;
	height: 0.45rem;
	border-radius: 999px;
	background: rgb(203 213 225);
}

.admissions-timeline-ladder__step--done {
	border-color: rgb(var(--canopy-rgb) / 0.35);
	background: rgb(var(--canopy-rgb) / 0.08);
	color: rgb(var(--canopy-rgb));
}

.admissions-timeline-ladder__step--done .admissions-timeline-ladder__dot {
	background: rgb(var(--canopy-rgb));
}

.admissions-timeline-ladder__step--current {
	border-color: rgb(var(--jacaranda-rgb) / 0.35);
	background: rgb(var(--jacaranda-rgb) / 0.08);
	color: rgb(var(--jacaranda-rgb));
}

.admissions-timeline-ladder__step--current .admissions-timeline-ladder__dot {
	background: rgb(var(--jacaranda-rgb));
}

.admissions-timeline-actions {
	display: flex;
	flex-wrap: wrap;
	gap: 0.45rem;
}

.admissions-timeline-action {
	text-align: left;
}

.admissions-timeline-action:not(:disabled):hover {
	border-color: rgb(var(--canopy-rgb) / 0.45);
	color: rgb(var(--canopy-rgb));
}

.admissions-timeline-action--disabled {
	cursor: not-allowed;
	opacity: 0.66;
}

.admissions-timeline-action small {
	display: block;
	max-width: 14rem;
	font-weight: 600;
	margin-top: 0.18rem;
	white-space: normal;
}

.admissions-timeline-items {
	display: grid;
	gap: 0.75rem;
	margin: 0;
	padding: 0;
	list-style: none;
}

.admissions-timeline-item {
	display: grid;
	grid-template-columns: auto minmax(0, 1fr);
	gap: 0.75rem;
}

.admissions-timeline-item__marker {
	width: 0.75rem;
	height: 0.75rem;
	border-radius: 999px;
	background: rgb(var(--sky-rgb));
	margin-top: 0.55rem;
	box-shadow: 0 0 0 0.25rem rgb(var(--sky-rgb) / 0.14);
}

.admissions-timeline-item__marker--message {
	background: rgb(var(--jacaranda-rgb));
	box-shadow: 0 0 0 0.25rem rgb(var(--jacaranda-rgb) / 0.14);
}

.admissions-timeline-item__marker--visit,
.admissions-timeline-item__marker--offer,
.admissions-timeline-item__marker--deposit {
	background: rgb(var(--canopy-rgb));
	box-shadow: 0 0 0 0.25rem rgb(var(--canopy-rgb) / 0.14);
}

.admissions-timeline-item__marker--enrollment {
	background: rgb(var(--leaf-rgb));
	box-shadow: 0 0 0 0.25rem rgb(var(--leaf-rgb) / 0.16);
}

.admissions-timeline-item__body {
	min-width: 0;
	border: 1px solid rgb(226 232 240);
	border-radius: 0.5rem;
	background: white;
	padding: 0.75rem;
}

.admissions-timeline-item__heading,
.admissions-timeline-item__footer {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: 0.75rem;
}

.admissions-timeline-item__summary {
	color: rgb(var(--slate-rgb));
	font-size: 0.875rem;
	line-height: 1.45;
	margin-top: 0.45rem;
}

.admissions-timeline-item__footer {
	align-items: center;
	margin-top: 0.65rem;
}

.admissions-timeline-item__open {
	color: rgb(var(--canopy-rgb));
	font-size: 0.78rem;
	font-weight: 750;
}

@media (max-width: 720px) {
	.admissions-timeline-panel__header,
	.admissions-timeline-item__heading,
	.admissions-timeline-item__footer {
		align-items: stretch;
		flex-direction: column;
	}
}
</style>
