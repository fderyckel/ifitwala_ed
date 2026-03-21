<!-- ifitwala_ed/ui-spa/src/components/communication/OrgCommunicationQuickCreateModal.vue -->
<template>
	<TransitionRoot as="template" :show="open" @after-leave="emitAfterLeave">
		<Dialog
			as="div"
			class="if-overlay if-overlay--meeting"
			:style="overlayStyle"
			:initialFocus="initialFocus"
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
				<div class="if-overlay__backdrop" @click="handleClose('backdrop')" />
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
						<button
							ref="initialFocus"
							type="button"
							class="sr-only"
							aria-hidden="true"
							tabindex="0"
							@click="handleClose('programmatic')"
						>
							Close
						</button>

						<div class="if-overlay__header px-6 pt-6">
							<div class="min-w-0">
								<p class="type-overline text-ink/55">{{ eyebrow }}</p>
								<DialogTitle class="type-h2 text-ink">{{ overlayTitle }}</DialogTitle>
								<p class="mt-1 type-caption text-ink/65">
									{{ overlayDescription }}
								</p>
							</div>
							<button
								type="button"
								class="if-overlay__close"
								aria-label="Close"
								@click="handleClose('programmatic')"
							>
								<FeatherIcon name="x" class="h-5 w-5" />
							</button>
						</div>

						<div class="if-overlay__body space-y-5 px-6 pb-6">
							<div
								v-if="errorMessage"
								class="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 shadow-soft"
								role="alert"
							>
								<p class="type-body-strong text-rose-900">Action blocked</p>
								<p class="mt-1 whitespace-pre-wrap type-caption text-rose-900/80">
									{{ errorMessage }}
								</p>
							</div>

							<div
								v-if="optionsLoading"
								class="flex items-center gap-2 rounded-2xl border border-border/70 bg-white px-4 py-3 text-ink/70"
							>
								<Spinner class="h-4 w-4" />
								<span class="type-caption">Loading communication options...</span>
							</div>

							<form v-else class="space-y-5" @submit.prevent="submit">
								<div
									class="grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1.5fr)_minmax(22rem,0.9fr)]"
								>
									<div class="space-y-5">
										<section
											class="rounded-[28px] border border-border/70 bg-white p-5 shadow-soft"
										>
											<div
												class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between"
											>
												<div class="space-y-1">
													<p class="type-overline text-ink/55">Message</p>
													<h3 class="type-h3 text-ink">Core details</h3>
													<p class="type-caption text-ink/65">
														Use the same organization, school, delivery, and audience rules as
														Desk, without leaving the staff shell.
													</p>
												</div>
												<span
													v-if="isClassEventMode"
													class="rounded-full bg-sky/25 px-3 py-1.5 type-caption text-canopy"
												>
													Class event context locked
												</span>
											</div>

											<div
												class="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]"
											>
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
													<FormControl
														v-model="form.communication_type"
														type="select"
														:options="communicationTypeOptions"
														:disabled="submitting || isClassEventMode"
													/>
												</div>
											</div>

											<div class="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
												<div class="space-y-1">
													<label class="type-label">Organization</label>
													<FormControl
														v-model="form.organization"
														type="select"
														:options="organizationSelectOptions"
														option-label="label"
														option-value="value"
														:disabled="submitting || isClassEventMode"
													/>
													<p class="type-caption text-ink/55">
														{{ organizationHelpText }}
													</p>
												</div>

												<div class="space-y-1">
													<label class="type-label">Issuing school</label>
													<FormControl
														v-model="form.school"
														type="select"
														:options="schoolSelectOptions"
														option-label="label"
														option-value="value"
														:disabled="submitting || schoolSelectionLocked"
													/>
													<p class="type-caption text-ink/55">
														{{ schoolHelpText }}
													</p>
												</div>
											</div>

											<div class="mt-4 space-y-1">
												<label class="type-label">Message</label>
												<FormControl
													v-model="form.message"
													type="textarea"
													:rows="9"
													placeholder="Share the update, call to action, or announcement."
													:disabled="submitting"
												/>
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

										<section
											class="rounded-[28px] border border-border/70 bg-white p-5 shadow-soft"
										>
											<div class="space-y-1">
												<p class="type-overline text-ink/55">Delivery</p>
												<h3 class="type-h3 text-ink">Publishing and surfaces</h3>
												<p class="type-caption text-ink/65">
													{{
														isClassEventMode
															? 'Choose whether this is saved as a draft, scheduled, or published immediately.'
															: 'Publish will send now or schedule from Publish from. Save as draft keeps the communication editable.'
													}}
												</p>
											</div>

											<div v-if="isClassEventMode" class="mt-4 flex flex-wrap gap-2">
												<button
													v-for="statusOption in statusOptions"
													:key="statusOption"
													type="button"
													class="rounded-full px-3 py-1.5 type-button-label transition"
													:class="
														form.status === statusOption
															? 'bg-jacaranda text-white'
															: 'bg-slate-100 text-slate-token hover:bg-slate-200'
													"
													:disabled="submitting"
													@click="form.status = statusOption"
												>
													{{ statusOption }}
												</button>
											</div>
											<div
												v-else
												class="mt-4 rounded-2xl border border-sky/30 bg-sky/10 px-4 py-3"
											>
												<p class="type-caption text-canopy">
													Publish action status:
													<span class="type-body-strong text-canopy">
														{{ publishActionStatus }}
													</span>
												</p>
											</div>

											<div class="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
												<div class="space-y-1">
													<label class="type-label">Priority</label>
													<FormControl
														v-model="form.priority"
														type="select"
														:options="priorityOptions"
														:disabled="submitting"
													/>
												</div>
												<div class="space-y-1">
													<label class="type-label">Portal surface</label>
													<FormControl
														v-model="form.portal_surface"
														type="select"
														:options="portalSurfaceOptions"
														:disabled="submitting"
													/>
												</div>
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

											<div class="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
												<div class="space-y-1">
													<label class="type-label">Publish from</label>
													<input
														v-model="form.publish_from"
														type="datetime-local"
														class="w-full rounded-2xl border border-border/80 bg-white px-3 py-2 text-sm text-ink shadow-sm focus:border-jacaranda/50 focus:ring-1 focus:ring-jacaranda/30"
														:disabled="submitting"
													/>
												</div>
												<div class="space-y-1">
													<label class="type-label">Publish until</label>
													<input
														v-model="form.publish_to"
														type="datetime-local"
														class="w-full rounded-2xl border border-border/80 bg-white px-3 py-2 text-sm text-ink shadow-sm focus:border-jacaranda/50 focus:ring-1 focus:ring-jacaranda/30"
														:disabled="submitting"
													/>
												</div>
											</div>

											<div class="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
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
													/>
												</div>
												<div class="space-y-1">
													<label class="type-label">Brief end date</label>
													<input
														v-model="form.brief_end_date"
														type="date"
														class="w-full rounded-2xl border border-border/80 bg-white px-3 py-2 text-sm text-ink shadow-sm focus:border-jacaranda/50 focus:ring-1 focus:ring-jacaranda/30"
														:disabled="submitting"
													/>
												</div>
											</div>
										</section>

										<section
											class="rounded-[28px] border border-border/70 bg-white p-5 shadow-soft"
										>
											<div
												class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between"
											>
												<div class="space-y-1">
													<p class="type-overline text-ink/55">Audience</p>
													<h3 class="type-h3 text-ink">Targeting</h3>
													<p class="type-caption text-ink/65">
														Choose one or more audience rows. Recipient toggles follow the same
														target-mode rules as Desk.
													</p>
												</div>
												<button
													v-if="!isClassEventMode"
													type="button"
													class="rounded-full border border-border/80 bg-surface px-3 py-1.5 type-button-label text-ink transition hover:border-jacaranda hover:text-jacaranda"
													:disabled="submitting"
													@click="addAudienceRow()"
												>
													Add audience
												</button>
											</div>

											<div class="mt-4 space-y-4">
												<div
													v-for="(row, index) in audienceRows"
													:key="row.id"
													class="rounded-[24px] border border-border/70 bg-surface-soft/70 p-4"
												>
													<div
														class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between"
													>
														<div class="space-y-1">
															<p class="type-caption text-ink/55">Audience row {{ index + 1 }}</p>
															<div class="flex flex-wrap gap-2">
																<button
																	v-for="targetMode in audienceTargetModeOptions"
																	:key="targetMode"
																	type="button"
																	class="rounded-full px-3 py-1.5 type-button-label transition"
																	:class="
																		row.target_mode === targetMode
																			? 'bg-ink text-white'
																			: 'bg-white text-slate-token hover:bg-slate-100'
																	"
																	:disabled="submitting || isAudienceTargetLocked(row)"
																	@click="setAudienceTargetMode(row, targetMode)"
																>
																	{{ targetMode }}
																</button>
															</div>
														</div>

														<button
															v-if="!isClassEventMode && audienceRows.length > 1"
															type="button"
															class="rounded-full border border-border/80 bg-white px-3 py-1.5 type-button-label text-slate-token transition hover:border-rose-300 hover:text-rose-700"
															:disabled="submitting"
															@click="removeAudienceRow(row.id)"
														>
															Remove
														</button>
													</div>

													<div class="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
														<div v-if="row.target_mode === 'School Scope'" class="space-y-1">
															<label class="type-label">Audience school</label>
															<FormControl
																v-model="row.school"
																type="select"
																:options="schoolSelectOptions"
																option-label="label"
																option-value="value"
																:disabled="submitting || schoolSelectionLocked"
															/>
															<label
																class="mt-2 inline-flex cursor-pointer items-center gap-2 type-caption text-ink/70"
															>
																<input
																	v-model="row.include_descendants"
																	type="checkbox"
																	class="rounded border-slate-300 text-jacaranda"
																	:disabled="submitting"
																/>
																Include descendant schools
															</label>
														</div>

														<div v-else-if="row.target_mode === 'Team'" class="space-y-1">
															<label class="type-label">Team</label>
															<FormControl
																v-model="row.team"
																type="select"
																:options="teamSelectOptions"
																option-label="label"
																option-value="value"
																:disabled="submitting"
															/>
														</div>

														<div v-else class="space-y-1">
															<label class="type-label">Student group</label>
															<FormControl
																v-model="row.student_group"
																type="select"
																:options="studentGroupSelectOptions"
																option-label="label"
																option-value="value"
																:disabled="submitting || isClassEventMode"
															/>
														</div>

														<div class="space-y-2">
															<label class="type-label">Recipients</label>
															<div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
																<label
																	v-for="recipient in recipientToggleDefinitions"
																	:key="recipient.field"
																	class="flex items-center gap-2 rounded-2xl border border-border/70 bg-white px-3 py-2 type-caption text-ink/75"
																	:class="
																		isRecipientDisabled(row, recipient.field) ? 'opacity-55' : ''
																	"
																>
																	<input
																		:checked="Boolean(row[recipient.field])"
																		type="checkbox"
																		class="rounded border-slate-300 text-jacaranda"
																		:disabled="
																			submitting || isRecipientDisabled(row, recipient.field)
																		"
																		@change="toggleRecipient(row, recipient.field, $event)"
																	/>
																	<span>{{ recipient.label }}</span>
																</label>
															</div>
															<p
																v-if="
																	row.target_mode === 'School Scope' && !canTargetWideSchoolScope
																"
																class="type-caption text-amber-700"
															>
																School-scope Staff and Community rows require Academic Admin,
																Assistant Admin, HR Manager, Accounts Manager, or System Manager.
															</p>
														</div>
													</div>

													<div class="mt-4 space-y-1">
														<label class="type-label">Row note</label>
														<FormControl
															v-model="row.note"
															type="textarea"
															:rows="2"
															placeholder="Optional note for this audience row."
															:disabled="submitting"
														/>
													</div>
												</div>
											</div>
										</section>
									</div>

									<aside class="space-y-5">
										<section
											class="overflow-hidden rounded-[32px] border border-canopy/10 bg-[linear-gradient(160deg,rgba(var(--canopy-rgb),0.96),rgba(var(--ink-rgb),0.92))] p-5 text-white shadow-soft"
										>
											<p class="type-overline text-white/65">Ready check</p>
											<h3 class="mt-1 type-h3 text-white">{{ summaryTitle }}</h3>
											<p class="mt-2 type-caption text-white/70">
												{{ summarySubtitle }}
											</p>

											<div class="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-1">
												<div class="rounded-2xl bg-white/10 px-4 py-3 backdrop-blur-sm">
													<p class="type-caption text-white/60">
														{{ isClassEventMode ? 'Delivery' : 'Publish action' }}
													</p>
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

										<section
											class="rounded-[28px] border border-border/70 bg-white p-5 shadow-soft"
										>
											<p class="type-overline text-ink/55">Interaction</p>
											<h3 class="mt-1 type-h3 text-ink">Thread settings</h3>
											<div class="mt-4 space-y-4">
												<div class="space-y-1">
													<label class="type-label">Interaction mode</label>
													<FormControl
														v-model="form.interaction_mode"
														type="select"
														:options="interactionModeOptions"
														:disabled="submitting"
													/>
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
													<span>Allow private notes to school staff.</span>
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
													<span>Allow audience-visible public thread entries.</span>
												</label>
											</div>
										</section>

										<section
											class="rounded-[28px] border border-border/70 bg-white p-5 shadow-soft"
										>
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
									</aside>
								</div>

								<footer class="if-overlay__footer flex flex-wrap items-center justify-end gap-2">
									<Button
										appearance="secondary"
										:disabled="submitting"
										@click="handleClose('programmatic')"
									>
										Cancel
									</Button>
									<Button
										v-if="!isClassEventMode"
										appearance="secondary"
										:disabled="submitDisabled"
										@click="submitDraft"
									>
										Save as draft
									</Button>
									<Button
										appearance="primary"
										:loading="submitting"
										:disabled="submitDisabled"
										type="submit"
									>
										{{ primarySubmitLabel }}
									</Button>
								</footer>
							</form>
						</div>
					</DialogPanel>
				</TransitionChild>
			</div>
		</Dialog>
	</TransitionRoot>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue';
