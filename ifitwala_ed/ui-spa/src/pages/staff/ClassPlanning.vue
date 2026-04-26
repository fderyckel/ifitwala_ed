<template>
	<div class="staff-shell space-y-6">
		<section class="overflow-hidden rounded-[2rem] border border-line-soft bg-white shadow-soft">
			<div class="space-y-4 px-6 py-6">
				<RouterLink
					:to="{ name: 'ClassHub', params: { studentGroup } }"
					class="inline-flex items-center gap-2 type-caption text-ink/70 transition hover:text-ink"
				>
					<span>←</span>
					<span>Back to Class Hub</span>
				</RouterLink>
				<div class="page-header">
					<div class="page-header__intro">
						<p class="type-overline text-ink/60">Class Delivery</p>
						<h1 class="mt-2 type-h1 text-canopy">
							{{ surface?.group.title || studentGroup || 'Class Delivery' }}
						</h1>
						<p class="mt-2 max-w-3xl type-meta text-slate-token/80">
							Keep the shared unit backbone intact while adapting pacing, session design, and
							student-visible delivery for this class.
						</p>
					</div>
					<div class="page-header__actions">
						<span class="chip">{{ surface?.group.course || 'Course pending' }}</span>
						<span class="chip">{{ surface?.curriculum.units.length || 0 }} units</span>
						<span class="chip">{{ surface?.curriculum.session_count || 0 }} sessions</span>
						<span class="chip"
							>{{ surface?.curriculum.assigned_work_count || 0 }} assigned work</span
						>
						<span v-if="surface?.teaching_plan?.planning_status" class="chip">
							{{ surface.teaching_plan.planning_status }}
						</span>
					</div>
				</div>
			</div>
		</section>

		<section
			v-if="errorMessage"
			class="rounded-2xl border border-flame/30 bg-[var(--flame)]/5 px-5 py-4"
		>
			<p class="type-body-strong text-flame">Could not load Class Delivery.</p>
			<p class="mt-1 type-caption text-ink/70">{{ errorMessage }}</p>
		</section>

		<section
			v-else-if="loading && !surface"
			class="rounded-2xl border border-line-soft bg-white px-5 py-8"
		>
			<p class="type-body text-ink/70">Loading Class Delivery...</p>
		</section>

		<template v-else-if="surface">
			<section
				v-if="!surface.teaching_plan"
				class="grid gap-6 rounded-[2rem] border border-line-soft bg-white p-6 xl:grid-cols-[minmax(0,18rem),minmax(0,1fr)]"
			>
				<div class="space-y-3">
					<p class="type-overline text-ink/60">Step 1</p>
					<h2 class="type-h2 text-ink">Create Class Delivery</h2>
					<p class="type-body text-ink/80">
						Select the Course Plan this class will use. The shared unit backbone stays intact,
						while pacing, sessions, assigned work, and class resources become class-owned.
					</p>
				</div>

				<div class="space-y-5">
					<div
						v-if="!surface.course_plans.length"
						class="rounded-2xl border border-dashed border-line-soft p-5"
					>
						<p class="type-body-strong text-ink">No course plans are available yet.</p>
						<p class="mt-2 type-caption text-ink/70">
							Create the shared course plan and unit backbone before creating Class Delivery.
						</p>
					</div>

					<template v-else>
						<label class="block space-y-2">
							<span class="type-caption text-ink/70">Governing Course Plan</span>
							<select v-model="draftCoursePlan" class="if-input w-full">
								<option value="">Select a course plan</option>
								<option
									v-for="plan in surface.course_plans"
									:key="plan.course_plan"
									:value="plan.course_plan"
								>
									{{ plan.title }}
								</option>
							</select>
						</label>

						<div class="grid gap-3 md:grid-cols-2">
							<article
								v-for="plan in surface.course_plans"
								:key="plan.course_plan"
								class="rounded-2xl border border-line-soft bg-surface-soft p-4"
							>
								<div class="flex items-start justify-between gap-3">
									<div>
										<p class="type-body-strong text-ink">{{ plan.title }}</p>
										<p class="mt-1 type-caption text-ink/70">
											{{ plan.academic_year || 'No academic year' }}
											<span v-if="plan.cycle_label">· {{ plan.cycle_label }}</span>
										</p>
									</div>
									<span class="chip">{{ plan.plan_status || 'Draft' }}</span>
								</div>
							</article>
						</div>

						<div class="flex flex-wrap gap-3">
							<button
								type="button"
								class="if-action"
								:disabled="!draftCoursePlan || createPending"
								@click="handleCreatePlan"
							>
								{{ createPending ? 'Creating...' : 'Create Class Delivery' }}
							</button>
							<p class="type-caption text-ink/70">
								Students see shared resources once Class Delivery is active.
							</p>
						</div>
					</template>
				</div>
			</section>

			<section
				v-else
				class="grid gap-6 xl:grid-cols-[minmax(0,20rem),minmax(0,1fr)] 2xl:grid-cols-[minmax(0,22rem),minmax(0,1fr)]"
			>
				<aside class="space-y-6 xl:self-start">
					<section class="rounded-[2rem] border border-line-soft bg-white p-5 shadow-soft">
						<div class="space-y-4">
							<div class="flex items-center justify-between gap-3">
								<div>
									<p class="type-overline text-ink/60">Class Delivery</p>
									<h2 class="mt-1 type-h3 text-ink">{{ surface.teaching_plan.title }}</h2>
								</div>
								<span class="chip">{{ surface.teaching_plan.planning_status || 'Draft' }}</span>
							</div>

							<label v-if="surface.class_teaching_plans.length > 1" class="block space-y-2">
								<span class="type-caption text-ink/70">Switch plan</span>
								<select
									:value="surface.resolved.class_teaching_plan || ''"
									class="if-input w-full"
									@change="handlePlanSelectionChange"
								>
									<option
										v-for="plan in surface.class_teaching_plans"
										:key="plan.class_teaching_plan"
										:value="plan.class_teaching_plan"
									>
										{{ plan.title }}
									</option>
								</select>
							</label>

							<label class="block space-y-2">
								<span class="type-caption text-ink/70">Student portal status</span>
								<select v-model="planForm.planning_status" class="if-input w-full">
									<option value="Draft">Draft</option>
									<option value="Active">Active</option>
									<option value="Archived">Archived</option>
								</select>
							</label>

							<label class="block space-y-2">
								<span class="type-caption text-ink/70">Teaching team note</span>
								<textarea
									v-model="planForm.team_note"
									rows="5"
									class="if-input min-h-[8rem] w-full resize-y"
									placeholder="Shared planning note for the teaching team"
								/>
							</label>

							<button
								type="button"
								class="if-action"
								:disabled="planPending"
								@click="handleSavePlan"
							>
								{{ planPending ? 'Saving...' : 'Save Delivery Overview' }}
							</button>

							<RouterLink
								v-if="surface.teaching_plan?.course_plan"
								:to="{
									name: 'staff-course-plan',
									params: { coursePlan: surface.teaching_plan.course_plan },
									query: {
										student_group: studentGroup || undefined,
										unit_plan: selectedUnit?.unit_plan || undefined,
									},
								}"
								class="if-action"
							>
								Open Shared Course Plan
							</RouterLink>
						</div>
					</section>

					<section class="rounded-[2rem] border border-line-soft bg-white p-5 shadow-soft">
						<div class="mb-4 flex items-center justify-between gap-3">
							<div>
								<p class="type-overline text-ink/60">Unit Backbone</p>
								<h2 class="mt-1 type-h3 text-ink">Class-owned pacing</h2>
							</div>
							<span class="chip">{{ surface.curriculum.units.length }} units</span>
						</div>

						<div
							v-if="!surface.curriculum.units.length"
							class="rounded-2xl border border-dashed border-line-soft p-4"
						>
							<p class="type-caption text-ink/70">
								This course plan does not have any governed units yet.
							</p>
						</div>

						<div v-else class="space-y-3">
							<button
								v-for="unit in surface.curriculum.units"
								:key="unit.unit_plan"
								type="button"
								class="w-full rounded-2xl border p-4 text-left transition"
								:class="
									selectedUnit?.unit_plan === unit.unit_plan
										? 'border-jacaranda bg-jacaranda/10 shadow-soft'
										: 'border-line-soft bg-surface-soft hover:border-jacaranda/40'
								"
								@click="selectUnit(unit.unit_plan)"
							>
								<div class="flex items-start justify-between gap-3">
									<div class="min-w-0">
										<p class="type-overline text-ink/60">Unit {{ unit.unit_order || '—' }}</p>
										<p class="mt-1 type-body-strong text-ink">{{ unit.title }}</p>
										<p class="mt-1 type-caption text-ink/70">
											{{ unit.sessions.length }} sessions
										</p>
									</div>
									<span class="chip">{{
										unit.resolved_pacing_status || unit.pacing_status || 'Not Started'
									}}</span>
								</div>
							</button>
						</div>
					</section>
				</aside>

				<div v-if="selectedUnit" class="space-y-6">
					<section class="rounded-[2rem] border border-line-soft bg-white p-6 shadow-soft">
						<div class="grid gap-5 lg:grid-cols-[minmax(0,1fr),auto] lg:items-start">
							<div>
								<p class="type-overline text-ink/60">Selected Unit</p>
								<h2 class="mt-2 type-h2 text-ink">{{ selectedUnit.title }}</h2>
								<p class="mt-2 type-body text-ink/80">
									Plan pacing, class reflections, and teaching focus for this class without
									breaking the shared course sequence.
								</p>
							</div>
							<div class="flex flex-wrap gap-2">
								<span class="chip">Unit {{ selectedUnit.unit_order || '—' }}</span>
								<span class="chip">{{ selectedUnit.sessions.length }} sessions</span>
								<span v-if="selectedUnit.duration" class="chip">{{ selectedUnit.duration }}</span>
								<span v-if="selectedUnit.estimated_duration" class="chip">
									{{ selectedUnit.estimated_duration }}
								</span>
								<span class="chip">{{
									selectedUnit.resolved_pacing_status || unitForm.pacing_status || 'Not Started'
								}}</span>
							</div>
						</div>

						<div class="mt-6 grid gap-4 lg:grid-cols-3">
							<label class="block space-y-2">
								<span class="type-caption text-ink/70">Pacing status</span>
								<select v-model="unitForm.pacing_status" class="if-input w-full">
									<option value="Not Started">Not Started</option>
									<option value="In Progress">In Progress</option>
									<option value="Completed">Completed</option>
									<option value="Hold">Hold</option>
								</select>
							</label>
							<label class="block space-y-2 lg:col-span-2">
								<span class="type-caption text-ink/70">Teacher focus</span>
								<input
									v-model="unitForm.teacher_focus"
									type="text"
									class="if-input w-full"
									placeholder="What matters most for this class inside the unit"
								/>
							</label>
						</div>

						<label class="mt-4 block space-y-2">
							<span class="type-caption text-ink/70">Pacing note</span>
							<textarea
								v-model="unitForm.pacing_note"
								rows="4"
								class="if-input min-h-[7rem] w-full resize-y"
								placeholder="Record adjustments, substitutions, or class-specific constraints"
							/>
						</label>

						<div class="mt-6 space-y-4">
							<div>
								<p class="type-overline text-ink/60">Class Reflection</p>
								<p class="mt-1 type-caption text-ink/70">
									Record what this class needed before, during, and after the unit. These
									reflections are rolled up into the broader unit view for staff.
								</p>
							</div>

							<div class="grid gap-4 xl:grid-cols-2">
								<label class="block space-y-2">
									<span class="type-caption text-ink/70">Prior to the unit</span>
									<textarea
										v-model="unitForm.prior_to_the_unit"
										rows="4"
										class="if-input min-h-[7rem] w-full resize-y"
										placeholder="What this class needed before starting the unit"
									/>
								</label>
								<label class="block space-y-2">
									<span class="type-caption text-ink/70">During the unit</span>
									<textarea
										v-model="unitForm.during_the_unit"
										rows="4"
										class="if-input min-h-[7rem] w-full resize-y"
										placeholder="What changed or surfaced while teaching the unit"
									/>
								</label>
								<label class="block space-y-2">
									<span class="type-caption text-ink/70">What worked well</span>
									<textarea
										v-model="unitForm.what_work_well"
										rows="4"
										class="if-input min-h-[7rem] w-full resize-y"
										placeholder="Approaches, resources, or structures that worked"
									/>
								</label>
								<label class="block space-y-2">
									<span class="type-caption text-ink/70">What didn’t work well</span>
									<textarea
										v-model="unitForm.what_didnt_work_well"
										rows="4"
										class="if-input min-h-[7rem] w-full resize-y"
										placeholder="Where this class struggled or the plan broke down"
									/>
								</label>
							</div>

							<label class="block space-y-2">
								<span class="type-caption text-ink/70">Changes and suggestions</span>
								<textarea
									v-model="unitForm.changes_suggestions"
									rows="4"
									class="if-input min-h-[7rem] w-full resize-y"
									placeholder="What should change the next time this unit is taught"
								/>
							</label>
						</div>

						<div class="mt-4 flex flex-wrap gap-3">
							<button
								type="button"
								class="if-action"
								:disabled="unitPending"
								@click="handleSaveUnit"
							>
								{{ unitPending ? 'Saving...' : 'Save Unit Plan For This Class' }}
							</button>
							<p class="type-caption text-ink/70">
								The unit order remains governed across all classes on this course plan.
							</p>
						</div>
					</section>

					<section class="rounded-[2rem] border border-line-soft bg-white p-6 shadow-soft">
						<div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
							<div>
								<p class="type-overline text-ink/60">Shared Unit Plan</p>
								<h2 class="mt-1 type-h3 text-ink">Curriculum backbone for all classes</h2>
								<p class="mt-2 type-body text-ink/80">
									This is the governed unit context inherited from the course plan, enriched by
									reflections from teaching teams.
								</p>
							</div>
							<div class="flex flex-wrap gap-2">
								<span v-if="selectedUnit.unit_status" class="chip">
									{{ selectedUnit.unit_status }}
								</span>
								<span v-if="selectedUnit.version" class="chip">{{ selectedUnit.version }}</span>
								<span class="chip">{{ selectedUnit.standards.length }} standards</span>
								<span v-if="selectedUnit.class_reflections?.length" class="chip">
									{{ selectedUnit.class_reflections.length }} class reflections
								</span>
							</div>
						</div>

						<div class="mt-6 grid gap-4 xl:grid-cols-2">
							<article
								v-if="selectedUnit.overview"
								class="rounded-2xl border border-line-soft bg-surface-soft p-4"
							>
								<p class="type-overline text-ink/60">Overview and Rationale</p>
								<p class="mt-2 type-body text-ink/80">{{ selectedUnit.overview }}</p>
							</article>
							<article
								v-if="selectedUnit.essential_understanding"
								class="rounded-2xl border border-line-soft bg-surface-soft p-4"
							>
								<p class="type-overline text-ink/60">Essential Understanding</p>
								<p class="mt-2 type-body text-ink/80">
									{{ selectedUnit.essential_understanding }}
								</p>
							</article>
							<article
								v-if="selectedUnit.content"
								class="rounded-2xl border border-line-soft bg-surface-soft p-4"
							>
								<p class="type-overline text-ink/60">Content</p>
								<p class="mt-2 type-body text-ink/80">{{ selectedUnit.content }}</p>
							</article>
							<article
								v-if="selectedUnit.skills"
								class="rounded-2xl border border-line-soft bg-surface-soft p-4"
							>
								<p class="type-overline text-ink/60">Skills</p>
								<p class="mt-2 type-body text-ink/80">{{ selectedUnit.skills }}</p>
							</article>
							<article
								v-if="selectedUnit.concepts"
								class="rounded-2xl border border-line-soft bg-surface-soft p-4"
							>
								<p class="type-overline text-ink/60">Concepts</p>
								<p class="mt-2 type-body text-ink/80">{{ selectedUnit.concepts }}</p>
							</article>
							<article
								v-if="selectedUnit.misconceptions"
								class="rounded-2xl border border-line-soft bg-surface-soft p-4"
							>
								<p class="type-overline text-ink/60">Likely Misconceptions</p>
								<p class="mt-2 type-body text-ink/80">{{ selectedUnit.misconceptions }}</p>
							</article>
						</div>

						<div v-if="selectedUnit.standards.length" class="mt-6 space-y-3">
							<div class="flex items-center justify-between gap-3">
								<h3 class="type-h3 text-ink">Standards Alignment</h3>
								<span class="chip">{{ selectedUnit.standards.length }}</span>
							</div>
							<div class="grid gap-3">
								<article
									v-for="standard in selectedUnit.standards"
									:key="`${selectedUnit.unit_plan}-${standard.standard_code}-${standard.standard_description}`"
									class="rounded-2xl border border-line-soft bg-surface-soft p-4"
								>
									<div class="flex flex-wrap items-center gap-2">
										<p class="type-body-strong text-ink">
											{{ standard.standard_code || 'Standard' }}
										</p>
										<span v-if="standard.coverage_level" class="chip">
											{{ standard.coverage_level }}
										</span>
										<span v-if="standard.alignment_strength" class="chip">
											{{ standard.alignment_strength }}
										</span>
									</div>
									<p v-if="standard.standard_description" class="mt-2 type-body text-ink/80">
										{{ standard.standard_description }}
									</p>
									<p
										v-if="standard.framework_name || standard.strand || standard.substrand"
										class="mt-2 type-caption text-ink/70"
									>
										{{
											[standard.framework_name, standard.strand, standard.substrand]
												.filter(Boolean)
												.join(' · ')
										}}
									</p>
								</article>
							</div>
						</div>

						<div v-if="selectedUnit.shared_reflections?.length" class="mt-6 space-y-3">
							<div class="flex items-center justify-between gap-3">
								<h3 class="type-h3 text-ink">Shared Curriculum Reflections</h3>
								<span class="chip">{{ selectedUnit.shared_reflections.length }}</span>
							</div>
							<div class="grid gap-3 xl:grid-cols-2">
								<article
									v-for="(reflection, index) in selectedUnit.shared_reflections"
									:key="`${selectedUnit.unit_plan}-shared-${index}`"
									class="rounded-2xl border border-line-soft bg-surface-soft p-4"
								>
									<p class="type-caption text-ink/70">
										{{ reflection.academic_year || 'Shared unit reflection' }}
									</p>
									<p v-if="reflection.prior_to_the_unit" class="mt-2 type-body text-ink/80">
										{{ reflection.prior_to_the_unit }}
									</p>
									<p v-if="reflection.during_the_unit" class="mt-2 type-body text-ink/80">
										{{ reflection.during_the_unit }}
									</p>
									<p v-if="reflection.what_work_well" class="mt-2 type-caption text-ink/70">
										Worked well: {{ reflection.what_work_well }}
									</p>
									<p v-if="reflection.changes_suggestions" class="mt-2 type-caption text-ink/70">
										Next change: {{ reflection.changes_suggestions }}
									</p>
								</article>
							</div>
						</div>

						<div v-if="selectedUnit.class_reflections?.length" class="mt-6 space-y-3">
							<div class="flex items-center justify-between gap-3">
								<h3 class="type-h3 text-ink">What Other Classes Learned</h3>
								<span class="chip">{{ selectedUnit.class_reflections.length }}</span>
							</div>
							<div class="grid gap-3 xl:grid-cols-2">
								<article
									v-for="reflection in selectedUnit.class_reflections"
									:key="`${selectedUnit.unit_plan}-${reflection.class_teaching_plan}`"
									class="rounded-2xl border border-line-soft bg-surface-soft p-4"
								>
									<div class="flex flex-wrap items-center gap-2">
										<p class="type-body-strong text-ink">{{ reflection.class_label }}</p>
										<span v-if="reflection.academic_year" class="chip">
											{{ reflection.academic_year }}
										</span>
									</div>
									<p v-if="reflection.prior_to_the_unit" class="mt-2 type-body text-ink/80">
										{{ reflection.prior_to_the_unit }}
									</p>
									<p v-if="reflection.during_the_unit" class="mt-2 type-body text-ink/80">
										{{ reflection.during_the_unit }}
									</p>
									<p v-if="reflection.what_work_well" class="mt-2 type-caption text-ink/70">
										Worked well: {{ reflection.what_work_well }}
									</p>
									<p v-if="reflection.what_didnt_work_well" class="mt-2 type-caption text-ink/70">
										Watch for: {{ reflection.what_didnt_work_well }}
									</p>
									<p v-if="reflection.changes_suggestions" class="mt-2 type-caption text-ink/70">
										Next change: {{ reflection.changes_suggestions }}
									</p>
								</article>
							</div>
						</div>

						<div v-if="selectedUnit.shared_resources.length" class="mt-6 space-y-3">
							<div class="flex items-center justify-between gap-3">
								<h3 class="type-h3 text-ink">Shared Unit Resources</h3>
								<span class="chip">{{ selectedUnit.shared_resources.length }}</span>
							</div>
							<PlanningResourcePanel
								anchor-doctype="Unit Plan"
								:anchor-name="selectedUnit.unit_plan"
								:can-manage="false"
								:show-read-only-notice="false"
								eyebrow="Shared Unit Resources"
								title="Shared resources for this unit"
								description="Inherited governed materials from the shared unit backbone."
								empty-message="No shared unit resources are attached to this unit."
								blocked-message="Select a governed unit before reviewing shared unit resources."
								:resources="selectedUnit.shared_resources"
								enable-attachment-preview
								hide-header
								embedded
							/>
						</div>
					</section>

					<section class="grid gap-6 xl:grid-cols-2">
						<PlanningResourcePanel
							anchor-doctype="Class Teaching Plan"
							:anchor-name="surface.teaching_plan.class_teaching_plan"
							eyebrow="Class-Owned Resources"
							title="Shared across this class delivery"
							description="Keep class-wide links, files, and exemplars where the teaching team already plans."
							empty-message="No class-wide resources shared yet."
							blocked-message="Create Class Delivery before sharing class resources."
							:resources="surface.resources.class_resources"
							enable-attachment-preview
							@changed="loadSurface"
						/>

						<article class="rounded-[2rem] border border-line-soft bg-white p-6 shadow-soft">
							<div class="flex items-center justify-between gap-3">
								<div>
									<p class="type-overline text-ink/60">Assigned Work</p>
									<h2 class="mt-1 type-h3 text-ink">Not tied to one unit or session</h2>
								</div>
								<span class="chip">{{ surface.resources.general_assigned_work.length }}</span>
							</div>

							<div
								v-if="!surface.resources.general_assigned_work.length"
								class="mt-5 rounded-2xl border border-dashed border-line-soft px-4 py-4"
							>
								<p class="type-caption text-ink/70">
									No class-wide assigned work yet. Launch assigned work from a unit or session when
									it is ready.
								</p>
							</div>

							<div v-else class="mt-5 space-y-3">
								<article
									v-for="item in surface.resources.general_assigned_work"
									:key="item.task_delivery"
									class="rounded-2xl border border-line-soft bg-surface-soft p-4"
								>
									<div class="flex flex-wrap items-center gap-2">
										<p class="type-body-strong text-ink">{{ item.title }}</p>
										<span v-if="item.task_type" class="chip">{{ item.task_type }}</span>
										<span v-if="item.delivery_mode" class="chip">{{ item.delivery_mode }}</span>
									</div>
									<p v-if="item.due_date" class="mt-2 type-caption text-ink/70">
										Due {{ item.due_date }}
									</p>
									<div class="mt-3 flex flex-wrap gap-2">
										<button type="button" class="if-action" @click="openGradebook(item)">
											{{ gradebookActionLabel(item) }}
										</button>
									</div>
								</article>
							</div>
						</article>
					</section>

					<section class="rounded-[2rem] border border-line-soft bg-white p-6 shadow-soft">
						<div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
							<div>
								<p class="type-overline text-ink/60">Class Sessions</p>
								<h2 class="mt-1 type-h3 text-ink">Plan what this class will actually do</h2>
							</div>
							<div class="flex flex-wrap gap-3">
								<button type="button" class="if-action" @click="openAssignedWorkOverlay()">
									Assign Work To This Class
								</button>
								<button type="button" class="if-action" @click="startNewSession">
									New Class Session
								</button>
							</div>
						</div>

						<div class="mt-5 grid gap-6 lg:grid-cols-[minmax(0,16rem),minmax(0,1fr)]">
							<div class="space-y-3">
								<button
									v-for="session in selectedUnit.sessions"
									:key="session.class_session"
									type="button"
									class="w-full rounded-2xl border p-4 text-left transition"
									:class="
										selectedSessionId === session.class_session
											? 'border-canopy bg-canopy/10 shadow-soft'
											: 'border-line-soft bg-surface-soft hover:border-canopy/40'
									"
									@click="selectSession(session.class_session)"
								>
									<p class="type-body-strong text-ink">{{ session.title }}</p>
									<p class="mt-1 type-caption text-ink/70">
										{{ session.session_status || 'Draft' }}
										<span v-if="session.session_date">· {{ session.session_date }}</span>
									</p>
								</button>

								<div
									v-if="!selectedUnit.sessions.length"
									class="rounded-2xl border border-dashed border-line-soft p-4 type-caption text-ink/70"
								>
									No sessions planned yet for this unit.
								</div>
							</div>

							<div class="space-y-4 rounded-[1.75rem] border border-line-soft bg-surface-soft p-5">
								<div class="flex items-start justify-between gap-3">
									<div>
										<p class="type-overline text-ink/60">
											{{ selectedSessionId ? 'Edit Session' : 'New Session' }}
										</p>
										<h3 class="mt-1 type-h3 text-ink">
											{{
												selectedSessionId
													? sessionForm.title || 'Untitled session'
													: 'Plan a class session'
											}}
										</h3>
									</div>
									<span class="chip">{{ sessionForm.session_status || 'Draft' }}</span>
								</div>

								<div class="grid gap-4 md:grid-cols-2">
									<label class="block space-y-2 md:col-span-2">
										<span class="type-caption text-ink/70">Session title</span>
										<input
											v-model="sessionForm.title"
											type="text"
											class="if-input w-full"
											placeholder="e.g. Evidence walk and structured discussion"
										/>
									</label>
									<label class="block space-y-2">
										<span class="type-caption text-ink/70">Session status</span>
										<select v-model="sessionForm.session_status" class="if-input w-full">
											<option value="Draft">Draft</option>
											<option value="Planned">Planned</option>
											<option value="In Progress">In Progress</option>
											<option value="Taught">Taught</option>
											<option value="Changed">Changed</option>
											<option value="Canceled">Canceled</option>
										</select>
									</label>
									<label class="block space-y-2">
										<span class="type-caption text-ink/70">Session date</span>
										<input
											v-model="sessionForm.session_date"
											type="date"
											class="if-input w-full"
										/>
									</label>
									<label class="block space-y-2">
										<span class="type-caption text-ink/70">Sequence</span>
										<input
											v-model.number="sessionForm.sequence_index"
											type="number"
											min="1"
											step="1"
											class="if-input w-full"
										/>
									</label>
									<label class="block space-y-2 md:col-span-2">
										<span class="type-caption text-ink/70">Learning goal</span>
										<textarea
											v-model="sessionForm.learning_goal"
											rows="3"
											class="if-input min-h-[6rem] w-full resize-y"
											placeholder="State the learning goal students should understand and act on"
										/>
									</label>
									<label class="block space-y-2 md:col-span-2">
										<span class="type-caption text-ink/70">Teacher note</span>
										<textarea
											v-model="sessionForm.teacher_note"
											rows="4"
											class="if-input min-h-[7rem] w-full resize-y"
											placeholder="Private teacher-facing note for delivery and reflection"
										/>
									</label>
								</div>

								<div class="space-y-3">
									<div class="flex items-center justify-between gap-3">
										<div>
											<p class="type-overline text-ink/60">Session Activities</p>
											<p class="type-caption text-ink/70">
												Capture the flow students will experience in this class.
											</p>
										</div>
										<button type="button" class="if-action" @click="addActivity">
											Add Activity
										</button>
									</div>

									<div
										v-if="!sessionForm.activities.length"
										class="rounded-2xl border border-dashed border-line-soft p-4"
									>
										<p class="type-caption text-ink/70">
											Add teaching steps, checks for understanding, practice, or reflection.
										</p>
									</div>

									<div v-else class="space-y-3">
										<div
											v-for="(activity, index) in sessionForm.activities"
											:key="activity.local_id"
											class="rounded-2xl border border-line-soft bg-white p-4"
										>
											<div class="grid gap-4 md:grid-cols-2">
												<label class="block space-y-2 md:col-span-2">
													<span class="type-caption text-ink/70">Activity title</span>
													<input
														v-model="activity.title"
														type="text"
														class="if-input w-full"
														:placeholder="`Activity ${index + 1}`"
													/>
												</label>
												<label class="block space-y-2">
													<span class="type-caption text-ink/70">Activity type</span>
													<select v-model="activity.activity_type" class="if-input w-full">
														<option value="Discuss">Discuss</option>
														<option value="Practice">Practice</option>
														<option value="Read">Read</option>
														<option value="Watch">Watch</option>
														<option value="Write">Write</option>
														<option value="Collaborate">Collaborate</option>
														<option value="Check for Understanding">
															Check for Understanding
														</option>
														<option value="Reflect">Reflect</option>
														<option value="Assess">Assess</option>
														<option value="Other">Other</option>
													</select>
												</label>
												<label class="block space-y-2">
													<span class="type-caption text-ink/70">Estimated minutes</span>
													<input
														v-model.number="activity.estimated_minutes"
														type="number"
														min="0"
														step="1"
														class="if-input w-full"
													/>
												</label>
												<label class="block space-y-2 md:col-span-2">
													<span class="type-caption text-ink/70">Student direction</span>
													<textarea
														v-model="activity.student_direction"
														rows="2"
														class="if-input min-h-[5rem] w-full resize-y"
													/>
												</label>
												<label class="block space-y-2">
													<span class="type-caption text-ink/70">Teacher prompt</span>
													<textarea
														v-model="activity.teacher_prompt"
														rows="2"
														class="if-input min-h-[5rem] w-full resize-y"
													/>
												</label>
												<label class="block space-y-2">
													<span class="type-caption text-ink/70">Resource note</span>
													<textarea
														v-model="activity.resource_note"
														rows="2"
														class="if-input min-h-[5rem] w-full resize-y"
													/>
												</label>
											</div>

											<div class="mt-3 flex justify-end">
												<button
													type="button"
													class="rounded-full border border-line-soft px-4 py-2 type-button-label text-ink transition hover:border-flame hover:text-flame"
													@click="removeActivity(activity.local_id)"
												>
													Remove Activity
												</button>
											</div>
										</div>
									</div>
								</div>

								<div class="flex flex-wrap gap-3">
									<button
										v-if="selectedSessionId"
										type="button"
										class="if-action"
										@click="
											openAssignedWorkOverlay({
												unitPlan: selectedUnit?.unit_plan || null,
												classSession: selectedSessionId || null,
											})
										"
									>
										Assign Work To This Session
									</button>
									<button
										type="button"
										class="if-action"
										:disabled="sessionPending || !sessionForm.title.trim()"
										@click="handleSaveSession"
									>
										{{
											sessionPending
												? 'Saving...'
												: selectedSessionId
													? 'Save Session'
													: 'Create Session'
										}}
									</button>
									<button
										v-if="selectedSessionId"
										type="button"
										class="rounded-full border border-line-soft px-4 py-2 type-button-label text-ink transition hover:border-ink/30"
										@click="startNewSession"
									>
										Start New Session Draft
									</button>
								</div>

								<div
									v-if="selectedUnit.assigned_work.length"
									class="space-y-3 border-t border-line-soft pt-4"
								>
									<div class="flex items-center justify-between gap-3">
										<div>
											<p class="type-overline text-ink/60">Assigned Work In This Unit</p>
											<p class="type-caption text-ink/70">
												Reusable tasks delivered to this class for the selected unit.
											</p>
										</div>
										<span class="chip">{{ selectedUnit.assigned_work.length }}</span>
									</div>
									<div class="space-y-3">
										<article
											v-for="item in selectedUnit.assigned_work"
											:key="item.task_delivery"
											class="rounded-2xl border border-line-soft bg-white p-4"
										>
											<div class="flex flex-wrap items-center gap-2">
												<p class="type-body-strong text-ink">{{ item.title }}</p>
												<span v-if="item.task_type" class="chip">{{ item.task_type }}</span>
												<span v-if="item.delivery_mode" class="chip">{{
													item.delivery_mode
												}}</span>
											</div>
											<p v-if="item.due_date" class="mt-2 type-caption text-ink/70">
												Due {{ item.due_date }}
											</p>
											<div class="mt-3 flex flex-wrap gap-2">
												<button type="button" class="if-action" @click="openGradebook(item)">
													{{ gradebookActionLabel(item) }}
												</button>
											</div>
										</article>
									</div>
								</div>

								<div class="space-y-3 border-t border-line-soft pt-4">
									<div class="grid gap-6 xl:grid-cols-2">
										<PlanningResourcePanel
											anchor-doctype="Class Session"
											:anchor-name="selectedSessionId || null"
											eyebrow="Session Resources"
											title="Materials for this class session"
											description="Share the exact files and links students should open from the selected session."
											empty-message="No session resources shared yet."
											blocked-message="Create or select a class session before sharing session resources."
											:resources="selectedSessionResources"
											enable-attachment-preview
											@changed="loadSurface"
										/>

										<article
											class="rounded-[2rem] border border-line-soft bg-white p-6 shadow-soft"
										>
											<div class="flex items-center justify-between gap-3">
												<div>
													<p class="type-overline text-ink/60">Session Assigned Work</p>
													<p class="type-caption text-ink/70">
														Assignments launched from the selected class session.
													</p>
												</div>
												<span class="chip">{{ selectedSessionAssignedWork.length }}</span>
											</div>

											<div
												v-if="!selectedSessionAssignedWork.length"
												class="mt-5 rounded-2xl border border-dashed border-line-soft px-4 py-4"
											>
												<p class="type-caption text-ink/70">
													No assigned work is tied to this session yet.
												</p>
											</div>

											<div v-else class="mt-5 space-y-3">
												<article
													v-for="item in selectedSessionAssignedWork"
													:key="item.task_delivery"
													class="rounded-2xl border border-line-soft bg-surface-soft p-4"
												>
													<div class="flex flex-wrap items-center gap-2">
														<p class="type-body-strong text-ink">{{ item.title }}</p>
														<span v-if="item.task_type" class="chip">{{ item.task_type }}</span>
													</div>
													<p v-if="item.due_date" class="mt-2 type-caption text-ink/70">
														Due {{ item.due_date }}
													</p>
													<div class="mt-3 flex flex-wrap gap-2">
														<button type="button" class="if-action" @click="openGradebook(item)">
															{{ gradebookActionLabel(item) }}
														</button>
													</div>
												</article>
											</div>
										</article>
									</div>
								</div>
							</div>
						</div>
					</section>
				</div>

				<section v-else class="rounded-[2rem] border border-line-soft bg-white p-6 shadow-soft">
					<p class="type-body text-ink/70">Select a governed unit to plan this class.</p>
				</section>
			</section>
		</template>
	</div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue';
