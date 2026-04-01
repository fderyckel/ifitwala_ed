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
							Review the shared unit backbone, manage governed resources, and start each unit with
							a bird's-eye view of reflections across classes.
						</p>
					</div>
				</div>
				<div class="flex flex-wrap gap-2 lg:justify-end">
					<span class="chip">{{ surface?.course_plan.course_name || 'Course pending' }}</span>
					<span class="chip">{{ surface?.curriculum.unit_count || 0 }} units</span>
					<span class="chip">{{ surface?.course_plan.plan_status || 'Draft' }}</span>
					<span class="chip">
						{{ canManageResources ? 'Editable' : 'Read only' }}
					</span>
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
				<div class="grid gap-4 lg:grid-cols-[minmax(0,1fr),auto] lg:items-start">
					<div>
						<p class="type-overline text-ink/60">Course Plan Overview</p>
						<h2 class="mt-2 type-h2 text-ink">
							{{ surface.course_plan.course_name || surface.course_plan.course }}
						</h2>
						<p v-if="surface.course_plan.summary" class="mt-3 type-body text-ink/80">
							{{ surface.course_plan.summary }}
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
			</section>

			<section class="grid gap-6 xl:grid-cols-[minmax(0,20rem),minmax(0,1fr)]">
				<aside class="space-y-6 xl:self-start">
					<PlanningResourcePanel
						anchor-doctype="Course Plan"
						:anchor-name="surface.course_plan.course_plan"
						:can-manage="canManageResources"
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

						<div
							v-if="!surface.curriculum.units.length"
							class="rounded-2xl border border-dashed border-line-soft p-4"
						>
							<p class="type-caption text-ink/70">
								Add unit plans to this course plan to define the shared teaching backbone.
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
									</div>
									<span class="chip">{{ unit.shared_resources.length }} resources</span>
								</div>
							</button>
						</div>
					</section>
				</aside>

				<section
					v-if="selectedUnit"
					class="space-y-6 rounded-[2rem] border border-line-soft bg-white p-6 shadow-soft"
				>
					<div class="grid gap-4 lg:grid-cols-[minmax(0,1fr),auto] lg:items-start">
						<div>
							<p class="type-overline text-ink/60">Selected Unit</p>
							<h2 class="mt-2 type-h2 text-ink">{{ selectedUnit.title }}</h2>
							<p class="mt-2 type-body text-ink/80">
								This is the governed backbone every class teaching plan inherits before teachers
								adapt pacing and session design.
							</p>
						</div>
						<div class="flex flex-wrap gap-2">
							<span class="chip">Unit {{ selectedUnit.unit_order || '—' }}</span>
							<span v-if="selectedUnit.unit_status" class="chip">{{
								selectedUnit.unit_status
							}}</span>
							<span v-if="selectedUnit.duration" class="chip">{{ selectedUnit.duration }}</span>
							<span v-if="selectedUnit.estimated_duration" class="chip">
								{{ selectedUnit.estimated_duration }}
							</span>
						</div>
					</div>

					<div class="grid gap-4 lg:grid-cols-2">
						<div
							v-if="selectedUnit.overview"
							class="rounded-2xl border border-line-soft bg-surface-soft p-4"
						>
							<p class="type-overline text-ink/60">Overview</p>
							<p class="mt-2 type-body text-ink/80">{{ selectedUnit.overview }}</p>
						</div>
						<div
							v-if="selectedUnit.essential_understanding"
							class="rounded-2xl border border-line-soft bg-surface-soft p-4"
						>
							<p class="type-overline text-ink/60">Essential Understanding</p>
							<p class="mt-2 type-body text-ink/80">{{ selectedUnit.essential_understanding }}</p>
						</div>
						<div
							v-if="selectedUnit.content"
							class="rounded-2xl border border-line-soft bg-surface-soft p-4"
						>
							<p class="type-overline text-ink/60">Content</p>
							<p class="mt-2 type-body text-ink/80">{{ selectedUnit.content }}</p>
						</div>
						<div
							v-if="selectedUnit.skills"
							class="rounded-2xl border border-line-soft bg-surface-soft p-4"
						>
							<p class="type-overline text-ink/60">Skills</p>
							<p class="mt-2 type-body text-ink/80">{{ selectedUnit.skills }}</p>
						</div>
						<div
							v-if="selectedUnit.concepts"
							class="rounded-2xl border border-line-soft bg-surface-soft p-4"
						>
							<p class="type-overline text-ink/60">Concepts</p>
							<p class="mt-2 type-body text-ink/80">{{ selectedUnit.concepts }}</p>
						</div>
						<div
							v-if="selectedUnit.misconceptions"
							class="rounded-2xl border border-line-soft bg-surface-soft p-4"
						>
							<p class="type-overline text-ink/60">Likely Misconceptions</p>
							<p class="mt-2 type-body text-ink/80">{{ selectedUnit.misconceptions }}</p>
						</div>
					</div>

					<div v-if="selectedUnit.standards.length" class="space-y-3">
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
								<p class="type-body-strong text-ink">
									{{ standard.standard_code || 'Standard' }}
								</p>
								<p v-if="standard.standard_description" class="mt-2 type-body text-ink/80">
									{{ standard.standard_description }}
								</p>
								<div class="mt-3 flex flex-wrap gap-2">
									<span v-if="standard.coverage_level" class="chip">
										{{ standard.coverage_level }}
									</span>
									<span v-if="standard.strand" class="chip">{{ standard.strand }}</span>
									<span v-if="standard.program" class="chip">{{ standard.program }}</span>
								</div>
							</article>
						</div>
					</div>

					<div v-if="selectedUnit.shared_reflections?.length" class="space-y-3">
						<div class="flex items-center justify-between gap-3">
							<h3 class="type-h3 text-ink">Shared Reflections</h3>
							<span class="chip">{{ selectedUnit.shared_reflections.length }}</span>
						</div>
						<div class="grid gap-3">
							<article
								v-for="(reflection, index) in selectedUnit.shared_reflections"
								:key="`${selectedUnit.unit_plan}-shared-${index}`"
								class="rounded-2xl border border-line-soft bg-surface-soft p-4"
							>
								<p v-if="reflection.prior_to_the_unit" class="type-body text-ink/80">
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

					<div v-if="selectedUnit.class_reflections?.length" class="space-y-3">
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
					</div>

					<PlanningResourcePanel
						anchor-doctype="Unit Plan"
						:anchor-name="selectedUnit.unit_plan"
						:can-manage="canManageResources"
						eyebrow="Unit Resources"
						title="Shared resources for this unit"
						description="Use this layer for governed materials every class should inherit while teaching the unit."
						empty-message="No governed unit resources yet."
						blocked-message="Choose a unit plan before sharing resources."
						read-only-message="Only approved curriculum staff can edit shared unit resources."
						:resources="selectedUnit.shared_resources"
						@changed="loadSurface"
					/>
				</section>

				<section v-else class="rounded-[2rem] border border-line-soft bg-white p-6 shadow-soft">
					<p class="type-body text-ink/70">
						Select a governed unit to review resources and reflections.
					</p>
				</section>
			</section>
		</template>
	</div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import PlanningResourcePanel from '@/components/planning/PlanningResourcePanel.vue';
