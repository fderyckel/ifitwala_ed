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
				<div class="if-overlay__backdrop" @click="emitClose('backdrop')" />
			</TransitionChild>

			<div class="if-overlay__wrap" @click.self="emitClose('backdrop')">
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
									@click="emitClose('programmatic')"
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
								@click="emitClose('programmatic')"
							>
								Close
							</button>
							<RouterLink
								:to="gradebookTarget"
								class="rounded-full bg-jacaranda px-5 py-2 type-button-label text-white shadow-soft"
								@click="emitClose('programmatic')"
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
import { computed, onBeforeUnmount, watch } from 'vue';
import { RouterLink } from 'vue-router';
import { Dialog, DialogPanel, TransitionChild, TransitionRoot } from '@headlessui/vue';

type CloseReason = 'backdrop' | 'esc' | 'programmatic';

const props = defineProps<{
	open: boolean;
	zIndex?: number;
	overlayId?: string | null;
	title: string;
	gradebookQuery?: {
		student_group?: string | null;
		task?: string | null;
		school?: string | null;
		academic_year?: string | null;
		program?: string | null;
		course?: string | null;
	};
}>();

const emit = defineEmits<{
	(e: 'close', reason: CloseReason): void;
	(e: 'after-leave'): void;
}>();

const overlayStyle = computed(() => ({ zIndex: props.zIndex ?? 60 }));
const gradebookTarget = computed(() => ({
	name: 'staff-gradebook',
	query: Object.fromEntries(
		Object.entries({
			student_group: props.gradebookQuery?.student_group || null,
			task: props.gradebookQuery?.task || null,
			school: props.gradebookQuery?.school || null,
			academic_year: props.gradebookQuery?.academic_year || null,
			program: props.gradebookQuery?.program || null,
			course: props.gradebookQuery?.course || null,
		}).filter(([, value]) => value)
	),
}));

function emitClose(reason: CloseReason = 'programmatic') {
	emit('close', reason);
}

function onDialogClose(_payload: unknown) {
	// OverlayHost owns close enforcement.
}

function onKeydown(event: KeyboardEvent) {
	if (!props.open) return;
	if (event.key === 'Escape') emitClose('esc');
}

watch(
	() => props.open,
	value => {
		if (value) document.addEventListener('keydown', onKeydown, true);
		else document.removeEventListener('keydown', onKeydown, true);
	},
	{ immediate: true }
);

onBeforeUnmount(() => {
	document.removeEventListener('keydown', onKeydown, true);
});
</script>
