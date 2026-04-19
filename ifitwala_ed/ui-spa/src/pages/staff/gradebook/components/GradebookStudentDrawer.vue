<template>
	<aside
		class="gradebook-drawer flex min-h-[520px] flex-col overflow-hidden rounded-2xl border border-border bg-white shadow-sm"
	>
		<div
			v-if="loading"
			class="flex min-h-[520px] flex-1 flex-col items-center justify-center gap-3 p-8"
		>
			<Spinner class="h-8 w-8 text-canopy" />
			<p class="text-sm text-ink/55">Loading grading drawer...</p>
		</div>

		<div
			v-else-if="errorMessage"
			class="m-6 rounded-2xl border border-flame/20 bg-flame/5 p-5 text-sm text-ink/70"
		>
			<p class="font-semibold text-ink">Drawer unavailable</p>
			<p class="mt-1">{{ errorMessage }}</p>
		</div>

		<div
			v-else-if="!drawer"
			class="flex min-h-[520px] flex-1 flex-col items-center justify-center gap-3 p-8 text-center"
		>
			<div class="rounded-full bg-gray-100 p-4">
				<FeatherIcon name="sidebar" class="h-8 w-8 text-ink/30" />
			</div>
			<p class="text-lg font-semibold text-ink">Open a student drawer</p>
			<p class="max-w-sm text-sm text-ink/55">
				Select one student from the roster to review evidence, adjust marking, inspect the official
				result, and manage release.
			</p>
		</div>

		<template v-else>
			<header class="border-b border-border/60 bg-gray-50/70 px-5 py-4">
				<div class="flex items-start justify-between gap-4">
					<div class="min-w-0 flex items-center gap-3">
						<img
							:src="drawer.student.student_image || DEFAULT_STUDENT_IMAGE"
							alt=""
							class="h-12 w-12 rounded-full border border-white bg-white object-cover shadow-sm"
							loading="lazy"
							@error="onImgError"
						/>
						<div class="min-w-0">
							<p class="text-xs font-semibold uppercase tracking-[0.16em] text-ink/45">
								Grading Drawer
							</p>
							<h2 class="truncate text-lg font-semibold text-ink">
								{{ drawer.student.student_name || 'Student' }}
							</h2>
							<p class="truncate text-sm text-ink/55">
								{{ drawer.delivery.title }}
								<span v-if="drawer.student.student_id"> · {{ drawer.student.student_id }}</span>
							</p>
						</div>
					</div>

					<div class="flex shrink-0 items-center gap-2">
						<div
							v-if="sequenceLabel"
							class="hidden rounded-full border border-border/70 bg-white px-3 py-1 text-xs font-medium text-ink/55 lg:inline-flex"
						>
							{{ sequenceLabel }}
						</div>
						<button
							v-if="showSequenceControls"
							type="button"
							class="inline-flex h-9 w-9 items-center justify-center rounded-full border border-border/70 bg-white text-ink/65 transition hover:border-border hover:text-ink disabled:cursor-not-allowed disabled:opacity-50"
							:disabled="!canGoPrevious"
							aria-label="Open previous student"
							@click="emit('go-previous')"
						>
							<FeatherIcon name="chevron-left" class="h-4 w-4" />
						</button>
						<button
							v-if="showSequenceControls"
							type="button"
							class="inline-flex h-9 w-9 items-center justify-center rounded-full border border-border/70 bg-white text-ink/65 transition hover:border-border hover:text-ink disabled:cursor-not-allowed disabled:opacity-50"
							:disabled="!canGoNext"
							aria-label="Open next student"
							@click="emit('go-next')"
						>
							<FeatherIcon name="chevron-right" class="h-4 w-4" />
						</button>
						<button
							type="button"
							class="inline-flex h-9 w-9 items-center justify-center rounded-full border border-border/70 bg-white text-ink/65 transition hover:border-border hover:text-ink"
							aria-label="Close grading drawer"
							@click="emit('close')"
						>
							<FeatherIcon name="x" class="h-4 w-4" />
						</button>
					</div>
				</div>

				<div class="mt-4 flex flex-wrap gap-2">
					<Badge v-if="drawer.delivery.due_date" variant="subtle">
						Due {{ formatDate(drawer.delivery.due_date) }}
					</Badge>
					<Badge v-if="taskModeBadge(drawer.delivery)" variant="subtle">
						{{ taskModeBadge(drawer.delivery) }}
					</Badge>
					<Badge
						v-if="drawer.outcome.has_new_submission"
						variant="subtle"
						theme="orange"
						class="!bg-sand/25 !text-clay"
					>
						New evidence
					</Badge>
					<Badge v-if="drawer.outcome.is_published" variant="subtle" theme="green">
						Released
					</Badge>
					<Badge v-if="drawer.my_contribution?.is_stale" variant="subtle" theme="orange">
						My marking is stale
					</Badge>
				</div>
			</header>

			<nav class="flex flex-wrap gap-2 border-b border-border/60 px-5 py-3">
				<button
					v-for="tab in visibleTabs"
					:key="tab.id"
					type="button"
					class="rounded-full px-3 py-1.5 text-sm font-medium transition"
					:class="
						currentTab === tab.id
							? 'bg-canopy text-white shadow-sm'
							: 'bg-gray-100 text-ink/65 hover:bg-gray-200 hover:text-ink'
					"
					@click="currentTab = tab.id"
				>
					{{ tab.label }}
				</button>
			</nav>

			<section class="flex-1 overflow-y-auto p-5">
				<div v-if="currentTab === 'marking'" class="space-y-5">
					<div class="grid gap-4 sm:grid-cols-2">
						<div class="rounded-2xl border border-border/70 bg-gray-50/40 p-4">
							<p class="text-xs font-semibold uppercase tracking-[0.16em] text-ink/45">
								Delivery Policy
							</p>
							<div class="mt-3 space-y-2 text-sm text-ink/70">
								<p>Mode: {{ drawer.delivery.delivery_mode || '—' }}</p>
								<p>Grading: {{ drawer.delivery.grading_mode || '—' }}</p>
								<p>
									Comments:
									{{ drawer.delivery.allow_feedback ? 'Enabled' : 'Disabled' }}
								</p>
								<p v-if="showMaxPointsPill(drawer.delivery)">
									Max points: {{ formatPoints(drawer.delivery.max_points) }}
								</p>
							</div>
						</div>

						<div class="rounded-2xl border border-border/70 bg-gray-50/40 p-4">
							<p class="text-xs font-semibold uppercase tracking-[0.16em] text-ink/45">
								My Current Context
							</p>
							<div class="mt-3 space-y-2 text-sm text-ink/70">
								<p>
									Contribution:
									{{ drawer.my_contribution?.status || 'No saved contribution yet' }}
								</p>
								<p>
									Outcome status:
									{{ drawer.outcome.grading_status || '—' }}
								</p>
								<p>
									Selected evidence:
									{{ selectedSubmissionLabel }}
								</p>
							</div>
						</div>
					</div>

					<div
						v-if="isViewingHistoricalSubmission"
						class="rounded-2xl border border-sand/70 bg-sand/20 p-4 text-sm text-clay"
					>
						<p class="font-semibold text-ink">Viewing an earlier evidence version</p>
						<p class="mt-1 text-clay/90">
							Save Marking still records against {{ latestSubmissionLabel }}. Use the Evidence tab
							to inspect history without changing the latest-version grading target.
						</p>
					</div>

					<div
						v-if="showsStatusControl(drawer.delivery) && !drawer.outcome.is_published"
						class="space-y-1.5"
					>
						<label class="block text-xs font-semibold uppercase tracking-[0.16em] text-ink/45">
							Outcome Status
						</label>
						<FormControl
							type="select"
							:options="statusOptions"
							option-label="label"
							option-value="value"
							:model-value="form.status"
							@update:modelValue="form.status = String($event || '')"
						/>
					</div>

					<div v-if="isPointsTask(drawer.delivery)" class="space-y-1.5">
						<label class="block text-xs font-semibold uppercase tracking-[0.16em] text-ink/45">
							Points Awarded
						</label>
						<FormControl
							type="number"
							placeholder="Points"
							:step="0.5"
							:min="0"
							:max="drawer.delivery.max_points || undefined"
							:model-value="form.mark_awarded"
							@update:modelValue="onPointsChanged"
						/>
					</div>

					<div v-if="showsBooleanResult(drawer.delivery)" class="space-y-2">
						<label class="block text-xs font-semibold uppercase tracking-[0.16em] text-ink/45">
							{{ booleanControlLabel(drawer.delivery) }}
						</label>
						<div class="grid grid-cols-2 gap-2">
							<button
								type="button"
								class="rounded-xl border px-4 py-2 text-sm font-medium transition"
								:class="
									form.complete
										? 'border-leaf bg-leaf text-white'
										: 'border-border/70 bg-white text-ink/70 hover:border-leaf/60 hover:text-leaf'
								"
								@click="form.complete = true"
							>
								{{ booleanPositiveLabel(drawer.delivery) }}
							</button>
							<button
								type="button"
								class="rounded-xl border px-4 py-2 text-sm font-medium transition"
								:class="
									!form.complete
										? 'border-slate-300 bg-slate-100 text-ink'
										: 'border-border/70 bg-white text-ink/70 hover:border-leaf/60 hover:text-leaf'
								"
								@click="form.complete = false"
							>
								{{ booleanNegativeLabel(drawer.delivery) }}
							</button>
						</div>
					</div>

					<div
						v-if="isCriteriaTask(drawer.delivery) && form.criteria.length"
						class="space-y-3 rounded-2xl border border-border/70 bg-white p-4"
					>
						<div class="flex items-center justify-between gap-3">
							<div>
								<h3 class="text-sm font-semibold text-ink">Criteria Breakdown</h3>
								<p class="text-xs text-ink/55">
									Criterion rows stay aligned to the delivery rubric.
								</p>
							</div>
							<Badge v-if="drawer.delivery.rubric_scoring_strategy" variant="subtle">
								{{ drawer.delivery.rubric_scoring_strategy }}
							</Badge>
						</div>

						<div class="grid gap-3">
							<div
								v-for="criterion in form.criteria"
								:key="criterion.assessment_criteria"
								class="rounded-2xl border border-border/70 bg-gray-50/40 p-4"
							>
								<div class="flex items-start justify-between gap-3">
									<div>
										<p class="text-sm font-semibold text-ink">
											{{ criterion.criteria_name }}
										</p>
										<p v-if="criterion.criteria_weighting !== null" class="text-xs text-ink/55">
											{{ criterion.criteria_weighting }}%
										</p>
									</div>
									<span class="text-sm font-semibold text-ink">
										{{ formatPoints(criterion.level_points) }}
									</span>
								</div>

								<div class="mt-3 grid gap-3 md:grid-cols-[minmax(0,1fr)_120px]">
									<FormControl
										type="select"
										:options="
											criterion.levels.map(level => ({ label: level.level, value: level.level }))
										"
										option-label="label"
										option-value="value"
										:model-value="criterion.level"
										placeholder="Select level"
										@update:modelValue="
											value => onCriterionLevelChanged(criterion.assessment_criteria, value)
										"
									/>
									<FormControl
										type="number"
										:model-value="criterion.level_points"
										:step="0.1"
										:min="0"
										placeholder="Points"
										@update:modelValue="
											value => onCriterionPointsChanged(criterion.assessment_criteria, value)
										"
									/>
								</div>

								<div v-if="supportsFeedback(drawer.delivery)" class="mt-3">
									<FormControl
										type="textarea"
										rows="2"
										placeholder="Criterion feedback"
										:model-value="criterion.feedback"
										@update:modelValue="
											value =>
												onCriterionFeedbackChanged(
													criterion.assessment_criteria,
													String(value || '')
												)
										"
									/>
								</div>
							</div>
						</div>
					</div>

					<div v-if="supportsFeedback(drawer.delivery)" class="space-y-1.5">
						<label class="block text-xs font-semibold uppercase tracking-[0.16em] text-ink/45">
							Comment
						</label>
						<FormControl
							type="textarea"
							rows="5"
							placeholder="Add a comment for this student..."
							:model-value="form.feedback"
							@update:modelValue="form.feedback = String($event || '')"
						/>
					</div>

					<div class="flex items-center justify-between gap-3 border-t border-border/60 pt-4">
						<p class="text-xs text-ink/45">
							Changes save through the current gradebook mutation pipeline and refresh this drawer
							from server truth.
						</p>
						<button
							type="button"
							class="if-button if-button--primary"
							:disabled="markingBusy || !isDirty || !drawer.allowed_actions.can_edit_marking"
							@click="emitSaveMarking"
						>
							{{ markingBusy ? 'Saving…' : 'Save Marking' }}
						</button>
					</div>
				</div>

				<div v-else-if="currentTab === 'evidence'" class="space-y-5">
					<div
						v-if="drawer.outcome.has_new_submission"
						class="rounded-2xl border border-sand/70 bg-sand/20 p-4 text-sm text-clay"
					>
						<div class="flex flex-wrap items-center justify-between gap-3">
							<div>
								<p class="font-semibold text-ink">New student evidence is waiting</p>
								<p class="mt-1 text-clay/90">
									Review the latest submission version before finalizing or releasing.
								</p>
							</div>
							<button
								v-if="drawer.allowed_actions.can_mark_submission_seen"
								type="button"
								class="if-button if-button--secondary"
								:disabled="submissionSeenBusy"
								@click="emit('mark-submission-seen')"
							>
								{{ submissionSeenBusy ? 'Marking…' : 'Mark as seen' }}
							</button>
						</div>
					</div>

					<div class="space-y-2">
						<div class="flex items-center justify-between gap-3">
							<h3 class="text-sm font-semibold text-ink">Submission Versions</h3>
							<p class="text-xs text-ink/45">Latest version opens by default.</p>
						</div>
						<div class="flex flex-wrap gap-2">
							<button
								v-for="version in drawer.submission_versions"
								:key="version.submission_id"
								type="button"
								class="rounded-full border px-3 py-1.5 text-sm transition"
								:class="
									version.is_selected
										? 'border-leaf bg-sky/20 text-ink'
										: 'border-border/70 bg-white text-ink/65 hover:border-leaf/40 hover:text-ink'
								"
								@click="emitVersion(version)"
							>
								Version {{ version.version }}
								<span v-if="version.is_stub"> · Stub</span>
							</button>
						</div>
					</div>

					<div
						v-if="!drawer.selected_submission"
						class="rounded-2xl border border-dashed border-border/70 bg-gray-50/40 p-6 text-sm text-ink/60"
					>
						<p class="font-semibold text-ink">No digital submission</p>
						<p class="mt-2">
							This outcome has no learner-uploaded evidence yet. If the delivery requires
							submission, the grading pipeline can still create an evidence stub for offline or
							observed work.
						</p>
					</div>

					<div v-else class="space-y-4">
						<div class="rounded-2xl border border-border/70 bg-gray-50/40 p-4">
							<div class="flex flex-wrap gap-2">
								<Badge variant="subtle"> Version {{ drawer.selected_submission.version }} </Badge>
								<Badge variant="subtle">
									{{ drawer.selected_submission.origin || 'Submission' }}
								</Badge>
								<Badge v-if="drawer.selected_submission.is_stub" variant="subtle">
									Evidence stub
								</Badge>
							</div>
							<div class="mt-3 grid gap-2 text-sm text-ink/70">
								<p>
									Submitted:
									{{ formatDateTime(drawer.selected_submission.submitted_on) || '—' }}
								</p>
								<p>
									Submitted by:
									{{ drawer.selected_submission.submitted_by || '—' }}
								</p>
								<p v-if="drawer.selected_submission.evidence_note">
									Note: {{ drawer.selected_submission.evidence_note }}
								</p>
							</div>
						</div>

						<div
							v-if="drawer.selected_submission.annotation_readiness"
							class="rounded-2xl border border-border/70 bg-white p-4"
						>
							<div class="flex flex-wrap items-start justify-between gap-3">
								<div class="min-w-0">
									<p class="text-xs font-semibold uppercase tracking-[0.16em] text-ink/45">
										Annotation Surface
									</p>
									<h3 class="mt-2 text-sm font-semibold text-ink">
										{{ drawer.selected_submission.annotation_readiness.title }}
									</h3>
									<p class="mt-2 text-sm text-ink/70">
										{{ drawer.selected_submission.annotation_readiness.message }}
									</p>
								</div>
								<div class="flex flex-wrap gap-2">
									<Badge variant="subtle">
										{{ annotationModeLabel(drawer.selected_submission.annotation_readiness) }}
									</Badge>
									<Badge
										v-if="drawer.selected_submission.annotation_readiness.preview_status"
										variant="subtle"
									>
										Preview
										{{ drawer.selected_submission.annotation_readiness.preview_status }}
									</Badge>
								</div>
							</div>
							<p
								v-if="drawer.selected_submission.annotation_readiness.attachment_file_name"
								class="mt-3 text-sm text-ink/60"
							>
								Source PDF:
								{{ drawer.selected_submission.annotation_readiness.attachment_file_name }}
							</p>
							<div class="mt-4 flex flex-wrap gap-2">
								<a
									v-if="drawer.selected_submission.annotation_readiness.preview_url"
									class="if-button if-button--secondary"
									:href="drawer.selected_submission.annotation_readiness.preview_url || undefined"
									target="_blank"
									rel="noreferrer"
								>
									{{
										annotationPreviewActionLabel(drawer.selected_submission.annotation_readiness)
									}}
								</a>
								<a
									v-if="drawer.selected_submission.annotation_readiness.open_url"
									class="if-button if-button--secondary"
									:href="drawer.selected_submission.annotation_readiness.open_url || undefined"
									target="_blank"
									rel="noreferrer"
								>
									Open source PDF
								</a>
							</div>
						</div>

						<div
							v-if="drawer.selected_submission.text_content"
							class="rounded-2xl border border-border/70 bg-white p-4"
						>
							<h3 class="text-sm font-semibold text-ink">Text Submission</h3>
							<pre class="mt-3 whitespace-pre-wrap text-sm text-ink/75">{{
								drawer.selected_submission.text_content
							}}</pre>
						</div>

						<div
							v-if="drawer.selected_submission.link_url"
							class="rounded-2xl border border-border/70 bg-white p-4"
						>
							<h3 class="text-sm font-semibold text-ink">Linked Evidence</h3>
							<a
								class="mt-3 inline-flex items-center gap-2 text-sm font-medium text-canopy underline-offset-2 hover:underline"
								:href="drawer.selected_submission.link_url || undefined"
								target="_blank"
								rel="noreferrer"
							>
								<FeatherIcon name="external-link" class="h-4 w-4" />
								Open linked evidence
							</a>
						</div>

						<div
							v-if="drawer.selected_submission.attachments.length"
							class="space-y-3 rounded-2xl border border-border/70 bg-white p-4"
						>
							<div class="flex items-center justify-between gap-3">
								<h3 class="text-sm font-semibold text-ink">Attachments</h3>
								<p class="text-xs text-ink/45">Server-owned preview and open actions only.</p>
							</div>

							<div class="grid gap-3">
								<div
									v-for="attachment in drawer.selected_submission.attachments"
									:key="attachment.row_name || attachment.file_name || attachment.open_url"
									class="rounded-2xl border border-border/70 bg-gray-50/40 p-4"
								>
									<GradebookPdfWorkspace
										v-if="isPdfAttachment(attachment)"
										:attachment="attachment"
										:annotation-readiness="annotationReadinessForAttachment(attachment)"
										:items="feedbackForm.items"
										:comment-bank="drawer.comment_bank"
										:criteria-options="feedbackCriteriaOptions"
										:comment-bank-busy="commentBankBusy"
										:disabled="!drawer.allowed_actions.can_edit_feedback"
										@update:items="onFeedbackItemsChanged"
										@save-comment-bank-entry="emitSaveCommentBankEntry"
									/>
									<AttachmentPreviewCard
										v-else-if="attachment.attachment_preview"
										:attachment="attachment.attachment_preview"
										variant="evidence"
										:title="
											attachment.attachment_preview.display_name ||
											attachment.file_name ||
											'Attachment'
										"
										:description="attachment.description || null"
									>
										<template #badges>
											<Badge variant="subtle">{{ attachment.kind }}</Badge>
											<Badge v-if="attachment.preview_status" variant="subtle">
												Preview {{ attachment.preview_status }}
											</Badge>
											<Badge v-if="attachment.file_size" variant="subtle">
												{{ formatBytes(attachment.file_size) }}
											</Badge>
										</template>
									</AttachmentPreviewCard>
								</div>
							</div>
						</div>

						<div
							v-if="drawer.selected_submission"
							class="rounded-2xl border border-border/70 bg-white p-4"
						>
							<div class="flex flex-wrap items-start justify-between gap-3">
								<div class="min-w-0">
									<p class="text-xs font-semibold uppercase tracking-[0.16em] text-ink/45">
										Feedback Draft
									</p>
									<h3 class="mt-2 text-sm font-semibold text-ink">
										Version-bound feedback workspace
									</h3>
									<p class="mt-2 text-sm text-ink/70">
										Summary and anchored comments bind to
										{{ selectedSubmissionLabel }} and stay separate from official grade truth.
									</p>
								</div>
								<div class="flex flex-wrap gap-2">
									<Badge variant="subtle">
										{{ feedbackForm.items.length }}
										{{ feedbackForm.items.length === 1 ? 'item' : 'items' }}
									</Badge>
									<Badge v-if="drawer.feedback_workspace?.modified" variant="subtle">
										Updated {{ formatDateTime(drawer.feedback_workspace.modified) }}
									</Badge>
								</div>
							</div>

							<div class="mt-4 grid gap-4 lg:grid-cols-2">
								<div class="space-y-1.5 lg:col-span-2">
									<label
										class="block text-xs font-semibold uppercase tracking-[0.16em] text-ink/45"
									>
										Overall Summary
									</label>
									<FormControl
										type="textarea"
										rows="3"
										placeholder="Summarize what matters most in this submission draft."
										:model-value="feedbackForm.summary.overall"
										@update:modelValue="feedbackForm.summary.overall = String($event || '')"
									/>
								</div>

								<div class="space-y-1.5">
									<label
										class="block text-xs font-semibold uppercase tracking-[0.16em] text-ink/45"
									>
										Strengths
									</label>
									<FormControl
										type="textarea"
										rows="3"
										placeholder="Capture the strongest evidence first."
										:model-value="feedbackForm.summary.strengths"
										@update:modelValue="feedbackForm.summary.strengths = String($event || '')"
									/>
								</div>

								<div class="space-y-1.5">
									<label
										class="block text-xs font-semibold uppercase tracking-[0.16em] text-ink/45"
									>
										Improvements
									</label>
									<FormControl
										type="textarea"
										rows="3"
										placeholder="Call out the main gaps to address."
										:model-value="feedbackForm.summary.improvements"
										@update:modelValue="feedbackForm.summary.improvements = String($event || '')"
									/>
								</div>

								<div class="space-y-1.5 lg:col-span-2">
									<label
										class="block text-xs font-semibold uppercase tracking-[0.16em] text-ink/45"
									>
										Next Steps
									</label>
									<FormControl
										type="textarea"
										rows="3"
										placeholder="State the next actions the student should take."
										:model-value="feedbackForm.summary.next_steps"
										@update:modelValue="feedbackForm.summary.next_steps = String($event || '')"
									/>
								</div>
							</div>

							<div
								class="mt-4 flex items-center justify-between gap-3 border-t border-border/60 pt-4"
							>
								<p class="text-xs text-ink/45">
									Save one bounded draft for this selected submission version after updating
									summary text or anchored comments.
								</p>
								<button
									type="button"
									class="if-button if-button--primary"
									:disabled="feedbackBusy || !feedbackDraftDirty || !canSaveFeedbackDraft"
									@click="emitSaveFeedbackDraft"
								>
									{{ feedbackBusy ? 'Saving…' : 'Save Feedback Draft' }}
								</button>
							</div>
						</div>
					</div>
				</div>

				<div v-else-if="currentTab === 'official'" class="space-y-5">
					<div class="grid gap-4 sm:grid-cols-2">
						<div class="rounded-2xl border border-border/70 bg-gray-50/40 p-4">
							<p class="text-xs font-semibold uppercase tracking-[0.16em] text-ink/45">
								Official Status
							</p>
							<div class="mt-3 space-y-2 text-sm text-ink/70">
								<p>Grading status: {{ drawer.outcome.grading_status || '—' }}</p>
								<p>Procedural status: {{ drawer.outcome.procedural_status || '—' }}</p>
								<p>Released: {{ drawer.outcome.is_published ? 'Yes' : 'No' }}</p>
								<p v-if="drawer.outcome.published_on">
									Released on: {{ formatDateTime(drawer.outcome.published_on) }}
								</p>
							</div>
						</div>

						<div class="rounded-2xl border border-border/70 bg-gray-50/40 p-4">
							<p class="text-xs font-semibold uppercase tracking-[0.16em] text-ink/45">
								Official Result
							</p>
							<div class="mt-3 space-y-2 text-sm text-ink/70">
								<p>Score: {{ formatPoints(drawer.outcome.official.score) }}</p>
								<p>Grade: {{ drawer.outcome.official.grade || '—' }}</p>
								<p>
									Grade value:
									{{ formatPoints(drawer.outcome.official.grade_value) }}
								</p>
							</div>
						</div>
					</div>

					<div
						v-if="drawer.outcome.official.feedback"
						class="rounded-2xl border border-border/70 bg-white p-4"
					>
						<h3 class="text-sm font-semibold text-ink">Official Feedback</h3>
						<p class="mt-3 whitespace-pre-wrap text-sm text-ink/75">
							{{ normalizeFeedback(drawer.outcome.official.feedback) }}
						</p>
					</div>

					<div
						v-if="drawer.outcome.criteria.length"
						class="space-y-3 rounded-2xl border border-border/70 bg-white p-4"
					>
						<h3 class="text-sm font-semibold text-ink">Official Criteria</h3>
						<div class="grid gap-3">
							<div
								v-for="criterion in drawer.outcome.criteria"
								:key="criterion.criteria"
								class="flex items-center justify-between rounded-2xl border border-border/70 bg-gray-50/40 px-4 py-3"
							>
								<div>
									<p class="text-sm font-semibold text-ink">{{ criterion.criteria }}</p>
									<p class="text-xs text-ink/55">{{ criterion.level || '—' }}</p>
								</div>
								<span class="text-sm font-semibold text-ink">
									{{ formatPoints(criterion.points) }}
								</span>
							</div>
						</div>
					</div>

					<div
						v-if="showPublicationSection"
						class="rounded-2xl border border-border/70 bg-white p-4"
					>
						<div class="flex flex-wrap items-start justify-between gap-3">
							<div>
								<h3 class="text-sm font-semibold text-ink">Assessment Publication Channels</h3>
								<p class="mt-1 text-sm text-ink/60">
									These explicit feedback and grade visibility states are stored per selected
									submission version.
									<span v-if="publicationContextMissing">
										Select a submission version to change them.
									</span>
									Current student/guardian portals still follow the legacy outcome release path
									until the feedback navigator lands.
								</p>
							</div>
							<Badge
								v-if="drawer.feedback_workspace?.publication.derived_from_legacy_outcome"
								variant="subtle"
							>
								Derived from legacy release
							</Badge>
						</div>

						<div class="mt-4 grid gap-4 md:grid-cols-2">
							<div class="space-y-1.5">
								<label class="block text-xs font-semibold uppercase tracking-[0.16em] text-ink/45">
									Feedback Visibility
								</label>
								<FormControl
									type="select"
									:options="publicationOptions"
									option-label="label"
									option-value="value"
									:model-value="feedbackForm.publication.feedback_visibility"
									:disabled="publicationControlsDisabled"
									@update:modelValue="onPublicationVisibilityChanged('feedback', $event)"
								/>
							</div>

							<div class="space-y-1.5">
								<label class="block text-xs font-semibold uppercase tracking-[0.16em] text-ink/45">
									Grade Visibility
								</label>
								<FormControl
									type="select"
									:options="publicationOptions"
									option-label="label"
									option-value="value"
									:model-value="feedbackForm.publication.grade_visibility"
									:disabled="publicationControlsDisabled"
									@update:modelValue="onPublicationVisibilityChanged('grade', $event)"
								/>
							</div>
						</div>

						<div
							class="mt-4 flex items-center justify-between gap-3 border-t border-border/60 pt-4"
						>
							<p class="text-xs text-ink/45">
								Stored channel state is audit-friendly and separate from the current one-bit
								outcome release.
							</p>
							<button
								type="button"
								class="if-button if-button--secondary"
								:disabled="publicationBusy || !publicationDirty || !canSaveFeedbackPublication"
								@click="emitSaveFeedbackPublication"
							>
								{{ publicationBusy ? 'Saving…' : 'Save Publication State' }}
							</button>
						</div>
					</div>

					<div class="rounded-2xl border border-border/70 bg-white p-4">
						<div class="flex flex-wrap items-center justify-between gap-3">
							<div>
								<h3 class="text-sm font-semibold text-ink">Release</h3>
								<p class="mt-1 text-sm text-ink/60">
									Current runtime still uses one published state on the outcome.
								</p>
							</div>
							<button
								v-if="drawer.outcome.is_published"
								type="button"
								class="if-button if-button--secondary"
								:disabled="publishBusy || !drawer.allowed_actions.can_unpublish"
								@click="emit('unpublish')"
							>
								{{ publishBusy ? 'Updating…' : 'Unrelease' }}
							</button>
							<button
								v-else
								type="button"
								class="if-button if-button--primary"
								:disabled="publishBusy || !drawer.allowed_actions.can_publish"
								@click="emit('publish')"
							>
								{{ publishBusy ? 'Updating…' : 'Release' }}
							</button>
						</div>
					</div>
				</div>

				<div v-else-if="currentTab === 'compare'" class="space-y-3">
					<div
						v-if="!drawer.contributions.length"
						class="rounded-2xl border border-dashed border-border/70 bg-gray-50/40 p-6 text-sm text-ink/60"
					>
						No contribution history yet.
					</div>
					<div
						v-for="row in drawer.contributions"
						:key="row.name"
						class="rounded-2xl border border-border/70 bg-white p-4"
					>
						<div class="flex flex-wrap items-start justify-between gap-3">
							<div>
								<p class="text-sm font-semibold text-ink">
									{{ row.contributor || row.contribution_type }}
								</p>
								<p class="mt-1 text-xs text-ink/55">
									{{ row.contribution_type }} · {{ row.status }}
									<span v-if="row.moderation_action"> · {{ row.moderation_action }}</span>
								</p>
							</div>
							<div class="flex flex-wrap gap-2">
								<Badge v-if="Boolean(row.is_stale)" variant="subtle" theme="orange"> Stale </Badge>
								<Badge v-if="row.task_submission" variant="subtle">
									{{ submissionLabel(row.task_submission) }}
								</Badge>
							</div>
						</div>
						<div class="mt-3 grid gap-2 text-sm text-ink/70 sm:grid-cols-3">
							<p>Score: {{ formatPoints(row.score) }}</p>
							<p>Grade: {{ row.grade || '—' }}</p>
							<p>Saved: {{ formatDateTime(row.submitted_on || row.modified) || '—' }}</p>
						</div>
						<p v-if="row.feedback" class="mt-3 whitespace-pre-wrap text-sm text-ink/75">
							{{ normalizeFeedback(row.feedback) }}
						</p>
					</div>
				</div>

				<div v-else-if="currentTab === 'review'" class="space-y-3">
					<div
						v-if="drawer.allowed_actions.can_moderate"
						class="rounded-2xl border border-border/70 bg-white p-4"
					>
						<div class="flex flex-wrap items-start justify-between gap-3">
							<div>
								<h3 class="text-sm font-semibold text-ink">Moderation Actions</h3>
								<p class="mt-1 text-sm text-ink/60">
									Approve or Adjust applies the current My Marking values as the moderated outcome.
									Return to Grader leaves official truth unchanged and sends the outcome back to In
									Progress.
								</p>
								<p v-if="isViewingHistoricalSubmission" class="mt-2 text-sm text-clay">
									You are reviewing {{ selectedSubmissionLabel }}. Moderation actions still target
									{{ latestSubmissionLabel }}.
								</p>
							</div>
							<div class="flex flex-wrap gap-2">
								<button
									type="button"
									class="if-button if-button--secondary"
									:disabled="moderationBusy"
									@click="emitModeratorAction('Approve')"
								>
									{{ moderationBusy ? 'Updating…' : 'Approve' }}
								</button>
								<button
									type="button"
									class="if-button if-button--secondary"
									:disabled="moderationBusy"
									@click="emitModeratorAction('Adjust')"
								>
									{{ moderationBusy ? 'Updating…' : 'Adjust' }}
								</button>
								<button
									type="button"
									class="if-button if-button--primary"
									:disabled="moderationBusy"
									@click="emitModeratorAction('Return to Grader')"
								>
									{{ moderationBusy ? 'Updating…' : 'Return to Grader' }}
								</button>
							</div>
						</div>
					</div>

					<div
						v-if="!drawer.moderation_history.length"
						class="rounded-2xl border border-dashed border-border/70 bg-gray-50/40 p-6 text-sm text-ink/60"
					>
						No moderation actions have been recorded for this outcome.
					</div>
					<div
						v-for="entry in drawer.moderation_history"
						:key="`${entry.by}-${entry.on}-${entry.action}`"
						class="rounded-2xl border border-border/70 bg-white p-4"
					>
						<p class="text-sm font-semibold text-ink">{{ entry.by }}</p>
						<p class="mt-1 text-sm text-ink/70">{{ entry.action || 'Moderation update' }}</p>
						<p class="mt-1 text-xs text-ink/55">
							{{ formatDateTime(entry.on) || '—' }}
						</p>
					</div>
				</div>
			</section>
		</template>
	</aside>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue';
