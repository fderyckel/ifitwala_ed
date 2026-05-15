<!-- ifitwala_ed/ui-spa/src/components/analytics/GenericListDialog.vue -->
<template>
	<Teleport to="body">
		<TransitionRoot as="template" :show="show">
			<Dialog
				as="div"
				class="if-overlay if-overlay--morning-brief-list"
				:initialFocus="closeButtonRef"
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
					<div class="if-overlay__backdrop" @click="closeDialog" />
				</TransitionChild>

				<div class="if-overlay__wrap generic-list-dialog__wrap" @click.self="closeDialog">
					<TransitionChild
						as="template"
						enter="if-overlay__panel-enter"
						enter-from="if-overlay__panel-from"
						enter-to="if-overlay__panel-to"
						leave="if-overlay__panel-leave"
						leave-from="if-overlay__panel-to"
						leave-to="if-overlay__panel-from"
					>
						<DialogPanel class="if-overlay__panel generic-list-dialog__panel">
							<header class="generic-list-dialog__header">
								<div class="min-w-0">
									<p class="type-overline generic-list-dialog__eyebrow">
										{{ __('Morning Brief') }}
									</p>
									<DialogTitle class="type-h2 text-ink mt-2">
										{{ title }}
									</DialogTitle>
									<p v-if="subtitle" class="type-caption mt-2 text-ink/65">
										{{ subtitle }}
									</p>
								</div>

								<button
									ref="closeButtonRef"
									type="button"
									class="if-overlay__icon-button"
									aria-label="Close"
									@click="closeDialog"
								>
									<FeatherIcon name="x" class="h-4 w-4" />
								</button>
							</header>

							<section class="if-overlay__body generic-list-dialog__body custom-scrollbar">
								<div v-if="loading" class="generic-list-dialog__state">
									<FeatherIcon name="loader" class="h-8 w-8 animate-spin text-slate-token/40" />
								</div>

								<div
									v-else-if="items && items.length > 0"
									class="generic-list-dialog__list divide-y divide-border/45"
								>
									<div
										v-for="(item, index) in items"
										:key="index"
										class="generic-list-dialog__item"
									>
										<slot name="item" :item="item" :index="index">
											<div class="p-4">{{ item }}</div>
										</slot>
									</div>
								</div>

								<div v-else class="generic-list-dialog__empty">
									<div class="generic-list-dialog__empty-icon">
										<FeatherIcon name="inbox" class="h-8 w-8 text-slate-token/45" />
									</div>
									<p class="mt-4 text-sm font-semibold text-ink/75">{{ __('No items found') }}</p>
									<p class="mt-1 text-xs text-slate-token/65">
										{{ __('This list is currently empty for the selected briefing context.') }}
									</p>
								</div>
							</section>

							<footer class="if-overlay__footer">
								<button
									type="button"
									class="generic-list-dialog__footer-button"
									@click="closeDialog"
								>
									{{ __('Close') }}
								</button>
							</footer>
						</DialogPanel>
					</TransitionChild>
				</div>
			</Dialog>
		</TransitionRoot>
	</Teleport>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import {
	Dialog,
	DialogPanel,
	DialogTitle,
	TransitionChild,
	TransitionRoot,
} from '@headlessui/vue';
import { FeatherIcon } from 'frappe-ui';
import { __ } from '@/lib/i18n';

const props = defineProps<{
	modelValue: boolean;
	title: string;
	subtitle?: string;
	items: any[];
	loading?: boolean;
}>();

const emit = defineEmits<{
	(event: 'update:modelValue', value: boolean): void;
}>();

const closeButtonRef = ref<HTMLButtonElement | null>(null);

const show = computed({
	get: () => props.modelValue,
	set: value => emit('update:modelValue', value),
});

function closeDialog() {
	show.value = false;
}

function onDialogClose(_payload: unknown) {
	// Explicit close paths only.
}

function onKeydown(event: KeyboardEvent) {
	if (!show.value) return;
	if (event.key === 'Escape') closeDialog();
}

onMounted(() => {
	document.addEventListener('keydown', onKeydown, true);
});

onBeforeUnmount(() => {
	document.removeEventListener('keydown', onKeydown, true);
});
</script>

<style scoped>
.generic-list-dialog__wrap {
	align-items: center;
}

.generic-list-dialog__panel {
	max-width: min(64rem, calc(100vw - 1.5rem));
}

.generic-list-dialog__header {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: 1rem;
	padding: 1.35rem 1.5rem;
	border-bottom: 1px solid rgb(var(--border-rgb) / 0.65);
	background:
		radial-gradient(circle at top left, rgb(var(--flame-rgb) / 0.08), transparent 32%),
		radial-gradient(circle at top right, rgb(var(--leaf-rgb) / 0.12), transparent 35%),
		linear-gradient(180deg, rgb(var(--surface-rgb) / 0.98), rgb(var(--surface-strong-rgb) / 1));
}

.generic-list-dialog__eyebrow {
	color: rgb(var(--slate-rgb) / 0.74);
}

.generic-list-dialog__body {
	padding: 0;
	background: linear-gradient(
		180deg,
		rgb(var(--surface-rgb) / 0.72),
		rgb(var(--surface-strong-rgb) / 0.94)
	);
}

.generic-list-dialog__list {
	padding: 0.5rem;
}

.generic-list-dialog__item {
	border-radius: 1.25rem;
	background: rgb(var(--surface-strong-rgb) / 0.94);
	box-shadow: var(--shadow-soft);
}

.generic-list-dialog__item + .generic-list-dialog__item {
	margin-top: 0.5rem;
}

.generic-list-dialog__state,
.generic-list-dialog__empty {
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	min-height: 18rem;
	padding: 2rem;
	text-align: center;
}

.generic-list-dialog__empty-icon {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	height: 4rem;
	width: 4rem;
	border-radius: 9999px;
	background: rgb(var(--surface-rgb) / 0.9);
	border: 1px solid rgb(var(--border-rgb) / 0.7);
}

.generic-list-dialog__footer-button {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	border-radius: 9999px;
	border: 1px solid rgb(var(--border-rgb) / 0.85);
	background: rgb(var(--surface-strong-rgb) / 1);
	padding: 0.6rem 1.05rem;
	font-size: 0.85rem;
	font-weight: 600;
	color: rgb(var(--ink-rgb) / 0.9);
	transition:
		border-color 120ms ease,
		color 120ms ease,
		transform 120ms ease;
}

.generic-list-dialog__footer-button:hover {
	border-color: rgb(var(--jacaranda-rgb) / 0.35);
	color: rgb(var(--jacaranda-rgb) / 0.95);
	transform: translateY(-1px);
}

@media (max-width: 767px) {
	.generic-list-dialog__panel {
		max-width: calc(100vw - 1rem);
		max-height: calc(100vh - 1rem);
	}

	.generic-list-dialog__header {
		padding: 1rem;
	}
}
</style>
