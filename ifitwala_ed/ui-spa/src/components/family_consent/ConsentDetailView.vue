<template>
	<div class="portal-page">
		<header class="card-surface p-5 sm:p-6">
			<div class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
				<div>
					<p class="type-overline text-ink/60">{{ portalLabel }}</p>
					<h1 class="type-h1 text-ink">{{ titleLabel }}</h1>
					<p class="type-body text-ink/70">
						Review the request details, confirm any prefilled data, and submit your decision.
					</p>
				</div>
				<RouterLink :to="{ name: backRouteName }" class="if-button if-button--quiet">
					Back to forms
				</RouterLink>
			</div>
		</header>

		<section v-if="loading" class="card-surface p-5">
			<p class="type-body text-ink/70">Loading form details...</p>
		</section>

		<section v-else-if="errorMessage" class="card-surface p-5">
			<p class="type-body-strong text-flame">Could not load this form request.</p>
			<p class="type-body text-ink/70">{{ errorMessage }}</p>
		</section>

		<template v-else-if="detail">
			<section class="student-hub-section">
				<div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
					<div>
						<p class="type-caption text-ink/60">
							{{ detail.target.student_name
							}}<span v-if="detail.target.school"> · {{ detail.target.school }}</span>
						</p>
						<h2 class="type-h2 text-ink">{{ detail.request.request_title }}</h2>
						<p class="mt-2 type-body text-ink/70">
							{{ detail.request.request_type }} · {{ detail.request.decision_mode }}
						</p>
						<div class="mt-3 flex flex-wrap gap-2">
							<span class="chip">{{ detail.target.current_status_label }}</span>
							<span class="chip">{{ detail.request.completion_channel_mode }}</span>
							<span v-if="detail.request.due_on" class="chip"
								>Due {{ detail.request.due_on }}</span
							>
						</div>
					</div>
					<div class="rounded-xl border border-line-soft bg-surface-soft p-4 lg:max-w-sm">
						<p class="type-caption text-ink/60">Expected signer</p>
						<p class="type-body-strong text-ink">{{ detail.signer.expected_signature_name }}</p>
						<p class="mt-2 type-caption text-ink/60">
							Status: {{ detail.target.current_status_label }}
						</p>
					</div>
				</div>
			</section>

			<section
				v-if="detail.request.completion_channel_mode === 'Paper Only'"
				class="student-hub-section border border-sand/60 bg-sand/30"
			>
				<p class="type-body-strong text-clay">Paper return is required for this request.</p>
				<p class="mt-2 type-body text-ink/70">
					This form stays visible here for monitoring, but portal submission is disabled because
					staff must collect the signed paper copy.
				</p>
			</section>

			<section
				v-else-if="submitBlockedReason"
				class="student-hub-section border border-line-soft bg-surface-soft"
			>
				<p class="type-body-strong text-ink">{{ submitBlockedReason }}</p>
			</section>

			<section class="student-hub-section space-y-4">
				<div>
					<h2 class="type-h3 text-ink">Request details</h2>
					<p class="mt-1 type-caption text-ink/60">
						Review the instructions and the prefilled values below before you sign.
					</p>
				</div>
				<div
					class="portal-richtext prose prose-sm max-w-none text-ink/80"
					v-html="trustedHtml(detail.request.request_text)"
				/>
			</section>

			<section class="student-hub-section space-y-4">
				<div>
					<h2 class="type-h3 text-ink">Form fields</h2>
					<p class="mt-1 type-caption text-ink/60">
						Known profile data is already placed into the form. Editable fields can be corrected
						here without retyping everything else.
					</p>
				</div>

				<div class="space-y-4">
					<article
						v-for="field in detail.fields"
						:key="field.field_key"
						class="rounded-xl border border-line-soft bg-white p-4"
					>
						<div class="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
							<div>
								<p class="type-body-strong text-ink">
									{{ field.field_label }}
									<span v-if="field.required" class="type-caption text-flame">*</span>
								</p>
								<p v-if="field.binding_label" class="mt-1 type-caption text-ink/60">
									{{ field.binding_label }}
								</p>
							</div>
							<span class="chip">{{ field.field_mode }}</span>
						</div>

						<div v-if="field.field_mode === 'Allow Override'" class="mt-4 space-y-3">
							<label v-if="field.field_type === 'Long Text'" class="block space-y-1">
								<span class="type-caption text-ink/70">Updated value</span>
								<textarea
									:model-value="textDraftValue(field)"
									class="if-input min-h-[132px] w-full"
									@input="setTextDraft(field, $event)"
								/>
							</label>

							<label v-else-if="field.field_type === 'Checkbox'" class="flex items-start gap-2">
								<input
									:checked="Boolean(fieldDraftValue(field))"
									type="checkbox"
									class="mt-1 h-4 w-4"
									@change="setCheckboxDraft(field, $event)"
								/>
								<span class="type-body text-ink/80">{{ field.field_label }}</span>
							</label>

							<div v-else-if="field.field_type === 'Address'" class="grid gap-3 sm:grid-cols-2">
								<label class="block space-y-1 sm:col-span-2">
									<span class="type-caption text-ink/70">Address line 1</span>
									<input
										:value="addressDraftValue(field).address_line1 || ''"
										type="text"
										class="if-input w-full"
										@input="setAddressDraftValue(field, 'address_line1', $event)"
									/>
								</label>
								<label class="block space-y-1 sm:col-span-2">
									<span class="type-caption text-ink/70">Address line 2</span>
									<input
										:value="addressDraftValue(field).address_line2 || ''"
										type="text"
										class="if-input w-full"
										@input="setAddressDraftValue(field, 'address_line2', $event)"
									/>
								</label>
								<label class="block space-y-1">
									<span class="type-caption text-ink/70">City</span>
									<input
										:value="addressDraftValue(field).city || ''"
										type="text"
										class="if-input w-full"
										@input="setAddressDraftValue(field, 'city', $event)"
									/>
								</label>
								<label class="block space-y-1">
									<span class="type-caption text-ink/70">State</span>
									<input
										:value="addressDraftValue(field).state || ''"
										type="text"
										class="if-input w-full"
										@input="setAddressDraftValue(field, 'state', $event)"
									/>
								</label>
								<label class="block space-y-1">
									<span class="type-caption text-ink/70">Postal code</span>
									<input
										:value="addressDraftValue(field).pincode || ''"
										type="text"
										class="if-input w-full"
										@input="setAddressDraftValue(field, 'pincode', $event)"
									/>
								</label>
								<label class="block space-y-1">
									<span class="type-caption text-ink/70">Country</span>
									<input
										:value="addressDraftValue(field).country || ''"
										type="text"
										class="if-input w-full"
										@input="setAddressDraftValue(field, 'country', $event)"
									/>
								</label>
							</div>

							<label v-else class="block space-y-1">
								<span class="type-caption text-ink/70">Updated value</span>
								<input
									:value="textDraftValue(field)"
									:type="inputType(field)"
									class="if-input w-full"
									@input="setTextDraft(field, $event)"
								/>
							</label>

							<p class="type-caption text-ink/60">Current value: {{ formatValue(field) }}</p>
							<p v-if="field.allow_profile_writeback" class="type-caption text-ink/60">
								If this value changes, you can choose whether it updates only this form or your
								saved profile everywhere.
							</p>
						</div>

						<div v-else class="mt-4 rounded-xl border border-line-soft bg-surface-soft p-3">
							<p class="type-body text-ink/85">{{ formatValue(field) }}</p>
						</div>
					</article>
				</div>
			</section>

			<section class="student-hub-section space-y-4">
				<div>
					<h2 class="type-h3 text-ink">Electronic signature</h2>
					<p class="mt-1 type-caption text-ink/60">
						Type your full name exactly as recorded and confirm the legal attestation before you
						submit.
					</p>
				</div>

				<label class="block space-y-1">
					<span class="type-caption text-ink/70">Expected signer name</span>
					<p class="type-body-strong text-ink">{{ detail.signer.expected_signature_name }}</p>
				</label>

				<label class="block space-y-1">
					<span class="type-caption text-ink/70">Type full name as electronic signature</span>
					<input
						v-model="typedSignatureName"
						type="text"
						class="if-input w-full"
						:placeholder="'Enter your full name'"
					/>
				</label>

				<p
					v-if="
						detail.request.requires_typed_signature &&
						typedSignatureName.trim() &&
						!isTypedSignatureMatch
					"
					class="type-caption text-flame"
				>
					Typed signature must match exactly: {{ detail.signer.expected_signature_name }}
				</p>

				<label class="flex items-start gap-2">
					<input v-model="attestationConfirmed" type="checkbox" class="mt-1 h-4 w-4" />
					<span class="type-caption text-ink/80">
						I confirm that typing my name is my electronic signature and that I am submitting this
						decision knowingly.
					</span>
				</label>

				<p v-if="submitError" class="type-body text-flame">{{ submitError }}</p>

				<div class="flex flex-wrap gap-3">
					<button
						v-if="canSubmit"
						type="button"
						class="if-button if-button--secondary"
						:disabled="submitting"
						@click="handleSubmit(negativeDecision.status)"
					>
						{{
							submitting && activeDecisionStatus === negativeDecision.status
								? 'Saving…'
								: negativeDecision.label
						}}
					</button>
					<button
						v-if="canSubmit"
						type="button"
						class="if-button if-button--primary"
						:disabled="submitting"
						@click="handleSubmit(positiveDecision.status)"
					>
						{{
							submitting && activeDecisionStatus === positiveDecision.status
								? 'Saving…'
								: positiveDecision.label
						}}
					</button>
				</div>
			</section>

			<section class="student-hub-section space-y-4">
				<div>
					<h2 class="type-h3 text-ink">History</h2>
					<p class="mt-1 type-caption text-ink/60">
						Previous decisions for this signer stay attached to the request as audit history.
					</p>
				</div>
				<div v-if="!detail.history.length" class="rounded-xl border border-line-soft bg-white p-4">
					<p class="type-body text-ink/70">No decision history yet.</p>
				</div>
				<ul v-else class="space-y-3">
					<li
						v-for="(item, index) in detail.history"
						:key="`${item.decision_status}:${item.decision_at}:${index}`"
						class="rounded-xl border border-line-soft bg-white p-4"
					>
						<div class="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
							<div>
								<p class="type-body-strong text-ink">{{ item.decision_status }}</p>
								<p class="mt-1 type-caption text-ink/65">{{ item.source_channel }}</p>
							</div>
							<p class="type-caption text-ink/60">{{ item.decision_at }}</p>
						</div>
					</li>
				</ul>
			</section>
		</template>
	</div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { RouterLink } from 'vue-router';
