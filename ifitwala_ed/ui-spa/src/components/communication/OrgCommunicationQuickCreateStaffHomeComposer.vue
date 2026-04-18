<template>
	<div class="grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1.5fr)_minmax(22rem,0.9fr)]">
		<div class="space-y-5">
			<section class="rounded-[28px] border border-border/70 bg-white p-5 shadow-soft">
				<div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
					<div class="space-y-1">
						<p class="type-overline text-ink/55">Message</p>
						<h3 class="type-h3 text-ink">Core details</h3>
						<p class="type-caption text-ink/65">
							Use the same organization, school, delivery, and audience rules as Desk, without
							leaving the staff shell.
						</p>
					</div>
				</div>

				<div class="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
					<div class="space-y-1">
						<label class="type-label">Title</label>
						<FormControl
							v-model="form.title"
							type="text"
							placeholder="Weekly staff update"
							:disabled="submitting"
						/>
					</div>

					<div class="space-y-1">
						<label class="type-label">Communication type</label>
						<select
							v-model="form.communication_type"
							class="if-org-communication-native-select"
							:disabled="submitting"
						>
							<option
								v-for="option in communicationTypeOptions"
								:key="getSelectOptionValue(option)"
								:value="getSelectOptionValue(option)"
							>
								{{ getSelectOptionLabel(option) }}
							</option>
						</select>
					</div>
				</div>

				<div class="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
					<div class="space-y-1">
						<label class="type-label">Organization</label>
						<select
							v-model="form.organization"
							class="if-org-communication-native-select"
							:disabled="submitting || attachmentContextLocked"
						>
							<option
								v-for="option in organizationSelectOptions"
								:key="getSelectOptionValue(option)"
								:value="getSelectOptionValue(option)"
							>
								{{ getSelectOptionLabel(option) }}
							</option>
						</select>
						<p class="type-caption text-ink/55">
							{{ organizationHelpText }}
						</p>
					</div>

					<div class="space-y-1">
						<label class="type-label">Issuing school</label>
						<select
							v-model="form.school"
							class="if-org-communication-native-select"
							:disabled="submitting || issuingSchoolSelectionLocked || attachmentContextLocked"
						>
							<option value="">No issuing school</option>
							<option
								v-for="option in schoolSelectOptions"
								:key="getSelectOptionValue(option)"
								:value="getSelectOptionValue(option)"
							>
								{{ getSelectOptionLabel(option) }}
							</option>
						</select>
						<p class="type-caption text-ink/55">
							{{ schoolHelpText }}
						</p>
					</div>
				</div>

				<div
					v-if="attachmentContextLocked"
					class="mt-4 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3"
				>
					<p class="type-caption text-amber-900">
						{{ attachmentContextLockMessage }}
					</p>
				</div>

				<div class="mt-4 space-y-1">
					<label class="type-label">Message</label>
					<div
						class="if-org-communication-message-editor overflow-hidden rounded-2xl border border-border/80 bg-white shadow-sm"
					>
						<TextEditor
							:content="form.message"
							placeholder="Share the update, call to action, or announcement."
							:editable="!submitting"
							:fixed-menu="messageEditorButtons"
							editor-class="prose prose-sm max-w-none min-h-[14rem] bg-white px-4 py-3 text-sm text-ink focus:outline-none"
							@change="updateMessage"
						/>
					</div>
				</div>

				<div class="mt-4 space-y-1">
					<label class="type-label">Internal note</label>
					<FormControl
						v-model="form.internal_note"
						type="textarea"
						:rows="3"
						placeholder="Optional staff note for managing this communication."
						:disabled="submitting"
					/>
				</div>
			</section>

			<OrgCommunicationQuickCreateAttachmentSection
				v-bind="attachmentSection"
				@trigger-file-picker="emit('trigger-file-picker')"
				@toggle-link-composer="emit('toggle-link-composer')"
				@reset-link-draft="emit('reset-link-draft')"
				@submit-link="emit('submit-link')"
				@delete-attachment="emit('delete-attachment', $event)"
			/>

			<section class="rounded-[28px] border border-border/70 bg-white p-5 shadow-soft">
				<div class="space-y-1">
					<p class="type-overline text-ink/55">Delivery</p>
					<h3 class="type-h3 text-ink">Publishing and surfaces</h3>
					<p class="type-caption text-ink/65">
						Publish will send now or schedule from Publish from. Save as draft keeps the
						communication editable.
					</p>
				</div>

				<div class="mt-4 rounded-2xl border border-sky/30 bg-sky/10 px-4 py-3">
					<p class="type-caption text-canopy">
						Publish action status:
						<span class="type-body-strong text-canopy">
							{{ publishActionStatus }}
						</span>
					</p>
				</div>

				<div
					class="if-org-communication-delivery-select-grid mt-4 grid grid-cols-1 gap-4 min-[480px]:grid-cols-2"
				>
					<div class="space-y-1">
						<label class="type-label">Priority</label>
						<select
							v-model="form.priority"
							class="if-org-communication-native-select"
							:disabled="submitting"
						>
							<option
								v-for="option in priorityOptions"
								:key="getSelectOptionValue(option)"
								:value="getSelectOptionValue(option)"
							>
								{{ getSelectOptionLabel(option) }}
							</option>
						</select>
					</div>
					<div class="space-y-1">
						<label class="type-label">Portal surface</label>
						<select
							v-model="form.portal_surface"
							class="if-org-communication-native-select"
							:disabled="submitting"
						>
							<option
								v-for="option in portalSurfaceOptions"
								:key="getSelectOptionValue(option)"
								:value="getSelectOptionValue(option)"
							>
								{{ getSelectOptionLabel(option) }}
							</option>
						</select>
					</div>
				</div>

				<div class="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
					<div class="space-y-1">
						<label class="type-label">Brief order</label>
						<FormControl
							v-model="form.brief_order"
							type="number"
							placeholder="Optional"
							:disabled="submitting"
						/>
					</div>
				</div>

				<div
					class="if-org-communication-publish-window-grid mt-4 grid grid-cols-1 gap-4 min-[480px]:grid-cols-2"
				>
					<div class="space-y-1">
						<label class="type-label">Publish from</label>
						<input
							v-model="form.publish_from"
							type="datetime-local"
							class="w-full rounded-2xl border border-border/80 bg-white px-3 py-2 text-sm text-ink shadow-sm focus:border-jacaranda/50 focus:ring-1 focus:ring-jacaranda/30"
							:disabled="submitting"
							@click="openNativeDatePicker"
							@focus="openNativeDatePicker"
						/>
					</div>
					<div class="space-y-1">
						<label class="type-label">Publish until</label>
						<input
							v-model="form.publish_to"
							type="datetime-local"
							class="w-full rounded-2xl border border-border/80 bg-white px-3 py-2 text-sm text-ink shadow-sm focus:border-jacaranda/50 focus:ring-1 focus:ring-jacaranda/30"
							:disabled="submitting"
							@click="openNativeDatePicker"
							@focus="openNativeDatePicker"
						/>
					</div>
				</div>

				<div
					class="if-org-communication-brief-window-grid mt-4 grid grid-cols-1 gap-4 min-[480px]:grid-cols-2"
				>
					<div class="space-y-1">
						<label class="type-label">
							Brief start date
							<span v-if="briefDatesRequired" class="text-rose-600">*</span>
						</label>
						<input
							v-model="form.brief_start_date"
							type="date"
							class="w-full rounded-2xl border border-border/80 bg-white px-3 py-2 text-sm text-ink shadow-sm focus:border-jacaranda/50 focus:ring-1 focus:ring-jacaranda/30"
							:disabled="submitting"
							@click="openNativeDatePicker"
							@focus="openNativeDatePicker"
						/>
					</div>
					<div class="space-y-1">
						<label class="type-label">Brief end date</label>
						<input
							v-model="form.brief_end_date"
							type="date"
							class="w-full rounded-2xl border border-border/80 bg-white px-3 py-2 text-sm text-ink shadow-sm focus:border-jacaranda/50 focus:ring-1 focus:ring-jacaranda/30"
							:disabled="submitting"
							@click="openNativeDatePicker"
							@focus="openNativeDatePicker"
						/>
					</div>
				</div>

				<div
					v-if="deliveryValidationMessage"
					class="mt-4 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3"
				>
					<p class="type-caption text-rose-900">
						{{ deliveryValidationMessage }}
					</p>
				</div>
			</section>

			<section class="rounded-[28px] border border-border/70 bg-white p-5 shadow-soft">
				<div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
					<div class="space-y-1">
						<p class="type-overline text-ink/55">Audience</p>
						<h3 class="type-h3 text-ink">Targeting</h3>
						<p class="type-caption text-ink/65">
							Start from a real communication workflow, then fine-tune recipients only when needed.
						</p>
					</div>
				</div>

				<div class="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
					<button
						v-for="preset in audiencePresets"
						:key="preset.key"
						type="button"
						class="rounded-[24px] border border-border/70 bg-surface-soft/70 px-4 py-4 text-left transition hover:-translate-y-0.5 hover:border-jacaranda/50 hover:bg-white"
						:disabled="submitting || attachmentContextLocked"
						@click="addAudiencePreset(preset.key)"
					>
						<p class="type-body-strong text-ink">{{ preset.label }}</p>
						<p class="mt-1 type-caption text-ink/65">
							{{ preset.description }}
						</p>
					</button>
				</div>

				<div
					v-if="attachmentContextLocked"
					class="mt-4 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3"
				>
					<p class="type-caption text-amber-900">
						Attachment scope is locked while governed files remain attached.
					</p>
				</div>

				<div
					v-if="audienceValidationMessage"
					class="mt-4 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3"
				>
					<p class="type-caption text-rose-900">
						{{ audienceValidationMessage }}
					</p>
				</div>

				<div class="mt-4 space-y-4">
					<p v-if="!audienceRows.length" class="type-caption text-ink/60">
						Choose an audience workflow above. You can add more than one audience when needed.
					</p>

					<div
						v-for="(row, index) in audienceRows"
						:key="row.id"
						class="rounded-[24px] border border-border/70 bg-surface-soft/70 p-4"
					>
						<div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
							<div class="space-y-1">
								<p class="type-caption text-ink/55">Audience row {{ index + 1 }}</p>
								<p class="type-body-strong text-ink">{{ getAudienceRowTitle(row) }}</p>
								<p class="type-caption text-ink/65">
									{{ getAudienceRowDescription(row) }}
								</p>
							</div>

							<button
								type="button"
								class="rounded-full border border-border/80 bg-white px-3 py-1.5 type-button-label text-slate-token transition hover:border-rose-300 hover:text-rose-700"
								:disabled="submitting || attachmentContextLocked"
								@click="removeAudienceRow(row.id)"
							>
								Remove
							</button>
						</div>

						<div
							v-if="row.target_mode === 'School Scope'"
							class="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2"
						>
							<div class="space-y-1">
								<label class="type-label">Audience school</label>
								<select
									v-model="row.school"
									class="if-org-communication-native-select"
									:disabled="
										submitting || audienceSchoolSelectionLocked || attachmentContextLocked
									"
								>
									<option value="">Select school</option>
									<option
										v-for="option in schoolSelectOptions"
										:key="getSelectOptionValue(option)"
										:value="getSelectOptionValue(option)"
									>
										{{ getSelectOptionLabel(option) }}
									</option>
								</select>
								<label
									class="mt-2 inline-flex cursor-pointer items-center gap-2 type-caption text-ink/70"
								>
									<input
										v-model="row.include_descendants"
										type="checkbox"
										class="rounded border-slate-300 text-jacaranda"
										:disabled="submitting || attachmentContextLocked"
									/>
									Include descendant schools
								</label>
							</div>

							<div class="space-y-2">
								<label class="type-label">Recipients</label>
								<div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
									<label
										v-for="recipient in recipientToggleDefinitions"
										:key="recipient.field"
										class="flex items-center gap-2 rounded-2xl border border-border/70 bg-white px-3 py-2 type-caption text-ink/75"
										:class="isRecipientDisabled(row, recipient.field) ? 'opacity-55' : ''"
									>
										<input
											:checked="Boolean(row[recipient.field])"
											type="checkbox"
											class="rounded border-slate-300 text-jacaranda"
											:disabled="submitting || isRecipientDisabled(row, recipient.field)"
											@change="toggleRecipient(row, recipient.field, $event)"
										/>
										<span>{{ recipient.label }}</span>
									</label>
								</div>
								<p
									v-if="row.target_mode === 'School Scope' && !canTargetWideSchoolScope"
									class="type-caption text-amber-700"
								>
									School-scope Staff rows require Academic Admin, Academic Assistant, HR Manager,
									Accounts Manager, Nurse, or System Manager.
								</p>
							</div>
						</div>

						<div
							v-else-if="row.target_mode === 'Team' || row.target_mode === 'Student Group'"
							class="mt-4 space-y-3"
						>
							<div class="flex flex-col gap-3 lg:flex-row lg:items-end">
								<div class="min-w-0 flex-1 space-y-1">
									<label class="type-label">
										{{
											row.target_mode === 'Team' ? 'Search team' : 'Search class or student group'
										}}
									</label>
									<input
										v-model.trim="row.search_query"
										type="text"
										class="w-full rounded-2xl border border-border/80 bg-white px-3 py-2 text-sm text-ink shadow-sm focus:border-jacaranda/50 focus:ring-1 focus:ring-jacaranda/30"
										:placeholder="
											row.target_mode === 'Team'
												? 'Type a team name or code'
												: 'Type a class, course, or student group'
										"
										:disabled="submitting || row.search_loading || attachmentContextLocked"
										@keydown.enter.prevent="searchAudienceTargets(row)"
									/>
								</div>

								<div class="flex flex-wrap gap-2">
									<button
										type="button"
										class="if-button if-button--secondary"
										:disabled="submitting || row.search_loading || attachmentContextLocked"
										@click="searchAudienceTargets(row)"
									>
										{{ row.search_loading ? 'Searching...' : 'Search' }}
									</button>
									<button
										v-if="row.team || row.student_group"
										type="button"
										class="rounded-full border border-border/80 bg-white px-3 py-1.5 type-button-label text-slate-token transition hover:border-rose-300 hover:text-rose-700"
										:disabled="submitting || attachmentContextLocked"
										@click="clearAudienceSearchSelection(row)"
									>
										Clear
									</button>
								</div>
							</div>

							<div
								v-if="row.team || row.student_group"
								class="rounded-2xl border border-border/70 bg-white px-4 py-3"
							>
								<p class="type-caption text-ink/55">Selected</p>
								<p class="mt-1 type-body-strong text-ink">
									{{ row.target_mode === 'Team' ? row.team_label : row.student_group_label }}
								</p>
							</div>

							<p v-if="row.search_message" class="type-caption text-ink/65">
								{{ row.search_message }}
							</p>

							<div
								v-if="getAudienceSearchItems(row).length"
								class="grid grid-cols-1 gap-2 md:grid-cols-2"
							>
								<button
									v-for="item in getAudienceSearchItems(row)"
									:key="item.value"
									type="button"
									class="rounded-2xl border px-4 py-3 text-left transition"
									:class="
										(row.target_mode === 'Team' ? row.team : row.student_group) === item.value
											? 'border-jacaranda bg-jacaranda/5'
											: 'border-border/70 bg-white hover:border-jacaranda/50'
									"
									:disabled="submitting || attachmentContextLocked"
									@click="selectAudienceSearchItem(row, item)"
								>
									<p class="type-body-strong text-ink">{{ item.label }}</p>
									<p class="mt-1 type-caption text-ink/60">{{ item.description }}</p>
								</button>
							</div>

							<div v-if="row.target_mode === 'Student Group'" class="space-y-2">
								<label class="type-label">Recipients</label>
								<div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
									<label
										v-for="recipient in recipientToggleDefinitions"
										:key="recipient.field"
										class="flex items-center gap-2 rounded-2xl border border-border/70 bg-white px-3 py-2 type-caption text-ink/75"
										:class="isRecipientDisabled(row, recipient.field) ? 'opacity-55' : ''"
									>
										<input
											:checked="Boolean(row[recipient.field])"
											type="checkbox"
											class="rounded border-slate-300 text-jacaranda"
											:disabled="submitting || isRecipientDisabled(row, recipient.field)"
											@change="toggleRecipient(row, recipient.field, $event)"
										/>
										<span>{{ recipient.label }}</span>
									</label>
								</div>
							</div>

							<p v-else class="type-caption text-ink/60">
								Recipients stay fixed to staff for team communications.
							</p>
						</div>

						<div v-else class="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
							<div class="space-y-1">
								<label class="type-label">Organization audience</label>
								<p
									class="rounded-2xl border border-border/70 bg-white px-3 py-3 type-caption text-ink/70"
								>
									Uses the selected organization. Staff without a School and guardians linked to
									students in that organization tree remain included.
								</p>
							</div>

							<div class="space-y-2">
								<label class="type-label">Recipients</label>
								<div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
									<label
										v-for="recipient in recipientToggleDefinitions"
										:key="recipient.field"
										class="flex items-center gap-2 rounded-2xl border border-border/70 bg-white px-3 py-2 type-caption text-ink/75"
										:class="isRecipientDisabled(row, recipient.field) ? 'opacity-55' : ''"
									>
										<input
											:checked="Boolean(row[recipient.field])"
											type="checkbox"
											class="rounded border-slate-300 text-jacaranda"
											:disabled="submitting || isRecipientDisabled(row, recipient.field)"
											@change="toggleRecipient(row, recipient.field, $event)"
										/>
										<span>{{ recipient.label }}</span>
									</label>
								</div>
								<p v-if="!canTargetWideSchoolScope" class="type-caption text-amber-700">
									Organization audience rows require Academic Admin, Academic Assistant, HR
									Manager, Accounts Manager, Nurse, or System Manager.
								</p>
							</div>
						</div>

						<details class="mt-4 rounded-2xl border border-border/70 bg-white px-4 py-3">
							<summary class="cursor-pointer list-none">
								<p class="type-caption text-ink/70">Advanced notes</p>
							</summary>

							<div class="mt-3 space-y-1">
								<label class="type-label">Row note</label>
								<FormControl
									v-model="row.note"
									type="textarea"
									:rows="2"
									placeholder="Optional note for this audience row."
									:disabled="submitting"
								/>
							</div>
						</details>
					</div>
				</div>
			</section>
		</div>

		<aside class="space-y-5">
			<section class="rounded-[28px] border border-border/70 bg-white p-5 shadow-soft">
				<p class="type-overline text-ink/55">Interaction</p>
				<h3 class="mt-1 type-h3 text-ink">Interaction settings</h3>
				<div class="mt-4 space-y-4">
					<div class="space-y-1">
						<label class="type-label">Interaction mode</label>
						<select
							v-model="form.interaction_mode"
							class="if-org-communication-native-select"
							:disabled="submitting"
						>
							<option
								v-for="option in interactionModeOptions"
								:key="getSelectOptionValue(option)"
								:value="getSelectOptionValue(option)"
							>
								{{ getSelectOptionLabel(option) }}
							</option>
						</select>
					</div>
					<label
						class="flex cursor-pointer items-start gap-3 rounded-2xl border border-border/70 bg-surface-soft px-4 py-3 type-caption text-ink/75"
					>
						<input
							v-model="form.allow_private_notes"
							type="checkbox"
							class="mt-0.5 rounded border-slate-300 text-jacaranda"
							:disabled="submitting || privateNotesDisabled"
						/>
						<span>
							<span class="block"> Let teachers and staff reply privately. </span>
							<span class="mt-1 block text-[11px] text-ink/60">
								{{ privateNotesHelpText }}
							</span>
						</span>
					</label>
					<label
						class="flex cursor-pointer items-start gap-3 rounded-2xl border border-border/70 bg-surface-soft px-4 py-3 type-caption text-ink/75"
					>
						<input
							v-model="form.allow_public_thread"
							type="checkbox"
							class="mt-0.5 rounded border-slate-300 text-jacaranda"
							:disabled="submitting || publicThreadDisabled"
						/>
						<span>
							<span class="block"> Let students or families reply in the shared thread. </span>
							<span class="mt-1 block text-[11px] text-ink/60">
								{{ publicThreadHelpText }}
							</span>
						</span>
					</label>
				</div>
			</section>

			<section class="rounded-[28px] border border-border/70 bg-white p-5 shadow-soft">
				<p class="type-overline text-ink/55">Audience summary</p>
				<div class="mt-4 space-y-3">
					<div
						v-for="item in audienceSummaryRows"
						:key="item.id"
						class="rounded-2xl border border-border/70 bg-surface-soft px-4 py-3"
					>
						<p class="type-body-strong text-ink">{{ item.scope }}</p>
						<p class="mt-1 type-caption text-ink/65">{{ item.recipients }}</p>
					</div>
					<p v-if="!audienceSummaryRows.length" class="type-caption text-ink/60">
						Add at least one audience row.
					</p>
				</div>
			</section>

			<section
				class="if-org-communication-ready-check overflow-hidden rounded-[32px] border border-canopy/10 bg-canopy bg-[linear-gradient(160deg,rgb(var(--canopy-rgb)/0.96),rgb(var(--ink-rgb)/0.92))] p-5 text-white shadow-soft"
			>
				<p class="type-overline text-white/65">Ready check</p>
				<h3 class="mt-1 type-h3 text-white">{{ summaryTitle }}</h3>
				<p class="mt-2 type-caption text-white/70">
					{{ summarySubtitle }}
				</p>

				<div class="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-1">
					<div class="rounded-2xl bg-white/10 px-4 py-3 backdrop-blur-sm">
						<p class="type-caption text-white/60">Publish action</p>
						<p class="mt-1 type-body-strong text-white">
							{{ publishActionStatus }} · {{ form.portal_surface }}
						</p>
					</div>
					<div class="rounded-2xl bg-white/10 px-4 py-3 backdrop-blur-sm">
						<p class="type-caption text-white/60">Issuing scope</p>
						<p class="mt-1 type-body-strong text-white">
							{{ issuingScopeLabel }}
						</p>
					</div>
				</div>
			</section>
		</aside>
	</div>