import {
	Dialog,
	DialogPanel,
	DialogTitle,
	TransitionChild,
	TransitionRoot,
} from '@headlessui/vue';
import { Button, FeatherIcon, FormControl, Spinner } from 'frappe-ui';

import {
	createOrgCommunicationQuick,
	getOrgCommunicationQuickCreateOptions,
} from '@/lib/services/orgCommunicationQuickCreateService';
import type {
	Request as CreateOrgCommunicationQuickRequest,
	OrgCommunicationQuickAudienceRow,
} from '@/types/contracts/org_communication_quick_create/create_org_communication_quick';
import type { Response as OrgCommunicationQuickCreateOptionsResponse } from '@/types/contracts/org_communication_quick_create/get_org_communication_quick_create_options';

type CloseReason = 'backdrop' | 'esc' | 'programmatic';
type EntryMode = 'staff-home' | 'class-event';
type RecipientField = 'to_staff' | 'to_students' | 'to_guardians' | 'to_community';
type AudienceRowState = {
	id: string;
	target_mode: string;
	school: string;
	team: string;
	student_group: string;
	include_descendants: boolean;
	to_staff: boolean;
	to_students: boolean;
	to_guardians: boolean;
	to_community: boolean;
	note: string;
};

const props = defineProps<{
	open: boolean;
	zIndex?: number;
	overlayId?: string;
	entryMode?: EntryMode | null;
	studentGroup?: string | null;
	school?: string | null;
	title?: string | null;
	sessionDate?: string | null;
	courseLabel?: string | null;
	sourceLabel?: string | null;
}>();

