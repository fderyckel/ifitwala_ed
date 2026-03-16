<!-- ifitwala_ed/ui-spa/src/pages/admissions/ApplicantProfile.vue -->

<template>
	<div class="space-y-6">
		<div class="flex flex-wrap items-start justify-between gap-4">
			<div>
				<p class="type-h2 text-ink">{{ __('Profile information') }}</p>
				<p class="mt-1 type-caption text-ink/60">
					{{ __('Provide core student profile details used at promotion time.') }}
				</p>
			</div>
			<button
				type="button"
				class="rounded-full bg-ink px-4 py-2 type-caption text-white shadow-soft disabled:opacity-50"
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

		<div v-if="loading" class="rounded-2xl border border-border/70 bg-surface px-4 py-4">
			<div class="flex items-center gap-3">
				<Spinner class="h-4 w-4" />
				<p class="type-body-strong text-ink">{{ __('Loading profile…') }}</p>
			</div>
		</div>

		<div v-else-if="error" class="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3">
			<p class="type-body-strong text-rose-900">{{ __('Unable to load profile information') }}</p>
			<p class="mt-1 type-caption text-rose-900/80 whitespace-pre-wrap">{{ error }}</p>
			<button
				type="button"
				class="mt-3 rounded-full border border-rose-200 bg-surface px-4 py-2 type-caption text-rose-900"
				@click="loadProfile"
			>
				{{ __('Try again') }}
			</button>
		</div>

		<div v-else class="space-y-4">
			<div v-if="actionError" class="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3">
				<p class="type-body-strong text-amber-900">{{ __('Notice') }}</p>
				<p class="mt-1 type-caption text-amber-900/80">{{ actionError }}</p>
			</div>
			<div
				v-if="!options.languages.length || !options.countries.length"
				class="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3"
			>
				<p class="type-body-strong text-amber-900">{{ __('Setup required') }}</p>
				<p class="mt-1 type-caption text-amber-900/80">
					{{
						__(
							'Some profile option lists are not configured yet. Please contact the admissions office.'
						)
					}}
				</p>
			</div>

			<div class="rounded-2xl border border-border/70 bg-surface px-4 py-4 shadow-soft">
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
							class="rounded-full border border-border/70 bg-surface px-4 py-2 type-caption text-ink/70 disabled:opacity-50"
							:disabled="isReadOnly || uploadingImage"
							@click="openImagePicker"
						>
							{{ __('Choose image') }}
						</button>
						<button
							type="button"
							class="rounded-full bg-ink px-4 py-2 type-caption text-white shadow-soft disabled:opacity-50"
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

				<div class="mt-4 flex flex-wrap items-center gap-4">
					<div class="h-24 w-24 overflow-hidden rounded-2xl border border-border/70 bg-surface">
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
								applicantImage
									? __('Current image is saved.')
									: __('No student image uploaded yet.')
							}}
						</p>
						<a
							v-if="applicantImage"
							:href="applicantImage"
							target="_blank"
							rel="noopener noreferrer"
							class="type-caption text-ink/70 underline"
						>
							{{ __('Open image in new tab') }}
						</a>
					</div>
				</div>
			</div>

			<div
				class="rounded-2xl px-4 py-4 shadow-soft"
				:class="
					completeness.ok
						? 'border border-leaf/40 bg-leaf/10'
						: 'border border-amber-200 bg-amber-50'
				"
			>
				<p
					class="type-body-strong"
					:class="completeness.ok ? 'text-emerald-900' : 'text-amber-900'"
				>
					{{
						completeness.ok
							? __('Profile information complete')
							: __('Profile information still required')
					}}
				</p>
				<p v-if="!completeness.ok" class="mt-1 type-caption text-amber-900/80">
					{{ __('Missing: {0}').replace('{0}', completeness.missing.join(', ')) }}
				</p>
			</div>

			<div class="rounded-2xl border border-border/70 bg-surface px-4 py-4 shadow-soft">
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

			<div class="rounded-2xl border border-border/70 bg-surface px-4 py-4 shadow-soft">
				<p class="type-body-strong text-ink">{{ __('Student profile') }}</p>
				<div class="mt-4 grid gap-4 md:grid-cols-2">
					<label class="block">
						<span class="type-caption text-ink/60">{{ __('Preferred name') }}</span>
						<input
							v-model="profile.student_preferred_name"
							type="text"
							class="mt-1 w-full rounded-xl border border-border/70 bg-surface px-3 py-2 type-body text-ink focus:outline-none focus:ring-2 focus:ring-ink/20"
							:disabled="isReadOnly || saving"
						/>
					</label>

					<label class="block">
						<span class="type-caption text-ink/60">{{ __('Date of birth') }}</span>
						<input
							v-model="profile.student_date_of_birth"
							type="date"
							class="mt-1 w-full rounded-xl border border-border/70 bg-surface px-3 py-2 type-body text-ink focus:outline-none focus:ring-2 focus:ring-ink/20"
							:disabled="isReadOnly || saving"
						/>
					</label>

					<label class="block">
						<span class="type-caption text-ink/60">{{ __('Gender') }}</span>
						<select
							v-model="profile.student_gender"
							class="mt-1 w-full rounded-xl border border-border/70 bg-surface px-3 py-2 type-body text-ink focus:outline-none focus:ring-2 focus:ring-ink/20"
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
							class="mt-1 w-full rounded-xl border border-border/70 bg-surface px-3 py-2 type-body text-ink focus:outline-none focus:ring-2 focus:ring-ink/20"
							:disabled="isReadOnly || saving"
						/>
					</label>

					<label class="block">
						<span class="type-caption text-ink/60">{{ __('Admission date') }}</span>
						<input
							v-model="profile.student_joining_date"
							type="date"
							class="mt-1 w-full rounded-xl border border-border/70 bg-surface px-3 py-2 type-body text-ink focus:outline-none focus:ring-2 focus:ring-ink/20"
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
							class="mt-1 w-full rounded-xl border border-border/70 bg-surface px-3 py-2 type-body text-ink focus:outline-none focus:ring-2 focus:ring-ink/20"
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
							class="mt-1 w-full rounded-xl border border-border/70 bg-surface px-3 py-2 type-body text-ink focus:outline-none focus:ring-2 focus:ring-ink/20"
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
							class="mt-1 w-full rounded-xl border border-border/70 bg-surface px-3 py-2 type-body text-ink focus:outline-none focus:ring-2 focus:ring-ink/20"
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
							class="mt-1 w-full rounded-xl border border-border/70 bg-surface px-3 py-2 type-body text-ink focus:outline-none focus:ring-2 focus:ring-ink/20"
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
							class="mt-1 w-full rounded-xl border border-border/70 bg-surface px-3 py-2 type-body text-ink focus:outline-none focus:ring-2 focus:ring-ink/20"
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

			<div
				v-if="guardiansEnabled"
				class="rounded-2xl border border-border/70 bg-surface px-4 py-4 shadow-soft"
			>
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
						class="rounded-full border border-border/70 bg-surface px-4 py-2 type-caption text-ink/70 disabled:opacity-50"
						:disabled="isReadOnly || saving"
						@click="addGuardianRow"
					>
						{{ __('Add guardian') }}
					</button>
				</div>

				<div v-if="!guardians.length" class="mt-4 rounded-xl border border-border/60 px-3 py-3">
					<p class="type-body text-ink/70">{{ __('No guardians added yet.') }}</p>
				</div>

				<div v-else class="mt-4 space-y-4">
					<div
						v-for="(guardian, idx) in guardians"
						:key="guardian.name || `guardian-${idx}`"
						class="rounded-xl border border-border/60 bg-surface/40 px-3 py-3"
					>
						<div class="flex flex-wrap items-center justify-between gap-3">
							<p class="type-body-strong text-ink">
								{{ __('Guardian #{0}').replace('{0}', String(idx + 1)) }}
							</p>
							<button
								type="button"
								class="rounded-full border border-rose-200 bg-surface px-3 py-1 type-caption text-rose-700 disabled:opacity-50"
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
									class="mt-1 w-full rounded-xl border border-border/70 bg-surface px-3 py-2 type-body text-ink focus:outline-none focus:ring-2 focus:ring-ink/20"
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

							<label class="flex items-center gap-2 md:col-span-2">
								<input
									v-model="guardian.use_applicant_contact"
									type="checkbox"
									class="h-4 w-4 rounded border-border/70"
									:disabled="isReadOnly || saving"
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
									class="mt-1 w-full rounded-xl border border-border/70 bg-surface px-3 py-2 type-body text-ink focus:outline-none focus:ring-2 focus:ring-ink/20"
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
									class="mt-1 w-full rounded-xl border border-border/70 bg-surface px-3 py-2 type-body text-ink focus:outline-none focus:ring-2 focus:ring-ink/20"
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
									class="mt-1 w-full rounded-xl border border-border/70 bg-surface px-3 py-2 type-body text-ink focus:outline-none focus:ring-2 focus:ring-ink/20"
									:disabled="isReadOnly || saving"
								/>
							</label>

							<label class="block">
								<span class="type-caption text-ink/60">{{ __('Last name *') }}</span>
								<input
									v-model="guardian.guardian_last_name"
									type="text"
									required
									class="mt-1 w-full rounded-xl border border-border/70 bg-surface px-3 py-2 type-body text-ink focus:outline-none focus:ring-2 focus:ring-ink/20"
									:disabled="isReadOnly || saving"
								/>
							</label>

							<label class="block">
								<span class="type-caption text-ink/60">{{ __('Personal email *') }}</span>
								<input
									v-model="guardian.guardian_email"
									type="email"
									required
									class="mt-1 w-full rounded-xl border border-border/70 bg-surface px-3 py-2 type-body text-ink focus:outline-none focus:ring-2 focus:ring-ink/20"
									:disabled="isReadOnly || saving"
								/>
							</label>

							<label class="block">
								<span class="type-caption text-ink/60">{{ __('Mobile phone *') }}</span>
								<input
									v-model="guardian.guardian_mobile_phone"
									type="text"
									required
									class="mt-1 w-full rounded-xl border border-border/70 bg-surface px-3 py-2 type-body text-ink focus:outline-none focus:ring-2 focus:ring-ink/20"
									:disabled="isReadOnly || saving"
								/>
							</label>

							<label class="block">
								<span class="type-caption text-ink/60">{{ __('Employment sector') }}</span>
								<select
									v-model="guardian.employment_sector"
									class="mt-1 w-full rounded-xl border border-border/70 bg-surface px-3 py-2 type-body text-ink focus:outline-none focus:ring-2 focus:ring-ink/20"
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
									class="mt-1 w-full rounded-xl border border-border/70 bg-surface px-3 py-2 type-body text-ink focus:outline-none focus:ring-2 focus:ring-ink/20"
									:disabled="isReadOnly || saving"
								/>
							</label>

							<label class="block">
								<span class="type-caption text-ink/60">{{ __('Designation at work') }}</span>
								<input
									v-model="guardian.guardian_designation"
									type="text"
									class="mt-1 w-full rounded-xl border border-border/70 bg-surface px-3 py-2 type-body text-ink focus:outline-none focus:ring-2 focus:ring-ink/20"
									:disabled="isReadOnly || saving"
								/>
							</label>

							<label class="block">
								<span class="type-caption text-ink/60">{{ __('Work email') }}</span>
								<input
									v-model="guardian.guardian_work_email"
									type="email"
									class="mt-1 w-full rounded-xl border border-border/70 bg-surface px-3 py-2 type-body text-ink focus:outline-none focus:ring-2 focus:ring-ink/20"
									:disabled="isReadOnly || saving"
								/>
							</label>

							<label class="block">
								<span class="type-caption text-ink/60">{{ __('Work phone') }}</span>
								<input
									v-model="guardian.guardian_work_phone"
									type="text"
									class="mt-1 w-full rounded-xl border border-border/70 bg-surface px-3 py-2 type-body text-ink focus:outline-none focus:ring-2 focus:ring-ink/20"
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
										class="rounded-full border border-border/70 bg-surface px-3 py-2 type-caption text-ink/70 disabled:opacity-50"
										:disabled="isReadOnly || saving || uploadingGuardianImageIndex === idx"
										@click="openGuardianImagePicker(idx)"
									>
										{{ __('Choose photo') }}
									</button>
									<button
										type="button"
										class="rounded-full bg-ink px-3 py-2 type-caption text-white shadow-soft disabled:opacity-50"
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
								<div class="mt-3 flex flex-wrap items-center gap-3">
									<div
										class="h-14 w-14 overflow-hidden rounded-xl border border-border/70 bg-surface"
									>
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
										v-if="guardian.guardian_image"
										:href="guardian.guardian_image"
										target="_blank"
										rel="noopener noreferrer"
										class="type-caption text-ink/70 underline"
									>
										{{ __('Open photo') }}
									</a>
								</div>
							</div>

							<label class="flex items-center gap-2">
								<input
									v-model="guardian.is_primary"
									type="checkbox"
									class="h-4 w-4 rounded border-border/70"
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
									class="h-4 w-4 rounded border-border/70"
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
									class="h-4 w-4 rounded border-border/70"
									:disabled="isReadOnly || saving"
								/>
								<span class="type-caption text-ink/70">{{ __('Is primary guardian') }}</span>
							</label>

							<label class="flex items-center gap-2">
								<input
									v-model="guardian.is_financial_guardian"
									type="checkbox"
									class="h-4 w-4 rounded border-border/70"
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