import { Badge, FeatherIcon, FormControl, Spinner } from 'frappe-ui';

import AttachmentPreviewCard from '@/components/attachments/AttachmentPreviewCard.vue';
import type { CommentBankScopeMode } from '@/types/contracts/gradebook/comment_bank';
import type {
	FeedbackIntent,
	FeedbackVisibility,
	FeedbackWorkspaceItem,
} from '@/types/contracts/gradebook/feedback_workspace';
import type { Request as UpdateTaskStudentRequest } from '@/types/contracts/gradebook/update_task_student';
import type { Response as GetDrawerResponse } from '@/types/contracts/gradebook/get_drawer';
import GradebookPdfWorkspace from './GradebookPdfWorkspace.vue';
import {
	DEFAULT_STUDENT_IMAGE,
	booleanControlLabel,
	booleanNegativeLabel,
	booleanPositiveLabel,
	formatDate,
	formatDateTime,
	formatPoints,
	isCriteriaTask,
	isPointsTask,
	normalizeFeedback,
	showMaxPointsPill,
	showsBooleanResult,
	showsStatusControl,
	supportsFeedback,
	taskModeBadge,
} from '../gradebookUtils';

type DrawerTab = 'marking' | 'evidence' | 'official' | 'compare' | 'review';

type CriterionFormRow = {
	assessment_criteria: string;
	criteria_name: string;
	criteria_weighting: number | null;
	levels: Array<{ level: string; points: number }>;
	level: string | number | null;
	level_points: number | null;
	feedback: string;
};