import { toast } from 'frappe-ui';
import { RouterLink, useRoute, useRouter } from 'vue-router';

import PlanningResourcePanel from '@/components/planning/PlanningResourcePanel.vue';
import { useOverlayStack } from '@/composables/useOverlayStack';
import { SIGNAL_TASK_DELIVERY_CREATED, uiSignals } from '@/lib/uiSignals';
import { normalizePlanningSurfaceError } from '@/lib/planning/planningActionGuards';
import {
	createClassTeachingPlan,
	getStaffClassPlanningSurface,
	saveClassSession,
	saveClassTeachingPlan,
	saveClassTeachingPlanUnit,
} from '@/lib/services/staff/staffTeachingService';
import type {
	Response as StaffClassPlanningSurfaceResponse,
	StaffAssignedWork,
	StaffPlanningActivity,
	StaffPlanningSession,
	StaffPlanningUnit,
} from '@/types/contracts/staff_teaching/get_staff_class_planning_surface';
import type { TaskDeliveryCreatedSignal } from '@/types/tasks';

type EditableActivity = StaffPlanningActivity & {
	local_id: number;
};

const route = useRoute();
const router = useRouter();
const overlay = useOverlayStack();

const surface = ref<StaffClassPlanningSurfaceResponse | null>(null);
const loading = ref(false);
const errorMessage = ref('');

