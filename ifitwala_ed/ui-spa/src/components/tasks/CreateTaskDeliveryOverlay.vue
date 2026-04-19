<!-- ifitwala_ed/ui-spa/src/components/tasks/CreateTaskDeliveryOverlay.vue -->
<!--
  CreateTaskDeliveryOverlay.vue
  A multi-step wizard for creating a Task (content) and Task Delivery (assignment) in one flow.
  Supports creating assignments from Calendar, Class Hub, and other contexts.

  Used by:
  - OverlayHost.vue (registered globally)
  - ClassEventModal.vue
  - StaffHome.vue
-->
<template>
	<TransitionRoot as="template" :show="open" @after-leave="emitAfterLeave">
		<Dialog
			as="div"
			class="if-overlay"
			:style="{ zIndex }"
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
					<DialogPanel class="if-overlay__panel">
						<button
							ref="initialFocus"
							type="button"
							class="sr-only"
							aria-hidden="true"
							tabindex="0"
							@click="emitClose('programmatic')"
						>
							Close
						</button>
						<!-- Header -->
						<div class="flex items-start justify-between gap-3 px-5 pt-5">
							<div>
								<p class="type-overline">Task</p>
								<DialogTitle class="type-h3 text-ink mt-1">{{ dialogTitle }}</DialogTitle>
							</div>

							<button
								type="button"
								class="if-overlay__icon-button"
								aria-label="Close"
								@click="emitClose('programmatic')"
							>
								<FeatherIcon name="x" class="h-5 w-5" />
							</button>
						</div>

						<!-- Body -->
						<div class="if-overlay__body">
							<div class="space-y-6">
								<template v-if="!createdTask">
									<section class="card-panel space-y-4 p-5">
										<div class="flex items-center gap-3">
											<span class="chip">Mode</span>
											<h3 class="type-h3 text-ink">How do you want to assign this work?</h3>
										</div>
										<div class="grid gap-3 md:grid-cols-2">
											<button
												type="button"
												class="rounded-2xl border px-4 py-4 text-left transition"
												:class="
													taskMode === 'create'
														? 'border-leaf/60 bg-sky/20 text-ink shadow-sm'
														: 'border-border/70 bg-white text-ink/80 hover:border-leaf/40'
												"
												@click="setTaskMode('create')"
											>
												<p class="text-sm font-semibold text-ink">Create new task</p>
												<p class="mt-1 text-xs text-ink/60">
													Author a new reusable task, then assign it to this class.
												</p>
											</button>
											<button
												type="button"
												class="rounded-2xl border px-4 py-4 text-left transition"
												:class="
													taskMode === 'reuse'
														? 'border-leaf/60 bg-sky/20 text-ink shadow-sm'
														: 'border-border/70 bg-white text-ink/80 hover:border-leaf/40'
												"
												@click="setTaskMode('reuse')"
											>
												<p class="text-sm font-semibold text-ink">Reuse existing task</p>
												<p class="mt-1 text-xs text-ink/60">
													Assign one of your course tasks again without rewriting the task
													definition.
												</p>
											</button>
										</div>
										<p class="text-xs text-ink/60">
											New tasks stay reusable for you across your groups and future years. Share
											with the course team only when the task is ready for other teachers too.
										</p>
									</section>

									<template v-if="taskMode === 'create'">
										<section class="card-panel space-y-4 p-5">
											<div class="flex items-center gap-3">
												<span class="chip">Step 1</span>
												<h3 class="type-h3 text-ink">What are you giving students?</h3>
											</div>

											<div class="grid gap-4 md:grid-cols-2">
												<div class="space-y-1">
													<label class="type-label">Title</label>
													<FormControl
														v-model="form.title"
														type="text"
														placeholder="Assignment title"
													/>
												</div>
												<div class="space-y-1">
													<label class="type-label">Type</label>
													<FormControl
														v-model="form.task_type"
														type="select"
														:options="taskTypeOptions"
														option-label="label"
														option-value="value"
														placeholder="Select type (optional)"
													/>
												</div>
											</div>

											<div class="space-y-1">
												<label class="type-label">Instructions</label>
												<FormControl
													v-model="form.instructions"
													type="textarea"
													:rows="4"
													placeholder="Share directions, resources, or expectations..."
												/>
											</div>

											<div
												v-if="props.prefillQuizQuestionBankLabel || props.prefillUnitPlan"
												class="flex flex-wrap gap-2"
											>
												<span v-if="props.prefillUnitPlan" class="chip">
													Unit {{ props.prefillUnitPlan }}
												</span>
												<span v-if="props.prefillQuizQuestionBankLabel" class="chip">
													Quiz {{ props.prefillQuizQuestionBankLabel }}
												</span>
											</div>

											<div v-if="isQuizTask" class="grid gap-4 md:grid-cols-2">
												<div class="space-y-1">
													<label class="type-label">Question bank</label>
													<FormControl
														v-model="form.quiz_question_bank"
														type="select"
														:options="quizBankOptions"
														option-label="label"
														option-value="value"
														placeholder="Select a quiz bank"
													/>
													<p v-if="!quizBankOptions.length" class="type-caption text-ink/70">
														No published quiz banks are available yet. Build one in the shared
														course-plan workspace first.
													</p>
												</div>
												<div class="space-y-1">
													<label class="type-label">Questions per attempt</label>
													<FormControl
														v-model="form.quiz_question_count"
														type="number"
														:min="1"
														:step="1"
														placeholder="Use all if blank"
													/>
												</div>
												<div class="space-y-1">
													<label class="type-label">Time limit (minutes)</label>
													<FormControl
														v-model="form.quiz_time_limit_minutes"
														type="number"
														:min="1"
														:step="1"
														placeholder="Optional"
													/>
												</div>
												<div class="space-y-1">
													<label class="type-label">Maximum attempts</label>
													<FormControl
														v-model="form.quiz_max_attempts"
														type="number"
														:min="0"
														:step="1"
														placeholder="Unlimited if blank"
													/>
												</div>
												<div class="space-y-1">
													<label class="type-label">Pass percentage</label>
													<FormControl
														v-model="form.quiz_pass_percentage"
														type="number"
														:min="0"
														:max="100"
														:step="1"
														placeholder="Optional"
													/>
												</div>
											</div>

											<label
												class="flex items-start gap-3 rounded-2xl border border-border/70 bg-slate-50 px-4 py-3 text-sm text-ink/80"
											>
												<input
													v-model="form.share_with_course_team"
													type="checkbox"
													class="mt-0.5 rounded border-border/70 text-jacaranda"
												/>
												<span>
													<span class="block font-medium text-ink">
														Share this task with other teachers on this course
													</span>
													<span class="block text-xs text-ink/60">
														Leave this off to keep the task private to you. You can still reuse it
														across your own groups and future school years.
													</span>
												</span>
											</label>
										</section>

										<section class="card-panel space-y-4 p-5">
											<div class="flex items-center gap-3">
												<span class="chip">Step 2</span>
												<h3 class="type-h3 text-ink">Which class?</h3>
											</div>

											<div class="space-y-1">
												<label class="type-label">Class</label>

												<div
													v-if="isGroupLocked"
													class="rounded-xl border border-border/80 bg-slate-50 px-3 py-2 text-sm text-ink/80"
												>
													{{ selectedGroupLabel || props.prefillStudentGroup || 'Class selected' }}
												</div>

												<FormControl
													v-else
													v-model="form.student_group"
													type="select"
													:options="groupOptions"
													option-label="label"
													option-value="value"
													:disabled="groupsLoading"
													placeholder="Select a class"
												/>

												<p
													v-if="!groupsLoading && !groupOptions.length"
													class="type-caption text-slate-token/70"
												>
													No classes available for your role yet.
												</p>

												<div
													v-if="props.prefillUnitPlan || props.prefillClassSession"
													class="mt-3 flex flex-wrap gap-2"
												>
													<span v-if="props.prefillUnitPlan" class="chip">
														Unit {{ props.prefillUnitPlan }}
													</span>
													<span v-if="props.prefillClassSession" class="chip">
														Session {{ props.prefillClassSession }}
													</span>
												</div>
											</div>
										</section>
									</template>

									<template v-else>
										<section class="card-panel space-y-4 p-5">
											<div class="flex items-center gap-3">
												<span class="chip">Step 1</span>
												<h3 class="type-h3 text-ink">Which class and which reusable task?</h3>
											</div>

											<div class="space-y-1">
												<label class="type-label">Class</label>

												<div
													v-if="isGroupLocked"
													class="rounded-xl border border-border/80 bg-slate-50 px-3 py-2 text-sm text-ink/80"
												>
													{{ selectedGroupLabel || props.prefillStudentGroup || 'Class selected' }}
												</div>

												<FormControl
													v-else
													v-model="form.student_group"
													type="select"
													:options="groupOptions"
													option-label="label"
													option-value="value"
													:disabled="groupsLoading"
													placeholder="Select a class"
												/>

												<p
													v-if="!groupsLoading && !groupOptions.length"
													class="type-caption text-slate-token/70"
												>
													No classes available for your role yet.
												</p>
											</div>

											<div
												v-if="props.prefillUnitPlan || props.prefillClassSession"
												class="flex flex-wrap gap-2"
											>
												<span v-if="props.prefillUnitPlan" class="chip">
													Unit {{ props.prefillUnitPlan }}
												</span>
												<span v-if="props.prefillClassSession" class="chip">
													Session {{ props.prefillClassSession }}
												</span>
											</div>

											<div class="grid gap-3 md:grid-cols-[minmax(0,1fr)_auto] md:items-end">
												<div class="space-y-1">
													<label class="type-label">Search reusable tasks</label>
													<FormControl
														v-model="taskLibraryQuery"
														type="text"
														:disabled="!form.student_group"
														placeholder="Search by title"
													/>
												</div>
												<button
													type="button"
													class="if-button if-button--quiet"
													:disabled="!form.student_group || taskLibraryLoading"
													@click="loadReusableTasks"
												>
													Refresh library
												</button>
											</div>

											<div
												v-if="taskLibraryError"
												class="rounded-xl border border-flame/30 bg-flame/10 px-4 py-3 text-sm text-flame"
											>
												{{ taskLibraryError }}
											</div>

											<div
												v-else-if="!form.student_group"
												class="rounded-xl border border-dashed border-border/80 bg-slate-50 px-4 py-3 text-sm text-ink/70"
											>
												Select a class first to load reusable tasks for its course.
											</div>

											<div
												v-else-if="taskLibraryLoading && !reusableTasks.length"
												class="rounded-xl border border-line-soft bg-surface-soft px-4 py-3 text-sm text-ink/70"
											>
												Loading reusable tasks...
											</div>

											<div
												v-else-if="!reusableTasks.length"
												class="rounded-xl border border-dashed border-border/80 bg-slate-50 px-4 py-3 text-sm text-ink/70"
											>
												No reusable tasks found for this course yet.
											</div>

											<div v-else class="space-y-3">
												<button
													v-for="task in reusableTasks"
													:key="task.name"
													type="button"
													class="w-full rounded-2xl border px-4 py-4 text-left transition"
													:class="
														selectedReusableTaskName === task.name
															? 'border-leaf/60 bg-sky/20 text-ink shadow-sm'
															: 'border-border/70 bg-white text-ink/80 hover:border-leaf/40'
													"
													@click="chooseReusableTask(task.name)"
												>
													<div class="flex flex-wrap items-start justify-between gap-3">
														<div class="min-w-0">
															<p class="text-sm font-semibold text-ink">{{ task.title }}</p>
															<p class="mt-1 text-xs text-ink/60">
																{{ task.task_type || 'Task' }}
																<span v-if="task.unit_plan"> · {{ task.unit_plan }}</span>
															</p>
															<p
																v-if="task.visibility_scope === 'shared' && task.owner"
																class="mt-1 text-xs text-ink/60"
															>
																Shared by {{ task.owner }}
															</p>
														</div>
														<span class="chip">{{ task.visibility_label }}</span>
													</div>
												</button>
											</div>
										</section>

										<section v-if="selectedReusableTaskDetails" class="card-panel space-y-4 p-5">
											<div class="flex items-center gap-3">
												<span class="chip">Step 2</span>
												<h3 class="type-h3 text-ink">Selected reusable task</h3>
											</div>

											<div class="rounded-2xl border border-line-soft bg-surface-soft p-4">
												<div class="flex flex-wrap items-center gap-2">
													<p class="type-body-strong text-ink">
														{{ selectedReusableTaskDetails.title }}
													</p>
													<span class="chip">
														{{ selectedReusableTaskDetails.task_type || 'Task' }}
													</span>
													<span class="chip">
														{{
															selectedReusableTaskDetails.visibility_scope === 'shared'
																? 'Shared with course team'
																: 'Your reusable task'
														}}
													</span>
													<span v-if="selectedReusableTaskDetails.unit_plan" class="chip">
														{{ selectedReusableTaskDetails.unit_plan }}
													</span>
												</div>
												<p
													v-if="selectedReusableTaskDetails.instructions"
													class="mt-3 text-sm text-ink/70"
												>
													{{ selectedReusableTaskDetails.instructions }}
												</p>
												<p class="mt-3 text-xs text-ink/60">
													Task definition edits and task materials stay on the reusable task. Use
													this flow only for class-local assignment settings.
												</p>
											</div>
										</section>
									</template>

									<!-- Step 3 -->
									<section
										v-if="taskMode === 'create' || selectedReusableTaskDetails"
										class="card-panel space-y-4 p-5"
									>
										<div class="flex items-center gap-3">
											<span class="chip">Step 3</span>
											<h3 class="type-h3 text-ink">What will happen?</h3>
										</div>

										<div class="grid gap-3 md:grid-cols-3">
											<button
												v-for="option in deliveryOptions"
												:key="option.value"
												type="button"
												class="rounded-2xl border px-4 py-4 text-left transition"
												:class="
													form.delivery_mode === option.value
														? 'border-leaf/60 bg-sky/20 text-ink shadow-sm'
														: 'border-border/70 bg-white text-ink/80 hover:border-leaf/40'
												"
												@click="form.delivery_mode = option.value"
											>
												<p class="text-sm font-semibold text-ink">{{ option.label }}</p>
												<p class="mt-1 text-xs text-ink/60">{{ option.help }}</p>
											</button>
										</div>

										<p v-if="isQuizTask" class="type-caption text-ink/70">
											Quiz mode is controlled here: use `Assess` for an official graded quiz, or
											choose another mode for practice.
										</p>
									</section>

									<!-- Step 4 -->
									<section
										v-if="(taskMode === 'create' || selectedReusableTaskDetails) && !isQuizTask"
										class="card-panel space-y-4 p-5"
									>
										<div class="flex items-center gap-3">
											<span class="chip">Step 4</span>
											<h3 class="type-h3 text-ink">Dates</h3>
										</div>

										<div class="grid gap-4 md:grid-cols-3">
											<div class="space-y-1">
												<label class="type-label">Available from</label>
												<input
													v-model="form.available_from"
													type="datetime-local"
													class="w-full rounded-xl border border-border/80 bg-white px-3 py-2 text-sm text-ink shadow-sm focus:border-jacaranda/50 focus:ring-1 focus:ring-jacaranda/30"
												/>
											</div>
											<div class="space-y-1">
												<label class="type-label">Due date</label>
												<input
													v-model="form.due_date"
													type="datetime-local"
													class="w-full rounded-xl border border-border/80 bg-white px-3 py-2 text-sm text-ink shadow-sm focus:border-jacaranda/50 focus:ring-1 focus:ring-jacaranda/30"
												/>
											</div>
											<div class="space-y-1">
												<label class="type-label">Lock date</label>
												<input
													v-model="form.lock_date"
													type="datetime-local"
													class="w-full rounded-xl border border-border/80 bg-white px-3 py-2 text-sm text-ink shadow-sm focus:border-jacaranda/50 focus:ring-1 focus:ring-jacaranda/30"
												/>
											</div>
										</div>

										<div class="grid gap-4 md:grid-cols-2">
											<label
												v-if="showLateSubmission"
												class="flex items-center gap-2 text-sm text-ink/80"
											>
												<input
													v-model="form.allow_late_submission"
													type="checkbox"
													class="rounded border-border/70 text-jacaranda"
												/>
												Allow late submissions
											</label>
											<div
												class="rounded-xl border border-dashed border-border/80 bg-slate-50 px-3 py-2 text-sm text-ink/70"
											>
												Group submission is paused until the subgroup workflow is implemented.
											</div>
										</div>
									</section>

									<!-- Step 5 -->
									<section
										v-if="taskMode === 'create' || selectedReusableTaskDetails"
										class="card-panel space-y-4 p-5"
									>
										<div class="flex items-center gap-3">
											<span class="chip">Step 5</span>
											<h3 class="type-h3 text-ink">Grading (optional)</h3>
										</div>

										<div class="space-y-2">
											<p class="type-label">Will you assess it?</p>
											<div class="flex flex-wrap gap-2">
												<button
													type="button"
													class="rounded-full border px-4 py-2 text-sm font-medium transition"
													:class="
														gradingEnabled
															? 'border-leaf/60 bg-sky/20 text-ink'
															: 'border-border/70 bg-white text-ink/70 hover:border-leaf/40'
													"
													@click="setGradingEnabled(true)"
												>
													Yes
												</button>
												<button
													type="button"
													class="rounded-full border px-4 py-2 text-sm font-medium transition"
													:class="
														!gradingEnabled
															? 'border-leaf/60 bg-sky/20 text-ink'
															: 'border-border/70 bg-white text-ink/70 hover:border-leaf/40'
													"
													@click="setGradingEnabled(false)"
												>
													No
												</button>
											</div>
										</div>

										<div v-if="gradingEnabled" class="space-y-4">
											<div class="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
												<button
													v-for="option in gradingOptions"
													:key="option.value"
													type="button"
													class="rounded-2xl border px-4 py-4 text-left transition"
													:class="
														form.grading_mode === option.value
															? 'border-leaf/60 bg-sky/20 text-ink shadow-sm'
															: 'border-border/70 bg-white text-ink/80 hover:border-leaf/40'
													"
													@click="form.grading_mode = option.value"
												>
													<p class="text-sm font-semibold text-ink">{{ option.label }}</p>
													<p class="mt-1 text-xs text-ink/60">{{ option.help }}</p>
												</button>
											</div>

											<div v-if="form.grading_mode === 'Points'" class="max-w-xs space-y-1">
												<label class="type-label">Max points</label>
												<FormControl
													v-model="form.max_points"
													type="number"
													:min="0"
													:step="0.5"
													placeholder="Enter max points"
												/>
											</div>

											<div
												v-if="form.grading_mode === 'Criteria'"
												class="space-y-4 rounded-2xl border border-border/70 bg-surface-soft p-4"
											>
												<div class="grid gap-4 md:grid-cols-[220px_minmax(0,1fr)]">
													<div class="space-y-1">
														<label class="type-label">Rubric strategy</label>
														<FormControl
															v-model="form.rubric_scoring_strategy"
															type="select"
															:options="rubricScoringStrategyOptions"
															option-label="label"
															option-value="value"
															placeholder="Select strategy"
															data-rubric-strategy-select="true"
														/>
													</div>
													<div
														class="rounded-2xl border border-dashed border-border/80 bg-white/70 px-4 py-3 text-sm text-ink/70"
													>
														<p class="font-medium text-ink">
															Criteria stay reusable. Scoring stays local.
														</p>
														<p class="mt-1 text-xs">
															`Sum Total` computes one task total from weighted criterion points.
															`Separate Criteria` keeps the task criterion-by-criterion with no
															task total.
														</p>
													</div>
												</div>

												<div
													v-if="taskMode === 'create'"
													class="space-y-4 rounded-2xl border border-border/70 bg-white p-4"
												>
													<div class="flex items-start justify-between gap-3">
														<div>
															<p class="text-sm font-semibold text-ink">Task criteria</p>
															<p class="mt-1 text-xs text-ink/60">
																Choose from this course's assessment criteria, then set the local
																weighting and max points that this task will snapshot.
															</p>
														</div>
														<span class="chip">{{ taskCriteriaRows.length }} selected</span>
													</div>

													<div class="grid gap-3 md:grid-cols-[minmax(0,1fr)_auto] md:items-end">
														<div class="space-y-1">
															<label class="type-label">Add course criterion</label>
															<FormControl
																v-model="criteriaLibrarySelection"
																type="select"
																:options="availableCriteriaOptions"
																option-label="label"
																option-value="value"
																:disabled="criteriaLibraryLoading || !form.student_group"
																placeholder="Select a criterion"
																data-criteria-library-select="true"
															/>
														</div>
														<button
															type="button"
															class="if-button if-button--secondary"
															:disabled="!criteriaLibrarySelection"
															data-add-task-criterion="true"
															@click="addTaskCriterion"
														>
															Add criterion
														</button>
													</div>

													<div
														v-if="criteriaLibraryError"
														class="rounded-xl border border-flame/30 bg-flame/10 px-4 py-3 text-sm text-flame"
													>
														{{ criteriaLibraryError }}
													</div>

													<div
														v-else-if="criteriaLibraryLoading && !courseCriteriaLibrary.length"
														class="rounded-xl border border-dashed border-border/80 bg-slate-50 px-4 py-3 text-sm text-ink/70"
													>
														Loading course criteria...
													</div>

													<div
														v-else-if="!courseCriteriaLibrary.length"
														class="rounded-xl border border-dashed border-border/80 bg-slate-50 px-4 py-3 text-sm text-ink/70"
													>
														No course assessment criteria are configured for this class yet.
													</div>

													<div
														v-else-if="!taskCriteriaRows.length"
														class="rounded-xl border border-dashed border-border/80 bg-slate-50 px-4 py-3 text-sm text-ink/70"
													>
														Add at least one criterion to create a criteria-based task.
													</div>

													<div v-else class="space-y-3">
														<div
															v-for="row in taskCriteriaRows"
															:key="row.assessment_criteria"
															class="rounded-2xl border border-border/70 bg-slate-50/70 p-4"
														>
															<div class="flex items-start justify-between gap-3">
																<div>
																	<p class="text-sm font-semibold text-ink">
																		{{ row.criteria_name || row.assessment_criteria }}
																	</p>
																	<p class="mt-1 text-xs text-ink/60">
																		{{ row.assessment_criteria }}
																		<span v-if="row.levels?.length">
																			· Levels:
																			{{ row.levels.map(level => level.level).join(' · ') }}
																		</span>
																	</p>
																</div>
																<button
																	type="button"
																	class="text-xs font-medium text-flame transition hover:text-flame/80"
																	@click="removeTaskCriterion(row.assessment_criteria)"
																>
																	Remove
																</button>
															</div>

															<div class="mt-3 grid gap-3 md:grid-cols-2">
																<div class="space-y-1">
																	<label class="type-label">Weighting (%)</label>
																	<FormControl
																		v-model="row.criteria_weighting"
																		type="number"
																		:min="0"
																		:step="0.1"
																		placeholder="e.g. 25"
																	/>
																</div>
																<div class="space-y-1">
																	<label class="type-label">Max points</label>
																	<FormControl
																		v-model="row.criteria_max_points"
																		type="number"
																		:min="0"
																		:step="0.1"
																		placeholder="e.g. 8"
																	/>
																</div>
															</div>
														</div>
													</div>

													<p
														v-if="
															form.rubric_scoring_strategy === 'Sum Total' &&
															taskCriteriaRows.length
														"
														class="text-xs"
														:class="criteriaWeightingLooksReady ? 'text-ink/60' : 'text-clay'"
													>
														Current weighting total: {{ criteriaWeightTotalLabel }}%. Sum Total
														works best when the course weighting adds to 100%.
													</p>
												</div>

												<div
													v-else
													class="space-y-3 rounded-2xl border border-border/70 bg-white p-4"
												>
													<div class="flex items-start justify-between gap-3">
														<div>
															<p class="text-sm font-semibold text-ink">Reusable task criteria</p>
															<p class="mt-1 text-xs text-ink/60">
																This reusable task already owns its criteria rows. You can review
																them here and change only the delivery strategy for this class.
															</p>
														</div>
														<span class="chip">{{ activeCriteriaRows.length }} criteria</span>
													</div>

													<div
														v-if="!activeCriteriaRows.length"
														class="rounded-xl border border-flame/30 bg-flame/10 px-4 py-3 text-sm text-flame"
													>
														This reusable task is marked as criteria-based but does not carry task
														criteria yet.
													</div>

													<div v-else class="space-y-3">
														<div
															v-for="row in activeCriteriaRows"
															:key="row.assessment_criteria"
															class="rounded-2xl border border-border/70 bg-slate-50/70 p-4"
														>
															<div class="flex flex-wrap items-start justify-between gap-3">
																<div>
																	<p class="text-sm font-semibold text-ink">
																		{{ row.criteria_name || row.assessment_criteria }}
																	</p>
																	<p class="mt-1 text-xs text-ink/60">
																		{{ row.assessment_criteria }}
																	</p>
																</div>
																<div class="flex flex-wrap gap-2 text-xs text-ink/60">
																	<span v-if="row.criteria_weighting != null" class="chip">
																		{{ row.criteria_weighting }}%
																	</span>
																	<span v-if="row.criteria_max_points != null" class="chip">
																		{{ row.criteria_max_points }} pts
																	</span>
																</div>
															</div>
															<p v-if="row.levels?.length" class="mt-2 text-xs text-ink/60">
																Levels: {{ row.levels.map(level => level.level).join(' · ') }}
															</p>
														</div>
													</div>
												</div>
											</div>
										</div>

										<div class="space-y-2">
											<p class="type-label">Allow comment in gradebook?</p>
											<div class="flex flex-wrap gap-2">
												<button
													type="button"
													class="rounded-full border px-4 py-2 text-sm font-medium transition"
													:class="
														form.allow_feedback
															? 'border-leaf/60 bg-sky/20 text-ink'
															: 'border-border/70 bg-white text-ink/70 hover:border-leaf/40'
													"
													@click="form.allow_feedback = true"
												>
													Yes
												</button>
												<button
													type="button"
													class="rounded-full border px-4 py-2 text-sm font-medium transition"
													:class="
														!form.allow_feedback
															? 'border-leaf/60 bg-sky/20 text-ink'
															: 'border-border/70 bg-white text-ink/70 hover:border-leaf/40'
													"
													@click="form.allow_feedback = false"
												>
													No
												</button>
											</div>
											<p class="text-xs text-ink/60">
												Show a comment box in the gradebook only when this is turned on. Comments
												stay separate from points, criteria, or completion.
											</p>
										</div>

										<p class="text-xs text-ink/60">
											Moderation happens after grading (peer check).
										</p>
									</section>

									<div
										v-if="errorMessage"
										class="rounded-xl border border-flame/30 bg-flame/10 px-4 py-3 text-sm text-flame"
									>
										<p>{{ errorMessage }}</p>
										<div
											v-if="errorRecovery === 'open-class-planning' && form.student_group"
											class="mt-3"
										>
											<button
												type="button"
												class="if-button if-button--secondary"
												@click="openClassPlanning"
											>
												Open class planning
											</button>
										</div>
									</div>
								</template>

								<template v-else>
									<section class="card-panel space-y-4 p-5">
										<div class="flex items-center gap-3">
											<span class="chip">Created</span>
											<h3 class="type-h3 text-ink">Assigned work ready</h3>
										</div>
										<p v-if="canEditTaskMaterials" class="type-body text-ink/80">
											Add supporting materials while you are still in the task flow. Shared plan
											content stays in curriculum planning; these are separately openable materials
											for students.
										</p>
										<p v-else class="type-body text-ink/80">
											This delivery now points to the reusable task you selected. Add any
											class-specific resources in Class Planning rather than editing shared task
											materials from this assign flow.
										</p>
										<div class="grid gap-3 md:grid-cols-3">
											<div class="rounded-2xl border border-line-soft bg-surface-soft p-4">
												<p class="type-overline text-ink/60">Task</p>
												<p class="mt-1 type-body-strong text-ink">{{ createdTask.task }}</p>
											</div>
											<div class="rounded-2xl border border-line-soft bg-surface-soft p-4">
												<p class="type-overline text-ink/60">Delivery</p>
												<p class="mt-1 type-body-strong text-ink">
													{{ createdTask.task_delivery }}
												</p>
											</div>
											<div class="rounded-2xl border border-line-soft bg-surface-soft p-4">
												<p class="type-overline text-ink/60">Outcomes</p>
												<p class="mt-1 type-body-strong text-ink">
													{{ createdTask.outcomes_created ?? '—' }}
												</p>
											</div>
										</div>
									</section>

									<section v-if="canEditTaskMaterials" class="card-panel space-y-4 p-5">
										<div class="flex items-center gap-3">
											<span class="chip">Materials</span>
											<h3 class="type-h3 text-ink">Add task materials</h3>
										</div>

										<div class="flex flex-wrap gap-2">
											<button
												type="button"
												class="rounded-full border px-4 py-2 text-sm font-medium transition"
												:class="
													materialComposerMode === 'link'
														? 'border-leaf/60 bg-sky/20 text-ink'
														: 'border-border/70 bg-white text-ink/70 hover:border-leaf/40'
												"
												@click="materialComposerMode = 'link'"
											>
												Add link
											</button>
											<button
												type="button"
												class="rounded-full border px-4 py-2 text-sm font-medium transition"
												:class="
													materialComposerMode === 'file'
														? 'border-leaf/60 bg-sky/20 text-ink'
														: 'border-border/70 bg-white text-ink/70 hover:border-leaf/40'
												"
												@click="materialComposerMode = 'file'"
											>
												Upload file
											</button>
										</div>

										<div class="grid gap-4 md:grid-cols-2">
											<div class="space-y-1">
												<label class="type-label">Title</label>
												<FormControl
													v-model="materialForm.title"
													type="text"
													placeholder="Material title"
												/>
											</div>
											<div class="space-y-1">
												<label class="type-label">How students use it</label>
												<FormControl
													v-model="materialForm.modality"
													type="select"
													:options="materialModalityOptions"
													option-label="label"
													option-value="value"
												/>
											</div>
										</div>

										<div class="grid gap-4 md:grid-cols-2">
											<div class="space-y-1">
												<label class="type-label">Usage role</label>
												<FormControl
													v-model="materialForm.usage_role"
													type="select"
													:options="materialUsageRoleOptions"
													option-label="label"
													option-value="value"
												/>
											</div>
											<div class="space-y-1">
												<label class="type-label">Teacher note</label>
												<FormControl
													v-model="materialForm.placement_note"
													type="text"
													placeholder="Optional note for students"
												/>
											</div>
										</div>

										<div class="space-y-1">
											<label class="type-label">Description</label>
											<FormControl
												v-model="materialForm.description"
												type="textarea"
												:rows="3"
												placeholder="Optional context about this material"
											/>
										</div>

										<div v-if="materialComposerMode === 'link'" class="space-y-1">
											<label class="type-label">Reference URL</label>
											<FormControl
												v-model="materialForm.reference_url"
												type="text"
												placeholder="https://..."
											/>
										</div>

										<div v-else class="space-y-3">
											<input
												ref="materialFileInput"
												type="file"
												class="hidden"
												@change="onMaterialFileSelected"
											/>
											<div class="flex flex-wrap items-center gap-3">
												<button
													type="button"
													class="if-button if-button--secondary"
													@click="materialFileInput?.click()"
												>
													Choose file
												</button>
												<p class="type-caption text-ink/70">
													{{ selectedMaterialFile?.name || 'No file selected yet.' }}
												</p>
											</div>
											<InlineUploadStatus
												v-if="materialUploadProgress"
												:label="materialUploadProgressLabel"
												:progress="materialUploadProgress"
											/>
										</div>

										<div
											v-if="materialError"
											class="rounded-xl border border-flame/30 bg-flame/10 px-4 py-3 text-sm text-flame"
										>
											{{ materialError }}
										</div>

										<div class="flex justify-end">
											<button
												type="button"
												class="if-button if-button--primary"
												:disabled="!canAddMaterial || materialSubmitting"
												@click="addMaterial"
											>
												{{
													materialSubmitting
														? materialComposerMode === 'link'
															? 'Adding…'
															: 'Uploading…'
														: materialComposerMode === 'link'
															? 'Add link'
															: 'Upload file'
												}}
											</button>
										</div>
									</section>

									<section v-if="canEditTaskMaterials" class="card-panel space-y-4 p-5">
										<div class="flex items-center justify-between gap-3">
											<div class="flex items-center gap-3">
												<span class="chip">Shared</span>
												<h3 class="type-h3 text-ink">Current task materials</h3>
											</div>
											<span class="chip">{{ taskMaterials.length }} items</span>
										</div>

										<div
											v-if="materialsLoading"
											class="rounded-xl border border-line-soft bg-surface-soft px-4 py-3 text-sm text-ink/70"
										>
											Loading materials...
										</div>

										<div
											v-else-if="!taskMaterials.length"
											class="rounded-xl border border-dashed border-border/80 bg-slate-50 px-4 py-3 text-sm text-ink/70"
										>
											No materials shared on this task yet.
										</div>

										<div v-else class="space-y-3">
											<article
												v-for="material in taskMaterials"
												:key="material.placement"
												class="rounded-2xl border border-line-soft bg-surface-soft p-4"
											>
												<div v-if="showInlineImagePreview(material)" class="mb-4">
													<a
														:href="primaryMaterialUrl(material) || undefined"
														target="_blank"
														rel="noreferrer"
														class="group block overflow-hidden rounded-2xl border border-line-soft bg-white"
														data-task-material-preview-kind="image"
													>
														<img
															:src="primaryMaterialUrl(material) || undefined"
															:alt="material.title"
															class="h-40 w-full object-cover transition duration-200 group-hover:scale-[1.01]"
															loading="lazy"
														/>
														<div
															class="flex items-center justify-between border-t border-line-soft bg-white px-4 py-3"
														>
															<div>
																<p
																	class="text-xs font-semibold uppercase tracking-[0.18em] text-ink/45"
																>
																	Image preview
																</p>
																<p class="mt-1 text-sm text-ink/80">
																	Open the governed preview for this task material.
																</p>
															</div>
															<span class="chip">{{ materialExtensionLabel(material) }}</span>
														</div>
													</a>
												</div>

												<div v-else-if="showPdfPreviewTile(material)" class="mb-4">
													<a
														:href="primaryMaterialUrl(material) || undefined"
														target="_blank"
														rel="noreferrer"
														class="group block rounded-2xl border border-line-soft bg-white p-4 transition hover:border-jacaranda/30 hover:bg-jacaranda/5"
														data-task-material-preview-kind="pdf"
													>
														<div class="flex items-start justify-between gap-3">
															<div>
																<p
																	class="text-xs font-semibold uppercase tracking-[0.18em] text-ink/45"
																>
																	PDF preview
																</p>
																<p class="mt-2 text-base font-semibold text-ink">
																	{{ material.title }}
																</p>
																<p class="mt-2 text-sm text-ink/75">
																	Open a compact governed preview for this task material.
																</p>
															</div>
															<div class="rounded-2xl bg-clay/15 px-3 py-2 text-right">
																<p
																	class="text-[11px] font-semibold uppercase tracking-[0.18em] text-clay"
																>
																	{{ materialExtensionLabel(material) }}
																</p>
																<p class="mt-1 text-xs text-ink/60">Preview ready</p>
															</div>
														</div>
													</a>
												</div>

												<div class="flex items-start justify-between gap-3">
													<div class="min-w-0">
														<div class="flex flex-wrap items-center gap-2">
															<p class="type-body-strong text-ink">{{ material.title }}</p>
															<span class="chip">{{ material.material_type }}</span>
															<span v-if="material.usage_role" class="chip">
																{{ material.usage_role }}
															</span>
														</div>
														<p v-if="material.description" class="mt-2 type-caption text-ink/70">
															{{ material.description }}
														</p>
														<p
															v-if="material.placement_note"
															class="mt-2 type-caption text-ink/70"
														>
															{{ material.placement_note }}
														</p>
														<p
															v-if="material.file_name || material.reference_url"
															class="mt-2 type-caption text-ink/70"
														>
															{{ material.file_name || material.reference_url }}
														</p>
													</div>
													<div class="flex items-center gap-2">
														<a
															v-if="primaryMaterialUrl(material)"
															:href="primaryMaterialUrl(material) || undefined"
															target="_blank"
															rel="noreferrer"
															class="if-action"
														>
															{{ primaryMaterialActionLabel(material) }}
														</a>
														<a
															v-if="showMaterialOpenOriginalAction(material)"
															:href="material.open_url || undefined"
															target="_blank"
															rel="noreferrer"
															class="if-action"
														>
															Open original
														</a>
														<button
															type="button"
															class="if-button if-button--danger"
															:disabled="removingPlacement === material.placement"
															@click="removeMaterial(material.placement)"
														>
															Remove
														</button>
													</div>
												</div>
											</article>
										</div>
									</section>
								</template>
							</div>
						</div>

						<!-- Footer -->
						<div class="if-overlay__footer">
							<button
								type="button"
								class="if-button if-button--secondary"
								@click="emitClose('programmatic')"
							>
								{{ createdTask ? 'Done' : 'Cancel' }}
							</button>
							<button
								v-if="!createdTask"
								type="button"
								class="if-button if-button--primary"
								:disabled="!canSubmit"
								@click="submit"
							>
								{{ submitLabel }}
							</button>
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
import { FormControl, createResource, toast, FeatherIcon } from 'frappe-ui';
import { useRouter } from 'vue-router';
import InlineUploadStatus from '@/components/feedback/InlineUploadStatus.vue';
import { apiUpload } from '@/lib/client';
import { SIGNAL_TASK_DELIVERY_CREATED, uiSignals } from '@/lib/uiSignals';
import type { UploadProgressState } from '@/lib/uploadProgress';
import type {
	CreateTaskDeliveryInput,
	CreateTaskDeliveryPayload,
	CourseAssessmentCriteriaOption,
	ReusableTaskSummary,
	TaskCriteriaRow,
	TaskForDeliveryPayload,
	TaskLibraryScope,
} from '@/types/tasks';