import { toast } from 'frappe-ui';

import { useOverlayStack } from '@/composables/useOverlayStack';
import {
	buildConsentFieldDraftValue,
	emptyAddressValue,
	formatConsentValue,
	isConsentFieldChanged,
	normalizeConsentFieldValue,
} from '@/lib/familyConsent/consentFieldUtils';

import type {
	ConsentAddressValue,
	ConsentDetailRequestBlock,
	ConsentDetailSignerBlock,
	ConsentDetailTargetBlock,
	ConsentFieldRow,
	ConsentFieldValue,
} from '@/types/contracts/family_consent/shared';

type DetailResponse = {
	meta: { generated_at: string };
	request: ConsentDetailRequestBlock;
	target: ConsentDetailTargetBlock;
	signer: ConsentDetailSignerBlock;
	fields: ConsentFieldRow[];
	history: Array<{
		decision_status: string;
		decision_at: string;
		decision_by_doctype: string;
		decision_by: string;
		source_channel: string;
	}>;
};

type SubmitResponse = {
	ok: boolean;
	status: 'submitted' | 'already_current';
	decision_name: string;
	request_key: string;
	student: string;
	current_status: string;
	profile_writeback_mode?: string | null;
};

const props = defineProps<{
	portalLabel: string;
	titleLabel: string;
	backRouteName: string;
	requestKey: string;
	studentId: string;
	loadDetail: (payload: { request_key: string; student: string }) => Promise<DetailResponse>;
	submitDecision: (payload: {
		request_key: string;
		student: string;
		decision_status: string;
		typed_signature_name?: string;
		attestation_confirmed?: number;
		field_values?: Array<{ field_key: string; value: ConsentFieldValue }>;
		profile_writeback_mode?: 'Form Only' | 'Update Profile';
	}) => Promise<SubmitResponse>;
}>();