const createPending = ref(false);
const planPending = ref(false);
const unitPending = ref(false);
const sessionPending = ref(false);

const draftCoursePlan = ref('');
const selectedUnitPlan = ref('');
const selectedSessionId = ref('');
const nextActivityId = ref(1);
const loadToken = ref(0);

const planForm = reactive({
	planning_status: 'Draft',
	team_note: '',
});

const unitForm = reactive({
	pacing_status: 'Not Started',
	teacher_focus: '',
	pacing_note: '',
	prior_to_the_unit: '',
	during_the_unit: '',
	what_work_well: '',
	what_didnt_work_well: '',
	changes_suggestions: '',
});

const sessionForm = reactive({
	class_session: '',
	title: '',
	session_status: 'Draft',
	session_date: '',
	sequence_index: null as number | null,
	learning_goal: '',
	teacher_note: '',
	activities: [] as EditableActivity[],
});

const studentGroup = computed(() => String(route.params.studentGroup || '').trim());
const requestedPlan = computed(() =>
	typeof route.query.class_teaching_plan === 'string' ? route.query.class_teaching_plan : ''
);
const requestedUnit = computed(() =>
	typeof route.query.unit_plan === 'string' ? route.query.unit_plan : ''
);

const selectedUnit = computed<StaffPlanningUnit | null>(() => {
	return (
		surface.value?.curriculum.units.find(unit => unit.unit_plan === selectedUnitPlan.value) || null
	);
});

