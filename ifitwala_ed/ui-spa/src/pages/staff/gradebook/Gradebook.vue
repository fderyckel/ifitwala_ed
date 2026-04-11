<template>
	<div class="gradebook-shell min-h-full px-4 pb-8 pt-6 md:px-6 lg:px-8 xl:px-10">
		<div class="mx-auto flex w-full max-w-[1640px] flex-col gap-6 xl:gap-8">
			<header class="flex flex-col gap-5">
				<div class="flex flex-wrap items-center justify-between gap-3">
					<div class="space-y-1">
						<h1 class="text-2xl font-semibold tracking-tight text-ink sm:text-3xl">Gradebook</h1>
						<p class="max-w-3xl text-base text-ink/70">
							Pick a student group, choose a task, and record student outcomes.
						</p>
					</div>
				</div>

				<!-- TOP FILTER BAR -->
				<div
					class="surface-toolbar ifit-filters flex items-center gap-2 overflow-x-auto no-scrollbar rounded-2xl border border-border/80 bg-white/90 px-4 py-3 shadow-sm backdrop-blur sm:px-5"
				>
					<div class="w-48 shrink-0">
						<FormControl
							type="select"
							size="md"
							:options="schoolOptions"
							option-label="school_name"
							option-value="name"
							:model-value="filters.school"
							:disabled="schoolsLoading || !schoolOptions.length"
							placeholder="School"
							@update:modelValue="onSchoolSelected"
						/>
					</div>

					<div class="w-36 shrink-0">
						<FormControl
							type="select"
							size="md"
							:options="yearOptions"
							option-label="label"
							option-value="value"
							:model-value="filters.academic_year"
							:disabled="!yearOptions.length"
							placeholder="Year"
							@update:modelValue="onYearSelected"
						/>
					</div>
					<div class="w-40 shrink-0">
						<FormControl
							type="select"
							size="md"
							:options="programOptions"
							option-label="label"
							option-value="value"
							:model-value="filters.program"
							:disabled="!programOptions.length"
							placeholder="Program"
							@update:modelValue="onProgramSelected"
						/>
					</div>
					<div class="w-40 shrink-0">
						<FormControl
							type="select"
							size="md"
							:options="courseOptions"
							option-label="label"
							option-value="value"
							:model-value="filters.course"
							:disabled="!courseOptions.length"
							placeholder="Course"
							@update:modelValue="onCourseSelected"
						/>
					</div>

					<div class="w-48 shrink-0">
						<FormControl
							type="select"
							size="md"
							:options="groupPickerOptions"
							option-label="label"
							option-value="value"
							:model-value="selectedGroup?.name || null"
							:disabled="!groupPickerOptions.length"
							placeholder="Select group"
							@update:modelValue="onGroupSelectedFromToolbar"
						/>
					</div>

					<div class="ml-auto">
						<Button
							v-if="hasActiveFilters"
							appearance="minimal"
							size="md"
							icon="x"
							@click="resetFilters"
						>
							Reset
						</Button>
					</div>
				</div>
			</header>

			<div class="grid gap-6 xl:gap-8 lg:grid-cols-[minmax(21rem,1fr)_minmax(0,2fr)]">
				<div class="flex flex-col gap-6 xl:gap-8">
					<!-- Student groups Panel -->
					<section
						class="flex flex-col overflow-hidden rounded-2xl border border-border bg-white shadow-sm transition-all hover:shadow-md"
					>
						<div class="border-b border-border/50 bg-gray-50/50 px-4 py-3">
							<div class="flex items-center justify-between gap-2">
								<h2 class="text-sm font-semibold uppercase tracking-wide text-ink/70">
									Student Groups
								</h2>
								<Button
									size="sm"
									appearance="minimal"
									icon="refresh-cw"
									:loading="groupsLoading"
									@click="reloadGroups()"
								/>
							</div>
						</div>

						<div class="flex-1 space-y-2 overflow-y-auto p-4" style="max-height: 24rem">
							<div v-if="groupsLoading" class="space-y-2">
								<div
									v-for="n in 6"
									:key="`group-skeleton-${n}`"
									class="h-14 animate-pulse rounded-lg bg-gray-100"
								/>
							</div>
							<div
								v-else-if="!derivedGroups.length"
								class="flex flex-col items-center justify-center rounded-lg border border-dashed border-border/80 bg-gray-50/50 p-6 text-center text-sm text-ink/60"
							>
								<FeatherIcon name="users" class="mb-2 h-8 w-8 text-ink/20" />
								<p>No groups match filters.</p>
							</div>
							<ul v-else class="space-y-2">
								<li v-for="group in derivedGroups" :key="group.name">
									<button
										type="button"
										class="relative w-full rounded-lg border px-4 py-3 text-left transition-all"
										:class="[
											selectedGroup?.name === group.name
												? 'border-leaf bg-sky/20 text-ink shadow-sm ring-1 ring-leaf/20'
												: 'border-transparent bg-gray-50 hover:bg-gray-100 hover:text-ink',
										]"
										@click="selectGroup(group)"
									>
										<div class="flex items-center justify-between gap-2">
											<p
												class="truncate text-sm font-semibold"
												:class="selectedGroup?.name === group.name ? 'text-ink' : 'text-ink/80'"
											>
												{{ group.label }}
											</p>
											<span
												v-if="group.program || group.course"
												class="inline-flex shrink-0 items-center rounded-full px-2 py-0.5 text-[10px] uppercase tracking-wider"
												:class="
													selectedGroup?.name === group.name
														? 'bg-white/60 text-ink/70'
														: 'bg-gray-200/60 text-ink/50'
												"
											>
												{{ [group.program, group.course].filter(Boolean).join(' • ') }}
											</span>
										</div>
										<p v-if="group.cohort" class="mt-1 truncate text-xs text-ink/50">
											Cohort {{ group.cohort }}
										</p>
									</button>
								</li>
							</ul>
						</div>
					</section>

					<!-- Tasks Panel -->
					<section
						class="flex flex-col overflow-hidden rounded-2xl border border-border bg-white shadow-sm transition-all hover:shadow-md"
					>
						<div class="border-b border-border/50 bg-gray-50/50 px-4 py-3">
							<div class="flex items-center justify-between gap-2">
								<div>
									<h2 class="text-sm font-semibold uppercase tracking-wide text-ink/70">Tasks</h2>
									<p class="text-xs text-ink/50" v-if="selectedGroup">
										{{ selectedGroup.label }}
									</p>
								</div>
							</div>
						</div>

						<!-- Task Filters within Panel -->
						<div
							v-if="selectedGroup && (taskSummaries.length || derivedTasks.length)"
							class="border-b border-border/50 bg-white px-4 py-2"
						>
							<div class="grid grid-cols-2 gap-2">
								<FormControl
									type="select"
									size="sm"
									:options="taskTypeOptions"
									option-label="label"
									option-value="value"
									placeholder="All Types"
									v-model="filters.task_type"
									class="!mb-0"
								/>
								<FormControl
									type="select"
									size="sm"
									:options="deliveryTypeOptions"
									option-label="label"
									option-value="value"
									placeholder="All Modes"
									v-model="filters.delivery_type"
									class="!mb-0"
								/>
							</div>
						</div>

						<div class="flex-1 space-y-3 p-4">
							<div
								v-if="!selectedGroup"
								class="flex flex-col items-center justify-center rounded-lg border border-dashed border-border/80 bg-gray-50/50 p-8 text-center text-sm text-ink/60"
							>
								<FeatherIcon name="arrow-up" class="mb-2 h-8 w-8 text-ink/20" />
								<p>Select a group above.</p>
							</div>

							<div v-else class="space-y-3 overflow-y-auto pr-1" style="max-height: 26rem">
								<div v-if="tasksLoading" class="space-y-2">
									<div
										v-for="n in 4"
										:key="`task-skeleton-${n}`"
										class="h-16 animate-pulse rounded-lg bg-gray-100"
									/>
								</div>
								<div
									v-else-if="!taskSummaries.length"
									class="flex flex-col items-center justify-center rounded-lg border border-dashed border-border/80 bg-gray-50/50 p-6 text-center text-sm text-ink/60"
								>
									<p>No tasks assigned.</p>
								</div>
								<div
									v-else-if="!derivedTasks.length"
									class="flex flex-col items-center justify-center rounded-lg border border-dashed border-border/80 bg-gray-50/50 p-6 text-center text-sm text-ink/60"
								>
									<p>No tasks match filters.</p>
								</div>
								<ul v-else class="space-y-2">
									<li v-for="task in derivedTasks" :key="task.name">
										<button
											type="button"
											class="w-full rounded-lg border px-4 py-3 text-left transition-all"
											:class="[
												selectedTask?.name === task.name
													? 'border-leaf bg-sky/20 text-ink shadow-sm ring-1 ring-leaf/20'
													: 'border-transparent bg-gray-50 hover:bg-gray-100 hover:text-ink',
											]"
											@click="selectTask(task)"
										>
											<div class="flex flex-col gap-1">
												<div class="flex items-start justify-between gap-2">
													<p
														class="text-sm font-semibold"
														:class="selectedTask?.name === task.name ? 'text-ink' : 'text-ink/80'"
													>
														{{ task.title }}
													</p>
												</div>
												<div class="flex flex-col gap-1.5 text-xs text-ink/60">
													<div class="flex items-center gap-2">
														<Badge
															v-if="task.status"
															:variant="task.status === 'Open' ? 'solid' : 'subtle'"
															theme="gray"
														>
															{{ task.status }}
														</Badge>
														<span>Due {{ formatDate(task.due_date) || '—' }}</span>
													</div>
													<div class="flex flex-wrap gap-1 opacity-80">
														<Badge v-if="taskModeBadge(task)" variant="subtle">
															{{ taskModeBadge(task) }}
														</Badge>
														<Badge v-if="task.allow_feedback" variant="subtle">Comment</Badge>
													</div>
												</div>
											</div>
										</button>
									</li>
								</ul>
							</div>
						</div>
					</section>
				</div>

				<!-- Grade entry -->
				<section
					class="flex h-fit flex-col overflow-hidden rounded-2xl border border-border bg-white shadow-sm transition-all hover:shadow-md"
				>
					<div class="border-b border-border/50 bg-gray-50/50 px-6 py-4">
						<div class="flex flex-wrap items-center justify-between gap-4">
							<div class="flex items-center gap-3">
								<h2 class="text-lg font-semibold text-ink">Grade Entry</h2>
								<div
									v-if="showMaxPointsPill(gradebook.task)"
									class="flex items-center gap-2 rounded-full bg-white px-2 py-0.5 text-xs text-ink/60 shadow-sm border border-border/50"
								>
									<span class="font-medium">Max Points:</span>
									<span class="font-bold text-ink">{{ gradebook.task?.max_points || '—' }}</span>
								</div>
							</div>

							<div v-if="gradebook.students.length" class="flex flex-wrap items-center gap-2">
								<span class="text-xs font-medium uppercase tracking-wider text-ink/50"
									>Visible to all:</span
								>
								<Button
									size="sm"
									appearance="minimal"
									:class="
										allStudentsVisible
											? 'bg-sky/30 text-ink font-semibold'
											: 'text-ink/60 hover:text-ink'
									"
									@click="toggleVisibilityGroup('student')"
								>
									Students
								</Button>
								<Button
									size="sm"
									appearance="minimal"
									:class="
										allGuardiansVisible
											? 'bg-sky/30 text-ink font-semibold'
											: 'text-ink/60 hover:text-ink'
									"
									@click="toggleVisibilityGroup('guardian')"
								>
									Guardians
								</Button>
							</div>
						</div>
					</div>

					<div class="min-h-[400px] flex-1 bg-white p-6">
						<div
							v-if="gradebookLoading"
							class="flex h-full flex-col items-center justify-center gap-3 pt-20"
						>
							<Spinner class="h-8 w-8 text-canopy" />
							<p class="text-sm text-ink/50">Loading gradebook...</p>
						</div>

						<div
							v-else-if="!selectedTask"
							class="flex h-full flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed border-border/60 bg-gray-50/30 p-12 text-center text-ink/60"
						>
							<div class="rounded-full bg-gray-100 p-4">
								<FeatherIcon name="check-square" class="h-8 w-8 text-ink/30" />
							</div>
							<p class="text-lg font-medium text-ink">No Task Selected</p>
							<p class="max-w-xs text-sm">
								Choose a task from the left panel to begin entering grades.
							</p>
						</div>

						<div
							v-else-if="!gradebook.students.length"
							class="flex h-full flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed border-border/60 bg-gray-50/30 p-12 text-center text-ink/60"
						>
							<p class="text-lg font-medium text-ink">No Students Assigned</p>
							<p class="max-w-xs text-sm">This task has no students in the roster.</p>
							<Button size="md" appearance="primary" :loading="rosterSyncing" @click="syncRoster">
								Sync roster
							</Button>
						</div>

						<div v-else class="space-y-6">
							<section
								v-if="showsQuizManualReview"
								class="space-y-5 rounded-xl border border-border bg-gray-50/30 p-5"
							>
								<div class="flex flex-wrap items-start justify-between gap-4">
									<div class="space-y-1">
										<h3 class="text-lg font-semibold text-ink">Open-ended Quiz Review</h3>
										<p class="max-w-2xl text-sm text-ink/60">
											Score manually graded quiz responses by question or by student. Each save
											refreshes the official quiz attempt and outcome state on the server.
										</p>
									</div>
									<Button
										size="sm"
										appearance="primary"
										:loading="quizManualSavingVisible"
										:disabled="!visibleDirtyQuizManualRows.length"
										@click="saveVisibleQuizManualRows"
									>
										Save Visible
									</Button>
								</div>

								<div class="flex flex-wrap gap-2">
									<Badge variant="subtle"
										>Manual Items {{ quizManualReview?.summary.manual_item_count || 0 }}</Badge
									>
									<Badge variant="subtle"
										>Pending {{ quizManualReview?.summary.pending_item_count || 0 }}</Badge
									>
									<Badge variant="subtle"
										>Students {{ quizManualReview?.summary.pending_student_count || 0 }}</Badge
									>
									<Badge variant="subtle"
										>Attempts {{ quizManualReview?.summary.pending_attempt_count || 0 }}</Badge
									>
								</div>

								<div class="grid gap-4 lg:grid-cols-[auto_minmax(0,1fr)]">
									<div class="inline-flex rounded-lg border border-border bg-white p-1 shadow-sm">
										<button
											type="button"
											class="rounded-md px-3 py-2 text-sm font-medium transition-all"
											:class="
												quizManualViewMode === 'question'
													? 'bg-leaf text-white shadow-sm'
													: 'text-ink/70 hover:text-ink'
											"
											@click="setQuizManualViewMode('question')"
										>
											By Question
										</button>
										<button
											type="button"
											class="rounded-md px-3 py-2 text-sm font-medium transition-all"
											:class="
												quizManualViewMode === 'student'
													? 'bg-leaf text-white shadow-sm'
													: 'text-ink/70 hover:text-ink'
											"
											@click="setQuizManualViewMode('student')"
										>
											By Student
										</button>
									</div>

									<div class="w-full">
										<FormControl
											v-if="quizManualViewMode === 'question'"
											type="select"
											:options="
												(quizManualReview?.questions || []).map(question => ({
													label: quizManualQuestionLabel(question),
													value: question.quiz_question,
												}))
											"
											:model-value="selectedQuizManualQuestion"
											:disabled="quizManualLoading || !(quizManualReview?.questions || []).length"
											placeholder="Select question"
											@update:modelValue="onQuizManualQuestionSelected"
										/>
										<FormControl
											v-else
											type="select"
											:options="
												(quizManualReview?.students || []).map(student => ({
													label: quizManualStudentLabel(student),
													value: student.student,
												}))
											"
											:model-value="selectedQuizManualStudent"
											:disabled="quizManualLoading || !(quizManualReview?.students || []).length"
											placeholder="Select student"
											@update:modelValue="onQuizManualStudentSelected"
										/>
									</div>
								</div>

								<div
									v-if="quizManualLoading"
									class="flex min-h-[220px] flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-border/70 bg-white/70 p-6 text-center"
								>
									<Spinner class="h-7 w-7 text-canopy" />
									<p class="text-sm text-ink/50">Loading open-ended quiz responses...</p>
								</div>

								<div
									v-else-if="!(quizManualReview?.rows || []).length"
									class="rounded-lg border border-dashed border-border/70 bg-white/70 p-6 text-center text-sm text-ink/60"
								>
									<p class="font-medium text-ink">No open-ended quiz responses to review.</p>
									<p class="mt-1">
										This assessed quiz does not currently have submitted manual-grading items in
										the selected view.
									</p>
								</div>

								<div v-else class="space-y-4">
									<article
										v-for="row in quizManualReview?.rows || []"
										:key="row.item_id"
										class="rounded-xl border border-border bg-white p-5 shadow-sm"
									>
										<div
											class="flex flex-wrap items-start justify-between gap-3 border-b border-border/50 pb-4"
										>
											<div class="space-y-1">
												<p class="text-base font-semibold text-ink">{{ row.title }}</p>
												<div class="flex flex-wrap items-center gap-2 text-xs text-ink/55">
													<span>{{ row.student_name }}</span>
													<span v-if="row.student_id">• {{ row.student_id }}</span>
													<span>• Attempt {{ row.attempt_number || '—' }}</span>
													<span>• {{ row.attempt_status || '—' }}</span>
												</div>
											</div>
											<div class="flex flex-wrap items-center gap-2">
												<Badge v-if="row.requires_manual_grading" variant="subtle" theme="orange">
													Needs Review
												</Badge>
												<Badge v-else variant="subtle" theme="green">Scored</Badge>
												<Badge v-if="row.grading_status" variant="subtle">
													{{ row.grading_status }}
												</Badge>
											</div>
										</div>

										<div class="mt-4 grid gap-5 xl:grid-cols-[minmax(0,2fr)_minmax(16rem,1fr)]">
											<div class="space-y-4">
												<div class="space-y-2">
													<p class="text-xs font-semibold uppercase tracking-wide text-ink/45">
														Prompt
													</p>
													<div
														class="prose prose-sm max-w-none rounded-lg border border-border/60 bg-gray-50/60 px-4 py-3 text-ink"
														v-html="row.prompt_html || '<p>No prompt available.</p>'"
													/>
												</div>

												<div class="space-y-2">
													<p class="text-xs font-semibold uppercase tracking-wide text-ink/45">
														Student Response
													</p>
													<div class="rounded-lg border border-border/60 bg-white px-4 py-3">
														<pre class="whitespace-pre-wrap text-sm text-ink">{{
															quizManualResponseLabel(row)
														}}</pre>
													</div>
												</div>
											</div>

											<div class="space-y-4 rounded-lg border border-border/60 bg-gray-50/50 p-4">
												<div class="space-y-1.5">
													<label
														class="block text-xs font-semibold uppercase tracking-wide text-ink/50"
													>
														Awarded Score
													</label>
													<FormControl
														type="number"
														:min="0"
														:max="1"
														:step="0.1"
														:model-value="quizManualRowStates[row.item_id]?.awarded_score"
														@update:modelValue="onQuizManualScoreChanged(row.item_id, $event)"
													/>
													<p class="text-xs text-ink/50">
														Use 0 to 1 for each manually graded quiz item.
													</p>
												</div>

												<div class="space-y-1 text-xs text-ink/55">
													<p>
														Submitted
														{{ formatDateTime(row.submitted_on) || '—' }}
													</p>
													<p>Question #{{ row.position || '—' }}</p>
												</div>

												<div
													class="flex items-center justify-between border-t border-border/50 pt-3"
												>
													<Badge
														v-if="quizManualRowStates[row.item_id]?.dirty"
														variant="subtle"
														theme="orange"
													>
														Unsaved
													</Badge>
													<span v-else class="text-xs text-ink/40">Saved</span>
													<Button
														size="sm"
														appearance="primary"
														:loading="quizManualRowStates[row.item_id]?.saving"
														:disabled="
															!quizManualRowStates[row.item_id]?.dirty ||
															quizManualRowStates[row.item_id]?.awarded_score === null
														"
														@click="saveQuizManualRow(row.item_id)"
													>
														Save Score
													</Button>
												</div>
											</div>
										</div>
									</article>
								</div>
							</section>

							<template v-else>
								<article
									v-for="student in gradebook.students"
									:key="student.task_student"
									class="group relative rounded-xl border border-border bg-gray-50/30 p-5 transition-all hover:bg-white hover:shadow-md"
								>
									<!-- Current Student Header -->
									<div
										class="flex flex-wrap items-start justify-between gap-4 border-b border-border/40 pb-4 mb-4"
									>
										<div class="flex min-w-0 flex-1 items-center gap-4">
											<img
												:src="student.student_image || DEFAULT_STUDENT_IMAGE"
												alt=""
												class="h-12 w-12 rounded-full border border-white bg-white object-cover shadow-sm"
												loading="lazy"
												@error="onImgError"
											/>
											<div class="min-w-0 flex-1">
												<div class="flex flex-wrap items-center gap-x-4 gap-y-2">
													<p
														class="text-base font-bold text-ink transition-colors hover:text-leaf"
													>
														{{ student.student_name }}
													</p>
													<div
														class="gradebook-student-visibility grid grid-cols-2 gap-x-4 gap-y-2"
													>
														<label
															class="inline-flex cursor-pointer items-center gap-2 text-sm text-ink/70"
														>
															<input
																type="checkbox"
																class="h-4 w-4 rounded border-border/70 text-leaf focus:ring-[rgb(var(--leaf-rgb)/0.35)]"
																:checked="
																	Boolean(studentStates[student.task_student]?.visible_to_student)
																"
																@change="
																	onVisibilityInputChange(
																		student.task_student,
																		'visible_to_student',
																		$event
																	)
																"
															/>
															<span>Visible to Student</span>
														</label>
														<label
															class="inline-flex cursor-pointer items-center gap-2 text-sm text-ink/70"
														>
															<input
																type="checkbox"
																class="h-4 w-4 rounded border-border/70 text-leaf focus:ring-[rgb(var(--leaf-rgb)/0.35)]"
																:checked="
																	Boolean(studentStates[student.task_student]?.visible_to_guardian)
																"
																@change="
																	onVisibilityInputChange(
																		student.task_student,
																		'visible_to_guardian',
																		$event
																	)
																"
															/>
															<span>Visible to Guardian</span>
														</label>
													</div>
												</div>
												<div class="flex items-center gap-2 text-xs text-ink/50">
													<span v-if="student.student_id" class="font-mono">{{
														student.student_id
													}}</span>
													<span>•</span>
													<span
														:class="{
															'text-leaf font-medium':
																studentStates[student.task_student]?.status === 'Finalized' ||
																studentStates[student.task_student]?.status === 'Released',
														}"
													>
														{{ studentStates[student.task_student]?.status || '—' }}
													</span>
												</div>
											</div>
										</div>

										<div class="flex flex-wrap items-center gap-2">
											<Badge
												v-if="showsBooleanResult(gradebook.task)"
												:variant="
													studentStates[student.task_student]?.complete ? 'subtle' : 'outline'
												"
												:theme="studentStates[student.task_student]?.complete ? 'green' : 'gray'"
												:class="
													studentStates[student.task_student]?.complete
														? '!bg-leaf/10 !text-leaf'
														: ''
												"
											>
												<FeatherIcon
													:name="
														studentStates[student.task_student]?.complete
															? 'check'
															: 'minus-circle'
													"
													class="mr-1 h-3 w-3"
												/>
												{{ booleanResultLabel(gradebook.task, student.task_student) }}
											</Badge>

											<div
												v-if="showsScoreSummary(gradebook.task)"
												class="flex items-center rounded-lg bg-white px-3 py-1.5 shadow-sm border border-border/40"
											>
												<span
													class="mr-2 text-xs font-medium uppercase tracking-wider text-ink/40"
												>
													{{ scoreSummaryLabel(gradebook.task) }}
												</span>
												<span class="text-lg font-bold text-ink">
													{{ formatPoints(studentStates[student.task_student]?.mark_awarded) }}
												</span>
											</div>
										</div>
									</div>

									<!-- Grading Controls -->
									<div class="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
										<div class="space-y-4">
											<FormControl
												v-if="showsStatusControl(gradebook.task)"
												type="select"
												label="Status"
												:options="statusOptions"
												option-label="label"
												option-value="value"
												placeholder="Select status"
												:model-value="studentStates[student.task_student]?.status || ''"
												@update:modelValue="onStatusChanged(student.task_student, $event)"
											/>

											<div v-if="isPointsTask(gradebook.task)" class="space-y-1.5">
												<label
													class="block text-xs font-semibold uppercase tracking-wide text-ink/50"
													>Points Awarded</label
												>
												<FormControl
													type="number"
													placeholder="Points"
													:step="0.5"
													:min="0"
													:max="gradebook.task?.max_points || undefined"
													:model-value="studentStates[student.task_student]?.mark_awarded"
													@update:modelValue="onPointsChanged(student.task_student, $event)"
												/>
											</div>

											<div v-if="showsBooleanResult(gradebook.task)" class="space-y-1.5">
												<label
													class="block text-xs font-semibold uppercase tracking-wide text-ink/50"
													>{{ booleanControlLabel(gradebook.task) }}</label
												>
												<div class="grid grid-cols-2 gap-2">
													<button
														type="button"
														class="rounded-md border px-4 py-2 text-sm font-medium transition-all"
														:class="
															studentStates[student.task_student]?.complete
																? '!border-leaf !bg-leaf !text-white'
																: 'border-border/60 bg-white text-ink/70 hover:border-leaf/60 hover:text-leaf'
														"
														@click="setBooleanState(student.task_student, true)"
													>
														{{ booleanPositiveLabel(gradebook.task) }}
													</button>
													<button
														type="button"
														class="rounded-md border px-4 py-2 text-sm font-medium transition-all"
														:class="
															!studentStates[student.task_student]?.complete
																? 'border-slate-300 bg-slate-100 text-ink'
																: 'border-border/60 bg-white text-ink/70 hover:border-leaf/60 hover:text-leaf'
														"
														@click="setBooleanState(student.task_student, false)"
													>
														{{ booleanNegativeLabel(gradebook.task) }}
													</button>
												</div>
											</div>
										</div>

										<!-- Feedback Column -->
										<div
											v-if="supportsFeedback(gradebook.task)"
											class="space-y-1.5 md:col-span-1 lg:col-span-2"
										>
											<label
												class="block text-xs font-semibold uppercase tracking-wide text-ink/50"
											>
												Comment
											</label>
											<FormControl
												type="textarea"
												rows="5"
												placeholder="Add a comment for this student..."
												class="!h-full"
												:model-value="studentStates[student.task_student]?.feedback || ''"
												@update:modelValue="onFeedbackChanged(student.task_student, $event)"
											/>
										</div>
									</div>

									<!-- Criteria Section -->
									<div
										v-if="gradebook.task?.criteria && gradebook.criteria.length"
										class="mt-6 rounded-lg border border-border/60 bg-white p-4 shadow-sm"
									>
										<div class="mb-4 flex items-center justify-between">
											<h4 class="text-sm font-bold text-ink">Criteria Breakdown</h4>
											<Badge
												v-if="studentStates[student.task_student]?.dirtyCriteria"
												variant="subtle"
												theme="orange"
											>
												Unsaved Changes
											</Badge>
										</div>
										<div class="grid gap-4 md:grid-cols-2">
											<div
												v-for="criterion in gradebook.criteria"
												:key="criterion.assessment_criteria"
												class="space-y-2 rounded-md bg-gray-50/50 p-3 ring-1 ring-border/40"
											>
												<div class="flex justify-between">
													<span class="text-sm font-medium text-ink">{{
														criterion.criteria_name
													}}</span>
													<span v-if="criterion.criteria_weighting" class="text-xs text-ink/50"
														>{{ criterion.criteria_weighting }}%</span
													>
												</div>
												<FormControl
													v-if="criterion.levels && criterion.levels.length"
													type="select"
													size="sm"
													:options="criterionLevelOptions(criterion)"
													placeholder="Level Achieved"
													:model-value="
														getCriterionState(student.task_student, criterion.assessment_criteria)
															?.level ?? null
													"
													@update:modelValue="
														level =>
															onCriterionLevelChanged(student.task_student, criterion, level)
													"
												/>
												<FormControl
													v-else
													type="text"
													size="sm"
													placeholder="Level"
													:model-value="
														getCriterionState(student.task_student, criterion.assessment_criteria)
															?.level ?? ''
													"
													@update:modelValue="
														level =>
															onCriterionLevelChanged(student.task_student, criterion, level)
													"
												/>
												<FormControl
													type="number"
													size="sm"
													:step="0.1"
													:min="0"
													placeholder="Points"
													:model-value="
														getCriterionState(student.task_student, criterion.assessment_criteria)
															?.level_points ?? 0
													"
													@update:modelValue="
														value =>
															onCriterionPointsChanged(
																student.task_student,
																criterion.assessment_criteria,
																value
															)
													"
												/>
												<FormControl
													v-if="supportsFeedback(gradebook.task)"
													type="textarea"
													rows="2"
													size="sm"
													placeholder="Criterion feedback"
													:model-value="
														getCriterionState(student.task_student, criterion.assessment_criteria)
															?.feedback || ''
													"
													@update:modelValue="
														value =>
															onCriterionFeedbackChanged(
																student.task_student,
																criterion.assessment_criteria,
																value
															)
													"
												/>
												<div class="flex items-center justify-between text-xs">
													<span class="text-ink/60">Score:</span>
													<span class="font-bold text-ink">
														{{
															formatPoints(
																getCriterionState(
																	student.task_student,
																	criterion.assessment_criteria
																)?.level_points
															)
														}}
													</span>
												</div>
											</div>
										</div>
									</div>

									<!-- Action Footer for Student Card -->
									<div
										class="mt-4 flex items-center justify-between border-t border-border/40 pt-4"
									>
										<p class="text-xs text-ink/40">
											Last updated
											{{
												formatDateTime(studentStates[student.task_student]?.updated_on) || 'Never'
											}}
										</p>
										<div class="flex gap-2">
											<Button
												v-if="gradebook.task?.criteria && gradebook.criteria.length"
												size="sm"
												appearance="white"
												:loading="studentStates[student.task_student]?.savingCriteria"
												:disabled="!studentStates[student.task_student]?.dirtyCriteria"
												@click="saveCriteria(student.task_student)"
											>
												Save Criteria
											</Button>
											<Button
												size="sm"
												appearance="primary"
												:loading="studentStates[student.task_student]?.saving"
												:disabled="!studentStates[student.task_student]?.dirty"
												@click="saveStudent(student.task_student)"
											>
												Save
											</Button>
										</div>
									</div>
								</article>
							</template>
						</div>
					</div>
				</section>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch, onMounted, onBeforeUnmount } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { Button, FormControl, Badge, FeatherIcon, Spinner, toast } from 'frappe-ui';