type SubmissionAttachmentRow = NonNullable<
	NonNullable<GetDrawerResponse['selected_submission']>['attachments']
>[number];

type AnnotationReadinessPayload = NonNullable<
	NonNullable<GetDrawerResponse['selected_submission']>['annotation_readiness']
>;

const props = defineProps<{
	loading: boolean;
	drawer: GetDrawerResponse | null;
	errorMessage?: string | null;
	markingBusy?: boolean;
	feedbackBusy?: boolean;
	commentBankBusy?: boolean;
	publicationBusy?: boolean;
	submissionSeenBusy?: boolean;
	publishBusy?: boolean;
	moderationBusy?: boolean;
	showSequenceControls?: boolean;
	canGoPrevious?: boolean;
	canGoNext?: boolean;
	sequenceLabel?: string | null;
}>();

const emit = defineEmits<{
	(e: 'close'): void;
	(e: 'switch-version', payload: { submissionId?: string | null; version?: number | null }): void;
	(e: 'save-marking', payload: UpdateTaskStudentRequest['updates']): void;
	(
		e: 'save-feedback-draft',
		payload: {
			outcome_id: string;
			submission_id: string;
			summary: {
				overall: string;
				strengths: string;
				improvements: string;
				next_steps: string;
			};
			items: FeedbackWorkspaceItem[];
		}
	): void;
	(
		e: 'save-feedback-publication',
		payload: {
			outcome_id: string;
			submission_id: string;
			feedback_visibility: FeedbackVisibility;
			grade_visibility: FeedbackVisibility;
		}
	): void;
	(
		e: 'save-comment-bank-entry',
		payload: {
			outcome_id: string;
			body: string;
			feedback_intent: FeedbackIntent;
			assessment_criteria?: string | null;
			scope_mode: CommentBankScopeMode;
		}
	): void;
	(
		e: 'moderator-action',
		payload: {
			action: 'Approve' | 'Adjust' | 'Return to Grader';
			updates: UpdateTaskStudentRequest['updates'];
		}
	): void;
	(e: 'mark-submission-seen'): void;
	(e: 'publish'): void;
	(e: 'unpublish'): void;
	(e: 'go-previous'): void;
	(e: 'go-next'): void;
}>();

