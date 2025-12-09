<!-- ifitwala_ed/ui-spa/src/components/ContentDialog.vue -->
<template>
	<Dialog
		class="content-dialog"
		v-model="isOpen"
		:options="dialogOptions"
	>
		<template #body-content>
				<div class="content-card relative flex flex-col gap-4 rounded-2xl bg-gradient-to-br from-white via-surface-soft to-white p-4 text-ink shadow-xl ring-1 ring-border/60 sm:p-5">
					<button
						@click="isOpen = false"
						class="absolute right-3 top-3 inline-flex h-8 w-8 items-center justify-center rounded-full border border-border/80 bg-surface-soft text-slate-token/70 transition hover:border-jacaranda/40 hover:text-jacaranda focus:outline-none focus-visible:ring-2 focus-visible:ring-jacaranda/40"
						aria-label="Close"
					>
						<FeatherIcon
							name="x"
							class="h-4 w-4"
						/>
					</button>

					<div v-if="hasHeaderContent" class="flex items-start gap-3 border-b border-border/60 pb-3 pr-8">
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
								<span
									v-if="badge"
									class="chip"
								>
									{{ badge }}
								</span>
							</div>
						</div>
					</div>

				<div class="prose prose-sm max-w-none text-slate-token/90">
					<div v-html="cleanedContent"></div>
				</div>

				<div
					v-if="showInteractions"
					class="flex items-center justify-between border-t border-border/60 pt-3 text-[11px] text-slate-token/70"
				>
					<div class="flex items-center gap-3">
						<button
							type="button"
							class="inline-flex items-center gap-1 rounded-full bg-surface-soft px-2 py-1 hover:bg-surface-soft/80"
							@click="$emit('acknowledge')"
						>
							<FeatherIcon name="thumbs-up" class="h-3 w-3 text-canopy" />
							<span>
								Acknowledge
								<span class="ml-1 text-[10px] text-slate-token/60">
									({{ interaction.counts?.Acknowledged || 0 }})
								</span>
							</span>
						</button>

						<button
							type="button"
							class="inline-flex items-center gap-1 rounded-full px-2 py-1 hover:bg-surface-soft"
							@click="$emit('open-comments')"
						>
							<FeatherIcon name="message-circle" class="h-3 w-3" />
							<span>Comments</span>
							<span class="text-[10px] text-slate-token/60">
								({{ interaction.counts?.Question || 0 }})
							</span>
						</button>
					</div>

					<div v-if="interaction.self" class="hidden text-[10px] text-jacaranda md:block">
						You responded: {{ interaction.self.intent_type || 'Commented' }}
					</div>
				</div>

				<div class="flex justify-end border-t border-border/70 pt-3">
					<Button
						variant="solid"
						label="Close"
						@click="isOpen = false"
					/>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Dialog, Button, FeatherIcon } from 'frappe-ui'
import type { InteractionSummary } from '@/types/morning_brief'

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
}>()

const emit = defineEmits(['update:modelValue', 'acknowledge', 'open-comments'])

const hasHeaderContent = computed<boolean>(() => !!(props.title || props.subtitle || props.image || props.imageFallback || props.badge))

const isOpen = computed<boolean>({
	get: () => props.modelValue,
	set: (value) => emit('update:modelValue', value)
})

const interaction = computed<InteractionSummary>(() => props.interaction ?? { counts: {}, self: null })

const dialogOptions: { size: 'xl'; title: null } = {
	size: 'xl',
	title: null
}

const cleanedContent = computed<string>(() => {
	if (!props.content) return ''
	if (!props.subtitle) return props.content

	const pattern = new RegExp(`^\\s*${escapeRegExp(props.subtitle)}`, 'i')
	return props.content.replace(pattern, '').trim()
})

function escapeRegExp(str: string): string {
	return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}
</script>