import { createGradebookService } from '@/lib/services/gradebook/gradebookService';
import { createStudentAttendanceService } from '@/lib/services/studentAttendance/studentAttendanceService';
import type { FetchSchoolFilterContextResponse } from '@/types/contracts/studentAttendance';
import type { GroupSummary as GradebookGroupSummary } from '@/types/contracts/gradebook/fetch_groups';
import type { TaskSummary as GradebookTaskSummary } from '@/types/contracts/gradebook/fetch_group_tasks';
import type {
	TaskPayload as GradebookTaskPayload,
	CriterionPayload as GradebookCriterionPayload,
	StudentRow as GradebookStudentRow,
} from '@/types/contracts/gradebook/get_task_gradebook';
import type {
	Response as GetTaskQuizManualReviewResponse,
	ReviewRow as QuizManualReviewRow,
	QuestionOption as QuizManualQuestionOption,
	StudentOption as QuizManualStudentOption,
} from '@/types/contracts/gradebook/get_task_quiz_manual_review';
import type { Response as UpdateTaskStudentResponse } from '@/types/contracts/gradebook/update_task_student';

/* TYPE DEFINITIONS ------------------------------------------------ */

type GroupSummary = GradebookGroupSummary;
type TaskSummary = GradebookTaskSummary;
type TaskPayload = GradebookTaskPayload;
type CriterionPayload = GradebookCriterionPayload;

