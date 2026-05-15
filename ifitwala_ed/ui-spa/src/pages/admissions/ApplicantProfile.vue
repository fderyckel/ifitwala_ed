<!-- ifitwala_ed/ui-spa/src/pages/admissions/ApplicantProfile.vue -->

<template>
	<div data-testid="admissions-profile-page" class="admissions-page">
		<header class="page-header">
			<div class="page-header__intro">
				<h1 class="type-h1 text-ink">{{ __('Profile information') }}</h1>
				<p class="type-meta text-ink/70">
					{{ __('Provide core student profile details used at promotion time.') }}
				</p>
			</div>
			<div class="page-header__actions">
				<button
					data-testid="admissions-profile-save"
					type="button"
					class="if-button if-button--primary"
					:disabled="
						isReadOnly ||
						loading ||
						saving ||
						uploadingImage ||
						uploadingGuardianImageIndex !== null ||
						Boolean(error)
					"
					@click="saveProfile"
				>
					<span v-if="saving">{{ __('Saving…') }}</span>
					<span v-else>{{ __('Save profile') }}</span>
				</button>
			</div>
		</header>

		<div v-if="loading" class="admissions-state-card">
			<div class="admissions-state-inline">
				<Spinner class="h-4 w-4" />
				<p class="type-body-strong text-ink">{{ __('Loading profile…') }}</p>
			</div>
		</div>

		<div v-else-if="error" class="if-banner if-banner--danger">
			<p class="if-banner__title type-body-strong">
				{{ __('Unable to load profile information') }}
			</p>
			<p class="if-banner__body mt-1 type-caption whitespace-pre-wrap">{{ error }}</p>
			<button type="button" class="if-button if-button--secondary mt-3" @click="loadProfile">
				{{ __('Try again') }}
			</button>
		</div>

		<div v-else class="space-y-4">
			<div v-if="actionError" class="admissions-card admissions-card--warm">
				<p class="type-body-strong text-clay">{{ __('Notice') }}</p>
				<p class="mt-1 type-caption text-clay/85">{{ actionError }}</p>
			</div>
			<div
				v-if="!options.languages.length || !options.countries.length"
				class="admissions-card admissions-card--warm"
			>
				<p class="type-body-strong text-clay">{{ __('Setup required') }}</p>
				<p class="mt-1 type-caption text-clay/85">
					{{
						__(
							'Some profile option lists are not configured yet. Please contact the admissions office.'
						)
					}}
				</p>
			</div>

			<div class="admissions-card admissions-card--plain">
				<div class="flex flex-wrap items-start justify-between gap-4">
					<div>
						<p class="type-body-strong text-ink">{{ __('Student image') }}</p>
						<p class="mt-1 type-caption text-ink/60">
							{{ __('Upload a clear photo of the student for identity and profile use.') }}
						</p>
						<p class="mt-2 type-caption text-ink/55">
							{{ acceptedImageHelpText }}
						</p>
					</div>
					<div class="flex flex-wrap items-center gap-2">
						<input
							ref="imageInput"
							type="file"
							:accept="acceptedImageInput"
							class="hidden"
							:disabled="isReadOnly || uploadingImage"
							@change="onImageSelected"
						/>
						<button
							type="button"
							class="if-button if-button--secondary"
							:disabled="isReadOnly || uploadingImage"
							@click="openImagePicker"
						>
							{{ __('Choose image') }}
						</button>
						<button
							type="button"
							class="if-button if-button--primary"
							:disabled="isReadOnly || uploadingImage || !selectedImageFile"
							@click="uploadSelectedImage"
						>
							<span v-if="uploadingImage">{{ __('Uploading…') }}</span>
							<span v-else>{{ __('Upload image') }}</span>
						</button>
					</div>
				</div>

				<p v-if="selectedImageFile" class="mt-2 type-caption text-ink/55">
					{{ __('Selected') }}: {{ selectedImageFile.name }}
				</p>
				<InlineUploadStatus
					v-if="imageUploadProgress"
					class="mt-3"
					:label="imageUploadProgressLabel"
					:progress="imageUploadProgress"
				/>

				<div class="mt-4 flex flex-wrap items-center gap-4">
					<div class="admissions-photo-frame h-24 w-24">
						<img
							v-if="applicantImage"
							:src="applicantImage"
							:alt="__('Student image')"
							class="h-full w-full object-cover"
						/>
						<div
							v-else
							class="flex h-full w-full items-center justify-center type-caption text-ink/55"
						>
							{{ __('No image') }}
						</div>
					</div>
					<div class="space-y-1">
						<p class="type-caption text-ink/60">
							{{
								hasApplicantImage
									? __('Current image is saved.')
									: __('No student image uploaded yet.')
							}}
						</p>
						<a
							v-if="applicantImageOpenUrl"
							:href="applicantImageOpenUrl"
							target="_blank"
							rel="noopener noreferrer"
							class="type-caption text-jacaranda underline"
						>
							{{ __('Open image in new tab') }}
						</a>
					</div>
				</div>
			</div>

			<div
				class="admissions-card"
				:class="completeness.ok ? 'admissions-card--success' : 'admissions-card--warm'"
			>
				<p class="type-body-strong" :class="completeness.ok ? 'text-canopy' : 'text-clay'">
					{{
						completeness.ok
							? __('Profile information complete')
							: __('Profile information still required')
					}}
				</p>
				<p v-if="!completeness.ok" class="mt-1 type-caption text-clay/85">
					{{ __('Missing: {0}', [completeness.missing.join(', ')]) }}
				</p>
			</div>

			<div class="admissions-card admissions-card--plain">
				<p class="type-body-strong text-ink">{{ __('Application details') }}</p>
				<div class="mt-3 grid gap-3 md:grid-cols-2">
					<div>
						<p class="type-caption text-ink/60">{{ __('School') }}</p>
						<p class="mt-1 type-body text-ink/80">{{ displayText(applicationContext.school) }}</p>
					</div>
					<div>
						<p class="type-caption text-ink/60">{{ __('Organization') }}</p>
						<p class="mt-1 type-body text-ink/80">
							{{ displayText(applicationContext.organization) }}
						</p>
					</div>
					<div>
						<p class="type-caption text-ink/60">{{ __('Academic year') }}</p>
						<p class="mt-1 type-body text-ink/80">
							{{ displayText(applicationContext.academic_year) }}
						</p>
					</div>
					<div>
						<p class="type-caption text-ink/60">{{ __('Program') }}</p>
						<p class="mt-1 type-body text-ink/80">{{ displayText(applicationContext.program) }}</p>
					</div>
				</div>
			</div>

			<div class="admissions-card admissions-card--plain">
				<p class="type-body-strong text-ink">{{ __('Student profile') }}</p>
				<div class="mt-4 grid gap-4 md:grid-cols-2">
					<label class="block">
						<span class="type-caption text-ink/60">{{ __('Preferred name') }}</span>
						<input
							v-model="profile.student_preferred_name"
							type="text"
							class="admissions-input mt-1"
							:disabled="isReadOnly || saving"
						/>
					</label>

					<label class="block">
						<span class="type-caption text-ink/60">{{ __('Date of birth') }}</span>
						<input
							v-model="profile.student_date_of_birth"
							type="date"
							class="admissions-input mt-1"
							:disabled="isReadOnly || saving"
						/>
					</label>

					<label class="block">
						<span class="type-caption text-ink/60">{{ __('Gender') }}</span>
						<select
							v-model="profile.student_gender"
							class="admissions-input mt-1"
							:disabled="isReadOnly || saving"
						>
							<option value="">{{ __('Select') }}</option>
							<option v-for="item in options.genders" :key="item" :value="item">
								{{ item }}
							</option>
						</select>
					</label>

					<label class="block">
						<span class="type-caption text-ink/60">{{ __('Mobile number') }}</span>
						<input
							v-model="profile.student_mobile_number"
							type="text"
							class="admissions-input mt-1"
							:disabled="isReadOnly || saving"
						/>
					</label>

					<label class="block">
						<span class="type-caption text-ink/60">{{ __('Admission date') }}</span>
						<input
							v-model="profile.student_joining_date"
							type="date"
							class="admissions-input mt-1"
							disabled
						/>
						<p class="mt-1 type-caption text-ink/55">
							{{ __('Set by the admissions office.') }}
						</p>
					</label>

					<label class="block">
						<span class="type-caption text-ink/60">{{ __('Residency status') }}</span>
						<select
							v-model="profile.residency_status"
							class="admissions-input mt-1"
							:disabled="isReadOnly || saving"
						>
							<option value="">{{ __('Select') }}</option>
							<option v-for="item in options.residency_statuses" :key="item" :value="item">
								{{ item }}
							</option>
						</select>
					</label>

					<label class="block">
						<span class="type-caption text-ink/60">{{ __('First language') }}</span>
						<select
							v-model="profile.student_first_language"
							class="admissions-input mt-1"
							:disabled="isReadOnly || saving"
						>
							<option value="">{{ __('Select') }}</option>
							<option
								v-for="item in options.languages"
								:key="`fl-${item.value}`"
								:value="item.value"
							>
								{{ item.label }}
							</option>
						</select>
					</label>

					<label class="block">
						<span class="type-caption text-ink/60">{{ __('Second language') }}</span>
						<select
							v-model="profile.student_second_language"
							class="admissions-input mt-1"
							:disabled="isReadOnly || saving"
						>
							<option value="">{{ __('Select') }}</option>
							<option
								v-for="item in options.languages"
								:key="`sl-${item.value}`"
								:value="item.value"
							>
								{{ item.label }}
							</option>
						</select>
					</label>

					<label class="block">
						<span class="type-caption text-ink/60">{{ __('Nationality') }}</span>
						<select
							v-model="profile.student_nationality"
							class="admissions-input mt-1"
							:disabled="isReadOnly || saving"
						>
							<option value="">{{ __('Select') }}</option>
							<option
								v-for="item in options.countries"
								:key="`nat-${item.value}`"
								:value="item.value"
							>
								{{ item.label }}
							</option>
						</select>
					</label>

					<label class="block">
						<span class="type-caption text-ink/60">{{ __('Second nationality') }}</span>
						<select
							v-model="profile.student_second_nationality"
							class="admissions-input mt-1"
							:disabled="isReadOnly || saving"
						>
							<option value="">{{ __('Select') }}</option>
							<option
								v-for="item in options.countries"
								:key="`nat2-${item.value}`"
								:value="item.value"
							>
								{{ item.label }}
							</option>
						</select>
					</label>
				</div>
			</div>

			<div v-if="guardiansEnabled" class="admissions-card admissions-card--plain">
				<div class="flex flex-wrap items-start justify-between gap-3">
					<div>
						<p class="type-body-strong text-ink">{{ __('Guardians') }}</p>
						<p class="mt-1 type-caption text-ink/60">
							{{
								__('Add one or more guardians and their contact details for promotion readiness.')
							}}
						</p>
					</div>
					<button
						type="button"
						class="if-button if-button--secondary"
						:disabled="isReadOnly || saving"
						@click="addGuardianRow"
					>
						{{ __('Add guardian') }}
					</button>
				</div>

				<div v-if="!guardians.length" class="mt-4 admissions-detail-card">
					<p class="type-body text-ink/70">{{ __('No guardians added yet.') }}</p>
				</div>

				<div v-else class="mt-4 space-y-4">
					<div
						v-for="(guardian, idx) in guardians"
						:key="guardian.name || `guardian-${idx}`"
						class="admissions-detail-card"
					>
						<div class="flex flex-wrap items-center justify-between gap-3">
							<p class="type-body-strong text-ink">
								{{ __('Guardian #{0}', [idx + 1]) }}
							</p>
							<button
								type="button"
								class="if-button if-button--danger"
								:disabled="isReadOnly || saving"
								@click="removeGuardianRow(idx)"
							>
								{{ __('Remove') }}
							</button>
						</div>

						<div class="mt-3 grid gap-4 md:grid-cols-2">
							<label class="block md:col-span-2">
								<span class="type-caption text-ink/60">{{ __('Relationship to student') }}</span>
								<select
									v-model="guardian.relationship"
									class="admissions-input mt-1"
									:disabled="isReadOnly || saving"
								>
									<option value="">{{ __('Select') }}</option>
									<option
										v-for="item in options.guardian_relationships || []"
										:key="`rel-${idx}-${item}`"
										:value="item"
									>
										{{ item }}
									</option>
								</select>
							</label>

							<label v-if="canUseApplicantContact" class="flex items-center gap-2 md:col-span-2">
								<input
									v-model="guardian.use_applicant_contact"
									type="checkbox"
									class="admissions-checkbox"
									:disabled="isReadOnly || saving"
									@change="onUseApplicantContactChanged(idx)"
								/>
								<span class="type-caption text-ink/70">{{
									__('Use applicant contact for this guardian')
								}}</span>
							</label>

							<div class="md:col-span-2">
								<p class="type-caption text-ink/60">{{ __('Tracked contact') }}</p>
								<p class="mt-1 type-body text-ink/80">{{ displayText(guardian.contact) }}</p>
							</div>

							<label class="block">
								<span class="type-caption text-ink/60">{{ __('Salutation') }}</span>
								<select
									v-model="guardian.salutation"
									class="admissions-input mt-1"
									:disabled="isReadOnly || saving"
								>
									<option value="">{{ __('Select') }}</option>
									<option
										v-for="item in options.salutations || []"
										:key="`sal-${idx}-${item.value}`"
										:value="item.value"
									>
										{{ item.label }}
									</option>
								</select>
							</label>

							<label class="block">
								<span class="type-caption text-ink/60">{{ __('Gender') }}</span>
								<select
									v-model="guardian.guardian_gender"
									class="admissions-input mt-1"
									:disabled="isReadOnly || saving"
								>
									<option value="">{{ __('Select') }}</option>
									<option
										v-for="item in options.guardian_genders || []"
										:key="`gg-${idx}-${item}`"
										:value="item"
									>
										{{ item }}
									</option>
								</select>
							</label>

							<label class="block">
								<span class="type-caption text-ink/60">{{ __('First name *') }}</span>
								<input
									v-model="guardian.guardian_first_name"
									type="text"
									required
									class="admissions-input mt-1"
									:disabled="isReadOnly || saving"
								/>
							</label>

							<label class="block">
								<span class="type-caption text-ink/60">{{ __('Last name *') }}</span>
								<input
									v-model="guardian.guardian_last_name"
									type="text"
									required
									class="admissions-input mt-1"
									:disabled="isReadOnly || saving"
								/>
							</label>

							<label class="block">
								<span class="type-caption text-ink/60">{{ __('Personal email *') }}</span>
								<input
									v-model="guardian.guardian_email"
									type="email"
									required
									class="admissions-input mt-1"
									:disabled="isReadOnly || saving"
								/>
							</label>

							<label class="block">
								<span class="type-caption text-ink/60">{{ __('Mobile phone *') }}</span>
								<input
									v-model="guardian.guardian_mobile_phone"
									type="text"
									required
									class="admissions-input mt-1"
									:disabled="isReadOnly || saving"
								/>
							</label>

							<label class="block">
								<span class="type-caption text-ink/60">{{ __('Employment sector') }}</span>
								<select
									v-model="guardian.employment_sector"
									class="admissions-input mt-1"
									:disabled="isReadOnly || saving"
								>
									<option value="">{{ __('Select') }}</option>
									<option
										v-for="item in options.guardian_employment_sectors || []"
										:key="`ges-${idx}-${item}`"
										:value="item"
									>
										{{ item }}
									</option>
								</select>
							</label>

							<label class="block">
								<span class="type-caption text-ink/60">{{ __('Work place') }}</span>
								<input
									v-model="guardian.work_place"
									type="text"
									class="admissions-input mt-1"
									:disabled="isReadOnly || saving"
								/>
							</label>

							<label class="block">
								<span class="type-caption text-ink/60">{{ __('Designation at work') }}</span>
								<input
									v-model="guardian.guardian_designation"
									type="text"
									class="admissions-input mt-1"
									:disabled="isReadOnly || saving"
								/>
							</label>

							<label class="block">
								<span class="type-caption text-ink/60">{{ __('Work email') }}</span>
								<input
									v-model="guardian.guardian_work_email"
									type="email"
									class="admissions-input mt-1"
									:disabled="isReadOnly || saving"
								/>
							</label>

							<label class="block">
								<span class="type-caption text-ink/60">{{ __('Work phone') }}</span>
								<input
									v-model="guardian.guardian_work_phone"
									type="text"
									class="admissions-input mt-1"
									:disabled="isReadOnly || saving"
								/>
							</label>

							<div class="block md:col-span-2">
								<p class="type-caption text-ink/60">{{ __('Photo *') }}</p>
								<p class="mt-1 type-caption text-ink/55">
									{{ acceptedImageHelpText }}
								</p>
								<div class="mt-2 flex flex-wrap items-center gap-2">
									<input
										:ref="element => setGuardianImageInputRef(idx, element)"
										type="file"
										:accept="acceptedImageInput"
										class="hidden"
										:disabled="isReadOnly || saving || uploadingGuardianImageIndex === idx"
										@change="event => onGuardianImageSelected(idx, event)"
									/>
									<button
										type="button"
										class="if-button if-button--secondary"
										:disabled="isReadOnly || saving || uploadingGuardianImageIndex === idx"
										@click="openGuardianImagePicker(idx)"
									>
										{{ __('Choose photo') }}
									</button>
									<button
										type="button"
										class="if-button if-button--primary"
										:disabled="
											isReadOnly ||
											saving ||
											uploadingGuardianImageIndex === idx ||
											!selectedGuardianImageFileName(idx)
										"
										@click="uploadGuardianImage(idx)"
									>
										<span v-if="uploadingGuardianImageIndex === idx">
											{{ __('Uploading…') }}
										</span>
										<span v-else>{{ __('Upload photo') }}</span>
									</button>
								</div>
								<p v-if="selectedGuardianImageFileName(idx)" class="mt-2 type-caption text-ink/55">
									{{ __('Selected') }}: {{ selectedGuardianImageFileName(idx) }}
								</p>
								<InlineUploadStatus
									v-if="guardianUploadProgress(idx)"
									class="mt-3"
									:label="guardianUploadProgressLabel(idx)"
									:progress="guardianUploadProgress(idx)!"
								/>
								<div class="mt-3 flex flex-wrap items-center gap-3">
									<div class="admissions-photo-frame h-14 w-14">
										<img
											v-if="guardian.guardian_image"
											:src="guardian.guardian_image"
											:alt="__('Guardian photo')"
											class="h-full w-full object-cover"
										/>
										<div
											v-else
											class="flex h-full w-full items-center justify-center type-caption text-ink/55"
										>
											{{ __('No photo') }}
										</div>
									</div>
									<a
										v-if="guardian.guardian_image_open_url"
										:href="guardian.guardian_image_open_url"
										target="_blank"
										rel="noopener noreferrer"
										class="type-caption text-jacaranda underline"
									>
										{{ __('Open photo') }}
									</a>
								</div>
							</div>

							<label class="flex items-center gap-2">
								<input
									v-model="guardian.is_primary"
									type="checkbox"
									class="admissions-checkbox"
									:disabled="isReadOnly || saving"
								/>
								<span class="type-caption text-ink/70">{{
									__('Primary relationship contact')
								}}</span>
							</label>

							<label class="flex items-center gap-2">
								<input
									v-model="guardian.can_consent"
									type="checkbox"
									class="admissions-checkbox"
									:disabled="isReadOnly || saving"
								/>
								<span class="type-caption text-ink/70">{{
									__('Authorized signer for school documents and consents')
								}}</span>
							</label>

							<label class="flex items-center gap-2">
								<input
									v-model="guardian.is_primary_guardian"
									type="checkbox"
									class="admissions-checkbox"
									:disabled="isReadOnly || saving"
								/>
								<span class="type-caption text-ink/70">{{ __('Is primary guardian') }}</span>
							</label>

							<label class="flex items-center gap-2">
								<input
									v-model="guardian.is_financial_guardian"
									type="checkbox"
									class="admissions-checkbox"
									:disabled="isReadOnly || saving"
								/>
								<span class="type-caption text-ink/70">{{ __('Is financial guardian') }}</span>
							</label>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, computed } from 'vue';