const props = defineProps<{
	open: boolean;
	zIndex?: number;
	prefillStudentGroup?: string | null;
	prefillCourse?: string | null;
	prefillClassTeachingPlan?: string | null;
	prefillClassSession?: string | null;
	prefillUnitPlan?: string | null;
	prefillQuizQuestionBank?: string | null;
	prefillQuizQuestionBankLabel?: string | null;
	prefillTitle?: string | null;
	prefillTaskType?: string | null;
	prefillDueDate?: string | null;
	prefillAvailableFrom?: string | null;
}>();

type CloseReason = 'backdrop' | 'esc' | 'programmatic';
type ErrorRecoveryAction = 'open-class-planning' | null;

const MISSING_ACTIVE_PLAN_MESSAGE =
	'This class needs an active Class Teaching Plan before assigned work can be created.';
const SELECT_CLASS_PLAN_MESSAGE =
	'Select the Class Teaching Plan for this class before creating assigned work.';

const emit = defineEmits<{
	(e: 'close', reason: CloseReason): void;
	(e: 'created', payload: CreateTaskDeliveryPayload): void;
	(e: 'after-leave'): void;
}>();

const open = computed(() => props.open);
const zIndex = computed(() => props.zIndex ?? 60);
const router = useRouter();

const submitting = ref(false);
const errorMessage = ref('');
const errorRecovery = ref<ErrorRecoveryAction>(null);
const createdTask = ref<CreateTaskDeliveryPayload | null>(null);
const taskMaterials = ref<TaskMaterialRow[]>([]);
const materialComposerMode = ref<'link' | 'file'>('link');
const materialSubmitting = ref(false);
const materialError = ref('');
const selectedMaterialFile = ref<File | null>(null);
const materialFileInput = ref<HTMLInputElement | null>(null);
const removingPlacement = ref<string | null>(null);
const materialUploadProgress = ref<UploadProgressState | null>(null);

