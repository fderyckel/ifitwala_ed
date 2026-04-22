<template>
	<TransitionRoot as="template" :show="open" @after-leave="emit('after-leave')">
		<Dialog as="div" class="if-overlay" :style="overlayStyle" @close="onDialogClose">
			<TransitionChild
				as="template"
				enter="if-overlay__fade-enter"
				enter-from="if-overlay__fade-from"
				enter-to="if-overlay__fade-to"
				leave="if-overlay__fade-leave"
				leave-from="if-overlay__fade-to"
				leave-to="if-overlay__fade-from"
			>
				<div class="if-overlay__backdrop" @click="cancel('backdrop')" />
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
					<DialogPanel class="if-overlay__panel">
						<div class="if-overlay__header px-6 pt-6">
							<div class="min-w-0">
								<DialogTitle class="type-h2 text-ink">
									{{ __('Use these changes just for this form, or update the profile?') }}
								</DialogTitle>
								<p class="mt-1 type-caption text-ink/60">
									{{
										__(
											'Updated phone, email, or address values can stay on this form only, or become the new profile data everywhere.'
										)
									}}
								</p>
							</div>
							<button
								type="button"
								class="if-overlay__close"
								@click="cancel('programmatic')"
								aria-label="Close"
							>
								<FeatherIcon name="x" class="h-5 w-5" />
							</button>
						</div>

						<div class="if-overlay__body space-y-5 px-6 pb-6">
							<div class="rounded-2xl border border-line-soft bg-surface-soft p-4">
								<p class="type-body-strong text-ink">{{ __('Changed fields') }}</p>
								<ul class="mt-3 space-y-3">
									<li
										v-for="item in changedFields"
										:key="item.field_key"
										class="rounded-xl border border-line-soft bg-white p-3"
									>
										<p class="type-body-strong text-ink">{{ item.field_label }}</p>
										<p class="mt-1 type-caption text-ink/65">{{ __('Current value') }}</p>
										<p class="type-body text-ink/80">{{ item.before_label || '—' }}</p>
										<p class="mt-2 type-caption text-ink/65">{{ __('Updated value') }}</p>
										<p class="type-body text-ink/80">{{ item.after_label || '—' }}</p>
									</li>
								</ul>
							</div>
						</div>

						<div
							class="if-overlay__footer flex flex-wrap items-center justify-between gap-3 px-6 pb-6"
						>
							<p class="type-caption text-ink/55">
								{{ __('You can cancel and keep editing if these changes are not ready.') }}
							</p>
							<div class="flex flex-wrap items-center gap-3">
								<button
									type="button"
									class="if-button if-button--quiet"
									@click="cancel('programmatic')"
								>
									{{ __('Cancel') }}
								</button>
								<button
									type="button"
									class="if-button if-button--secondary"
									@click="selectMode('Form Only')"
								>
									{{ __('Use for this form only') }}
								</button>
								<button
									type="button"
									class="if-button if-button--primary"
									@click="selectMode('Update Profile')"
								>
									{{ __('Update profile everywhere') }}
								</button>
							</div>
						</div>
					</DialogPanel>
				</TransitionChild>
			</div>
		</Dialog>
	</TransitionRoot>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import {
	Dialog,
	DialogPanel,
	DialogTitle,
	TransitionChild,
	TransitionRoot,
} from '@headlessui/vue';
import { FeatherIcon } from 'frappe-ui';

import { __ } from '@/lib/i18n';

type CloseReason = 'backdrop' | 'esc' | 'programmatic';
type ProfileWritebackMode = 'Form Only' | 'Update Profile';

const props = defineProps<{
	open: boolean;
	zIndex?: number;
	changedFields: Array<{
		field_key: string;
		field_label: string;
		before_label: string;
		after_label: string;
	}>;
	onSelect?: (mode: ProfileWritebackMode) => void;
	onCancel?: () => void;
}>();

const emit = defineEmits<{
	(e: 'close', reason: CloseReason): void;
	(e: 'after-leave'): void;
}>();

const overlayStyle = computed(() => ({ zIndex: props.zIndex || 0 }));

function onDialogClose(value: unknown) {
	if (value === false) return;
	cancel('esc');
}

function selectMode(mode: ProfileWritebackMode) {
	props.onSelect?.(mode);
	emit('close', 'programmatic');
}

function cancel(reason: CloseReason) {
	props.onCancel?.();
	emit('close', reason);
}
</script>
