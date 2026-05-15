<template>
	<section class="overflow-hidden rounded-[2rem] border border-line-soft bg-white shadow-soft">
		<div class="course-plan-workspace-header">
			<div class="space-y-4">
				<RouterLink
					:to="{ name: 'staff-course-plan-index' }"
					class="inline-flex items-center gap-2 type-caption text-ink/70 transition hover:text-ink"
				>
					<span>←</span>
					<span>Back to Course Plans</span>
				</RouterLink>
				<div class="page-header">
					<div class="page-header__intro">
						<p class="type-overline text-ink/60">Governed Curriculum</p>
						<h1 class="mt-2 type-h1 text-canopy">
							{{ surface?.course_plan.title || coursePlan || 'Course Plan' }}
						</h1>
						<p class="mt-2 max-w-3xl type-meta text-slate-token/80">
							Shape the shared course backbone, capture reusable unit guidance, and build quiz
							banks teachers can assign without leaving the staff SPA.
						</p>
					</div>
					<div class="page-header__actions">
						<button
							type="button"
							class="chip cursor-pointer transition hover:border-jacaranda/40 hover:bg-sky/20 hover:text-ink"
							@click="emit('jump-to-section', SECTION_IDS.overview)"
						>
							{{ surface?.course_plan.course_name || 'Course pending' }}
						</button>
						<button
							type="button"
							class="chip cursor-pointer transition hover:border-jacaranda/40 hover:bg-sky/20 hover:text-ink"
							@click="emit('jump-to-section', SECTION_IDS.units)"
						>
							{{ surface?.curriculum.unit_count || 0 }} units
						</button>
						<button
							type="button"
							class="chip cursor-pointer transition hover:border-jacaranda/40 hover:bg-sky/20 hover:text-ink"
							@click="emit('jump-to-section', SECTION_IDS.quizBanks)"
						>
							{{ surface?.assessment.quiz_question_banks.length || 0 }} quiz banks
						</button>
						<span class="chip">{{ surface?.course_plan.plan_status || 'Draft' }}</span>
						<span class="chip">{{ canManagePlan ? 'Editable' : 'Read only' }}</span>
					</div>
				</div>
			</div>

			<template v-if="surface && navigationSections.length">
				<div class="course-plan-workspace-header__divider" />

				<div class="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
					<div class="min-w-0">
						<p class="type-overline text-ink/55">Quick Access</p>
						<p class="mt-1 type-caption text-ink/65">
							Jump to the next planning area without losing your place.
						</p>
					</div>

					<div v-if="canManagePlan" class="flex flex-wrap gap-2">
						<button
							type="button"
							class="if-action"
							:disabled="!selectedUnit"
							@click="emit('quick-edit-unit')"
						>
							Edit Unit
						</button>
						<button
							type="button"
							class="if-action"
							:disabled="!selectedUnit"
							@click="emit('quick-upload-unit-file')"
						>
							Upload Unit PDF
						</button>
						<button
							type="button"
							class="if-action"
							:disabled="!selectedUnit"
							@click="emit('quick-add-reflection')"
						>
							Add Reflection
						</button>
						<button type="button" class="if-action" @click="emit('quick-start-quiz-bank')">
							New Quiz Bank
						</button>
					</div>
				</div>

				<div class="mt-3 flex gap-2 overflow-x-auto pb-1">
					<button
						v-for="section in navigationSections"
						:key="section.id"
						type="button"
						class="course-plan-quick-access-pill"
						:class="
							activeSectionId === section.id
								? 'course-plan-quick-access-pill--active'
								: 'course-plan-quick-access-pill--idle'
						"
						@click="emit('jump-to-section', section.id)"
					>
						<span>{{ section.label }}</span>
						<span
							v-if="section.count !== undefined && section.count !== null"
							class="course-plan-quick-access-pill__count"
						>
							{{ section.count }}
						</span>
					</button>
				</div>

				<p v-if="canManagePlan && !selectedUnit" class="mt-3 type-caption text-ink/65">
					Select a governed unit first to unlock reflection and unit-resource shortcuts.
				</p>
			</template>
		</div>
	</section>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router';

import type { Response as StaffCoursePlanSurfaceResponse } from '@/types/contracts/staff_teaching/get_staff_course_plan_surface';
import type { StaffCoursePlanUnit } from '@/types/contracts/staff_teaching/get_staff_course_plan_surface';
import {
	SECTION_IDS,
	type WorkspaceNavigationSection,
	type WorkspaceSectionId,
} from '@/lib/planning/coursePlanWorkspace';

defineProps<{
	coursePlan?: string;
	surface: StaffCoursePlanSurfaceResponse | null;
	canManagePlan: boolean;
	navigationSections: WorkspaceNavigationSection[];
	activeSectionId: WorkspaceSectionId;
	selectedUnit: StaffCoursePlanUnit | null;
}>();

const emit = defineEmits<{
	(e: 'jump-to-section', sectionId: WorkspaceSectionId): void;
	(e: 'quick-edit-unit'): void;
	(e: 'quick-upload-unit-file'): void;
	(e: 'quick-add-reflection'): void;
	(e: 'quick-start-quiz-bank'): void;
}>();
</script>