import { Spinner } from 'frappe-ui';

import InlineUploadStatus from '@/components/feedback/InlineUploadStatus.vue';
import { createAdmissionsService } from '@/lib/services/admissions/admissionsService';
import { useAdmissionsSession } from '@/composables/useAdmissionsSession';
import { __ } from '@/lib/i18n';
import { readFileAsBase64, type UploadProgressState } from '@/lib/uploadProgress';
import {
	createEmptyGuardian,
	guardianRowsForSubmit,
	haveGuardianRowsChanged,
	normalizeGuardianRow,
} from '@/pages/admissions/applicantProfileGuardians';
import { uiSignals, SIGNAL_ADMISSIONS_PORTAL_INVALIDATE } from '@/lib/uiSignals';
import type { Response as ApplicantProfileResponse } from '@/types/contracts/admissions/get_applicant_profile';
import type { Request as UpdateApplicantProfileRequest } from '@/types/contracts/admissions/update_applicant_profile';
import type {
	ApplicantContactPrefill,
	ApplicantGuardianProfile,
	ApplicantProfile,
} from '@/types/contracts/admissions/types';

const service = createAdmissionsService();
const { session, currentApplicantName } = useAdmissionsSession();
const acceptedImageInput = '.jpg,.jpeg,.png,image/jpeg,image/png';
const acceptedImageHelpText = __(
	'Accepted formats: JPG or PNG, up to 10 MB. Convert iPhone HEIC or HEIF photos to JPG before uploading.'
);
const acceptedImageExtensions = new Set(['jpg', 'jpeg', 'png']);
const acceptedImageMimeTypes = new Set(['image/jpeg', 'image/png']);
const maxAcceptedImageBytes = 10 * 1024 * 1024;
const invalidImageFormatMessage = __(
	'Please choose a JPG or PNG image. Convert HEIC or HEIF photos to JPG before uploading.'
);
const imageTooLargeMessage = __('Image is too large. Max file size is 10 MB.');

