<!-- ifitwala_ed/ui-spa/src/pages/admissions/ApplicantDocuments.vue -->

<template>
	<div class="admissions-page">
		<header class="page-header">
			<div class="page-header__intro">
				<h1 class="type-h1 text-ink">{{ __('Documents') }}</h1>
				<p class="type-meta text-ink/70">
					{{ __('Upload the documents requested by the admissions team.') }}
				</p>
			</div>
		</header>

		<div v-if="loading" class="rounded-2xl border border-border/70 bg-surface px-4 py-4">
			<div class="flex items-center gap-3">
				<Spinner class="h-4 w-4" />
				<p class="type-body-strong text-ink">{{ __('Loading documents…') }}</p>
			</div>
		</div>

		<div v-else-if="error" class="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3">
			<p class="type-body-strong text-rose-900">{{ __('Unable to load documents') }}</p>
			<p class="mt-1 type-caption text-rose-900/80 whitespace-pre-wrap">{{ error }}</p>
			<button type="button" class="if-button if-button--secondary mt-3" @click="loadDocuments">
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
						class="if-button if-button--primary"
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
							<span
								v-if="doc.is_repeatable"
								class="rounded-full border border-sky-200 bg-sky-50 px-2 py-0.5 type-caption text-sky-900"
							>
								{{ __('Multiple files') }}
							</span>
						</div>
						<p class="mt-1 type-caption" :class="doc.statusTone">{{ doc.statusLabel }}</p>
						<p v-if="doc.countSummary" class="mt-1 type-caption text-ink/55">
							{{ doc.countSummary }}
						</p>
						<p v-if="doc.description" class="mt-1 type-caption text-ink/60">
							{{ doc.description }}
						</p>
						<p v-if="doc.overrideReason" class="mt-1 type-caption text-ink/60">
							{{ doc.overrideReason }}
						</p>
					</div>
					<div class="flex items-center gap-3">
						<button
							type="button"
							class="if-button if-button--primary"
							:disabled="isReadOnly || !doc.canAddItem"
							@click="openUpload(doc, null)"
						>
							{{ doc.items.length ? __('Add file') : __('Upload file') }}
						</button>
					</div>
				</div>

				<div v-if="doc.items.length" class="mt-4 space-y-3">
					<div
						v-for="item in doc.items"
						:key="`${doc.key}:${item.name || item.item_key}`"
						class="rounded-xl border border-border/60 bg-surface/50 px-3 py-3"
					>
						<AttachmentPreviewCard
							v-if="item.attachment_preview"
							:attachment="item.attachment_preview"
							variant="planning"
							:title="item.item_label || item.item_key"
							:chips="[itemStatusLabel(item)]"
							:meta-text="item.uploaded_at ? `${__('Uploaded')}: ${item.uploaded_at}` : ''"
						>
							<template #extra-actions>
								<button
									type="button"
									class="if-action"
									:disabled="isReadOnly || !doc.canUpload"
									@click="openUpload(doc, item)"
								>
									{{ __('Replace') }}
								</button>
							</template>
						</AttachmentPreviewCard>
						<div v-else class="flex flex-wrap items-start justify-between gap-3">
							<div>
								<p class="type-body-strong text-ink">{{ item.item_label || item.item_key }}</p>
								<p class="mt-1 type-caption" :class="statusToneFor(itemStatusKey(item))">
									{{ itemStatusLabel(item) }}
								</p>
								<p v-if="item.uploaded_at" class="mt-1 type-caption text-ink/55">
									{{ __('Uploaded') }}: {{ item.uploaded_at }}
								</p>
							</div>
							<div class="flex items-center gap-2">
								<a
									v-if="item.open_url"
									:href="item.open_url"
									target="_blank"
									rel="noopener"
									class="if-action"
								>
									{{ __('View') }}
								</a>
								<button
									type="button"
									class="if-action"
									:disabled="isReadOnly || !doc.canUpload"
									@click="openUpload(doc, item)"
								>
									{{ __('Replace') }}
								</button>
							</div>
						</div>
					</div>
				</div>

				<div
					v-else
					class="mt-4 rounded-xl border border-dashed border-border/70 bg-surface/40 px-3 py-3"
				>
					<p class="type-caption text-ink/60">{{ __('No files uploaded yet.') }}</p>
				</div>
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