const emit = defineEmits<{
	(e: 'close', reason: CloseReason): void;
	(e: 'after-leave'): void;
	(e: 'done', payload?: unknown): void;
}>();

const initialFocus = ref<HTMLElement | null>(null);
const optionsLoading = ref(false);
const submitting = ref(false);
const errorMessage = ref('');
const options = ref<OrgCommunicationQuickCreateOptionsResponse | null>(null);
const audienceRows = ref<AudienceRowState[]>([]);

const form = reactive({
	title: '',
	communication_type: '',
	status: '',
	priority: '',
	portal_surface: '',
	publish_from: '',
	publish_to: '',
	brief_start_date: '',
	brief_end_date: '',
	brief_order: '',
	organization: '',
	school: '',
	message: '',
	internal_note: '',
	interaction_mode: '',
	allow_private_notes: true,
	allow_public_thread: false,
});

const overlayStyle = computed(() => ({
	zIndex: props.zIndex ?? 70,
}));

const mode = computed<EntryMode>(() => {
	if (props.entryMode === 'class-event' || props.studentGroup) return 'class-event';
	return 'staff-home';
});

const isClassEventMode = computed(() => mode.value === 'class-event');
const canTargetWideSchoolScope = computed(() =>
	Boolean(options.value?.permissions?.can_target_wide_school_scope)
);
const context = computed(() => options.value?.context ?? null);