interface StudentCriterionState {
	assessment_criteria: string;
	level: string | number | null;
	level_points: number;
	feedback: string;
}

type StudentRow = GradebookStudentRow;

interface StudentState {
	status: string;
	mark_awarded: number | null;
	feedback: string;
	visible_to_student: boolean;
	visible_to_guardian: boolean;
	complete: boolean;
	criteria: StudentCriterionState[];
	updated_on?: string | null;
	dirty: boolean;
	dirtyCriteria: boolean;
	saving: boolean;
	savingCriteria: boolean;
}

interface QuizManualRowState {
	awarded_score: number | null;
	dirty: boolean;
	saving: boolean;
}

/* STATE --------------------------------------------------------- */
const route = useRoute();
const router = useRouter();
const gradebookService = createGradebookService();
const studentAttendanceService = createStudentAttendanceService();

// Filtering state
const filters = reactive({
	school: null as string | null,
	academic_year: null as string | null,
	program: null as string | null,
	course: null as string | null,
	// Task filters
	task_type: null as string | null,
	delivery_type: null as string | null,
});

const defaultSchool = ref<string | null>(null);
const schools = ref<FetchSchoolFilterContextResponse['schools']>([]);
const schoolsLoading = ref(false);
const routeGroupResolving = ref(false);