</template>

<script setup lang="ts">
import { FormControl, TextEditor } from 'frappe-ui';

import OrgCommunicationQuickCreateAttachmentSection from './OrgCommunicationQuickCreateAttachmentSection.vue';
import type { OrgCommunicationAttachmentRow } from '@/types/contracts/org_communication_attachments/shared';
import type { OrgCommunicationAudiencePreset } from '@/types/contracts/org_communication_quick_create/get_org_communication_quick_create_options';
import type {
	AttachmentSectionState,
	AudienceRowState,
	AudienceSummaryRow,
	AudienceTargetSearchItem,
	MessageEditorButton,
	QuickCreateSelectOption,
	RecipientField,
	RecipientToggleDefinition,
} from './orgCommunicationQuickCreateTypes';

defineProps<{
	form: {
		title: string;
		communication_type: string;
		organization: string;
		school: string;
		message: string;
		internal_note: string;
		priority: string;
		portal_surface: string;
		brief_order: string;
		publish_from: string;
		publish_to: string;
		brief_start_date: string;
		brief_end_date: string;
		interaction_mode: string;
		allow_private_notes: boolean;
		allow_public_thread: boolean;
	};
	submitting: boolean;
	communicationTypeOptions: QuickCreateSelectOption[];
	organizationSelectOptions: QuickCreateSelectOption[];
	schoolSelectOptions: QuickCreateSelectOption[];
	priorityOptions: QuickCreateSelectOption[];
	portalSurfaceOptions: QuickCreateSelectOption[];
	interactionModeOptions: QuickCreateSelectOption[];
	audiencePresets: OrgCommunicationAudiencePreset[];
	organizationHelpText: string;
	schoolHelpText: string;
	issuingSchoolSelectionLocked: boolean;
	audienceSchoolSelectionLocked: boolean;
	attachmentContextLocked: boolean;
	attachmentContextLockMessage: string;
	briefDatesRequired: boolean;
	deliveryValidationMessage: string;
	audienceValidationMessage: string;
	publishActionStatus: string;
	privateNotesDisabled: boolean;
	publicThreadDisabled: boolean;
	privateNotesHelpText: string;
	publicThreadHelpText: string;
	audienceRows: AudienceRowState[];
	recipientToggleDefinitions: RecipientToggleDefinition[];
	canTargetWideSchoolScope: boolean;
	audienceSummaryRows: AudienceSummaryRow[];
	getAudienceRowTitle: (row: AudienceRowState) => string;
	getAudienceRowDescription: (row: AudienceRowState) => string;
	getAudienceSearchItems: (row: AudienceRowState) => AudienceTargetSearchItem[];
	summaryTitle: string;
	summarySubtitle: string;
	issuingScopeLabel: string;
	messageEditorButtons: MessageEditorButton[];
	attachmentSection: AttachmentSectionState;
	getSelectOptionValue: (option: QuickCreateSelectOption) => string;
	getSelectOptionLabel: (option: QuickCreateSelectOption) => string;
	addAudiencePreset: (presetKey: string) => void;
	removeAudienceRow: (rowId: string) => void;
	isRecipientDisabled: (row: AudienceRowState, field: RecipientField) => boolean;
	toggleRecipient: (row: AudienceRowState, field: RecipientField, event: Event) => void;
	searchAudienceTargets: (row: AudienceRowState) => void | Promise<void>;
	selectAudienceSearchItem: (row: AudienceRowState, item: AudienceTargetSearchItem) => void;
	clearAudienceSearchSelection: (row: AudienceRowState) => void;
	updateMessage: (content: string) => void;
	openNativeDatePicker: (event: Event) => void;
}>();

