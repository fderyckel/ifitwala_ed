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
				v-if="requiredTotalCount"
				class="rounded-2xl border border-border/70 bg-sand/30 px-4 py-4 shadow-soft"
			>
				<div class="flex flex-wrap items-center justify-between gap-3">
					<div>
						<p class="type-body-strong text-ink">{{ __('Required documents') }}</p>
						<p class="mt-1 type-caption text-ink/65">{{ requiredSummaryText }}</p>
					</div>
					<button
						type="button"
						class="rounded-full bg-ink px-4 py-2 type-caption text-white shadow-soft disabled:opacity-50"
						:disabled="isReadOnly || !nextRequiredDoc"
						@click="openNextRequired"
					>
						{{ __('Upload next required') }}
					</button>
				</div>
			</div>
			<div
				v-for="doc in displayDocuments"
				:key="doc.key"
				class="rounded-2xl border border-border/70 bg-white px-4 py-4 shadow-soft"
			>
				<div class="flex flex-wrap items-center justify-between gap-3">
					<div>
						<div class="flex flex-wrap items-center gap-2">
							<p class="type-body-strong text-ink">{{ doc.label }}</p>
							<span
								class="rounded-full border px-2 py-0.5 type-caption"
								:class="
									doc.is_required
										? 'border-amber-300 bg-amber-50 text-amber-900'
										: 'border-border/70 bg-surface text-ink/60'
								"
							>
								{{ doc.is_required ? __('Required') : __('Optional') }}
							</span>
						</div>
						<p class="mt-1 type-caption" :class="doc.statusTone">{{ doc.statusLabel }}</p>
						<p
							v-if="doc.is_required && doc.statusKey !== 'approved'"
							class="mt-1 type-caption text-ink/55"
						>
							{{ __('Needed before submission.') }}
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
							:disabled="isReadOnly || !doc.document_type || !doc.canUpload"
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
import { __ } from '@/lib/i18n';
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

function statusKeyFor(doc: ApplicantDocument | null, isRequired: boolean) {
	if (!doc) return isRequired ? 'missing' : 'optional';
	if (doc.review_status === 'Approved') return 'approved';
	if (doc.review_status === 'Rejected') return 'rejected';
	return 'pending';
}

function statusLabelFor(statusKey: string) {
	switch (statusKey) {
		case 'approved':
			return __('Approved');
		case 'rejected':
			return __('Rejected');
		case 'pending':
			return __('Pending review');
		case 'missing':
			return __('Missing');
		case 'optional':
		default:
			return __('Optional');
	}
}

function statusToneFor(statusKey: string) {
	switch (statusKey) {
		case 'approved':
			return 'text-leaf';
		case 'rejected':
		case 'missing':
			return 'text-rose-700';
		case 'pending':
			return 'text-sun';
		case 'optional':
		default:
			return 'text-ink/55';
	}
}

function statusSortWeight(statusKey: string) {
	switch (statusKey) {
		case 'missing':
			return 0;
		case 'rejected':
			return 1;
		case 'pending':
			return 2;
		case 'approved':
			return 3;
		case 'optional':
		default:
			return 4;
	}
}

const displayDocuments = computed(() => {
	const docMap = new Map<string, ApplicantDocument>();
	documents.value.forEach(doc => {
		if (doc.document_type) docMap.set(doc.document_type, doc);
	});

	const items = documentTypes.value.map(docType => {
		const doc = docMap.get(docType.name) || null;
		const statusKey = statusKeyFor(doc, docType.is_required);
		return {
			key: docType.name,
			document_type: docType.name,
			label: docType.document_type_name || docType.code || docType.name,
			description: docType.description,
			is_required: docType.is_required,
			file_url: doc?.file_url || null,
			uploaded_at: doc?.uploaded_at || null,
			statusKey,
			statusLabel: statusLabelFor(statusKey),
			statusTone: statusToneFor(statusKey),
			canUpload: true,
		};
	});

	// Include documents that aren't in the type list
	documents.value.forEach(doc => {
		if (!doc.document_type || items.find(item => item.document_type === doc.document_type)) return;
		const statusKey = statusKeyFor(doc, false);
		items.push({
			key: doc.document_type,
			document_type: doc.document_type,
			label: doc.document_type,
			description: '',
			is_required: false,
			file_url: doc.file_url || null,
			uploaded_at: doc.uploaded_at || null,
			statusKey,
			statusLabel: statusLabelFor(statusKey),
			statusTone: statusToneFor(statusKey),
			canUpload: false,
		});
	});

	return items.sort((a, b) => {
		if (a.is_required !== b.is_required) return a.is_required ? -1 : 1;
		const byStatus = statusSortWeight(a.statusKey) - statusSortWeight(b.statusKey);
		if (byStatus) return byStatus;
		return a.label.localeCompare(b.label);
	});
});

const requiredDocuments = computed(() => displayDocuments.value.filter(doc => doc.is_required));
const requiredTotalCount = computed(() => requiredDocuments.value.length);
const requiredApprovedCount = computed(
	() => requiredDocuments.value.filter(doc => doc.statusKey === 'approved').length
);
const nextRequiredDoc = computed(
	() => requiredDocuments.value.find(doc => doc.statusKey !== 'approved') || null
);
const requiredSummaryText = computed(() => {
	const total = requiredTotalCount.value;
	const approved = requiredApprovedCount.value;
	if (!total) return __('No required documents configured.');
	return __('Approved {0} of {1} required documents.')
		.replace('{0}', String(approved))
		.replace('{1}', String(total));
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

function openUpload(doc: {
	document_type: string;
	label: string;
	description?: string;
	canUpload?: boolean;
}) {
	if (isReadOnly.value) {
		actionError.value = __('This application is read-only.');
		return;
	}
	if (!doc.document_type) {
		actionError.value = __(
			'This document request is incomplete. Please contact the admissions office.'
		);
		return;
	}
	if (!doc.canUpload) {
		actionError.value = __('This document can no longer be uploaded from the applicant portal.');
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

function openNextRequired() {
	if (!nextRequiredDoc.value) {
		actionError.value = __('All required documents are already approved.');
		return;
	}
	openUpload(nextRequiredDoc.value);
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
