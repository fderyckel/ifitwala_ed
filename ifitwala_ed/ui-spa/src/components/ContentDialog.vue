<!-- ifitwala_ed/ui-spa/src/components/ContentDialog.vue -->
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
							<div v-html="contentHtml"></div>
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
								<span class="text-[10px] text-slate-token/60">
									({{ commentCount }})
								</span>
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
								:on-react="(code) => $emit('react', code)"
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
import { computed } from 'vue'
import { Button, FeatherIcon } from 'frappe-ui'
import { getInteractionStats } from '@/utils/interactionStats'
import type { InteractionSummary } from '@/types/morning_brief'
import type { ReactionCode } from '@/types/interactions'
import InteractionEmojiChips from '@/components/InteractionEmojiChips.vue'

defineOptions({
	inheritAttrs: false
})

const props = defineProps<{
	modelValue: boolean
	title?: string
	subtitle?: string
	content?: string
	image?: string
	imageFallback?: string
	badge?: string
	interaction?: InteractionSummary
	showInteractions?: boolean
	showComments?: boolean
}>()

const emit = defineEmits<{
	'update:modelValue': [boolean]
	acknowledge: []
	'open-comments': []
	react: [ReactionCode]
}>()

const hasHeaderContent = computed(
	() => !!(props.title || props.subtitle || props.image || props.imageFallback || props.badge)
)

const isOpen = computed({
	get: () => props.modelValue,
	set: (value: boolean) => emit('update:modelValue', value)
})

const interaction = computed<InteractionSummary>(() => ({
  counts: {},
  self: null,
  reaction_counts: {},
  reactions_total: 0,
  comments_total: 0,
  ...(props.interaction ?? {})
}))

const stats = computed(() => getInteractionStats(interaction.value))

// HTML straight-through from Org Communication.message
const contentHtml = computed(() => props.content || '')

// Comment count = thread entries (Comment + Question)
const commentCount = computed(() => stats.value.comments_total ?? 0)


</script>