import { getStaffCoursePlanSurface } from '@/lib/services/staff/staffTeachingService';
import type {
	Response as StaffCoursePlanSurfaceResponse,
	StaffCoursePlanUnit,
} from '@/types/contracts/staff_teaching/get_staff_course_plan_surface';

const props = defineProps<{
	coursePlan: string;
	unitPlan?: string;
}>();

const route = useRoute();
const router = useRouter();

const surface = ref<StaffCoursePlanSurfaceResponse | null>(null);
const loading = ref(false);
const errorMessage = ref('');
const selectedUnitPlan = ref('');
const loadToken = ref(0);

const selectedUnit = computed<StaffCoursePlanUnit | null>(() => {
	return (
		surface.value?.curriculum.units.find(unit => unit.unit_plan === selectedUnitPlan.value) || null
	);
});

const canManageResources = computed(() =>
	Boolean(surface.value?.course_plan.can_manage_resources)
);

function applySurfaceSelection(payload: StaffCoursePlanSurfaceResponse) {
	const requestedUnit = String(props.unitPlan || '').trim();
	const resolvedUnit = payload.resolved.unit_plan || payload.curriculum.units[0]?.unit_plan || '';
	const nextSelectedUnit = payload.curriculum.units.some(unit => unit.unit_plan === requestedUnit)
		? requestedUnit
		: resolvedUnit;
	selectedUnitPlan.value = nextSelectedUnit;
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
	selectedUnitPlan.value = unitPlan;
	await router.replace({
		name: 'staff-course-plan',
		params: { coursePlan: props.coursePlan },
		query: {
			...route.query,
			unit_plan: unitPlan || undefined,
		},
	});
}

watch(
	() => [props.coursePlan, props.unitPlan],
	() => {
		loadSurface();
	},
	{ immediate: true }
);
</script>
