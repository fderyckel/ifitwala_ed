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

						<section class="if-overlay__body interview-workspace__body px-6 pb-6">
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

							<div v-else-if="hasWorkspace" class="grid gap-5 xl:grid-cols-[1.2fr_1fr]">
								<section class="space-y-4">
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
												class="rounded-xl border border-border/60 bg-white px-3 py-2"
											>
												<p class="type-body-strong text-ink">
													{{ guardian.full_name || 'Guardian' }}
													<span class="text-ink/60">· {{ guardian.relationship || '—' }}</span>
												</p>
												<p class="type-caption text-ink/70 mt-1">
													{{ guardian.email || 'No personal email' }}
													<span v-if="guardian.mobile_phone"> · {{ guardian.mobile_phone }}</span>
												</p>
											</li>
										</ul>
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
														<a
															v-if="item.file_url"
															:href="item.file_url"
															target="_blank"
															rel="noreferrer"
															class="underline"
														>
															{{ item.item_label || item.file_name || 'View file' }}
														</a>
														<span v-else>{{
															item.item_label || item.item_key || 'Document item'
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
												class="rounded-2xl border border-border/70 bg-white p-4"
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
															class="if-action"
															:disabled="requirementSubmitting"
															@click="cancelRequirementOverride"
														>
															Cancel
														</button>
														<button
															type="button"
															class="if-action if-action--primary"
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
														class="rounded-xl border border-border/60 bg-slate-50/60 p-3"
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
																<a
																	v-if="item.file_url"
																	:href="item.file_url"
																	target="_blank"
																	rel="noreferrer"
																	class="mt-2 inline-flex text-sm font-medium text-canopy underline"
																>
																	{{ item.file_name || 'Open file' }}
																</a>
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
																	class="if-action"
																	:disabled="submissionSubmitting"
																	@click="cancelSubmissionDecision"
																>
																	Cancel
																</button>
																<button
																	type="button"
																	class="if-action if-action--primary"
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
													class="rounded-xl border border-border/60 bg-slate-50/60 p-3"
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
															<a
																v-if="row.file_url"
																:href="row.file_url"
																target="_blank"
																rel="noreferrer"
																class="mt-2 inline-flex text-sm font-medium text-canopy underline"
															>
																{{ row.file_name || 'Open file' }}
															</a>
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
																class="if-action"
																:disabled="submissionSubmitting"
																@click="cancelSubmissionDecision"
															>
																Cancel
															</button>
															<button
																type="button"
																class="if-action if-action--primary"
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
										<h3 class="type-h3 text-ink">Recommendations</h3>
										<div class="mt-3 grid gap-2 sm:grid-cols-3">
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

								<section class="space-y-4">
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
											<h3 class="type-h3 text-ink">Panel Feedback</h3>
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
											<h3 class="type-h3 text-ink">My Interview Feedback</h3>
											<p class="type-caption text-ink/65 mt-1">
												Separate notes per interviewer to avoid edit collisions.
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
													class="if-action"
													:disabled="!canEdit || submitting"
													@click="saveDraft"
												>
													{{ submitting ? 'Saving…' : 'Save Draft' }}
												</button>
												<button
													type="button"
													class="if-action if-action--primary"
													:disabled="!canEdit || submitting"
													@click="submitFeedback"
												>
													{{ submitting ? 'Submitting…' : 'Submit Feedback' }}
												</button>
											</div>
											<p v-if="!canEdit" class="type-caption text-ink/60 mt-3">
												You are not assigned to edit feedback for this interview.
											</p>
										</article>
									</template>

									<article v-else class="interview-card">
										<h3 class="type-h3 text-ink">Interview Notes</h3>
										<p class="type-caption text-ink/70 mt-2">
											Select an interview to view panel feedback and submit interviewer notes.
										</p>
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
import { computed, onBeforeUnmount, ref, watch } from 'vue';
import {
	Dialog,
	DialogPanel,
	DialogTitle,
	TransitionChild,
	TransitionRoot,
} from '@headlessui/vue';
import { FeatherIcon } from 'frappe-ui';

import {
	getApplicantWorkspace,
	getInterviewWorkspace,
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
	InterviewWorkspaceResponse,
} from '@/types/contracts/admissions/admissions_workspace';

const props = defineProps<{
	open: boolean;
	zIndex?: number;
	interview?: string | null;
	schoolEvent?: string | null;
	mode?: 'interview' | 'applicant' | null;
	studentApplicant?: string | null;
}>();

type CloseReason = 'backdrop' | 'esc' | 'programmatic';

type WorkspaceMode = 'interview' | 'applicant';

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

const overlayStyle = computed(() => ({ zIndex: props.zIndex ?? 70 }));
const closeBtnRef = ref<HTMLButtonElement | null>(null);

const loading = ref(false);
const submitting = ref(false);
const errorText = ref<string | null>(null);
const formError = ref<string | null>(null);
const saveNotice = ref<string | null>(null);

const workspace = ref<InterviewWorkspaceResponse | null>(null);
const applicantWorkspace = ref<ApplicantWorkspaceResponse | null>(null);
const currentMode = ref<WorkspaceMode>('interview');
const activeInterviewName = ref('');

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
		workspace.value?.recommendations ||
		applicantWorkspace.value?.recommendations || {
			summary: {
				required_total: 0,
				received_total: 0,
				requested_total: 0,
			},
			requests: [],
			submissions: [],
		}
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
const canManageApplicantOverrides = computed(() =>
	Boolean(!isInterviewMode.value && applicantDocumentReview.value.can_manage_overrides)
);
const submissionRequiresNotes = computed(
	() => submissionDecision.value === 'Needs Follow-Up' || submissionDecision.value === 'Rejected'
);

const hasWorkspace = computed(() => Boolean(workspace.value || applicantWorkspace.value));
const isInterviewMode = computed(() => currentMode.value === 'interview');
const showBackToApplicant = computed(
	() => isInterviewMode.value && Boolean(applicantWorkspace.value)
);

const applicantDisplayName = computed(() => workspaceApplicant.value?.display_name || '');

const workspaceOverline = computed(() =>
	isInterviewMode.value ? 'Admission Interview Workspace' : 'Admission Applicant Workspace'
);

const interviewWindowLabel = computed(() => {
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
	} catch (err) {
		applicantWorkspace.value = null;
		errorText.value = err instanceof Error ? err.message : 'Failed to load applicant workspace.';
	} finally {
		loading.value = false;
	}
}

function resolveRequestedMode(): WorkspaceMode {
	const requested = String(props.mode || '')
		.trim()
		.toLowerCase();
	if (requested === 'applicant') return 'applicant';
	if (requested === 'interview') return 'interview';
	return String(props.interview || '').trim() ? 'interview' : 'applicant';
}

async function loadWorkspace() {
	const mode = resolveRequestedMode();
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

function newClientRequestId(prefix = 'admissions_workspace') {
	return `${prefix}_${Date.now()}_${Math.random().toString(16).slice(2, 12)}`;
}

function getApplicantWorkspaceName() {
	return String(applicantWorkspace.value?.applicant?.name || '').trim();
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
		formError.value = 'Open an interview before saving feedback.';
		return;
	}
	formError.value = null;
	saveNotice.value = null;

	if (!canEdit.value) {
		formError.value = 'You are not allowed to edit feedback for this interview.';
		return;
	}

	if (status === 'Submitted' && !hasAnyFeedbackContent()) {
		formError.value = 'Add at least one feedback note before submitting.';
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
		saveNotice.value = status === 'Submitted' ? 'Feedback submitted.' : 'Draft saved.';
	} catch (err) {
		formError.value = err instanceof Error ? err.message : 'Failed to save feedback.';
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
	() => [props.open, props.interview, props.mode, props.studentApplicant] as const,
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