const loading = ref(false);
const saving = ref(false);
const uploadingImage = ref(false);
const imageUploadProgress = ref<UploadProgressState | null>(null);
const error = ref<string | null>(null);
const actionError = ref('');
const applicantImage = ref('');
const applicantImageOpenUrl = ref('');
const recordModified = ref('');
const selectedImageFile = ref<File | null>(null);
const imageInput = ref<HTMLInputElement | null>(null);
const selectedGuardianImageFiles = ref<Record<number, File | null>>({});
const guardianImageInputs = ref<Record<number, HTMLInputElement | null>>({});
const uploadingGuardianImageIndex = ref<number | null>(null);
const guardianImageUploadProgress = ref<Record<number, UploadProgressState>>({});
const savedGuardians = ref<ApplicantGuardianProfile[]>([]);

const profile = ref<ApplicantProfile>(createEmptyProfile());
const guardians = ref<ApplicantGuardianProfile[]>([]);
const guardiansEnabled = ref(false);
const applicantContactPrefill = ref<ApplicantContactPrefill>(createEmptyApplicantContactPrefill());
const options = ref<ApplicantProfileResponse['options']>(createEmptyOptions());
const completeness = ref<ApplicantProfileResponse['completeness']>(createEmptyCompleteness());
const applicationContext = ref<ApplicantProfileResponse['application_context']>(
	createEmptyApplicationContext()
);

