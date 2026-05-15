<template>
	<section
		:id="SECTION_IDS.overview"
		class="scroll-mt-40 rounded-[2rem] border border-line-soft bg-white p-6 shadow-soft"
	>
		<button
			type="button"
			class="flex w-full flex-col gap-4 text-left lg:flex-row lg:items-start lg:justify-between"
			:aria-expanded="!collapsed"
			@click="emit('toggle')"
		>
			<div>
				<p class="type-overline text-ink/60">Course Plan Overview</p>
				<h2 class="mt-2 type-h2 text-ink">
					{{ coursePlanSurface?.course_name || coursePlanSurface?.course }}
				</h2>
				<p class="mt-2 type-body text-ink/80">
					{{
						collapsed
							? 'Open the shared plan metadata, summary, and publishing controls.'
							: 'This shared plan sets the governed backbone every linked class teaching plan uses.'
					}}
				</p>
			</div>
			<div class="flex flex-wrap items-center gap-2 lg:justify-end">
				<span v-if="coursePlanSurface?.course_group" class="chip">
					{{ coursePlanSurface.course_group }}
				</span>
				<span v-if="coursePlanSurface?.academic_year" class="chip">
					{{ coursePlanSurface.academic_year }}
				</span>
				<span v-if="coursePlanSurface?.cycle_label" class="chip">
					{{ coursePlanSurface.cycle_label }}
				</span>
				<span class="chip">{{ collapsed ? 'Show' : 'Hide' }}</span>
			</div>
		</button>

		<div v-if="!collapsed && canManagePlan" class="mt-6 grid gap-4 lg:grid-cols-2">
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
				<select
					v-model="coursePlanForm.academic_year"
					class="if-input w-full"
					:disabled="!academicYearOptions.length"
				>
					<option value="">Optional academic year</option>
					<option v-for="option in academicYearOptions" :key="option.value" :value="option.value">
						{{ option.label }}
					</option>
				</select>
				<p class="type-caption text-ink/60">
					{{
						academicYearOptions.length
							? 'Only Academic Year records in this course school scope are available here.'
							: 'No Academic Year records are available for this course school yet.'
					}}
				</p>
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
				<PlanningRichTextField
					v-model="coursePlanForm.summary"
					placeholder="State the shared purpose, scope, and non-negotiables for this course plan."
					min-height-class="min-h-[9rem]"
				/>
			</label>
			<div class="flex justify-end lg:col-span-2">
				<button type="button" class="if-action" :disabled="pending" @click="emit('save')">
					{{ pending ? 'Saving...' : 'Save Shared Course Plan' }}
				</button>
			</div>
		</div>

		<div
			v-else-if="!collapsed"
			class="mt-6 rounded-2xl border border-line-soft bg-surface-soft p-5"
		>
			<PlanningRichTextField
				v-if="hasRichTextContent(coursePlanSurface?.summary)"
				:model-value="coursePlanSurface?.summary"
				:editable="false"
				display-class="text-ink/80"
			/>
			<p v-else class="type-caption text-ink/70">
				No shared summary has been captured for this course plan yet.
			</p>
		</div>
	</section>
</template>

<script setup lang="ts">
import PlanningRichTextField from '@/components/planning/PlanningRichTextField.vue';
import {
	SECTION_IDS,
	coursePlanStatusOptions,
	hasRichTextContent,
	type CoursePlanFormState,
} from '@/lib/planning/coursePlanWorkspace';
import type { Response as StaffCoursePlanSurfaceResponse } from '@/types/contracts/staff_teaching/get_staff_course_plan_surface';

defineProps<{
	coursePlanSurface: StaffCoursePlanSurfaceResponse['course_plan'] | null;
	coursePlanForm: CoursePlanFormState;
	academicYearOptions: Array<{ label: string; value: string }>;
	canManagePlan: boolean;
	collapsed: boolean;
	pending: boolean;
}>();

const emit = defineEmits<{
	(e: 'toggle'): void;
	(e: 'save'): void;
}>();
</script>
