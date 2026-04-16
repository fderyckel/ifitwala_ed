<!-- ifitwala_ed/ui-spa/src/overlays/admissions/AdmissionsWorkspaceOverlay.vue -->
<template>
	<TransitionRoot as="template" :show="open" @after-leave="emitAfterLeave">
		<Dialog
			as="div"
			class="if-overlay if-overlay--admissions"
			:style="overlayStyle"
			:initialFocus="closeBtnRef"
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
					<DialogPanel class="if-overlay__panel interview-workspace__panel">
						<header class="interview-workspace__header px-6 pt-6">
							<div class="min-w-0">
								<p class="type-overline text-ink/60">{{ workspaceOverline }}</p>
								<DialogTitle class="type-h2 text-canopy truncate">
									{{ applicantDisplayName || 'Applicant Workspace' }}
								</DialogTitle>
								<p class="type-caption text-ink/65 mt-1">
									{{ interviewWindowLabel }}
								</p>
							</div>

							<div class="flex items-center gap-2">
								<button
									v-if="showBackToApplicant"
									type="button"
									class="if-action"
									@click="returnToApplicantMode"
								>
									Back to Applicant
								</button>
								<button
									ref="closeBtnRef"
									type="button"
									class="if-overlay__icon-button"
									@click="emitClose('programmatic')"
									aria-label="Close admissions workspace"
								>
									<FeatherIcon name="x" class="h-5 w-5" />
								</button>
							</div>
						</header>

						<section
							ref="bodyScrollRef"
							class="if-overlay__body interview-workspace__body px-6 pb-6"
						>
							<div v-if="loading" class="space-y-3 py-10">
								<div class="if-skel h-6 w-2/3" />
								<div class="if-skel h-20 w-full rounded-xl" />
								<div class="if-skel h-48 w-full rounded-xl" />
							</div>

							<div
								v-else-if="errorText"
								class="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3"
							>
								<p class="type-body-strong text-rose-900">Unable to load admissions workspace</p>
								<p class="type-caption text-rose-900/85 mt-1">{{ errorText }}</p>
								<div class="mt-4 flex justify-end gap-2">
									<button class="if-action" type="button" @click="emitClose('programmatic')">
										Close
									</button>
									<button class="if-action" type="button" @click="loadWorkspace">Retry</button>
								</div>
							</div>

							<div v-else-if="hasWorkspace" class="space-y-4">
								<section v-if="isGuardianMode && selectedGuardian" class="space-y-4">
									<article class="interview-card">
										<div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
											<div class="flex items-start gap-4">
												<div
													v-if="selectedGuardian.image"
													class="h-16 w-16 overflow-hidden rounded-2xl border border-border/60 bg-slate-50"
												>
													<img
														:src="selectedGuardian.image"
														:alt="selectedGuardian.full_name || 'Guardian photo'"
														class="h-full w-full object-cover"
													/>
												</div>
												<div class="min-w-0">
													<div class="flex flex-wrap items-center gap-2">
														<h3 class="type-h3 text-ink">
															{{ selectedGuardian.full_name || 'Guardian' }}
														</h3>
														<span
															v-if="selectedGuardian.relationship"
															class="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-xs font-semibold text-slate-700"
														>
															{{ selectedGuardian.relationship }}
														</span>
														<span
															v-if="
																selectedGuardian.is_primary || selectedGuardian.is_primary_guardian
															"
															class="rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-xs font-semibold text-emerald-900"
														>
															Primary
														</span>
														<span
															v-if="selectedGuardian.is_financial_guardian"
															class="rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-xs font-semibold text-amber-900"
														>
															Financial
														</span>
													</div>
													<p class="mt-1 type-caption text-ink/65">
														Guardian intake details captured on the applicant profile.
													</p>
												</div>
											</div>
										</div>
									</article>

									<article class="interview-card">
										<h3 class="type-h3 text-ink">Profile</h3>
										<div class="mt-3 grid gap-3 sm:grid-cols-2">
											<div v-for="field in guardianProfileFields" :key="field.label">
												<p class="type-caption text-ink/65">{{ field.label }}</p>
												<p class="type-body text-ink break-words">{{ field.value }}</p>
											</div>
										</div>
									</article>

									<article class="interview-card">
										<h3 class="type-h3 text-ink">Contact & Access</h3>
										<div class="mt-3 grid gap-3 sm:grid-cols-2">
											<div v-for="field in guardianContactFields" :key="field.label">
												<p class="type-caption text-ink/65">{{ field.label }}</p>
												<p class="type-body text-ink break-words">{{ field.value }}</p>
											</div>
										</div>
									</article>

									<article class="interview-card">
										<h3 class="type-h3 text-ink">Work Details</h3>
										<div class="mt-3 grid gap-3 sm:grid-cols-2">
											<div v-for="field in guardianWorkFields" :key="field.label">
												<p class="type-caption text-ink/65">{{ field.label }}</p>
												<p class="type-body text-ink break-words">{{ field.value }}</p>
											</div>
										</div>
									</article>
								</section>

								<section v-else class="space-y-4">
									<article class="interview-card">
										<h3 class="type-h3 text-ink">Applicant Brief</h3>
										<div class="mt-3 grid gap-3 sm:grid-cols-2">
											<div>
												<p class="type-caption text-ink/65">Status</p>
												<p class="type-body-strong text-ink">
													{{ workspaceApplicant?.application_status || '—' }}
												</p>
											</div>
											<div>
												<p class="type-caption text-ink/65">Program Intent</p>
												<p class="type-body-strong text-ink">
													{{ workspaceApplicant?.program || '—' }}
													<span v-if="workspaceApplicant?.program_offering" class="text-ink/65">
														· {{ workspaceApplicant.program_offering }}
													</span>
												</p>
											</div>
											<div>
												<p class="type-caption text-ink/65">School</p>
												<p class="type-body text-ink">{{ workspaceApplicant?.school || '—' }}</p>
											</div>
											<div>
												<p class="type-caption text-ink/65">Applicant Email</p>
												<p class="type-body text-ink">
													{{ workspaceApplicant?.applicant_email || '—' }}
												</p>
											</div>
											<div>
												<p class="type-caption text-ink/65">Submitted</p>
												<p class="type-body text-ink">
													{{ formatHumanDateTime(workspaceApplicant?.submitted_at) }}
												</p>
											</div>
											<div>
												<p class="type-caption text-ink/65">Date of Birth</p>
												<p class="type-body text-ink">
													{{
														formatHumanDate(workspaceApplicant?.student_date_of_birth, {
															includeYear: true,
															includeWeekday: false,
														})
													}}
												</p>
											</div>
										</div>
									</article>

									<article class="interview-card">
										<div class="flex items-center justify-between gap-2">
											<h3 class="type-h3 text-ink">Guardians</h3>
											<span
												class="type-badge-label rounded-full bg-sky/20 px-2 py-0.5 text-ink/70"
											>
												{{ workspaceApplicant?.guardians?.length || 0 }}
											</span>
										</div>
										<div
											v-if="!(workspaceApplicant?.guardians?.length || 0)"
											class="mt-2 type-caption text-ink/60"
										>
											No guardian details available.
										</div>
										<ul v-else class="mt-3 space-y-2">
											<li
												v-for="guardian in workspaceApplicant?.guardians || []"
												:key="guardian.guardian || guardian.full_name"
												class="rounded-xl border border-border/60 bg-white"
											>
												<button
													type="button"
													class="flex w-full items-start justify-between gap-3 px-3 py-2 text-left transition hover:bg-slate-50"
													@click="openGuardianDetails(guardian)"
												>
													<div class="min-w-0">
														<p class="type-body-strong text-ink">
															{{ guardian.full_name || 'Guardian' }}
															<span class="text-ink/60">· {{ guardian.relationship || '—' }}</span>
														</p>
														<p class="type-caption text-ink/70 mt-1">
															{{ guardian.email || 'No personal email' }}
															<span v-if="guardian.mobile_phone">
																· {{ guardian.mobile_phone }}
															</span>
														</p>
													</div>
													<span class="type-caption text-canopy whitespace-nowrap">
														Open details
													</span>
												</button>
											</li>
										</ul>
									</article>

									<article class="interview-card">
										<div class="flex items-center justify-between gap-2">
											<h3 class="type-h3 text-ink">Interviews</h3>
											<span
												class="type-badge-label rounded-full bg-sky/20 px-2 py-0.5 text-ink/70"
											>
												{{ workspaceInterviews.length }}
											</span>
										</div>
										<div v-if="!workspaceInterviews.length" class="mt-2 type-caption text-ink/60">
											No interviews recorded yet for this applicant.
										</div>
										<ul v-else class="mt-3 space-y-2 max-h-72 overflow-y-auto pr-1">
											<li
												v-for="item in workspaceInterviews"
												:key="item.name"
												class="rounded-xl border px-3 py-2"
												:class="
													isActiveInterview(item.name)
														? 'border-canopy bg-canopy/5'
														: 'border-border/60 bg-white'
												"
											>
												<div class="flex items-start justify-between gap-3">
													<div class="min-w-0">
														<p class="type-body-strong text-ink truncate">
															{{ item.interview_type || 'Interview' }}
															<span class="text-ink/60">· {{ item.name }}</span>
														</p>
														<p class="type-caption text-ink/70 mt-1">
															{{ formatInterviewStart(item) }}
															<span v-if="formatInterviewEnd(item)">
																→ {{ formatInterviewEnd(item) }}</span
															>
														</p>
														<p
															v-if="item.interviewers?.length"
															class="type-caption text-ink/65 mt-1 truncate"
														>
															{{ item.interviewers.map(row => row.name || row.user).join(', ') }}
														</p>
														<p
															v-if="interviewFeedbackStatusLabel(item)"
															class="type-caption mt-1 font-medium"
															:class="
																interviewFeedbackComplete(item)
																	? 'text-emerald-700'
																	: 'text-amber-800'
															"
														>
															{{ interviewFeedbackStatusLabel(item) }}
														</p>
													</div>
													<button
														type="button"
														class="if-action"
														:disabled="loading"
														@click="openInterview(item.name)"
													>
														{{ isActiveInterview(item.name) ? 'Opened' : 'Open' }}
													</button>
												</div>
											</li>
										</ul>
									</article>

									<template v-if="isInterviewMode && workspace">
										<article class="interview-card">
											<h3 class="type-h3 text-ink">Interview Context</h3>
											<div class="mt-3 grid gap-3 sm:grid-cols-2">
												<div>
													<p class="type-caption text-ink/65">Interview Type</p>
													<p class="type-body text-ink">
														{{ workspace.interview.interview_type || '—' }}
													</p>
												</div>
												<div>
													<p class="type-caption text-ink/65">Mode</p>
													<p class="type-body text-ink">
														{{ workspace.interview.mode || '—' }}
													</p>
												</div>
												<div>
													<p class="type-caption text-ink/65">Confidentiality</p>
													<p class="type-body text-ink">
														{{ workspace.interview.confidentiality_level || '—' }}
													</p>
												</div>
												<div>
													<p class="type-caption text-ink/65">Scheduled</p>
													<p class="type-body text-ink">
														{{ formatInterviewStart(workspace.interview) }}
														<span v-if="formatInterviewEnd(workspace.interview)">
															→ {{ formatInterviewEnd(workspace.interview) }}
														</span>
													</p>
												</div>
											</div>
											<div
												v-if="workspace.interview.operational_notes"
												class="mt-3 rounded-xl border border-border/60 bg-slate-50 px-3 py-3"
											>
												<p class="type-caption text-ink/65">Operational Notes</p>
												<p class="type-body text-ink whitespace-pre-line mt-1">
													{{ workspace.interview.operational_notes }}
												</p>
											</div>
										</article>

										<article class="interview-card">
											<h3 class="type-h3 text-ink">Interview Team</h3>
											<ul class="mt-3 space-y-2">
												<li
													v-for="member in workspace.feedback.panel"
													:key="member.interviewer_user"
													class="rounded-xl border border-border/60 px-3 py-2 flex items-center justify-between gap-2"
												>
													<p class="type-body text-ink">
														{{ member.interviewer_name || member.interviewer_user }}
													</p>
													<span
														class="type-caption rounded-full bg-sky/20 px-2 py-0.5 text-ink/70"
													>
														{{ member.feedback_status || 'Pending' }}
													</span>
												</li>
											</ul>
										</article>

										<article class="interview-card">
											<h3 class="type-h3 text-ink">Interview Notes</h3>
											<p class="type-caption text-ink/65 mt-1">
												Your notes are saved separately per interviewer to avoid edit collisions.
											</p>

											<div
												v-if="formError"
												class="mt-3 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 type-caption text-rose-900"
											>
												{{ formError }}
											</div>
											<div
												v-if="saveNotice"
												class="mt-3 rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 type-caption text-emerald-900"
											>
												{{ saveNotice }}
											</div>

											<div class="mt-3 space-y-3">
												<label class="block space-y-1">
													<span class="type-caption text-ink/70">Recommendation</span>
													<select
														v-model="formRecommendation"
														class="if-field"
														:disabled="!canEdit || submitting"
													>
														<option value="">Select recommendation</option>
														<option
															v-for="option in recommendationOptions"
															:key="option"
															:value="option"
														>
															{{ option }}
														</option>
													</select>
												</label>

												<label class="block space-y-1">
													<span class="type-caption text-ink/70">Strengths</span>
													<textarea
														v-model="formStrengths"
														class="if-field"
														rows="3"
														:disabled="!canEdit || submitting"
													></textarea>
												</label>

												<label class="block space-y-1">
													<span class="type-caption text-ink/70">Concerns</span>
													<textarea
														v-model="formConcerns"
														class="if-field"
														rows="3"
														:disabled="!canEdit || submitting"
													></textarea>
												</label>

												<label class="block space-y-1">
													<span class="type-caption text-ink/70">Shared Values</span>
													<textarea
														v-model="formSharedValues"
														class="if-field"
														rows="3"
														:disabled="!canEdit || submitting"
													></textarea>
												</label>

												<label class="block space-y-1">
													<span class="type-caption text-ink/70">Other Notes</span>
													<textarea
														v-model="formOtherNotes"
														class="if-field"
														rows="4"
														:disabled="!canEdit || submitting"
													></textarea>
												</label>
											</div>

											<div class="mt-4 flex flex-wrap items-center justify-end gap-2">
												<button
													type="button"
													class="if-button if-button--secondary"
													:disabled="!canEdit || submitting"
													@click="saveDraft"
												>
													{{ submitting ? 'Saving…' : 'Save Notes' }}
												</button>
												<button
													type="button"
													class="if-button if-button--primary"
													:disabled="!canEdit || submitting"
													@click="submitFeedback"
												>
													{{ submitting ? 'Submitting…' : 'Submit Notes' }}
												</button>
											</div>
											<p v-if="!canEdit" class="type-caption text-ink/60 mt-3">
												You are not assigned to add notes for this interview.
											</p>
										</article>
									</template>

									<article v-else class="interview-card">
										<h3 class="type-h3 text-ink">Interview Notes</h3>
										<p class="type-caption text-ink/70 mt-2">
											Select an interview to view the team status and add your notes.
										</p>
									</article>

									<article v-if="isInterviewMode" class="interview-card">
										<div class="flex items-center justify-between gap-2">
											<h3 class="type-h3 text-ink">Documents</h3>
											<span
												class="type-badge-label rounded-full bg-sky/20 px-2 py-0.5 text-ink/70"
											>
												{{ workspaceDocuments.count }}
											</span>
										</div>
										<div
											v-if="!workspaceDocuments.rows.length"
											class="mt-2 type-caption text-ink/60"
										>
											No applicant documents found.
										</div>
										<ul v-else class="mt-3 space-y-2 max-h-64 overflow-y-auto pr-1">
											<li
												v-for="doc in workspaceDocuments.rows"
												:key="doc.name"
												class="rounded-xl border border-border/60 px-3 py-2"
											>
												<p class="type-body-strong text-ink">
													{{ doc.document_label || doc.document_type || doc.name }}
													<span class="text-ink/60">· {{ doc.review_status || 'Pending' }}</span>
												</p>
												<p class="type-caption text-ink/70 mt-1">
													{{ doc.items.length }} file{{ doc.items.length === 1 ? '' : 's' }}
												</p>
												<ul class="mt-1 space-y-1">
													<li
														v-for="item in doc.items"
														:key="item.name || item.item_key || item.item_label"
														class="type-caption text-ink/75"
													>
														<button
															v-if="item.file_url"
															type="button"
															class="underline"
															@click="
																openWorkspaceFile(
																	item.file_url,
																	item.item_label || item.file_name || 'submitted file'
																)
															"
														>
															{{ item.item_label || item.file_name || 'View file' }}
														</button>
														<span v-else>{{
															item.item_label || item.item_key || 'Submitted file'
														}}</span>
													</li>
												</ul>
											</li>
										</ul>
									</article>

									<article v-else class="interview-card">
										<div class="flex items-start justify-between gap-3">
											<div>
												<h3 class="type-h3 text-ink">Evidence Review</h3>
												<p class="mt-1 type-caption text-ink/65">
													Requirement cards show readiness. Review happens on each submitted file.
												</p>
											</div>
											<span
												class="type-badge-label rounded-full bg-sky/20 px-2 py-0.5 text-ink/70"
											>
												{{ applicantRequirementRows.length }} requirements
											</span>
										</div>

										<div class="mt-3 grid gap-2 sm:grid-cols-3">
											<div class="rounded-xl bg-sky/20 px-3 py-2">
												<p class="type-caption text-ink/70">Complete</p>
												<p class="type-body-strong text-ink">
													{{ completedRequirementCount }}/{{ applicantRequirementRows.length }}
												</p>
											</div>
											<div class="rounded-xl bg-sky/20 px-3 py-2">
												<p class="type-caption text-ink/70">Missing Requirements</p>
												<p class="type-body-strong text-ink">{{ missingRequirementCount }}</p>
											</div>
											<div class="rounded-xl bg-sky/20 px-3 py-2">
												<p class="type-caption text-ink/70">Pending File Reviews</p>
												<p class="type-body-strong text-ink">{{ pendingSubmissionCount }}</p>
											</div>
										</div>

										<div
											v-if="documentActionError"
											class="mt-3 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 type-caption text-rose-900"
										>
											{{ documentActionError }}
										</div>
										<div
											v-if="documentActionNotice"
											class="mt-3 rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 type-caption text-emerald-900"
										>
											{{ documentActionNotice }}
										</div>

										<div
											v-if="!applicantRequirementRows.length"
											class="mt-3 type-caption text-ink/60"
										>
											No document requirements are in scope for this applicant.
										</div>
										<div v-else class="mt-4 space-y-3">
											<section
												v-for="row in applicantRequirementRows"
												:key="row.applicant_document || row.document_type || row.label"
												:id="requirementAnchorId(row) || undefined"
												class="rounded-2xl border border-border/70 bg-white p-4 transition"
												:class="
													isFocusedRequirement(row)
														? 'border-canopy/50 ring-2 ring-canopy/20 shadow-sm'
														: ''
												"
											>
												<div
													class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between"
												>
													<div class="min-w-0">
														<div class="flex flex-wrap items-center gap-2">
															<h4 class="type-body-strong text-ink">
																{{ row.label || row.document_type || 'Requirement' }}
															</h4>
															<span
																class="rounded-full border px-2 py-0.5 text-xs font-semibold"
																:class="requirementStatusClass(row.review_status)"
															>
																{{ row.review_status || 'Pending' }}
															</span>
															<span
																class="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-xs font-semibold text-slate-700"
															>
																{{ formatRequirementProgress(row) }}
															</span>
														</div>
														<p class="mt-1 type-caption text-ink/65">
															{{ formatRequirementMeta(row) }}
														</p>
													</div>

													<div
														v-if="canManageApplicantOverrides"
														class="flex flex-wrap gap-2 lg:justify-end"
													>
														<button
															v-if="row.requirement_override"
															type="button"
															class="if-action"
															:disabled="requirementSubmitting"
															@click="clearRequirementOverride(row)"
														>
															Clear Override
														</button>
														<template v-else>
															<button
																type="button"
																class="if-action"
																:disabled="requirementSubmitting"
																@click="beginRequirementOverride(row, 'Waived')"
															>
																Waive
															</button>
															<button
																type="button"
																class="if-action"
																:disabled="requirementSubmitting"
																@click="beginRequirementOverride(row, 'Exception Approved')"
															>
																Exception
															</button>
														</template>
													</div>
												</div>

												<div
													v-if="row.requirement_override"
													class="mt-3 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2"
												>
													<p class="type-caption text-amber-900">
														{{ row.requirement_override }}
														<span v-if="row.override_reason"> · {{ row.override_reason }}</span>
													</p>
												</div>

												<div
													v-if="isEditingRequirement(row)"
													class="mt-3 rounded-xl border border-slate-200 bg-slate-50 p-3"
												>
													<label class="block space-y-1">
														<span class="type-caption text-ink/70">
															Reason for {{ requirementActionValue }} on
															{{ requirementActionLabel || 'this requirement' }}
														</span>
														<textarea
															v-model="requirementActionReason"
															class="if-field"
															rows="3"
															:disabled="requirementSubmitting"
														></textarea>
													</label>
													<div class="mt-3 flex flex-wrap justify-end gap-2">
														<button
															type="button"
															class="if-button if-button--secondary"
															:disabled="requirementSubmitting"
															@click="cancelRequirementOverride"
														>
															Cancel
														</button>
														<button
															type="button"
															class="if-button if-button--primary"
															:disabled="requirementSubmitting"
															@click="submitRequirementOverride"
														>
															{{ requirementSubmitting ? 'Saving…' : 'Apply Override' }}
														</button>
													</div>
												</div>

												<div v-if="row.items?.length" class="mt-3 space-y-2">
													<div
														v-for="item in row.items"
														:key="item.name || item.item_key || item.item_label"
														:id="submissionAnchorId(item.name) || undefined"
														class="rounded-xl border border-border/60 bg-slate-50/60 p-3 transition"
														:class="
															isFocusedSubmission(item.name)
																? 'border-canopy/50 ring-2 ring-canopy/20 bg-white shadow-sm'
																: ''
														"
													>
														<div
															class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between"
														>
															<div class="min-w-0">
																<div class="flex flex-wrap items-center gap-2">
																	<p class="type-body text-ink">
																		{{ item.item_label || item.item_key || 'Submitted file' }}
																	</p>
																	<span
																		class="rounded-full border px-2 py-0.5 text-xs font-semibold"
																		:class="submissionStatusClass(item.review_status)"
																	>
																		{{ item.review_status || 'Pending' }}
																	</span>
																</div>
																<p class="mt-1 type-caption text-ink/65">
																	{{ formatSubmissionMeta(item) }}
																</p>
																<button
																	v-if="item.file_url"
																	type="button"
																	class="mt-2 inline-flex text-sm font-medium text-canopy underline"
																	@click="
																		openWorkspaceFile(
																			item.file_url,
																			item.file_name || item.item_label || 'submitted file'
																		)
																	"
																>
																	{{ item.file_name || 'Open file' }}
																</button>
															</div>

															<div
																v-if="canReviewApplicantSubmissions && item.name"
																class="flex flex-wrap gap-2 lg:justify-end"
															>
																<button
																	type="button"
																	class="if-action"
																	:disabled="submissionSubmitting"
																	@click="approveSubmission(item)"
																>
																	Approve
																</button>
																<button
																	type="button"
																	class="if-action"
																	:disabled="submissionSubmitting"
																	@click="beginSubmissionDecision(item, 'Needs Follow-Up')"
																>
																	Request Changes
																</button>
																<button
																	type="button"
																	class="if-action"
																	:disabled="submissionSubmitting"
																	@click="beginSubmissionDecision(item, 'Rejected')"
																>
																	Reject
																</button>
															</div>
														</div>

														<div
															v-if="isEditingSubmission(item)"
															class="mt-3 rounded-xl border border-slate-200 bg-white p-3"
														>
															<label class="block space-y-1">
																<span class="type-caption text-ink/70">
																	Review note
																	<span v-if="submissionRequiresNotes"> (required)</span>
																</span>
																<textarea
																	v-model="submissionDecisionNotes"
																	class="if-field"
																	rows="3"
																	:disabled="submissionSubmitting"
																></textarea>
															</label>
															<div class="mt-3 flex flex-wrap justify-end gap-2">
																<button
																	type="button"
																	class="if-button if-button--secondary"
																	:disabled="submissionSubmitting"
																	@click="cancelSubmissionDecision"
																>
																	Cancel
																</button>
																<button
																	type="button"
																	class="if-button if-button--primary"
																	:disabled="submissionSubmitting"
																	@click="submitSubmissionDecision"
																>
																	{{ submissionSubmitting ? 'Saving…' : 'Save Review' }}
																</button>
															</div>
														</div>
													</div>
												</div>
												<p v-else class="mt-3 type-caption text-ink/60">No submitted files yet.</p>
											</section>
										</div>

										<div v-if="applicantSupplementalUploads.length" class="mt-4">
											<h4 class="type-body-strong text-ink">Additional Submitted Files</h4>
											<p class="mt-1 type-caption text-ink/65">
												Optional evidence appears here so staff can review it without leaving
												applicant context.
											</p>
											<div class="mt-3 space-y-2">
												<div
													v-for="row in applicantSupplementalUploads"
													:key="row.applicant_document_item || row.label"
													:id="submissionAnchorId(row.applicant_document_item) || undefined"
													class="rounded-xl border border-border/60 bg-slate-50/60 p-3 transition"
													:class="
														isFocusedSubmission(row.applicant_document_item)
															? 'border-canopy/50 ring-2 ring-canopy/20 bg-white shadow-sm'
															: ''
													"
												>
													<div
														class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between"
													>
														<div class="min-w-0">
															<div class="flex flex-wrap items-center gap-2">
																<p class="type-body text-ink">
																	{{ row.label || row.document_label || 'Submitted file' }}
																</p>
																<span
																	class="rounded-full border px-2 py-0.5 text-xs font-semibold"
																	:class="submissionStatusClass(row.review_status)"
																>
																	{{ row.review_status || 'Pending' }}
																</span>
															</div>
															<p class="mt-1 type-caption text-ink/65">
																{{ formatSubmissionMeta(row) }}
															</p>
															<button
																v-if="row.file_url"
																type="button"
																class="mt-2 inline-flex text-sm font-medium text-canopy underline"
																@click="
																	openWorkspaceFile(
																		row.file_url,
																		row.file_name || row.label || 'submitted file'
																	)
																"
															>
																{{ row.file_name || 'Open file' }}
															</button>
														</div>

														<div
															v-if="canReviewApplicantSubmissions && row.applicant_document_item"
															class="flex flex-wrap gap-2 lg:justify-end"
														>
															<button
																type="button"
																class="if-action"
																:disabled="submissionSubmitting"
																@click="
																	approveSubmission({
																		name: row.applicant_document_item,
																		item_label: row.item_label,
																		item_key: row.item_key,
																	})
																"
															>
																Approve
															</button>
															<button
																type="button"
																class="if-action"
																:disabled="submissionSubmitting"
																@click="
																	beginSubmissionDecision(
																		{
																			name: row.applicant_document_item,
																			item_label: row.item_label,
																			item_key: row.item_key,
																		},
																		'Needs Follow-Up'
																	)
																"
															>
																Request Changes
															</button>
															<button
																type="button"
																class="if-action"
																:disabled="submissionSubmitting"
																@click="
																	beginSubmissionDecision(
																		{
																			name: row.applicant_document_item,
																			item_label: row.item_label,
																			item_key: row.item_key,
																		},
																		'Rejected'
																	)
																"
															>
																Reject
															</button>
														</div>
													</div>

													<div
														v-if="isEditingSubmission({ name: row.applicant_document_item })"
														class="mt-3 rounded-xl border border-slate-200 bg-white p-3"
													>
														<label class="block space-y-1">
															<span class="type-caption text-ink/70">
																Review note
																<span v-if="submissionRequiresNotes"> (required)</span>
															</span>
															<textarea
																v-model="submissionDecisionNotes"
																class="if-field"
																rows="3"
																:disabled="submissionSubmitting"
															></textarea>
														</label>
														<div class="mt-3 flex flex-wrap justify-end gap-2">
															<button
																type="button"
																class="if-button if-button--secondary"
																:disabled="submissionSubmitting"
																@click="cancelSubmissionDecision"
															>
																Cancel
															</button>
															<button
																type="button"
																class="if-button if-button--primary"
																:disabled="submissionSubmitting"
																@click="submitSubmissionDecision"
															>
																{{ submissionSubmitting ? 'Saving…' : 'Save Review' }}
															</button>
														</div>
													</div>
												</div>
											</div>
										</div>
									</article>

									<article class="interview-card">
										<div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
											<div>
												<h3 class="type-h3 text-ink">Recommendations</h3>
												<p class="mt-1 type-caption text-ink/65">
													Review referee context and approve the linked submission without leaving
													applicant workspace.
												</p>
											</div>
											<div class="flex flex-wrap gap-2">
												<span
													v-if="(workspaceRecommendations.summary.pending_review_count || 0) > 0"
													class="rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-xs font-semibold text-amber-900"
												>
													{{ workspaceRecommendations.summary.pending_review_count || 0 }}
													awaiting review
												</span>
												<button
													v-if="nextPendingRecommendationRow && recommendationReview"
													type="button"
													class="if-action"
													@click="openNextPendingRecommendation"
												>
													Next Pending
												</button>
											</div>
										</div>
										<div class="mt-3 grid gap-2 sm:grid-cols-4">
											<div class="rounded-xl bg-sky/20 px-3 py-2">
												<p class="type-caption text-ink/70">Required</p>
												<p class="type-body-strong text-ink">
													{{ workspaceRecommendations.summary.required_total || 0 }}
												</p>
											</div>
											<div class="rounded-xl bg-sky/20 px-3 py-2">
												<p class="type-caption text-ink/70">Received</p>
												<p class="type-body-strong text-ink">
													{{ workspaceRecommendations.summary.received_total || 0 }}
												</p>
											</div>
											<div class="rounded-xl bg-sky/20 px-3 py-2">
												<p class="type-caption text-ink/70">Requested</p>
												<p class="type-body-strong text-ink">
													{{ workspaceRecommendations.summary.requested_total || 0 }}
												</p>
											</div>
											<div class="rounded-xl bg-sky/20 px-3 py-2">
												<p class="type-caption text-ink/70">Pending Review</p>
												<p class="type-body-strong text-ink">
													{{ workspaceRecommendations.summary.pending_review_count || 0 }}
												</p>
											</div>
										</div>

										<div
											v-if="!recommendationReviewRows.length"
											class="mt-4 rounded-xl border border-dashed border-border/70 bg-slate-50/70 px-4 py-5 type-caption text-ink/60"
										>
											No submitted recommendations are available yet.
										</div>
										<div v-else class="mt-4 grid gap-4 xl:grid-cols-[0.92fr_1.08fr]">
											<div class="space-y-2">
												<button
													v-for="row in recommendationReviewRows"
													:key="
														row.recommendation_request ||
														row.recommendation_submission ||
														row.applicant_document_item
													"
													type="button"
													class="w-full rounded-2xl border px-4 py-3 text-left transition"
													:class="
														selectedRecommendationRow?.recommendation_request ===
														row.recommendation_request
															? 'border-canopy bg-canopy/5 shadow-sm'
															: 'border-border/70 bg-white hover:border-canopy/40 hover:bg-slate-50'
													"
													@click="openRecommendationReviewRow(row)"
												>
													<div class="flex items-start justify-between gap-3">
														<div class="min-w-0">
															<p class="type-body-strong text-ink truncate">
																{{ row.recommender_name || row.recommender_email || 'Referee' }}
															</p>
															<p class="mt-1 type-caption text-ink/65 truncate">
																{{
																	row.template_name ||
																	row.recommendation_template ||
																	'Recommendation'
																}}
																<span v-if="row.recommender_relationship">
																	· {{ row.recommender_relationship }}</span
																>
															</p>
														</div>
														<span
															class="rounded-full border px-2 py-0.5 text-xs font-semibold"
															:class="submissionStatusClass(row.review_status)"
														>
															{{ row.review_status || 'Pending' }}
														</span>
													</div>
													<p class="mt-2 type-caption text-ink/70">
														Submitted {{ formatHumanMoment(row.submitted_on) }}
													</p>
													<p class="mt-1 type-caption text-ink/60">
														Shared {{ formatHumanMoment(row.sent_on) }}
														<span v-if="row.opened_on">
															· Opened {{ formatHumanMoment(row.opened_on) }}</span
														>
													</p>
												</button>
											</div>

											<div class="rounded-2xl border border-border/70 bg-slate-50/60 p-4">
												<div v-if="recommendationReviewLoading" class="space-y-3">
													<div class="if-skel h-5 w-1/3" />
													<div class="if-skel h-16 w-full rounded-xl" />
													<div class="if-skel h-32 w-full rounded-xl" />
												</div>
												<div
													v-else-if="recommendationReviewError"
													class="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3"
												>
													<p class="type-body-strong text-rose-900">
														Unable to load recommendation
													</p>
													<p class="mt-1 type-caption text-rose-900/85">
														{{ recommendationReviewError }}
													</p>
												</div>
												<div v-else-if="recommendationReview" class="space-y-4">
													<div
														class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between"
													>
														<div class="min-w-0">
															<p class="type-overline text-ink/55">Recommendation Review</p>
															<h4 class="type-h3 text-ink">
																{{
																	recommendationReview.recommendation.recommender_name ||
																	recommendationReview.recommendation.recommender_email ||
																	'Referee'
																}}
															</h4>
															<p class="mt-1 type-caption text-ink/65">
																{{
																	recommendationReview.recommendation.template_name ||
																	recommendationReview.recommendation.recommendation_template ||
																	'Recommendation'
																}}
																<span
																	v-if="
																		recommendationReview.recommendation.recommender_relationship
																	"
																>
																	·
																	{{
																		recommendationReview.recommendation.recommender_relationship
																	}}
																</span>
															</p>
														</div>
														<span
															class="rounded-full border px-2 py-0.5 text-xs font-semibold"
															:class="
																submissionStatusClass(
																	recommendationReview.recommendation.review_status
																)
															"
														>
															{{ recommendationReview.recommendation.review_status || 'Pending' }}
														</span>
													</div>

													<div class="grid gap-3 sm:grid-cols-2">
														<div class="rounded-xl border border-border/70 bg-white px-3 py-2">
															<p class="type-caption text-ink/60">Shared</p>
															<p class="type-body text-ink">
																{{
																	formatHumanMoment(recommendationReview.recommendation.sent_on)
																}}
															</p>
														</div>
														<div class="rounded-xl border border-border/70 bg-white px-3 py-2">
															<p class="type-caption text-ink/60">Opened</p>
															<p class="type-body text-ink">
																{{
																	formatHumanMoment(recommendationReview.recommendation.opened_on)
																}}
															</p>
														</div>
														<div class="rounded-xl border border-border/70 bg-white px-3 py-2">
															<p class="type-caption text-ink/60">Submitted</p>
															<p class="type-body text-ink">
																{{
																	formatHumanMoment(
																		recommendationReview.recommendation.submitted_on
																	)
																}}
															</p>
														</div>
														<div class="rounded-xl border border-border/70 bg-white px-3 py-2">
															<p class="type-caption text-ink/60">Reviewed</p>
															<p class="type-body text-ink">
																{{
																	recommendationReview.recommendation.reviewed_on
																		? `${formatHumanMoment(
																				recommendationReview.recommendation.reviewed_on
																			)} · ${
																				recommendationReview.recommendation.reviewed_by || 'Staff'
																			}`
																		: 'Awaiting review'
																}}
															</p>
														</div>
													</div>

													<div class="rounded-xl border border-border/70 bg-white px-4 py-3">
														<div class="flex flex-wrap items-center gap-2">
															<span
																v-if="recommendationReview.recommendation.attestation_confirmed"
																class="rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-xs font-semibold text-emerald-900"
															>
																Attestation confirmed
															</span>
															<span
																v-if="recommendationReview.recommendation.item_label"
																class="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-xs font-semibold text-slate-700"
															>
																{{ recommendationReview.recommendation.item_label }}
															</span>
															<button
																v-if="recommendationReview.recommendation.file_url"
																type="button"
																class="text-sm font-medium text-canopy underline"
																@click="
																	openWorkspaceFile(
																		recommendationReview.recommendation.file_url,
																		recommendationReview.recommendation.file_name ||
																			'recommendation attachment'
																	)
																"
															>
																{{
																	recommendationReview.recommendation.file_name ||
																	'Open attached file'
																}}
															</button>
														</div>
														<p
															v-if="recommendationReview.recommendation.recommender_email"
															class="mt-2 type-caption text-ink/65"
														>
															{{ recommendationReview.recommendation.recommender_email }}
														</p>
													</div>

													<div>
														<h5 class="type-body-strong text-ink">Submission Answers</h5>
														<div
															v-if="!recommendationReview.recommendation.answers.length"
															class="mt-2 type-caption text-ink/60"
														>
															No structured answers were captured for this recommendation.
														</div>
														<div v-else class="mt-3 space-y-2">
															<div
																v-for="answer in recommendationReview.recommendation.answers"
																:key="answer.field_key"
																class="rounded-xl border border-border/70 bg-white px-4 py-3"
															>
																<p class="type-caption text-ink/60">
																	{{ answer.label }}
																</p>
																<p class="mt-1 type-body whitespace-pre-wrap text-ink">
																	{{
																		answer.display_value ||
																		(answer.has_value ? String(answer.value || '') : 'No response')
																	}}
																</p>
															</div>
														</div>
													</div>

													<div
														v-if="documentActionError"
														class="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 type-caption text-rose-900"
													>
														{{ documentActionError }}
													</div>
													<div
														v-if="documentActionNotice"
														class="rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 type-caption text-emerald-900"
													>
														{{ documentActionNotice }}
													</div>

													<div
														v-if="
															recommendationReviewItem &&
															canReviewRecommendationSubmissions &&
															recommendationReview.recommendation.can_review
														"
														class="rounded-xl border border-border/70 bg-white p-4"
													>
														<div
															v-if="isEditingSubmission(recommendationReviewItem)"
															class="space-y-3"
														>
															<label class="block space-y-1">
																<span class="type-caption text-ink/70">
																	Review note
																	<span v-if="submissionRequiresNotes"> (required)</span>
																</span>
																<textarea
																	v-model="submissionDecisionNotes"
																	class="if-field"
																	rows="3"
																	:disabled="submissionSubmitting"
																></textarea>
															</label>
															<div class="flex flex-wrap justify-end gap-2">
																<button
																	type="button"
																	class="if-button if-button--secondary"
																	:disabled="submissionSubmitting"
																	@click="cancelSubmissionDecision"
																>
																	Cancel
																</button>
																<button
																	type="button"
																	class="if-button if-button--primary"
																	:disabled="submissionSubmitting"
																	@click="submitSubmissionDecision"
																>
																	{{ submissionSubmitting ? 'Saving…' : 'Save Review' }}
																</button>
															</div>
														</div>
														<div v-else class="flex flex-wrap justify-end gap-2">
															<button
																type="button"
																class="if-action"
																:disabled="submissionSubmitting"
																@click="approveSubmission(recommendationReviewItem)"
															>
																Approve
															</button>
															<button
																type="button"
																class="if-action"
																:disabled="submissionSubmitting"
																@click="
																	beginSubmissionDecision(
																		recommendationReviewItem,
																		'Needs Follow-Up'
																	)
																"
															>
																Request Changes
															</button>
															<button
																type="button"
																class="if-action"
																:disabled="submissionSubmitting"
																@click="
																	beginSubmissionDecision(recommendationReviewItem, 'Rejected')
																"
															>
																Reject
															</button>
														</div>
													</div>
													<p v-else-if="recommendationReviewItem" class="type-caption text-ink/60">
														Evidence review actions are available from applicant workspace for
														admissions reviewers.
													</p>
												</div>
												<div
													v-else
													class="flex h-full min-h-56 items-center justify-center rounded-xl border border-dashed border-border/70 bg-white/70 px-4 py-5 text-center type-caption text-ink/60"
												>
													Select a submitted recommendation to review the full referee response.
												</div>
											</div>
										</div>
									</article>

									<article class="interview-card">
										<h3 class="type-h3 text-ink">Timeline Highlights</h3>
										<div v-if="!workspaceTimeline.length" class="mt-2 type-caption text-ink/60">
											No timeline entries yet.
										</div>
										<ul v-else class="mt-3 space-y-2 max-h-56 overflow-y-auto pr-1">
											<li
												v-for="row in timelineRows"
												:key="row.name"
												class="rounded-xl border border-border/60 px-3 py-2"
											>
												<p class="type-caption text-ink/65">
													{{ row.comment_by || row.comment_email || 'System' }} ·
													{{ formatHumanDateTime(row.creation) }}
												</p>
												<p class="type-body text-ink/80 mt-1" v-html="row.renderedContent"></p>
											</li>
										</ul>
									</article>
								</section>
							</div>
						</section>
					</DialogPanel>
				</TransitionChild>
			</div>
		</Dialog>
	</TransitionRoot>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue';