const selectedSessionResources = computed(() => {
	return (
		selectedUnit.value?.sessions.find(session => session.class_session === selectedSessionId.value)
			?.resources || []
	);
});

const selectedSessionAssignedWork = computed(() => {
	return (
		selectedUnit.value?.sessions.find(session => session.class_session === selectedSessionId.value)
			?.assigned_work || []
	);
});

function buildEditableActivity(activity?: StaffPlanningActivity): EditableActivity {
	return {
		local_id: nextActivityId.value++,
		title: activity?.title || '',
		activity_type: activity?.activity_type || 'Other',
		estimated_minutes: activity?.estimated_minutes ?? null,
		sequence_index: activity?.sequence_index ?? null,
		student_direction: activity?.student_direction || '',
		teacher_prompt: activity?.teacher_prompt || '',
		resource_note: activity?.resource_note || '',
	};
}

function syncPlanForm() {
	planForm.planning_status = surface.value?.teaching_plan?.planning_status || 'Draft';
	planForm.team_note = surface.value?.teaching_plan?.team_note || '';
}

function syncUnitForm(unit: StaffPlanningUnit | null) {
	unitForm.pacing_status = unit?.pacing_status || 'Not Started';
	unitForm.teacher_focus = unit?.teacher_focus || '';
	unitForm.pacing_note = unit?.pacing_note || '';
	unitForm.prior_to_the_unit = unit?.prior_to_the_unit || '';
	unitForm.during_the_unit = unit?.during_the_unit || '';
	unitForm.what_work_well = unit?.what_work_well || '';
	unitForm.what_didnt_work_well = unit?.what_didnt_work_well || '';
	unitForm.changes_suggestions = unit?.changes_suggestions || '';
}