const groups = ref<GroupSummary[]>([]);
const groupsLoading = ref(false);

const selectedGroup = ref<GroupSummary | null>(null);
const taskSummaries = ref<TaskSummary[]>([]);
const tasksLoading = ref(false);
const selectedTask = ref<TaskSummary | null>(null);
const gradebookLoading = ref(false);
const rosterSyncing = ref(false);
const quizManualLoading = ref(false);
const quizManualSavingVisible = ref(false);

const gradebook = reactive<{
	task: TaskPayload | null;
	criteria: CriterionPayload[];
	students: StudentRow[];
}>({
	task: null,
	criteria: [],
	students: [],
});

const studentStates = reactive<Record<string, StudentState>>({});
const quizManualReview = ref<GetTaskQuizManualReviewResponse | null>(null);
const quizManualViewMode = ref<'question' | 'student'>('question');
const selectedQuizManualQuestion = ref<string | null>(null);
const selectedQuizManualStudent = ref<string | null>(null);
const quizManualRowStates = reactive<Record<string, QuizManualRowState>>({});
const statusOptions = [
	{ label: 'Not Started', value: 'Not Started' },
	{ label: 'In Progress', value: 'In Progress' },
	{ label: 'Needs Review', value: 'Needs Review' },
	{ label: 'Moderated', value: 'Moderated' },
	{ label: 'Finalized', value: 'Finalized' },
	{ label: 'Released', value: 'Released' },
	{ label: 'Not Applicable', value: 'Not Applicable' },
];

