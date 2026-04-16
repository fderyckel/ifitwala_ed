<template>
	<aside class="space-y-6 xl:self-start">
		<section
			:id="SECTION_IDS.courseResources"
			class="scroll-mt-40 rounded-[2rem] border border-line-soft bg-white p-6 shadow-soft"
		>
			<button
				type="button"
				class="flex w-full flex-col gap-4 text-left lg:flex-row lg:items-start lg:justify-between"
				:aria-expanded="!courseResourcesCollapsed"
				@click="emit('toggle-course-resources')"
			>
				<div>
					<p class="type-overline text-ink/60">Shared Plan Resources</p>
					<h2 class="mt-2 type-h2 text-ink">Resources for every class using this plan</h2>
					<p class="mt-2 type-body text-ink/80">
						{{
							courseResourcesCollapsed
								? 'Open the governed references, links, and shared files attached at the course-plan level.'
								: 'Keep governed references, anchor texts, and shared files at the course-plan level.'
						}}
					</p>
				</div>
				<div class="flex flex-wrap items-center gap-2 lg:justify-end">
					<span class="chip">{{ coursePlanResourceCount }} resources</span>
					<span class="chip">{{ courseResourcesCollapsed ? 'Show' : 'Hide' }}</span>
				</div>
			</button>

			<div v-if="!courseResourcesCollapsed" class="mt-6">
				<PlanningResourcePanel
					anchor-doctype="Course Plan"
					:anchor-name="coursePlanName"
					:can-manage="canManagePlan"
					eyebrow="Shared Plan Resources"
					title="Resources for every class using this plan"
					description="Keep governed references, anchor texts, and shared files at the course-plan level."
					empty-message="No shared course-plan resources yet."
					blocked-message="Choose a course plan before sharing resources."
					read-only-message="Only approved curriculum staff can edit shared course-plan resources."
					:resources="coursePlanResources"
					enable-attachment-preview
					hide-header
					embedded
					@changed="emit('resource-changed')"
				/>
			</div>
		</section>

		<section
			:id="SECTION_IDS.units"
			class="scroll-mt-40 rounded-[2rem] border border-line-soft bg-white p-5 shadow-soft"
		>
			<div class="mb-4 flex items-center justify-between gap-3">
				<div>
					<p class="type-overline text-ink/60">Unit Backbone</p>
					<h2 class="mt-1 type-h3 text-ink">Governed sequence</h2>
				</div>
				<span class="chip">{{ unitCount }}</span>
			</div>

			<div class="space-y-3">
				<button
					v-for="unit in units"
					:key="unit.unit_plan"
					type="button"
					class="w-full rounded-2xl border p-4 text-left transition"
					:class="
						selectedUnitPlan === unit.unit_plan && !creatingUnit
							? 'border-jacaranda bg-jacaranda/10 shadow-soft'
							: 'border-line-soft bg-surface-soft hover:border-jacaranda/40'
					"
					@click="emit('select-unit', unit.unit_plan)"
				>
					<div class="flex items-start justify-between gap-3">
						<div class="min-w-0">
							<p class="type-overline text-ink/60">Unit {{ unit.unit_order || '—' }}</p>
							<p class="mt-1 type-body-strong text-ink">{{ unit.title }}</p>
						</div>
						<span class="chip">{{ unit.shared_resources.length }} resources</span>
					</div>
				</button>

				<div v-if="!units.length" class="rounded-2xl border border-dashed border-line-soft p-4">
					<p class="type-caption text-ink/70">
						Add the first unit plan to define the shared curriculum backbone.
					</p>
				</div>
			</div>

			<div v-if="canManagePlan" class="mt-4">
				<button type="button" class="if-action w-full" @click="emit('start-new-unit')">
					{{ creatingUnit ? 'Editing New Unit' : 'New Unit Plan' }}
				</button>
			</div>
		</section>
	</aside>
</template>

<script setup lang="ts">
import PlanningResourcePanel from '@/components/planning/PlanningResourcePanel.vue';
import { SECTION_IDS } from '@/lib/planning/coursePlanWorkspace';
import type { Response as StaffCoursePlanSurfaceResponse } from '@/types/contracts/staff_teaching/get_staff_course_plan_surface';

defineProps<{
	coursePlanName: string;
	coursePlanResources: StaffCoursePlanSurfaceResponse['resources']['course_plan_resources'];
	canManagePlan: boolean;
	coursePlanResourceCount: number;
	courseResourcesCollapsed: boolean;
	units: StaffCoursePlanSurfaceResponse['curriculum']['units'];
	unitCount: number;
	selectedUnitPlan: string;
	creatingUnit: boolean;
}>();

const emit = defineEmits<{
	(e: 'toggle-course-resources'): void;
	(e: 'resource-changed'): void;
	(e: 'select-unit', unitPlan: string): void;
	(e: 'start-new-unit'): void;
}>();
</script>