import { createAdmissionsService } from '@/lib/services/admissions/admissionsService';
import { useAdmissionsSession } from '@/composables/useAdmissionsSession';
import { __ } from '@/lib/i18n';
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
const error = ref<string | null>(null);
const actionError = ref('');
const applicantImage = ref('');
const recordModified = ref('');
const selectedImageFile = ref<File | null>(null);
const imageInput = ref<HTMLInputElement | null>(null);
const selectedGuardianImageFiles = ref<Record<number, File | null>>({});
const guardianImageInputs = ref<Record<number, HTMLInputElement | null>>({});
const uploadingGuardianImageIndex = ref<number | null>(null);
const savedGuardians = ref<ApplicantGuardianProfile[]>([]);

const profile = ref<ApplicantProfile>(createEmptyProfile());
const guardians = ref<ApplicantGuardianProfile[]>([]);
const guardiansEnabled = ref(false);
const options = ref<ApplicantProfileResponse['options']>(createEmptyOptions());
const completeness = ref<ApplicantProfileResponse['completeness']>(createEmptyCompleteness());
const applicationContext = ref<ApplicantProfileResponse['application_context']>(
	createEmptyApplicationContext()
);

const isReadOnly = computed(() => Boolean(session.value?.applicant?.is_read_only));

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