const organizationSelectOptions = computed(() => {
	const rows = options.value?.references.organizations ?? [];
	return rows.map(row => ({
		label: row.abbr
			? `${row.abbr} · ${row.organization_name || row.name}`
			: row.organization_name || row.name,
		value: row.name,
	}));
});

const schoolSelectOptions = computed(() => {
	const rows = (options.value?.references.schools ?? []).filter(row => {
		if (!form.organization) return true;
		return !row.organization || row.organization === form.organization;
	});
	return rows.map(row => ({
		label: row.abbr ? `${row.abbr} · ${row.school_name || row.name}` : row.school_name || row.name,
		value: row.name,
	}));
});

const teamSelectOptions = computed(() => {
	const rows = (options.value?.references.teams ?? []).filter(row => {
		if (form.school && row.school) return row.school === form.school;
		if (form.organization && row.organization) return row.organization === form.organization;
		return true;
	});
	return rows.map(row => ({
		label: row.team_code
			? `${row.team_code} · ${row.team_name || row.name}`
			: row.team_name || row.name,
		value: row.name,
	}));
});

const studentGroupSelectOptions = computed(() => {
	const rows = (options.value?.references.student_groups ?? []).filter(row => {
		if (!form.school) return true;
		return !row.school || row.school === form.school;
	});
	return rows.map(row => ({
		label: row.student_group_abbreviation
			? `${row.student_group_abbreviation} · ${row.student_group_name || row.name}`
			: row.student_group_name || row.name,
		value: row.name,
	}));
});