const overlay = useOverlayStack();

const loading = ref(true);
const submitting = ref(false);
const activeDecisionStatus = ref('');
const errorMessage = ref('');
const submitError = ref('');
const detail = ref<DetailResponse | null>(null);
const typedSignatureName = ref('');
const attestationConfirmed = ref(false);
const fieldDrafts = ref<Record<string, ConsentFieldValue>>({});

const positiveDecision = computed(() =>
	detail.value?.request.decision_mode === 'Grant / Deny'
		? { label: 'Grant', status: 'Granted' }
		: { label: 'Approve', status: 'Approved' }
);
const negativeDecision = computed(() =>
	detail.value?.request.decision_mode === 'Grant / Deny'
		? { label: 'Deny', status: 'Denied' }
		: { label: 'Decline', status: 'Declined' }
);
const isTypedSignatureMatch = computed(() => {
	if (!detail.value) return false;
	const typed = typedSignatureName.value.trim().replace(/\s+/g, ' ').toLowerCase();
	if (!typed) return false;
	return (
		typed === detail.value.signer.expected_signature_name.trim().replace(/\s+/g, ' ').toLowerCase()
	);
});
const submitBlockedReason = computed(() => {
	if (!detail.value) return '';
	if (detail.value.request.status && detail.value.request.status !== 'Published') {
		return 'This request is no longer open for portal submission.';
	}
	if (detail.value.request.completion_channel_mode === 'Paper Only') {
		return 'Paper return is required for this request.';
	}
	if (detail.value.target.current_status === 'completed') {
		return 'This request is already complete for this signer.';
	}
	if (detail.value.target.current_status === 'declined') {
		return 'This request has already been declined for this signer.';
	}
	if (detail.value.target.current_status === 'withdrawn') {
		return 'This request was previously withdrawn for this signer.';
	}
	if (detail.value.target.current_status === 'expired') {
		return 'This request has expired and can no longer be completed in portal.';
	}
	return '';
});
const canSubmit = computed(() => Boolean(detail.value) && !submitBlockedReason.value);

