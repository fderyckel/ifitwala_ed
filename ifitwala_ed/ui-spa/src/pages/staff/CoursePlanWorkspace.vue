<template>
	<div class="staff-shell space-y-6">
		<section class="overflow-hidden rounded-[2rem] border border-line-soft bg-white shadow-soft">
			<div class="grid gap-6 px-6 py-6 lg:grid-cols-[minmax(0,1fr),auto] lg:items-end">
				<div class="space-y-4">
					<RouterLink
						:to="{ name: 'staff-course-plan-index' }"
						class="inline-flex items-center gap-2 type-caption text-ink/70 transition hover:text-ink"
					>
						<span>←</span>
						<span>Back to Course Plans</span>
					</RouterLink>
					<div>
						<p class="type-overline text-ink/60">Governed Curriculum</p>
						<h1 class="mt-2 type-h1 text-ink">
							{{ surface?.course_plan.title || coursePlan || 'Course Plan' }}
						</h1>
						<p class="mt-2 max-w-3xl type-body text-ink/80">
							Shape the shared course backbone, keep lesson guidance thin, and build quiz banks
							teachers can assign without leaving the staff SPA.
						</p>
					</div>
				</div>
				<div class="flex flex-wrap gap-2 lg:justify-end">
					<span class="chip">{{ surface?.course_plan.course_name || 'Course pending' }}</span>
					<span class="chip">{{ surface?.curriculum.unit_count || 0 }} units</span>
					<span class="chip"
						>{{ surface?.assessment.quiz_question_banks.length || 0 }} quiz banks</span
					>
					<span class="chip">{{ surface?.course_plan.plan_status || 'Draft' }}</span>
					<span class="chip">{{ canManagePlan ? 'Editable' : 'Read only' }}</span>
				</div>
			</div>
		</section>

		<section
			v-if="errorMessage"
			class="rounded-2xl border border-flame/30 bg-[var(--flame)]/5 px-5 py-4"
		>
			<p class="type-body-strong text-flame">Could not load the shared course plan.</p>
			<p class="mt-1 type-caption text-ink/70">{{ errorMessage }}</p>
		</section>

		<section
			v-else-if="loading && !surface"
			class="rounded-2xl border border-line-soft bg-white px-5 py-8"
		>
			<p class="type-body text-ink/70">Loading shared course plan...</p>
		</section>

		<template v-else-if="surface">
			<section class="rounded-[2rem] border border-line-soft bg-white p-6 shadow-soft">
				<div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
					<div>
						<p class="type-overline text-ink/60">Course Plan Overview</p>
						<h2 class="mt-2 type-h2 text-ink">
							{{ surface.course_plan.course_name || surface.course_plan.course }}
						</h2>
						<p class="mt-2 type-body text-ink/80">
							This shared plan sets the governed backbone every linked class teaching plan uses.
						</p>
					</div>
					<div class="flex flex-wrap gap-2">
						<span v-if="surface.course_plan.course_group" class="chip">
							{{ surface.course_plan.course_group }}
						</span>
						<span v-if="surface.course_plan.academic_year" class="chip">
							{{ surface.course_plan.academic_year }}
						</span>
						<span v-if="surface.course_plan.cycle_label" class="chip">
							{{ surface.course_plan.cycle_label }}
						</span>
					</div>
				</div>

				<div v-if="canManagePlan" class="mt-6 grid gap-4 lg:grid-cols-2">
					<label class="block space-y-2">
						<span class="type-caption text-ink/70">Course Plan Title</span>
						<input
							v-model="coursePlanForm.title"
							type="text"
							class="if-input w-full"
							placeholder="e.g. Biology Semester 1 Plan"
						/>
					</label>
					<label class="block space-y-2">
						<span class="type-caption text-ink/70">Academic Year</span>
						<input
							v-model="coursePlanForm.academic_year"
							type="text"
							class="if-input w-full"
							placeholder="e.g. 2026-2027"
						/>
					</label>
					<label class="block space-y-2">
						<span class="type-caption text-ink/70">Cycle Label</span>
						<input
							v-model="coursePlanForm.cycle_label"
							type="text"
							class="if-input w-full"
							placeholder="e.g. Semester 1"
						/>
					</label>
					<label class="block space-y-2">
						<span class="type-caption text-ink/70">Publishing Status</span>
						<select v-model="coursePlanForm.plan_status" class="if-input w-full">
							<option v-for="option in coursePlanStatusOptions" :key="option" :value="option">
								{{ option }}
							</option>
						</select>
					</label>
					<label class="block space-y-2 lg:col-span-2">
						<span class="type-caption text-ink/70">Summary</span>
						<textarea
							v-model="coursePlanForm.summary"
							rows="5"
							class="if-input min-h-[9rem] w-full resize-y"
							placeholder="State the shared purpose, scope, and non-negotiables for this course plan."
						/>
					</label>
					<div class="flex justify-end lg:col-span-2">
						<button
							type="button"
							class="if-action"
							:disabled="coursePlanPending"
							@click="handleSaveCoursePlan"
						>
							{{ coursePlanPending ? 'Saving...' : 'Save Shared Course Plan' }}
						</button>
					</div>
				</div>

				<div v-else class="mt-6 rounded-2xl border border-line-soft bg-surface-soft p-5">
					<p v-if="surface.course_plan.summary" class="type-body text-ink/80">
						{{ surface.course_plan.summary }}
					</p>
					<p v-else class="type-caption text-ink/70">
						No shared summary has been captured for this course plan yet.
					</p>
				</div>
			</section>

			<section class="grid gap-6 xl:grid-cols-[minmax(0,20rem),minmax(0,1fr)]">
				<aside class="space-y-6 xl:self-start">
					<PlanningResourcePanel
						anchor-doctype="Course Plan"
						:anchor-name="surface.course_plan.course_plan"
						:can-manage="canManagePlan"
						eyebrow="Shared Plan Resources"
						title="Resources for every class using this plan"
						description="Keep governed references, anchor texts, and shared files at the course-plan level."
						empty-message="No shared course-plan resources yet."
						blocked-message="Choose a course plan before sharing resources."
						read-only-message="Only approved curriculum staff can edit shared course-plan resources."
						:resources="surface.resources.course_plan_resources"
						@changed="loadSurface"
					/>

					<section class="rounded-[2rem] border border-line-soft bg-white p-5 shadow-soft">
						<div class="mb-4 flex items-center justify-between gap-3">
							<div>
								<p class="type-overline text-ink/60">Unit Backbone</p>
								<h2 class="mt-1 type-h3 text-ink">Governed sequence</h2>
							</div>
							<span class="chip">{{ surface.curriculum.unit_count }}</span>
						</div>

						<div class="space-y-3">
							<button
								v-for="unit in surface.curriculum.units"
								:key="unit.unit_plan"
								type="button"
								class="w-full rounded-2xl border p-4 text-left transition"
								:class="
									selectedUnit?.unit_plan === unit.unit_plan && !creatingUnit
										? 'border-jacaranda bg-jacaranda/10 shadow-soft'
										: 'border-line-soft bg-surface-soft hover:border-jacaranda/40'
								"
								@click="selectUnit(unit.unit_plan)"
							>
								<div class="flex items-start justify-between gap-3">
									<div class="min-w-0">
										<p class="type-overline text-ink/60">Unit {{ unit.unit_order || '—' }}</p>
										<p class="mt-1 type-body-strong text-ink">{{ unit.title }}</p>
									</div>
									<span class="chip">{{ unit.shared_resources.length }} resources</span>
								</div>
							</button>

							<div
								v-if="!surface.curriculum.units.length"
								class="rounded-2xl border border-dashed border-line-soft p-4"
							>
								<p class="type-caption text-ink/70">
									Add the first unit plan to define the shared curriculum backbone.
								</p>
							</div>
						</div>

						<div v-if="canManagePlan" class="mt-4">
							<button type="button" class="if-action w-full" @click="startNewUnit">
								{{ creatingUnit ? 'Editing New Unit' : 'New Unit Plan' }}
							</button>
						</div>
					</section>
				</aside>

				<section
					v-if="showUnitEditor"
					class="space-y-6 rounded-[2rem] border border-line-soft bg-white p-6 shadow-soft"
				>
					<div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
						<div>
							<p class="type-overline text-ink/60">
								{{ creatingUnit ? 'New Unit Plan' : 'Selected Unit' }}
							</p>
							<h2 class="mt-2 type-h2 text-ink">
								{{ creatingUnit ? 'Draft a governed unit' : selectedUnit?.title || 'Unit Plan' }}
							</h2>
							<p class="mt-2 type-body text-ink/80">
								Keep the unit backbone shared while class teaching plans continue to own pacing,
								sessions, and local delivery choices.
							</p>
						</div>
						<div class="flex flex-wrap gap-2">
							<span v-if="!creatingUnit" class="chip">Unit {{ unitForm.unit_order || '—' }}</span>
							<span v-if="unitForm.unit_status" class="chip">{{ unitForm.unit_status }}</span>
							<span v-if="unitForm.duration" class="chip">{{ unitForm.duration }}</span>
							<span v-if="unitForm.estimated_duration" class="chip">
								{{ unitForm.estimated_duration }}
							</span>
						</div>
					</div>

					<div v-if="canManagePlan" class="grid gap-4 lg:grid-cols-2">
						<label class="block space-y-2">
							<span class="type-caption text-ink/70">Unit Title</span>
							<input
								v-model="unitForm.title"
								type="text"
								class="if-input w-full"
								placeholder="e.g. Cells and Systems"
							/>
						</label>
						<label class="block space-y-2">
							<span class="type-caption text-ink/70">Program</span>
							<input
								v-model="unitForm.program"
								type="text"
								class="if-input w-full"
								placeholder="Optional program"
							/>
						</label>
						<label class="block space-y-2">
							<span class="type-caption text-ink/70">Unit Code</span>
							<input
								v-model="unitForm.unit_code"
								type="text"
								class="if-input w-full"
								placeholder="Optional unit code"
							/>
						</label>
						<label class="block space-y-2">
							<span class="type-caption text-ink/70">Unit Order</span>
							<input
								v-model.number="unitForm.unit_order"
								type="number"
								min="1"
								step="1"
								class="if-input w-full"
							/>
						</label>
						<label class="block space-y-2">
							<span class="type-caption text-ink/70">Unit Status</span>
							<select v-model="unitForm.unit_status" class="if-input w-full">
								<option v-for="option in unitStatusOptions" :key="option" :value="option">
									{{ option }}
								</option>
							</select>
						</label>
						<label class="block space-y-2">
							<span class="type-caption text-ink/70">Version</span>
							<input
								v-model="unitForm.version"
								type="text"
								class="if-input w-full"
								placeholder="Optional version"
							/>
						</label>
						<label class="block space-y-2">
							<span class="type-caption text-ink/70">Duration</span>
							<input
								v-model="unitForm.duration"
								type="text"
								class="if-input w-full"
								placeholder="e.g. 6 weeks"
							/>
						</label>
						<label class="block space-y-2">
							<span class="type-caption text-ink/70">Estimated Duration</span>
							<input
								v-model="unitForm.estimated_duration"
								type="text"
								class="if-input w-full"
								placeholder="e.g. 24 GLH"
							/>
						</label>
						<label
							class="flex items-center gap-3 rounded-2xl border border-line-soft bg-surface-soft px-4 py-4 lg:col-span-2"
						>
							<input v-model="unitForm.is_published" type="checkbox" class="h-4 w-4" />
							<div>
								<p class="type-body-strong text-ink">Published for class inheritance</p>
								<p class="type-caption text-ink/70">
									Use this when the governed unit is ready for linked classes to inherit.
								</p>
							</div>
						</label>
						<label class="block space-y-2 lg:col-span-2">
							<span class="type-caption text-ink/70">Overview & Rationale</span>
							<textarea
								v-model="unitForm.overview"
								rows="4"
								class="if-input min-h-[8rem] w-full resize-y"
								placeholder="State the unit arc, rationale, and what makes this backbone important."
							/>
						</label>
						<label class="block space-y-2 lg:col-span-2">
							<span class="type-caption text-ink/70">Essential Understanding</span>
							<textarea
								v-model="unitForm.essential_understanding"
								rows="4"
								class="if-input min-h-[8rem] w-full resize-y"
								placeholder="Capture the shared understanding every class should build."
							/>
						</label>
						<label class="block space-y-2 lg:col-span-2">
							<span class="type-caption text-ink/70">Likely Misconceptions</span>
							<textarea
								v-model="unitForm.misconceptions"
								rows="4"
								class="if-input min-h-[8rem] w-full resize-y"
								placeholder="List likely misunderstandings students may bring into the unit."
							/>
						</label>
						<label class="block space-y-2">
							<span class="type-caption text-ink/70">Content</span>
							<textarea
								v-model="unitForm.content"
								rows="4"
								class="if-input min-h-[8rem] w-full resize-y"
								placeholder="What should students know?"
							/>
						</label>
						<label class="block space-y-2">
							<span class="type-caption text-ink/70">Skills</span>
							<textarea
								v-model="unitForm.skills"
								rows="4"
								class="if-input min-h-[8rem] w-full resize-y"
								placeholder="What should students be able to do?"
							/>
						</label>
						<label class="block space-y-2 lg:col-span-2">
							<span class="type-caption text-ink/70">Concepts</span>
							<textarea
								v-model="unitForm.concepts"
								rows="4"
								class="if-input min-h-[8rem] w-full resize-y"
								placeholder="Which big ideas or concepts should anchor the unit?"
							/>
						</label>
					</div>

					<div v-else class="grid gap-4 lg:grid-cols-2">
						<div
							v-if="selectedUnit?.overview"
							class="rounded-2xl border border-line-soft bg-surface-soft p-4"
						>
							<p class="type-overline text-ink/60">Overview</p>
							<p class="mt-2 type-body text-ink/80">{{ selectedUnit.overview }}</p>
						</div>
						<div
							v-if="selectedUnit?.essential_understanding"
							class="rounded-2xl border border-line-soft bg-surface-soft p-4"
						>
							<p class="type-overline text-ink/60">Essential Understanding</p>
							<p class="mt-2 type-body text-ink/80">
								{{ selectedUnit.essential_understanding }}
							</p>
						</div>
						<div
							v-if="selectedUnit?.content"
							class="rounded-2xl border border-line-soft bg-surface-soft p-4"
						>
							<p class="type-overline text-ink/60">Content</p>
							<p class="mt-2 type-body text-ink/80">{{ selectedUnit.content }}</p>
						</div>
						<div
							v-if="selectedUnit?.skills"
							class="rounded-2xl border border-line-soft bg-surface-soft p-4"
						>
							<p class="type-overline text-ink/60">Skills</p>
							<p class="mt-2 type-body text-ink/80">{{ selectedUnit.skills }}</p>
						</div>
						<div
							v-if="selectedUnit?.concepts"
							class="rounded-2xl border border-line-soft bg-surface-soft p-4"
						>
							<p class="type-overline text-ink/60">Concepts</p>
							<p class="mt-2 type-body text-ink/80">{{ selectedUnit.concepts }}</p>
						</div>
						<div
							v-if="selectedUnit?.misconceptions"
							class="rounded-2xl border border-line-soft bg-surface-soft p-4"
						>
							<p class="type-overline text-ink/60">Likely Misconceptions</p>
							<p class="mt-2 type-body text-ink/80">{{ selectedUnit.misconceptions }}</p>
						</div>
					</div>

					<section class="space-y-3">
						<div class="flex items-center justify-between gap-3">
							<div>
								<p class="type-overline text-ink/60">Standards Alignment</p>
								<h3 class="mt-1 type-h3 text-ink">Shared alignment rows</h3>
							</div>
							<div class="flex items-center gap-2">
								<span class="chip">{{ unitForm.standards.length }}</span>
								<button
									v-if="canManagePlan"
									type="button"
									class="if-action if-action--subtle"
									@click="addStandard"
								>
									Add Standard
								</button>
							</div>
						</div>

						<div
							v-if="!unitForm.standards.length"
							class="rounded-2xl border border-dashed border-line-soft p-4"
						>
							<p class="type-caption text-ink/70">
								No standards have been captured for this unit yet.
							</p>
						</div>

						<div v-else class="space-y-4">
							<article
								v-for="standard in unitForm.standards"
								:key="standard.local_id"
								class="rounded-2xl border border-line-soft bg-surface-soft p-4"
							>
								<div class="grid gap-4 lg:grid-cols-2">
									<label class="block space-y-2">
										<span class="type-caption text-ink/70">Framework Name</span>
										<input
											v-model="standard.framework_name"
											type="text"
											class="if-input w-full"
											:disabled="!canManagePlan"
										/>
									</label>
									<label class="block space-y-2">
										<span class="type-caption text-ink/70">Framework Version</span>
										<input
											v-model="standard.framework_version"
											type="text"
											class="if-input w-full"
											:disabled="!canManagePlan"
										/>
									</label>
									<label class="block space-y-2">
										<span class="type-caption text-ink/70">Subject Area</span>
										<input
											v-model="standard.subject_area"
											type="text"
											class="if-input w-full"
											:disabled="!canManagePlan"
										/>
									</label>
									<label class="block space-y-2">
										<span class="type-caption text-ink/70">Program</span>
										<input
											v-model="standard.program"
											type="text"
											class="if-input w-full"
											:disabled="!canManagePlan"
										/>
									</label>
									<label class="block space-y-2">
										<span class="type-caption text-ink/70">Strand</span>
										<input
											v-model="standard.strand"
											type="text"
											class="if-input w-full"
											:disabled="!canManagePlan"
										/>
									</label>
									<label class="block space-y-2">
										<span class="type-caption text-ink/70">Substrand</span>
										<input
											v-model="standard.substrand"
											type="text"
											class="if-input w-full"
											:disabled="!canManagePlan"
										/>
									</label>
									<label class="block space-y-2">
										<span class="type-caption text-ink/70">Standard Code</span>
										<input
											v-model="standard.standard_code"
											type="text"
											class="if-input w-full"
											:disabled="!canManagePlan"
										/>
									</label>
									<label class="block space-y-2">
										<span class="type-caption text-ink/70">Coverage Level</span>
										<select
											v-model="standard.coverage_level"
											class="if-input w-full"
											:disabled="!canManagePlan"
										>
											<option value="">Select</option>
											<option v-for="option in coverageLevelOptions" :key="option" :value="option">
												{{ option }}
											</option>
										</select>
									</label>
									<label class="block space-y-2">
										<span class="type-caption text-ink/70">Alignment Strength</span>
										<select
											v-model="standard.alignment_strength"
											class="if-input w-full"
											:disabled="!canManagePlan"
										>
											<option value="">Select</option>
											<option
												v-for="option in alignmentStrengthOptions"
												:key="option"
												:value="option"
											>
												{{ option }}
											</option>
										</select>
									</label>
									<label class="block space-y-2">
										<span class="type-caption text-ink/70">Alignment Type</span>
										<select
											v-model="standard.alignment_type"
											class="if-input w-full"
											:disabled="!canManagePlan"
										>
											<option value="">Select</option>
											<option v-for="option in alignmentTypeOptions" :key="option" :value="option">
												{{ option }}
											</option>
										</select>
									</label>
									<label class="block space-y-2 lg:col-span-2">
										<span class="type-caption text-ink/70">Standard Description</span>
										<textarea
											v-model="standard.standard_description"
											rows="3"
											class="if-input min-h-[6rem] w-full resize-y"
											:disabled="!canManagePlan"
										/>
									</label>
									<label class="block space-y-2 lg:col-span-2">
										<span class="type-caption text-ink/70">Notes</span>
										<textarea
											v-model="standard.notes"
											rows="3"
											class="if-input min-h-[6rem] w-full resize-y"
											:disabled="!canManagePlan"
										/>
									</label>
								</div>
								<div v-if="canManagePlan" class="mt-4 flex justify-end">
									<button
										type="button"
										class="if-action if-action--subtle"
										@click="removeStandard(standard.local_id)"
									>
										Remove Standard
									</button>
								</div>
							</article>
						</div>
					</section>

					<section class="space-y-3">
						<div class="flex items-center justify-between gap-3">
							<div>
								<p class="type-overline text-ink/60">Shared Reflections</p>
								<h3 class="mt-1 type-h3 text-ink">Bird's-eye planning notes</h3>
							</div>
							<div class="flex items-center gap-2">
								<span class="chip">{{ unitForm.reflections.length }}</span>
								<button
									v-if="canManagePlan"
									type="button"
									class="if-action if-action--subtle"
									@click="addReflection"
								>
									Add Reflection
								</button>
							</div>
						</div>

						<div
							v-if="!unitForm.reflections.length"
							class="rounded-2xl border border-dashed border-line-soft p-4"
						>
							<p class="type-caption text-ink/70">
								No shared reflections captured yet for this unit.
							</p>
						</div>

						<div v-else class="space-y-4">
							<article
								v-for="reflection in unitForm.reflections"
								:key="reflection.local_id"
								class="rounded-2xl border border-line-soft bg-surface-soft p-4"
							>
								<div class="grid gap-4 lg:grid-cols-2">
									<label class="block space-y-2">
										<span class="type-caption text-ink/70">Academic Year</span>
										<input
											v-model="reflection.academic_year"
											type="text"
											class="if-input w-full"
											:disabled="!canManagePlan"
										/>
									</label>
									<label class="block space-y-2">
										<span class="type-caption text-ink/70">School</span>
										<input
											v-model="reflection.school"
											type="text"
											class="if-input w-full"
											:disabled="!canManagePlan"
										/>
									</label>
									<label class="block space-y-2 lg:col-span-2">
										<span class="type-caption text-ink/70">Prior To The Unit</span>
										<textarea
											v-model="reflection.prior_to_the_unit"
											rows="3"
											class="if-input min-h-[6rem] w-full resize-y"
											:disabled="!canManagePlan"
										/>
									</label>
									<label class="block space-y-2 lg:col-span-2">
										<span class="type-caption text-ink/70">During The Unit</span>
										<textarea
											v-model="reflection.during_the_unit"
											rows="3"
											class="if-input min-h-[6rem] w-full resize-y"
											:disabled="!canManagePlan"
										/>
									</label>
									<label class="block space-y-2 lg:col-span-2">
										<span class="type-caption text-ink/70">What Worked Well</span>
										<textarea
											v-model="reflection.what_work_well"
											rows="3"
											class="if-input min-h-[6rem] w-full resize-y"
											:disabled="!canManagePlan"
										/>
									</label>
									<label class="block space-y-2 lg:col-span-2">
										<span class="type-caption text-ink/70">What Didn't Work Well</span>
										<textarea
											v-model="reflection.what_didnt_work_well"
											rows="3"
											class="if-input min-h-[6rem] w-full resize-y"
											:disabled="!canManagePlan"
										/>
									</label>
									<label class="block space-y-2 lg:col-span-2">
										<span class="type-caption text-ink/70">Change Suggestions</span>
										<textarea
											v-model="reflection.changes_suggestions"
											rows="3"
											class="if-input min-h-[6rem] w-full resize-y"
											:disabled="!canManagePlan"
										/>
									</label>
								</div>
								<div v-if="canManagePlan" class="mt-4 flex justify-end">
									<button
										type="button"
										class="if-action if-action--subtle"
										@click="removeReflection(reflection.local_id)"
									>
										Remove Reflection
									</button>
								</div>
							</article>
						</div>
					</section>

					<section v-if="selectedUnit?.class_reflections?.length" class="space-y-3">
						<div class="flex items-center justify-between gap-3">
							<h3 class="type-h3 text-ink">Class Reflections Across This Unit</h3>
							<span class="chip">{{ selectedUnit.class_reflections.length }}</span>
						</div>
						<div class="grid gap-3 xl:grid-cols-2">
							<article
								v-for="reflection in selectedUnit.class_reflections"
								:key="`${selectedUnit.unit_plan}-${reflection.class_teaching_plan}`"
								class="rounded-2xl border border-line-soft bg-surface-soft p-4"
							>
								<div class="flex items-center justify-between gap-3">
									<p class="type-body-strong text-ink">{{ reflection.class_label }}</p>
									<span v-if="reflection.academic_year" class="chip">
										{{ reflection.academic_year }}
									</span>
								</div>
								<p v-if="reflection.prior_to_the_unit" class="mt-3 type-body text-ink/80">
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
					</section>

					<section
						v-if="!creatingUnit && selectedUnit"
						class="space-y-4 rounded-[2rem] border border-line-soft bg-surface-soft p-5"
					>
						<div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
							<div>
								<p class="type-overline text-ink/60">Lesson Outlines</p>
								<h3 class="mt-1 type-h3 text-ink">Shared lesson guidance for this unit</h3>
								<p class="mt-2 max-w-2xl type-caption text-ink/70">
									Keep lessons thin and reusable here. Class sessions remain the live teaching
									record.
								</p>
							</div>
							<div class="flex items-center gap-2">
								<span class="chip">{{ currentUnitLessons.length }}</span>
								<button
									v-if="canManagePlan"
									type="button"
									class="if-action if-action--subtle"
									@click="startNewLesson"
								>
									New Lesson Outline
								</button>
							</div>
						</div>

						<div class="grid gap-5 xl:grid-cols-[minmax(0,18rem),minmax(0,1fr)]">
							<aside class="space-y-3">
								<button
									v-for="lesson in currentUnitLessons"
									:key="lesson.lesson"
									type="button"
									class="w-full rounded-2xl border p-4 text-left transition"
									:class="
										selectedLesson?.lesson === lesson.lesson && !creatingLesson
											? 'border-jacaranda bg-white shadow-soft'
											: 'border-line-soft bg-white hover:border-jacaranda/40'
									"
									@click="selectLesson(lesson.lesson)"
								>
									<div class="flex items-start justify-between gap-3">
										<div class="min-w-0">
											<p class="type-overline text-ink/60">
												Lesson {{ lesson.lesson_order || '—' }}
											</p>
											<p class="mt-1 type-body-strong text-ink">{{ lesson.title }}</p>
											<p v-if="lesson.lesson_type" class="mt-1 type-caption text-ink/70">
												{{ lesson.lesson_type }}
											</p>
										</div>
										<div class="flex flex-col items-end gap-2">
											<span class="chip"> {{ lesson.activities.length }} activities </span>
											<div
												v-if="canManagePlan && currentUnitLessons.length > 1"
												class="flex items-center gap-1"
											>
												<button
													type="button"
													class="if-action if-action--subtle px-2 py-1"
													:disabled="lessonReorderPending"
													@click.stop="moveLesson(lesson.lesson, -1)"
												>
													↑
												</button>
												<button
													type="button"
													class="if-action if-action--subtle px-2 py-1"
													:disabled="lessonReorderPending"
													@click.stop="moveLesson(lesson.lesson, 1)"
												>
													↓
												</button>
											</div>
										</div>
									</div>
								</button>

								<div
									v-if="!currentUnitLessons.length"
									class="rounded-2xl border border-dashed border-line-soft bg-white p-4"
								>
									<p class="type-caption text-ink/70">No lesson outlines yet for this unit.</p>
								</div>
							</aside>

							<section
								v-if="showLessonEditor"
								class="space-y-4 rounded-2xl border border-line-soft bg-white p-5"
							>
								<div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
									<div>
										<p class="type-overline text-ink/60">
											{{ creatingLesson ? 'New Lesson Outline' : 'Selected Lesson' }}
										</p>
										<h4 class="mt-1 type-h3 text-ink">
											{{
												creatingLesson
													? 'Capture shared lesson guidance'
													: lessonForm.title || 'Lesson Outline'
											}}
										</h4>
									</div>
									<div class="flex flex-wrap gap-2">
										<span v-if="lessonForm.lesson_order" class="chip">
											Order {{ lessonForm.lesson_order }}
										</span>
										<span v-if="lessonForm.lesson_type" class="chip">
											{{ lessonForm.lesson_type }}
										</span>
										<span class="chip">
											{{ lessonForm.is_published ? 'Published' : 'Draft only' }}
										</span>
										<button
											v-if="canManagePlan && !creatingLesson && selectedLesson"
											type="button"
											class="if-action if-action--subtle"
											:disabled="!selectedLesson.is_published"
											@click="openAssignFromLesson(selectedLesson)"
										>
											Assign From Lesson
										</button>
									</div>
								</div>
								<p
									v-if="
										canManagePlan &&
										!creatingLesson &&
										selectedLesson &&
										!selectedLesson.is_published
									"
									class="type-caption text-ink/70"
								>
									Publish the lesson outline before assigning from shared lesson guidance.
								</p>

								<div v-if="canManagePlan" class="grid gap-4 lg:grid-cols-2">
									<label class="block space-y-2">
										<span class="type-caption text-ink/70">Lesson Title</span>
										<input
											v-model="lessonForm.title"
											type="text"
											class="if-input w-full"
											placeholder="e.g. Microscopy foundations"
										/>
									</label>
									<label class="block space-y-2">
										<span class="type-caption text-ink/70">Lesson Type</span>
										<select v-model="lessonForm.lesson_type" class="if-input w-full">
											<option value="">Select</option>
											<option v-for="option in lessonTypeOptions" :key="option" :value="option">
												{{ option }}
											</option>
										</select>
									</label>
									<label class="block space-y-2">
										<span class="type-caption text-ink/70">Lesson Order</span>
										<input
											v-model.number="lessonForm.lesson_order"
											type="number"
											min="1"
											step="1"
											class="if-input w-full"
										/>
									</label>
									<label class="block space-y-2">
										<span class="type-caption text-ink/70">Start Date</span>
										<input v-model="lessonForm.start_date" type="date" class="if-input w-full" />
									</label>
									<label class="block space-y-2">
										<span class="type-caption text-ink/70"
											>Estimated Duration (teaching periods)</span
										>
										<input
											v-model.number="lessonForm.duration"
											type="number"
											min="1"
											step="1"
											class="if-input w-full"
										/>
									</label>
									<label
										class="flex items-center gap-3 rounded-2xl border border-line-soft bg-surface-soft px-4 py-4"
									>
										<input v-model="lessonForm.is_published" type="checkbox" class="h-4 w-4" />
										<div>
											<p class="type-body-strong text-ink">Published in the shared plan</p>
											<p class="type-caption text-ink/70">
												Show this lesson as ready for class teams to reference.
											</p>
										</div>
									</label>
								</div>

								<section class="space-y-3">
									<div class="flex items-center justify-between gap-3">
										<div>
											<p class="type-overline text-ink/60">Lesson Activities</p>
											<h5 class="mt-1 type-body-strong text-ink">Thin shared lesson flow</h5>
										</div>
										<button
											v-if="canManagePlan"
											type="button"
											class="if-action if-action--subtle"
											@click="addLessonActivity"
										>
											Add Activity
										</button>
									</div>

									<div
										v-if="!lessonForm.activities.length"
										class="rounded-2xl border border-dashed border-line-soft p-4"
									>
										<p class="type-caption text-ink/70">
											No lesson activities yet. Add only the reusable flow; keep class-specific
											adaptation in class sessions.
										</p>
									</div>

									<div v-else class="space-y-4">
										<article
											v-for="activity in lessonForm.activities"
											:key="activity.local_id"
											class="rounded-2xl border border-line-soft bg-surface-soft p-4"
										>
											<div class="grid gap-4 lg:grid-cols-2">
												<label class="block space-y-2">
													<span class="type-caption text-ink/70">Activity Title</span>
													<input
														v-model="activity.title"
														type="text"
														class="if-input w-full"
														placeholder="e.g. Observe slide examples"
														:disabled="!canManagePlan"
													/>
												</label>
												<label class="block space-y-2">
													<span class="type-caption text-ink/70">Activity Type</span>
													<select
														v-model="activity.activity_type"
														class="if-input w-full"
														:disabled="!canManagePlan"
													>
														<option
															v-for="option in lessonActivityTypeOptions"
															:key="option"
															:value="option"
														>
															{{ option }}
														</option>
													</select>
												</label>
												<label class="block space-y-2">
													<span class="type-caption text-ink/70">Order</span>
													<input
														v-model.number="activity.lesson_activity_order"
														type="number"
														min="1"
														step="1"
														class="if-input w-full"
														:disabled="!canManagePlan"
													/>
												</label>
												<label class="block space-y-2">
													<span class="type-caption text-ink/70">Estimated Minutes</span>
													<input
														v-model.number="activity.estimated_duration"
														type="number"
														min="1"
														step="1"
														class="if-input w-full"
														:disabled="!canManagePlan"
													/>
												</label>
												<label
													class="flex items-center gap-3 rounded-2xl border border-line-soft bg-white px-4 py-4 lg:col-span-2"
												>
													<input
														v-model="activity.is_required"
														type="checkbox"
														class="h-4 w-4"
														:disabled="!canManagePlan"
													/>
													<div>
														<p class="type-body-strong text-ink">Required in the shared flow</p>
														<p class="type-caption text-ink/70">
															Mark this only when every class should encounter this activity.
														</p>
													</div>
												</label>
												<label
													v-if="activity.activity_type === 'Reading'"
													class="block space-y-2 lg:col-span-2"
												>
													<span class="type-caption text-ink/70">Reading Content</span>
													<textarea
														v-model="activity.reading_content"
														rows="4"
														class="if-input min-h-[8rem] w-full resize-y"
														:disabled="!canManagePlan"
													/>
												</label>
												<label
													v-if="activity.activity_type === 'Video'"
													class="block space-y-2 lg:col-span-2"
												>
													<span class="type-caption text-ink/70">Video URL</span>
													<input
														v-model="activity.video_url"
														type="url"
														class="if-input w-full"
														placeholder="https://..."
														:disabled="!canManagePlan"
													/>
												</label>
												<label
													v-if="activity.activity_type === 'Link'"
													class="block space-y-2 lg:col-span-2"
												>
													<span class="type-caption text-ink/70">External Link</span>
													<input
														v-model="activity.external_link"
														type="url"
														class="if-input w-full"
														placeholder="https://..."
														:disabled="!canManagePlan"
													/>
												</label>
												<label
													v-if="activity.activity_type === 'Discussion'"
													class="block space-y-2 lg:col-span-2"
												>
													<span class="type-caption text-ink/70">Discussion Prompt</span>
													<textarea
														v-model="activity.discussion_prompt"
														rows="3"
														class="if-input min-h-[6rem] w-full resize-y"
														:disabled="!canManagePlan"
													/>
												</label>
											</div>
											<div v-if="canManagePlan" class="mt-4 flex justify-end">
												<button
													type="button"
													class="if-action if-action--subtle"
													@click="removeLessonActivity(activity.local_id)"
												>
													Remove Activity
												</button>
											</div>
										</article>
									</div>
								</section>

								<div v-if="canManagePlan" class="flex flex-wrap justify-end gap-3">
									<button
										v-if="creatingLesson"
										type="button"
										class="if-action if-action--subtle"
										@click="cancelNewLesson"
									>
										Cancel New Lesson
									</button>
									<button
										v-if="!creatingLesson && selectedLesson"
										type="button"
										class="if-action if-action--subtle"
										:disabled="lessonPending"
										@click="handleDeleteLesson"
									>
										Delete Lesson
									</button>
									<button
										type="button"
										class="if-action"
										:disabled="lessonPending"
										@click="handleSaveLesson"
									>
										{{
											lessonPending
												? 'Saving...'
												: creatingLesson
													? 'Create Lesson Outline'
													: 'Save Lesson Outline'
										}}
									</button>
								</div>
							</section>

							<section
								v-else
								class="rounded-2xl border border-dashed border-line-soft bg-white p-5"
							>
								<p class="type-caption text-ink/70">
									Select a lesson outline or start a new one for this unit.
								</p>
							</section>
						</div>
					</section>

					<div v-if="canManagePlan" class="flex justify-end gap-3">
						<button
							v-if="creatingUnit"
							type="button"
							class="if-action if-action--subtle"
							@click="cancelNewUnit"
						>
							Cancel New Unit
						</button>
						<button
							type="button"
							class="if-action"
							:disabled="unitPending"
							@click="handleSaveUnitPlan"
						>
							{{
								unitPending ? 'Saving...' : creatingUnit ? 'Create Unit Plan' : 'Save Unit Plan'
							}}
						</button>
					</div>

					<PlanningResourcePanel
						anchor-doctype="Unit Plan"
						:anchor-name="selectedUnit?.unit_plan || null"
						:can-manage="canManagePlan"
						eyebrow="Unit Resources"
						title="Shared resources for this unit"
						description="Use this layer for governed materials every class should inherit while teaching the unit."
						empty-message="No governed unit resources yet."
						blocked-message="Save the unit plan before sharing unit resources."
						read-only-message="Only approved curriculum staff can edit shared unit resources."
						:resources="selectedUnit?.shared_resources || []"
						@changed="loadSurface"
					/>
				</section>

				<section v-else class="rounded-[2rem] border border-line-soft bg-white p-6 shadow-soft">
					<p class="type-body text-ink/70">
						Select a governed unit to edit the shared backbone, or create a new unit plan.
					</p>
				</section>
			</section>

			<section class="grid gap-6 xl:grid-cols-[minmax(0,20rem),minmax(0,1fr)]">
				<aside class="space-y-4 xl:self-start">
					<section class="rounded-[2rem] border border-line-soft bg-white p-5 shadow-soft">
						<div class="mb-4 flex items-center justify-between gap-3">
							<div>
								<p class="type-overline text-ink/60">Course Quiz Banks</p>
								<h2 class="mt-1 type-h3 text-ink">Shared quiz authoring</h2>
							</div>
							<span class="chip">{{ surface.assessment.quiz_question_banks.length }}</span>
						</div>

						<p class="mb-4 type-caption text-ink/70">
							Quiz banks are shared at the course level so teachers can assign them later from the
							class task flow.
						</p>

						<div class="space-y-3">
							<button
								v-for="bank in surface.assessment.quiz_question_banks"
								:key="bank.quiz_question_bank"
								type="button"
								class="w-full rounded-2xl border p-4 text-left transition"
								:class="
									selectedQuizQuestionBank?.quiz_question_bank === bank.quiz_question_bank &&
									!creatingQuizQuestionBank
										? 'border-jacaranda bg-jacaranda/10 shadow-soft'
										: 'border-line-soft bg-surface-soft hover:border-jacaranda/40'
								"
								@click="selectQuizQuestionBank(bank.quiz_question_bank)"
							>
								<div class="flex items-start justify-between gap-3">
									<div class="min-w-0">
										<p class="type-body-strong text-ink">{{ bank.bank_title }}</p>
										<p class="mt-1 type-caption text-ink/70">
											{{ bank.published_question_count || 0 }} published of
											{{ bank.question_count || 0 }} total
										</p>
									</div>
									<span class="chip">
										{{ bank.is_published ? 'Ready' : 'Draft' }}
									</span>
								</div>
							</button>

							<div
								v-if="!surface.assessment.quiz_question_banks.length"
								class="rounded-2xl border border-dashed border-line-soft p-4"
							>
								<p class="type-caption text-ink/70">No course quiz banks yet.</p>
							</div>
						</div>

						<div v-if="canManagePlan" class="mt-4">
							<button type="button" class="if-action w-full" @click="startNewQuizQuestionBank">
								{{ creatingQuizQuestionBank ? 'Editing New Quiz Bank' : 'New Quiz Bank' }}
							</button>
						</div>
					</section>
				</aside>

				<section class="rounded-[2rem] border border-line-soft bg-white p-6 shadow-soft">
					<div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
						<div>
							<p class="type-overline text-ink/60">
								{{ creatingQuizQuestionBank ? 'New Quiz Bank' : 'Selected Quiz Bank' }}
							</p>
							<h2 class="mt-2 type-h2 text-ink">
								{{
									creatingQuizQuestionBank
										? 'Draft a reusable quiz bank'
										: quizBankForm.bank_title || 'Quiz Bank'
								}}
							</h2>
							<p class="mt-2 type-body text-ink/80">
								Build question banks once, then assign them through the class task flow without
								rewriting the quiz each time.
							</p>
						</div>
						<div class="flex flex-wrap gap-2">
							<span class="chip"> {{ quizBankForm.questions.length }} questions </span>
							<span class="chip">
								{{ quizBankForm.is_published ? 'Published' : 'Draft only' }}
							</span>
							<button
								v-if="canManagePlan && !creatingQuizQuestionBank && selectedQuizQuestionBank"
								type="button"
								class="if-action if-action--subtle"
								:disabled="!selectedQuizQuestionBank.is_published"
								@click="openAssignFromQuizBank(selectedQuizQuestionBank)"
							>
								Assign This Quiz
							</button>
						</div>
					</div>
					<p
						v-if="
							canManagePlan &&
							!creatingQuizQuestionBank &&
							selectedQuizQuestionBank &&
							!selectedQuizQuestionBank.is_published
						"
						class="mt-3 type-caption text-ink/70"
					>
						Publish the quiz bank before assigning it to a class.
					</p>

					<div
						v-if="!showQuizBankEditor"
						class="mt-6 rounded-2xl border border-dashed border-line-soft p-5"
					>
						<p class="type-caption text-ink/70">
							Select a quiz bank, or create a new one for this course.
						</p>
					</div>

					<template v-else>
						<div v-if="canManagePlan" class="mt-6 grid gap-4 lg:grid-cols-2">
							<label class="block space-y-2">
								<span class="type-caption text-ink/70">Bank Title</span>
								<input
									v-model="quizBankForm.bank_title"
									type="text"
									class="if-input w-full"
									placeholder="e.g. Cell Structure Check-in"
								/>
							</label>
							<label
								class="flex items-center gap-3 rounded-2xl border border-line-soft bg-surface-soft px-4 py-4"
							>
								<input v-model="quizBankForm.is_published" type="checkbox" class="h-4 w-4" />
								<div>
									<p class="type-body-strong text-ink">Ready for assignment</p>
									<p class="type-caption text-ink/70">
										Published banks appear in the quiz selection step when teachers assign work.
									</p>
								</div>
							</label>
							<label class="block space-y-2 lg:col-span-2">
								<span class="type-caption text-ink/70">Description</span>
								<textarea
									v-model="quizBankForm.description"
									rows="4"
									class="if-input min-h-[8rem] w-full resize-y"
									placeholder="Explain what this quiz bank checks and when teachers should use it."
								/>
							</label>
						</div>

						<section class="mt-6 space-y-4">
							<div class="flex items-center justify-between gap-3">
								<div>
									<p class="type-overline text-ink/60">Questions</p>
									<h3 class="mt-1 type-h3 text-ink">Reusable quiz items</h3>
								</div>
								<button
									v-if="canManagePlan"
									type="button"
									class="if-action if-action--subtle"
									@click="addQuizQuestion"
								>
									Add Question
								</button>
							</div>

							<div
								v-if="!quizBankForm.questions.length"
								class="rounded-2xl border border-dashed border-line-soft p-4"
							>
								<p class="type-caption text-ink/70">
									No questions yet. Add reusable questions teachers can pull into quiz-backed
									tasks.
								</p>
							</div>

							<div v-else class="space-y-4">
								<article
									v-for="question in quizBankForm.questions"
									:key="question.local_id"
									class="rounded-2xl border border-line-soft bg-surface-soft p-4"
								>
									<div class="grid gap-4 lg:grid-cols-2">
										<label class="block space-y-2">
											<span class="type-caption text-ink/70">Question Title</span>
											<input
												v-model="question.title"
												type="text"
												class="if-input w-full"
												placeholder="e.g. Identify the nucleus"
												:disabled="!canManagePlan"
											/>
										</label>
										<label class="block space-y-2">
											<span class="type-caption text-ink/70">Question Type</span>
											<select
												v-model="question.question_type"
												class="if-input w-full"
												:disabled="!canManagePlan"
												@change="handleQuizQuestionTypeChange(question)"
											>
												<option
													v-for="option in quizQuestionTypeOptions"
													:key="option"
													:value="option"
												>
													{{ option }}
												</option>
											</select>
										</label>
										<label
											class="flex items-center gap-3 rounded-2xl border border-line-soft bg-white px-4 py-4 lg:col-span-2"
										>
											<input
												v-model="question.is_published"
												type="checkbox"
												class="h-4 w-4"
												:disabled="!canManagePlan"
											/>
											<div>
												<p class="type-body-strong text-ink">Published in the bank</p>
												<p class="type-caption text-ink/70">
													Only published questions are available for quiz attempts.
												</p>
											</div>
										</label>
										<label class="block space-y-2 lg:col-span-2">
											<span class="type-caption text-ink/70">Prompt</span>
											<textarea
												v-model="question.prompt"
												rows="4"
												class="if-input min-h-[8rem] w-full resize-y"
												:disabled="!canManagePlan"
											/>
										</label>
										<label
											v-if="question.question_type === 'Short Answer'"
											class="block space-y-2 lg:col-span-2"
										>
											<span class="type-caption text-ink/70">Accepted Answers</span>
											<textarea
												v-model="question.accepted_answers"
												rows="4"
												class="if-input min-h-[8rem] w-full resize-y"
												placeholder="One accepted answer per line"
												:disabled="!canManagePlan"
											/>
										</label>
									</div>

									<section
										v-if="isChoiceQuestion(question.question_type)"
										class="mt-4 space-y-3 rounded-2xl border border-line-soft bg-white p-4"
									>
										<div class="flex items-center justify-between gap-3">
											<div>
												<p class="type-overline text-ink/60">Answer Options</p>
												<h4 class="mt-1 type-body-strong text-ink">Choice payload</h4>
											</div>
											<button
												v-if="canManagePlan && question.question_type !== 'True / False'"
												type="button"
												class="if-action if-action--subtle"
												@click="addQuizOption(question)"
											>
												Add Option
											</button>
										</div>

										<div class="space-y-3">
											<div
												v-for="option in question.options"
												:key="option.local_id"
												class="grid gap-3 rounded-2xl border border-line-soft bg-surface-soft p-3 md:grid-cols-[minmax(0,1fr),auto,auto]"
											>
												<input
													v-model="option.option_text"
													type="text"
													class="if-input w-full"
													placeholder="Option text"
													:disabled="!canManagePlan"
												/>
												<label
													class="flex items-center gap-2 rounded-xl border border-line-soft bg-white px-3 py-2 type-caption text-ink/70"
												>
													<input
														v-model="option.is_correct"
														type="checkbox"
														class="h-4 w-4"
														:disabled="!canManagePlan"
													/>
													<span>Correct</span>
												</label>
												<button
													v-if="canManagePlan && question.question_type !== 'True / False'"
													type="button"
													class="if-action if-action--subtle"
													@click="removeQuizOption(question, option.local_id)"
												>
													Remove
												</button>
											</div>
										</div>
									</section>

									<label class="mt-4 block space-y-2">
										<span class="type-caption text-ink/70">Explanation</span>
										<textarea
											v-model="question.explanation"
											rows="3"
											class="if-input min-h-[6rem] w-full resize-y"
											placeholder="Optional feedback or explanation shown when allowed."
											:disabled="!canManagePlan"
										/>
									</label>

									<div v-if="canManagePlan" class="mt-4 flex justify-end">
										<button
											type="button"
											class="if-action if-action--subtle"
											@click="removeQuizQuestion(question.local_id)"
										>
											Remove Question
										</button>
									</div>
								</article>
							</div>
						</section>

						<div v-if="canManagePlan" class="mt-6 flex flex-wrap justify-end gap-3">
							<button
								v-if="creatingQuizQuestionBank"
								type="button"
								class="if-action if-action--subtle"
								@click="cancelNewQuizQuestionBank"
							>
								Cancel New Quiz Bank
							</button>
							<button
								type="button"
								class="if-action"
								:disabled="quizBankPending"
								@click="handleSaveQuizQuestionBank"
							>
								{{
									quizBankPending
										? 'Saving...'
										: creatingQuizQuestionBank
											? 'Create Quiz Bank'
											: 'Save Quiz Bank'
								}}
							</button>
						</div>
					</template>
				</section>
			</section>
		</template>
	</div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue';
