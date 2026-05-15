<!-- ifitwala_ed/ui-spa/src/components/CommentThreadDrawer.vue -->
<!--
  CommentThreadDrawer.vue
  Slide-out drawer for viewing and replying to comment threads on generic documents/communications.

  Used by:
  - MorningBriefing.vue (pages/staff/morning_brief)
  - OrgCommunicationArchive.vue (pages/staff)
-->
<template>
	<Teleport to="body">
		<TransitionRoot as="template" :show="open">
			<Dialog
				as="div"
				class="if-overlay if-overlay--drawer if-overlay--comment-thread z-[100]"
				:initialFocus="closeButtonRef"
				@close="emit('close')"
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
					<div class="if-overlay__backdrop" @click="emit('close')" />
				</TransitionChild>

				<div class="if-overlay__wrap if-overlay__wrap--drawer" @click.self="emit('close')">
					<TransitionChild
						as="template"
						enter="if-overlay__panel-enter"
						enter-from="if-overlay__panel-from"
						enter-to="if-overlay__panel-to"
						leave="if-overlay__panel-leave"
						leave-from="if-overlay__panel-to"
						leave-to="if-overlay__panel-from"
					>
						<DialogPanel
							class="if-overlay__panel if-overlay__panel--drawer-sm comment-thread__panel"
						>
							<header
								class="comment-thread__header flex items-start justify-between gap-3 border-b border-border/60 px-4 py-4"
							>
								<div class="min-w-0">
									<p class="type-overline text-ink/60">Thread</p>
									<DialogTitle class="type-h3 mt-2 text-ink">{{ title }}</DialogTitle>
								</div>
								<button
									ref="closeButtonRef"
									type="button"
									class="if-overlay__icon-button"
									aria-label="Close"
									@click="emit('close')"
								>
									<FeatherIcon name="x" class="h-4 w-4" />
								</button>
							</header>

							<section
								class="if-overlay__body comment-thread__body custom-scrollbar space-y-4 px-4 py-4"
							>
								<div v-if="loading" class="py-4 text-center">
									<LoadingIndicator />
								</div>
								<div v-else-if="!safeRows.length" class="py-8 text-center type-body text-ink/55">
									{{ emptyMessage }}
								</div>

								<div
									v-for="comment in safeRows"
									:key="comment.name || comment.id || comment.creation"
									class="flex gap-3"
								>
									<Avatar :label="comment.full_name || comment.user || 'User'" size="md" />
									<div class="flex-1 space-y-1">
										<div class="flex items-center justify-between gap-2">
											<span class="type-body-strong text-ink">
												{{ comment.full_name || comment.user || 'User' }}
											</span>
											<span class="type-caption text-ink/50">
												{{ formatTimestamp(comment.creation) }}
											</span>
										</div>
										<div
											class="rounded-lg rounded-tl-none bg-surface-soft p-3 type-body text-ink/90"
										>
											{{ comment.note }}
										</div>
									</div>
								</div>
							</section>

							<div class="comment-thread__footer border-t border-border/60 p-4">
								<div class="flex flex-col gap-2">
									<FormControl
										v-model="commentValue"
										type="textarea"
										:placeholder="placeholder"
										:rows="2"
									/>
									<div class="flex justify-end">
										<Button
											variant="solid"
											color="gray"
											:loading="submitLoading"
											:disabled="submitIsDisabled"
											@click="emit('submit')"
										>
											{{ submitLabel }}
										</Button>
									</div>
								</div>
							</div>
						</DialogPanel>
					</TransitionChild>
				</div>
			</Dialog>
		</TransitionRoot>
	</Teleport>
</template>

<script setup lang="ts">
import {
	Dialog,
	DialogPanel,
	DialogTitle,
	TransitionChild,
	TransitionRoot,
} from '@headlessui/vue';
import { computed, ref } from 'vue';
import { Avatar, Button, FeatherIcon, FormControl, LoadingIndicator } from 'frappe-ui';

type ThreadRow = {
	id?: string | number;
	name?: string;
	full_name?: string;
	user?: string;
	creation?: string | null;
	note?: string;
};

const props = withDefaults(
	defineProps<{
		open: boolean;
		title?: string;
		rows?: ThreadRow[];
		loading?: boolean;
		comment?: string;
		submitLabel?: string;
		submitLoading?: boolean;
		submitDisabled?: boolean;
		placeholder?: string;
		emptyMessage?: string;
		formatTimestamp?: (value: string | null | undefined) => string;
	}>(),
	{
		title: 'Comments',
		rows: () => [],
		submitLabel: 'Post Comment',
		submitLoading: false,
		placeholder: 'Write a comment...',
		emptyMessage: 'No comments yet. Start the conversation!',
	}
);

const emit = defineEmits<{
	(e: 'close'): void;
	(e: 'submit'): void;
	(e: 'update:comment', value: string): void;
}>();

const closeButtonRef = ref<HTMLButtonElement | null>(null);

const safeRows = computed(() => props.rows || []);

const commentValue = computed({
	get: () => props.comment ?? '',
	set: (value: string) => emit('update:comment', value),
});

const submitIsDisabled = computed(() => {
	if (props.submitDisabled !== undefined) return props.submitDisabled;
	return !commentValue.value.trim();
});

function formatTimestamp(value?: string | null) {
	if (props.formatTimestamp) return props.formatTimestamp(value);
	return value ?? '';
}
</script>

<style scoped>
.comment-thread__panel {
	background: rgb(var(--surface-strong-rgb) / 1);
	border-left: 1px solid rgb(var(--border-rgb) / 0.9);
	box-shadow: var(--shadow-overlay);
}

.comment-thread__header,
.comment-thread__body,
.comment-thread__footer {
	background: rgb(var(--surface-strong-rgb) / 1);
}
</style>