function trustedHtml(html: string): string {
	return String(html || '');
}

function syncDrafts() {
	const next: Record<string, ConsentFieldValue> = {};
	for (const field of detail.value?.fields || []) {
		if (field.field_mode === 'Allow Override') {
			next[field.field_key] = buildConsentFieldDraftValue(field);
		}
	}
	fieldDrafts.value = next;
}

function fieldDraftValue(field: ConsentFieldRow): ConsentFieldValue {
	return fieldDrafts.value[field.field_key] ?? buildConsentFieldDraftValue(field);
}

function textDraftValue(field: ConsentFieldRow): string {
	const value = fieldDraftValue(field);
	return typeof value === 'string' || typeof value === 'number' ? String(value) : '';
}

function addressDraftValue(field: ConsentFieldRow): ConsentAddressValue {
	const value = fieldDraftValue(field);
	if (value && typeof value === 'object' && !Array.isArray(value)) {
		return { ...emptyAddressValue(), ...(value as ConsentAddressValue) };
	}
	return emptyAddressValue();
}

function setTextDraft(field: ConsentFieldRow, event: Event) {
	fieldDrafts.value = {
		...fieldDrafts.value,
		[field.field_key]: normalizeConsentFieldValue(
			field.field_type,
			(event.target as HTMLInputElement | HTMLTextAreaElement).value
		),
	};
}

function setCheckboxDraft(field: ConsentFieldRow, event: Event) {
	fieldDrafts.value = {
		...fieldDrafts.value,
		[field.field_key]: Boolean((event.target as HTMLInputElement).checked),
	};
}

function setAddressDraftValue(
	field: ConsentFieldRow,
	key: keyof ConsentAddressValue,
	event: Event
) {
	const next = {
		...addressDraftValue(field),
		[key]: (event.target as HTMLInputElement).value,
	};
	fieldDrafts.value = {
		...fieldDrafts.value,
		[field.field_key]: normalizeConsentFieldValue(field.field_type, next),
	};
}

