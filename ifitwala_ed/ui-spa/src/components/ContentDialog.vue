<!-- ifitwala_ed/ui-spa/src/components/ContentDialog.vue -->
<!--
  ContentDialog.vue
  A generic, high-z-index dialog for displaying rich HTML content (e.g., announcements, messages)
  directly via Teleport to body, often bypassing the standard OverlayHost stack.

  Used by:
  - MorningBriefing.vue (pages/staff/morning_brief)
-->
<template>
	<teleport to="body">
		<transition name="content-dialog-fade">
			<div
				v-if="isOpen"
				class="fixed inset-0 z-[60] flex items-center justify-center bg-[color:rgb(var(--ink-rgb)/0.45)] backdrop-blur-sm"
				@click.self="isOpen = false"
			>
				<!-- SINGLE visible box -->
				<div
					class="content-card relative flex max-h-[80vh] w-full max-w-3xl flex-col gap-4 overflow-y-auto rounded-2xl bg-surface-soft p-4 text-ink shadow-strong ring-1 ring-border/60 sm:p-5"
				>
					<button
						@click="isOpen = false"
						class="absolute right-3 top-3 inline-flex h-8 w-8 items-center justify-center rounded-full border border-border/80 bg-surface-soft text-slate-token/70 transition hover:border-jacaranda/40 hover:text-jacaranda focus:outline-none focus-visible:ring-2 focus-visible:ring-jacaranda/40"
						aria-label="Close"
					>
						<FeatherIcon name="x" class="h-4 w-4" />
					</button>

					<!-- HEADER -->
					<div
						v-if="hasHeaderContent"
						class="flex items-start gap-3 border-b border-line-soft bg-surface-soft/70 pb-3 pr-8"
					>
						<div
							v-if="image || imageFallback"
							class="flex h-12 w-12 items-center justify-center rounded-xl border border-border/70 bg-surface-soft text-sm font-semibold text-slate-token/75 shadow-inner"
						>
							<img
								v-if="image"
								:src="image"
								class="h-full w-full object-cover"
								alt="Context image"
							/>
							<span v-else>
								{{ imageFallback }}
							</span>
						</div>

						<div class="flex flex-col gap-1">
							<p v-if="title" class="type-h2 text-ink">
								{{ title }}
							</p>
							<p v-if="subtitle" class="type-meta text-jacaranda">
								{{ subtitle }}
							</p>

							<div class="flex items-center gap-2">
								<span v-if="badge" class="chip">
									{{ badge }}
								</span>
							</div>
						</div>
					</div>

					<!-- BODY CONTENT: respects HTML from Org Communication.message -->
					<div class="rounded-2xl border border-line-soft bg-white/85 p-5 shadow-soft">
						<div class="prose prose-sm max-w-none text-slate-token/90">
							<div ref="contentRootEl" v-html="contentHtml" @click="onContentClick"></div>
						</div>
					</div>

					<!-- INTERACTIONS -->
					<div
						v-if="showInteractions"
						class="flex flex-col gap-2 border-t border-border/60 pt-3 text-[11px] text-slate-token/70"
					>
						<!-- Action buttons -->
						<div class="flex items-center gap-3">
							<button
								type="button"
								class="inline-flex items-center gap-1 rounded-full bg-surface-soft px-2 py-1 hover:bg-surface-soft/80"
								@click="$emit('acknowledge')"
							>
								<FeatherIcon name="thumbs-up" class="h-3 w-3 text-canopy" />
								<span>Acknowledge</span>
							</button>

							<button
								type="button"
								class="inline-flex items-center gap-1 rounded-full px-2 py-1 hover:bg-surface-soft"
								@click="$emit('open-comments')"
							>
								<FeatherIcon name="message-circle" class="h-3 w-3" />
								<span>Comments</span>
								<span class="text-[10px] text-slate-token/60"> ({{ commentCount }}) </span>
							</button>
						</div>

						<!-- Self status -->
						<div v-if="interaction.self" class="hidden text-[10px] text-jacaranda md:block">
							You responded: {{ interaction.self.intent_type || 'Commented' }}
						</div>

						<!-- Reaction summary row: shared component -->
						<div class="mt-1">
							<InteractionEmojiChips
								v-if="interaction"
								:interaction="interaction"
								:readonly="false"
								:on-react="code => $emit('react', code)"
							/>
						</div>
					</div>

					<div class="flex justify-end border-t border-border/70 pt-3">
						<Button variant="solid" label="Close" @click="isOpen = false" />
					</div>
				</div>
			</div>
		</transition>
	</teleport>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue';