const statusOptions = [
	{ label: 'Not Started', value: 'Not Started' },
	{ label: 'In Progress', value: 'In Progress' },
	{ label: 'Needs Review', value: 'Needs Review' },
	{ label: 'Moderated', value: 'Moderated' },
	{ label: 'Finalized', value: 'Finalized' },
	{ label: 'Not Applicable', value: 'Not Applicable' },
];

const publicationOptions: Array<{ label: string; value: FeedbackVisibility }> = [
	{ label: 'Hidden', value: 'hidden' },
	{ label: 'Student only', value: 'student' },
	{ label: 'Student and guardian', value: 'student_and_guardian' },
];
const feedbackCriteriaOptions = computed(() =>
	(props.drawer?.delivery.criteria || []).map(row => ({
		label: row.criteria_name || row.assessment_criteria,
		value: row.assessment_criteria,
	}))
);

const currentTab = ref<DrawerTab>('marking');
const form = reactive({
	status: 'Not Started',
	mark_awarded: null as number | null,
	complete: false,
	feedback: '',
	criteria: [] as CriterionFormRow[],
});
const baseline = ref('');
const feedbackForm = reactive({
	summary: {
		overall: '',
		strengths: '',
		improvements: '',
		next_steps: '',
	},
	items: [] as FeedbackWorkspaceItem[],
	publication: {
		feedback_visibility: 'hidden' as FeedbackVisibility,
		grade_visibility: 'hidden' as FeedbackVisibility,
	},
});
const feedbackDraftBaseline = ref('');
const publicationBaseline = ref('');