function syncSessionForm(session: StaffPlanningSession | null) {
	sessionForm.class_session = session?.class_session || '';
	sessionForm.title = session?.title || '';
	sessionForm.session_status = session?.session_status || 'Draft';
	sessionForm.session_date = session?.session_date || '';
	sessionForm.sequence_index = session?.sequence_index ?? null;
	sessionForm.learning_goal = session?.learning_goal || '';
	sessionForm.teacher_note = session?.teacher_note || '';
	sessionForm.activities = (session?.activities || []).map(activity =>
		buildEditableActivity(activity)
	);
}

function startNewSession() {
	selectedSessionId.value = '';
	syncSessionForm(null);
}

function selectUnit(unitPlan: string) {
	selectedUnitPlan.value = unitPlan;
	const unit = surface.value?.curriculum.units.find(row => row.unit_plan === unitPlan) || null;
	syncUnitForm(unit);
	const firstSession = unit?.sessions[0] || null;
	selectedSessionId.value = firstSession?.class_session || '';
	syncSessionForm(firstSession);
	void router.replace({
		query: {
			...route.query,
			unit_plan: unitPlan || undefined,
		},
	});
}

function selectSession(classSession: string) {
	const session =
		selectedUnit.value?.sessions.find(row => row.class_session === classSession) || null;
	selectedSessionId.value = session?.class_session || '';
	syncSessionForm(session);
}

