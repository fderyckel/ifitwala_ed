<!-- ifitwala_ed/ui-spa/src/components/ContentDialog.vue -->
<template>
	<Teleport to="body">
		<TransitionRoot as="template" :show="isOpen">
			<Dialog
				as="div"
				class="if-overlay if-overlay--morning-brief-content"
				:initialFocus="closeButtonRef"
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
					<div class="if-overlay__backdrop" @click="closeDialog" />
				</TransitionChild>

				<div class="if-overlay__wrap content-dialog__wrap" @click.self="closeDialog">
					<TransitionChild
						as="template"
						enter="if-overlay__panel-enter"
						enter-from="if-overlay__panel-from"
						enter-to="if-overlay__panel-to"
						leave="if-overlay__panel-leave"
						leave-from="if-overlay__panel-to"
						leave-to="if-overlay__panel-from"
					>
						<DialogPanel class="if-overlay__panel content-dialog__panel">
							<header class="content-dialog__hero">
								<div class="content-dialog__hero-copy">
									<div class="content-dialog__title-row">
										<p class="type-overline content-dialog__eyebrow">
											{{ eyebrowLabel }}
										</p>
										<DialogTitle
											class="type-h2 content-dialog__title"
											data-testid="content-dialog-title"
										>
											{{ title || __('Detail') }}
										</DialogTitle>
									</div>

									<div v-if="hasHeaderMetadata" class="content-dialog__meta-strip">
										<span v-if="badge" class="content-dialog__badge">
											{{ badge }}
										</span>
										<span v-if="subtitle" class="content-dialog__meta-item">
											{{ subtitle }}
										</span>
										<span v-if="publishWindow" class="content-dialog__meta-item">
											<FeatherIcon name="calendar" class="h-3.5 w-3.5" />
											<span>{{ publishWindow }}</span>
										</span>
										<a
											v-if="deskHref"
											class="content-dialog__meta-link"
											:href="deskHref"
											target="_blank"
											rel="noopener"
										>
											<FeatherIcon name="external-link" class="h-3.5 w-3.5" />
											<span>{{ __('Open Org Communication in Desk') }}</span>
										</a>
									</div>
								</div>

								<div class="content-dialog__hero-meta">
									<div
										v-if="image || imageFallback"
										class="content-dialog__avatar"
										:class="{ 'content-dialog__avatar--image': !!image }"
									>
										<img v-if="image" :src="image" class="h-full w-full object-cover" alt="" />
										<span v-else>{{ imageFallback }}</span>
									</div>

									<button
										ref="closeButtonRef"
										type="button"
										class="if-overlay__icon-button"
										aria-label="Close"
										@click="closeDialog"
									>
										<FeatherIcon name="x" class="h-4 w-4" />
									</button>
								</div>
							</header>

							<section class="if-overlay__body content-dialog__body custom-scrollbar">
								<div class="content-dialog__content-card">
									<div class="prose prose-sm max-w-none text-slate-token/90">
										<div ref="contentRootEl" v-html="contentHtml" @click="onContentClick"></div>
									</div>
								</div>

								<section
									v-if="showAttachmentSection"
									class="rounded-[1.35rem] border border-border/70 bg-white/95 p-4 shadow-soft"
								>
									<div class="flex items-start gap-3">
										<div
											class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-surface-soft text-slate-token/70"
										>
											<FeatherIcon name="paperclip" class="h-4 w-4" />
										</div>
										<div class="min-w-0 flex-1">
											<p class="text-sm font-semibold text-ink">{{ __('Attachments') }}</p>
											<p class="mt-1 text-xs text-slate-token/75">
												{{
													__(
														'Preview governed files from this announcement without leaving the briefing.'
													)
												}}
											</p>
										</div>
									</div>

									<p
										v-if="attachmentsLoading"
										class="mt-4 rounded-2xl border border-dashed border-border/70 bg-surface-soft/70 px-4 py-3 text-sm text-slate-token/80"
									>
										{{ __('Loading attachments...') }}
									</p>
									<p
										v-else-if="attachmentsError"
										class="mt-4 rounded-2xl border border-flame/20 bg-flame/5 px-4 py-3 text-sm text-flame"
									>
										{{ attachmentsError }}
									</p>
									<div v-else-if="attachmentItems.length" class="mt-4">
										<CommunicationAttachmentPreviewList :attachments="attachmentItems" />
									</div>
								</section>

								<section v-if="showInteractions" class="content-dialog__interaction-panel">
									<div class="content-dialog__interaction-header">
										<div>
											<p class="text-sm font-semibold text-ink">
												{{ __('Team Responses') }}
											</p>
											<p class="mt-1 text-xs text-slate-token/75">
												{{ interactionDescription }}
											</p>
										</div>
										<div
											v-if="interaction.self"
											class="rounded-full border border-jacaranda/20 bg-jacaranda/5 px-3 py-1 text-[11px] font-semibold text-jacaranda"
										>
											{{ __('You responded') }}
										</div>
									</div>

									<div class="content-dialog__interaction-actions">
										<button
											type="button"
											class="content-dialog__action-button"
											@click="$emit('acknowledge')"
										>
											<FeatherIcon name="thumbs-up" class="h-4 w-4 text-canopy" />
											<span>{{ __('Acknowledge') }}</span>
										</button>

										<button
											v-if="showCommentsAction"
											type="button"
											class="content-dialog__action-button"
											@click="$emit('open-comments')"
										>
											<FeatherIcon name="message-circle" class="h-4 w-4 text-jacaranda" />
											<span>{{ __('Comments') }}</span>
											<span class="text-[11px] text-slate-token/60"> ({{ commentCount }}) </span>
										</button>
									</div>

									<div class="content-dialog__chips-row">
										<InteractionEmojiChips
											v-if="interaction"
											:interaction="interaction"
											:readonly="false"
											:on-react="code => $emit('react', code)"
										/>
									</div>
								</section>
							</section>

							<footer class="if-overlay__footer">
								<button type="button" class="content-dialog__footer-button" @click="closeDialog">
									{{ __('Close') }}
								</button>
							</footer>
						</DialogPanel>
					</TransitionChild>
				</div>
			</Dialog>
		</TransitionRoot>
	</Teleport>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import {
	Dialog,
	DialogPanel,
	DialogTitle,
	TransitionChild,
	TransitionRoot,
} from '@headlessui/vue';
import { FeatherIcon } from 'frappe-ui';
import { __ } from '@/lib/i18n';
import { getInteractionStats } from '@/utils/interactionStats';
import {
	extractPolicyInformLinkFromClickEvent,
	type PolicyInformLinkPayload,
} from '@/utils/policyInformLink';
import type { OrgCommunicationAttachmentRow } from '@/types/contracts/org_communication_attachments/shared';
import type { InteractionSummary } from '@/types/morning_brief';
import type { ReactionCode } from '@/types/interactions';
import CommunicationAttachmentPreviewList from '@/components/communication/CommunicationAttachmentPreviewList.vue';
import InteractionEmojiChips from '@/components/InteractionEmojiChips.vue';