import { toast } from 'frappe-ui';
import { useRoute, useRouter } from 'vue-router';

import PlanningResourcePanel from '@/components/planning/PlanningResourcePanel.vue';
import { useOverlayStack } from '@/composables/useOverlayStack';
import {
	getStaffCoursePlanSurface,
	removeLessonOutline,
	reorderUnitLessons,
	saveCoursePlan,
	saveGovernedUnitPlan,
	saveLessonOutline,
	saveQuizQuestionBank,
} from '@/lib/services/staff/staffTeachingService';
import type {
	Response as StaffCoursePlanSurfaceResponse,
	StaffCoursePlanLesson,
	StaffCoursePlanLessonActivity,
	StaffCoursePlanQuizQuestion,
	StaffCoursePlanQuizQuestionBank,
	StaffCoursePlanQuizQuestionOption,
	StaffCoursePlanUnit,
} from '@/types/contracts/staff_teaching/get_staff_course_plan_surface';
import type {
	StaffPlanningReflection,
	StaffPlanningStandard,
} from '@/types/contracts/staff_teaching/get_staff_class_planning_surface';

type EditableStandard = StaffPlanningStandard & {
	local_id: number;
};

type EditableReflection = StaffPlanningReflection & {
	local_id: number;
};

type EditableLessonActivity = StaffCoursePlanLessonActivity & {
	local_id: number;
	is_required: boolean;
};