import {
	Dialog,
	DialogPanel,
	DialogTitle,
	TransitionChild,
	TransitionRoot,
} from '@headlessui/vue';
import { FeatherIcon } from 'frappe-ui';

import { useOverlayStack } from '@/composables/useOverlayStack';
import {
	getApplicantWorkspace,
	getInterviewWorkspace,
	getRecommendationReviewPayload,
	reviewApplicantDocumentSubmission,
	saveMyInterviewFeedback,
	setDocumentRequirementOverride,
} from '@/lib/services/admissions/admissionsWorkspaceService';
import type {
	ApplicantDocumentRequirementOverride,
	ApplicantDocumentReviewDecision,
	ApplicantWorkspaceDocumentItem,
	ApplicantWorkspaceDocumentReview,
	ApplicantWorkspaceRequirementRow,
	ApplicantWorkspaceUploadedRow,
	ApplicantWorkspaceResponse,
	InterviewWorkspaceInterview,
	InterviewWorkspaceGuardian,
	InterviewWorkspaceResponse,
	RecommendationReviewPayload,
	RecommendationReviewRow,
} from '@/types/contracts/admissions/admissions_workspace';

const props = defineProps<{
	open: boolean;
	zIndex?: number;
	interview?: string | null;
	schoolEvent?: string | null;
	mode?: 'interview' | 'applicant' | 'guardian' | null;
	studentApplicant?: string | null;
	guardian?: InterviewWorkspaceGuardian | null;
	applicantDisplayName?: string | null;
	documentType?: string | null;
	applicantDocument?: string | null;
	documentItem?: string | null;
	recommendationRequest?: string | null;
	recommendationSubmission?: string | null;
	applicantDocumentItem?: string | null;
}>();