const isReadOnly = computed(() => Boolean(session.value?.applicant?.is_read_only));
const hasApplicantImage = computed(() =>
	Boolean((applicantImage.value || '').trim() || (applicantImageOpenUrl.value || '').trim())
);
const imageUploadProgressLabel = computed(() =>
	selectedImageFile.value?.name
		? __('Uploading {0}', [selectedImageFile.value.name])
		: __('Uploading image')
);
const canUseApplicantContact = computed(() => Boolean(applicantContactPrefill.value.available));

function createEmptyProfile(): ApplicantProfile {
	return {
		student_preferred_name: '',
		student_date_of_birth: '',
		student_gender: '',
		student_mobile_number: '',
		student_joining_date: '',
		student_first_language: '',
		student_second_language: '',
		student_nationality: '',
		student_second_nationality: '',
		residency_status: '',
	};
}

function createEmptyOptions(): ApplicantProfileResponse['options'] {
	return {
		genders: [],
		residency_statuses: [],
		languages: [],
		countries: [],
		guardian_relationships: [],
		guardian_genders: [],
		guardian_employment_sectors: [],
		salutations: [],
	};
}

function createEmptyCompleteness(): ApplicantProfileResponse['completeness'] {
	return {
		ok: false,
		missing: [],
		required: [],
	};
}