import { Button, FeatherIcon } from 'frappe-ui';
import { getInteractionStats } from '@/utils/interactionStats';
import {
	extractPolicyInformLinkFromClickEvent,
	type PolicyInformLinkPayload,
} from '@/utils/policyInformLink';
import type { InteractionSummary } from '@/types/morning_brief';
import type { ReactionCode } from '@/types/interactions';
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
	interaction?: InteractionSummary;
	showInteractions?: boolean;
	showComments?: boolean;
}>();

const emit = defineEmits<{
	'update:modelValue': [boolean];
	acknowledge: [];
	'open-comments': [];
	react: [ReactionCode];
	'policy-inform': [PolicyInformLinkPayload];
}>();

const hasHeaderContent = computed(
	() => !!(props.title || props.subtitle || props.image || props.imageFallback || props.badge)
);

const isOpen = computed({
	get: () => props.modelValue,
	set: (value: boolean) => emit('update:modelValue', value),
});
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

// HTML straight-through from Org Communication.message
const contentHtml = computed(() => props.content || '');

// Comment count = thread entries (Comment + Question)
const commentCount = computed(() => stats.value.comments_total ?? 0);

function onContentClick(event: MouseEvent) {
	const target = event.target;
	if (target instanceof Element) {
		const actionButton = target.closest('[data-policy-action]');
		if (actionButton instanceof HTMLButtonElement) {
			event.preventDefault();
			const action = String(actionButton.getAttribute('data-policy-action') || '').trim();
			const href = String(actionButton.getAttribute('data-policy-href') || '').trim();
			const policyVersion =
				String(actionButton.getAttribute('data-policy-version') || '').trim() ||
				policyVersionFromHref(href);
			const orgCommunication = String(
				actionButton.getAttribute('data-org-communication') || ''
			).trim();

			if (action === 'desk' && href) {
				window.open(href, '_blank', 'noopener');
				return;
			}
			if (action === 'inform' && policyVersion) {
				emit('policy-inform', {
					policyVersion,
					orgCommunication: orgCommunication || null,
				});
				return;
			}
		}
	}

	const payload = extractPolicyInformLinkFromClickEvent(event);
	if (!payload) return;
	event.preventDefault();
	emit('policy-inform', payload);
}

function isPolicyInformHref(href: string): boolean {
	return href.startsWith('#policy-inform');
}

function isPolicyDeskHref(href: string): boolean {
	return /\/(?:app|desk)\/policy-version\//i.test(href);
}

function policyVersionFromHref(href: string): string {
	const raw = String(href || '').trim();
	if (!raw) return '';
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
		return isPolicyInformHref(href) || isPolicyDeskHref(href);
	});
}

function decoratePolicyActionLinks() {
	const root = contentRootEl.value;
	if (!root) return;

	root.querySelectorAll('.if-policy-action-row').forEach(node => node.remove());

	const anchors = getPolicyActionAnchors(root);
	if (!anchors.length) return;

	const row = document.createElement('div');
	row.className = 'if-policy-action-row mt-3 flex flex-wrap justify-end gap-2';

	for (const anchor of anchors) {
		const href = String(anchor.getAttribute('href') || '').trim();
		const isInform = isPolicyInformHref(href);
		const policyVersion =
			String(anchor.getAttribute('data-policy-version') || '').trim() ||
			policyVersionFromHref(href);
		const orgCommunication = String(anchor.getAttribute('data-org-communication') || '').trim();
		const label =
			(anchor.textContent || '').trim() || (isInform ? 'Open Policy' : 'Version in Desk');

		const button = document.createElement('button');
		button.type = 'button';
		button.className = isInform ? 'btn btn-primary' : 'btn btn-quiet';
		button.setAttribute('data-policy-action', isInform ? 'inform' : 'desk');
		button.setAttribute('data-policy-href', href);
		if (policyVersion) button.setAttribute('data-policy-version', policyVersion);
		if (orgCommunication) button.setAttribute('data-org-communication', orgCommunication);
		button.textContent = label;

		const parent = anchor.parentElement;
		anchor.remove();
		row.appendChild(button);
		if (parent && parent !== row && !parent.textContent?.trim()) {
			parent.remove();
		}
	}

	root.appendChild(row);
}

watch(
	() => [props.modelValue, contentHtml.value],
	async ([open]) => {
		if (!open) return;
		await nextTick();
		decoratePolicyActionLinks();
	},
	{ immediate: true }
);
</script>