const visibleTabs = computed(() => {
	const base = [
		{ id: 'marking' as DrawerTab, label: 'My Marking' },
		{ id: 'evidence' as DrawerTab, label: 'Evidence' },
		{ id: 'official' as DrawerTab, label: 'Official Result' },
		{ id: 'compare' as DrawerTab, label: 'Compare' },
	];
	if (props.drawer?.allowed_actions.show_review_tab) {
		base.push({ id: 'review' as DrawerTab, label: 'Review' });
	}
	return base;
});

const isDirty = computed(() => baseline.value !== serializeCurrentForm());
const feedbackDraftDirty = computed(
	() =>
		feedbackDraftBaseline.value !==
		JSON.stringify({
			summary: feedbackForm.summary,
			items: feedbackForm.items,
		})
);
const publicationDirty = computed(
	() =>
		publicationBaseline.value !==
		JSON.stringify({
			feedback_visibility: feedbackForm.publication.feedback_visibility,
			grade_visibility: feedbackForm.publication.grade_visibility,
		})
);
const canSaveFeedbackDraft = computed(
	() =>
		Boolean(props.drawer?.selected_submission?.submission_id) &&
		Boolean(props.drawer?.allowed_actions.can_edit_feedback)
);
const canSaveFeedbackPublication = computed(
	() =>
		Boolean(props.drawer?.selected_submission?.submission_id) &&
		Boolean(props.drawer?.allowed_actions.can_manage_feedback_publication)
);
const showPublicationSection = computed(
	() =>
		Boolean(props.drawer?.allowed_actions.can_manage_feedback_publication) ||
		Boolean(props.drawer?.feedback_workspace) ||
		Boolean(props.drawer?.selected_submission)
);
const publicationContextMissing = computed(
	() => !props.drawer?.selected_submission?.submission_id
);
const publicationControlsDisabled = computed(
	() =>
		Boolean(props.publicationBusy) ||
		publicationContextMissing.value ||
		!canSaveFeedbackPublication.value
);