const emit = defineEmits<{
	(e: 'trigger-file-picker'): void;
	(e: 'toggle-link-composer'): void;
	(e: 'reset-link-draft'): void;
	(e: 'submit-link'): void;
	(e: 'delete-attachment', attachment: OrgCommunicationAttachmentRow): void;
}>();
</script>

<style scoped>
.if-org-communication-native-select {
	width: 100%;
	appearance: none;
	border-radius: 1rem;
	border: 1px solid rgb(var(--border-rgb) / 0.8);
	background-color: rgb(var(--surface-rgb));
	background-image:
		linear-gradient(45deg, transparent 50%, rgb(var(--ink-rgb) / 0.55) 50%),
		linear-gradient(135deg, rgb(var(--ink-rgb) / 0.55) 50%, transparent 50%);
	background-position:
		calc(100% - 1.1rem) calc(50% - 0.12rem),
		calc(100% - 0.8rem) calc(50% - 0.12rem);
	background-repeat: no-repeat;
	background-size:
		0.4rem 0.4rem,
		0.4rem 0.4rem;
	box-shadow: var(--shadow-soft);
	color: rgb(var(--ink-rgb));
	font-size: 0.875rem;
	line-height: 1.25rem;
	padding: 0.625rem 2.5rem 0.625rem 0.875rem;
	transition:
		border-color 120ms ease,
		box-shadow 120ms ease,
		background-color 120ms ease;
}

.if-org-communication-native-select:focus {
	border-color: rgb(var(--jacaranda-rgb) / 0.5);
	box-shadow:
		var(--shadow-soft),
		0 0 0 1px rgb(var(--jacaranda-rgb) / 0.3);
	outline: none;
}

.if-org-communication-native-select:disabled {
	cursor: not-allowed;
	background-color: rgb(var(--surface-rgb) / 0.8);
	color: rgb(var(--ink-rgb) / 0.5);
	opacity: 0.8;
}
</style>
