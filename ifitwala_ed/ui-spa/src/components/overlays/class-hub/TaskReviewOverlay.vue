<!-- ifitwala_ed/ui-spa/src/components/overlays/class-hub/TaskReviewOverlay.vue -->
<!--
  TaskReviewOverlay.vue
  A simple confirmation/action overlay for reviewing a task.
  Directs the user to the Gradebook for detailed review.

  Used by:
  - ClassHub.vue (via OverlayHost)
-->
<template>
	<TransitionRoot :show="open" as="template" @after-leave="$emit('after-leave')">
		<Dialog
			as="div"
			class="if-overlay if-overlay--class-hub"
			:style="overlayStyle"
			@close="emitClose"
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
				<div class="if-overlay__backdrop" />
			</TransitionChild>

			<div class="if-overlay__wrap">
				<TransitionChild
					as="template"
					enter="if-overlay__panel-enter"
					enter-from="if-overlay__panel-from"
					enter-to="if-overlay__panel-to"
					leave="if-overlay__panel-leave"
					leave-from="if-overlay__panel-to"
					leave-to="if-overlay__panel-from"
				>
					<DialogPanel class="if-overlay__panel if-overlay__panel--compact">
						<div class="if-overlay__header px-6 pt-6">
							<div class="flex items-start justify-between gap-4">
								<div>
									<p class="type-overline text-slate-token/70">Task Review</p>
									<h2 class="type-h2 text-ink">{{ title }}</h2>
								</div>
								<button
									type="button"
									class="if-overlay__icon-button"
									aria-label="Close"
									@click="emitClose"
								>
									<span aria-hidden="true">x</span>
								</button>
							</div>
						</div>

						<div class="if-overlay__body space-y-4">
							<p class="type-body text-slate-token/70">
								This task is ready for review. Open the gradebook to review evidence and give
								feedback.
							</p>
						</div>

						<div class="if-overlay__footer">
							<button
								type="button"
								class="rounded-full border border-slate-200 bg-white px-4 py-2 type-button-label text-ink"
								@click="emitClose"
							>
								Close
							</button>
							<RouterLink
								:to="{ name: 'staff-gradebook' }"
								class="rounded-full bg-jacaranda px-5 py-2 type-button-label text-white shadow-soft"
								@click="emitClose"
							>
								Go to gradebook
							</RouterLink>
						</div>
					</DialogPanel>
				</TransitionChild>
			</div>
		</Dialog>
	</TransitionRoot>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { RouterLink } from 'vue-router';
import { Dialog, DialogPanel, TransitionChild, TransitionRoot } from '@headlessui/vue';

const props = defineProps<{
	open: boolean;
	zIndex?: number;
	overlayId?: string | null;
	title: string;
}>();

const emit = defineEmits<{
	(e: 'close'): void;
	(e: 'after-leave'): void;
}>();

const overlayStyle = computed(() => ({ zIndex: props.zIndex ?? 60 }));

function emitClose() {
	emit('close');
}
</script>
