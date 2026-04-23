<template>
	<TransitionRoot as="template" :show="open" @after-leave="emitAfterLeave">
		<Dialog
			as="div"
			class="if-overlay if-overlay--focus"
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
						<div class="if-overlay__header px-6 pt-6">
							<div class="space-y-1">
								<DialogTitle class="type-h2 text-ink"
									>Complete Professional Development</DialogTitle
								>
								<p class="type-caption text-ink/60">
									{{ record?.title || 'Record completion and actual spend.' }}
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

						<div class="if-overlay__body px-6 pb-6 space-y-5">
							<div
								v-if="submitError"
								class="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3"
							>
								<p class="type-body-strong text-rose-900">Completion could not be saved.</p>
								<p class="mt-1 type-caption text-rose-900/80 whitespace-pre-wrap">
									{{ submitError }}
								</p>
							</div>

							<section class="grid gap-4 md:grid-cols-2">
								<label class="space-y-1">
									<span class="type-caption text-ink/70">Completion date</span>
									<input
										v-model="form.completion_date"
										type="date"
										class="if-overlay__input"
										:disabled="submitting"
									/>
								</label>
								<label class="space-y-1">
									<span class="type-caption text-ink/70">Actual total</span>
									<input
										v-model.number="form.actual_total"
										type="number"
										min="0"
										step="0.01"
										class="if-overlay__input"
										:disabled="submitting"
									/>
								</label>
							</section>

							<section class="space-y-2">
								<div class="flex items-center justify-between">
									<span class="type-caption text-ink/70">Evidence</span>
									<button
										type="button"
										class="if-action"
										:disabled="submitting"
										@click="addEvidence"
									>
										Add evidence
									</button>
								</div>
								<div
									v-for="(row, idx) in form.evidence"
									:key="`pd-evidence-${idx}`"
									class="grid gap-3 rounded-2xl border border-line-soft bg-surface-soft p-3"
								>
									<input
										v-model="row.evidence_label"
										class="if-overlay__input"
										:disabled="submitting"
										placeholder="Evidence label"
									/>
									<input
										v-model="row.attachment"
										class="if-overlay__input"
										:disabled="submitting"
										placeholder="Attachment URL or file reference"
									/>
									<input
										v-model="row.notes"
										class="if-overlay__input"
										:disabled="submitting"
										placeholder="Optional notes"
									/>
									<div class="flex justify-end">
										<button
											type="button"
											class="if-action"
											:disabled="submitting || form.evidence.length === 1"
											@click="removeEvidence(idx)"
										>
											Remove
										</button>
									</div>
								</div>
							</section>

							<section class="space-y-2">
								<label class="flex items-center gap-2 type-caption text-ink/70">
									<input v-model="form.liquidation_ready" type="checkbox" :disabled="submitting" />
									<span>Ready for liquidation</span>
								</label>
								<textarea
									v-model="form.reflection"
									rows="5"
									class="if-overlay__input"
									:disabled="submitting"
									placeholder="Reflection, impact, and sharing-back notes"
								/>
							</section>
						</div>

						<footer class="if-overlay__footer">
							<button
								type="button"
								class="if-button if-button--secondary"
								@click="emitClose('programmatic')"
							>
								Cancel
							</button>
							<button
								type="button"
								class="if-button if-button--primary"
								:disabled="submitting"
								@click="submitForm"
							>
								Save completion
							</button>
						</footer>
					</DialogPanel>
				</TransitionChild>
			</div>
		</Dialog>
	</TransitionRoot>
</template>

<script setup lang="ts">
import {
	Dialog,
	DialogPanel,
	DialogTitle,
	TransitionChild,
	TransitionRoot,
} from '@headlessui/vue';
import { FeatherIcon } from 'frappe-ui';
import { computed, ref, watch } from 'vue';

import { useOverlayStack } from '@/composables/useOverlayStack';
import { completeProfessionalDevelopmentRecord } from '@/lib/services/professionalDevelopment/professionalDevelopmentService';
import { SIGNAL_PROFESSIONAL_DEVELOPMENT_INVALIDATE, uiSignals } from '@/lib/uiSignals';

type CloseReason = 'backdrop' | 'esc' | 'programmatic';

const props = defineProps<{
	open: boolean;
	zIndex?: number;
	overlayId?: string;
	record: {
		name: string;
		title: string;
		estimated_total?: number;
		actual_total?: number;
	} | null;
}>();

const emit = defineEmits<{
	(e: 'close', reason: CloseReason): void;
	(e: 'after-leave'): void;
}>();

const overlay = useOverlayStack();
const closeBtnEl = ref<HTMLButtonElement | null>(null);
const overlayStyle = computed(() => ({ zIndex: props.zIndex ?? 0 }));

const today = new Date().toISOString().slice(0, 10);
const submitting = ref(false);
const submitError = ref('');
const form = ref({
	completion_date: today,
	actual_total: Number(props.record?.actual_total ?? props.record?.estimated_total ?? 0),
	reflection: '',
	liquidation_ready: true,
	evidence: [{ evidence_label: '', attachment: '', notes: '' }],
});

watch(
	() => props.record,
	record => {
		form.value = {
			completion_date: today,
			actual_total: Number(record?.actual_total ?? record?.estimated_total ?? 0),
			reflection: '',
			liquidation_ready: true,
			evidence: [{ evidence_label: '', attachment: '', notes: '' }],
		};
	},
	{ immediate: true }
);

function emitClose(reason: CloseReason) {
	if (props.overlayId) {
		overlay.close(props.overlayId);
		return;
	}
	emit('close', reason);
}

function emitAfterLeave() {
	emit('after-leave');
}

function onDialogClose(_payload: unknown) {
	// no-op: close is explicit
}

function addEvidence() {
	form.value.evidence.push({ evidence_label: '', attachment: '', notes: '' });
}

function removeEvidence(index: number) {
	if (form.value.evidence.length <= 1) return;
	form.value.evidence.splice(index, 1);
}

async function submitForm() {
	if (!props.record?.name) return;
	submitting.value = true;
	submitError.value = '';
	try {
		await completeProfessionalDevelopmentRecord({
			record_name: props.record.name,
			actual_total: Number(form.value.actual_total || 0),
			completion_date: form.value.completion_date,
			reflection: form.value.reflection || undefined,
			liquidation_ready: form.value.liquidation_ready ? 1 : 0,
			evidence: form.value.evidence
				.filter(row => row.evidence_label.trim())
				.map(row => ({
					evidence_label: row.evidence_label.trim(),
					attachment: row.attachment || undefined,
					notes: row.notes || undefined,
				})),
		});
		uiSignals.emit(SIGNAL_PROFESSIONAL_DEVELOPMENT_INVALIDATE);
		emitClose('programmatic');
	} catch (error: any) {
		submitError.value = error?.message || 'Could not save completion.';
	} finally {
		submitting.value = false;
	}
}
</script>
