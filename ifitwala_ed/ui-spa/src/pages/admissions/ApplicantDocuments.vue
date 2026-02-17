<!-- ifitwala_ed/ui-spa/src/pages/admissions/ApplicantDocuments.vue -->

<template>
	<div class="space-y-6">
		<div class="flex flex-wrap items-start justify-between gap-4">
			<div>
				<p class="type-h2 text-ink">{{ __('Documents') }}</p>
				<p class="mt-1 type-caption text-ink/60">
					{{ __('Upload the documents requested by the admissions team.') }}
				</p>
			</div>
		</div>

		<div v-if="loading" class="rounded-2xl border border-border/70 bg-surface px-4 py-4">
			<div class="flex items-center gap-3">
				<Spinner class="h-4 w-4" />
				<p class="type-body-strong text-ink">{{ __('Loading documents…') }}</p>
			</div>
		</div>

		<div v-else-if="error" class="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3">
			<p class="type-body-strong text-rose-900">{{ __('Unable to load documents') }}</p>
			<p class="mt-1 type-caption text-rose-900/80 whitespace-pre-wrap">{{ error }}</p>
			<button
				type="button"
				class="mt-3 rounded-full border border-rose-200 bg-white px-4 py-2 type-caption text-rose-900"
				@click="loadDocuments"
			>
				{{ __('Try again') }}
			</button>
		</div>

		<div v-else class="grid gap-4">
			<div v-if="actionError" class="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3">
				<p class="type-body-strong text-amber-900">{{ __('Notice') }}</p>
				<p class="mt-1 type-caption text-amber-900/80">{{ actionError }}</p>
			</div>
			<div
				v-for="doc in displayDocuments"
				:key="doc.key"
				class="rounded-2xl border border-border/70 bg-white px-4 py-4 shadow-soft"
			>
				<div class="flex flex-wrap items-center justify-between gap-3">
					<div>
						<p class="type-body-strong text-ink">{{ doc.label }}</p>
						<p class="mt-1 type-caption" :class="doc.statusTone">
							{{ doc.statusLabel }}
						</p>
						<p v-if="doc.uploaded_at" class="mt-1 type-caption text-ink/55">
							{{ __('Uploaded') }}: {{ doc.uploaded_at }}
						</p>
					</div>
					<div class="flex items-center gap-3">
						<a
							v-if="doc.file_url"
							:href="doc.file_url"
							target="_blank"
							rel="noopener"
							class="rounded-full border border-border/70 bg-white px-4 py-2 type-caption text-ink/70"
						>
							{{ __('View') }}
						</a>
						<button
							type="button"
							class="rounded-full bg-ink px-4 py-2 type-caption text-white shadow-soft disabled:opacity-50"
							:disabled="isReadOnly"
							@click="openUpload(doc)"
						>
							{{ doc.file_url ? __('Replace') : __('Upload') }}
						</button>
					</div>
				</div>
				<p v-if="doc.description" class="mt-2 type-caption text-ink/60">
					{{ doc.description }}
				</p>
			</div>

			<div
				v-if="!displayDocuments.length"
				class="rounded-2xl border border-border/70 bg-white px-4 py-4"
			>
				<p class="type-caption text-ink/60">
					{{ __('No document requests are configured yet.') }}
				</p>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { Spinner } from 'frappe-ui';

import { createAdmissionsService } from '@/lib/services/admissions/admissionsService';
import { useOverlayStack } from '@/composables/useOverlayStack';
import { useAdmissionsSession } from '@/composables/useAdmissionsSession';
import { uiSignals, SIGNAL_ADMISSIONS_PORTAL_INVALIDATE } from '@/lib/uiSignals';
import type { ApplicantDocument } from '@/types/contracts/admissions/types';
import type { Response as DocumentTypesResponse } from '@/types/contracts/admissions/list_applicant_document_types';
import type { Response as DocumentsResponse } from '@/types/contracts/admissions/list_applicant_documents';

const service = createAdmissionsService();
const overlay = useOverlayStack();
const { session } = useAdmissionsSession();

const documents = ref<DocumentsResponse['documents']>([]);
const documentTypes = ref<DocumentTypesResponse['document_types']>([]);
const loading = ref(false);
const error = ref<string | null>(null);
const actionError = ref('');

const isReadOnly = computed(() => Boolean(session.value?.applicant?.is_read_only));

function statusLabelFor(doc: ApplicantDocument | null, isRequired: boolean) {
	if (!doc) return isRequired ? __('Missing') : __('Optional');
	return doc.review_status === 'Approved'
		? __('Approved')
		: doc.review_status === 'Rejected'
			? __('Rejected')
			: __('Pending review');
}

function statusToneFor(doc: ApplicantDocument | null, isRequired: boolean) {
	if (!doc) return isRequired ? 'text-rose-700' : 'text-ink/55';
	if (doc.review_status === 'Approved') return 'text-leaf';
	if (doc.review_status === 'Rejected') return 'text-rose-700';
	return 'text-sun';
}

const displayDocuments = computed(() => {
	const docMap = new Map<string, ApplicantDocument>();
	documents.value.forEach(doc => {
		if (doc.document_type) docMap.set(doc.document_type, doc);
	});

	const items = documentTypes.value.map(docType => {
		const doc = docMap.get(docType.code || docType.name) || null;
		return {
			key: docType.code || docType.name,
			document_type: docType.code || docType.name,
			label: docType.document_type_name || docType.code,
			description: docType.description,
			is_required: docType.is_required,
			file_url: doc?.file_url || null,
			uploaded_at: doc?.uploaded_at || null,
			statusLabel: statusLabelFor(doc, docType.is_required),
			statusTone: statusToneFor(doc, docType.is_required),
		};
	});

	// Include documents that aren't in the type list
	documents.value.forEach(doc => {
		if (!doc.document_type || items.find(item => item.document_type === doc.document_type)) return;
		items.push({
			key: doc.document_type,
			document_type: doc.document_type,
			label: doc.document_type,
			description: '',
			is_required: false,
			file_url: doc.file_url || null,
			uploaded_at: doc.uploaded_at || null,
			statusLabel: statusLabelFor(doc, false),
			statusTone: statusToneFor(doc, false),
		});
	});

	return items;
});

async function loadDocuments() {
	loading.value = true;
	error.value = null;
	actionError.value = '';
	try {
		const [docsResp, typesResp] = await Promise.all([
			service.listDocuments(),
			service.listDocumentTypes(),
		]);
		documents.value = docsResp.documents || [];
		documentTypes.value = typesResp.document_types || [];
	} catch (err) {
		const message = err instanceof Error ? err.message : __('Unable to load documents.');
		error.value = message;
	} finally {
		loading.value = false;
	}
}

function openUpload(doc: { document_type: string; label: string; description?: string }) {
	if (isReadOnly.value) {
		actionError.value = __('This application is read-only.');
		return;
	}
	actionError.value = '';
	overlay.open('admissions-document-upload', {
		documentType: doc.document_type,
		documentLabel: doc.label,
		description: doc.description || '',
		readOnly: isReadOnly.value,
	});
}

let unsubscribe: (() => void) | null = null;

onMounted(async () => {
	await loadDocuments();
	unsubscribe = uiSignals.subscribe(SIGNAL_ADMISSIONS_PORTAL_INVALIDATE, () => {
		loadDocuments();
	});
});

onBeforeUnmount(() => {
	if (unsubscribe) unsubscribe();
});
</script>