const AUTOSAVE_DELAY = 2500;
const studentSaveTimers: Record<string, ReturnType<typeof setTimeout> | null> = {};
const criteriaSaveTimers: Record<string, ReturnType<typeof setTimeout> | null> = {};

/* SERVICES ----------------------------------------------------- */

function showToast(title: string, appearance: 'danger' | 'success' | 'warning' = 'danger') {
	const toastApi = toast as unknown as
		| ((payload: { title: string; appearance?: string }) => void)
		| {
				error?: (message: string) => void;
				create?: (payload: { title: string; appearance?: string }) => void;
		  };
	if (typeof toastApi === 'function') {
		toastApi({ title, appearance });
		return;
	}
	if (appearance === 'danger' && toastApi && typeof toastApi.error === 'function') {
		toastApi.error(title);
		return;
	}
	if (toastApi && typeof toastApi.create === 'function') {
		toastApi.create({ title, appearance });
	}
}

function showDangerToast(title: string) {
	showToast(title, 'danger');
}

function showSuccessToast(title: string) {
	showToast(title, 'success');
}

function onSchoolsLoaded(data: FetchSchoolFilterContextResponse) {
	const rows = Array.isArray(data.schools) ? data.schools : [];
	schools.value = rows;
	const def = data.default_school || null;
	if (def) {
		defaultSchool.value = def;
		// Only set filter if not already set (e.g. via persistence? not implementing persistence for now)
		if (!filters.school) {
			filters.school = def;
		}
	}
}

async function loadSchoolContext() {
	schoolsLoading.value = true;
	try {
		const payload = await studentAttendanceService.fetchSchoolContext({});
		onSchoolsLoaded(payload);
	} catch (error) {
		console.error('Failed to load school context', error);
		showDangerToast('Could not load schools');
	} finally {
		schoolsLoading.value = false;
	}
}

// 2. Groups Loader
async function loadGroups(options: { skipRouteGroupSync?: boolean } = {}) {
	groupsLoading.value = true;
	try {
		const rows = await gradebookService.fetchGroups({
			school: filters.school,
		});

		// If currently selected group is not in list, add it (edge case)
		if (
			selectedGroup.value &&
			selectedGroup.value.name &&
			!rows.find(row => row.name === selectedGroup.value?.name)
		) {
			rows.unshift(selectedGroup.value);
		}
		groups.value = rows;

		if (!options.skipRouteGroupSync) {
			await applyRouteGroupFromQuery();
		}
	} catch (error) {
		console.error('Failed to load student groups', error);
		showDangerToast('Could not load student groups');
	} finally {
		groupsLoading.value = false;
	}
}

function reloadGroups() {
	void loadGroups();
}

// 3. Tasks Loader
async function loadTasks(groupName: string) {
	tasksLoading.value = true;
	try {
		const payload = await gradebookService.fetchGroupTasks({
			student_group: groupName,
		});
		taskSummaries.value = payload?.tasks ?? [];
		applyRouteTaskFromQuery(taskSummaries.value);
	} catch (error) {
		console.error('Failed to load tasks', error);
		showDangerToast('Could not load tasks');
	} finally {
		tasksLoading.value = false;
	}
}

// 4. Gradebook Loader
async function loadGradebook(taskName: string) {
	gradebookLoading.value = true;
	try {
		const payload = await gradebookService.getTaskGradebook({
			task: taskName,
		});
		if (payload) {
			gradebook.task = payload.task;
			gradebook.criteria = payload.criteria || [];
			gradebook.students = payload.students || [];
			initializeStudentStates();
			if (isAssessedQuizTask(payload.task)) {
				await loadQuizManualReview(taskName);
			} else {
				clearQuizManualReviewState();
			}
		}
	} catch (error) {
		console.error('Failed to load gradebook', error);
		showDangerToast('Could not load gradebook');
		clearQuizManualReviewState();
	} finally {
		gradebookLoading.value = false;
	}
}

async function loadQuizManualReview(taskName: string) {
	quizManualLoading.value = true;
	try {
		const payload = await gradebookService.getTaskQuizManualReview({
			task: taskName,
			view_mode: quizManualViewMode.value,
			quiz_question: selectedQuizManualQuestion.value,
			student: selectedQuizManualStudent.value,
		});
		quizManualReview.value = payload;
		quizManualViewMode.value = payload.view_mode;
		selectedQuizManualQuestion.value = payload.selected_question?.quiz_question || null;
		selectedQuizManualStudent.value = payload.selected_student?.student || null;
		initializeQuizManualRowStates();
	} catch (error) {
		console.error('Failed to load quiz manual review', error);
		showDangerToast('Could not load open-ended quiz review');
		clearQuizManualReviewState();
	} finally {
		quizManualLoading.value = false;
	}
}

async function syncRoster() {
	if (!selectedTask.value?.name) {
		showToast('Select a task first.', 'warning');
		return;
	}

	rosterSyncing.value = true;
	try {
		const payload = await gradebookService.repairTaskRoster({
			task: selectedTask.value.name,
		});
		showSuccessToast(payload.message || 'Roster synced.');
		await loadGradebook(selectedTask.value.name);
	} catch (error) {
		console.error('Failed to sync task roster', error);
		showDangerToast('Could not sync the task roster');
	} finally {
		rosterSyncing.value = false;
	}
}

/* COMPUTED - FILTER OPTIONS & DERIVED DATA ---------------------- */

const schoolOptions = computed(() => {
	const base = schools.value.map(s => ({
		label: s.school_name || s.name,
		value: s.name,
	}));
	if (defaultSchool.value) return base;
	// If no default school (admin global), add All option
	return [{ label: 'All Schools', value: null }, ...base];
});

function criterionLevelOptions(criterion: CriterionPayload) {
	return (criterion.levels || []).map(level => ({
		label: level.level,
		value: level.level,
	}));
}

// Derived Groups: Filter raw groups list by top bar selections
const derivedGroups = computed(() => {
	let list = groups.value;
	const f = filters;

	// 1. School Filter
	// Note: instructor with restricted scope might only see 1 school in list.
	// But if they have access to multiple (e.g. descendants), we filter here.
	if (f.school) {
		list = list.filter(g => g.school === f.school);
	}
	// 2. Year Filter
	if (f.academic_year) {
		list = list.filter(g => g.academic_year === f.academic_year);
	}
	// 3. Program Filter
	if (f.program) {
		list = list.filter(g => g.program === f.program);
	}
	// 4. Course Filter
	if (f.course) {
		list = list.filter(g => g.course === f.course);
	}
	return list;
});

const groupPickerOptions = computed(() =>
	derivedGroups.value.map(group => ({
		label: group.label,
		value: group.name,
	}))
);

// Options derived from CURRENT visible groups (after school filter applied)
// This ensures cascading logic: selecting a school reduces available years/programs.
const availableGroupsForOptions = computed(() => {
	let list = groups.value;
	if (filters.school) {
		list = list.filter(g => g.school === filters.school);
	}
	return list;
});

const yearOptions = computed(() => {
	// Unique academic years from available groups
	const years = new Set(availableGroupsForOptions.value.map(g => g.academic_year).filter(Boolean));
	return Array.from(years)
		.sort()
		.reverse()
		.map(y => ({ label: y, value: y }));
});

const programOptions = computed(() => {
	// Filter by year if selected
	let list = availableGroupsForOptions.value;
	if (filters.academic_year) {
		list = list.filter(g => g.academic_year === filters.academic_year);
	}
	const progs = new Set(list.map(g => g.program).filter(Boolean));
	return Array.from(progs)
		.sort()
		.map(p => ({ label: p, value: p }));
});