const selectedSubmissionLabel = computed(() => {
	const row = props.drawer?.selected_submission;
	if (!row) return 'No digital submission';
	return `Version ${row.version}${row.is_stub ? ' (stub)' : ''}`;
});

const latestSubmissionLabel = computed(() => {
	const row = props.drawer?.latest_submission;
	if (!row) return 'the latest submission';
	return `Version ${row.version}${row.is_stub ? ' (stub)' : ''}`;
});

const isViewingHistoricalSubmission = computed(() => {
	const selected = props.drawer?.selected_submission;
	const latest = props.drawer?.latest_submission;
	if (!selected || !latest) return false;
	return selected.submission_id !== latest.submission_id;
});

watch(visibleTabs, tabs => {
	if (!tabs.find(tab => tab.id === currentTab.value)) {
		currentTab.value = tabs[0]?.id || 'marking';
	}
});

watch(
	() => props.drawer,
	value => {
		resetForm(value);
	},
	{ immediate: true }
);

function resetForm(drawer: GetDrawerResponse | null) {
	if (!drawer) {
		form.status = 'Not Started';
		form.mark_awarded = null;
		form.complete = false;
		form.feedback = '';
		form.criteria = [];
		baseline.value = serializeCurrentForm();
		return;
	}

	form.status = drawer.outcome.grading_status || 'Not Started';
	form.mark_awarded =
		typeof drawer.my_contribution?.score === 'number'
			? drawer.my_contribution.score
			: (drawer.outcome.official.score ?? null);
	form.complete = Boolean(drawer.outcome.is_complete);
	form.feedback = normalizeFeedback(
		drawer.my_contribution?.feedback || drawer.outcome.official.feedback || ''
	);
	form.criteria = buildCriterionFormRows(drawer);
	baseline.value = serializeCurrentForm();
	resetFeedbackForm(drawer);
}