const initialFocus = ref<HTMLElement | null>(null);

function emitClose(reason: CloseReason = 'programmatic') {
	emit('close', reason);
}

function emitAfterLeave() {
	emit('after-leave');
}

/**
 * HeadlessUI Dialog @close payload is ambiguous (boolean/undefined).
 * Under A+, ignore it and close only via explicit backdrop/esc/button paths.
 */
function onDialogClose(_payload: unknown) {
	// no-op by design
}

function onKeydown(e: KeyboardEvent) {
	if (!props.open) return;
	if (e.key === 'Escape') emitClose('esc');
}

const taskTypeOptions = [
	{ label: 'Assignment', value: 'Assignment' },
	{ label: 'Homework', value: 'Homework' },
	{ label: 'Classwork', value: 'Classwork' },
	{ label: 'Quiz', value: 'Quiz' },
	{ label: 'Test', value: 'Test' },
	{ label: 'Summative assessment', value: 'Summative assessment' },
	{ label: 'Formative assessment', value: 'Formative assessment' },
	{ label: 'Discussion', value: 'Discussion' },
	{ label: 'Project', value: 'Project' },
	{ label: 'Long Term Project', value: 'Long Term Project' },
	{ label: 'Exam', value: 'Exam' },
	{ label: 'Other', value: 'Other' },
];