type CloseReason = 'backdrop' | 'esc' | 'programmatic';

type WorkspaceMode = 'interview' | 'applicant' | 'guardian';
type GuardianDetailField = { label: string; value: string };

function emptyApplicantDocumentReview(): ApplicantWorkspaceDocumentReview {
	return {
		ok: false,
		missing: [],
		unapproved: [],
		required: [],
		required_rows: [],
		uploaded_rows: [],
		can_review_submissions: false,
		can_manage_overrides: false,
	};
}

const emit = defineEmits<{
	(e: 'close', reason: CloseReason): void;
	(e: 'after-leave'): void;
}>();

const overlay = useOverlayStack();
const overlayStyle = computed(() => ({ zIndex: props.zIndex ?? 70 }));
const closeBtnRef = ref<HTMLButtonElement | null>(null);
const bodyScrollRef = ref<HTMLElement | null>(null);

const loading = ref(false);
const submitting = ref(false);
const errorText = ref<string | null>(null);
const formError = ref<string | null>(null);
const saveNotice = ref<string | null>(null);
const recommendationReviewLoading = ref(false);
const recommendationReviewError = ref<string | null>(null);

const workspace = ref<InterviewWorkspaceResponse | null>(null);
const applicantWorkspace = ref<ApplicantWorkspaceResponse | null>(null);
const currentMode = ref<WorkspaceMode>('interview');
const activeInterviewName = ref('');
const recommendationReview = ref<RecommendationReviewPayload | null>(null);
const selectedRecommendationRequest = ref('');
const focusedRequirementAnchor = ref('');
const focusedSubmissionAnchor = ref('');