function createEmptyApplicationContext(): ApplicantProfileResponse['application_context'] {
	return {
		organization: '',
		school: '',
		academic_year: '',
		term: '',
		program: '',
		program_offering: '',
	};
}

function createEmptyApplicantContactPrefill(): ApplicantContactPrefill {
	return {
		available: false,
		contact: '',
		first_name: '',
		last_name: '',
		email: '',
		mobile_phone: '',
	};
}

function displayText(value: unknown): string {
	const text = typeof value === 'string' ? value.trim() : String(value || '').trim();
	return text || __('Not provided');
}

function clearGuardianImageUploadState() {
	selectedGuardianImageFiles.value = {};
	guardianImageInputs.value = {};
	uploadingGuardianImageIndex.value = null;
	guardianImageUploadProgress.value = {};
}

function addGuardianRow() {
	if (isReadOnly.value) {
		actionError.value = __('This application is read-only.');
		return;
	}
	guardians.value = [...guardians.value, createEmptyGuardian()];
}

function removeGuardianRow(index: number) {
	if (isReadOnly.value) {
		actionError.value = __('This application is read-only.');
		return;
	}
	guardians.value = guardians.value.filter((_item, idx) => idx !== index);
	clearGuardianImageUploadState();
}

function onUseApplicantContactChanged(index: number) {
	const row = guardians.value[index];
	if (!row?.use_applicant_contact) return;
	const prefill = applicantContactPrefill.value;
	if (!prefill.available) {
		actionError.value = __('Applicant contact information is unavailable.');
		guardians.value[index] = normalizeGuardianRow({
			...row,
			use_applicant_contact: false,
		});
		return;
	}
	actionError.value = '';
	guardians.value[index] = normalizeGuardianRow({
		...row,
		contact: row.contact || prefill.contact || '',
		guardian_first_name: row.guardian_first_name || prefill.first_name || '',
		guardian_last_name: row.guardian_last_name || prefill.last_name || '',
		guardian_email: row.guardian_email || prefill.email || '',
		guardian_mobile_phone: row.guardian_mobile_phone || prefill.mobile_phone || '',
	});
}

