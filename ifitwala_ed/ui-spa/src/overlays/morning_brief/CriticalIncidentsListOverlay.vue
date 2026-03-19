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

			<div class="if-overlay__wrap critical-incidents__wrap" @click.self="emitClose('backdrop')">
				<TransitionChild
					as="template"
					enter="if-overlay__panel-enter"
					enter-from="if-overlay__panel-from"
					enter-to="if-overlay__panel-to"
					leave="if-overlay__panel-leave"
					leave-from="if-overlay__panel-to"
					leave-to="if-overlay__panel-from"
				>
					<DialogPanel class="if-overlay__panel critical-incidents__panel">
						<header class="critical-incidents__hero">
							<div class="critical-incidents__hero-copy">
								<p class="type-overline critical-incidents__eyebrow">
									{{ __('Morning Brief') }}
								</p>
								<DialogTitle class="type-h2 text-ink mt-2 flex items-center gap-2">
									<FeatherIcon name="alert-triangle" class="h-5 w-5 text-flame" />
									{{ __('Critical Incidents') }}
								</DialogTitle>
								<p class="mt-2 text-sm text-ink/70">
									{{
										__('Open student logs that still need follow-up from academic administration.')
									}}
								</p>
							</div>

							<div class="critical-incidents__hero-meta">
								<div class="critical-incidents__count-chip">
									<span class="critical-incidents__count-value">{{ items?.length || 0 }}</span>
									<span class="critical-incidents__count-label">{{ __('Open') }}</span>
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
						</header>

						<section class="if-overlay__body critical-incidents__body custom-scrollbar">
							<div v-if="loading" class="critical-incidents__state">
								<FeatherIcon name="loader" class="h-8 w-8 animate-spin text-slate-token/40" />
							</div>

							<div v-else-if="!items || items.length === 0" class="critical-incidents__empty">
								<div class="critical-incidents__empty-icon">
									<FeatherIcon name="check-circle" class="h-8 w-8 text-canopy/75" />
								</div>
								<p class="mt-4 text-sm font-semibold text-ink/80">
									{{ __('No critical incidents') }}
								</p>
								<p class="mt-1 text-xs text-slate-token/65">
									{{ __('All currently escalated logs have been resolved or reassigned.') }}
								</p>
							</div>

							<div v-else class="critical-incidents__grid">
								<article v-for="item in items" :key="item.name" class="critical-incidents__card">
									<div class="critical-incidents__card-top">
										<div class="critical-incidents__identity">
											<div class="critical-incidents__avatar">
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

											<div class="min-w-0">
												<h4 class="text-base font-semibold text-ink">
													{{ item.student_name }}
												</h4>
												<p class="mt-1 text-xs text-slate-token/65">
													{{ item.date_display }}
												</p>
											</div>
										</div>

										<span class="critical-incidents__type-pill">
											{{ item.log_type }}
										</span>
									</div>

									<p class="critical-incidents__snippet">
										{{ item.snippet }}
									</p>

									<div class="critical-incidents__actions">
										<button
											type="button"
											class="critical-incidents__action-button"
											@click="openLog(item)"
										>
											<span>{{ __('View Full Log') }}</span>
											<FeatherIcon name="arrow-up-right" class="h-3.5 w-3.5" />
										</button>
									</div>
								</article>
							</div>
						</section>

						<footer class="if-overlay__footer critical-incidents__footer">
							<p class="text-xs text-slate-token/70">
								{{
									__(
										'Open the full log to review context, comments, and required follow-up action.'
									)
								}}
							</p>
							<button
								type="button"
								class="critical-incidents__footer-button"
								@click="emitClose('programmatic')"
							>
								{{ __('Close') }}
							</button>
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
import { FeatherIcon } from 'frappe-ui';

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

<style scoped>
.critical-incidents__wrap {
	align-items: center;
}

.critical-incidents__panel {
	max-width: min(72rem, calc(100vw - 1.5rem));
}

.critical-incidents__hero {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: 1rem;
	padding: 1.5rem;
	border-bottom: 1px solid rgb(var(--border-rgb) / 0.65);
	background:
		radial-gradient(circle at top left, rgb(var(--flame-rgb) / 0.14), transparent 32%),
		radial-gradient(circle at top right, rgb(var(--sky-rgb) / 0.16), transparent 36%),
		linear-gradient(180deg, rgb(var(--surface-rgb) / 0.98), rgb(var(--surface-strong-rgb) / 1));
}

.critical-incidents__hero-copy {
	min-width: 0;
	flex: 1;
}

.critical-incidents__eyebrow {
	color: rgb(var(--slate-rgb) / 0.74);
}

.critical-incidents__hero-meta {
	display: flex;
	align-items: flex-start;
	gap: 0.75rem;
}