const communicationTypeOptions = computed(() => options.value?.fields.communication_types ?? []);
const statusOptions = computed(() => options.value?.fields.statuses ?? []);
const priorityOptions = computed(() => options.value?.fields.priorities ?? []);
const portalSurfaceOptions = computed(() => options.value?.fields.portal_surfaces ?? []);
const interactionModeOptions = computed(() => options.value?.fields.interaction_modes ?? []);
const audienceTargetModeOptions = computed(
	() => options.value?.fields.audience_target_modes ?? []
);

const schoolSelectionLocked = computed(() => {
	if (isClassEventMode.value) return true;
	if (!context.value) return false;
	if (context.value.lock_to_default_school) return true;
	return !context.value.can_select_school;
});

const recipientToggleDefinitions: Array<{ field: RecipientField; label: string }> = [
	{ field: 'to_staff', label: 'Staff' },
	{ field: 'to_students', label: 'Students' },
	{ field: 'to_guardians', label: 'Guardians' },
	{ field: 'to_community', label: 'Community' },
];

const eyebrow = computed(
	() => props.sourceLabel || (isClassEventMode.value ? 'Class Event' : 'Staff Home')
);
const overlayTitle = computed(() =>
	isClassEventMode.value ? 'Create class announcement' : 'Create org communication'
);
const overlayDescription = computed(() =>
	isClassEventMode.value
		? 'Create an org communication from this class context without leaving the calendar flow.'
		: 'Publish or save a communication for staff, a student group, or your broader school community from Staff Home.'
);
const isFuturePublishFrom = computed(() => {
	if (!form.publish_from) return false;
	return toTimestamp(form.publish_from) > Date.now();
});
const publishActionStatus = computed(() => {
	if (isClassEventMode.value) return form.status || 'Published';
	return isFuturePublishFrom.value ? 'Scheduled' : 'Published';
});
const primarySubmitLabel = computed(() =>
	isClassEventMode.value
		? form.status === 'Draft'
			? 'Save draft'
			: 'Create communication'
		: 'Publish'
);
const summaryTitle = computed(() =>
	form.title.trim() ? form.title.trim() : 'Untitled communication'
);
const summarySubtitle = computed(() => {
	if (isClassEventMode.value) {
		const parts = [props.courseLabel, props.sessionDate].filter(Boolean);
		return parts.length ? parts.join(' · ') : 'Class event communication';
	}
	return 'Check issuing scope, thread settings, and audience rows before publishing.';
});
const issuingScopeLabel = computed(() => {
	const schoolOption = schoolSelectOptions.value.find(option => option.value === form.school);
	const orgOption = organizationSelectOptions.value.find(
		option => option.value === form.organization
	);
	if (schoolOption) return schoolOption.label;
	if (orgOption) return orgOption.label;
	return 'No issuing scope selected';
});
const briefDatesRequired = computed(() =>
	['Morning Brief', 'Everywhere'].includes(String(form.portal_surface || '').trim())
);
const privateNotesDisabled = computed(() => form.interaction_mode === 'None');
const publicThreadDisabled = computed(() => form.interaction_mode === 'None');
const organizationHelpText = computed(
	() => 'Organization is required and defaults from your user scope.'
);
const schoolHelpText = computed(() => {
	if (!context.value) return 'Loading school scope...';
	if (isClassEventMode.value)
		return 'Class event entry keeps the issuing school aligned to the selected class.';
	if (context.value.lock_to_default_school) {
		return 'Issuing School is fixed to your default school when your school scope is locked.';
	}
	if (context.value.can_select_school || context.value.is_privileged) {
		return context.value.is_privileged
			? 'Optional issuing school within your scope. Leave blank for organization-level communication.'
			: 'Optional issuing school from your organization scope.';
	}
	return 'No issuing school scope is configured. Use organization-level communication or ask admin to configure school scope.';
});