const formStrengths = ref('');
const formConcerns = ref('');
const formSharedValues = ref('');
const formOtherNotes = ref('');
const formRecommendation = ref('');
const documentActionError = ref<string | null>(null);
const documentActionNotice = ref<string | null>(null);
const submissionDecisionItem = ref<string | null>(null);
const submissionDecision = ref<ApplicantDocumentReviewDecision | null>(null);
const submissionDecisionNotes = ref('');
const submissionSubmitting = ref(false);
const requirementActionDocument = ref<string | null>(null);
const requirementActionType = ref<string | null>(null);
const requirementActionValue = ref<ApplicantDocumentRequirementOverride | null>(null);
const requirementActionLabel = ref('');
const requirementActionReason = ref('');
const requirementSubmitting = ref(false);

const recommendationOptions = [
	'Strongly Recommend',
	'Recommend',
	'Recommend with Conditions',
	'Do Not Recommend',
];

const workspaceApplicant = computed(
	() => workspace.value?.applicant || applicantWorkspace.value?.applicant || null
);
const workspaceTimeline = computed(
	() => workspace.value?.timeline || applicantWorkspace.value?.timeline || []
);
const workspaceDocuments = computed(() => workspace.value?.documents || { rows: [], count: 0 });
const applicantDocumentReview = computed(
	() => applicantWorkspace.value?.document_review || emptyApplicantDocumentReview()
);
const applicantRequirementRows = computed<ApplicantWorkspaceRequirementRow[]>(
	() => applicantDocumentReview.value.required_rows || []
);
const applicantUploadedRows = computed<ApplicantWorkspaceUploadedRow[]>(
	() => applicantDocumentReview.value.uploaded_rows || []
);
const workspaceRecommendations = computed(
	() =>
		(currentMode.value === 'applicant'
			? applicantWorkspace.value?.recommendations
			: applicantWorkspace.value?.recommendations || workspace.value?.recommendations) || {
			summary: {
				required_total: 0,
				received_total: 0,
				requested_total: 0,
				pending_review_count: 0,
			},
			requests: [],
			submissions: [],
			review_rows: [],
		}
);
const recommendationReviewRows = computed<RecommendationReviewRow[]>(
	() => workspaceRecommendations.value.review_rows || []
);
const workspaceInterviews = computed<InterviewWorkspaceInterview[]>(() => {
	if (applicantWorkspace.value?.interviews?.length) {
		return applicantWorkspace.value.interviews;
	}
	if (workspace.value?.interview?.name) {
		return [workspace.value.interview];
	}
	return [];
});
const supplementalDocumentNames = computed(() => {
	const names = new Set<string>();
	for (const row of applicantRequirementRows.value) {
		const name = String(row?.applicant_document || '').trim();
		if (name) {
			names.add(name);
		}
	}
	return names;
});
const applicantSupplementalUploads = computed<ApplicantWorkspaceUploadedRow[]>(() =>
	applicantUploadedRows.value.filter(row => {
		const applicantDocument = String(row?.applicant_document || '').trim();
		return !applicantDocument || !supplementalDocumentNames.value.has(applicantDocument);
	})
);
const missingRequirementCount = computed(() => applicantDocumentReview.value.missing.length);
const pendingSubmissionCount = computed(
	() =>
		applicantUploadedRows.value.filter(
			row => String(row?.review_status || 'Pending').trim() === 'Pending'
		).length
);
const completedRequirementCount = computed(
	() =>
		applicantRequirementRows.value.filter(row =>
			['Approved', 'Waived', 'Exception Approved'].includes(
				String(row?.review_status || '').trim()
			)
		).length
);
const canReviewApplicantSubmissions = computed(() =>
	Boolean(!isInterviewMode.value && applicantDocumentReview.value.can_review_submissions)
);
const canReviewRecommendationSubmissions = computed(() =>
	Boolean(applicantDocumentReview.value.can_review_submissions)
);
const canManageApplicantOverrides = computed(() =>
	Boolean(!isInterviewMode.value && applicantDocumentReview.value.can_manage_overrides)
);
const submissionRequiresNotes = computed(
	() => submissionDecision.value === 'Needs Follow-Up' || submissionDecision.value === 'Rejected'
);

