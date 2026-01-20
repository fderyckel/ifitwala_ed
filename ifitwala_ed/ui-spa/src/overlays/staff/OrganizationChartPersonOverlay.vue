<!-- ui-spa/src/overlays/staff/OrganizationChartPersonOverlay.vue -->
<template>
	<TransitionRoot as="template" :show="open" @after-leave="emitAfterLeave">
		<Dialog as="div" class="if-overlay if-overlay--org-chart-person" @close="onDialogClose">
			<TransitionChild
				as="template"
				enter="if-overlay__fade-enter"
				enter-from="if-overlay__fade-from"
				enter-to="if-overlay__fade-to"
				leave="if-overlay__fade-leave"
				leave-from="if-overlay__fade-to"
				leave-to="if-overlay__fade-from"
			>
				<div class="if-overlay__backdrop" @click="emitClose('backdrop')" />
			</TransitionChild>

			<div class="if-overlay__wrap" :style="overlayStyle">
				<TransitionChild
					as="template"
					enter="if-overlay__panel-enter"
					enter-from="if-overlay__panel-from"
					enter-to="if-overlay__panel-to"
					leave="if-overlay__panel-leave"
					leave-from="if-overlay__panel-to"
					leave-to="if-overlay__panel-from"
				>
					<DialogPanel class="if-overlay__panel">
						<button
							ref="initialFocus"
							type="button"
							class="sr-only"
							aria-hidden="true"
							tabindex="0"
							@click="emitClose('programmatic')"
						>
							Close
						</button>

						<div class="flex items-start justify-between gap-3 px-5 pt-5">
							<div>
								<p class="type-overline">Organization Chart</p>
								<DialogTitle class="type-h2 text-ink mt-1">
									{{ person.name || 'Staff member' }}
								</DialogTitle>
								<p class="type-caption mt-1 text-slate-500">
									{{ person.title || 'Role not specified' }}
								</p>
							</div>

							<button
								type="button"
								class="if-overlay__icon-button"
								aria-label="Close"
								@click="emitClose('programmatic')"
							>
								<FeatherIcon name="x" class="h-4 w-4" />
							</button>
						</div>

						<div class="if-overlay__body">
							<div class="org-chart-person">
								<div class="org-chart-person__avatar">
									<img v-if="person.image" :src="person.image" :alt="person.name" />
									<span v-else class="type-caption">{{ initials }}</span>
								</div>

								<div class="space-y-2">
									<p class="type-body-strong text-ink">
										{{ person.name || 'Staff member' }}
									</p>
									<p class="type-caption text-slate-500">
										First name: {{ person.first_name || '-' }}
									</p>
									<p class="type-caption text-slate-500">
										{{ person.title || 'Role not specified' }}
									</p>
									<p class="type-caption text-slate-500 break-all">
										Email: {{ person.professional_email || '-' }}
									</p>
									<p class="type-caption text-slate-500">
										Ext: {{ person.phone_ext || '-' }}
									</p>
									<p class="type-caption text-slate-500">
										{{ person.school || '-' }} · {{ person.organization || '-' }}
									</p>
								</div>
							</div>
						</div>
					</DialogPanel>
				</TransitionChild>
			</div>
		</Dialog>
	</TransitionRoot>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Dialog, DialogPanel, DialogTitle, TransitionChild, TransitionRoot } from '@headlessui/vue'
import { FeatherIcon } from 'frappe-ui'

const props = defineProps<{
	open: boolean
	zIndex?: number
	overlayId?: string | null
	person: {
		id?: string
		name?: string | null
		first_name?: string | null
		title?: string | null
		school?: string | null
		organization?: string | null
		image?: string | null
		professional_email?: string | null
		phone_ext?: string | null
	}
}>()

type CloseReason = 'backdrop' | 'esc' | 'programmatic'

const emit = defineEmits<{
	(e: 'close', reason: CloseReason): void
	(e: 'after-leave'): void
}>()

const initialFocus = ref<HTMLElement | null>(null)
const overlayStyle = computed(() => ({ zIndex: props.zIndex ?? 60 }))

const initials = computed(() => {
	const source = (props.person.first_name || props.person.name || '').trim()
	if (!source) return '-'
	const parts = source.split(/\s+/).slice(0, 2)
	return parts.map((part) => part[0]?.toUpperCase() || '').join('') || '-'
})

function emitClose(reason: CloseReason) {
	emit('close', reason)
}

function emitAfterLeave() {
	emit('after-leave')
}

function onDialogClose() {
	emitClose('esc')
}
</script>