type TaskComposerMode = 'create' | 'reuse';
type DeliveryMode = CreateTaskDeliveryInput['delivery_mode'];
type RubricScoringStrategy = NonNullable<CreateTaskDeliveryInput['rubric_scoring_strategy']>;
type TaskMaterialRow = {
	placement: string;
	material: string;
	title: string;
	material_type: 'File' | 'Reference Link';
	modality?: 'Read' | 'Watch' | 'Listen' | 'Use' | null;
	description?: string | null;
	reference_url?: string | null;
	preview_url?: string | null;
	open_url?: string | null;
	file_name?: string | null;
	file_size?: number | string | null;
	usage_role?: 'Required' | 'Reference' | 'Template' | 'Example' | null;
	placement_note?: string | null;
};

const deliveryOptions: Array<{ label: string; value: DeliveryMode; help: string }> = [
	{
		label: 'Just post it',
		value: 'Assign Only',
		help: 'Share the assignment without collecting work.',
	},
	{
		label: 'Collect work',
		value: 'Collect Work',
		help: 'Students submit evidence; grading is optional.',
	},
	{ label: 'Collect and assess', value: 'Assess', help: 'Collect evidence and grade it.' },
];

const gradingOptions = [
	{ label: 'Points', value: 'Points', help: 'Score work with a numeric total.' },
	{ label: 'Complete / Not complete', value: 'Completion', help: 'Track completion only.' },
	{ label: 'Yes / No', value: 'Binary', help: 'Simple yes or no grading.' },
	{
		label: 'Criteria',
		value: 'Criteria',
		help: 'Assess with reusable criteria and a local rubric strategy.',
	},
];
const rubricScoringStrategyOptions: Array<{ label: string; value: RubricScoringStrategy }> = [
	{ label: 'Sum Total', value: 'Sum Total' },
	{ label: 'Separate Criteria', value: 'Separate Criteria' },
];
const materialModalityOptions = [
	{ label: 'Read', value: 'Read' },
	{ label: 'Watch', value: 'Watch' },
	{ label: 'Listen', value: 'Listen' },
	{ label: 'Use', value: 'Use' },
];
const materialUsageRoleOptions = [
	{ label: 'Reference', value: 'Reference' },
	{ label: 'Required', value: 'Required' },
	{ label: 'Template', value: 'Template' },
	{ label: 'Example', value: 'Example' },
];