function openAssignedWorkOverlay(options?: {
	unitPlan?: string | null;
	classSession?: string | null;
}) {
	if (!surface.value?.teaching_plan?.class_teaching_plan) {
		toast.error('Create Class Delivery before assigning work.');
		return;
	}
	if (String(surface.value.teaching_plan.planning_status || '').trim() !== 'Active') {
		toast.error('Set Class Delivery to Active before assigning work.');
		return;
	}
	overlay.open('create-task', {
		prefillStudentGroup: studentGroup.value,
		prefillCourse: surface.value.group.course,
		prefillClassTeachingPlan: surface.value.teaching_plan.class_teaching_plan,
		prefillUnitPlan: options?.unitPlan ?? selectedUnit.value?.unit_plan ?? null,
		prefillClassSession: (options?.classSession ?? selectedSessionId.value) || null,
	});
}

function gradebookActionLabel(item: StaffAssignedWork) {
	const deliveryMode = String(item.delivery_mode || '').trim();
	const gradingMode = String(item.grading_mode || '').trim();
	if (deliveryMode === 'Assign Only' && !gradingMode) {
		return 'Review completion';
	}
	return 'Open gradebook';
}

function openGradebook(item: StaffAssignedWork) {
	void router.push({
		name: 'staff-gradebook',
		query: {
			student_group: studentGroup.value,
			task: item.task_delivery,
		},
	});
}