defineOptions({
	inheritAttrs: false,
});

const props = defineProps<{
	modelValue: boolean;
	title?: string;
	subtitle?: string;
	content?: string;
	image?: string;
	imageFallback?: string;
	badge?: string;
	isAnnouncement?: boolean;
	deskHref?: string;
	publishWindow?: string;
	interaction?: InteractionSummary;
	showInteractions?: boolean;
	showComments?: boolean;
	attachments?: OrgCommunicationAttachmentRow[];
	attachmentsLoading?: boolean;
	attachmentsError?: string;
}>();

const emit = defineEmits<{
	'update:modelValue': [boolean];
	acknowledge: [];
	'open-comments': [];
	react: [ReactionCode];
	'policy-inform': [PolicyInformLinkPayload];
}>();

const isOpen = computed({
	get: () => props.modelValue,
	set: (value: boolean) => emit('update:modelValue', value),
});

const closeButtonRef = ref<HTMLButtonElement | null>(null);
const contentRootEl = ref<HTMLElement | null>(null);

const interaction = computed<InteractionSummary>(() => ({
	counts: {},
	self: null,
	reaction_counts: {},
	reactions_total: 0,
	comments_total: 0,
	...(props.interaction ?? {}),
}));

const stats = computed(() => getInteractionStats(interaction.value));
const contentHtml = computed(() => props.content || '');
const attachmentItems = computed<OrgCommunicationAttachmentRow[]>(() => props.attachments || []);
const commentCount = computed(() => stats.value.comments_total ?? 0);
const eyebrowLabel = computed(() =>
	props.isAnnouncement || props.showInteractions ? __('Announcement') : __('Student Log')
);
const showCommentsAction = computed(() => props.showComments !== false);
const hasHeaderMetadata = computed(() =>
	Boolean(props.badge || props.subtitle || props.publishWindow || props.deskHref)
);
const showAttachmentSection = computed(() =>
	Boolean(props.attachmentsLoading || props.attachmentsError || attachmentItems.value.length)
);
const interactionDescription = computed(() =>
	showCommentsAction.value
		? __('Acknowledge, react, or continue the discussion without leaving the briefing.')
		: __('Acknowledge or react without leaving the briefing.')
);