type FormState = {
	title: string;
	instructions: string;
	task_type: string;
	quiz_question_bank: string;
	quiz_question_count: string;
	quiz_time_limit_minutes: string;
	quiz_max_attempts: string;
	quiz_pass_percentage: string;
	student_group: string;
	delivery_mode: DeliveryMode;
	available_from: string;
	due_date: string;
	lock_date: string;
	allow_late_submission: boolean;
	group_submission: boolean;
	share_with_course_team: boolean;
	grading_mode: string;
	rubric_scoring_strategy: '' | RubricScoringStrategy;
	allow_feedback: boolean;
	max_points: string;
};
type MaterialFormState = {
	title: string;
	description: string;
	reference_url: string;
	modality: 'Read' | 'Watch' | 'Listen' | 'Use';
	usage_role: 'Required' | 'Reference' | 'Template' | 'Example';
	placement_note: string;
};

const form = reactive<FormState>({
	title: '',
	instructions: '',
	task_type: '',
	quiz_question_bank: '',
	quiz_question_count: '',
	quiz_time_limit_minutes: '',
	quiz_max_attempts: '',
	quiz_pass_percentage: '',
	student_group: '',
	delivery_mode: 'Assign Only',
	available_from: '',
	due_date: '',
	lock_date: '',
	allow_late_submission: false,
	group_submission: false,
	share_with_course_team: false,
	grading_mode: '',
	rubric_scoring_strategy: '',
	allow_feedback: false,
	max_points: '',
});
const materialForm = reactive<MaterialFormState>({
	title: '',
	description: '',
	reference_url: '',
	modality: 'Read',
	usage_role: 'Reference',
	placement_note: '',
});

const gradingEnabled = ref(false);
const taskMode = ref<TaskComposerMode>('create');
const createdTaskMode = ref<TaskComposerMode | null>(null);
const reusableTasks = ref<ReusableTaskSummary[]>([]);
const taskLibraryQuery = ref('');
const taskLibraryError = ref('');
const selectedReusableTaskName = ref('');
const selectedReusableTaskDetails = ref<TaskForDeliveryPayload | null>(null);
const courseCriteriaLibrary = ref<CourseAssessmentCriteriaOption[]>([]);
const criteriaLibraryLoadedForGroup = ref('');
const criteriaLibraryError = ref('');
const criteriaLibrarySelection = ref('');
const taskCriteriaRows = ref<TaskCriteriaRow[]>([]);

function unwrapMessage<T>(res: any): T | undefined {
	if (res && typeof res === 'object' && 'message' in res) return (res as any).message;
	return res as T;
}

const isGroupLocked = computed(() => !!props.prefillStudentGroup);

const groups = ref<Array<{ name: string; student_group_name?: string }>>([]);

const groupResource = createResource({
	url: 'ifitwala_ed.api.student_groups.fetch_groups',
	method: 'POST',
	auto: false,
	transform: unwrapMessage,
	onSuccess: (rows: any) => {
		groups.value = Array.isArray(rows) ? rows : [];
	},
	onError: () => {
		groups.value = [];
		toast.create({ appearance: 'danger', message: 'Unable to load classes right now.' });
	},
});

const groupsLoading = computed(() => groupResource.loading);

const quizBanks = ref<Array<{ name: string; bank_title?: string; course?: string }>>([]);

const quizBankResource = createResource({
	url: 'ifitwala_ed.api.quiz.list_question_banks',
	method: 'POST',
	auto: false,
	transform: unwrapMessage,
	onSuccess: (rows: any) => {
		quizBanks.value = Array.isArray(rows) ? rows : [];
	},
	onError: () => {
		quizBanks.value = [];
	},
});

const searchReusableTasksResource = createResource({
	url: 'ifitwala_ed.api.task.search_reusable_tasks',
	method: 'POST',
	auto: false,
	transform: unwrapMessage,
	onSuccess: (rows: any) => {
		reusableTasks.value = Array.isArray(rows) ? rows : [];
		taskLibraryError.value = '';
		if (selectedReusableTaskName.value) {
			const stillVisible = reusableTasks.value.some(
				row => row.name === selectedReusableTaskName.value
			);
			if (!stillVisible) {
				selectedReusableTaskName.value = '';
				selectedReusableTaskDetails.value = null;
			}
		}
	},
	onError: (err: any) => {
		console.error('[CreateTaskDeliveryOverlay] searchReusableTasks:error', err);
		reusableTasks.value = [];
		selectedReusableTaskName.value = '';
		selectedReusableTaskDetails.value = null;
		taskLibraryError.value = extractTaskActionErrorMessage(
			err,
			'Unable to load reusable tasks right now.'
		);
	},
});

const getReusableTaskResource = createResource({
	url: 'ifitwala_ed.api.task.get_task_for_delivery',
	method: 'POST',
	auto: false,
	transform: unwrapMessage,
	onSuccess: (payload: any) => {
		selectedReusableTaskDetails.value = payload || null;
		taskLibraryError.value = '';
		if (payload) applyReusableTaskDefaults(payload as TaskForDeliveryPayload);
	},
	onError: (err: any) => {
		console.error('[CreateTaskDeliveryOverlay] getReusableTask:error', err);
		selectedReusableTaskDetails.value = null;
		taskLibraryError.value = extractTaskActionErrorMessage(
			err,
			'Unable to load that task right now.'
		);
	},
});
const listCourseAssessmentCriteriaResource = createResource({
	url: 'ifitwala_ed.api.task.list_course_assessment_criteria',
	method: 'POST',
	auto: false,
	transform: unwrapMessage,
	onSuccess: (rows: any) => {
		courseCriteriaLibrary.value = normalizeCriteriaRows(Array.isArray(rows) ? rows : []);
		criteriaLibraryLoadedForGroup.value = form.student_group;
		criteriaLibraryError.value = '';
	},
	onError: (err: any) => {
		console.error('[CreateTaskDeliveryOverlay] listCourseAssessmentCriteria:error', err);
		courseCriteriaLibrary.value = [];
		criteriaLibraryLoadedForGroup.value = '';
		criteriaLibraryError.value = extractTaskActionErrorMessage(
			err,
			'Unable to load course assessment criteria right now.'
		);
	},
});

const groupOptions = computed(() =>
	groups.value.map(row => ({
		label: row.student_group_name || row.name,
		value: row.name,
	}))
);

const quizBankOptions = computed(() =>
	quizBanks.value.map(row => ({
		label: row.course
			? `${row.bank_title || row.name} · ${row.course}`
			: row.bank_title || row.name,
		value: row.name,
	}))
);

const selectedGroupLabel = computed(() => {
	const match = groupOptions.value.find(o => o.value === form.student_group);
	return match?.label || '';
});

