<template>
	<article :class="panelClasses">
		<div v-if="!hideHeader" class="flex items-center justify-between gap-3">
			<div>
				<p class="type-overline text-ink/60">{{ eyebrow }}</p>
				<h2 class="mt-1 type-h3 text-ink">{{ title }}</h2>
				<p class="mt-2 type-caption text-ink/70">{{ description }}</p>
			</div>
			<span class="chip">{{ resources.length }}</span>
		</div>

		<div
			v-if="!anchorName"
			:class="[
				panelSectionOffset,
				'rounded-2xl border border-dashed border-line-soft bg-surface-soft px-4 py-4',
			]"
		>
			<p class="type-body-strong text-ink">Resource sharing is blocked here.</p>
			<p class="mt-1 type-caption text-ink/70">{{ blockedMessage }}</p>
		</div>

		<template v-else>
			<div
				v-if="shouldShowReadOnlyNotice"
				:class="[
					panelSectionOffset,
					'rounded-2xl border border-line-soft bg-surface-soft px-4 py-4',
				]"
			>
				<p class="type-body-strong text-ink">Resources are visible here, but editing is locked.</p>
				<p class="mt-1 type-caption text-ink/70">{{ readOnlyMessageToUse }}</p>
			</div>

			<section
				v-if="canManageResources"
				:class="[panelSectionOffset, 'rounded-2xl border border-line-soft bg-surface-soft p-5']"
			>
				<div class="if-segmented flex-wrap">
					<button
						type="button"
						data-resource-mode="link"
						class="if-segmented__item"
						:class="{ 'if-segmented__item--active': composerMode === 'link' }"
						@click="composerMode = 'link'"
					>
						Add link
					</button>
					<button
						type="button"
						data-resource-mode="file"
						class="if-segmented__item"
						:class="{ 'if-segmented__item--active': composerMode === 'file' }"
						@click="composerMode = 'file'"
					>
						Upload file
					</button>
				</div>

				<div class="mt-4 grid gap-4 md:grid-cols-2">
					<div class="space-y-1">
						<label class="type-label">Title</label>
						<FormControl v-model="form.title" type="text" placeholder="Resource title" />
						<p v-if="composerMode === 'link'" class="type-caption text-ink/60">
							Leave this blank to use the link domain as the title.
						</p>
					</div>
					<div class="space-y-1">
						<label class="type-label">How students use it</label>
						<FormControl
							v-model="form.modality"
							type="select"
							:options="modalityOptions"
							option-label="label"
							option-value="value"
						/>
					</div>
				</div>

				<div class="mt-4 grid gap-4 md:grid-cols-2">
					<div class="space-y-1">
						<label class="type-label">Usage role</label>
						<FormControl
							v-model="form.usage_role"
							type="select"
							:options="usageRoleOptions"
							option-label="label"
							option-value="value"
						/>
					</div>
					<div class="space-y-1">
						<label class="type-label">Teacher note</label>
						<FormControl
							v-model="form.placement_note"
							type="text"
							placeholder="Optional note students should see"
						/>
					</div>
				</div>

				<div class="mt-4 space-y-1">
					<label class="type-label">Description</label>
					<FormControl
						v-model="form.description"
						type="textarea"
						:rows="3"
						placeholder="Optional context for this resource"
					/>
				</div>

				<div v-if="composerMode === 'link'" class="mt-4 space-y-1">
					<label class="type-label">Reference URL</label>
					<FormControl v-model="form.reference_url" type="text" placeholder="https://..." />
				</div>

				<div v-else class="mt-4 space-y-3">
					<input ref="fileInput" type="file" class="hidden" @change="onFileSelected" />
					<div class="flex flex-wrap items-center gap-3">
						<button
							type="button"
							class="if-button if-button--secondary"
							data-resource-choose-file="true"
							@click="fileInput?.click()"
						>
							Choose file
						</button>
						<p class="type-caption text-ink/70">
							{{ selectedFile?.name || 'No file selected yet.' }}
						</p>
					</div>
					<InlineUploadStatus
						v-if="uploadProgress"
						:label="uploadProgressLabel"
						:progress="uploadProgress"
					/>
				</div>

				<div
					v-if="errorMessage"
					class="mt-4 rounded-xl border border-flame/30 bg-flame/10 px-4 py-3 text-sm text-flame"
				>
					{{ errorMessage }}
				</div>

				<div class="mt-4 flex justify-end">
					<button
						type="button"
						class="if-button if-button--primary"
						:disabled="!canSubmit || submitting"
						@click="addResource"
					>
						{{
							submitting
								? composerMode === 'link'
									? 'Adding…'
									: 'Uploading…'
								: composerMode === 'link'
									? 'Add link'
									: 'Upload file'
						}}
					</button>
				</div>
			</section>

			<section :class="[panelSectionOffset, 'space-y-3']">
				<div
					v-if="!resources.length"
					class="rounded-2xl border border-dashed border-line-soft px-4 py-4"
				>
					<p class="type-caption text-ink/70">{{ emptyMessage }}</p>
				</div>

				<article
					v-for="resource in resources"
					:key="resource.placement || resource.material"
					class="rounded-2xl border border-line-soft bg-surface-soft p-4"
				>
					<AttachmentPreviewCard
						v-if="resource.attachment_preview"
						:attachment="resource.attachment_preview"
						variant="planning"
						:title="resource.title"
						:description="resourceDescription(resource)"
						:meta-text="resourceMetaLine(resource)"
						:chips="resourceChips(resource)"
						:enable-preview-surface="enableAttachmentPreview"
					>
						<template #extra-actions>
							<button
								v-if="resource.placement && canManageResources"
								type="button"
								class="if-button if-button--danger"
								:disabled="removingPlacement === resource.placement"
								@click="removeResource(resource.placement)"
							>
								{{ removingPlacement === resource.placement ? 'Removing…' : 'Remove' }}
							</button>
						</template>
					</AttachmentPreviewCard>
				</article>
			</section>
		</template>
	</article>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue';
