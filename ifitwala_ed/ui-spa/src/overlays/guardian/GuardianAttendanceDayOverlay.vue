<template>
	<TransitionRoot as="template" :show="open" @after-leave="emitAfterLeave">
		<Dialog
			as="div"
			class="if-overlay if-overlay--guardian-attendance-day"
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
					<DialogPanel class="if-overlay__panel if-overlay__panel--compact">
						<header class="px-6 pt-6">
							<div class="flex items-start justify-between gap-4">
								<div>
									<p class="type-overline text-ink/60">Guardian Portal</p>
									<DialogTitle class="mt-1 type-h2 text-ink">
										{{ studentName || 'Attendance detail' }}
									</DialogTitle>
									<p v-if="day?.date" class="mt-2 type-body text-ink/70">
										{{ formatDetailDate(day.date) }}
									</p>
								</div>

								<button
									ref="closeBtnEl"
									type="button"
									class="if-overlay__icon-button"
									aria-label="Close attendance detail"
									@click="emitClose('programmatic')"
								>
									<FeatherIcon name="x" class="h-4 w-4" />
								</button>
							</div>

							<div class="mt-4 flex flex-wrap items-center gap-2">
								<p class="type-caption text-ink/60">{{ detailCount }} attendance detail(s)</p>
								<p
									class="rounded-full px-3 py-1 type-caption"
									:class="detailStateClass(day?.state || 'present')"
								>
									{{ detailStateLabel(day?.state || 'present') }}
								</p>
							</div>
						</header>

						<div class="if-overlay__body pt-5">
							<div
								v-if="!day?.details?.length"
								class="rounded-2xl border border-line-soft bg-surface-soft p-4"
							>
								<p class="type-body text-ink/70">
									No attendance detail is available for this date.
								</p>
							</div>

							<ul v-else class="space-y-3">
								<li
									v-for="detail in day.details"
									:key="detail.attendance"
									class="rounded-xl border border-line-soft bg-surface-soft p-4"
								>
									<p class="type-body-strong text-ink">{{ detail.attendance_code_name }}</p>
									<p class="type-caption text-ink/60">
										{{ detail.whole_day ? 'Whole day' : detail.time || 'Time not recorded' }}
										<span v-if="detail.course"> - {{ detail.course }}</span>
										<span v-if="detail.location"> - {{ detail.location }}</span>
									</p>
									<p v-if="detail.remark" class="mt-2 type-body text-ink/80">
										{{ detail.remark }}
									</p>
								</li>
							</ul>
						</div>

						<footer class="if-overlay__footer">
							<button
								type="button"
								class="if-button if-button--secondary"
								@click="emitClose('programmatic')"
							>
								Close
							</button>
						</footer>
					</DialogPanel>
				</TransitionChild>
			</div>
		</Dialog>
	</TransitionRoot>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import {
	Dialog,
	DialogPanel,
	DialogTitle,
	TransitionChild,
	TransitionRoot,
} from '@headlessui/vue';
import { FeatherIcon } from 'frappe-ui';

import { useOverlayStack } from '@/composables/useOverlayStack';

import type { GuardianAttendanceDay } from '@/types/contracts/guardian/get_guardian_attendance_snapshot';

type CloseReason = 'backdrop' | 'esc' | 'programmatic';

const props = defineProps<{
	open: boolean;
	zIndex?: number;
	overlayId?: string;
	studentName?: string | null;
	day?: GuardianAttendanceDay | null;
	onClose?: () => void;
}>();

const emit = defineEmits<{
	(e: 'close', reason: CloseReason): void;
	(e: 'after-leave'): void;
	(e: 'done'): void;
}>();

const overlay = useOverlayStack();

const overlayStyle = computed(() => ({ zIndex: props.zIndex ?? 0 }));
const closeBtnEl = ref<HTMLButtonElement | null>(null);
const detailCount = computed(() => props.day?.details.length ?? 0);

function emitClose(reason: CloseReason) {
	props.onClose?.();
	const overlayId = props.overlayId || null;
	if (overlayId) {
		try {
			overlay.close(overlayId);
			return;
		} catch (error) {
			// Fall back to OverlayHost if the direct close path is unavailable.
		}
	}

	emit('close', reason);
}

function emitAfterLeave() {
	emit('after-leave');
}

function onDialogClose(_payload: unknown) {
	// OverlayHost owns close enforcement.
}

function detailStateLabel(state: GuardianAttendanceDay['state']): string {
	if (state === 'late') return 'Late or tardy';
	if (state === 'absence') return 'Absence recorded';
	return 'Present';
}

function detailStateClass(state: GuardianAttendanceDay['state']): string {
	if (state === 'late') return 'bg-jacaranda/12 text-jacaranda';
	if (state === 'absence') return 'bg-flame/12 text-flame';
	return 'bg-moss/15 text-ink';
}

function formatDetailDate(value: string): string {
	if (!value) return '';
	return new Intl.DateTimeFormat(undefined, {
		weekday: 'long',
		day: 'numeric',
		month: 'long',
		year: 'numeric',
	}).format(parseIsoDate(value));
}

function parseIsoDate(value: string): Date {
	const [year, month, day] = value.split('-').map(Number);
	return new Date(year, month - 1, day);
}
</script>