import AttachmentPreviewCard from '@/components/attachments/AttachmentPreviewCard.vue';
import { createAdmissionsService } from '@/lib/services/admissions/admissionsService';
import { useOverlayStack } from '@/composables/useOverlayStack';
import { useAdmissionsSession } from '@/composables/useAdmissionsSession';
import { __ } from '@/lib/i18n';
import { uiSignals, SIGNAL_ADMISSIONS_PORTAL_INVALIDATE } from '@/lib/uiSignals';
import type { ApplicantDocument } from '@/types/contracts/admissions/types';
import type { AttachmentPreviewItem } from '@/types/contracts/attachments/shared';
import type { Response as DocumentTypesResponse } from '@/types/contracts/admissions/list_applicant_document_types';
import type { Response as DocumentsResponse } from '@/types/contracts/admissions/list_applicant_documents';

const service = createAdmissionsService();
const overlay = useOverlayStack();
const { session, currentApplicantName } = useAdmissionsSession();

const documents = ref<DocumentsResponse['documents']>([]);
const documentTypes = ref<DocumentTypesResponse['document_types']>([]);
const loading = ref(false);
const error = ref<string | null>(null);
const actionError = ref('');

const isReadOnly = computed(() => Boolean(session.value?.applicant?.is_read_only));

type DisplayItem = {
	name: string;
	item_key: string;
	item_label: string;
	review_status: string;
	uploaded_at?: string | null;
	open_url?: string | null;
	preview_url?: string | null;
	thumbnail_url?: string | null;
	preview_status?: string | null;
	file_name?: string | null;
	drive_file_id?: string | null;
	canonical_ref?: string | null;
	attachment_preview?: AttachmentPreviewItem | null;
};

type DisplayDocument = {
	key: string;
	document_type: string;
	label: string;
	description: string;
	overrideReason?: string | null;
	is_required: boolean;
	is_repeatable: boolean;
	requiredCount: number;
	uploadedCount: number;
	approvedCount: number;
	items: DisplayItem[];
	statusKey: string;
	statusLabel: string;
	statusTone: string;
	countSummary: string;
	canUpload: boolean;
	canAddItem: boolean;
};

function itemStatusKey(item: DisplayItem): string {
	if (!item.open_url) return 'missing';
	if (item.review_status === 'Approved') return 'approved';
	if (item.review_status === 'Rejected') return 'rejected';
	return 'pending';
}

function itemStatusLabel(item: DisplayItem): string {
	const statusKey = itemStatusKey(item);
	if (statusKey === 'approved') return __('Approved');
	if (statusKey === 'rejected') return __('Changes requested');
	if (statusKey === 'pending') return __('Uploaded - waiting for review');
	return __('Missing');
}

function statusToneFor(statusKey: string): string {
	switch (statusKey) {
		case 'approved':
		case 'complete':
		case 'waived':
		case 'exception_approved':
			return 'text-leaf';
		case 'rejected':
		case 'changes_requested':
		case 'missing':
		case 'not_started':
			return 'text-rose-700';
		case 'pending':
		case 'waiting_review':
			return 'text-clay';
		default:
			return 'text-ink/55';
	}
}

function statusSortWeight(statusKey: string): number {
	switch (statusKey) {
		case 'missing':
		case 'not_started':
			return 0;
		case 'rejected':
		case 'changes_requested':
			return 1;
		case 'pending':
		case 'waiting_review':
			return 2;
		case 'approved':
		case 'complete':
		case 'waived':
		case 'exception_approved':
			return 3;
		default:
			return 4;
	}
}