type EditableQuizQuestionOption = StaffCoursePlanQuizQuestionOption & {
	local_id: number;
	is_correct: boolean;
};

type EditableQuizQuestion = Omit<StaffCoursePlanQuizQuestion, 'options'> & {
	local_id: number;
	is_published: boolean;
	options: EditableQuizQuestionOption[];
};

const props = defineProps<{
	coursePlan: string;
	unitPlan?: string;
	quizQuestionBank?: string;
}>();

const route = useRoute();
const router = useRouter();
const overlay = useOverlayStack();

const surface = ref<StaffCoursePlanSurfaceResponse | null>(null);
const loading = ref(false);
const errorMessage = ref('');
const coursePlanPending = ref(false);
const unitPending = ref(false);
const lessonPending = ref(false);
const lessonReorderPending = ref(false);
const quizBankPending = ref(false);
const selectedUnitPlan = ref('');
const selectedLessonName = ref('');
const selectedQuizQuestionBankName = ref(String(props.quizQuestionBank || '').trim());
const creatingUnit = ref(false);
const creatingLesson = ref(false);
const creatingQuizQuestionBank = ref(false);
const loadToken = ref(0);
const nextLocalId = ref(1);

const coursePlanForm = reactive({
	title: '',
	academic_year: '',
	cycle_label: '',
	plan_status: 'Draft',
	summary: '',
});

