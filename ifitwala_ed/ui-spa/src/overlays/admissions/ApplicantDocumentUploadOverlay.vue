<!-- ifitwala_ed/ui-spa/src/overlays/admissions/ApplicantDocumentUploadOverlay.vue -->

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
								<DialogTitle class="type-h2 text-ink">{{ __('Upload document') }}</DialogTitle>
								<p class="mt-1 type-caption text-ink/60">
									{{ documentLabel || __('Provide the requested document for your application.') }}
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

							<div
								class="rounded-2xl border border-dashed border-border/70 bg-white px-4 py-4 shadow-soft"
							>
								<input
									ref="fileInput"
									type="file"
									class="block w-full type-caption text-ink"
									:disabled="isReadOnly || submitting"
									@change="onFileSelected"
								/>
								<p class="mt-2 type-caption text-ink/55">
									{{ selectedFile?.name || __('Choose a file to upload.') }}
								</p>
							</div>

							<div class="rounded-2xl border border-border/70 bg-white px-4 py-4 shadow-soft">
								<label class="type-caption text-ink/70" for="item-label-input">
									{{ __('File description') }}
								</label>
								<input
									id="item-label-input"
									v-model="itemLabelValue"
									type="text"
									class="mt-2 block w-full rounded-xl border border-border/70 px-3 py-2 type-caption text-ink"
									:placeholder="__('Example: AISL transcript 2019')"
									:disabled="isReadOnly || submitting"
								/>
								<p class="mt-2 type-caption text-ink/55">
									{{ __('This label helps admissions review each uploaded file separately.') }}
								</p>
							</div>

							<p v-if="description" class="type-caption text-ink/60">
								{{ description }}
							</p>
						</div>

						<div
							class="if-overlay__footer px-6 pb-6 flex flex-wrap items-center justify-between gap-3"
						>
							<p class="type-caption text-ink/55">
								{{
									isReadOnly
										? __('This application is read-only.')
										: __('Uploads are reviewed by admissions staff.')
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
										<Spinner class="h-4 w-4" /> {{ __('Uploading…') }}
									</span>
									<span v-else>{{ __('Upload') }}</span>
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

const props = defineProps<{
	open: boolean;
	zIndex?: number;
	overlayId?: string;
	documentType?: string;
	documentLabel?: string;
	description?: string;
	mode?: 'add' | 'replace';
	applicantDocumentItem?: string | null;
	itemKey?: string | null;
	itemLabel?: string | null;
	readOnly?: boolean;
}>();
const emit = defineEmits(['close', 'after-leave', 'done']);

const overlay = useOverlayStack();
const service = createAdmissionsService();

const submitting = ref(false);
const errorMessage = ref('');
const selectedFile = ref<File | null>(null);
const itemLabelValue = ref('');

const fileInput = ref<HTMLInputElement | null>(null);

const overlayStyle = computed(() => ({
	zIndex: props.zIndex || 0,
}));

const isReadOnly = computed(() => Boolean(props.readOnly));
const documentLabel = computed(() => props.documentLabel || '');
const description = computed(() => props.description || '');
const mode = computed(() => (props.mode === 'replace' ? 'replace' : 'add'));

function setError(err: unknown, fallback: string) {
	const raw =
		(typeof err === 'object' && err && 'message' in (err as any)
			? String((err as any).message)
			: '') ||
		(typeof err === 'string' ? err : '') ||
		'';
	errorMessage.value = normalizeUploadErrorMessage(raw, fallback);
}

function clearError() {
	errorMessage.value = '';
}

function normalizeUploadErrorMessage(raw: string, fallback: string): string {
	const msg = (raw || '').trim();
	if (!msg) return fallback;
	const lower = msg.toLowerCase();
	if (lower.includes('outside the applicant scope')) {
		return __(
			'This document request is no longer available for your application. Refresh the page and try again.'
		);
	}
	if (
		lower.includes('not configured for uploads') ||
		lower.includes('missing upload classification settings') ||
		lower.includes('retention policy defined')
	) {
		return __(
			'This document upload is temporarily unavailable. Please contact the admissions office.'
		);
	}
	return msg;
}

function resetForm() {
	selectedFile.value = null;
	itemLabelValue.value = (props.itemLabel || '').trim();
	if (fileInput.value) fileInput.value.value = '';
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
	resetForm();
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

function onFileSelected(event: Event) {
	const target = event.target as HTMLInputElement | null;
	const file = target?.files?.[0] || null;
	selectedFile.value = file;
}

async function readAsBase64(file: File): Promise<string> {
	return new Promise((resolve, reject) => {
		const reader = new FileReader();
		reader.onerror = () => reject(new Error('Unable to read file'));
		reader.onload = () => {
			const result = typeof reader.result === 'string' ? reader.result : '';
			const parts = result.split(',');
			resolve(parts.length > 1 ? parts[1] : result);
		};
		reader.readAsDataURL(file);
	});
}

async function submit() {
	if (isReadOnly.value) {
		setError('', __('This application is read-only.'));
		return;
	}
	if (!props.documentType) {
		setError('', __('Document type is required.'));
		return;
	}
	if (!selectedFile.value) {
		setError('', __('Please choose a file to upload.'));
		return;
	}
	const trimmedItemLabel = itemLabelValue.value.trim();
	if (!trimmedItemLabel) {
		setError('', __('Please provide a short description for this file.'));
		return;
	}

	submitting.value = true;
	clearError();
	try {
		const content = await readAsBase64(selectedFile.value);
		const clientRequestId = `admissions_upload_${Date.now()}_${Math.random().toString(16).slice(2)}`;
		await service.uploadDocument({
			document_type: props.documentType,
			applicant_document_item: props.applicantDocumentItem || null,
			item_key: mode.value === 'replace' ? props.itemKey || null : null,
			item_label: trimmedItemLabel,
			client_request_id: clientRequestId,
			file_name: selectedFile.value.name,
			content,
		});
		emitClose('programmatic');
		emit('done');
	} catch (err) {
		setError(err, __('Unable to upload document.'));
	} finally {
		submitting.value = false;
	}
}
</script>