const audienceSummaryRows = computed(() =>
	audienceRows.value.map(row => {
		let scope = row.target_mode;
		if (row.target_mode === 'School Scope') {
			scope =
				schoolSelectOptions.value.find(option => option.value === row.school)?.label ||
				row.school ||
				'School scope';
		} else if (row.target_mode === 'Team') {
			scope =
				teamSelectOptions.value.find(option => option.value === row.team)?.label ||
				row.team ||
				'Team';
		} else if (row.target_mode === 'Student Group') {
			scope =
				studentGroupSelectOptions.value.find(option => option.value === row.student_group)
					?.label ||
				row.student_group ||
				'Student group';
		}
		const recipients = recipientToggleDefinitions
			.filter(recipient => Boolean(row[recipient.field]))
			.map(recipient => recipient.label)
			.join(', ');
		return {
			id: row.id,
			scope,
			recipients: recipients || 'No recipients selected',
		};
	})
);

const validationMessage = computed(() => {
	if (!form.title.trim()) return 'Title is required.';
	if (!form.communication_type) return 'Communication type is required.';
	if (!form.status) return 'Status is required.';
	if (!form.organization) return 'Organization is required.';
	if (briefDatesRequired.value && !form.brief_start_date) {
		return 'Brief Start Date is required when Portal Surface is Morning Brief or Everywhere.';
	}
	if (
		form.brief_start_date &&
		form.brief_end_date &&
		form.brief_end_date < form.brief_start_date
	) {
		return 'Brief End Date cannot be before Brief Start Date.';
	}
	if (
		form.publish_from &&
		form.publish_to &&
		toTimestamp(form.publish_to) < toTimestamp(form.publish_from)
	) {
		return 'Publish Until cannot be earlier than Publish From.';
	}
	if (form.status === 'Scheduled' && !form.publish_from) {
		return "Scheduled communications must have a 'Publish From' datetime.";
	}
	if (
		form.status === 'Scheduled' &&
		form.publish_from &&
		toTimestamp(form.publish_from) <= Date.now()
	) {
		return 'Publish From for a Scheduled communication must be in the future.';
	}
	if (!audienceRows.value.length)
		return 'Please add at least one Audience for this communication.';
	for (const row of audienceRows.value) {
		if (!row.target_mode) return 'Target Mode is required for each Audience row.';
		if (row.target_mode === 'School Scope' && !row.school) {
			return 'Audience row for School Scope must specify a School.';
		}
		if (row.target_mode === 'Team' && !row.team) {
			return 'Audience row for Team must specify a Team.';
		}
		if (row.target_mode === 'Student Group' && !row.student_group) {
			return 'Audience row for Student Group must specify a Student Group.';
		}
		if (!recipientToggleDefinitions.some(recipient => Boolean(row[recipient.field]))) {
			return 'Audience row must include at least one Recipient toggle.';
		}
		if (
			!canTargetWideSchoolScope.value &&
			row.target_mode === 'School Scope' &&
			(row.to_staff || row.to_community)
		) {
			return 'You are not allowed to target Staff or Community at School Scope from your current role.';
		}
	}
	return '';
});

const submitDisabled = computed(
	() =>
		submitting.value || optionsLoading.value || !options.value || Boolean(validationMessage.value)
);

function emitAfterLeave() {
	emit('after-leave');
}

function handleClose(reason: CloseReason = 'programmatic') {
	emit('close', reason);
}

function onDialogClose(_payload: unknown) {
	// no-op by design
}

function onKeydown(event: KeyboardEvent) {
	if (!props.open) return;
	if (event.key === 'Escape') handleClose('esc');
}

watch(
	() => props.open,
	open => {
		if (open) document.addEventListener('keydown', onKeydown, true);
		else document.removeEventListener('keydown', onKeydown, true);
	},
	{ immediate: true }
);

watch(
	() => props.open,
	async open => {
		if (!open) return;
		errorMessage.value = '';
		await bootstrap();
	},
	{ immediate: true }
);

watch(
	() => form.organization,
	organization => {
		if (!organization || schoolSelectionLocked.value) return;
		const currentSchoolAllowed = schoolSelectOptions.value.some(
			option => option.value === form.school
		);
		if (!currentSchoolAllowed) {
			form.school = '';
		}
		for (const row of audienceRows.value) {
			if (row.target_mode !== 'School Scope') continue;
			const rowSchoolAllowed = schoolSelectOptions.value.some(
				option => option.value === row.school
			);
			if (!rowSchoolAllowed) row.school = form.school;
		}
	}
);

watch(
	() => form.interaction_mode,
	modeValue => {
		if (modeValue !== 'None') return;
		form.allow_public_thread = false;
		form.allow_private_notes = false;
	}
);

onBeforeUnmount(() => {
	document.removeEventListener('keydown', onKeydown, true);
});

async function bootstrap() {
	await loadOptions();
	if (options.value) initializeForm();
}