const unitForm = reactive({
	unit_plan: '',
	title: '',
	program: '',
	unit_code: '',
	unit_order: null as number | null,
	unit_status: 'Active',
	version: '',
	duration: '',
	estimated_duration: '',
	is_published: false,
	overview: '',
	essential_understanding: '',
	misconceptions: '',
	content: '',
	skills: '',
	concepts: '',
	standards: [] as EditableStandard[],
	reflections: [] as EditableReflection[],
});

const lessonForm = reactive({
	lesson: '',
	title: '',
	lesson_type: '',
	lesson_order: null as number | null,
	is_published: false,
	start_date: '',
	duration: null as number | null,
	activities: [] as EditableLessonActivity[],
});

const quizBankForm = reactive({
	quiz_question_bank: '',
	bank_title: '',
	description: '',
	is_published: true,
	questions: [] as EditableQuizQuestion[],
});

const coursePlanStatusOptions = ['Draft', 'Active', 'Archived'];
const unitStatusOptions = ['Draft', 'Active', 'Archived'];
const coverageLevelOptions = ['Introduced', 'Reinforced', 'Mastered'];
const alignmentStrengthOptions = ['Exact', 'Partial', 'Broad'];
const alignmentTypeOptions = ['Knowledge', 'Skill', 'Practice', 'Process'];
const lessonTypeOptions = ['Instruction', 'Practice', 'Assessment', 'Project', 'Review', 'Other'];
const lessonActivityTypeOptions = ['Reading', 'Video', 'Link', 'Discussion', 'Interactive'];
const quizQuestionTypeOptions = [
	'Single Choice',
	'Multiple Answer',
	'True / False',
	'Short Answer',
	'Essay',
];