function setGuardianImageInputRef(index: number, element: unknown) {
	if (element instanceof HTMLInputElement) {
		guardianImageInputs.value[index] = element;
		return;
	}
	delete guardianImageInputs.value[index];
}

function selectedGuardianImageFileName(index: number): string {
	return selectedGuardianImageFiles.value[index]?.name || '';
}

function imageExtension(fileName: string): string {
	const normalizedName = String(fileName || '')
		.trim()
		.toLowerCase();
	const dotIndex = normalizedName.lastIndexOf('.');
	return dotIndex >= 0 ? normalizedName.slice(dotIndex + 1) : '';
}

function validateSelectedImageFile(file: File): string | null {
	if (!acceptedImageExtensions.has(imageExtension(file.name))) {
		return invalidImageFormatMessage;
	}

	const mimeType = String(file.type || '')
		.trim()
		.toLowerCase();
	if (mimeType && !acceptedImageMimeTypes.has(mimeType)) {
		return invalidImageFormatMessage;
	}

	if (file.size > maxAcceptedImageBytes) {
		return imageTooLargeMessage;
	}

	return null;
}

function openGuardianImagePicker(index: number) {
	if (isReadOnly.value) {
		actionError.value = __('This application is read-only.');
		return;
	}
	guardianImageInputs.value[index]?.click();
}