function displayText(value: unknown): string {
	const text = typeof value === 'string' ? value.trim() : String(value || '').trim();
	return text || __('Not provided');
}

function clearGuardianImageUploadState() {
	selectedGuardianImageFiles.value = {};
	guardianImageInputs.value = {};
	uploadingGuardianImageIndex.value = null;
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

	uploadingGuardianImageIndex.value = index;
	actionError.value = '';
	try {
		const content = await readAsBase64(file);
		const payload = await service.uploadApplicantGuardianImage({
			student_applicant: currentApplicantName.value,
			file_name: file.name,
			content,
		});
		const fileUrl = String(payload.file_url || '').trim();
		if (!fileUrl) {
			throw new Error(__('Unable to upload guardian image.'));
		}
		guardians.value[index] = normalizeGuardianRow({
			...guardians.value[index],
			guardian_image: fileUrl,
		});
		delete selectedGuardianImageFiles.value[index];
		const input = guardianImageInputs.value[index];
		if (input) input.value = '';
	} catch (err) {
		const message = err instanceof Error ? err.message : __('Unable to upload guardian image.');
		actionError.value = message;
	} finally {
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
	guardians.value = ((payload.guardians || []) as ApplicantGuardianProfile[]).map(row =>
		normalizeGuardianRow(row)
	);
	recordModified.value = String(payload.record_modified || '').trim();
	savedGuardians.value = guardianRowsForSubmit(guardians.value);
	clearGuardianImageUploadState();
	applicantImage.value = (payload.applicant_image || '').trim();
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
		applicantImage.value = '';
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
		const content = await readAsBase64(selectedImageFile.value);
		const payload = await service.uploadApplicantProfileImage({
			student_applicant: currentApplicantName.value,
			file_name: selectedImageFile.value.name,
			content,
		});
		applicantImage.value = (payload.file_url || '').trim();
		selectedImageFile.value = null;
		if (imageInput.value) imageInput.value.value = '';
		await loadProfile();
	} catch (err) {
		const message = err instanceof Error ? err.message : __('Unable to upload image.');
		actionError.value = message;
	} finally {
		uploadingImage.value = false;
	}
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
