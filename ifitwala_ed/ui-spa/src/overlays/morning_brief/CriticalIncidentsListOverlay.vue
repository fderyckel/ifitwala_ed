<!-- ifitwala_ed/ui-spa/src/overlays/morning_brief/CriticalIncidentsListOverlay.vue -->
<!--
  CriticalIncidentsListOverlay
  A+ compliant overlay for displaying critical student log incidents requiring follow-up.
  Uses our own overlay architecture (not frappe-ui Dialog) with proper backdrop.

  Used by:
  - MorningBriefing.vue (pages/staff/morning_brief)
-->
<template>
	<TransitionRoot as="template" :show="open" @after-leave="emitAfterLeave">
		<Dialog
			as="div"
			class="if-overlay if-overlay--critical-incidents"
			:style="overlayStyle"
			:initialFocus="closeBtnEl"
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
						<!-- Header -->
						<div class="if-overlay__header">
							<div class="min-w-0">
								<DialogTitle class="type-h2 text-ink flex items-center gap-2">
									<FeatherIcon name="alert-circle" class="h-5 w-5 text-flame" />
									{{ __('Critical Incidents') }}
								</DialogTitle>
								<p class="mt-1 type-caption text-ink/60">
									{{ __('Open logs requiring follow-up') }}
								</p>
							</div>

							<button
								ref="closeBtnEl"
								type="button"
								class="if-overlay__icon-button"
								@click="emitClose('programmatic')"
								aria-label="Close"
							>
								<FeatherIcon name="x" class="h-4 w-4" />
							</button>
						</div>

						<!-- Body -->
						<div class="if-overlay__body">
							<!-- Loading State -->
							<div v-if="loading" class="flex items-center justify-center py-12">
								<FeatherIcon name="loader" class="h-8 w-8 animate-spin text-slate-token/40" />
							</div>

							<!-- Empty State -->
							<div
								v-else-if="!items || items.length === 0"
								class="flex flex-col items-center justify-center py-12 text-center"
							>
								<div
									class="flex h-16 w-16 items-center justify-center rounded-full bg-surface-soft"
								>
									<FeatherIcon name="inbox" class="h-8 w-8 text-slate-token/50" />
								</div>
								<p class="mt-4 type-body-strong text-ink/70">
									{{ __('No critical incidents') }}
								</p>
								<p class="mt-1 type-caption text-ink/50">
									{{ __('All logs have been resolved.') }}
								</p>
							</div>

							<!-- List -->
							<div v-else class="space-y-3">
								<div
									v-for="item in items"
									:key="item.name"
									class="rounded-2xl border border-border/60 bg-white p-4 shadow-soft transition-all hover:shadow-md"
								>
									<div class="flex gap-4">
										<!-- Student Avatar -->
										<div
											class="h-12 w-12 shrink-0 overflow-hidden rounded-full bg-surface-soft ring-1 ring-border/50"
										>
											<img
												v-if="item.student_image"
												:src="item.student_image"
												class="h-full w-full object-cover"
												alt=""
											/>
											<div
												v-else
												class="flex h-full w-full items-center justify-center text-xs font-bold text-slate-token/65"
											>
												{{ item.student_name.substring(0, 2) }}
											</div>
										</div>

										<!-- Content -->
										<div class="min-w-0 flex-1">
											<div class="flex items-start justify-between gap-2">
												<h4 class="type-body-strong text-ink">
													{{ item.student_name }}
												</h4>
												<span class="type-caption text-slate-token/60 shrink-0">
													{{ item.date_display }}
												</span>
											</div>

											<div class="mt-1">
												<span
													class="inline-flex items-center rounded-md bg-surface-soft px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-slate-token/80"
												>
													{{ item.log_type }}
												</span>
											</div>

											<p class="mt-2 text-sm text-slate-token/90 line-clamp-2">
												{{ item.snippet }}
											</p>

											<button
												type="button"
												class="mt-3 inline-flex items-center gap-1 text-xs font-medium text-jacaranda transition-colors hover:text-jacaranda/80"
												@click="openLog(item)"
											>
												{{ __('View Full Log') }}
												<FeatherIcon name="maximize-2" class="h-3 w-3" />
											</button>
										</div>
									</div>
								</div>
							</div>
						</div>

						<!-- Footer -->
						<footer class="if-overlay__footer">
							<Button appearance="minimal" @click="emitClose('programmatic')">
								{{ __('Close') }}
							</Button>
						</footer>
					</DialogPanel>
				</TransitionChild>
			</div>
		</Dialog>
	</TransitionRoot>
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
import { Button, FeatherIcon } from 'frappe-ui';

import { __ } from '@/lib/i18n';
import { useOverlayStack } from '@/composables/useOverlayStack';
import type { StudentLogDetail } from '@/types/contracts/morning_brief/get_critical_incidents_details';

type CloseReason = 'backdrop' | 'esc' | 'programmatic';

const props = defineProps<{
	open: boolean;
	zIndex?: number;
	overlayId?: string;
	items: StudentLogDetail[];
	loading?: boolean;
	onViewLog?: (item: StudentLogDetail) => void;
}>();

const emit = defineEmits<{
	(e: 'close', reason: CloseReason): void;
	(e: 'after-leave'): void;
	(e: 'view-log', item: StudentLogDetail): void;
}>();

const overlay = useOverlayStack();

const overlayStyle = computed(() => ({ zIndex: props.zIndex ?? 0 }));
const closeBtnEl = ref<HTMLButtonElement | null>(null);

function emitClose(reason: CloseReason) {
	const overlayId = props.overlayId || null;
	if (overlayId) {
		try {
			overlay.close(overlayId);
			return;
		} catch {
			// fall through to emit fallback
		}
	}
	emit('close', reason);
}

function emitAfterLeave() {
	emit('after-leave');
}

function onDialogClose(_payload: unknown) {
	// no-op by design - we handle close explicitly
}

function openLog(item: StudentLogDetail) {
	if (props.onViewLog) {
		props.onViewLog(item);
	}
	emit('view-log', item);
}

function onKeydown(e: KeyboardEvent) {
	if (!props.open) return;
	if (e.key === 'Escape') emitClose('esc');
}

onMounted(() => {
	document.addEventListener('keydown', onKeydown, true);
});

onBeforeUnmount(() => {
	document.removeEventListener('keydown', onKeydown, true);
});
</script>