const isInterviewMode = computed(() => currentMode.value === 'interview');
const isGuardianMode = computed(() => currentMode.value === 'guardian');
const selectedGuardian = computed<InterviewWorkspaceGuardian | null>(() =>
	isGuardianMode.value ? props.guardian || null : null
);
const hasWorkspace = computed(() =>
	isGuardianMode.value
		? Boolean(selectedGuardian.value)
		: Boolean(workspace.value || applicantWorkspace.value)
);
const showBackToApplicant = computed(
	() => isInterviewMode.value && Boolean(applicantWorkspace.value)
);

const applicantDisplayName = computed(() => {
	if (isGuardianMode.value) {
		return String(props.applicantDisplayName || '').trim();
	}
	return workspaceApplicant.value?.display_name || '';
});
const guardianProfileFields = computed<GuardianDetailField[]>(() => {
	const guardian = selectedGuardian.value;
	if (!guardian) return [];
	return [
		{ label: 'Full Name', value: displayValue(guardian.full_name) },
		{ label: 'First Name', value: displayValue(guardian.first_name) },
		{ label: 'Last Name', value: displayValue(guardian.last_name) },
		{ label: 'Relationship', value: displayValue(guardian.relationship) },
		{ label: 'Salutation', value: displayValue(guardian.salutation) },
		{ label: 'Gender', value: displayValue(guardian.gender) },
		{ label: 'Guardian Record', value: displayValue(guardian.guardian) },
		{ label: 'User ID', value: displayValue(guardian.user) },
	];
});
const guardianContactFields = computed<GuardianDetailField[]>(() => {
	const guardian = selectedGuardian.value;
	if (!guardian) return [];
	return [
		{ label: 'Personal Email', value: displayValue(guardian.email) },
		{ label: 'Mobile Phone', value: displayValue(guardian.mobile_phone) },
		{ label: 'Work Email', value: displayValue(guardian.work_email) },
		{ label: 'Work Phone', value: displayValue(guardian.work_phone) },
		{ label: 'Contact Record', value: displayValue(guardian.contact) },
		{ label: 'Use Applicant Contact', value: booleanValue(guardian.use_applicant_contact) },
		{ label: 'Authorized Signer', value: booleanValue(guardian.can_consent) },
		{ label: 'Is Primary', value: booleanValue(guardian.is_primary) },
	];
});
const guardianWorkFields = computed<GuardianDetailField[]>(() => {
	const guardian = selectedGuardian.value;
	if (!guardian) return [];
	return [
		{ label: 'Employment Sector', value: displayValue(guardian.employment_sector) },
		{ label: 'Work Place', value: displayValue(guardian.work_place) },
		{ label: 'Designation', value: displayValue(guardian.designation) },
		{ label: 'Is Primary Guardian', value: booleanValue(guardian.is_primary_guardian) },
		{ label: 'Is Financial Guardian', value: booleanValue(guardian.is_financial_guardian) },
	];
});
const selectedRecommendationRow = computed<RecommendationReviewRow | null>(() => {
	const requestName = String(
		recommendationReview.value?.recommendation?.recommendation_request ||
			selectedRecommendationRequest.value ||
			''
	).trim();
	if (!requestName) {
		return null;
	}
	return (
		recommendationReviewRows.value.find(
			row => String(row?.recommendation_request || '').trim() === requestName
		) || null
	);
});
const recommendationReviewItem = computed<ApplicantWorkspaceDocumentItem | null>(() => {
	const recommendation = recommendationReview.value?.recommendation;
	const itemName = String(recommendation?.applicant_document_item || '').trim();
	if (!itemName) {
		return null;
	}
	return {
		name: itemName,
		item_label: recommendation?.item_label || recommendation?.file_name || 'Recommendation',
		item_key: recommendation?.item_key || null,
		review_status: recommendation?.review_status || null,
		reviewed_by: recommendation?.reviewed_by || null,
		reviewed_on: recommendation?.reviewed_on || null,
		file_name: recommendation?.file_name || null,
		file_url: recommendation?.file_url || null,
	};
});
const nextPendingRecommendationRow = computed<RecommendationReviewRow | null>(() => {
	const activeRequest = String(
		recommendationReview.value?.recommendation?.recommendation_request ||
			selectedRecommendationRequest.value ||
			''
	).trim();
	return (
		recommendationReviewRows.value.find(row => {
			const requestName = String(row?.recommendation_request || '').trim();
			return Boolean(row?.needs_review) && requestName && requestName !== activeRequest;
		}) || null
	);
});

const workspaceOverline = computed(() => {
	if (isGuardianMode.value) return 'Admission Guardian Workspace';
	return isInterviewMode.value ? 'Admission Interview Workspace' : 'Admission Applicant Workspace';
});

const interviewWindowLabel = computed(() => {
	if (isGuardianMode.value) {
		return 'Guardian intake details captured from the applicant admission form';
	}
	if (!isInterviewMode.value) {
		return 'Applicant evidence, readiness, and interview summary';
	}
	const startLabel = formatHumanDateTime(workspace.value?.interview?.interview_start, {
		fallback: '',
	});
	const endLabel = formatHumanDateTime(workspace.value?.interview?.interview_end, {
		fallback: '',
	});
	if (startLabel && endLabel) return `${startLabel} to ${endLabel}`;
	if (startLabel) return startLabel;
	const dateOnlyLabel = formatHumanDate(workspace.value?.interview?.interview_date, {
		fallback: '',
	});
	if (dateOnlyLabel) return dateOnlyLabel;
	return 'Interview schedule';
});

const canEdit = computed(() =>
	Boolean(isInterviewMode.value && workspace.value?.feedback?.can_edit)
);
const timelineRows = computed(() =>
	workspaceTimeline.value.map(row => ({
		...row,
		renderedContent: formatTimelineContent(row.content),
	}))
);

function emitAfterLeave() {
	emit('after-leave');
}

function emitClose(reason: CloseReason = 'programmatic') {
	emit('close', reason);
}

function onDialogClose(payload: unknown) {
	void payload;
}

function displayValue(value: unknown, fallback = '—') {
	const resolved = String(value ?? '').trim();
	return resolved || fallback;
}

function booleanValue(value: unknown) {
	return Boolean(value) ? 'Yes' : 'No';
}

function clearRuntimeMessages() {
	formError.value = null;
	saveNotice.value = null;
}

function resetApplicantActionState() {
	documentActionError.value = null;
	documentActionNotice.value = null;
	submissionSubmitting.value = false;
	requirementSubmitting.value = false;
	submissionDecisionItem.value = null;
	submissionDecision.value = null;
	submissionDecisionNotes.value = '';
	requirementActionDocument.value = null;
	requirementActionType.value = null;
	requirementActionValue.value = null;
	requirementActionLabel.value = '';
	requirementActionReason.value = '';
	clearRecommendationReviewState();
}

function clearRecommendationReviewState() {
	recommendationReviewLoading.value = false;
	recommendationReviewError.value = null;
	recommendationReview.value = null;
	selectedRecommendationRequest.value = '';
}

function resolveRequestedDocumentRequirementAnchor() {
	const applicantDocument = String(props.applicantDocument || '').trim();
	const documentType = String(props.documentType || '').trim();
	if (!applicantDocument && !documentType) {
		return null;
	}
	return {
		applicant_document: applicantDocument || null,
		document_type: documentType || null,
	};
}

function resolveRequestedDocumentItemAnchor() {
	const applicantDocumentItem = String(props.documentItem || '').trim();
	if (!applicantDocumentItem) {
		return null;
	}
	return { applicant_document_item: applicantDocumentItem };
}

function requirementAnchorId(row: ApplicantWorkspaceRequirementRow) {
	const applicantDocument = String(row?.applicant_document || '').trim();
	if (applicantDocument) {
		return `admissions-requirement-${applicantDocument}`;
	}
	const documentType = String(row?.document_type || '').trim();
	if (documentType) {
		return `admissions-requirement-type-${documentType}`;
	}
	return '';
}