const selectedUnit = computed<StaffCoursePlanUnit | null>(() => {
	return (
		surface.value?.curriculum.units.find(unit => unit.unit_plan === selectedUnitPlan.value) || null
	);
});

const currentUnitLessons = computed<StaffCoursePlanLesson[]>(() => {
	return surface.value?.curriculum.selected_unit_lessons || [];
});

const selectedLesson = computed<StaffCoursePlanLesson | null>(() => {
	return (
		currentUnitLessons.value.find(lesson => lesson.lesson === selectedLessonName.value) || null
	);
});

const selectedQuizQuestionBank = computed<StaffCoursePlanQuizQuestionBank | null>(() => {
	const detail = surface.value?.assessment.selected_quiz_question_bank || null;
	if (!detail) return null;
	if (
		selectedQuizQuestionBankName.value &&
		detail.quiz_question_bank !== selectedQuizQuestionBankName.value
	) {
		return null;
	}
	return detail;
});

const canManagePlan = computed(() => Boolean(surface.value?.course_plan.can_manage_resources));
const showUnitEditor = computed(() => Boolean(selectedUnit.value || creatingUnit.value));
const showLessonEditor = computed(() => Boolean(selectedLesson.value || creatingLesson.value));
const showQuizBankEditor = computed(() =>
	Boolean(selectedQuizQuestionBank.value || creatingQuizQuestionBank.value)
);