function closeDialog() {
	isOpen.value = false;
}

function onDialogClose(_payload: unknown) {
	// A+ rule: ignore framework close payloads and close explicitly only.
}

function onContentClick(event: MouseEvent) {
	const payload = extractPolicyInformLinkFromClickEvent(event);
	if (!payload) return;
	event.preventDefault();
	emit('policy-inform', payload);
}

function isPolicyInformHref(href: string): boolean {
	return href.startsWith('#policy-inform');
}

function isPolicyDeskHref(href: string): boolean {
	return (
		/\/(?:app|desk)\/policy-version\//i.test(href) ||
		/#.*form\/policy(?:%20|\s)+version\//i.test(href) ||
		/[?&](?:doctype=policy(?:%20|\+)+version|policy_version=|name=)/i.test(href)
	);
}

function policyVersionFromHref(href: string): string {
	const raw = String(href || '').trim();
	if (!raw) return '';

	try {
		const normalized = new URL(raw, window.location.origin);
		const policyVersionParam =
			normalized.searchParams.get('policy_version') || normalized.searchParams.get('name');
		if (policyVersionParam) return String(policyVersionParam).trim();

		const hashRaw = String(normalized.hash || '');
		const hash = hashRaw.startsWith('#') ? hashRaw.slice(1) : hashRaw;
		if (hash) {
			const formMatch = hash.match(/form\/policy(?:%20|\s)+version\/([^/?#]+)/i);
			if (formMatch?.[1]) return decodeURIComponent(formMatch[1]).trim();
			const appMatch = hash.match(/(?:app|desk)\/policy-version\/([^/?#]+)/i);
			if (appMatch?.[1]) return decodeURIComponent(appMatch[1]).trim();
		}
	} catch {
		// Fall through to regex-only parsing below.
	}

	if (raw.startsWith('#policy-inform')) {
		const query = raw.split('?', 2)[1] || '';
		return String(new URLSearchParams(query).get('policy_version') || '').trim();
	}
	const match = raw.match(/\/(?:app|desk)\/policy-version\/([^/?#]+)/i);
	if (!match || !match[1]) return '';
	try {
		return decodeURIComponent(match[1]).trim();
	} catch {
		return String(match[1] || '').trim();
	}
}

function getPolicyActionAnchors(root: HTMLElement): HTMLAnchorElement[] {
	const anchors = Array.from(root.querySelectorAll('a')) as HTMLAnchorElement[];
	return anchors.filter(anchor => {
		const href = String(anchor.getAttribute('href') || '').trim();
		const label = (anchor.textContent || '').trim().toLowerCase();
		return (
			isPolicyInformHref(href) ||
			isPolicyDeskHref(href) ||
			Boolean(String(anchor.getAttribute('data-policy-version') || '').trim()) ||
			(label.includes('policy') && (label.includes('desk') || label.includes('read')))
		);
	});
}

function decoratePolicyActionLinks() {
	const root = contentRootEl.value;
	if (!root) return;

	root.querySelectorAll('.if-policy-action-row').forEach(node => node.remove());

	const anchors = getPolicyActionAnchors(root);
	if (!anchors.length) return;

	let policyVersion = '';
	let orgCommunication = '';
	for (const anchor of anchors) {
		if (!policyVersion) {
			const href = String(anchor.getAttribute('href') || '').trim();
			policyVersion =
				String(anchor.getAttribute('data-policy-version') || '').trim() ||
				policyVersionFromHref(href);
		}
		if (!orgCommunication) {
			orgCommunication = String(anchor.getAttribute('data-org-communication') || '').trim();
		}
	}
	if (!policyVersion) return;

	for (const anchor of anchors) {
		const parent = anchor.parentElement;
		anchor.remove();
		if (parent && !parent.textContent?.trim()) {
			parent.remove();
		}
	}

	const row = document.createElement('div');
	row.className = 'if-policy-action-row not-prose mt-4 flex flex-wrap justify-end gap-2';

	const actionButtonClass =
		'inline-flex items-center rounded-full border border-jacaranda/20 bg-jacaranda/5 px-3 py-1.5 text-xs font-semibold text-jacaranda transition-colors hover:bg-jacaranda/10';

	const readPolicy = document.createElement('a');
	readPolicy.textContent = 'Read Policy';
	readPolicy.setAttribute(
		'href',
		`#policy-inform?policy_version=${encodeURIComponent(policyVersion)}`
	);
	readPolicy.setAttribute('data-policy-inform', '1');
	readPolicy.setAttribute('data-policy-version', policyVersion);
	if (orgCommunication) readPolicy.setAttribute('data-org-communication', orgCommunication);
	readPolicy.className = actionButtonClass;

	const openDesk = document.createElement('a');
	openDesk.textContent = 'Open Policy in Desk';
	openDesk.setAttribute('href', `/app/policy-version/${encodeURIComponent(policyVersion)}`);
	openDesk.setAttribute('data-policy-inform', '0');
	openDesk.setAttribute('data-policy-version', policyVersion);
	openDesk.setAttribute('target', '_blank');
	openDesk.setAttribute('rel', 'noopener');
	openDesk.className = actionButtonClass;

	row.appendChild(readPolicy);
	row.appendChild(openDesk);
	root.appendChild(row);
}

function onKeydown(event: KeyboardEvent) {
	if (!isOpen.value) return;
	if (event.key === 'Escape') closeDialog();
}

watch(
	() => [contentRootEl.value, props.modelValue, contentHtml.value],
	async ([root, open]) => {
		if (!open || !root) return;
		await nextTick();
		decoratePolicyActionLinks();
	},
	{ immediate: true }
);

onMounted(() => {
	document.addEventListener('keydown', onKeydown, true);
});

onBeforeUnmount(() => {
	document.removeEventListener('keydown', onKeydown, true);
});
</script>

<style scoped>
.content-dialog__wrap {
	align-items: center;
}

.content-dialog__panel {
	max-width: min(72rem, calc(100vw - 1.5rem));
}

.content-dialog__hero {
	display: flex;
	gap: 1rem;
	justify-content: space-between;
	padding: 1.5rem;
	border-bottom: 1px solid rgb(var(--border-rgb) / 0.65);
	background:
		radial-gradient(circle at top left, rgb(var(--jacaranda-rgb) / 0.12), transparent 32%),
		radial-gradient(circle at top right, rgb(var(--sky-rgb) / 0.18), transparent 38%),
		linear-gradient(180deg, rgb(var(--surface-rgb) / 0.98), rgb(var(--surface-strong-rgb) / 1));
}

.content-dialog__hero-copy {
	min-width: 0;
	flex: 1;
}

.content-dialog__title-row {
	display: grid;
	grid-template-columns: minmax(7.5rem, 0.34fr) minmax(0, 1fr);
	align-items: baseline;
	column-gap: 1rem;
}

.content-dialog__title {
	margin: 0;
	min-width: 0;
	color: rgb(var(--ink-rgb) / 1);
}

.content-dialog__hero-meta {
	display: flex;
	align-items: flex-start;
	gap: 0.75rem;
}

.content-dialog__eyebrow {
	color: rgb(var(--slate-rgb) / 0.75);
}

.content-dialog__meta-strip {
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	gap: 0.5rem;
	margin-top: 0.85rem;
	color: rgb(var(--slate-rgb) / 0.72);
}

.content-dialog__badge {
	display: inline-flex;
	align-items: center;
	border-radius: 9999px;
	padding: 0.35rem 0.75rem;
	font-size: 0.72rem;
	font-weight: 700;
	letter-spacing: 0.08em;
	text-transform: uppercase;
	border: 1px solid rgb(var(--jacaranda-rgb) / 0.18);
	background: rgb(var(--jacaranda-rgb) / 0.08);
	color: rgb(var(--jacaranda-rgb) / 0.95);
}

.content-dialog__meta-item,
.content-dialog__meta-link {
	display: inline-flex;
	align-items: center;
	gap: 0.4rem;
	min-height: 1.85rem;
	border-radius: 9999px;
	border: 1px solid rgb(var(--border-rgb) / 0.7);
	background: rgb(var(--surface-strong-rgb) / 0.72);
	padding: 0.35rem 0.75rem;
	font-size: 0.78rem;
	font-weight: 600;
	line-height: 1.2;
	color: rgb(var(--slate-rgb) / 0.78);
}

.content-dialog__meta-link {
	text-decoration: none;
	color: rgb(var(--canopy-rgb) / 0.95);
	transition:
		border-color 120ms ease,
		background 120ms ease,
		color 120ms ease;
}

.content-dialog__meta-link:hover {
	border-color: rgb(var(--canopy-rgb) / 0.28);
	background: rgb(var(--canopy-rgb) / 0.06);
	color: rgb(var(--canopy-rgb) / 1);
}

.content-dialog__avatar {
	display: inline-flex;
	height: 3.5rem;
	width: 3.5rem;
	align-items: center;
	justify-content: center;
	overflow: hidden;
	border-radius: 1rem;
	border: 1px solid rgb(var(--border-rgb) / 0.8);
	background: rgb(var(--surface-strong-rgb) / 1);
	box-shadow: var(--shadow-soft);
	color: rgb(var(--slate-rgb) / 0.75);
	font-size: 0.9rem;
	font-weight: 700;
}

.content-dialog__avatar--image {
	padding: 0;
}

.content-dialog__body {
	display: flex;
	flex-direction: column;
	gap: 1rem;
	padding: 1.5rem;
}

.content-dialog__content-card {
	border-radius: 1.5rem;
	border: 1px solid rgb(var(--border-rgb) / 0.72);
	background:
		radial-gradient(circle at top left, rgb(var(--sand-rgb) / 0.28), transparent 32%),
		rgb(var(--surface-strong-rgb) / 0.98);
	padding: 1.35rem;
	box-shadow: var(--shadow-soft);
}

.content-dialog__interaction-panel {
	border-radius: 1.35rem;
	border: 1px solid rgb(var(--border-rgb) / 0.72);
	background: rgb(var(--surface-rgb) / 0.92);
	padding: 1rem;
	box-shadow: var(--shadow-soft);
}

.content-dialog__interaction-header {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: 0.75rem;
}

.content-dialog__interaction-actions {
	display: flex;
	flex-wrap: wrap;
	gap: 0.75rem;
	margin-top: 1rem;
}

.content-dialog__action-button {
	display: inline-flex;
	align-items: center;
	gap: 0.5rem;
	border-radius: 9999px;
	border: 1px solid rgb(var(--border-rgb) / 0.8);
	background: rgb(var(--surface-strong-rgb) / 0.95);
	padding: 0.55rem 0.95rem;
	font-size: 0.82rem;
	font-weight: 600;
	color: rgb(var(--ink-rgb) / 0.92);
	transition:
		border-color 120ms ease,
		transform 120ms ease,
		background 120ms ease;
}

.content-dialog__action-button:hover {
	border-color: rgb(var(--jacaranda-rgb) / 0.35);
	background: rgb(var(--surface-strong-rgb) / 1);
	transform: translateY(-1px);
}

.content-dialog__chips-row {
	margin-top: 1rem;
}

.content-dialog__footer-button {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	border-radius: 9999px;
	border: 1px solid rgb(var(--border-rgb) / 0.85);
	background: rgb(var(--surface-strong-rgb) / 1);
	padding: 0.6rem 1.05rem;
	font-size: 0.85rem;
	font-weight: 600;
	color: rgb(var(--ink-rgb) / 0.9);
	transition:
		border-color 120ms ease,
		color 120ms ease,
		transform 120ms ease;
}

.content-dialog__footer-button:hover {
	border-color: rgb(var(--jacaranda-rgb) / 0.35);
	color: rgb(var(--jacaranda-rgb) / 0.95);
	transform: translateY(-1px);
}

@media (max-width: 767px) {
	.content-dialog__panel {
		max-width: calc(100vw - 1rem);
		max-height: calc(100vh - 1rem);
	}

	.content-dialog__hero {
		flex-direction: column;
		padding: 1.1rem;
	}

	.content-dialog__title-row {
		grid-template-columns: 1fr;
		row-gap: 0.35rem;
	}

	.content-dialog__hero-meta {
		align-items: center;
		justify-content: space-between;
	}

	.content-dialog__body {
		padding: 1rem;
	}

	.content-dialog__interaction-header {
		flex-direction: column;
	}
}
</style>