function buildCriterionFormRows(drawer: GetDrawerResponse): CriterionFormRow[] {
	const myCriteriaMap = new Map(
		(drawer.my_contribution?.criteria || []).map(row => [row.criteria, row])
	);
	const officialCriteriaMap = new Map(drawer.outcome.criteria.map(row => [row.criteria, row]));
	const rows: CriterionFormRow[] = [];

	for (const criterion of drawer.delivery.criteria || []) {
		const my = myCriteriaMap.get(criterion.assessment_criteria);
		const official = officialCriteriaMap.get(criterion.assessment_criteria);
		rows.push({
			assessment_criteria: criterion.assessment_criteria,
			criteria_name: criterion.criteria_name,
			criteria_weighting: criterion.criteria_weighting,
			levels: criterion.levels || [],
			level: my?.level ?? official?.level ?? null,
			level_points:
				typeof my?.points === 'number'
					? my.points
					: typeof official?.points === 'number'
						? official.points
						: null,
			feedback: normalizeFeedback((my?.feedback as string | null) || ''),
		});
	}

	return rows;
}

function serializeCurrentForm() {
	return JSON.stringify({
		status: form.status,
		mark_awarded: form.mark_awarded,
		complete: form.complete,
		feedback: form.feedback,
		criteria: form.criteria.map(row => ({
			assessment_criteria: row.assessment_criteria,
			level: row.level,
			level_points: row.level_points,
			feedback: row.feedback,
		})),
	});
}

function resetFeedbackForm(drawer: GetDrawerResponse | null) {
	const workspace = drawer?.feedback_workspace;
	feedbackForm.summary.overall = workspace?.summary.overall || '';
	feedbackForm.summary.strengths = workspace?.summary.strengths || '';
	feedbackForm.summary.improvements = workspace?.summary.improvements || '';
	feedbackForm.summary.next_steps = workspace?.summary.next_steps || '';
	feedbackForm.items = cloneFeedbackItems(workspace?.items || []);
	feedbackForm.publication.feedback_visibility =
		workspace?.publication.feedback_visibility || 'hidden';
	feedbackForm.publication.grade_visibility = workspace?.publication.grade_visibility || 'hidden';
	feedbackDraftBaseline.value = JSON.stringify({
		summary: feedbackForm.summary,
		items: feedbackForm.items,
	});
	publicationBaseline.value = JSON.stringify({
		feedback_visibility: feedbackForm.publication.feedback_visibility,
		grade_visibility: feedbackForm.publication.grade_visibility,
	});
}

function cloneFeedbackItems(items: FeedbackWorkspaceItem[]): FeedbackWorkspaceItem[] {
	return items.map(item => ({
		...item,
		anchor: JSON.parse(JSON.stringify(item.anchor)),
	}));
}

function emitVersion(row: NonNullable<GetDrawerResponse['latest_submission']>) {
	emit('switch-version', {
		submissionId: row.submission_id,
		version: row.version,
	});
}

function emitSaveMarking() {
	emit('save-marking', buildMarkingPayload());
}

function emitSaveFeedbackDraft() {
	const outcomeId = props.drawer?.outcome.outcome_id;
	const submissionId = props.drawer?.selected_submission?.submission_id;
	if (!outcomeId || !submissionId) return;
	emit('save-feedback-draft', {
		outcome_id: outcomeId,
		submission_id: submissionId,
		summary: {
			overall: feedbackForm.summary.overall,
			strengths: feedbackForm.summary.strengths,
			improvements: feedbackForm.summary.improvements,
			next_steps: feedbackForm.summary.next_steps,
		},
		items: cloneFeedbackItems(feedbackForm.items),
	});
}

