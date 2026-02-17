<!-- ifitwala_ed/ui-spa/src/overlays/admissions/ApplicantHealthOverlay.vue -->

<template>
	<TransitionRoot as="template" :show="open" @after-leave="emitAfterLeave">
		<Dialog
			as="div"
			class="if-overlay if-overlay--admissions"
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
								<DialogTitle class="type-h2 text-ink">{{ __('Health information') }}</DialogTitle>
								<p class="mt-1 type-caption text-ink/60">
									{{ __('Share any important health details with the admissions team.') }}
								</p>
							</div>
							<button
								type="button"
								class="if-overlay__close"
								@click="emitClose('programmatic')"
								aria-label="Close"
							>
								<FeatherIcon name="x" class="h-5 w-5" />
							</button>
						</div>

						<div class="if-overlay__body px-6 pb-6 space-y-5">
							<div
								v-if="errorMessage"
								class="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 shadow-soft"
								role="alert"
							>
								<p class="type-body-strong text-rose-900">{{ __('Something went wrong') }}</p>
								<p class="mt-1 type-caption text-rose-900/80 whitespace-pre-wrap">
									{{ errorMessage }}
								</p>
							</div>

							<section class="space-y-2">
								<p class="type-caption text-ink/70">{{ __('Health summary') }}</p>
								<textarea
									v-model="form.health_summary"
									class="w-full rounded-2xl border border-border/70 bg-white px-4 py-3 text-sm text-ink shadow-soft outline-none focus:ring-2 focus:ring-[rgb(var(--leaf-rgb)/0.35)]"
									rows="3"
									:disabled="isReadOnly || submitting"
								/>
							</section>

							<section class="space-y-2">
								<p class="type-caption text-ink/70">{{ __('Medical conditions') }}</p>
								<textarea
									v-model="form.medical_conditions"
									class="w-full rounded-2xl border border-border/70 bg-white px-4 py-3 text-sm text-ink shadow-soft outline-none focus:ring-2 focus:ring-[rgb(var(--leaf-rgb)/0.35)]"
									rows="3"
									:disabled="isReadOnly || submitting"
								/>
							</section>

							<section class="space-y-2">
								<p class="type-caption text-ink/70">{{ __('Allergies') }}</p>
								<textarea
									v-model="form.allergies"
									class="w-full rounded-2xl border border-border/70 bg-white px-4 py-3 text-sm text-ink shadow-soft outline-none focus:ring-2 focus:ring-[rgb(var(--leaf-rgb)/0.35)]"
									rows="3"
									:disabled="isReadOnly || submitting"
								/>
							</section>

							<section class="space-y-2">
								<p class="type-caption text-ink/70">{{ __('Medications') }}</p>
								<textarea
									v-model="form.medications"
									class="w-full rounded-2xl border border-border/70 bg-white px-4 py-3 text-sm text-ink shadow-soft outline-none focus:ring-2 focus:ring-[rgb(var(--leaf-rgb)/0.35)]"
									rows="3"
									:disabled="isReadOnly || submitting"
								/>
							</section>
						</div>

						<div
							class="if-overlay__footer px-6 pb-6 flex flex-wrap items-center justify-between gap-3"
						>
							<p class="type-caption text-ink/55">
								{{
									isReadOnly
										? __('This application is read-only.')
										: __('You can update this later if needed.')
								}}
							</p>
							<div class="flex items-center gap-3">
								<button
									type="button"
									class="rounded-full border border-border/70 bg-white px-4 py-2 type-caption text-ink/70"
									@click="emitClose('programmatic')"
								>
									{{ __('Cancel') }}
								</button>
								<button
									type="button"
									class="rounded-full bg-ink px-5 py-2 type-caption text-white shadow-soft disabled:opacity-50"
									:disabled="isReadOnly || submitting"
									@click="submit"
								>
									<span v-if="submitting" class="inline-flex items-center gap-2">
										<Spinner class="h-4 w-4" /> {{ __('Saving…') }}
									</span>
									<span v-else>{{ __('Save') }}</span>
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
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue';
import {
	Dialog,
	DialogPanel,
	DialogTitle,
	TransitionChild,
	TransitionRoot,
} from '@headlessui/vue';
import { FeatherIcon, Spinner } from 'frappe-ui';

import { useOverlayStack } from '@/composables/useOverlayStack';
import { createAdmissionsService } from '@/lib/services/admissions/admissionsService';

type CloseReason = 'backdrop' | 'esc' | 'programmatic';

type HealthPayload = {
	health_summary: string;
	medical_conditions: string;
	allergies: string;
	medications: string;
};

const props = defineProps<{
	open: boolean;
	zIndex?: number;
	overlayId?: string;
	initial?: HealthPayload | null;
	readOnly?: boolean;
}>();
const emit = defineEmits(['close', 'after-leave', 'done']);

const overlay = useOverlayStack();
const service = createAdmissionsService();

const submitting = ref(false);
const errorMessage = ref('');

const form = reactive<HealthPayload>({
	health_summary: '',
	medical_conditions: '',
	allergies: '',
	medications: '',
});

const overlayStyle = computed(() => ({
	zIndex: props.zIndex || 0,
}));

const isReadOnly = computed(() => Boolean(props.readOnly));

function setError(err: unknown, fallback: string) {
	const msg =
		(typeof err === 'object' && err && 'message' in (err as any)
			? String((err as any).message)
			: '') ||
		(typeof err === 'string' ? err : '') ||
		fallback;
	errorMessage.value = msg;
}

function clearError() {
	errorMessage.value = '';
}

function resetForm() {
	form.health_summary = props.initial?.health_summary || '';
	form.medical_conditions = props.initial?.medical_conditions || '';
	form.allergies = props.initial?.allergies || '';
	form.medications = props.initial?.medications || '';
}

function emitClose(reason: CloseReason) {
	const overlayId = props.overlayId || null;
	if (overlayId) {
		try {
			overlay.close(overlayId);
			return;
		} catch {
			// fall through
		}
	}
	emit('close', reason);
}

function emitAfterLeave() {
	clearError();
	emit('after-leave');
}

function onDialogClose(_payload: unknown) {
	// no-op (A+ contract)
}

function onKeydown(e: KeyboardEvent) {
	if (!props.open) return;
	if (e.key === 'Escape') emitClose('esc');
}

watch(
	() => props.open,
	val => {
		if (val) {
			resetForm();
			document.addEventListener('keydown', onKeydown, true);
		} else {
			document.removeEventListener('keydown', onKeydown, true);
		}
	},
	{ immediate: true }
);

onBeforeUnmount(() => {
	document.removeEventListener('keydown', onKeydown, true);
});

async function submit() {
	if (isReadOnly.value) {
		setError('', __('This application is read-only.'));
		return;
	}
	submitting.value = true;
	clearError();
	try {
		await service.updateHealth({
			health_summary: form.health_summary,
			medical_conditions: form.medical_conditions,
			allergies: form.allergies,
			medications: form.medications,
		});
		emitClose('programmatic');
		emit('done');
	} catch (err) {
		setError(err, __('Unable to save health information.'));
	} finally {
		submitting.value = false;
	}
}
</script>
