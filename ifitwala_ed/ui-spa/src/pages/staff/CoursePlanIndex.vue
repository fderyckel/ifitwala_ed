<template>
	<div class="staff-shell space-y-6">
		<section class="overflow-hidden rounded-[2rem] border border-line-soft bg-white shadow-soft">
			<div class="grid gap-6 px-6 py-6 lg:grid-cols-[minmax(0,1fr),auto] lg:items-end">
				<div class="space-y-4">
					<RouterLink
						:to="{ name: 'staff-home' }"
						class="inline-flex items-center gap-2 type-caption text-ink/70 transition hover:text-ink"
					>
						<span>←</span>
						<span>Back to Staff Home</span>
					</RouterLink>
					<div>
						<p class="type-overline text-ink/60">Shared Curriculum Planning</p>
						<h1 class="mt-2 type-h1 text-ink">Course Plans</h1>
						<p class="mt-2 max-w-3xl type-body text-ink/80">
							Open the governed course backbone, shared unit resources, and cross-class reflections
							from one staff workspace.
						</p>
					</div>
				</div>
				<div class="flex flex-wrap gap-2 lg:justify-end">
					<span class="chip">{{ coursePlans.length }} course plans</span>
				</div>
			</div>
		</section>

		<section
			v-if="errorMessage"
			class="rounded-2xl border border-flame/30 bg-[var(--flame)]/5 px-5 py-4"
		>
			<p class="type-body-strong text-flame">Could not load the course plans.</p>
			<p class="mt-1 type-caption text-ink/70">{{ errorMessage }}</p>
		</section>

		<section
			v-else-if="loading && !surface"
			class="rounded-2xl border border-line-soft bg-white px-5 py-8"
		>
			<p class="type-body text-ink/70">Loading shared course plans...</p>
		</section>

		<section
			v-else-if="!coursePlans.length"
			class="rounded-[2rem] border border-line-soft bg-white p-6 shadow-soft"
		>
			<p class="type-body-strong text-ink">No governed course plans are available yet.</p>
			<p class="mt-2 type-body text-ink/70">
				Create the shared course plan first so teachers and curriculum coordinators can work inside
				one governed backbone.
			</p>
		</section>

		<section v-else class="grid gap-4 xl:grid-cols-2">
			<RouterLink
				v-for="plan in coursePlans"
				:key="plan.course_plan"
				:to="{ name: 'staff-course-plan', params: { coursePlan: plan.course_plan } }"
				class="rounded-[2rem] border border-line-soft bg-white p-6 shadow-soft transition hover:-translate-y-0.5 hover:border-jacaranda/40 hover:shadow-strong"
			>
				<div class="flex items-start justify-between gap-4">
					<div class="min-w-0">
						<p class="type-overline text-ink/60">
							{{ plan.course_name || plan.course }}
							<span v-if="plan.academic_year">· {{ plan.academic_year }}</span>
						</p>
						<h2 class="mt-2 type-h3 text-ink">{{ plan.title }}</h2>
						<p v-if="plan.summary" class="mt-3 type-body text-ink/75">
							{{ plan.summary }}
						</p>
					</div>
					<span class="chip">{{ plan.plan_status || 'Draft' }}</span>
				</div>

				<div class="mt-5 flex flex-wrap gap-2">
					<span v-if="plan.course_group" class="chip">{{ plan.course_group }}</span>
					<span v-if="plan.cycle_label" class="chip">{{ plan.cycle_label }}</span>
					<span class="chip">
						{{ plan.can_manage_resources ? 'Can edit resources' : 'Read-only access' }}
					</span>
				</div>
			</RouterLink>
		</section>
	</div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';

import { getStaffCoursePlanIndex } from '@/lib/services/staff/staffTeachingService';
import type { Response as StaffCoursePlanIndexResponse } from '@/types/contracts/staff_teaching/get_staff_course_plan_index';

const surface = ref<StaffCoursePlanIndexResponse | null>(null);
const loading = ref(false);
const errorMessage = ref('');

const coursePlans = computed(() => surface.value?.course_plans || []);

async function loadIndex() {
	loading.value = true;
	errorMessage.value = '';
	try {
		surface.value = await getStaffCoursePlanIndex();
	} catch (error) {
		surface.value = null;
		errorMessage.value = error instanceof Error ? error.message : 'Unknown error';
	} finally {
		loading.value = false;
	}
}

onMounted(() => {
	loadIndex();
});
</script>