function emitSaveFeedbackPublication() {
	const outcomeId = props.drawer?.outcome.outcome_id;
	const submissionId = props.drawer?.selected_submission?.submission_id;
	if (!outcomeId || !submissionId) return;
	emit('save-feedback-publication', {
		outcome_id: outcomeId,
		submission_id: submissionId,
		feedback_visibility: feedbackForm.publication.feedback_visibility,
		grade_visibility: feedbackForm.publication.grade_visibility,
	});
}

function emitSaveCommentBankEntry(payload: {
	body: string;
	feedback_intent: FeedbackIntent;
	assessment_criteria?: string | null;
	scope_mode: CommentBankScopeMode;
}) {
	const outcomeId = props.drawer?.outcome.outcome_id;
	if (!outcomeId) return;
	emit('save-comment-bank-entry', {
		outcome_id: outcomeId,
		body: payload.body,
		feedback_intent: payload.feedback_intent,
		assessment_criteria: payload.assessment_criteria || null,
		scope_mode: payload.scope_mode,
	});
}

function normalizePublicationVisibility(value: unknown): FeedbackVisibility {
	const resolved = String(value || 'hidden').trim();
	if (resolved === 'student' || resolved === 'student_and_guardian' || resolved === 'hidden') {
		return resolved;
	}
	return 'hidden';
}

function onPublicationVisibilityChanged(channel: 'feedback' | 'grade', value: unknown) {
	if (channel === 'feedback') {
		feedbackForm.publication.feedback_visibility = normalizePublicationVisibility(value);
		return;
	}
	feedbackForm.publication.grade_visibility = normalizePublicationVisibility(value);
}

function buildMarkingPayload(): UpdateTaskStudentRequest['updates'] {
	const payload: UpdateTaskStudentRequest['updates'] = {};
	const delivery = props.drawer?.delivery;
	if (!delivery) return payload;

	if (showsStatusControl(delivery) && !props.drawer?.outcome.is_published) {
		payload.status = form.status || null;
	}
	if (isPointsTask(delivery)) {
		payload.mark_awarded = form.mark_awarded;
	}
	if (showsBooleanResult(delivery)) {
		payload.complete = form.complete;
	}
	if (supportsFeedback(delivery)) {
		payload.feedback = form.feedback;
	}
	if (isCriteriaTask(delivery)) {
		const criteriaScores = form.criteria
			.filter(row => row.level !== null && row.level !== '')
			.map(row => ({
				assessment_criteria: row.assessment_criteria,
				level: row.level,
				level_points: row.level_points,
				feedback: row.feedback || null,
			}));
		if (criteriaScores.length) {
			payload.criteria_scores = criteriaScores;
		}
	}
	return payload;
}

function emitModeratorAction(action: 'Approve' | 'Adjust' | 'Return to Grader') {
	emit('moderator-action', {
		action,
		updates: buildMarkingPayload(),
	});
}

function onPointsChanged(value: unknown) {
	if (value === null || value === undefined || value === '') {
		form.mark_awarded = null;
		return;
	}
	const parsed = Number(value);
	form.mark_awarded = Number.isFinite(parsed) ? parsed : null;
}

function onCriterionLevelChanged(criteriaName: string, levelValue: unknown) {
	const row = form.criteria.find(item => item.assessment_criteria === criteriaName);
	if (!row) return;
	row.level = levelValue === '' ? null : (levelValue as string | number | null);
	const levelDef = row.levels.find(level => level.level === row.level);
	if (levelDef) {
		row.level_points = levelDef.points;
	}
}

function onCriterionPointsChanged(criteriaName: string, value: unknown) {
	const row = form.criteria.find(item => item.assessment_criteria === criteriaName);
	if (!row) return;
	if (value === null || value === undefined || value === '') {
		row.level_points = null;
		return;
	}
	const parsed = Number(value);
	row.level_points = Number.isFinite(parsed) ? parsed : null;
}

function onCriterionFeedbackChanged(criteriaName: string, value: string) {
	const row = form.criteria.find(item => item.assessment_criteria === criteriaName);
	if (!row) return;
	row.feedback = value;
}

function submissionLabel(submissionId?: string | null) {
	const row = props.drawer?.submission_versions.find(
		entry => entry.submission_id === submissionId
	);
	if (!row) return 'Submission';
	return `Version ${row.version}${row.is_stub ? ' · Stub' : ''}`;
}

function formatBytes(value?: number | null) {
	if (!value) return '0 B';
	if (value < 1024) return `${value} B`;
	const kb = value / 1024;
	if (kb < 1024) return `${kb.toFixed(1)} KB`;
	return `${(kb / 1024).toFixed(1)} MB`;
}

function annotationReadinessForAttachment(
	attachment: SubmissionAttachmentRow
): AnnotationReadinessPayload | null {
	const readiness = props.drawer?.selected_submission?.annotation_readiness;
	if (!readiness) return null;
	if (readiness.attachment_row_name && attachment.row_name) {
		return readiness.attachment_row_name === attachment.row_name ? readiness : null;
	}
	if (readiness.attachment_file_name && attachment.file_name) {
		return readiness.attachment_file_name === attachment.file_name ? readiness : null;
	}
	return null;
}

function attachmentExtension(attachment: SubmissionAttachmentRow): string {
	const explicitExtension = String(attachment.extension || '')
		.trim()
		.toLowerCase();
	if (explicitExtension) return explicitExtension;
	const rawName = String(attachment.file_name || '').trim();
	const lastDot = rawName.lastIndexOf('.');
	if (!rawName || lastDot < 0 || lastDot === rawName.length - 1) {
		return '';
	}
	return rawName.slice(lastDot + 1).toLowerCase();
}

function isPdfAttachment(attachment: SubmissionAttachmentRow): boolean {
	return (
		attachment.kind === 'file' &&
		(attachment.mime_type === 'application/pdf' || attachmentExtension(attachment) === 'pdf')
	);
}

function annotationModeLabel(readiness: AnnotationReadinessPayload): string {
	if (readiness.mode === 'reduced') return 'Reduced mode';
	if (readiness.mode === 'unavailable') return 'Preview fallback';
	return 'Not applicable';
}

function annotationPreviewActionLabel(readiness: AnnotationReadinessPayload): string {
	return readiness.preview_status === 'ready' ? 'Open preview' : 'Try preview';
}

function onFeedbackItemsChanged(items: FeedbackWorkspaceItem[]) {
	feedbackForm.items = cloneFeedbackItems(items);
}

function onImgError(event: Event) {
	const element = event.target as HTMLImageElement;
	element.onerror = null;
	element.src = DEFAULT_STUDENT_IMAGE;
}
</script>