function onGuardianImageSelected(index: number, event: Event) {
	const target = event.target as HTMLInputElement | null;
	const file = target?.files?.[0] || null;
	if (!file) {
		delete selectedGuardianImageFiles.value[index];
		return;
	}
	const validationError = validateSelectedImageFile(file);
	if (validationError) {
		actionError.value = validationError;
		delete selectedGuardianImageFiles.value[index];
		if (target) target.value = '';
		return;
	}
	actionError.value = '';
	selectedGuardianImageFiles.value[index] = file;
}

async function uploadGuardianImage(index: number) {
	if (isReadOnly.value) {
		actionError.value = __('This application is read-only.');
		return;
	}
	if (!currentApplicantName.value) {
		actionError.value = __('Applicant context is unavailable.');
		return;
	}
	if (error.value) {
		actionError.value = __('Please reload profile information before uploading.');
		return;
	}
	const file = selectedGuardianImageFiles.value[index] || null;
	if (!file) {
		actionError.value = __('Please choose an image to upload.');
		return;
	}
	if (!guardians.value[index]) {
		actionError.value = __('Guardian row is no longer available. Please retry.');
		return;
	}
	const guardianRowName = String(guardians.value[index]?.name || '').trim();
	if (!guardianRowName) {
		actionError.value = __('Save this guardian row before uploading an image.');
		return;
	}

	uploadingGuardianImageIndex.value = index;
	actionError.value = '';
	try {
		const content = await readFileAsBase64(file, progress => {
			guardianImageUploadProgress.value[index] = progress;
		});
		const payload = await service.uploadApplicantGuardianImage(
			{
				student_applicant: currentApplicantName.value,
				guardian_row_name: guardianRowName,
				file_name: file.name,
				content,
			},
			{
				onProgress: progress => {
					guardianImageUploadProgress.value[index] = progress;
				},
			}
		);
		const fileUrl = String(payload.image_url || '').trim();
		const openUrl = String(payload.open_url || '').trim();
		if (!fileUrl && !openUrl) {
			throw new Error(__('Unable to resolve guardian image.'));
		}
		guardians.value[index] = normalizeGuardianRow({
			...guardians.value[index],
			guardian_image: fileUrl,
			guardian_image_open_url: openUrl,
		});
		delete selectedGuardianImageFiles.value[index];
		const input = guardianImageInputs.value[index];
		if (input) input.value = '';
	} catch (err) {
		const message = err instanceof Error ? err.message : __('Unable to upload guardian image.');
		actionError.value = message;
	} finally {
		delete guardianImageUploadProgress.value[index];
		uploadingGuardianImageIndex.value = null;
	}
}

function applyPayload(payload: ApplicantProfileResponse) {
	profile.value = {
		...createEmptyProfile(),
		...(payload.profile || {}),
	};
	options.value = payload.options || createEmptyOptions();
	completeness.value = payload.completeness || createEmptyCompleteness();
	applicationContext.value = payload.application_context || createEmptyApplicationContext();
	guardiansEnabled.value = Boolean(payload.guardian_section_enabled);
	applicantContactPrefill.value =
		payload.applicant_contact_prefill || createEmptyApplicantContactPrefill();
	guardians.value = ((payload.guardians || []) as ApplicantGuardianProfile[]).map(row =>
		normalizeGuardianRow(row)
	);
	recordModified.value = String(payload.record_modified || '').trim();
	savedGuardians.value = guardianRowsForSubmit(guardians.value);
	clearGuardianImageUploadState();
	applicantImage.value = (payload.applicant_image || '').trim();
	applicantImageOpenUrl.value = (payload.applicant_image_open_url || '').trim();
	selectedImageFile.value = null;
	if (imageInput.value) imageInput.value.value = '';
}