function applySurfaceSelection(payload: StaffClassPlanningSurfaceResponse) {
	syncPlanForm();

	if (!draftCoursePlan.value && payload.course_plans.length === 1) {
		draftCoursePlan.value = payload.course_plans[0].course_plan;
	}

	const requestedUnitPlan = String(requestedUnit.value || '').trim();
	const resolvedUnitPlan = String(payload.resolved.unit_plan || '').trim();
	const currentUnitStillExists = payload.curriculum.units.some(
		unit => unit.unit_plan === selectedUnitPlan.value
	);
	if (
		requestedUnitPlan &&
		payload.curriculum.units.some(unit => unit.unit_plan === requestedUnitPlan)
	) {
		selectedUnitPlan.value = requestedUnitPlan;
	} else if (
		resolvedUnitPlan &&
		payload.curriculum.units.some(unit => unit.unit_plan === resolvedUnitPlan)
	) {
		selectedUnitPlan.value = resolvedUnitPlan;
	} else if (!currentUnitStillExists) {
		selectedUnitPlan.value = payload.curriculum.units[0]?.unit_plan || '';
	}

	const unit =
		payload.curriculum.units.find(row => row.unit_plan === selectedUnitPlan.value) || null;
	syncUnitForm(unit);

	const currentSessionStillExists = !!unit?.sessions.some(
		session => session.class_session === selectedSessionId.value
	);
	if (!currentSessionStillExists) {
		selectedSessionId.value = unit?.sessions[0]?.class_session || '';
	}

	const session =
		unit?.sessions.find(row => row.class_session === selectedSessionId.value) || null;
	syncSessionForm(session);
}