const dialogTitle = computed(() => (taskMode.value === 'reuse' ? 'Reuse task' : 'Create task'));
const submitLabel = computed(() =>
	taskMode.value === 'reuse' ? 'Assign existing task' : 'Create'
);
const selectedReusableTask = computed(
	() => reusableTasks.value.find(row => row.name === selectedReusableTaskName.value) || null
);
const activeCriteriaRows = computed(() =>
	taskMode.value === 'create'
		? taskCriteriaRows.value
		: normalizeCriteriaRows(
				selectedReusableTaskDetails.value?.criteria_defaults?.criteria_rows || []
			)
);
const activeTaskType = computed(() =>
	taskMode.value === 'reuse'
		? selectedReusableTaskDetails.value?.task_type || selectedReusableTask.value?.task_type || ''
		: form.task_type
);
const showLateSubmission = computed(() => form.delivery_mode !== 'Assign Only');
const isQuizTask = computed(() => activeTaskType.value === 'Quiz');
const canEditTaskMaterials = computed(() => createdTaskMode.value === 'create');
const criteriaLibraryLoading = computed(() => listCourseAssessmentCriteriaResource.loading);
const availableCriteriaOptions = computed(() =>
	courseCriteriaLibrary.value
		.filter(
			row =>
				!taskCriteriaRows.value.some(
					selected => selected.assessment_criteria === row.assessment_criteria
				)
		)
		.map(row => ({
			label: row.criteria_name || row.assessment_criteria,
			value: row.assessment_criteria,
		}))
);
const criteriaWeightTotal = computed(() =>
	activeCriteriaRows.value.reduce(
		(total, row) => total + coerceOptionalNumber(row.criteria_weighting),
		0
	)
);
const criteriaWeightingLooksReady = computed(
	() => Math.abs(criteriaWeightTotal.value - 100) <= 0.01
);
const criteriaWeightTotalLabel = computed(() => formatWeightTotal(criteriaWeightTotal.value));

watch(
	() => form.delivery_mode,
	mode => {
		if (mode === 'Assign Only') {
			form.allow_late_submission = false;
		}
	}
);

const canSubmit = computed(() => {
	if (!form.student_group) return false;
	if (!form.delivery_mode) return false;
	if (taskMode.value === 'reuse') {
		if (!selectedReusableTaskDetails.value?.name) return false;
		if (!gradingEnabled.value) return true;
		if (!form.grading_mode) return false;
		if (form.grading_mode === 'Points' && !String(form.max_points || '').trim()) return false;
		if (form.grading_mode === 'Criteria') {
			if (!form.rubric_scoring_strategy) return false;
			if (!activeCriteriaRows.value.length) return false;
		}
		return true;
	}
	if (!form.title.trim()) return false;
	if (isQuizTask.value && !form.quiz_question_bank) return false;
	if (!gradingEnabled.value) return true;
	if (!form.grading_mode) return false;
	if (form.grading_mode === 'Points' && !String(form.max_points || '').trim()) return false;
	if (form.grading_mode === 'Criteria') {
		if (!form.rubric_scoring_strategy) return false;
		if (!taskCriteriaRows.value.length) return false;
	}
	return true;
});
const canAddMaterial = computed(() => {
	if (!createdTask.value || materialSubmitting.value) return false;
	if (!materialForm.title.trim()) return false;
	if (materialComposerMode.value === 'link') return Boolean(materialForm.reference_url.trim());
	return Boolean(selectedMaterialFile.value);
});

watch(
	() => props.open,
	openNow => {
		if (!openNow) return;

		initializeForm();

		// quick-link mode (no prefill) => load dropdown list
		if (!isGroupLocked.value) {
			groupResource.submit({});
		}
		quizBankResource.submit({
			course: props.prefillCourse || undefined,
		});
	},
	{ immediate: true }
);

watch(
	() => props.open,
	v => {
		if (v) document.addEventListener('keydown', onKeydown, true);
		else document.removeEventListener('keydown', onKeydown, true);
	},
	{ immediate: true }
);

onBeforeUnmount(() => {
	document.removeEventListener('keydown', onKeydown, true);
});

function initializeForm() {
	createdTask.value = null;
	createdTaskMode.value = null;
	taskMode.value = 'create';
	form.title = props.prefillTitle || '';
	form.instructions = '';
	form.task_type = props.prefillTaskType || '';
	form.quiz_question_bank = props.prefillQuizQuestionBank || '';
	form.quiz_question_count = '';
	form.quiz_time_limit_minutes = '';
	form.quiz_max_attempts = '';
	form.quiz_pass_percentage = '';
	form.student_group = props.prefillStudentGroup || '';
	form.delivery_mode = 'Assign Only';
	form.available_from = toDateTimeInput(props.prefillAvailableFrom);
	form.due_date = toDateTimeInput(props.prefillDueDate);
	form.lock_date = '';
	form.allow_late_submission = false;
	form.group_submission = false;
	form.share_with_course_team = false;
	form.grading_mode = '';
	form.rubric_scoring_strategy = '';
	form.allow_feedback = false;
	form.max_points = '';
	gradingEnabled.value = false;
	errorMessage.value = '';
	errorRecovery.value = null;
	reusableTasks.value = [];
	taskLibraryQuery.value = '';
	taskLibraryError.value = '';
	selectedReusableTaskName.value = '';
	selectedReusableTaskDetails.value = null;
	courseCriteriaLibrary.value = [];
	criteriaLibraryLoadedForGroup.value = '';
	criteriaLibraryError.value = '';
	criteriaLibrarySelection.value = '';
	taskCriteriaRows.value = [];
	resetMaterialComposer();
}

function resetDeliveryFields() {
	form.delivery_mode = 'Assign Only';
	form.available_from = toDateTimeInput(props.prefillAvailableFrom);
	form.due_date = toDateTimeInput(props.prefillDueDate);
	form.lock_date = '';
	form.allow_late_submission = false;
	form.group_submission = false;
	form.grading_mode = '';
	form.rubric_scoring_strategy = '';
	form.allow_feedback = false;
	form.max_points = '';
	gradingEnabled.value = false;
	errorMessage.value = '';
	errorRecovery.value = null;
}

function setTaskMode(nextMode: TaskComposerMode) {
	if (taskMode.value === nextMode) return;
	taskMode.value = nextMode;
	errorMessage.value = '';
	errorRecovery.value = null;
	resetDeliveryFields();
	if (nextMode === 'create') {
		reusableTasks.value = [];
		taskLibraryQuery.value = '';
		taskLibraryError.value = '';
		selectedReusableTaskName.value = '';
		selectedReusableTaskDetails.value = null;
		taskCriteriaRows.value = [];
		criteriaLibrarySelection.value = '';
		form.title = props.prefillTitle || '';
		form.instructions = '';
		form.task_type = props.prefillTaskType || '';
		form.quiz_question_bank = props.prefillQuizQuestionBank || '';
		form.quiz_question_count = '';
		form.quiz_time_limit_minutes = '';
		form.quiz_max_attempts = '';
		form.quiz_pass_percentage = '';
		return;
	}
	form.title = '';
	form.instructions = '';
	form.task_type = '';
	form.quiz_question_bank = '';
	form.quiz_question_count = '';
	form.quiz_time_limit_minutes = '';
	form.quiz_max_attempts = '';
	form.quiz_pass_percentage = '';
	taskCriteriaRows.value = [];
	criteriaLibrarySelection.value = '';
	void loadReusableTasks();
}

function openClassPlanning() {
	if (!form.student_group) return;
	emitClose('programmatic');
	void router.push({
		name: 'staff-class-planning',
		params: { studentGroup: form.student_group },
	});
}

function setGradingEnabled(value: boolean) {
	gradingEnabled.value = value;
	if (!value) {
		form.grading_mode = '';
		form.rubric_scoring_strategy = '';
		form.max_points = '';
	}
}

watch(
	() => activeTaskType.value,
	taskType => {
		if (taskType === 'Quiz') {
			form.delivery_mode = 'Assign Only';
			gradingEnabled.value = false;
			form.grading_mode = '';
			form.rubric_scoring_strategy = '';
			form.max_points = '';
			if (taskMode.value === 'create') return;
			return;
		}
		if (taskMode.value === 'reuse') {
			return;
		}
		form.quiz_question_bank = '';
		form.quiz_question_count = '';
		form.quiz_time_limit_minutes = '';
		form.quiz_max_attempts = '';
		form.quiz_pass_percentage = '';
	}
);

watch(
	() => [props.open, taskMode.value, form.student_group, form.grading_mode] as const,
	([isOpen, mode, studentGroup, gradingMode]) => {
		if (!isOpen) return;
		if (mode !== 'create') return;
		if (gradingMode !== 'Criteria') return;
		if (!studentGroup) return;
		void ensureCourseCriteriaLibraryLoaded();
	},
	{ immediate: true }
);

watch(
	() => form.student_group,
	(studentGroup, previousGroup) => {
		if (studentGroup !== previousGroup) {
			courseCriteriaLibrary.value = [];
			criteriaLibraryLoadedForGroup.value = '';
			criteriaLibrarySelection.value = '';
			criteriaLibraryError.value = '';
		}
		if (!props.open || taskMode.value !== 'reuse') return;
		if (!studentGroup) {
			reusableTasks.value = [];
			selectedReusableTaskName.value = '';
			selectedReusableTaskDetails.value = null;
			taskLibraryError.value = '';
			return;
		}
		if (studentGroup !== previousGroup) {
			selectedReusableTaskName.value = '';
			selectedReusableTaskDetails.value = null;
		}
		void loadReusableTasks();
	}
);

function toDateTimeInput(value?: string | null) {
	if (!value) return '';
	if (value.includes('T')) {
		const [date, timeRaw] = value.split('T');
		const [hour = '00', minute = '00'] = timeRaw.split(':');
		return `${date}T${hour}:${minute}`;
	}
	if (value.includes(' ')) {
		const [date, timeRaw] = value.split(' ');
		const [hour = '00', minute = '00'] = timeRaw.split(':');
		return `${date}T${hour}:${minute}`;
	}
	const date = new Date(value);
	if (Number.isNaN(date.getTime())) return '';
	return formatDateTimeInput(date);
}