import { FormControl, toast } from 'frappe-ui';

import AttachmentPreviewCard from '@/components/attachments/AttachmentPreviewCard.vue';
import InlineUploadStatus from '@/components/feedback/InlineUploadStatus.vue';
import type { UploadProgressState } from '@/lib/uploadProgress';
import {
	createPlanningReferenceMaterial,
	removePlanningMaterial,
	uploadPlanningMaterialFile,
	type PlanningMaterialAnchorDoctype,
} from '@/lib/services/staff/staffTeachingService';
import type { StaffPlanningMaterial } from '@/types/contracts/staff_teaching/get_staff_class_planning_surface';

const props = withDefaults(
	defineProps<{
		anchorDoctype: PlanningMaterialAnchorDoctype;
		anchorName?: string | null;
		eyebrow: string;
		title: string;
		description: string;
		emptyMessage: string;
		blockedMessage: string;
		canManage?: boolean;
		readOnlyMessage?: string;
		showReadOnlyNotice?: boolean;
		resources: StaffPlanningMaterial[];
		enableAttachmentPreview?: boolean;
		hideHeader?: boolean;
		embedded?: boolean;
	}>(),
	{
		canManage: true,
		showReadOnlyNotice: true,
		enableAttachmentPreview: false,
		hideHeader: false,
		embedded: false,
	}
);

const emit = defineEmits<{
	(e: 'changed'): void;
}>();

const composerMode = ref<'link' | 'file'>('link');
const submitting = ref(false);
const removingPlacement = ref<string | null>(null);
const errorMessage = ref('');
const selectedFile = ref<File | null>(null);
const fileInput = ref<HTMLInputElement | null>(null);
const uploadProgress = ref<UploadProgressState | null>(null);

const form = reactive({
	title: '',
	description: '',
	reference_url: '',
	modality: 'Read',
	usage_role: 'Reference',
	placement_note: '',
});

const modalityOptions = [
	{ label: 'Read', value: 'Read' },
	{ label: 'Watch', value: 'Watch' },
	{ label: 'Listen', value: 'Listen' },
	{ label: 'Use', value: 'Use' },
];

const usageRoleOptions = [
	{ label: 'Required', value: 'Required' },
	{ label: 'Reference', value: 'Reference' },
	{ label: 'Template', value: 'Template' },
	{ label: 'Example', value: 'Example' },
];

const hideHeader = computed(() => props.hideHeader);
const canManageResources = computed(() => props.canManage !== false);
const shouldShowReadOnlyNotice = computed(
	() => !canManageResources.value && props.showReadOnlyNotice !== false
);
const panelClasses = computed(() =>
	props.embedded ? 'space-y-0' : 'rounded-[2rem] border border-line-soft bg-white p-6 shadow-soft'
);
const panelSectionOffset = computed(() => (hideHeader.value ? '' : 'mt-5'));
const readOnlyMessageToUse = computed(
	() =>
		props.readOnlyMessage ||
		'You can review the shared resources here, but only approved staff can edit this planning layer.'
);

const canSubmit = computed(() => {
	if (!canManageResources.value) return false;
	if (!props.anchorName?.trim()) return false;
	return composerMode.value === 'link'
		? Boolean(normalizeReferenceUrl(form.reference_url))
		: Boolean(selectedFile.value) && Boolean(form.title.trim());
});
const uploadProgressLabel = computed(() =>
	selectedFile.value?.name ? `Uploading ${selectedFile.value.name}` : 'Uploading file'
);