function summarizeDocumentStatus(doc: {
	is_required: boolean;
	required_count: number;
	uploaded_count: number;
	approved_count: number;
	has_rejected: boolean;
}): { key: string; label: string } {
	if (!doc.is_required) {
		if (!doc.uploaded_count) return { key: 'optional', label: __('Optional') };
		if (doc.approved_count >= doc.uploaded_count)
			return { key: 'approved', label: __('Approved') };
		if (doc.has_rejected) return { key: 'rejected', label: __('Needs replacement') };
		return { key: 'pending', label: __('Pending review') };
	}

	if (doc.uploaded_count < doc.required_count) {
		return {
			key: 'missing',
			label: __('Uploaded {0} of {1} required files.')
				.replace('{0}', String(doc.uploaded_count))
				.replace('{1}', String(doc.required_count)),
		};
	}
	if (doc.approved_count < doc.required_count) {
		if (doc.has_rejected) {
			return {
				key: 'rejected',
				label: __('Approved {0} of {1} required files (replace rejected files).')
					.replace('{0}', String(doc.approved_count))
					.replace('{1}', String(doc.required_count)),
			};
		}
		return {
			key: 'pending',
			label: __('Approved {0} of {1} required files.')
				.replace('{0}', String(doc.approved_count))
				.replace('{1}', String(doc.required_count)),
		};
	}

	return {
		key: 'approved',
		label: __('Approved {0} of {1} required files.')
			.replace('{0}', String(doc.approved_count))
			.replace('{1}', String(doc.required_count)),
	};
}

