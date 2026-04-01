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
							Edit the shared course backbone, tune the governed unit sequence, and begin each unit
							with a clear view of reflections gathered across classes.
						</p>
					</div>
				</div>
				<div class="flex flex-wrap gap-2 lg:justify-end">
					<span class="chip">{{ surface?.course_plan.course_name || 'Course pending' }}</span>
					<span class="chip">{{ surface?.curriculum.unit_count || 0 }} units</span>
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
		</template>
	</div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue';
import { toast } from 'frappe-ui';
import { useRoute, useRouter } from 'vue-router';

import PlanningResourcePanel from '@/components/planning/PlanningResourcePanel.vue';
import {
	getStaffCoursePlanSurface,
	saveCoursePlan,
	saveGovernedUnitPlan,
} from '@/lib/services/staff/staffTeachingService';
import type {
	Response as StaffCoursePlanSurfaceResponse,
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

const props = defineProps<{
	coursePlan: string;
	unitPlan?: string;
}>();

const route = useRoute();
const router = useRouter();

const surface = ref<StaffCoursePlanSurfaceResponse | null>(null);
const loading = ref(false);
const errorMessage = ref('');
const coursePlanPending = ref(false);
const unitPending = ref(false);
const selectedUnitPlan = ref('');
const creatingUnit = ref(false);
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

const coursePlanStatusOptions = ['Draft', 'Active', 'Archived'];
const unitStatusOptions = ['Draft', 'Active', 'Archived'];
const coverageLevelOptions = ['Introduced', 'Reinforced', 'Mastered'];
const alignmentStrengthOptions = ['Exact', 'Partial', 'Broad'];
const alignmentTypeOptions = ['Knowledge', 'Skill', 'Practice', 'Process'];

const selectedUnit = computed<StaffCoursePlanUnit | null>(() => {
	return (
		surface.value?.curriculum.units.find(unit => unit.unit_plan === selectedUnitPlan.value) || null
	);
});

const canManagePlan = computed(() => Boolean(surface.value?.course_plan.can_manage_resources));
const showUnitEditor = computed(() => Boolean(selectedUnit.value || creatingUnit.value));

function nextId() {
	return nextLocalId.value++;
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

function applySurfaceSelection(payload: StaffCoursePlanSurfaceResponse) {
	syncCoursePlanForm(payload);

	const requestedUnit = String(props.unitPlan || '').trim();
	if (creatingUnit.value && !requestedUnit) {
		return;
	}

	const resolvedUnit = payload.resolved.unit_plan || payload.curriculum.units[0]?.unit_plan || '';
	const nextSelectedUnit = payload.curriculum.units.some(unit => unit.unit_plan === requestedUnit)
		? requestedUnit
		: resolvedUnit;

	selectedUnitPlan.value = nextSelectedUnit;
	creatingUnit.value = false;
	syncUnitForm(payload.curriculum.units.find(unit => unit.unit_plan === nextSelectedUnit) || null);
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
	selectedUnitPlan.value = '';
	syncUnitForm(null);
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
		toast.success(wasCreating ? 'Unit plan created.' : 'Unit plan updated.');
	} catch (error) {
		toast.error(error instanceof Error ? error.message : 'Could not save the unit plan.');
	} finally {
		unitPending.value = false;
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