function submissionAnchorId(itemName: string | null | undefined) {
	const normalizedItem = String(itemName || '').trim();
	return normalizedItem ? `admissions-submission-${normalizedItem}` : '';
}

function isFocusedRequirement(row: ApplicantWorkspaceRequirementRow) {
	const anchorId = requirementAnchorId(row);
	return Boolean(anchorId && anchorId === focusedRequirementAnchor.value);
}

function isFocusedSubmission(itemName: string | null | undefined) {
	const anchorId = submissionAnchorId(itemName);
	return Boolean(anchorId && anchorId === focusedSubmissionAnchor.value);
}

async function scrollAnchorIntoView(anchorId: string) {
	const normalizedAnchor = String(anchorId || '').trim();
	if (!normalizedAnchor) {
		return;
	}

	await nextTick();
	const anchor = document.getElementById(normalizedAnchor);
	if (!anchor || (bodyScrollRef.value && !bodyScrollRef.value.contains(anchor))) {
		return;
	}

	anchor.scrollIntoView({
		behavior: 'smooth',
		block: 'center',
		inline: 'nearest',
	});
}

async function syncRequestedDocumentAnchor() {
	if (currentMode.value !== 'applicant' || !applicantWorkspace.value) {
		focusedRequirementAnchor.value = '';
		focusedSubmissionAnchor.value = '';
		return;
	}

	const requestedItem = resolveRequestedDocumentItemAnchor();
	if (requestedItem) {
		const itemName = requestedItem.applicant_document_item;
		const submissionAnchor = submissionAnchorId(itemName);
		const parentRequirement =
			applicantRequirementRows.value.find(row =>
				(row.items || []).some(item => String(item?.name || '').trim() === itemName)
			) || null;

		focusedSubmissionAnchor.value = submissionAnchor;
		focusedRequirementAnchor.value = parentRequirement
			? requirementAnchorId(parentRequirement)
			: '';
		await scrollAnchorIntoView(submissionAnchor || focusedRequirementAnchor.value);
		return;
	}

	const requestedRequirement = resolveRequestedDocumentRequirementAnchor();
	if (!requestedRequirement) {
		focusedRequirementAnchor.value = '';
		focusedSubmissionAnchor.value = '';
		return;
	}

	const matchedRequirement =
		applicantRequirementRows.value.find(row => {
			const applicantDocument = String(row?.applicant_document || '').trim();
			const documentType = String(row?.document_type || '').trim();
			return (
				(Boolean(requestedRequirement.applicant_document) &&
					applicantDocument === requestedRequirement.applicant_document) ||
				(Boolean(requestedRequirement.document_type) &&
					documentType === requestedRequirement.document_type)
			);
		}) || null;

	focusedSubmissionAnchor.value = '';
	focusedRequirementAnchor.value = matchedRequirement
		? requirementAnchorId(matchedRequirement)
		: '';
	await scrollAnchorIntoView(focusedRequirementAnchor.value);
}

function applyApplicantDocumentReview(documentReview: ApplicantWorkspaceDocumentReview) {
	if (!applicantWorkspace.value) {
		return;
	}
	applicantWorkspace.value.document_review = documentReview;
}

function resetFormFromWorkspace() {
	formError.value = null;
	saveNotice.value = null;
	formStrengths.value = workspace.value?.feedback?.my_feedback?.strengths || '';
	formConcerns.value = workspace.value?.feedback?.my_feedback?.concerns || '';
	formSharedValues.value = workspace.value?.feedback?.my_feedback?.shared_values || '';
	formOtherNotes.value = workspace.value?.feedback?.my_feedback?.other_notes || '';
	formRecommendation.value = workspace.value?.feedback?.my_feedback?.recommendation || '';
}

function resolveRequestedRecommendationAnchor() {
	const recommendationRequest = String(props.recommendationRequest || '').trim();
	if (recommendationRequest) {
		return { recommendation_request: recommendationRequest };
	}
	const recommendationSubmission = String(props.recommendationSubmission || '').trim();
	if (recommendationSubmission) {
		return { recommendation_submission: recommendationSubmission };
	}
	const applicantDocumentItem = String(props.applicantDocumentItem || '').trim();
	if (applicantDocumentItem) {
		return { applicant_document_item: applicantDocumentItem };
	}
	return null;
}

function normalizeRecommendationReviewAnchor(anchor: {
	recommendation_request?: string | null;
	recommendation_submission?: string | null;
	applicant_document_item?: string | null;
}) {
	const recommendationRequest = String(anchor.recommendation_request || '').trim();
	if (recommendationRequest) {
		return { recommendation_request: recommendationRequest };
	}
	const recommendationSubmission = String(anchor.recommendation_submission || '').trim();
	if (recommendationSubmission) {
		return { recommendation_submission: recommendationSubmission };
	}
	const applicantDocumentItem = String(anchor.applicant_document_item || '').trim();
	if (applicantDocumentItem) {
		return { applicant_document_item: applicantDocumentItem };
	}
	return null;
}

async function openRecommendationReview(anchor: {
	recommendation_request?: string | null;
	recommendation_submission?: string | null;
	applicant_document_item?: string | null;
}) {
	const studentApplicant = String(workspaceApplicant.value?.name || '').trim();
	if (!studentApplicant) {
		recommendationReviewError.value = 'Applicant reference is missing for recommendation review.';
		return;
	}

	const normalizedAnchor = normalizeRecommendationReviewAnchor(anchor);
	if (!normalizedAnchor) {
		recommendationReviewError.value = 'Recommendation reference is missing.';
		return;
	}

	recommendationReviewLoading.value = true;
	recommendationReviewError.value = null;
	documentActionError.value = null;
	try {
		recommendationReview.value = await getRecommendationReviewPayload({
			student_applicant: studentApplicant,
			recommendation_request: normalizedAnchor.recommendation_request || null,
			recommendation_submission: normalizedAnchor.recommendation_submission || null,
			applicant_document_item: normalizedAnchor.applicant_document_item || null,
		});
		selectedRecommendationRequest.value =
			String(recommendationReview.value.recommendation.recommendation_request || '').trim() ||
			String(normalizedAnchor.recommendation_request || '').trim();
	} catch (err) {
		recommendationReview.value = null;
		recommendationReviewError.value =
			err instanceof Error ? err.message : 'Unable to load recommendation details.';
	} finally {
		recommendationReviewLoading.value = false;
	}
}

async function openRecommendationReviewRow(row: RecommendationReviewRow | null | undefined) {
	const recommendationRequest = String(row?.recommendation_request || '').trim();
	const recommendationSubmission = String(row?.recommendation_submission || '').trim();
	const applicantDocumentItem = String(row?.applicant_document_item || '').trim();
	if (!recommendationRequest && !recommendationSubmission && !applicantDocumentItem) {
		recommendationReviewError.value = 'Recommendation reference is missing.';
		return;
	}
	await openRecommendationReview({
		recommendation_request: recommendationRequest || null,
		recommendation_submission: recommendationSubmission || null,
		applicant_document_item: applicantDocumentItem || null,
	});
}

async function syncRequestedRecommendationReview() {
	const requestedAnchor = resolveRequestedRecommendationAnchor();
	if (!requestedAnchor) {
		return;
	}
	await openRecommendationReview(requestedAnchor);
}

async function refreshApplicantWorkspaceContext(
	options: { syncRecommendationReview?: boolean } = {}
) {
	const studentApplicant = String(workspaceApplicant.value?.name || '').trim();
	if (!studentApplicant) {
		return;
	}

	try {
		applicantWorkspace.value = await getApplicantWorkspace(studentApplicant);
		await syncRequestedDocumentAnchor();
		if (options.syncRecommendationReview && recommendationReview.value?.recommendation) {
			await openRecommendationReview({
				recommendation_request:
					recommendationReview.value.recommendation.recommendation_request || null,
			});
		}
	} catch (err) {
		documentActionError.value =
			err instanceof Error ? err.message : 'Unable to refresh applicant workspace.';
	}
}

async function openNextPendingRecommendation() {
	if (!nextPendingRecommendationRow.value) {
		return;
	}
	await openRecommendationReviewRow(nextPendingRecommendationRow.value);
}

async function loadInterviewWorkspace(
	interviewName: string,
	options: { preserveApplicantContext?: boolean } = {}
) {
	const normalizedInterview = String(interviewName || '').trim();
	if (!normalizedInterview) {
		errorText.value = 'Interview reference is missing from this request.';
		workspace.value = null;
		return;
	}

	loading.value = true;
	errorText.value = null;
	clearRuntimeMessages();
	resetApplicantActionState();
	if (!options.preserveApplicantContext) {
		applicantWorkspace.value = null;
	}

	try {
		workspace.value = await getInterviewWorkspace(normalizedInterview);
		currentMode.value = 'interview';
		activeInterviewName.value = workspace.value.interview.name;
		resetFormFromWorkspace();
		await syncRequestedDocumentAnchor();
		await syncRequestedRecommendationReview();
	} catch (err) {
		const message = err instanceof Error ? err.message : 'Failed to load interview workspace.';
		workspace.value = null;
		if (options.preserveApplicantContext && applicantWorkspace.value) {
			formError.value = message;
		} else {
			errorText.value = message;
		}
	} finally {
		loading.value = false;
	}
}

async function loadApplicantWorkspace(studentApplicantName: string) {
	const normalizedApplicant = String(studentApplicantName || '').trim();
	if (!normalizedApplicant) {
		errorText.value = 'Applicant reference is missing from this cockpit action.';
		workspace.value = null;
		applicantWorkspace.value = null;
		return;
	}

	loading.value = true;
	errorText.value = null;
	clearRuntimeMessages();
	resetApplicantActionState();
	workspace.value = null;

	try {
		applicantWorkspace.value = await getApplicantWorkspace(normalizedApplicant);
		currentMode.value = 'applicant';
		activeInterviewName.value = '';
		resetFormFromWorkspace();
		await syncRequestedDocumentAnchor();
		await syncRequestedRecommendationReview();
	} catch (err) {
		applicantWorkspace.value = null;
		errorText.value = err instanceof Error ? err.message : 'Failed to load applicant workspace.';
	} finally {
		loading.value = false;
	}
}

function loadGuardianWorkspace() {
	loading.value = false;
	errorText.value = null;
	clearRuntimeMessages();
	resetApplicantActionState();
	workspace.value = null;
	applicantWorkspace.value = null;
	currentMode.value = 'guardian';
	activeInterviewName.value = '';

	if (!selectedGuardian.value) {
		errorText.value = 'Guardian details are missing from this admissions workspace action.';
	}
}

function resolveRequestedMode(): WorkspaceMode {
	const requested = String(props.mode || '')
		.trim()
		.toLowerCase();
	if (requested === 'guardian') return 'guardian';
	if (requested === 'applicant') return 'applicant';
	if (requested === 'interview') return 'interview';
	return String(props.interview || '').trim() ? 'interview' : 'applicant';
}

