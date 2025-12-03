<!-- ifitwala_ed/ui-spa/src/components/ContentDialog.vue -->
<template>
	<Dialog
		class="content-dialog"
		v-model="isOpen"
		:options="dialogOptions"
	>
		<template #body-content>
			<div class="paper-card flex flex-col gap-5 bg-white p-5 text-ink">
				<div class="flex items-start justify-between gap-4 border-b border-border/70 pb-3">
					<div class="flex items-start gap-3">
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
							<p
								v-if="subtitle"
								class="type-h2 text-ink"
							>
								{{ subtitle }}
							</p>

							<div class="flex items-center gap-2">
								<span
									v-if="badge"
									class="inline-flex items-center rounded-full border border-border/70 bg-surface-soft px-2.5 py-0.5 text-[11px] font-semibold text-slate-token/85"
								>
									{{ badge }}
								</span>
							</div>
						</div>
					</div>

					<button
						@click="isOpen = false"
						class="group -mr-1 rounded-full border border-border/80 bg-surface-soft p-2 text-slate-token/70 transition hover:border-jacaranda/40 hover:text-jacaranda focus:outline-none focus-visible:ring-2 focus-visible:ring-jacaranda/40"
						aria-label="Close"
					>
						<FeatherIcon
							name="x"
							class="h-4 w-4"
						/>
					</button>
				</div>

				<div class="prose prose-sm max-w-none text-slate-token/90">
					<div v-html="cleanedContent"></div>
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

<script setup>
import { computed } from 'vue'
import { Dialog, Button, FeatherIcon } from 'frappe-ui'

defineOptions({
	inheritAttrs: false
})

const props = defineProps({
	modelValue: {
		type: Boolean,
		required: true
	},
	subtitle: {
		type: String,
		default: ''
	},
	content: {
		type: String,
		default: ''
	},
	image: {
		type: String,
		default: ''
	},
	imageFallback: {
		type: String,
		default: ''
	},
	badge: {
		type: String,
		default: ''
	}
})

const emit = defineEmits(['update:modelValue'])

const isOpen = computed({
	get: () => props.modelValue,
	set: (value) => emit('update:modelValue', value)
})

const dialogOptions = {
	size: 'xl',
	title: null
}

const cleanedContent = computed(() => {
	if (!props.content) return ''
	if (!props.subtitle) return props.content

	const pattern = new RegExp(`^\\s*${escapeRegExp(props.subtitle)}`, 'i')
	return props.content.replace(pattern, '').trim()
})

function escapeRegExp(string) {
	return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}
</script>
