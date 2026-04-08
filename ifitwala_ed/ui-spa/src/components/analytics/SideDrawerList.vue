<!-- ifitwala_ed/ui-spa/src/components/analytics/SideDrawerList.vue -->
<!--
  SideDrawerList.vue
  A slide-over drawer for displaying lists of records associated with an analytics slice.
  Commonly triggered by clicking on chart elements.

  Used by:
  - EnrollmentAnalytics.vue
  - StudentLogAnalytics.vue
-->
<template>
	<Teleport to="body">
		<TransitionRoot as="template" :show="open">
			<Dialog
				as="div"
				class="if-overlay if-overlay--drawer if-overlay--analytics-drawer"
				:initialFocus="closeButtonRef"
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
					<div class="if-overlay__backdrop" @click="emitClose" />
				</TransitionChild>

				<div class="if-overlay__wrap if-overlay__wrap--drawer" @click.self="emitClose">
					<TransitionChild
						as="template"
						enter="if-overlay__panel-enter"
						enter-from="if-overlay__panel-from"
						enter-to="if-overlay__panel-to"
						leave="if-overlay__panel-leave"
						leave-from="if-overlay__panel-to"
						leave-to="if-overlay__panel-from"
					>
						<DialogPanel class="if-overlay__panel if-overlay__panel--drawer-md">
							<header
								class="flex items-start justify-between gap-3 border-b border-border/60 bg-[rgb(var(--surface-rgb)/0.96)] px-4 py-4"
							>
								<div class="min-w-0">
									<p class="type-overline text-ink/60">{{ entityLabel }}</p>
									<DialogTitle class="type-h3 mt-2 text-ink">{{ title }}</DialogTitle>
								</div>
								<button
									ref="closeButtonRef"
									type="button"
									class="if-overlay__icon-button"
									aria-label="Close"
									@click="emitClose"
								>
									<FeatherIcon name="x" class="h-4 w-4" />
								</button>
							</header>
							<section class="if-overlay__body custom-scrollbar px-4 py-3">
								<slot name="filters" />
								<div v-if="loading" class="py-6 text-center type-caption text-ink/60">
									Loading...
								</div>
								<div v-else-if="!rows.length" class="py-6 text-center type-body text-ink/55">
									No records for this slice.
								</div>
								<ul v-else class="divide-y divide-border/45">
									<li v-for="row in rows" :key="row.id || row.name" class="py-3">
										<slot name="row" :row="row">
											<div class="flex flex-col">
												<span class="type-body-strong text-ink">
													{{ row.name || row.title }}
												</span>
												<span class="type-caption mt-1 text-ink/60">{{ row.subtitle }}</span>
											</div>
										</slot>
									</li>
								</ul>
							</section>
							<footer class="if-overlay__footer justify-between">
								<slot name="actions" />
								<button
									v-if="onLoadMore"
									class="rounded-xl border border-border/70 bg-[rgb(var(--surface-strong-rgb)/1)] px-3 py-2 type-button-label text-ink/80 transition-colors hover:bg-surface-soft"
									@click="onLoadMore"
								>
									Load more
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
import {
	Dialog,
	DialogPanel,
	DialogTitle,
	TransitionChild,
	TransitionRoot,
} from '@headlessui/vue';
import { computed, ref } from 'vue';
import { FeatherIcon } from 'frappe-ui';

type EntityType = 'student' | 'guardian';

const props = defineProps<{
	open: boolean;
	title: string;
	rows: any[];
	entity?: EntityType;
	entityLabel?: string;
	loading?: boolean;
	onLoadMore?: () => void;
}>();

const emit = defineEmits<{
	(e: 'close'): void;
}>();

const closeButtonRef = ref<HTMLButtonElement | null>(null);

const entityLabel = computed(() => {
	if (props.entityLabel) return props.entityLabel;
	if (props.entity === 'student') return 'Students';
	if (props.entity === 'guardian') return 'Guardians';
	return 'Items';
});

function emitClose() {
	emit('close');
}
</script>