async function loadWorkspace() {
	const mode = resolveRequestedMode();
	if (mode === 'guardian') {
		loadGuardianWorkspace();
		return;
	}

	if (mode === 'applicant') {
		const applicantName = String(props.studentApplicant || '').trim();
		if (applicantName) {
			await loadApplicantWorkspace(applicantName);
			return;
		}

		const fallbackInterview = String(props.interview || '').trim();
		if (fallbackInterview) {
			await loadInterviewWorkspace(fallbackInterview, { preserveApplicantContext: false });
			return;
		}

		errorText.value = 'Applicant reference is missing from this cockpit action.';
		workspace.value = null;
		applicantWorkspace.value = null;
		return;
	}

	const interviewName = String(props.interview || '').trim();
	if (interviewName) {
		await loadInterviewWorkspace(interviewName, { preserveApplicantContext: false });
		return;
	}

	const fallbackApplicant = String(props.studentApplicant || '').trim();
	if (fallbackApplicant) {
		await loadApplicantWorkspace(fallbackApplicant);
		return;
	}

	errorText.value = 'Interview reference is missing from this calendar event.';
	workspace.value = null;
	applicantWorkspace.value = null;
}

function returnToApplicantMode() {
	if (!applicantWorkspace.value) {
		return;
	}
	workspace.value = null;
	currentMode.value = 'applicant';
	activeInterviewName.value = '';
	clearRuntimeMessages();
	resetApplicantActionState();
	resetFormFromWorkspace();
	void syncRequestedDocumentAnchor();
}

function isActiveInterview(interviewName: string | null | undefined) {
	return isInterviewMode.value && activeInterviewName.value === String(interviewName || '').trim();
}

async function openInterview(interviewName: string | null | undefined) {
	const normalizedInterview = String(interviewName || '').trim();
	if (!normalizedInterview) {
		formError.value = 'Interview reference is missing.';
		return;
	}
	await loadInterviewWorkspace(normalizedInterview, { preserveApplicantContext: true });
}

function openGuardianDetails(guardian: InterviewWorkspaceGuardian | null | undefined) {
	const studentApplicant =
		getApplicantWorkspaceName() || String(props.studentApplicant || '').trim();
	if (!guardian || (!guardian.full_name && !guardian.guardian && !guardian.email)) {
		documentActionError.value = 'Guardian details are not available for this applicant.';
		return;
	}

	documentActionError.value = null;
	overlay.open('admissions-workspace', {
		mode: 'guardian',
		studentApplicant: studentApplicant || null,
		applicantDisplayName: applicantDisplayName.value || null,
		guardian: { ...guardian },
	});
}

function openWorkspaceFile(fileUrl: string | null | undefined, label?: string | null) {
	const target = String(fileUrl || '').trim();
	if (!target) {
		documentActionError.value = `${displayValue(label, 'File')} is not available yet.`;
		return;
	}

	documentActionError.value = null;
	recommendationReviewError.value = null;
	const opened = window.open(target, '_blank', 'noopener,noreferrer');
	if (!opened) {
		window.location.assign(target);
	}
}

function newClientRequestId(prefix = 'admissions_workspace') {
	return `${prefix}_${Date.now()}_${Math.random().toString(16).slice(2, 12)}`;
}

function getApplicantWorkspaceName() {
	return String(workspaceApplicant.value?.name || '').trim();
}

function isEditingSubmission(item: ApplicantWorkspaceDocumentItem) {
	return Boolean(
		submissionDecisionItem.value &&
		submissionDecisionItem.value === String(item?.name || '').trim() &&
		submissionDecision.value
	);
}

function beginSubmissionDecision(
	item: ApplicantWorkspaceDocumentItem,
	decision: ApplicantDocumentReviewDecision
) {
	const itemName = String(item?.name || '').trim();
	if (!itemName) {
		documentActionError.value = 'Submitted file reference is missing.';
		return;
	}
	documentActionError.value = null;
	documentActionNotice.value = null;
	cancelRequirementOverride();
	submissionDecisionItem.value = itemName;
	submissionDecision.value = decision;
	submissionDecisionNotes.value = '';
}

function cancelSubmissionDecision() {
	submissionDecisionItem.value = null;
	submissionDecision.value = null;
	submissionDecisionNotes.value = '';
}

async function approveSubmission(item: ApplicantWorkspaceDocumentItem) {
	beginSubmissionDecision(item, 'Approved');
	await submitSubmissionDecision();
}

async function submitSubmissionDecision() {
	const studentApplicant = getApplicantWorkspaceName();
	const applicantDocumentItem = String(submissionDecisionItem.value || '').trim();
	const decision = submissionDecision.value;
	if (!studentApplicant || !applicantDocumentItem || !decision) {
		documentActionError.value = 'Submitted file reference is missing.';
		return;
	}
	if (submissionRequiresNotes.value && !submissionDecisionNotes.value.trim()) {
		documentActionError.value = 'A review note is required for this decision.';
		return;
	}

	documentActionError.value = null;
	documentActionNotice.value = null;
	submissionSubmitting.value = true;
	try {
		const result = await reviewApplicantDocumentSubmission({
			student_applicant: studentApplicant,
			applicant_document_item: applicantDocumentItem,
			decision,
			notes: submissionDecisionNotes.value.trim() || null,
			client_request_id: newClientRequestId('applicant_document_review'),
		});
		applyApplicantDocumentReview(result.documents);
		if (!isInterviewMode.value || applicantWorkspace.value) {
			await refreshApplicantWorkspaceContext({ syncRecommendationReview: true });
		}
		cancelSubmissionDecision();
		documentActionNotice.value =
			decision === 'Approved' ? 'Submitted file approved.' : 'Submitted file review updated.';
	} catch (err) {
		documentActionError.value =
			err instanceof Error ? err.message : 'Unable to update submitted file review.';
	} finally {
		submissionSubmitting.value = false;
	}
}

function isEditingRequirement(row: ApplicantWorkspaceRequirementRow) {
	const applicantDocument = String(row?.applicant_document || '').trim();
	const documentType = String(row?.document_type || '').trim();
	return Boolean(
		requirementActionValue.value &&
		requirementActionDocument.value === applicantDocument &&
		requirementActionType.value === documentType
	);
}

function beginRequirementOverride(
	row: ApplicantWorkspaceRequirementRow,
	overrideValue: ApplicantDocumentRequirementOverride
) {
	documentActionError.value = null;
	documentActionNotice.value = null;
	cancelSubmissionDecision();
	requirementActionDocument.value = String(row?.applicant_document || '').trim() || null;
	requirementActionType.value = String(row?.document_type || '').trim() || null;
	requirementActionValue.value = overrideValue;
	requirementActionLabel.value = String(row?.label || row?.document_type || 'Requirement').trim();
	requirementActionReason.value = '';
}

function cancelRequirementOverride() {
	requirementActionDocument.value = null;
	requirementActionType.value = null;
	requirementActionValue.value = null;
	requirementActionLabel.value = '';
	requirementActionReason.value = '';
}

async function submitRequirementOverride() {
	const studentApplicant = getApplicantWorkspaceName();
	if (!studentApplicant || !requirementActionValue.value) {
		documentActionError.value = 'Requirement reference is missing.';
		return;
	}
	if (!requirementActionReason.value.trim()) {
		documentActionError.value = 'A reason is required for waivers and exceptions.';
		return;
	}

	documentActionError.value = null;
	documentActionNotice.value = null;
	requirementSubmitting.value = true;
	try {
		const result = await setDocumentRequirementOverride({
			student_applicant: studentApplicant,
			applicant_document: requirementActionDocument.value,
			document_type: requirementActionType.value,
			requirement_override: requirementActionValue.value,
			override_reason: requirementActionReason.value.trim(),
			client_request_id: newClientRequestId('document_requirement_override'),
		});
		applyApplicantDocumentReview(result.documents);
		await refreshApplicantWorkspaceContext({ syncRecommendationReview: true });
		documentActionNotice.value = `${requirementActionValue.value} recorded.`;
		cancelRequirementOverride();
	} catch (err) {
		documentActionError.value =
			err instanceof Error ? err.message : 'Unable to update requirement override.';
	} finally {
		requirementSubmitting.value = false;
	}
}

async function clearRequirementOverride(row: ApplicantWorkspaceRequirementRow) {
	const studentApplicant = getApplicantWorkspaceName();
	const label = String(row?.label || row?.document_type || 'requirement').trim();
	if (!studentApplicant) {
		documentActionError.value = 'Requirement reference is missing.';
		return;
	}
	if (!window.confirm(`Clear the override for ${label}?`)) {
		return;
	}

	documentActionError.value = null;
	documentActionNotice.value = null;
	cancelSubmissionDecision();
	requirementSubmitting.value = true;
	try {
		const result = await setDocumentRequirementOverride({
			student_applicant: studentApplicant,
			applicant_document: String(row?.applicant_document || '').trim() || null,
			document_type: String(row?.document_type || '').trim() || null,
			requirement_override: '',
			override_reason: '',
			client_request_id: newClientRequestId('document_requirement_override_clear'),
		});
		applyApplicantDocumentReview(result.documents);
		await refreshApplicantWorkspaceContext({ syncRecommendationReview: true });
		documentActionNotice.value = 'Requirement override cleared.';
		cancelRequirementOverride();
	} catch (err) {
		documentActionError.value =
			err instanceof Error ? err.message : 'Unable to clear requirement override.';
	} finally {
		requirementSubmitting.value = false;
	}
}

function hasAnyFeedbackContent() {
	return Boolean(
		formStrengths.value.trim() ||
		formConcerns.value.trim() ||
		formSharedValues.value.trim() ||
		formOtherNotes.value.trim() ||
		formRecommendation.value.trim()
	);
}

async function persistFeedback(status: 'Draft' | 'Submitted') {
	if (!workspace.value || !isInterviewMode.value) {
		formError.value = 'Open an interview before saving notes.';
		return;
	}
	formError.value = null;
	saveNotice.value = null;

	if (!canEdit.value) {
		formError.value = 'You are not allowed to add notes for this interview.';
		return;
	}

	if (status === 'Submitted' && !hasAnyFeedbackContent()) {
		formError.value = 'Add at least one note before submitting.';
		return;
	}

	submitting.value = true;
	try {
		const result = await saveMyInterviewFeedback({
			interview: workspace.value.interview.name,
			strengths: formStrengths.value,
			concerns: formConcerns.value,
			shared_values: formSharedValues.value,
			other_notes: formOtherNotes.value,
			recommendation: formRecommendation.value,
			feedback_status: status,
		});

		if (workspace.value) {
			workspace.value.feedback = result.feedback;
		}
		resetFormFromWorkspace();
		saveNotice.value = status === 'Submitted' ? 'Notes submitted.' : 'Notes saved.';
	} catch (err) {
		formError.value = err instanceof Error ? err.message : 'Failed to save notes.';
	} finally {
		submitting.value = false;
	}
}

async function saveDraft() {
	await persistFeedback('Draft');
}

async function submitFeedback() {
	await persistFeedback('Submitted');
}

type HumanDateOptions = {
	includeYear?: boolean;
	includeWeekday?: boolean;
	includeOrdinalDay?: boolean;
	includeTime?: boolean;
	fallback?: string;
};

const TIMELINE_DATETIME_PATTERN =
	/\b\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(?::\d{2}(?:\.\d{1,6})?)?(?:Z|[+-]\d{2}:\d{2})?\b/g;

function resolveAppLocale() {
	if (typeof window === 'undefined') return undefined;
	const globalAny = window as unknown as Record<string, any>;
	const bootLang = String(globalAny.frappe?.boot?.lang || '').trim();
	if (bootLang) return bootLang.replace('_', '-');
	const htmlLang = document.documentElement.lang?.trim();
	if (htmlLang) return htmlLang.replace('_', '-');
	return navigator.languages?.[0] || navigator.language || undefined;
}