async function loadProfile() {
	if (!currentApplicantName.value) {
		profile.value = createEmptyProfile();
		guardians.value = [];
		savedGuardians.value = [];
		options.value = createEmptyOptions();
		completeness.value = createEmptyCompleteness();
		applicationContext.value = createEmptyApplicationContext();
		applicantContactPrefill.value = createEmptyApplicantContactPrefill();
		applicantImage.value = '';
		applicantImageOpenUrl.value = '';
		recordModified.value = '';
		error.value = null;
		return;
	}
	loading.value = true;
	error.value = null;
	actionError.value = '';
	try {
		const payload = await service.getProfile({ student_applicant: currentApplicantName.value });
		applyPayload(payload);
	} catch (err) {
		const message = err instanceof Error ? err.message : __('Unable to load profile information.');
		error.value = message;
	} finally {
		loading.value = false;
	}
}

async function saveProfile() {
	if (isReadOnly.value) {
		actionError.value = __('This application is read-only.');
		return;
	}
	if (!currentApplicantName.value) {
		actionError.value = __('Applicant context is unavailable.');
		return;
	}
	if (error.value) {
		actionError.value = __('Please reload profile information before saving.');
		return;
	}

	saving.value = true;
	actionError.value = '';
	try {
		const updatePayload: UpdateApplicantProfileRequest = {
			student_applicant: currentApplicantName.value,
			expected_modified: recordModified.value,
			student_preferred_name: profile.value.student_preferred_name || '',
			student_date_of_birth: profile.value.student_date_of_birth || '',
			student_gender: profile.value.student_gender || '',
			student_mobile_number: profile.value.student_mobile_number || '',
			student_first_language: profile.value.student_first_language || '',
			student_second_language: profile.value.student_second_language || '',
			student_nationality: profile.value.student_nationality || '',
			student_second_nationality: profile.value.student_second_nationality || '',
			residency_status: profile.value.residency_status || '',
		};
		const currentGuardians = guardianRowsForSubmit(guardians.value);
		if (
			guardiansEnabled.value &&
			haveGuardianRowsChanged(currentGuardians, savedGuardians.value)
		) {
			updatePayload.guardians = currentGuardians;
		}
		const payload = await service.updateProfile(updatePayload);
		applyPayload(payload);
	} catch (err) {
		const message = err instanceof Error ? err.message : __('Unable to save profile information.');
		actionError.value = message;
	} finally {
		saving.value = false;
	}
}

function openImagePicker() {
	if (isReadOnly.value) {
		actionError.value = __('This application is read-only.');
		return;
	}
	imageInput.value?.click();
}

function onImageSelected(event: Event) {
	const target = event.target as HTMLInputElement | null;
	const file = target?.files?.[0] || null;
	if (!file) {
		selectedImageFile.value = null;
		return;
	}
	const validationError = validateSelectedImageFile(file);
	if (validationError) {
		actionError.value = validationError;
		selectedImageFile.value = null;
		if (target) target.value = '';
		return;
	}
	actionError.value = '';
	selectedImageFile.value = file;
}

async function uploadSelectedImage() {
	if (isReadOnly.value) {
		actionError.value = __('This application is read-only.');
		return;
	}
	if (!currentApplicantName.value) {
		actionError.value = __('Applicant context is unavailable.');
		return;
	}
	if (error.value) {
		actionError.value = __('Please reload profile information before uploading.');
		return;
	}
	if (!selectedImageFile.value) {
		actionError.value = __('Please choose an image to upload.');
		return;
	}

	uploadingImage.value = true;
	actionError.value = '';
	try {
		const content = await readFileAsBase64(selectedImageFile.value, progress => {
			imageUploadProgress.value = progress;
		});
		const payload = await service.uploadApplicantProfileImage(
			{
				student_applicant: currentApplicantName.value,
				file_name: selectedImageFile.value.name,
				content,
			},
			{
				onProgress: progress => {
					imageUploadProgress.value = progress;
				},
			}
		);
		applicantImage.value = (payload.image_url || '').trim();
		applicantImageOpenUrl.value = (payload.open_url || '').trim();
		selectedImageFile.value = null;
		if (imageInput.value) imageInput.value.value = '';
		await loadProfile();
	} catch (err) {
		const message = err instanceof Error ? err.message : __('Unable to upload image.');
		actionError.value = message;
	} finally {
		imageUploadProgress.value = null;
		uploadingImage.value = false;
	}
}

function guardianUploadProgress(index: number): UploadProgressState | null {
	return guardianImageUploadProgress.value[index] || null;
}

function guardianUploadProgressLabel(index: number): string {
	const fileName = selectedGuardianImageFiles.value[index]?.name || '';
	return fileName ? __('Uploading {0}', [fileName]) : __('Uploading image');
}

let unsubscribe: (() => void) | null = null;

onMounted(async () => {
	await loadProfile();
	unsubscribe = uiSignals.subscribe(SIGNAL_ADMISSIONS_PORTAL_INVALIDATE, () => {
		loadProfile();
	});
});

onBeforeUnmount(() => {
	if (unsubscribe) unsubscribe();
});
</script>