function inputType(field: ConsentFieldRow): string {
	if (field.field_type === 'Phone') return 'tel';
	if (field.field_type === 'Email') return 'email';
	if (field.field_type === 'Date') return 'date';
	return 'text';
}

function formatValue(field: ConsentFieldRow): string {
	return formatConsentValue(field.field_type, fieldDraftValue(field));
}

function writableChangedFields() {
	return (detail.value?.fields || [])
		.filter(field => field.field_mode === 'Allow Override')
		.filter(field => isConsentFieldChanged(field, fieldDraftValue(field)))
		.filter(field => field.allow_profile_writeback)
		.map(field => ({
			field_key: field.field_key,
			field_label: field.field_label,
			before_label: formatConsentValue(field.field_type, field.presented_value),
			after_label: formatConsentValue(field.field_type, fieldDraftValue(field)),
		}));
}

function buildSubmitFieldValues() {
	return (detail.value?.fields || [])
		.filter(field => field.field_mode === 'Allow Override')
		.map(field => ({
			field_key: field.field_key,
			value: normalizeConsentFieldValue(field.field_type, fieldDraftValue(field)),
		}));
}

function chooseProfileWritebackMode(
	changedFields: Array<{
		field_key: string;
		field_label: string;
		before_label: string;
		after_label: string;
	}>
): Promise<'Form Only' | 'Update Profile' | null> {
	return new Promise(resolve => {
		let settled = false;
		const finalize = (value: 'Form Only' | 'Update Profile' | null) => {
			if (settled) return;
			settled = true;
			resolve(value);
		};

		overlay.open('consent-profile-writeback', {
			changedFields,
			onSelect: (mode: 'Form Only' | 'Update Profile') => finalize(mode),
			onCancel: () => finalize(null),
		});
	});
}

async function handleSubmit(decisionStatus: string) {
	if (!detail.value) return;
	submitError.value = '';

	if (detail.value.request.requires_typed_signature && !typedSignatureName.value.trim()) {
		submitError.value = 'Type your full name as your electronic signature.';
		return;
	}
	if (detail.value.request.requires_typed_signature && !isTypedSignatureMatch.value) {
		submitError.value = `Typed signature must match exactly: ${detail.value.signer.expected_signature_name}`;
		return;
	}
	if (detail.value.request.requires_attestation && !attestationConfirmed.value) {
		submitError.value = 'Confirm the electronic signature attestation before signing.';
		return;
	}

	let profileWritebackMode: 'Form Only' | 'Update Profile' | undefined;
	const changedFields = writableChangedFields();
	if (changedFields.length) {
		const selectedMode = await chooseProfileWritebackMode(changedFields);
		if (!selectedMode) return;
		profileWritebackMode = selectedMode;
	}

	submitting.value = true;
	activeDecisionStatus.value = decisionStatus;
	try {
		const response = await props.submitDecision({
			request_key: props.requestKey,
			student: props.studentId,
			decision_status: decisionStatus,
			typed_signature_name: typedSignatureName.value.trim() || undefined,
			attestation_confirmed: attestationConfirmed.value ? 1 : 0,
			field_values: buildSubmitFieldValues(),
			profile_writeback_mode: profileWritebackMode,
		});
		toast.success(
			response.status === 'already_current'
				? 'This form was already up to date.'
				: 'Your decision was recorded successfully.'
		);
		await load();
	} catch (error) {
		submitError.value = error instanceof Error ? error.message : 'Unknown error';
	} finally {
		submitting.value = false;
		activeDecisionStatus.value = '';
	}
}

async function load() {
	loading.value = true;
	errorMessage.value = '';
	submitError.value = '';
	try {
		detail.value = await props.loadDetail({
			request_key: props.requestKey,
			student: props.studentId,
		});
		typedSignatureName.value = '';
		attestationConfirmed.value = false;
		syncDrafts();
	} catch (error) {
		errorMessage.value = error instanceof Error ? error.message : 'Unknown error';
	} finally {
		loading.value = false;
	}
}

onMounted(() => {
	load();
});
</script>