function resolveSiteTimeZone() {
	if (typeof window === 'undefined') return undefined;
	const globalAny = window as unknown as Record<string, any>;
	const siteTz = String(globalAny.frappe?.boot?.sysdefaults?.time_zone || '').trim();
	return siteTz || undefined;
}

function parseDateInput(value: string) {
	const raw = String(value || '').trim();
	if (!raw) return null;
	const normalized = raw.replace(' ', 'T').replace(/\.(\d{3})\d+/, '.$1');
	const parsed = new Date(normalized);
	if (!Number.isNaN(parsed.getTime())) return parsed;
	const fallback = new Date(raw);
	return Number.isNaN(fallback.getTime()) ? null : fallback;
}

function withEnglishOrdinalDay(dayText: string, locale?: string) {
	const normalizedLocale = String(locale || '').toLowerCase();
	if (!normalizedLocale.startsWith('en')) return dayText;
	const dayNumber = Number.parseInt(dayText, 10);
	if (!Number.isFinite(dayNumber)) return dayText;
	const mod100 = dayNumber % 100;
	if (mod100 >= 11 && mod100 <= 13) return `${dayNumber}th`;
	switch (dayNumber % 10) {
		case 1:
			return `${dayNumber}st`;
		case 2:
			return `${dayNumber}nd`;
		case 3:
			return `${dayNumber}rd`;
		default:
			return `${dayNumber}th`;
	}
}

function formatHumanDateTime(value?: string | null, options: HumanDateOptions = {}) {
	const {
		includeYear = false,
		includeWeekday = true,
		includeOrdinalDay = true,
		includeTime = true,
		fallback = '—',
	} = options;
	const raw = String(value || '').trim();
	if (!raw) return fallback;
	const parsed = parseDateInput(raw);
	if (!parsed) return raw;
	const locale = resolveAppLocale();
	const timeZone = resolveSiteTimeZone();
	try {
		const formatter = new Intl.DateTimeFormat(locale, {
			weekday: includeWeekday ? 'short' : undefined,
			day: 'numeric',
			month: 'long',
			year: includeYear ? 'numeric' : undefined,
			hour: includeTime ? '2-digit' : undefined,
			minute: includeTime ? '2-digit' : undefined,
			hour12: false,
			timeZone,
		});
		const parts = formatter.formatToParts(parsed);
		const partByType = new Map(parts.map(part => [part.type, part.value]));
		const dayPart = partByType.get('day') || '';
		const dayLabel =
			includeOrdinalDay && dayPart ? withEnglishOrdinalDay(dayPart, locale) : dayPart;
		const dateBits: string[] = [];
		if (includeWeekday && partByType.get('weekday'))
			dateBits.push(partByType.get('weekday') || '');
		if (dayLabel) dateBits.push(dayLabel);
		if (partByType.get('month')) dateBits.push(partByType.get('month') || '');
		if (includeYear && partByType.get('year')) dateBits.push(partByType.get('year') || '');
		const dateLabel = dateBits.join(' ').trim();
		if (!includeTime) return dateLabel || formatter.format(parsed);
		const hour = partByType.get('hour');
		const minute = partByType.get('minute');
		const timeLabel = hour && minute ? `${hour}:${minute}` : '';
		if (dateLabel && timeLabel) return `${dateLabel} ${timeLabel}`;
		if (dateLabel) return dateLabel;
		if (timeLabel) return timeLabel;
		return formatter.format(parsed);
	} catch {
		return raw;
	}
}

function formatHumanDate(
	value?: string | null,
	options: Omit<HumanDateOptions, 'includeTime'> = {}
) {
	return formatHumanDateTime(value, {
		includeTime: false,
		...options,
	});
}

function formatRelativeTime(value?: string | null) {
	const raw = String(value || '').trim();
	if (!raw) return '';
	const parsed = parseDateInput(raw);
	if (!parsed) return '';

	const diffSeconds = Math.round((parsed.getTime() - Date.now()) / 1000);
	const absoluteSeconds = Math.abs(diffSeconds);
	const formatter = new Intl.RelativeTimeFormat(resolveAppLocale(), { numeric: 'auto' });

	if (absoluteSeconds < 60) return formatter.format(diffSeconds, 'second');
	if (absoluteSeconds < 3600) return formatter.format(Math.round(diffSeconds / 60), 'minute');
	if (absoluteSeconds < 86400) return formatter.format(Math.round(diffSeconds / 3600), 'hour');
	if (absoluteSeconds < 604800) return formatter.format(Math.round(diffSeconds / 86400), 'day');
	if (absoluteSeconds < 2629800) return formatter.format(Math.round(diffSeconds / 604800), 'week');
	return formatter.format(Math.round(diffSeconds / 2629800), 'month');
}

function formatHumanMoment(value?: string | null, options: HumanDateOptions = {}) {
	const absolute = formatHumanDateTime(value, { includeYear: true, ...options });
	if (!value) return absolute;
	const relative = formatRelativeTime(value);
	return relative && relative !== absolute ? `${absolute} (${relative})` : absolute;
}

function formatTimelineContent(content?: string | null) {
	const raw = String(content || '');
	if (!raw) return '';
	return raw.replace(TIMELINE_DATETIME_PATTERN, match =>
		formatHumanDateTime(match, {
			fallback: match,
		})
	);
}

function formatInterviewStart(item: InterviewWorkspaceInterview) {
	return (
		formatHumanDateTime(item.interview_start, { fallback: '' }) ||
		formatHumanDate(item.interview_date, { fallback: '' }) ||
		'No date set'
	);
}

function formatInterviewEnd(item: InterviewWorkspaceInterview) {
	return formatHumanDateTime(item.interview_end, { fallback: '' });
}

function interviewFeedbackStatusLabel(item: InterviewWorkspaceInterview) {
	const explicit = String(item?.feedback_status_label || '').trim();
	if (explicit) {
		return explicit;
	}

	const interviewName = String(item?.name || '').trim();
	const activeInterview = String(workspace.value?.interview?.name || '').trim();
	if (!interviewName || interviewName !== activeInterview) {
		return '';
	}

	const panel = workspace.value?.feedback?.panel || [];
	if (!panel.length) {
		return '';
	}

	const expectedCount = panel.length;
	const submittedCount = panel.filter(member => member?.feedback_status === 'Submitted').length;
	return expectedCount > 0
		? `${submittedCount}/${expectedCount} submitted`
		: 'No interviewers assigned';
}

function interviewFeedbackComplete(item: InterviewWorkspaceInterview) {
	if (typeof item?.feedback_complete === 'boolean') {
		return item.feedback_complete;
	}

	const interviewName = String(item?.name || '').trim();
	const activeInterview = String(workspace.value?.interview?.name || '').trim();
	if (!interviewName || interviewName !== activeInterview) {
		return false;
	}

	const panel = workspace.value?.feedback?.panel || [];
	if (!panel.length) {
		return false;
	}

	return panel.every(member => member?.feedback_status === 'Submitted');
}

function requirementStatusClass(status?: string | null) {
	const normalized = String(status || '').trim();
	if (['Approved', 'Waived', 'Exception Approved'].includes(normalized)) {
		return 'border-emerald-200 bg-emerald-50 text-emerald-900';
	}
	if (normalized === 'Missing' || normalized === 'Rejected') {
		return 'border-rose-200 bg-rose-50 text-rose-900';
	}
	return 'border-amber-200 bg-amber-50 text-amber-900';
}

function submissionStatusClass(status?: string | null) {
	return requirementStatusClass(status);
}

function formatRequirementProgress(row: ApplicantWorkspaceRequirementRow) {
	const approvedCount = Number(row?.approved_count || 0);
	const requiredCount = Number(row?.required_count || 0);
	if (!requiredCount) {
		return 'Optional';
	}
	return `${approvedCount}/${requiredCount} approved`;
}

function formatRequirementMeta(row: ApplicantWorkspaceRequirementRow) {
	const bits: string[] = [];
	const uploadedCount = Number(row?.uploaded_count || 0);
	if (uploadedCount) {
		bits.push(`${uploadedCount} submitted`);
	}
	if (row?.uploaded_by) {
		bits.push(`last upload by ${row.uploaded_by}`);
	}
	if (row?.uploaded_at) {
		bits.push(`on ${formatHumanDateTime(row.uploaded_at, { includeYear: true })}`);
	}
	return bits.join(' · ') || 'No submitted files yet.';
}

function formatSubmissionMeta(
	item: ApplicantWorkspaceDocumentItem | ApplicantWorkspaceUploadedRow
) {
	const bits: string[] = [];
	if (item?.uploaded_by) {
		bits.push(`uploaded by ${item.uploaded_by}`);
	}
	if (item?.uploaded_at) {
		bits.push(`on ${formatHumanDateTime(item.uploaded_at, { includeYear: true })}`);
	}
	if (item?.reviewed_by) {
		bits.push(`reviewed by ${item.reviewed_by}`);
	}
	if (item?.reviewed_on) {
		bits.push(`on ${formatHumanDateTime(item.reviewed_on, { includeYear: true })}`);
	}
	return bits.join(' · ') || 'Awaiting review.';
}

function onKeydown(event: KeyboardEvent) {
	if (!props.open) return;
	if (event.key === 'Escape') emitClose('esc');
}

watch(
	() =>
		[
			props.open,
			props.interview,
			props.mode,
			props.studentApplicant,
			props.guardian,
			props.applicantDisplayName,
			props.documentType,
			props.applicantDocument,
			props.documentItem,
			props.recommendationRequest,
			props.recommendationSubmission,
			props.applicantDocumentItem,
		] as const,
	([isOpen]) => {
		if (!isOpen) return;
		void loadWorkspace();
	},
	{ immediate: true }
);

watch(
	() => props.open,
	isOpen => {
		if (isOpen) {
			document.addEventListener('keydown', onKeydown, true);
			return;
		}
		document.removeEventListener('keydown', onKeydown, true);
	},
	{ immediate: true }
);

onBeforeUnmount(() => {
	document.removeEventListener('keydown', onKeydown, true);
});
</script>

<style scoped>
.interview-workspace__panel {
	max-width: min(1220px, calc(100vw - 2rem));
	width: 100%;
}

.interview-workspace__header {
	border-bottom: 1px solid rgb(var(--border-rgb) / 0.8);
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: 0.75rem;
	padding-bottom: 1rem;
}

.interview-workspace__body {
	max-height: calc(100vh - 9rem);
	overflow: auto;
	padding-top: 1rem;
}

.interview-card {
	background: white;
	border: 1px solid rgb(var(--border-rgb) / 0.7);
	border-radius: 1rem;
	padding: 1rem;
	box-shadow: 0 8px 24px rgb(15 23 42 / 0.05);
}

.if-field {
	width: 100%;
	border-radius: 0.85rem;
	border: 1px solid rgb(var(--border-rgb) / 0.85);
	background: white;
	padding: 0.62rem 0.78rem;
	font-size: 0.95rem;
	outline: none;
}

.if-field:focus {
	box-shadow: 0 0 0 2px rgb(var(--leaf-rgb) / 0.25);
}

.if-field:disabled {
	background: rgb(var(--sand-rgb) / 0.3);
	cursor: not-allowed;
}
</style>