async function loadOptions() {
	if (optionsLoading.value) return;
	optionsLoading.value = true;
	try {
		options.value = await getOrgCommunicationQuickCreateOptions({});
	} catch (error) {
		errorMessage.value =
			error instanceof Error ? error.message : 'Unable to load communication options.';
	} finally {
		optionsLoading.value = false;
	}
}

function initializeForm() {
	const defaults = options.value?.defaults;
	if (!defaults) return;

	const matchedSchool = props.school
		? (options.value?.references.schools ?? []).find(row => row.name === props.school)
		: null;
	const defaultOrganization =
		matchedSchool?.organization || context.value?.default_organization || '';
	const schoolCandidates = (options.value?.references.schools ?? []).filter(row => {
		if (!defaultOrganization) return true;
		return !row.organization || row.organization === defaultOrganization;
	});
	const defaultSchool =
		props.school ||
		(isClassEventMode.value ? '' : context.value?.default_school) ||
		(schoolCandidates.length === 1 ? schoolCandidates[0]?.name : '') ||
		'';

	form.title = props.title || '';
	form.communication_type = isClassEventMode.value
		? 'Class Announcement'
		: defaults.communication_type;
	form.status = isClassEventMode.value ? 'Published' : defaults.status;
	form.priority = defaults.priority;
	form.portal_surface = isClassEventMode.value ? 'Everywhere' : defaults.portal_surface;
	form.publish_from = formatDateTimeInput(new Date());
	form.publish_to = '';
	form.brief_start_date = props.sessionDate || '';
	form.brief_end_date = props.sessionDate || '';
	form.brief_order = '';
	form.organization = defaultOrganization;
	form.school = defaultSchool;
	form.message = '';
	form.internal_note = '';
	form.interaction_mode = defaults.interaction_mode;
	form.allow_private_notes =
		defaults.interaction_mode === 'None' ? false : Boolean(defaults.allow_private_notes);
	form.allow_public_thread =
		defaults.interaction_mode === 'None' ? false : Boolean(defaults.allow_public_thread);

	if (isClassEventMode.value && props.studentGroup) {
		audienceRows.value = [
			createAudienceRow({
				target_mode: 'Student Group',
				student_group: props.studentGroup,
				to_students: true,
				to_guardians: true,
				to_staff: false,
				to_community: false,
			}),
		];
		return;
	}

	audienceRows.value = [
		createAudienceRow({
			target_mode: 'School Scope',
			school: form.school,
			include_descendants: true,
		}),
	];
}

function createAudienceRow(seed: Partial<AudienceRowState> = {}): AudienceRowState {
	const row: AudienceRowState = {
		id: `aud_${Date.now()}_${Math.random().toString(16).slice(2)}`,
		target_mode: seed.target_mode || 'School Scope',
		school: seed.school || '',
		team: seed.team || '',
		student_group: seed.student_group || '',
		include_descendants: Boolean(seed.include_descendants ?? true),
		to_staff: Boolean(seed.to_staff ?? false),
		to_students: Boolean(seed.to_students ?? false),
		to_guardians: Boolean(seed.to_guardians ?? false),
		to_community: Boolean(seed.to_community ?? false),
		note: seed.note || '',
	};
	applyAudienceDefaults(row);
	return row;
}

function addAudienceRow() {
	audienceRows.value.push(
		createAudienceRow({
			target_mode: 'School Scope',
			school: form.school,
			include_descendants: true,
		})
	);
}

function removeAudienceRow(rowId: string) {
	audienceRows.value = audienceRows.value.filter(row => row.id !== rowId);
}

function isAudienceTargetLocked(row: AudienceRowState) {
	return isClassEventMode.value && row.student_group === props.studentGroup;
}

function setAudienceTargetMode(row: AudienceRowState, targetMode: string) {
	row.target_mode = targetMode;
	row.school = targetMode === 'School Scope' ? form.school || row.school : '';
	row.team = targetMode === 'Team' ? row.team : '';
	row.student_group = targetMode === 'Student Group' ? row.student_group : '';
	row.include_descendants = targetMode === 'School Scope';
	applyAudienceDefaults(row);
}

function allowedRecipientFields(targetMode: string): RecipientField[] {
	return (options.value?.recipient_rules?.[targetMode]?.allowed_fields ?? []) as RecipientField[];
}

function applyAudienceDefaults(row: AudienceRowState) {
	const allowed = new Set(allowedRecipientFields(row.target_mode));

	for (const recipient of recipientToggleDefinitions) {
		if (!allowed.has(recipient.field)) {
			row[recipient.field] = false;
		}
	}

	if (row.target_mode === 'Team') {
		row.to_staff = true;
		return;
	}

	if (row.target_mode === 'Student Group') {
		if (!row.to_staff && !row.to_students && !row.to_guardians) {
			row.to_students = true;
			row.to_guardians = true;
		}
		return;
	}

	if (row.target_mode === 'School Scope' && !row.school && form.school) {
		row.school = form.school;
	}
}