.critical-incidents__count-chip {
	display: inline-flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	min-width: 4.5rem;
	border-radius: 1.2rem;
	border: 1px solid rgb(var(--flame-rgb) / 0.18);
	background: rgb(var(--flame-rgb) / 0.08);
	padding: 0.7rem 0.95rem;
}

.critical-incidents__count-value {
	font-size: 1.35rem;
	font-weight: 700;
	line-height: 1;
	color: rgb(var(--flame-rgb) / 0.96);
}

.critical-incidents__count-label {
	margin-top: 0.25rem;
	font-size: 0.7rem;
	font-weight: 700;
	letter-spacing: 0.08em;
	text-transform: uppercase;
	color: rgb(var(--slate-rgb) / 0.75);
}

.critical-incidents__body {
	padding: 1.25rem;
	background: linear-gradient(
		180deg,
		rgb(var(--surface-rgb) / 0.74),
		rgb(var(--surface-strong-rgb) / 0.96)
	);
}

.critical-incidents__grid {
	display: grid;
	gap: 1rem;
	grid-template-columns: repeat(2, minmax(0, 1fr));
}

.critical-incidents__card {
	display: flex;
	flex-direction: column;
	gap: 1rem;
	border-radius: 1.5rem;
	border: 1px solid rgb(var(--border-rgb) / 0.72);
	background: rgb(var(--surface-strong-rgb) / 0.97);
	padding: 1.1rem;
	box-shadow: var(--shadow-soft);
}

.critical-incidents__card-top {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: 0.75rem;
}

.critical-incidents__identity {
	display: flex;
	align-items: center;
	gap: 0.85rem;
	min-width: 0;
}

.critical-incidents__avatar {
	height: 3rem;
	width: 3rem;
	flex-shrink: 0;
	overflow: hidden;
	border-radius: 9999px;
	border: 1px solid rgb(var(--border-rgb) / 0.7);
	background: rgb(var(--surface-rgb) / 0.9);
}

.critical-incidents__type-pill {
	display: inline-flex;
	align-items: center;
	border-radius: 9999px;
	background: rgb(var(--surface-rgb) / 0.94);
	padding: 0.4rem 0.7rem;
	font-size: 0.7rem;
	font-weight: 700;
	letter-spacing: 0.08em;
	text-transform: uppercase;
	color: rgb(var(--slate-rgb) / 0.78);
}

.critical-incidents__snippet {
	font-size: 0.92rem;
	line-height: 1.55;
	color: rgb(var(--slate-rgb) / 0.88);
	display: -webkit-box;
	-webkit-line-clamp: 3;
	-webkit-box-orient: vertical;
	overflow: hidden;
}

.critical-incidents__actions {
	display: flex;
	justify-content: flex-end;
}

.critical-incidents__action-button,
.critical-incidents__footer-button {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	gap: 0.45rem;
	border-radius: 9999px;
	padding: 0.6rem 1rem;
	font-size: 0.82rem;
	font-weight: 700;
	transition:
		transform 120ms ease,
		border-color 120ms ease,
		background 120ms ease,
		color 120ms ease;
}

.critical-incidents__action-button {
	border: 1px solid rgb(var(--jacaranda-rgb) / 0.2);
	background: rgb(var(--jacaranda-rgb) / 0.08);
	color: rgb(var(--jacaranda-rgb) / 0.96);
}

.critical-incidents__action-button:hover,
.critical-incidents__footer-button:hover {
	transform: translateY(-1px);
}

.critical-incidents__footer {
	justify-content: space-between;
	align-items: center;
}

.critical-incidents__footer-button {
	border: 1px solid rgb(var(--border-rgb) / 0.85);
	background: rgb(var(--surface-strong-rgb) / 1);
	color: rgb(var(--ink-rgb) / 0.9);
}

.critical-incidents__state,
.critical-incidents__empty {
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	min-height: 18rem;
	text-align: center;
}

.critical-incidents__empty-icon {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	height: 4rem;
	width: 4rem;
	border-radius: 9999px;
	border: 1px solid rgb(var(--border-rgb) / 0.72);
	background: rgb(var(--surface-rgb) / 0.94);
}

@media (max-width: 767px) {
	.critical-incidents__panel {
		max-width: calc(100vw - 1rem);
		max-height: calc(100vh - 1rem);
	}

	.critical-incidents__hero {
		flex-direction: column;
		padding: 1.1rem;
	}

	.critical-incidents__hero-meta,
	.critical-incidents__footer {
		width: 100%;
		justify-content: space-between;
	}

	.critical-incidents__body {
		padding: 1rem;
	}

	.critical-incidents__grid {
		grid-template-columns: 1fr;
	}

	.critical-incidents__footer {
		flex-direction: column;
		align-items: stretch;
		gap: 0.75rem;
	}
}
</style>