function nextId() {
	return nextLocalId.value++;
}

function isChoiceQuestion(questionType?: string | null) {
	return ['Single Choice', 'Multiple Answer', 'True / False'].includes(questionType || '');
}

function buildEditableStandard(standard?: StaffPlanningStandard): EditableStandard {
	return {
		local_id: nextId(),
		framework_name: standard?.framework_name || '',
		framework_version: standard?.framework_version || '',
		subject_area: standard?.subject_area || '',
		program: standard?.program || '',
		strand: standard?.strand || '',
		substrand: standard?.substrand || '',
		standard_code: standard?.standard_code || '',
		standard_description: standard?.standard_description || '',
		coverage_level: standard?.coverage_level || '',
		alignment_strength: standard?.alignment_strength || '',
		alignment_type: standard?.alignment_type || '',
		notes: standard?.notes || '',
	};
}

function buildEditableReflection(reflection?: StaffPlanningReflection): EditableReflection {
	return {
		local_id: nextId(),
		academic_year: reflection?.academic_year || '',
		school: reflection?.school || '',
		prior_to_the_unit: reflection?.prior_to_the_unit || '',
		during_the_unit: reflection?.during_the_unit || '',
		what_work_well: reflection?.what_work_well || '',
		what_didnt_work_well: reflection?.what_didnt_work_well || '',
		changes_suggestions: reflection?.changes_suggestions || '',
	};
}

function buildEditableLessonActivity(
	activity?: StaffCoursePlanLessonActivity
): EditableLessonActivity {
	return {
		local_id: nextId(),
		title: activity?.title || '',
		activity_type: activity?.activity_type || 'Interactive',
		lesson_activity_order: activity?.lesson_activity_order ?? null,
		reading_content: activity?.reading_content || '',
		video_url: activity?.video_url || '',
		external_link: activity?.external_link || '',
		discussion_prompt: activity?.discussion_prompt || '',
		is_required: Boolean(activity?.is_required),
		estimated_duration: activity?.estimated_duration ?? null,
	};
}

function buildEditableQuizOption(
	option?: StaffCoursePlanQuizQuestionOption
): EditableQuizQuestionOption {
	return {
		local_id: nextId(),
		option_text: option?.option_text || '',
		is_correct: Boolean(option?.is_correct),
	};
}