function resetDraftFields() {
	form.title = '';
	form.description = '';
	form.reference_url = '';
	form.modality = 'Read';
	form.usage_role = 'Reference';
	form.placement_note = '';
	selectedFile.value = null;
	if (fileInput.value) fileInput.value.value = '';
}

function onFileSelected(event: Event) {
	const target = event.target as HTMLInputElement | null;
	const file = target?.files?.[0] || null;
	selectedFile.value = file;
	errorMessage.value = '';
	if (file && !form.title.trim()) {
		form.title = file.name;
	}
}

async function addResource() {
	if (!props.anchorName) {
		toast.error(props.blockedMessage);
		return;
	}
	if (!canManageResources.value) {
		toast.error(readOnlyMessageToUse.value);
		return;
	}
	if (!canSubmit.value) {
		errorMessage.value =
			composerMode.value === 'link'
				? 'Provide a valid http or https link.'
				: 'Provide a title and choose a file.';
		return;
	}

	submitting.value = true;
	errorMessage.value = '';
	try {
		if (composerMode.value === 'link') {
			const referenceUrl = normalizeReferenceUrl(form.reference_url);
			if (!referenceUrl) {
				throw new Error('Provide a valid http or https link.');
			}
			await createPlanningReferenceMaterial({
				anchor_doctype: props.anchorDoctype,
				anchor_name: props.anchorName,
				title: resolveReferenceTitle(form.title, referenceUrl),
				reference_url: referenceUrl,
				description: form.description.trim() || undefined,
				modality: form.modality,
				usage_role: form.usage_role,
				placement_note: form.placement_note.trim() || undefined,
			});
		} else if (selectedFile.value) {
			await uploadPlanningMaterialFile(
				{
					anchor_doctype: props.anchorDoctype,
					anchor_name: props.anchorName,
					title: form.title.trim(),
					file: selectedFile.value,
					description: form.description.trim() || undefined,
					modality: form.modality,
					usage_role: form.usage_role,
					placement_note: form.placement_note.trim() || undefined,
				},
				{
					onProgress: progress => {
						uploadProgress.value = progress;
					},
				}
			);
		}
		resetDraftFields();
		emit('changed');
		toast.success('Resource shared successfully.');
	} catch (error) {
		const message =
			error instanceof Error ? error.message : 'Unable to share this resource right now.';
		errorMessage.value = message;
		toast.error(message);
	} finally {
		uploadProgress.value = null;
		submitting.value = false;
	}
}

async function removeResource(placement: string) {
	if (!props.anchorName || !placement) return;
	if (!canManageResources.value) {
		toast.error(readOnlyMessageToUse.value);
		return;
	}
	removingPlacement.value = placement;
	errorMessage.value = '';
	try {
		await removePlanningMaterial({
			anchor_doctype: props.anchorDoctype,
			anchor_name: props.anchorName,
			placement,
		});
		emit('changed');
		toast.success('Resource removed from this class context.');
	} catch (error) {
		const message =
			error instanceof Error ? error.message : 'Unable to remove this resource right now.';
		errorMessage.value = message;
		toast.error(message);
	} finally {
		removingPlacement.value = null;
	}
}

function normalizeReferenceUrl(value: string): string {
	const trimmed = String(value || '').trim();
	if (!trimmed) return '';
	try {
		const parsed = new URL(trimmed);
		return parsed.protocol === 'http:' || parsed.protocol === 'https:' ? trimmed : '';
	} catch {
		return '';
	}
}

function resolveReferenceTitle(title: string, referenceUrl: string): string {
	const explicitTitle = String(title || '').trim();
	if (explicitTitle) return explicitTitle;
	return deriveTitleFromUrl(referenceUrl);
}

function deriveTitleFromUrl(referenceUrl: string): string {
	try {
		const parsed = new URL(referenceUrl);
		return (parsed.hostname || referenceUrl).replace(/^www\./, '') || referenceUrl;
	} catch {
		return referenceUrl;
	}
}

function resourceDescription(resource: StaffPlanningMaterial): string | null {
	return resource.description || null;
}

function resourceMetaLine(resource: StaffPlanningMaterial): string | null {
	return (
		[resource.placement_note, resource.file_name || resource.reference_url]
			.filter(Boolean)
			.join(' · ') || null
	);
}

function resourceChips(resource: StaffPlanningMaterial): string[] {
	return [resource.material_type || null, resource.usage_role || null].filter(Boolean) as string[];
}
</script>