async function loadSurface() {
	const ticket = loadToken.value + 1;
	loadToken.value = ticket;
	loading.value = true;
	errorMessage.value = '';

	try {
		const payload = await getStaffClassPlanningSurface({
			student_group: studentGroup.value,
			class_teaching_plan: requestedPlan.value || undefined,
		});
		if (ticket !== loadToken.value) return;
		surface.value = payload;
		applySurfaceSelection(payload);
	} catch (error) {
		if (ticket !== loadToken.value) return;
		surface.value = null;
		errorMessage.value = normalizePlanningSurfaceError(error);
	} finally {
		if (ticket === loadToken.value) {
			loading.value = false;
		}
	}
}

async function handleCreatePlan() {
	if (!studentGroup.value || !draftCoursePlan.value) return;
	createPending.value = true;
	try {
		const result = await createClassTeachingPlan({
			student_group: studentGroup.value,
			course_plan: draftCoursePlan.value,
		});
		await router.replace({
			query: {
				...route.query,
				class_teaching_plan: result.class_teaching_plan,
			},
		});
		toast.success('Class Delivery created.');
	} catch (error) {
		toast.error(error instanceof Error ? error.message : 'Could not create Class Delivery.');
	} finally {
		createPending.value = false;
	}
}

async function handleSavePlan() {
	if (!surface.value?.teaching_plan?.class_teaching_plan) return;
	planPending.value = true;
	try {
		await saveClassTeachingPlan({
			class_teaching_plan: surface.value.teaching_plan.class_teaching_plan,
			planning_status: planForm.planning_status,
			team_note: planForm.team_note,
		});
		await loadSurface();
		toast.success('Class Delivery updated.');
	} catch (error) {
		toast.error(error instanceof Error ? error.message : 'Could not save Class Delivery.');
	} finally {
		planPending.value = false;
	}
}

async function handleSaveUnit() {
	if (!surface.value?.teaching_plan?.class_teaching_plan || !selectedUnit.value) return;
	unitPending.value = true;
	try {
		await saveClassTeachingPlanUnit({
			class_teaching_plan: surface.value.teaching_plan.class_teaching_plan,
			unit_plan: selectedUnit.value.unit_plan,
			pacing_status: unitForm.pacing_status,
			teacher_focus: unitForm.teacher_focus,
			pacing_note: unitForm.pacing_note,
			prior_to_the_unit: unitForm.prior_to_the_unit,
			during_the_unit: unitForm.during_the_unit,
			what_work_well: unitForm.what_work_well,
			what_didnt_work_well: unitForm.what_didnt_work_well,
			changes_suggestions: unitForm.changes_suggestions,
		});
		await loadSurface();
		toast.success('Unit plan updated for this class.');
	} catch (error) {
		toast.error(error instanceof Error ? error.message : 'Could not save the class unit plan.');
	} finally {
		unitPending.value = false;
	}
}

async function handleSaveSession() {
	if (!surface.value?.teaching_plan?.class_teaching_plan || !selectedUnit.value) return;
	sessionPending.value = true;
	try {
		const result = await saveClassSession({
			class_teaching_plan: surface.value.teaching_plan.class_teaching_plan,
			unit_plan: selectedUnit.value.unit_plan,
			class_session: sessionForm.class_session || undefined,
			title: sessionForm.title.trim(),
			session_status: sessionForm.session_status,
			session_date: sessionForm.session_date || null,
			sequence_index: sessionForm.sequence_index,
			learning_goal: sessionForm.learning_goal,
			teacher_note: sessionForm.teacher_note,
			activities: sessionForm.activities.map((activity, index) => ({
				title: activity.title,
				activity_type: activity.activity_type,
				estimated_minutes: activity.estimated_minutes,
				sequence_index: activity.sequence_index ?? (index + 1) * 10,
				student_direction: activity.student_direction,
				teacher_prompt: activity.teacher_prompt,
				resource_note: activity.resource_note,
			})),
		});
		selectedSessionId.value = result.class_session;
		await loadSurface();
		toast.success('Class session saved.');
	} catch (error) {
		toast.error(error instanceof Error ? error.message : 'Could not save the class session.');
	} finally {
		sessionPending.value = false;
	}
}

async function handlePlanSelectionChange(event: Event) {
	const target = event.target as HTMLSelectElement | null;
	const value = String(target?.value || '').trim();
	await router.replace({
		query: {
			...route.query,
			class_teaching_plan: value || undefined,
		},
	});
}

function addActivity() {
	sessionForm.activities.push(buildEditableActivity());
}

function removeActivity(localId: number) {
	sessionForm.activities = sessionForm.activities.filter(
		activity => activity.local_id !== localId
	);
}

watch(
	() => [studentGroup.value, requestedPlan.value],
	() => {
		loadSurface();
	},
	{ immediate: true }
);

watch(
	() => requestedUnit.value,
	() => {
		if (!surface.value) return;
		applySurfaceSelection(surface.value);
	}
);

const unsubscribeTaskDeliveryCreated = uiSignals.subscribe<TaskDeliveryCreatedSignal>(
	SIGNAL_TASK_DELIVERY_CREATED,
	payload => {
		const signalGroup = String(payload?.student_group || '').trim();
		if (!signalGroup || signalGroup !== studentGroup.value) return;

		const signalPlan = String(payload?.class_teaching_plan || '').trim();
		const currentPlan = String(surface.value?.teaching_plan?.class_teaching_plan || '').trim();
		if (signalPlan && currentPlan && signalPlan !== currentPlan) return;

		void loadSurface();
	}
);

onBeforeUnmount(() => {
	unsubscribeTaskDeliveryCreated();
});
</script>