function buildEditableQuizQuestion(question?: StaffCoursePlanQuizQuestion): EditableQuizQuestion {
	return {
		local_id: nextId(),
		quiz_question: question?.quiz_question || '',
		title: question?.title || '',
		question_type: question?.question_type || 'Single Choice',
		is_published: question?.is_published !== 0,
		prompt: question?.prompt || '',
		accepted_answers: question?.accepted_answers || '',
		explanation: question?.explanation || '',
		options: (question?.options || []).map(option => buildEditableQuizOption(option)),
	};
}

function buildBlankQuizQuestion(questionType = 'Single Choice'): EditableQuizQuestion {
	const question = buildEditableQuizQuestion({
		title: '',
		question_type: questionType,
		is_published: 1,
		prompt: '',
		accepted_answers: '',
		explanation: '',
		options: [],
	});
	handleQuizQuestionTypeChange(question);
	return question;
}

function syncCoursePlanForm(payload: StaffCoursePlanSurfaceResponse | null) {
	coursePlanForm.title = payload?.course_plan.title || '';
	coursePlanForm.academic_year = payload?.course_plan.academic_year || '';
	coursePlanForm.cycle_label = payload?.course_plan.cycle_label || '';
	coursePlanForm.plan_status = payload?.course_plan.plan_status || 'Draft';
	coursePlanForm.summary = payload?.course_plan.summary || '';
}

function syncUnitForm(unit: StaffCoursePlanUnit | null) {
	unitForm.unit_plan = unit?.unit_plan || '';
	unitForm.title = unit?.title || '';
	unitForm.program = unit?.program || '';
	unitForm.unit_code = unit?.unit_code || '';
	unitForm.unit_order = unit?.unit_order ?? null;
	unitForm.unit_status = unit?.unit_status || 'Active';
	unitForm.version = unit?.version || '';
	unitForm.duration = unit?.duration || '';
	unitForm.estimated_duration = unit?.estimated_duration || '';
	unitForm.is_published = Boolean(unit?.is_published);
	unitForm.overview = unit?.overview || '';
	unitForm.essential_understanding = unit?.essential_understanding || '';
	unitForm.misconceptions = unit?.misconceptions || '';
	unitForm.content = unit?.content || '';
	unitForm.skills = unit?.skills || '';
	unitForm.concepts = unit?.concepts || '';
	unitForm.standards = (unit?.standards || []).map(standard => buildEditableStandard(standard));
	unitForm.reflections = (unit?.shared_reflections || []).map(reflection =>
		buildEditableReflection(reflection)
	);
}

function syncLessonForm(lesson: StaffCoursePlanLesson | null) {
	lessonForm.lesson = lesson?.lesson || '';
	lessonForm.title = lesson?.title || '';
	lessonForm.lesson_type = lesson?.lesson_type || '';
	lessonForm.lesson_order = lesson?.lesson_order ?? null;
	lessonForm.is_published = Boolean(lesson?.is_published);
	lessonForm.start_date = lesson?.start_date || '';
	lessonForm.duration = lesson?.duration ?? null;
	lessonForm.activities = (lesson?.activities || []).map(activity =>
		buildEditableLessonActivity(activity)
	);
}

function syncQuizBankForm(bank: StaffCoursePlanQuizQuestionBank | null) {
	quizBankForm.quiz_question_bank = bank?.quiz_question_bank || '';
	quizBankForm.bank_title = bank?.bank_title || '';
	quizBankForm.description = bank?.description || '';
	quizBankForm.is_published = bank?.is_published !== 0;
	quizBankForm.questions = (bank?.questions || []).map(question =>
		buildEditableQuizQuestion(question)
	);
}

function applyLessonSelection(payload: StaffCoursePlanSurfaceResponse) {
	const lessons = payload.curriculum.selected_unit_lessons || [];
	if (creatingLesson.value) return;
	const nextSelectedLesson = lessons.some(lesson => lesson.lesson === selectedLessonName.value)
		? selectedLessonName.value
		: lessons[0]?.lesson || '';
	selectedLessonName.value = nextSelectedLesson;
	syncLessonForm(lessons.find(lesson => lesson.lesson === nextSelectedLesson) || null);
}

function applyQuizBankSelection(payload: StaffCoursePlanSurfaceResponse) {
	if (creatingQuizQuestionBank.value) return;
	const requestedBank = String(
		selectedQuizQuestionBankName.value || props.quizQuestionBank || ''
	).trim();
	const resolvedBank =
		payload.resolved.quiz_question_bank ||
		payload.assessment.quiz_question_banks[0]?.quiz_question_bank ||
		'';
	const nextBank = payload.assessment.quiz_question_banks.some(
		bank => bank.quiz_question_bank === requestedBank
	)
		? requestedBank
		: resolvedBank;
	selectedQuizQuestionBankName.value = nextBank;
	const detail = payload.assessment.selected_quiz_question_bank || null;
	syncQuizBankForm(detail && detail.quiz_question_bank === nextBank ? detail : null);
}

function applySurfaceSelection(payload: StaffCoursePlanSurfaceResponse) {
	syncCoursePlanForm(payload);

	if (!creatingUnit.value) {
		const requestedUnit = String(props.unitPlan || '').trim();
		const resolvedUnit =
			payload.resolved.unit_plan || payload.curriculum.units[0]?.unit_plan || '';
		const nextSelectedUnit = payload.curriculum.units.some(
			unit => unit.unit_plan === requestedUnit
		)
			? requestedUnit
			: resolvedUnit;
		selectedUnitPlan.value = nextSelectedUnit;
		syncUnitForm(
			payload.curriculum.units.find(unit => unit.unit_plan === nextSelectedUnit) || null
		);
	}

	applyLessonSelection(payload);
	applyQuizBankSelection(payload);
}

async function loadSurface() {
	const ticket = loadToken.value + 1;
	loadToken.value = ticket;
	loading.value = true;
	errorMessage.value = '';

	try {
		const payload = await getStaffCoursePlanSurface({
			course_plan: props.coursePlan,
			unit_plan: props.unitPlan || undefined,
			quiz_question_bank: selectedQuizQuestionBankName.value || undefined,
		});
		if (ticket !== loadToken.value) return;
		surface.value = payload;
		applySurfaceSelection(payload);
	} catch (error) {
		if (ticket !== loadToken.value) return;
		surface.value = null;
		errorMessage.value = error instanceof Error ? error.message : 'Unknown error';
	} finally {
		if (ticket === loadToken.value) {
			loading.value = false;
		}
	}
}

async function selectUnit(unitPlan: string) {
	creatingUnit.value = false;
	creatingLesson.value = false;
	selectedLessonName.value = '';
	syncLessonForm(null);
	selectedUnitPlan.value = unitPlan;
	syncUnitForm(surface.value?.curriculum.units.find(unit => unit.unit_plan === unitPlan) || null);
	await router.replace({
		name: 'staff-course-plan',
		params: { coursePlan: props.coursePlan },
		query: {
			...route.query,
			unit_plan: unitPlan || undefined,
		},
	});
}

async function startNewUnit() {
	creatingUnit.value = true;
	creatingLesson.value = false;
	selectedLessonName.value = '';
	selectedUnitPlan.value = '';
	syncUnitForm(null);
	syncLessonForm(null);
	await router.replace({
		name: 'staff-course-plan',
		params: { coursePlan: props.coursePlan },
		query: {
			...route.query,
			unit_plan: undefined,
		},
	});
}

function cancelNewUnit() {
	creatingUnit.value = false;
	const fallbackUnit = surface.value?.curriculum.units[0]?.unit_plan || '';
	if (fallbackUnit) {
		void selectUnit(fallbackUnit);
		return;
	}
	syncUnitForm(null);
}

function addStandard() {
	unitForm.standards.push(buildEditableStandard());
}

function removeStandard(localId: number) {
	unitForm.standards = unitForm.standards.filter(standard => standard.local_id !== localId);
}

function addReflection() {
	unitForm.reflections.push(
		buildEditableReflection({
			academic_year: coursePlanForm.academic_year || undefined,
		})
	);
}

function removeReflection(localId: number) {
	unitForm.reflections = unitForm.reflections.filter(
		reflection => reflection.local_id !== localId
	);
}

function serializeStandards(): StaffPlanningStandard[] {
	return unitForm.standards.map(({ local_id, ...row }) => row);
}

function serializeReflections(): StaffPlanningReflection[] {
	return unitForm.reflections.map(({ local_id, ...row }) => row);
}

function openAssignFromLesson(lesson: StaffCoursePlanLesson) {
	if (!surface.value) return;
	if (!lesson.is_published) {
		toast.error('Publish the lesson outline before assigning from it.');
		return;
	}
	overlay.open('create-task', {
		prefillCourse: surface.value.course_plan.course,
		prefillUnitPlan: lesson.unit_plan,
		prefillLesson: lesson.lesson,
		prefillLessonLabel: lesson.title,
		prefillTitle: lesson.title,
	});
}

function startNewLesson() {
	if (!selectedUnit.value) return;
	creatingLesson.value = true;
	selectedLessonName.value = '';
	syncLessonForm(null);
	const fallbackOrder =
		currentUnitLessons.value[currentUnitLessons.value.length - 1]?.lesson_order || 0;
	lessonForm.lesson_order = fallbackOrder + 10;
}

function selectLesson(lessonName: string) {
	creatingLesson.value = false;
	selectedLessonName.value = lessonName;
	syncLessonForm(currentUnitLessons.value.find(lesson => lesson.lesson === lessonName) || null);
}