const displayDocuments = computed<DisplayDocument[]>(() => {
	const docMap = new Map<string, ApplicantDocument>();
	documents.value.forEach(doc => {
		if (doc.document_type) docMap.set(doc.document_type, doc);
	});

	const items: DisplayDocument[] = documentTypes.value.map(docType => {
		const doc = docMap.get(docType.name) || null;
		const documentItems: DisplayItem[] = ((doc?.items || []) as DisplayItem[]).map(row => ({
			name: String(row.name || ''),
			item_key: String(row.item_key || ''),
			item_label: String(row.item_label || ''),
			review_status: String(row.review_status || 'Pending'),
			uploaded_at: row.uploaded_at || null,
			open_url: row.open_url || null,
			preview_url: row.preview_url || null,
			thumbnail_url: row.thumbnail_url || null,
			preview_status: row.preview_status || null,
			file_name: row.file_name || null,
			drive_file_id: row.drive_file_id || null,
			canonical_ref: row.canonical_ref || null,
			attachment_preview: row.attachment_preview || null,
		}));

		const requiredCount =
			typeof doc?.required_count === 'number'
				? doc.required_count
				: docType.is_required
					? docType.is_repeatable
						? Math.max(1, Number(docType.min_items_required || 1))
						: 1
					: 0;
		const uploadedCount =
			typeof doc?.uploaded_count === 'number'
				? doc.uploaded_count
				: documentItems.filter(row => Boolean(row.open_url)).length;
		const approvedCount =
			typeof doc?.approved_count === 'number'
				? doc.approved_count
				: documentItems.filter(row => Boolean(row.open_url) && row.review_status === 'Approved')
						.length;
		const hasRejected = documentItems.some(
			row => Boolean(row.open_url) && row.review_status === 'Rejected'
		);
		const fallbackSummary = summarizeDocumentStatus({
			is_required: Boolean(docType.is_required),
			required_count: requiredCount,
			uploaded_count: uploadedCount,
			approved_count: approvedCount,
			has_rejected: hasRejected,
		});
		const statusKey = String(doc?.requirement_state || '').trim() || fallbackSummary.key;
		const statusLabel = String(doc?.requirement_state_label || '').trim() || fallbackSummary.label;
		const requirementOverride = String(doc?.requirement_override || '').trim();
		const countSummary = requirementOverride
			? ''
			: requiredCount
				? __('Approved {0} of {1} required files.')
						.replace('{0}', String(approvedCount))
						.replace('{1}', String(requiredCount))
				: uploadedCount
					? __('Uploaded {0} file(s).').replace('{0}', String(uploadedCount))
					: '';

		return {
			key: docType.name,
			document_type: docType.name,
			label: String(doc?.label || docType.document_type_name || docType.code || docType.name),
			description: String(doc?.description || docType.description || ''),
			overrideReason: doc?.override_reason || null,
			is_required: Boolean(docType.is_required),
			is_repeatable: Boolean(docType.is_repeatable),
			requiredCount,
			uploadedCount,
			approvedCount,
			items: documentItems,
			statusKey,
			statusLabel,
			statusTone: statusToneFor(statusKey),
			countSummary,
			canUpload: !requirementOverride,
			canAddItem:
				!requirementOverride && (Boolean(docType.is_repeatable) || documentItems.length === 0),
		};
	});

	documents.value.forEach(doc => {
		if (!doc.document_type || items.find(item => item.document_type === doc.document_type)) return;
		const documentItems: DisplayItem[] = ((doc.items || []) as DisplayItem[]).map(row => ({
			name: String(row.name || ''),
			item_key: String(row.item_key || ''),
			item_label: String(row.item_label || ''),
			review_status: String(row.review_status || 'Pending'),
			uploaded_at: row.uploaded_at || null,
			open_url: row.open_url || null,
			preview_url: row.preview_url || null,
			thumbnail_url: row.thumbnail_url || null,
			preview_status: row.preview_status || null,
			file_name: row.file_name || null,
			drive_file_id: row.drive_file_id || null,
			canonical_ref: row.canonical_ref || null,
			attachment_preview: row.attachment_preview || null,
		}));
		const uploadedCount = documentItems.filter(row => Boolean(row.open_url)).length;
		const approvedCount = documentItems.filter(
			row => Boolean(row.open_url) && row.review_status === 'Approved'
		).length;
		items.push({
			key: doc.document_type,
			document_type: doc.document_type,
			label: String(doc.label || doc.document_type),
			description: String(doc.description || ''),
			overrideReason: doc.override_reason || null,
			is_required: false,
			is_repeatable: Boolean(doc.is_repeatable),
			requiredCount: 0,
			uploadedCount,
			approvedCount,
			items: documentItems,
			statusKey: String(doc.requirement_state || '').trim() || 'optional',
			statusLabel: String(doc.requirement_state_label || '').trim() || __('Optional'),
			statusTone: statusToneFor(String(doc.requirement_state || '').trim() || 'optional'),
			countSummary: uploadedCount
				? __('Uploaded {0} file(s).').replace('{0}', String(uploadedCount))
				: '',
			canUpload: !doc.requirement_override,
			canAddItem:
				!doc.requirement_override && (Boolean(doc.is_repeatable) || documentItems.length === 0),
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
	() =>
		requiredDocuments.value.filter(doc =>
			['complete', 'approved', 'waived', 'exception_approved'].includes(doc.statusKey)
		).length
);
const nextRequiredDoc = computed(
	() =>
		requiredDocuments.value.find(
			doc => !['complete', 'approved', 'waived', 'exception_approved'].includes(doc.statusKey)
		) || null
);
const requiredSummaryText = computed(() => {
	const total = requiredTotalCount.value;
	const approved = requiredApprovedCount.value;
	if (!total) return __('No required documents configured.');
	if (approved < total) {
		return __('Complete or approved {0} of {1} required document types.')
			.replace('{0}', String(approved))
			.replace('{1}', String(total));
	}
	return __('Complete or approved {0} of {1} required document types.')
		.replace('{0}', String(approved))
		.replace('{1}', String(total));
});

async function loadDocuments() {
	if (!currentApplicantName.value) {
		documents.value = [];
		documentTypes.value = [];
		error.value = null;
		return;
	}
	loading.value = true;
	error.value = null;
	actionError.value = '';
	try {
		const [docsResp, typesResp] = await Promise.all([
			service.listDocuments({ student_applicant: currentApplicantName.value }),
			service.listDocumentTypes({ student_applicant: currentApplicantName.value }),
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

function openUpload(doc: DisplayDocument, item: DisplayItem | null) {
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
		actionError.value = __(
			'This requirement is already completed by admissions and does not need another upload.'
		);
		return;
	}
	if (!item && !doc.canAddItem) {
		actionError.value = __('This document accepts one file. Use Replace on the existing item.');
		return;
	}
	actionError.value = '';
	overlay.open('admissions-document-upload', {
		studentApplicant: currentApplicantName.value,
		documentType: doc.document_type,
		documentLabel: doc.label,
		description: doc.description || '',
		readOnly: isReadOnly.value,
		applicantDocumentItem: item?.name || null,
		itemKey: item?.item_key || null,
		itemLabel: item?.item_label || '',
		mode: item ? 'replace' : 'add',
	});
}

function openNextRequired() {
	if (!nextRequiredDoc.value) {
		actionError.value = __('All required documents are already approved.');
		return;
	}
	openUpload(nextRequiredDoc.value, null);
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
