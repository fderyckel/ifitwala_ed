<!-- ifitwala_ed/ui-spa/src/components/focus/FocusRouterOverlay.vue -->
<template>
	<TransitionRoot
		as="template"
		:show="open"
		@after-leave="emitAfterLeave"
	>
		<Dialog
			as="div"
			class="if-overlay if-overlay--focus"
			:style="{ zIndex }"
			@close="emitClose"
		>
			<!-- Backdrop -->
			<TransitionChild
				as="template"
				enter="if-overlay__fade-enter"
				enter-from="if-overlay__fade-from"
				enter-to="if-overlay__fade-to"
				leave="if-overlay__fade-leave"
				leave-from="if-overlay__fade-to"
				leave-to="if-overlay__fade-from"
			>
				<div class="if-overlay__backdrop" />
			</TransitionChild>

			<!-- Panel -->
			<TransitionChild
				as="template"
				enter="if-overlay__panel-enter"
				enter-from="if-overlay__panel-from"
				enter-to="if-overlay__panel-to"
				leave="if-overlay__panel-leave"
				leave-from="if-overlay__panel-to"
				leave-to="if-overlay__panel-from"
			>
				<DialogPanel class="if-overlay__panel if-overlay__panel--md">
					<!-- Header -->
					<header class="if-overlay__header">
						<div class="min-w-0">
							<h2 class="type-h3 text-ink truncate">
								{{ headerTitle }}
							</h2>
							<p v-if="headerSubtitle" class="type-caption text-slate-token/70 truncate">
								{{ headerSubtitle }}
							</p>
						</div>
						<button
							type="button"
							class="if-overlay__close"
							@click="emitClose"
						>
							<span class="sr-only">Close</span>
							✕
						</button>
					</header>

					<!-- Body -->
					<section class="if-overlay__body">
						<!-- Loading -->
						<div v-if="loading" class="py-12 flex justify-center">
							<div class="if-spinner" />
						</div>

						<!-- Error / Missing -->
						<div v-else-if="error" class="py-12 text-center">
							<p class="type-body text-slate-token/70">
								This item is no longer available.
							</p>
						</div>

						<!-- Routed content -->
						<component
							v-else
							:is="resolvedComponent"
							:log="context.log"
							:follow_ups="context.follow_ups"
							:mode="context.mode"
							@close="emitClose"
						/>
					</section>
				</DialogPanel>
			</TransitionChild>
		</Dialog>
	</TransitionRoot>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
	Dialog,
	DialogPanel,
	TransitionChild,
	TransitionRoot,
} from '@headlessui/vue'
import { createResource } from 'frappe-ui'

// Workflow-owned body component
import StudentLogFollowUpOverlay from '@/components/student/StudentLogFollowUpOverlay.vue'

const props = defineProps<{
	focusItemId: string
	open: boolean
	zIndex?: number
}>()

const emit = defineEmits<{
	(e: 'close'): void
	(e: 'after-leave'): void
}>()

const loading = ref(true)
const error = ref(false)
const context = ref<any>(null)

const fetchContext = createResource({
	url: 'ifitwala_ed.api.focus.get_context',
	auto: false,
})

onMounted(async () => {
	try {
		loading.value = true
		const res = await fetchContext.submit({
			focus_item_id: props.focusItemId,
		})
		context.value = res
	} catch (e) {
		error.value = true
	} finally {
		loading.value = false
	}
})

const resolvedComponent = computed(() => {
	if (!context.value) return null
	switch (context.value.action_type) {
		case 'student_log.follow_up.act.submit':
		case 'student_log.follow_up.review.decide':
			return StudentLogFollowUpOverlay
		default:
			return null
	}
})

const headerTitle = computed(() => {
	if (!context.value) return ''
	switch (context.value.action_type) {
		case 'student_log.follow_up.act.submit':
			return 'Follow up'
		case 'student_log.follow_up.review.decide':
			return 'Review outcome'
		default:
			return 'Action'
	}
})

const headerSubtitle = computed(() => {
	return context.value?.log?.student_name || null
})

function emitClose() {
	emit('close')
}

function emitAfterLeave() {
	emit('after-leave')
}
</script>