function cancelNewLesson() {
	creatingLesson.value = false;
	const fallbackLesson = currentUnitLessons.value[0]?.lesson || '';
	selectedLessonName.value = fallbackLesson;
	syncLessonForm(
		currentUnitLessons.value.find(lesson => lesson.lesson === fallbackLesson) || null
	);
}

function addLessonActivity() {
	lessonForm.activities.push(
		buildEditableLessonActivity({
			activity_type: 'Interactive',
			is_required: 0,
		})
	);
}

function removeLessonActivity(localId: number) {
	lessonForm.activities = lessonForm.activities.filter(activity => activity.local_id !== localId);
}

function serializeLessonActivities(): StaffCoursePlanLessonActivity[] {
	return lessonForm.activities.map(({ local_id, is_required, ...row }) => ({
		...row,
		is_required: is_required ? 1 : 0,
	}));
}

async function moveLesson(lessonName: string, direction: -1 | 1) {
	if (!selectedUnit.value) return;
	const reordered = [...currentUnitLessons.value];
	const index = reordered.findIndex(lesson => lesson.lesson === lessonName);
	const targetIndex = index + direction;
	if (index < 0 || targetIndex < 0 || targetIndex >= reordered.length) return;

	lessonReorderPending.value = true;
	try {
		const [row] = reordered.splice(index, 1);
		reordered.splice(targetIndex, 0, row);
		await reorderUnitLessons({
			unit_plan: selectedUnit.value.unit_plan,
			lesson_names: reordered.map(lesson => lesson.lesson),
		});
		await loadSurface();
		toast.success('Lesson order updated.');
	} catch (error) {
		toast.error(error instanceof Error ? error.message : 'Could not reorder the lesson outlines.');
	} finally {
		lessonReorderPending.value = false;
	}
}

function startNewQuizQuestionBank() {
	creatingQuizQuestionBank.value = true;
	selectedQuizQuestionBankName.value = '';
	syncQuizBankForm(null);
}

function openAssignFromQuizBank(bank: StaffCoursePlanQuizQuestionBank) {
	if (!surface.value) return;
	if (!bank.is_published) {
		toast.error('Publish the quiz bank before assigning it.');
		return;
	}
	overlay.open('create-task', {
		prefillCourse: surface.value.course_plan.course,
		prefillUnitPlan: selectedUnit.value?.unit_plan || null,
		prefillQuizQuestionBank: bank.quiz_question_bank,
		prefillQuizQuestionBankLabel: bank.bank_title,
		prefillTitle: bank.bank_title,
		prefillTaskType: 'Quiz',
	});
}

async function selectQuizQuestionBank(questionBank: string) {
	creatingQuizQuestionBank.value = false;
	selectedQuizQuestionBankName.value = questionBank;
	await loadSurface();
}

function cancelNewQuizQuestionBank() {
	creatingQuizQuestionBank.value = false;
	const fallbackBank = surface.value?.assessment.quiz_question_banks[0]?.quiz_question_bank || '';
	selectedQuizQuestionBankName.value = fallbackBank;
	if (fallbackBank) {
		void loadSurface();
		return;
	}
	syncQuizBankForm(null);
}

function addQuizQuestion() {
	quizBankForm.questions.push(buildBlankQuizQuestion());
}

function removeQuizQuestion(localId: number) {
	quizBankForm.questions = quizBankForm.questions.filter(
		question => question.local_id !== localId
	);
}

function addQuizOption(question: EditableQuizQuestion) {
	question.options.push(buildEditableQuizOption());
}

function removeQuizOption(question: EditableQuizQuestion, localId: number) {
	question.options = question.options.filter(option => option.local_id !== localId);
}

function handleQuizQuestionTypeChange(question: EditableQuizQuestion) {
	if (question.question_type === 'True / False') {
		question.options = [
			buildEditableQuizOption({ option_text: 'True', is_correct: 1 }),
			buildEditableQuizOption({ option_text: 'False', is_correct: 0 }),
		];
		question.accepted_answers = '';
		return;
	}

	if (isChoiceQuestion(question.question_type)) {
		if (question.options.length < 2) {
			question.options = [buildEditableQuizOption(), buildEditableQuizOption()];
		}
		question.accepted_answers = '';
		return;
	}

	question.options = [];
	if (question.question_type !== 'Short Answer') {
		question.accepted_answers = '';
	}
}

function serializeQuizQuestions(): StaffCoursePlanQuizQuestion[] {
	return quizBankForm.questions.map(({ local_id, is_published, options, ...question }) => ({
		...question,
		is_published: is_published ? 1 : 0,
		options: options.map(({ local_id: optionLocalId, is_correct, ...option }) => ({
			...option,
			is_correct: is_correct ? 1 : 0,
		})),
	}));
}

async function handleSaveCoursePlan() {
	if (!surface.value?.course_plan.course_plan) return;
	coursePlanPending.value = true;
	try {
		await saveCoursePlan({
			course_plan: surface.value.course_plan.course_plan,
			title: coursePlanForm.title.trim(),
			academic_year: coursePlanForm.academic_year.trim() || null,
			cycle_label: coursePlanForm.cycle_label.trim() || null,
			plan_status: coursePlanForm.plan_status,
			summary: coursePlanForm.summary || null,
		});
		await loadSurface();
		toast.success('Shared course plan updated.');
	} catch (error) {
		toast.error(error instanceof Error ? error.message : 'Could not save the shared course plan.');
	} finally {
		coursePlanPending.value = false;
	}
}

async function handleSaveUnitPlan() {
	unitPending.value = true;
	try {
		const wasCreating = creatingUnit.value;
		const result = await saveGovernedUnitPlan({
			course_plan: props.coursePlan,
			unit_plan: wasCreating ? undefined : unitForm.unit_plan || undefined,
			title: unitForm.title.trim(),
			program: unitForm.program.trim() || null,
			unit_code: unitForm.unit_code.trim() || null,
			unit_order: unitForm.unit_order,
			unit_status: unitForm.unit_status,
			version: unitForm.version.trim() || null,
			duration: unitForm.duration.trim() || null,
			estimated_duration: unitForm.estimated_duration.trim() || null,
			is_published: unitForm.is_published ? 1 : 0,
			overview: unitForm.overview || null,
			essential_understanding: unitForm.essential_understanding || null,
			misconceptions: unitForm.misconceptions || null,
			content: unitForm.content || null,
			skills: unitForm.skills || null,
			concepts: unitForm.concepts || null,
			standards: serializeStandards(),
			reflections: serializeReflections(),
		});
		creatingUnit.value = false;
		await router.replace({
			name: 'staff-course-plan',
			params: { coursePlan: props.coursePlan },
			query: {
				...route.query,
				unit_plan: result.unit_plan,
			},
		});
		await loadSurface();
		toast.success(wasCreating ? 'Unit plan created.' : 'Unit plan updated.');
	} catch (error) {
		toast.error(error instanceof Error ? error.message : 'Could not save the unit plan.');
	} finally {
		unitPending.value = false;
	}
}

async function handleSaveLesson() {
	if (!selectedUnit.value) return;
	lessonPending.value = true;
	try {
		const wasCreating = creatingLesson.value;
		const result = await saveLessonOutline({
			unit_plan: selectedUnit.value.unit_plan,
			lesson: wasCreating ? undefined : lessonForm.lesson || undefined,
			title: lessonForm.title.trim(),
			lesson_type: lessonForm.lesson_type || null,
			lesson_order: lessonForm.lesson_order,
			is_published: lessonForm.is_published ? 1 : 0,
			start_date: lessonForm.start_date || null,
			duration: lessonForm.duration,
			activities: serializeLessonActivities(),
		});
		creatingLesson.value = false;
		selectedLessonName.value = result.lesson;
		await loadSurface();
		toast.success(wasCreating ? 'Lesson outline created.' : 'Lesson outline updated.');
	} catch (error) {
		toast.error(error instanceof Error ? error.message : 'Could not save the lesson outline.');
	} finally {
		lessonPending.value = false;
	}
}

async function handleDeleteLesson() {
	if (!selectedLesson.value) return;
	if (!window.confirm('Delete this lesson outline?')) return;
	lessonPending.value = true;
	try {
		await removeLessonOutline({ lesson: selectedLesson.value.lesson });
		selectedLessonName.value = '';
		await loadSurface();
		toast.success('Lesson outline deleted.');
	} catch (error) {
		toast.error(error instanceof Error ? error.message : 'Could not delete the lesson outline.');
	} finally {
		lessonPending.value = false;
	}
}

async function handleSaveQuizQuestionBank() {
	quizBankPending.value = true;
	try {
		const wasCreating = creatingQuizQuestionBank.value;
		const result = await saveQuizQuestionBank({
			course_plan: props.coursePlan,
			quiz_question_bank: wasCreating ? undefined : quizBankForm.quiz_question_bank || undefined,
			bank_title: quizBankForm.bank_title.trim(),
			description: quizBankForm.description || null,
			is_published: quizBankForm.is_published ? 1 : 0,
			questions: serializeQuizQuestions(),
		});
		creatingQuizQuestionBank.value = false;
		selectedQuizQuestionBankName.value = result.quiz_question_bank;
		await loadSurface();
		toast.success(wasCreating ? 'Quiz bank created.' : 'Quiz bank updated.');
	} catch (error) {
		toast.error(error instanceof Error ? error.message : 'Could not save the quiz bank.');
	} finally {
		quizBankPending.value = false;
	}
}

watch(
	() => [props.coursePlan, props.unitPlan],
	() => {
		loadSurface();
	},
	{ immediate: true }
);
</script>