const courseOptions = computed(() => {
	let list = availableGroupsForOptions.value;
	if (filters.academic_year) {
		list = list.filter(g => g.academic_year === filters.academic_year);
	}
	if (filters.program) {
		list = list.filter(g => g.program === filters.program);
	}
	const courses = new Set(list.map(g => g.course).filter(Boolean));
	return Array.from(courses)
		.sort()
		.map(c => ({ label: c, value: c }));
});

const hasActiveFilters = computed(() => {
	return !!(filters.school || filters.academic_year || filters.program || filters.course);
});

/* TASK FILTERING ------------------------------------------------ */

const derivedTasks = computed(() => {
	let list = taskSummaries.value;
	if (filters.task_type) {
		list = list.filter(t => t.task_type === filters.task_type);
	}
	if (filters.delivery_type) {
		list = list.filter(t => t.delivery_type === filters.delivery_type);
	}
	return list;
});

const taskTypeOptions = computed(() => {
	const types = new Set(taskSummaries.value.map(t => t.task_type).filter(Boolean));
	return [
		{ label: 'All Types', value: null },
		...Array.from(types)
			.sort()
			.map(t => ({ label: t, value: t })),
	];
});

const deliveryTypeOptions = computed(() => {
	const types = new Set(taskSummaries.value.map(t => t.delivery_type).filter(Boolean));
	return [
		{ label: 'All Modes', value: null },
		...Array.from(types)
			.sort()
			.map(t => ({ label: t, value: t })),
	];
});

/* FILTER ACTIONS ------------------------------------------------ */

function onSchoolSelected(val: string | null) {
	filters.school = val;
	// Cascade reset
	filters.academic_year = null;
	filters.program = null;
	filters.course = null;
	void loadGroups();
}

function onYearSelected(val: string | null) {
	filters.academic_year = val;
	filters.program = null;
	filters.course = null;
}

function onProgramSelected(val: string | null) {
	filters.program = val;
	filters.course = null;
}

function onCourseSelected(val: string | null) {
	filters.course = val;
}

function onGroupSelectedFromToolbar(groupName: string | null) {
	if (!groupName) {
		selectGroup(null);
		return;
	}

	const match = derivedGroups.value.find(group => group.name === groupName);
	if (!match) {
		showDangerToast('Selected group is no longer available.');
		return;
	}

	selectGroup(match);
}

function resetFilters() {
	filters.school = defaultSchool.value;
	filters.academic_year = null;
	filters.program = null;
	filters.course = null;
	void loadGroups();
}

function syncFiltersToGroup(group: GroupSummary) {
	filters.school = group.school || null;
	filters.academic_year = group.academic_year || null;
	filters.program = group.program || null;
	filters.course = group.course || null;
}

// Downstream Clearing Logic
// Watch derivedGroups: if selectedGroup is no longer in it, deselect.
watch(derivedGroups, newList => {
	if (selectedGroup.value) {
		const stillVisible = newList.find(g => g.name === selectedGroup.value?.name);
		if (!stillVisible) {
			selectGroup(null); // Clear selection
		}
	}
});

// Watch derivedTasks
watch(derivedTasks, newList => {
	if (selectedTask.value) {
		const stillVisible = newList.find(t => t.name === selectedTask.value?.name);
		if (!stillVisible) {
			selectTask(null); // Clear task selection
		}
	}
});

/* OTHER LOGIC (UNCHANGED MOSTLY) -------------------------------- */

function selectGroup(group: GroupSummary | null) {
	const previousGroup = selectedGroup.value?.name || null;
	selectedGroup.value = group;
	if (previousGroup !== (group?.name || null)) {
		updateRouteTask(null);
	}
	if (group) {
		// Reset task filters when switching group? Only if desired.
		// Let's keep them as sticky filters might be useful.
		updateRouteStudentGroup(group.name);
	} else {
		updateRouteStudentGroup(null);
	}
}

function selectTask(task: TaskSummary | null) {
	selectedTask.value = task;
	updateRouteTask(task?.name || null);
}

/* FORMATTERS & UTILS -------------------------------------------- */