function formatDateTimeInput(date: Date) {
	const year = date.getFullYear();
	const month = String(date.getMonth() + 1).padStart(2, '0');
	const day = String(date.getDate()).padStart(2, '0');
	const hours = String(date.getHours()).padStart(2, '0');
	const minutes = String(date.getMinutes()).padStart(2, '0');
	return `${year}-${month}-${day}T${hours}:${minutes}`;
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

function coerceOptionalNumber(value: unknown) {
	const parsed = Number(value);
	return Number.isFinite(parsed) ? parsed : 0;
}

function isEmptyFieldValue(value: unknown) {
	return value === null || value === undefined || value === '';
}

function formatWeightTotal(value: number) {
	return Number.isInteger(value) ? String(value) : value.toFixed(2).replace(/\.?0+$/, '');
}

function normalizeCriteriaRows(rows: TaskCriteriaRow[] | null | undefined) {
	return (rows || [])
		.map(row => ({
			assessment_criteria: String(row?.assessment_criteria || '').trim(),
			criteria_name: String(row?.criteria_name || row?.assessment_criteria || '').trim(),
			criteria_weighting: isEmptyFieldValue(row?.criteria_weighting)
				? null
				: row?.criteria_weighting,
			criteria_max_points: isEmptyFieldValue(row?.criteria_max_points)
				? null
				: row?.criteria_max_points,
			levels: Array.isArray(row?.levels)
				? row.levels
						.map(level => ({ level: String(level?.level || '').trim() }))
						.filter(level => Boolean(level.level))
				: [],
		}))
		.filter(row => Boolean(row.assessment_criteria));
}

async function ensureCourseCriteriaLibraryLoaded(force = false) {
	if (taskMode.value !== 'create' || !form.student_group) return;
	if (!force && criteriaLibraryLoadedForGroup.value === form.student_group) return;
	await listCourseAssessmentCriteriaResource.submit({
		student_group: form.student_group,
	});
}

function addTaskCriterion() {
	const criteriaName = criteriaLibrarySelection.value;
	if (!criteriaName) return;
	const match = courseCriteriaLibrary.value.find(row => row.assessment_criteria === criteriaName);
	if (!match) return;
	if (taskCriteriaRows.value.some(row => row.assessment_criteria === criteriaName)) {
		criteriaLibrarySelection.value = '';
		return;
	}
	taskCriteriaRows.value = [...taskCriteriaRows.value, ...normalizeCriteriaRows([match])];
	if (!form.rubric_scoring_strategy) {
		form.rubric_scoring_strategy = 'Sum Total';
	}
	criteriaLibrarySelection.value = '';
}

function removeTaskCriterion(criteriaName: string) {
	taskCriteriaRows.value = taskCriteriaRows.value.filter(
		row => row.assessment_criteria !== criteriaName
	);
}

/**
 * SPA POST contract: send the payload body directly.
 */
const createTaskResource = createResource({
	url: 'ifitwala_ed.assessment.task_creation_service.create_task_and_delivery',
	method: 'POST',
	auto: false,
	transform: unwrapMessage,
	onError: (err: any) => {
		console.error('[CreateTaskDeliveryOverlay] createTaskResource:error', err);
	},
});
const createTaskDeliveryResource = createResource({
	url: 'ifitwala_ed.api.task.create_task_delivery',
	method: 'POST',
	auto: false,
	transform: unwrapMessage,
	onError: (err: any) => {
		console.error('[CreateTaskDeliveryOverlay] createTaskDeliveryResource:error', err);
	},
});
const listTaskMaterialsResource = createResource({
	url: 'ifitwala_ed.api.materials.list_task_materials',
	method: 'POST',
	auto: false,
	transform: unwrapMessage,
	onSuccess: (payload: any) => {
		taskMaterials.value = Array.isArray(payload?.materials) ? payload.materials : [];
	},
	onError: (err: any) => {
		console.error('[CreateTaskDeliveryOverlay] listTaskMaterials:error', err);
		taskMaterials.value = [];
	},
});
const createTaskReferenceMaterialResource = createResource({
	url: 'ifitwala_ed.api.materials.create_task_reference_material',
	method: 'POST',
	auto: false,
	transform: unwrapMessage,
	onError: (err: any) => {
		console.error('[CreateTaskDeliveryOverlay] createTaskReferenceMaterial:error', err);
	},
});
const removeTaskMaterialResource = createResource({
	url: 'ifitwala_ed.api.materials.remove_task_material',
	method: 'POST',
	auto: false,
	transform: unwrapMessage,
	onError: (err: any) => {
		console.error('[CreateTaskDeliveryOverlay] removeTaskMaterial:error', err);
	},
});
const materialsLoading = computed(() => listTaskMaterialsResource.loading);
const taskLibraryLoading = computed(
	() => searchReusableTasksResource.loading || getReusableTaskResource.loading
);

function parseServerMessages(raw: unknown): string[] {
	if (typeof raw !== 'string' || !raw.trim()) {
		return [];
	}
	try {
		const entries = JSON.parse(raw);
		if (!Array.isArray(entries)) return [];
		return entries
			.map((entry: unknown) => {
				if (typeof entry !== 'string') return String(entry || '');
				try {
					const payload = JSON.parse(entry);
					return typeof payload?.message === 'string' ? payload.message : entry;
				} catch {
					return entry;
				}
			})
			.filter((message: string) => Boolean((message || '').trim()));
	} catch {
		return [];
	}
}

function isTransportOnlyErrorMessage(value: string) {
	const message = String(value || '').trim();
	if (!message) return false;
	return message.includes('/api/method/') && /(?:Validation|Permission)Error\b/.test(message);
}

function extractTaskActionErrorMessage(
	error: unknown,
	fallback = 'Unable to save assigned work right now.'
) {
	if (!error) return fallback;
	if (typeof error === 'string' && error.trim()) return error.trim();

	const maybe = error as Record<string, unknown> & {
		response?: Record<string, unknown>;
	};
	const serverMessages = [
		...parseServerMessages(maybe.response?._server_messages),
		...parseServerMessages(maybe._server_messages),
		...parseServerMessages(maybe.response?._messages),
		...parseServerMessages(maybe._messages),
	].filter(message => !isTransportOnlyErrorMessage(message));
	if (serverMessages.length) {
		return serverMessages.join('\n');
	}

	const candidates = [
		maybe.response?.message,
		maybe.message,
		maybe.response?.statusText,
		maybe.response?.exception,
		maybe.exception,
		maybe.response?.exc,
		maybe.exc,
	];
	for (const candidate of candidates) {
		if (
			typeof candidate === 'string' &&
			candidate.trim() &&
			!isTransportOnlyErrorMessage(candidate)
		) {
			return candidate.trim();
		}
		if (
			candidate &&
			typeof candidate === 'object' &&
			'message' in candidate &&
			typeof (candidate as Record<string, unknown>).message === 'string'
		) {
			const nestedMessage = String((candidate as Record<string, unknown>).message || '').trim();
			if (nestedMessage && !isTransportOnlyErrorMessage(nestedMessage)) {
				return nestedMessage;
			}
		}
	}

	if (error instanceof Error && error.message && !isTransportOnlyErrorMessage(error.message)) {
		return error.message;
	}

	return fallback;
}

function normalizeTaskActionError(message: string) {
	const cleanMessage = String(message || '').trim();
	if (cleanMessage.includes(MISSING_ACTIVE_PLAN_MESSAGE)) {
		return {
			message:
				'This class needs an active Class Teaching Plan before assigned work can be created. Open Class Planning for this class, create or activate the plan, then try again.',
			recovery: 'open-class-planning' as ErrorRecoveryAction,
		};
	}
	if (cleanMessage.includes(SELECT_CLASS_PLAN_MESSAGE)) {
		return {
			message:
				'This class has more than one active Class Teaching Plan. Open Class Planning for this class, choose the correct plan there, then create the task from that surface.',
			recovery: 'open-class-planning' as ErrorRecoveryAction,
		};
	}
	return {
		message: cleanMessage || 'Unable to save assigned work right now.',
		recovery: null as ErrorRecoveryAction,
	};
}

function applyReusableTaskDefaults(task: TaskForDeliveryPayload) {
	form.delivery_mode = (task.default_delivery_mode as DeliveryMode) || 'Assign Only';
	form.allow_feedback = Boolean(task.grading_defaults?.default_allow_feedback);
	form.max_points = '';
	form.rubric_scoring_strategy = '';

	const defaultGradingMode = task.grading_defaults?.default_grading_mode || '';
	if (task.task_type !== 'Quiz' && defaultGradingMode && defaultGradingMode !== 'None') {
		gradingEnabled.value = true;
		form.grading_mode = defaultGradingMode;
		if (defaultGradingMode === 'Points' && task.grading_defaults?.default_max_points != null) {
			form.max_points = String(task.grading_defaults.default_max_points);
		}
		if (defaultGradingMode === 'Criteria') {
			form.rubric_scoring_strategy =
				task.criteria_defaults?.rubric_scoring_strategy ||
				task.grading_defaults?.default_rubric_scoring_strategy ||
				'Sum Total';
		}
	} else {
		gradingEnabled.value = false;
		form.grading_mode = '';
	}

	form.allow_late_submission = false;
}

async function loadReusableTasks() {
	if (taskMode.value !== 'reuse') return;
	if (!form.student_group) {
		reusableTasks.value = [];
		selectedReusableTaskName.value = '';
		selectedReusableTaskDetails.value = null;
		taskLibraryError.value = 'Select a class first to load reusable tasks for its course.';
		return;
	}

	taskLibraryError.value = '';
	await searchReusableTasksResource.submit({
		student_group: form.student_group,
		unit_plan: props.prefillUnitPlan || undefined,
		query: taskLibraryQuery.value.trim() || undefined,
		scope: 'all' as TaskLibraryScope,
	});
}

async function chooseReusableTask(taskName: string) {
	if (!taskName || !form.student_group) return;
	selectedReusableTaskName.value = taskName;
	errorMessage.value = '';
	errorRecovery.value = null;
	await getReusableTaskResource.submit({
		task: taskName,
		student_group: form.student_group,
	});
}

function resetMaterialDraftFields() {
	materialForm.title = '';
	materialForm.description = '';
	materialForm.reference_url = '';
	materialForm.modality = 'Read';
	materialForm.usage_role = 'Reference';
	materialForm.placement_note = '';
	selectedMaterialFile.value = null;
	if (materialFileInput.value) materialFileInput.value.value = '';
}

function resetMaterialComposer() {
	materialComposerMode.value = 'link';
	materialSubmitting.value = false;
	materialError.value = '';
	taskMaterials.value = [];
	removingPlacement.value = null;
	resetMaterialDraftFields();
}

function materialExtension(material: TaskMaterialRow) {
	const rawName = String(material.file_name || '').trim();
	const lastDot = rawName.lastIndexOf('.');
	if (!rawName || lastDot < 0 || lastDot === rawName.length - 1) {
		return '';
	}
	return rawName.slice(lastDot + 1).toLowerCase();
}

function materialExtensionLabel(material: TaskMaterialRow) {
	return materialExtension(material) ? materialExtension(material).toUpperCase() : 'FILE';
}

function isImageMaterial(material: TaskMaterialRow) {
	return (
		material.material_type === 'File' &&
		['jpg', 'jpeg', 'png', 'webp'].includes(materialExtension(material))
	);
}

function isPdfMaterial(material: TaskMaterialRow) {
	return material.material_type === 'File' && materialExtension(material) === 'pdf';
}

function primaryMaterialUrl(material: TaskMaterialRow) {
	return material.preview_url || material.open_url || material.reference_url || null;
}

function showInlineImagePreview(material: TaskMaterialRow) {
	return Boolean(
		material.preview_url && primaryMaterialUrl(material) && isImageMaterial(material)
	);
}

function showPdfPreviewTile(material: TaskMaterialRow) {
	return Boolean(material.preview_url && primaryMaterialUrl(material) && isPdfMaterial(material));
}

function primaryMaterialActionLabel(material: TaskMaterialRow) {
	if (material.preview_url) {
		return 'Preview';
	}
	return material.material_type === 'Reference Link' ? 'Open link' : 'Open';
}

function showMaterialOpenOriginalAction(material: TaskMaterialRow) {
	return Boolean(
		material.material_type === 'File' &&
		material.preview_url &&
		material.open_url &&
		material.open_url !== material.preview_url
	);
}

async function loadTaskMaterials() {
	if (!createdTask.value) return;
	await listTaskMaterialsResource.submit({ task: createdTask.value.task });
}

function onMaterialFileSelected(event: Event) {
	const target = event.target as HTMLInputElement | null;
	const file = target?.files?.[0] || null;
	selectedMaterialFile.value = file;
	materialError.value = '';
	if (file && !materialForm.title.trim()) {
		materialForm.title = file.name;
	}
}

const materialUploadProgressLabel = computed(() =>
	selectedMaterialFile.value?.name
		? `Uploading ${selectedMaterialFile.value.name}`
		: 'Uploading file'
);

async function uploadTaskMaterialFileRequest(task: string): Promise<TaskMaterialRow> {
	if (!selectedMaterialFile.value) {
		throw new Error('Please choose a file first.');
	}

	const formData = new FormData();
	formData.append('task', task);
	formData.append('title', materialForm.title.trim());
	if (materialForm.description.trim())
		formData.append('description', materialForm.description.trim());
	if (materialForm.placement_note.trim())
		formData.append('placement_note', materialForm.placement_note.trim());
	formData.append('modality', materialForm.modality);
	formData.append('usage_role', materialForm.usage_role);
	formData.append('file', selectedMaterialFile.value, selectedMaterialFile.value.name);

	return apiUpload<TaskMaterialRow>(
		'ifitwala_ed.api.materials.upload_task_material_file',
		formData,
		{
			onProgress: progress => {
				materialUploadProgress.value = progress;
			},
		}
	);
}

async function addMaterial() {
	if (!createdTask.value) return;
	if (!canAddMaterial.value) {
		materialError.value =
			materialComposerMode.value === 'link'
				? 'Please provide a title and link.'
				: 'Please provide a title and choose a file.';
		return;
	}

	materialSubmitting.value = true;
	materialError.value = '';
	try {
		if (materialComposerMode.value === 'link') {
			await createTaskReferenceMaterialResource.submit({
				task: createdTask.value.task,
				title: materialForm.title.trim(),
				reference_url: materialForm.reference_url.trim(),
				description: materialForm.description.trim() || undefined,
				modality: materialForm.modality,
				usage_role: materialForm.usage_role,
				placement_note: materialForm.placement_note.trim() || undefined,
			});
		} else {
			await uploadTaskMaterialFileRequest(createdTask.value.task);
		}

		await loadTaskMaterials();
		resetMaterialDraftFields();
		toast.create({ appearance: 'success', message: 'Material added to the task.' });
	} catch (error) {
		const message =
			error instanceof Error ? error.message : 'Unable to add the material right now.';
		materialError.value = message;
		toast.create({ appearance: 'danger', message });
	} finally {
		materialUploadProgress.value = null;
		materialSubmitting.value = false;
	}
}

async function removeMaterial(placement: string) {
	if (!createdTask.value || !placement) return;
	removingPlacement.value = placement;
	try {
		await removeTaskMaterialResource.submit({
			task: createdTask.value.task,
			placement,
		});
		await loadTaskMaterials();
		toast.create({ appearance: 'success', message: 'Material removed from this task.' });
	} catch (error) {
		const message =
			error instanceof Error ? error.message : 'Unable to remove this material right now.';
		materialError.value = message;
		toast.create({ appearance: 'danger', message });
	} finally {
		removingPlacement.value = null;
	}
}

async function submit() {
	if (!canSubmit.value) {
		const missing: string[] = [];
		if (!form.student_group) missing.push('Class');
		if (taskMode.value === 'reuse') {
			if (!selectedReusableTaskDetails.value?.name) missing.push('Task to reuse');
		} else {
			if (!form.title.trim()) missing.push('Title');
			if (isQuizTask.value && !form.quiz_question_bank) missing.push('Quiz question bank');
		}
		if (gradingEnabled.value) {
			if (!form.grading_mode) missing.push('Grading mode');
			if (form.grading_mode === 'Points' && !String(form.max_points || '').trim())
				missing.push('Max points');
			if (form.grading_mode === 'Criteria') {
				if (!form.rubric_scoring_strategy) missing.push('Rubric strategy');
				if (!activeCriteriaRows.value.length) missing.push('Task criteria');
			}
		}

		const msg = missing.length
			? `Please complete: ${missing.join(', ')}.`
			: 'Please complete the required fields.';
		errorMessage.value = msg;
		errorRecovery.value = null;
		toast.create({ appearance: 'warning', message: msg });
		return;
	}

	submitting.value = true;
	errorMessage.value = '';
	errorRecovery.value = null;

	try {
		const deliveryPayload = {
			student_group: form.student_group,
			class_teaching_plan: props.prefillClassTeachingPlan || undefined,
			class_session: props.prefillClassSession || undefined,
			delivery_mode: form.delivery_mode,
			allow_late_submission:
				form.delivery_mode === 'Assign Only' ? 0 : form.allow_late_submission ? 1 : 0,
			group_submission: form.group_submission ? 1 : 0,
			allow_feedback: form.allow_feedback ? 1 : 0,
		} as Record<string, any>;

		if (props.prefillUnitPlan) {
			deliveryPayload.unit_plan = props.prefillUnitPlan;
		}
		if (form.available_from)
			deliveryPayload.available_from = toFrappeDatetime(form.available_from);
		if (form.due_date) deliveryPayload.due_date = toFrappeDatetime(form.due_date);
		if (form.lock_date) deliveryPayload.lock_date = toFrappeDatetime(form.lock_date);

		if (isQuizTask.value) {
			deliveryPayload.grading_mode = form.delivery_mode === 'Assess' ? 'Points' : 'None';
		} else if (gradingEnabled.value) {
			deliveryPayload.grading_mode = form.grading_mode;
			if (form.grading_mode === 'Points') deliveryPayload.max_points = form.max_points;
			if (form.grading_mode === 'Criteria') {
				deliveryPayload.rubric_scoring_strategy = form.rubric_scoring_strategy;
			}
		} else {
			deliveryPayload.grading_mode = 'None';
		}

		let res: unknown;
		if (taskMode.value === 'reuse') {
			deliveryPayload.task = selectedReusableTaskDetails.value?.name;
			res = await createTaskDeliveryResource.submit(deliveryPayload);
		} else {
			const payload: CreateTaskDeliveryInput = {
				...(deliveryPayload as CreateTaskDeliveryInput),
				title: form.title.trim(),
				is_template: form.share_with_course_team ? 1 : 0,
			};

			if (form.instructions.trim()) payload.instructions = form.instructions.trim();
			if (form.task_type) payload.task_type = form.task_type;
			if (isQuizTask.value) {
				payload.quiz_question_bank = form.quiz_question_bank;
				if (form.quiz_question_count)
					payload.quiz_question_count = form.quiz_question_count as any;
				if (form.quiz_time_limit_minutes)
					payload.quiz_time_limit_minutes = form.quiz_time_limit_minutes as any;
				if (form.quiz_max_attempts) payload.quiz_max_attempts = form.quiz_max_attempts as any;
				if (form.quiz_pass_percentage)
					payload.quiz_pass_percentage = form.quiz_pass_percentage as any;
			}
			if (form.grading_mode === 'Criteria') {
				payload.rubric_scoring_strategy = form.rubric_scoring_strategy || undefined;
				payload.criteria_rows = taskCriteriaRows.value.map(row => ({
					assessment_criteria: row.assessment_criteria,
					criteria_weighting: isEmptyFieldValue(row.criteria_weighting)
						? null
						: row.criteria_weighting,
					criteria_max_points: isEmptyFieldValue(row.criteria_max_points)
						? null
						: row.criteria_max_points,
				}));
			}
			res = await createTaskResource.submit(payload);
		}
		const out = res as CreateTaskDeliveryPayload | undefined;

		if (!out?.task || !out?.task_delivery) throw new Error('Unexpected server response.');

		emit('created', out);
		uiSignals.emit(SIGNAL_TASK_DELIVERY_CREATED, {
			task: out.task,
			task_delivery: out.task_delivery,
			student_group: form.student_group || null,
			class_teaching_plan: props.prefillClassTeachingPlan || null,
			unit_plan: props.prefillUnitPlan || null,
			class_session: props.prefillClassSession || null,
		});
		createdTask.value = out;
		createdTaskMode.value = taskMode.value;
		if (taskMode.value === 'create') {
			await loadTaskMaterials();
		}
		toast.create({
			appearance: 'success',
			message:
				taskMode.value === 'create'
					? 'Task created. Add materials or close when done.'
					: 'Assigned work created for this class.',
		});
	} catch (error) {
		console.error('[CreateTaskDeliveryOverlay] submit:error', error);
		const rawMessage = extractTaskActionErrorMessage(error);
		const normalized = normalizeTaskActionError(rawMessage);
		errorMessage.value = normalized.message;
		errorRecovery.value = normalized.recovery;
		toast.create({ appearance: 'danger', message: normalized.message });
	} finally {
		submitting.value = false;
	}
}
</script>
