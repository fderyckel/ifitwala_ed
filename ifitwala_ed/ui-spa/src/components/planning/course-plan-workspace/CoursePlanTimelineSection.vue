<template>
	<section
		:id="SECTION_IDS.timeline"
		class="scroll-mt-40 rounded-[2rem] border border-line-soft bg-white p-6 shadow-soft"
	>
		<button
			type="button"
			class="flex w-full flex-col gap-4 text-left lg:flex-row lg:items-start lg:justify-between"
			:aria-expanded="!collapsed"
			@click="emit('toggle')"
		>
			<div>
				<p class="type-overline text-ink/60">Curriculum Timeline</p>
				<h2 class="mt-2 type-h2 text-ink">Year-at-a-glance pacing</h2>
				<p class="mt-2 type-body text-ink/80">
					{{
						collapsed
							? 'Open the calendar view to see unit pacing against the real school schedule.'
							: 'See the governed unit sequence against instructional dates, terms, and break periods.'
					}}
				</p>
			</div>
			<div class="flex flex-wrap items-center gap-2 lg:justify-end">
				<span v-if="timelineScopeLabel" class="chip">{{ timelineScopeLabel }}</span>
				<span v-if="timelineDateLabel" class="chip">{{ timelineDateLabel }}</span>
				<span class="chip">{{ timeline.summary.scheduled_unit_count || 0 }} scheduled units</span>
				<span v-if="timeline.holidays.length" class="chip">
					{{ timeline.holidays.length }} holiday spans
				</span>
				<span class="chip">{{ collapsed ? 'Show' : 'Hide' }}</span>
			</div>
		</button>

		<div v-if="!collapsed" class="mt-6">
			<CoursePlanTimelineCard :timeline="timeline" hide-header embedded />
		</div>
	</section>
</template>

<script setup lang="ts">
import CoursePlanTimelineCard from '@/components/planning/CoursePlanTimelineCard.vue';
import { SECTION_IDS } from '@/lib/planning/coursePlanWorkspace';
import type { Response as StaffCoursePlanSurfaceResponse } from '@/types/contracts/staff_teaching/get_staff_course_plan_surface';

defineProps<{
	timeline: StaffCoursePlanSurfaceResponse['curriculum']['timeline'];
	timelineScopeLabel: string;
	timelineDateLabel: string;
	collapsed: boolean;
}>();

const emit = defineEmits<{
	(e: 'toggle'): void;
}>();
</script>