function formatDate(dateStr?: string | null) {
	if (!dateStr) return '';
	return new Date(dateStr).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

function formatDateTime(val?: string | null) {
	if (!val) return '';
	return new Date(val).toLocaleString(undefined, {
		month: 'short',
		day: 'numeric',
		hour: '2-digit',
		minute: '2-digit',
	});
}

function formatPoints(val: number | null | undefined) {
	return typeof val === 'number' ? val : '—';
}

function isPointsTask(task?: TaskPayload | TaskSummary | null) {
	return task?.grading_mode === 'Points';
}

function isBinaryTask(task?: TaskPayload | TaskSummary | null) {
	return task?.grading_mode === 'Binary';
}

function isCompletionTask(task?: TaskPayload | TaskSummary | null) {
	return task?.grading_mode === 'Completion' || task?.delivery_type === 'Assign Only';
}

function isCriteriaTask(task?: TaskPayload | TaskSummary | null) {
	return task?.grading_mode === 'Criteria';
}

function supportsFeedback(task?: TaskPayload | TaskSummary | null) {
	return Boolean(task?.allow_feedback);
}

function showsBooleanResult(task?: TaskPayload | TaskSummary | null) {
	return isBinaryTask(task) || isCompletionTask(task);
}

function showsScoreSummary(task?: TaskPayload | TaskSummary | null) {
	if (isPointsTask(task)) return true;
	if (!isCriteriaTask(task)) return false;
	return task?.rubric_scoring_strategy !== 'Separate Criteria';
}

function showsStatusControl(task?: TaskPayload | TaskSummary | null) {
	return task?.delivery_type === 'Assess';
}

function showMaxPointsPill(task?: TaskPayload | null) {
	return isPointsTask(task) && task?.max_points !== null && task?.max_points !== undefined;
}

function isAssessedQuizTask(task?: TaskPayload | TaskSummary | null) {
	return task?.task_type === 'Quiz' && task?.delivery_type === 'Assess';
}

function scoreSummaryLabel(task?: TaskPayload | TaskSummary | null) {
	return isCriteriaTask(task) ? 'Total' : 'Score';
}

function booleanControlLabel(task?: TaskPayload | TaskSummary | null) {
	return isBinaryTask(task) ? 'Yes / No' : 'Completion';
}

function booleanPositiveLabel(task?: TaskPayload | TaskSummary | null) {
	return isBinaryTask(task) ? 'Yes' : 'Complete';
}

function booleanNegativeLabel(task?: TaskPayload | TaskSummary | null) {
	return isBinaryTask(task) ? 'No' : 'Not complete';
}

function booleanResultLabel(task: TaskPayload | null, taskStudent: string) {
	const state = studentStates[taskStudent];
	if (!state) return '—';
	return state.complete ? booleanPositiveLabel(task) : booleanNegativeLabel(task);
}

function taskModeBadge(task?: TaskSummary | null) {
	if (isCriteriaTask(task)) return 'Criteria';
	if (isPointsTask(task)) return 'Points';
	if (isBinaryTask(task)) return 'Yes/No';
	if (isCompletionTask(task)) return 'Complete';
	if (task?.delivery_type === 'Collect Work') return 'Collect';
	return null;
}

const showsQuizManualReview = computed(() => isAssessedQuizTask(gradebook.task));

const visibleDirtyQuizManualRows = computed(() => {
	return (quizManualReview.value?.rows || []).filter(row => {
		const state = quizManualRowStates[row.item_id];
		return Boolean(state?.dirty && state.awarded_score !== null);
	});
});

const allStudentsVisible = computed(() => {
	if (!gradebook.students.length) return false;
	return gradebook.students.every(student => {
		const state = studentStates[student.task_student];
		return Boolean(state?.visible_to_student);
	});
});
const allGuardiansVisible = computed(() => {
	if (!gradebook.students.length) return false;
	return gradebook.students.every(student => {
		const state = studentStates[student.task_student];
		return Boolean(state?.visible_to_guardian);
	});
});

const DEFAULT_STUDENT_IMAGE = '/assets/ifitwala_ed/images/default_student_image.png';

function currentRouteStudentGroup(): string | null {
	const value = route.query.student_group;
	return typeof value === 'string' && value ? value : null;
}

function currentRouteTask(): string | null {
	const value = route.query.task;
	return typeof value === 'string' && value ? value : null;
}

const pendingRouteGroup = ref<string | null>(currentRouteStudentGroup());
const pendingRouteTask = ref<string | null>(currentRouteTask());

async function findRouteGroup(target: string) {
	const rows = await gradebookService.fetchGroups({
		search: target,
		limit: 20,
	});
	return rows.find(row => row.name === target) || null;
}

async function applyRouteGroupFromQuery() {
	const target = pendingRouteGroup.value;
	if (!target || routeGroupResolving.value) return;

	routeGroupResolving.value = true;
	try {
		const visibleMatch = groups.value.find(row => row.name === target);
		if (visibleMatch) {
			syncFiltersToGroup(visibleMatch);
			selectedGroup.value = visibleMatch;
			pendingRouteGroup.value = null;
			return;
		}

		const resolvedMatch = await findRouteGroup(target);
		if (!resolvedMatch) {
			pendingRouteGroup.value = null;
			showDangerToast('Linked student group is no longer available.');
			return;
		}

		syncFiltersToGroup(resolvedMatch);
		await loadGroups({ skipRouteGroupSync: true });
		selectedGroup.value = groups.value.find(row => row.name === target) || resolvedMatch;
		pendingRouteGroup.value = null;
	} catch (error) {
		console.error('Failed to resolve linked student group', error);
		showDangerToast('Could not load the linked student group');
	} finally {
		routeGroupResolving.value = false;
	}
}

function updateRouteStudentGroup(groupName: string | null) {
	const current = currentRouteStudentGroup();
	if (current === groupName || (!current && !groupName)) {
		return;
	}
	const nextQuery = { ...route.query };
	if (groupName) {
		nextQuery.student_group = groupName;
	} else {
		delete nextQuery.student_group;
	}
	router.replace({ query: nextQuery }).catch(() => {});
}

function applyRouteTaskFromQuery(taskList: TaskSummary[] = taskSummaries.value) {
	const target = pendingRouteTask.value;
	if (!target) return;

	const match = taskList.find(task => task.name === target) || null;
	if (match) {
		selectedTask.value = match;
		pendingRouteTask.value = null;
		return;
	}

	if (!taskList.length) {
		if (tasksLoading.value || !selectedGroup.value) {
			return;
		}
		pendingRouteTask.value = null;
		return;
	}

	pendingRouteTask.value = null;
	showDangerToast('Linked assigned work is no longer available for this class.');
}

function updateRouteTask(taskName: string | null) {
	const current = currentRouteTask();
	if (current === taskName || (!current && !taskName)) {
		return;
	}
	const nextQuery = { ...route.query };
	if (taskName) {
		nextQuery.task = taskName;
	} else {
		delete nextQuery.task;
	}
	router.replace({ query: nextQuery }).catch(() => {});
}

function onImgError(event: Event, fallback?: string) {
	const element = event.target as HTMLImageElement;
	element.onerror = null;
	element.src = fallback || DEFAULT_STUDENT_IMAGE;
}

function normalizeFeedback(value?: string | null) {
	if (!value) return '';
	try {
		if (typeof DOMParser !== 'undefined') {
			const parser = new DOMParser();
			const doc = parser.parseFromString(value, 'text/html');
			const text = doc.body.innerText || doc.body.textContent || '';
			return text.replace(/\u00a0/g, ' ').trim();
		}
	} catch {
		/* fall through to regex cleanup */
	}
	return value
		.replace(/<br\s*\/?>/gi, '\n')
		.replace(/<\/p>/gi, '\n')
		.replace(/<[^>]*>/g, '')
		.replace(/\u00a0/g, ' ')
		.replace(/\n{3,}/g, '\n\n')
		.trim();
}

function clearAllAutosaveTimers() {
	for (const key of Object.keys(studentSaveTimers)) {
		const handle = studentSaveTimers[key];
		if (handle) {
			clearTimeout(handle);
		}
		delete studentSaveTimers[key];
	}
	for (const key of Object.keys(criteriaSaveTimers)) {
		const handle = criteriaSaveTimers[key];
		if (handle) {
			clearTimeout(handle);
		}
		delete criteriaSaveTimers[key];
	}
}

function clearQuizManualReviewState() {
	quizManualReview.value = null;
	quizManualViewMode.value = 'question';
	selectedQuizManualQuestion.value = null;
	selectedQuizManualStudent.value = null;
	quizManualSavingVisible.value = false;
	for (const key of Object.keys(quizManualRowStates)) {
		delete quizManualRowStates[key];
	}
}

function scheduleStudentSave(taskStudent: string) {
	const state = studentStates[taskStudent];
	if (!state) return;

	const existing = studentSaveTimers[taskStudent];
	if (existing) {
		clearTimeout(existing);
	}

	studentSaveTimers[taskStudent] = setTimeout(() => {
		studentSaveTimers[taskStudent] = null;
		if (!state.dirty) {
			return;
		}
		if (state.saving) {
			scheduleStudentSave(taskStudent);
			return;
		}
		void saveStudent(taskStudent);
	}, AUTOSAVE_DELAY);
}

function scheduleCriteriaSave(taskStudent: string) {
	const state = studentStates[taskStudent];
	if (!state) return;

	const existing = criteriaSaveTimers[taskStudent];
	if (existing) {
		clearTimeout(existing);
	}

	criteriaSaveTimers[taskStudent] = setTimeout(() => {
		criteriaSaveTimers[taskStudent] = null;
		if (!state.dirtyCriteria) {
			return;
		}
		if (state.savingCriteria) {
			scheduleCriteriaSave(taskStudent);
			return;
		}
		void saveCriteria(taskStudent);
	}, AUTOSAVE_DELAY);
}

watch(
	() => route.query.student_group,
	() => {
		pendingRouteGroup.value = currentRouteStudentGroup();
		if (pendingRouteGroup.value) {
			void applyRouteGroupFromQuery();
		}
	}
);

watch(
	() => route.query.task,
	() => {
		pendingRouteTask.value = currentRouteTask();
		if (pendingRouteTask.value) {
			applyRouteTaskFromQuery();
		}
	}
);

watch(
	() => selectedGroup.value?.name,
	groupName => {
		taskSummaries.value = [];
		selectedTask.value = null;
		gradebook.task = null;
		gradebook.criteria = [];
		gradebook.students = [];
		clearQuizManualReviewState();
		if (groupName) {
			void loadTasks(groupName);
		} else {
			updateRouteStudentGroup(null);
		}
	}
);

watch(
	() => selectedTask.value?.name,
	taskName => {
		gradebook.task = null;
		gradebook.criteria = [];
		gradebook.students = [];
		clearQuizManualReviewState();
		if (taskName) {
			void loadGradebook(taskName);
		}
	}
);

onMounted(() => {
	void (async () => {
		await loadSchoolContext();
		await loadGroups();
	})();
});

onBeforeUnmount(() => {
	clearAllAutosaveTimers();
	clearQuizManualReviewState();
});

function initializeStudentStates() {
	clearAllAutosaveTimers();
	for (const key of Object.keys(studentStates)) {
		delete studentStates[key];
	}

	for (const student of gradebook.students) {
		studentStates[student.task_student] = {
			status: student.status || 'Not Started',
			mark_awarded: student.mark_awarded,
			feedback: normalizeFeedback(student.feedback),
			visible_to_student: Boolean(student.visible_to_student),
			visible_to_guardian: Boolean(student.visible_to_guardian),
			complete: Boolean(student.complete),
			updated_on: student.updated_on,
			dirty: false,
			dirtyCriteria: false,
			saving: false,
			savingCriteria: false,
			criteria: student.criteria_scores.map(c => ({
				assessment_criteria: c.assessment_criteria,
				level: c.level,
				level_points: c.level_points ?? 0,
				feedback: normalizeFeedback(c.feedback),
			})),
		};
	}
}

function initializeQuizManualRowStates() {
	for (const key of Object.keys(quizManualRowStates)) {
		delete quizManualRowStates[key];
	}

	for (const row of quizManualReview.value?.rows || []) {
		quizManualRowStates[row.item_id] = {
			awarded_score: row.awarded_score,
			dirty: false,
			saving: false,
		};
	}
}

function onStatusChanged(taskStudent: string, value: string) {
	const state = studentStates[taskStudent];
	if (!state || state.status === value) return;
	state.status = value;
	state.dirty = true;
	scheduleStudentSave(taskStudent);
}

function onPointsChanged(taskStudent: string, value: number | null) {
	const state = studentStates[taskStudent];
	if (!state || state.mark_awarded === value) return;
	state.mark_awarded = value;
	state.dirty = true;
	scheduleStudentSave(taskStudent);
}

function setBooleanState(taskStudent: string, value: boolean) {
	const state = studentStates[taskStudent];
	if (!state || state.complete === value) return;
	state.complete = value;
	state.dirty = true;
	scheduleStudentSave(taskStudent);
}

function setVisibility(
	taskStudent: string,
	field: 'visible_to_student' | 'visible_to_guardian',
	value: boolean
) {
	const state = studentStates[taskStudent];
	if (!state || state[field] === value) return;
	state[field] = value;
	state.dirty = true;
	scheduleStudentSave(taskStudent);
}

function onVisibilityInputChange(
	taskStudent: string,
	field: 'visible_to_student' | 'visible_to_guardian',
	event: Event
) {
	const target = event.target as HTMLInputElement | null;
	setVisibility(taskStudent, field, Boolean(target?.checked));
}

function onFeedbackChanged(taskStudent: string, value: string) {
	const state = studentStates[taskStudent];
	if (!state || state.feedback === value) return;
	state.feedback = value;
	state.dirty = true;
	scheduleStudentSave(taskStudent);
}

function getCriterionState(taskStudent: string, criteriaName: string) {
	const state = studentStates[taskStudent];
	return state?.criteria.find(c => c.assessment_criteria === criteriaName);
}

function onCriterionLevelChanged(
	taskStudent: string,
	criterionRow: CriterionPayload,
	levelValue: string | number | null
) {
	const state = studentStates[taskStudent];
	if (!state) return;
	const item = state.criteria.find(
		c => c.assessment_criteria === criterionRow.assessment_criteria
	);
	if (!item) return;

	if (item.level === levelValue) return;

	const levelDef = criterionRow.levels.find(l => l.level === levelValue);
	item.level = levelValue;
	item.level_points = levelDef ? levelDef.points : item.level_points;
	state.dirtyCriteria = true;
	scheduleCriteriaSave(taskStudent);
	if (state.dirty) {
		scheduleStudentSave(taskStudent);
	}
}

function onCriterionPointsChanged(
	taskStudent: string,
	criteriaName: string,
	value: number | null
) {
	const state = studentStates[taskStudent];
	if (!state) return;
	const item = state.criteria.find(c => c.assessment_criteria === criteriaName);
	if (!item) return;
	const nextValue = typeof value === 'number' ? value : 0;
	if (item.level_points === nextValue) return;
	item.level_points = nextValue;
	state.dirtyCriteria = true;
	scheduleCriteriaSave(taskStudent);
	if (state.dirty) {
		scheduleStudentSave(taskStudent);
	}
}

function onCriterionFeedbackChanged(taskStudent: string, criteriaName: string, value: string) {
	const state = studentStates[taskStudent];
	if (!state) return;
	const item = state.criteria.find(c => c.assessment_criteria === criteriaName);
	if (!item || item.feedback === value) return;
	item.feedback = value;
	state.dirtyCriteria = true;
	scheduleCriteriaSave(taskStudent);
	if (state.dirty) {
		scheduleStudentSave(taskStudent);
	}
}

function normalizeManualAwardedScore(value: string | number | null | undefined) {
	if (value === null || value === undefined || value === '') return null;
	const parsed = typeof value === 'number' ? value : Number.parseFloat(String(value));
	return Number.isFinite(parsed) ? parsed : null;
}

function onQuizManualScoreChanged(itemId: string, value: string | number | null) {
	const state = quizManualRowStates[itemId];
	if (!state) return;
	const nextValue = normalizeManualAwardedScore(value);
	if (state.awarded_score === nextValue) return;
	state.awarded_score = nextValue;
	state.dirty = true;
}

function quizManualQuestionLabel(option: QuizManualQuestionOption) {
	return option.pending_item_count
		? `${option.title} (${option.pending_item_count} pending)`
		: option.title;
}

function quizManualStudentLabel(option: QuizManualStudentOption) {
	const suffix = option.student_id ? ` • ${option.student_id}` : '';
	const pending = option.pending_item_count ? ` (${option.pending_item_count} pending)` : '';
	return `${option.student_name}${suffix}${pending}`;
}

function quizManualResponseLabel(row: QuizManualReviewRow) {
	const text = (row.response_text || '').trim();
	if (text) return text;
	if (row.selected_option_labels.length) return row.selected_option_labels.join(', ');
	return 'No response submitted.';
}

async function setQuizManualViewMode(mode: 'question' | 'student') {
	if (quizManualViewMode.value === mode) return;
	quizManualViewMode.value = mode;
	if (mode === 'question') {
		selectedQuizManualStudent.value = null;
	} else {
		selectedQuizManualQuestion.value = null;
	}
	if (selectedTask.value?.name) {
		await loadQuizManualReview(selectedTask.value.name);
	}
}

async function onQuizManualQuestionSelected(value: string | null) {
	selectedQuizManualQuestion.value = value;
	if (selectedTask.value?.name) {
		await loadQuizManualReview(selectedTask.value.name);
	}
}

async function onQuizManualStudentSelected(value: string | null) {
	selectedQuizManualStudent.value = value;
	if (selectedTask.value?.name) {
		await loadQuizManualReview(selectedTask.value.name);
	}
}

async function saveQuizManualRows(itemIds: string[]) {
	if (!selectedTask.value?.name || !itemIds.length) return;

	const grades = itemIds
		.map(itemId => ({
			item_id: itemId,
			awarded_score: quizManualRowStates[itemId]?.awarded_score ?? null,
		}))
		.filter(row => row.awarded_score !== null);
	if (!grades.length) return;

	const uniqueIds = new Set(itemIds);
	itemIds.forEach(itemId => {
		const state = quizManualRowStates[itemId];
		if (state) {
			state.saving = true;
		}
	});

	try {
		await gradebookService.saveTaskQuizManualReview({
			task: selectedTask.value.name,
			grades,
		});
		showSuccessToast(
			uniqueIds.size === 1
				? 'Quiz score saved.'
				: `Saved ${uniqueIds.size} open-ended quiz scores.`
		);
		await loadQuizManualReview(selectedTask.value.name);
	} catch (error) {
		console.error('Failed to save quiz manual review', error);
		showDangerToast('Could not save open-ended quiz scores');
	} finally {
		itemIds.forEach(itemId => {
			const state = quizManualRowStates[itemId];
			if (state) {
				state.saving = false;
			}
		});
	}
}

async function saveQuizManualRow(itemId: string) {
	await saveQuizManualRows([itemId]);
}

async function saveVisibleQuizManualRows() {
	const itemIds = visibleDirtyQuizManualRows.value.map(row => row.item_id);
	if (!itemIds.length) return;
	quizManualSavingVisible.value = true;
	try {
		await saveQuizManualRows(itemIds);
	} finally {
		quizManualSavingVisible.value = false;
	}
}

async function saveStudent(taskStudent: string) {
	const state = studentStates[taskStudent];
	if (!state) return;

	state.saving = true;
	try {
		const payload: Record<string, string | number | boolean | null> = {
			status: state.status,
			visible_to_student: state.visible_to_student,
			visible_to_guardian: state.visible_to_guardian,
		};
		if (isPointsTask(gradebook.task)) {
			payload.mark_awarded = state.mark_awarded;
		}
		if (showsBooleanResult(gradebook.task)) {
			payload.complete = state.complete;
		}
		if (supportsFeedback(gradebook.task)) {
			payload.feedback = state.feedback;
		}
		const doc: UpdateTaskStudentResponse = await gradebookService.updateTaskStudent({
			task_student: taskStudent,
			updates: payload,
		});
		state.dirty = false;
		state.updated_on = doc.updated_on;
	} catch (error) {
		console.error('Save failed', error);
		showDangerToast('Failed to save changes');
	} finally {
		state.saving = false;
		if (state.dirty) {
			scheduleStudentSave(taskStudent);
		}
	}
}

async function saveCriteria(taskStudent: string) {
	const state = studentStates[taskStudent];
	if (!state) return;
	state.savingCriteria = true;
	try {
		const criteriaScores = state.criteria
			.map(c => ({
				assessment_criteria: c.assessment_criteria,
				level: c.level,
				level_points: c.level_points ?? 0,
				feedback: c.feedback,
			}))
			.filter(row => row.assessment_criteria && row.level !== null && row.level !== '');

		if (criteriaScores.length) {
			const doc: UpdateTaskStudentResponse = await gradebookService.updateTaskStudent({
				task_student: taskStudent,
				updates: {
					criteria_scores: criteriaScores,
					...(supportsFeedback(gradebook.task) ? { feedback: state.feedback } : {}),
				},
			});
			if (doc?.updated_on) {
				state.updated_on = doc.updated_on;
			}
		}
		state.dirtyCriteria = false;
	} catch (err) {
		console.error(err);
		showDangerToast('Error saving criteria');
	} finally {
		state.savingCriteria = false;
	}
}

function toggleVisibilityGroup(type: 'student' | 'guardian') {
	const field = type === 'student' ? 'visible_to_student' : 'visible_to_guardian';
	const targetVal = type === 'student' ? !allStudentsVisible.value : !allGuardiansVisible.value;

	gradebook.students.forEach(student => {
		setVisibility(student.task_student, field, targetVal);
	});
}
</script>
