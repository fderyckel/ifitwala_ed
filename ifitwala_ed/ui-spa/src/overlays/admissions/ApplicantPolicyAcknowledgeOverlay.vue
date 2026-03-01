<!-- ifitwala_ed/ui-spa/src/overlays/admissions/ApplicantPolicyAcknowledgeOverlay.vue -->

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
								<DialogTitle class="type-h2 text-ink">{{
									policyName || __('Policy acknowledgement')
								}}</DialogTitle>
								<p class="mt-1 type-caption text-ink/60">
									{{ __('Please review the policy text before acknowledging.') }}
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

							<div class="rounded-2xl border border-border/70 bg-white p-4 shadow-soft">
								<div class="type-body text-ink/80 whitespace-pre-wrap" v-html="policyContent" />
							</div>

							<div class="rounded-2xl border border-border/70 bg-white p-4 shadow-soft space-y-3">
								<div>
									<p class="type-body-strong text-ink">{{ __('Electronic signature') }}</p>
									<p class="mt-1 type-caption text-ink/65">
										{{
											__('Type your full name and confirm attestation before signing this policy.')
										}}
									</p>
								</div>

								<p class="type-caption text-ink/70">
									{{ __('Expected signer name:') }}
									<span class="type-body-strong text-ink">{{ expectedSignerLabel }}</span>
								</p>

								<label class="block space-y-1">
									<span class="type-caption text-ink/70">{{
										__('Type full name as electronic signature')
									}}</span>
									<input
										v-model="typedSignatureName"
										type="text"
										class="if-input w-full"
										:placeholder="__('Enter your full name')"
										:disabled="isReadOnly || submitting"
										@input="signatureTouched = true"
									/>
								</label>

								<p
									v-if="signatureTouched && typedSignatureName.trim() && !isTypedSignatureMatch"
									class="type-caption text-ink/70"
								>
									{{ __('Typed signature must match exactly:') }} {{ expectedSignerLabel }}
								</p>

								<label class="flex items-start gap-2">
									<input
										v-model="attestationConfirmed"
										type="checkbox"
										class="mt-1 h-4 w-4"
										:disabled="isReadOnly || submitting"
									/>
									<span class="type-caption text-ink/80">
										{{
											__(
												'I confirm that typing my name is my electronic signature, and I have read, acknowledged, and agree to this policy.'
											)
										}}
									</span>
								</label>
							</div>
						</div>

						<div
							class="if-overlay__footer px-6 pb-6 flex flex-wrap items-center justify-between gap-3"
						>
							<p class="type-caption text-ink/55">
								{{
									isReadOnly
										? __('This application is read-only.')
										: __('Acknowledgements are permanent.')
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
										<Spinner class="h-4 w-4" /> {{ __('Signing…') }}
									</span>
									<span v-else>{{ __('Sign and acknowledge policy') }}</span>
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
import { computed, onBeforeUnmount, ref, watch } from 'vue';
import {
	Dialog,
	DialogPanel,
	DialogTitle,
	TransitionChild,
	TransitionRoot,
} from '@headlessui/vue';
import { FeatherIcon, Spinner } from 'frappe-ui';

import { useOverlayStack } from '@/composables/useOverlayStack';
import { __ } from '@/lib/i18n';
import { createAdmissionsService } from '@/lib/services/admissions/admissionsService';

type CloseReason = 'backdrop' | 'esc' | 'programmatic';

type PolicyPayload = {
	name: string;
	policy_version: string;
	content_html: string;
	expected_signer_name?: string;
};

const props = defineProps<{
	open: boolean;
	zIndex?: number;
	overlayId?: string;
	policy?: PolicyPayload | null;
	readOnly?: boolean;
}>();
const emit = defineEmits(['close', 'after-leave', 'done']);

const overlay = useOverlayStack();
const service = createAdmissionsService();

const submitting = ref(false);
const errorMessage = ref('');
const typedSignatureName = ref('');
const attestationConfirmed = ref(false);
const signatureTouched = ref(false);

const overlayStyle = computed(() => ({
	zIndex: props.zIndex || 0,
}));

const isReadOnly = computed(() => Boolean(props.readOnly));
const policyName = computed(() => props.policy?.name || '');
const policyContent = computed(() => props.policy?.content_html || '');
const expectedSignerLabel = computed(
	() => String(props.policy?.expected_signer_name || '').trim() || __('Applicant record')
);

function normalizeName(value: string): string {
	return value.trim().replace(/\s+/g, ' ').toLowerCase();
}

const isTypedSignatureMatch = computed(() => {
	const typed = normalizeName(typedSignatureName.value || '');
	if (!typed) return false;
	const expected = normalizeName(expectedSignerLabel.value || '');
	return expected ? typed === expected : true;
});

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

function resetSignatureFields() {
	typedSignatureName.value = '';
	attestationConfirmed.value = false;
	signatureTouched.value = false;
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
			resetSignatureFields();
			clearError();
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
	if (!props.policy?.policy_version) {
		setError('', __('Policy version is required.'));
		return;
	}
	signatureTouched.value = true;
	if (!typedSignatureName.value.trim()) {
		setError('', __('Type your full name to provide your electronic signature.'));
		return;
	}
	if (!isTypedSignatureMatch.value) {
		setError('', `${__('Typed signature must match exactly:')} ${expectedSignerLabel.value}`);
		return;
	}
	if (!attestationConfirmed.value) {
		setError('', __('Confirm the legal attestation before signing.'));
		return;
	}

	submitting.value = true;
	clearError();
	try {
		await service.acknowledgePolicy({
			policy_version: props.policy.policy_version,
			typed_signature_name: typedSignatureName.value.trim(),
			attestation_confirmed: attestationConfirmed.value ? 1 : 0,
		});
		emitClose('programmatic');
		emit('done');
	} catch (err) {
		setError(err, __('Unable to acknowledge policy.'));
	} finally {
		submitting.value = false;
	}
}
</script>