function isRecipientDisabled(row: AudienceRowState, field: RecipientField) {
	const allowed = new Set(allowedRecipientFields(row.target_mode));
	if (!allowed.has(field)) return true;
	if (
		row.target_mode === 'School Scope' &&
		!canTargetWideSchoolScope.value &&
		(field === 'to_staff' || field === 'to_community')
	) {
		return true;
	}
	if (row.target_mode === 'Team' && field === 'to_staff') return true;
	if (isClassEventMode.value && row.target_mode === 'Student Group' && field === 'to_students')
		return true;
	return false;
}

function toggleRecipient(row: AudienceRowState, field: RecipientField, event: Event) {
	const target = event.target as HTMLInputElement | null;
	if (!target) return;
	row[field] = target.checked;
	applyAudienceDefaults(row);
}

function toFrappeDatetime(value: string) {
	if (!value) return null;
	if (value.includes('T')) {
		const [date, timeRaw] = value.split('T');
		const [hour = '00', minute = '00', second = '00'] = timeRaw.split(':');
		return `${date} ${hour}:${minute}:${second}`;
	}
	return value;
}

function formatDateInput(date: Date) {
	const year = date.getFullYear();
	const month = String(date.getMonth() + 1).padStart(2, '0');
	const day = String(date.getDate()).padStart(2, '0');
	return `${year}-${month}-${day}`;
}

function formatDateTimeInput(date: Date) {
	const hours = String(date.getHours()).padStart(2, '0');
	const minutes = String(date.getMinutes()).padStart(2, '0');
	return `${formatDateInput(date)}T${hours}:${minutes}`;
}

function toTimestamp(value: string) {
	const normalized = value.includes('T') ? value : value.replace(' ', 'T');
	const timestamp = new Date(normalized).getTime();
	return Number.isNaN(timestamp) ? 0 : timestamp;
}

function buildAudiencePayload(): OrgCommunicationQuickAudienceRow[] {
	return audienceRows.value.map(row => ({
		target_mode: row.target_mode,
		school: row.school || null,
		team: row.team || null,
		student_group: row.student_group || null,
		include_descendants: row.include_descendants ? 1 : 0,
		to_staff: row.to_staff ? 1 : 0,
		to_students: row.to_students ? 1 : 0,
		to_guardians: row.to_guardians ? 1 : 0,
		to_community: row.to_community ? 1 : 0,
		note: row.note.trim() || null,
	}));
}

function buildPayload(statusOverride?: string): CreateOrgCommunicationQuickRequest {
	const briefStartDate = form.brief_start_date || null;
	const briefEndDate = form.brief_end_date || briefStartDate;
	return {
		title: form.title.trim(),
		communication_type: form.communication_type,
		status: statusOverride || form.status,
		priority: form.priority,
		portal_surface: form.portal_surface,
		publish_from: toFrappeDatetime(form.publish_from),
		publish_to: toFrappeDatetime(form.publish_to),
		brief_start_date: briefStartDate,
		brief_end_date: briefEndDate,
		brief_order: form.brief_order ? Number(form.brief_order) : null,
		organization: form.organization || null,
		school: form.school || null,
		message: form.message || null,
		internal_note: form.internal_note || null,
		interaction_mode: form.interaction_mode || null,
		allow_private_notes: form.allow_private_notes ? 1 : 0,
		allow_public_thread: form.allow_public_thread ? 1 : 0,
		audiences: buildAudiencePayload(),
		client_request_id: `org_comm_${Date.now()}_${Math.random().toString(16).slice(2)}`,
	};
}

async function submit() {
	if (!isClassEventMode.value) {
		await submitPublish();
		return;
	}
	await submitWithStatus(form.status);
}

async function submitDraft() {
	await submitWithStatus('Draft');
}

async function submitPublish() {
	await submitWithStatus(isFuturePublishFrom.value ? 'Scheduled' : 'Published');
}

async function submitWithStatus(statusOverride: string) {
	const validationError = validationMessage.value;
	if (validationError) {
		errorMessage.value = validationError;
		return;
	}

	errorMessage.value = '';
	submitting.value = true;

	try {
		const response = await createOrgCommunicationQuick(buildPayload(statusOverride));
		emit('close', 'programmatic');
		emit('done', response);
	} catch (error) {
		errorMessage.value =
			error instanceof Error ? error.message : 'Unable to create communication.';
	} finally {
		submitting.value = false;
	}
}
</script>
