<template>
	<div class="staff-shell space-y-6">
		<section class="overflow-hidden rounded-[2rem] border border-line-soft bg-white shadow-soft">
			<div class="space-y-4 px-6 py-6">
				<RouterLink
					:to="{ name: 'staff-home' }"
					class="inline-flex items-center gap-2 type-caption text-ink/70 transition hover:text-ink"
				>
					<span>←</span>
					<span>Back to Staff Home</span>
				</RouterLink>
				<div class="page-header">
					<div class="page-header__intro">
						<p class="type-overline text-ink/60">Shared Curriculum Planning</p>
						<h1 class="mt-2 type-h1 text-canopy">Course Plans</h1>
						<p class="mt-2 max-w-3xl type-meta text-slate-token/80">
							Open the governed course backbone, shared unit resources, and cross-class reflections
							from one staff workspace.
						</p>
					</div>
					<div class="page-header__actions">
						<span class="chip">{{ coursePlans.length }} course plans</span>
						<span v-if="canCreateCoursePlans" class="chip">
							{{ courseOptions.length }} courses ready to plan
						</span>
					</div>
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
			v-else-if="surface"
			class="grid gap-6 xl:grid-cols-[minmax(0,1.2fr),minmax(0,0.95fr)]"
		>
			<div class="rounded-[2rem] border border-line-soft bg-white p-6 shadow-soft">
				<p class="type-overline text-ink/60">Shared Planning Workflow</p>
				<h2 class="mt-2 type-h2 text-ink">
					Start the governed backbone where teachers already work
				</h2>
				<p class="mt-3 max-w-2xl type-body text-ink/80">
					Create the shared course plan here, then move straight into units, shared resources, quiz
					banks, and assign-ready curriculum assets without switching tools.
				</p>
				<div class="mt-5 flex flex-wrap gap-2">
					<span class="chip">One SPA-first workflow</span>
					<span class="chip">Multiple plans per course allowed</span>
					<span class="chip">Direct handoff into the governed workspace</span>
				</div>
			</div>

			<section class="rounded-[2rem] border border-line-soft bg-white p-6 shadow-soft">
				<div class="flex items-start justify-between gap-4">
					<div>
						<p class="type-overline text-ink/60">New Course Plan</p>
						<h2 class="mt-2 type-h3 text-ink">Create and open the workspace</h2>
					</div>
					<span class="chip">{{ canCreateCoursePlans ? 'Ready' : 'Blocked' }}</span>
				</div>

				<div
					v-if="createBlockReason && !canCreateCoursePlans"
					class="mt-5 rounded-2xl border border-line-soft bg-surface-soft px-4 py-4"
				>
					<p class="type-body text-ink/80">{{ createBlockReason }}</p>
				</div>

				<form v-else class="mt-5 space-y-4" @submit.prevent="handleCreateCoursePlan">
					<div
						v-if="createBlockReason"
						class="rounded-2xl border border-line-soft bg-surface-soft px-4 py-4"
					>
						<p class="type-body text-ink/80">{{ createBlockReason }}</p>
					</div>

					<label class="block space-y-2">
						<span class="type-caption text-ink/70">Find Course</span>
						<input
							v-model="courseSearch"
							type="text"
							class="if-input w-full"
							:disabled="!courseOptions.length || createPending"
							placeholder="Search by course, group, or school"
						/>
					</label>

					<label class="block space-y-2">
						<span class="type-caption text-ink/70">Course</span>
						<select
							v-model="createForm.course"
							class="if-input w-full"
							:disabled="!courseOptions.length || createPending"
						>
							<option value="">Select the course to govern</option>
							<option
								v-for="course in visibleCourseOptions"
								:key="course.course"
								:value="course.course"
							>
								{{ course.course_name }}
								{{ course.course_group ? ` · ${course.course_group}` : '' }}
								{{ course.school ? ` · ${course.school}` : '' }}
							</option>
						</select>
						<p
							v-if="courseOptions.length && !visibleCourseOptions.length"
							class="type-caption text-ink/60"
						>
							No courses match that search yet.
						</p>
					</label>

					<label class="block space-y-2">
						<span class="type-caption text-ink/70">Course Plan Title</span>
						<input
							v-model="createForm.title"
							type="text"
							class="if-input w-full"
							:disabled="createPending"
							placeholder="Defaults to the course name"
						/>
					</label>

					<div class="grid gap-4 lg:grid-cols-2">
						<label class="block space-y-2">
							<span class="type-caption text-ink/70">Academic Year</span>
							<select
								v-model="createForm.academic_year"
								class="if-input w-full"
								:disabled="createPending || !selectedCourseAcademicYearOptions.length"
							>
								<option value="">Optional academic year</option>
								<option
									v-for="option in selectedCourseAcademicYearOptions"
									:key="option.value"
									:value="option.value"
								>
									{{ option.label }}
								</option>
							</select>
							<p class="type-caption text-ink/60">
								{{
									createForm.course
										? selectedCourseAcademicYearOptions.length
											? 'Only Academic Year records in this course school scope are available here.'
											: 'No Academic Year records are available for this course school yet.'
										: 'Choose a course first to load Academic Year records.'
								}}
							</p>
						</label>

						<label class="block space-y-2">
							<span class="type-caption text-ink/70">Cycle Label</span>
							<input
								v-model="createForm.cycle_label"
								type="text"
								class="if-input w-full"
								:disabled="createPending"
								placeholder="e.g. Semester 1"
							/>
						</label>
					</div>

					<label class="block space-y-2">
						<span class="type-caption text-ink/70">Publishing Status</span>
						<select
							v-model="createForm.plan_status"
							class="if-input w-full"
							:disabled="createPending"
						>
							<option v-for="option in coursePlanStatusOptions" :key="option" :value="option">
								{{ option }}
							</option>
						</select>
					</label>

					<label class="block space-y-2">
						<span class="type-caption text-ink/70">Summary</span>
						<textarea
							v-model="createForm.summary"
							rows="4"
							class="if-input min-h-[7.5rem] w-full resize-y"
							:disabled="createPending"
							placeholder="Capture the shared intent and non-negotiables, or leave this for the workspace."
						/>
					</label>

					<p v-if="createError" class="type-caption text-flame">{{ createError }}</p>

					<div class="flex justify-end">
						<button
							type="submit"
							class="if-action"
							:disabled="createPending || !createForm.course || !courseOptions.length"
						>
							{{ createPending ? 'Creating...' : 'Create Course Plan' }}
						</button>
					</div>
				</form>
			</section>
		</section>

		<section
			v-if="surface && !coursePlans.length"
			class="rounded-[2rem] border border-line-soft bg-white p-6 shadow-soft"
		>
			<p class="type-body-strong text-ink">No governed course plans are available yet.</p>
			<p class="mt-2 type-body text-ink/70">
				{{
					canCreateCoursePlans
						? 'Start the first shared course plan above so teachers and curriculum coordinators can work inside one governed backbone.'
						: createBlockReason ||
							'A curriculum lead needs to create the first governed course plan.'
				}}
			</p>
		</section>

		<section v-if="surface && coursePlans.length" class="grid gap-4 xl:grid-cols-2">
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
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { RouterLink, useRouter } from 'vue-router';

import { toast } from 'frappe-ui';

import {
	createCoursePlan,
	getStaffCoursePlanIndex,
} from '@/lib/services/staff/staffTeachingService';
import type { Response as StaffCoursePlanIndexResponse } from '@/types/contracts/staff_teaching/get_staff_course_plan_index';

const router = useRouter();
const surface = ref<StaffCoursePlanIndexResponse | null>(null);
const loading = ref(false);
const errorMessage = ref('');
const createPending = ref(false);
const createError = ref('');
const courseSearch = ref('');

const coursePlanStatusOptions = ['Draft', 'Active', 'Archived'];
const createForm = reactive({
	course: '',
	title: '',
	academic_year: '',
	cycle_label: '',
	plan_status: 'Draft',
	summary: '',
});

const coursePlans = computed(() => surface.value?.course_plans || []);
const courseOptions = computed(() => surface.value?.course_options || []);
const selectedCourseOption = computed(
	() => courseOptions.value.find(option => option.course === createForm.course) || null
);
const selectedCourseAcademicYearOptions = computed(
	() => selectedCourseOption.value?.academic_year_options || []
);
const visibleCourseOptions = computed(() => {
	const query = courseSearch.value.trim().toLowerCase();
	if (!query) return courseOptions.value;
	return courseOptions.value.filter(option =>
		[option.course_name, option.course_group, option.school, option.course]
			.filter(Boolean)
			.some(value => String(value).toLowerCase().includes(query))
	);
});
const canCreateCoursePlans = computed(() =>
	Boolean(surface.value?.access?.can_create_course_plans)
);
const createBlockReason = computed(() => surface.value?.access?.create_block_reason || '');

function defaultTitleForCourse(course: string | null | undefined): string {
	const selected = courseOptions.value.find(option => option.course === course);
	return selected?.course_name ? `${selected.course_name} Plan` : '';
}

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

async function handleCreateCoursePlan() {
	if (!createForm.course) {
		createError.value = 'Choose a course before creating the shared plan.';
		return;
	}

	createPending.value = true;
	createError.value = '';
	try {
		const payload = await createCoursePlan({
			course: createForm.course,
			title: createForm.title.trim() || undefined,
			academic_year: createForm.academic_year.trim() || undefined,
			cycle_label: createForm.cycle_label.trim() || undefined,
			plan_status: createForm.plan_status || 'Draft',
			summary: createForm.summary.trim() || undefined,
		});
		toast.success('Course plan created.');
		await router.push({
			name: 'staff-course-plan',
			params: { coursePlan: payload.course_plan },
		});
	} catch (error) {
		createError.value =
			error instanceof Error ? error.message : 'Could not create the course plan.';
		toast.error(createError.value);
	} finally {
		createPending.value = false;
	}
}

watch(
	courseOptions,
	options => {
		if (!createForm.course && options.length === 1) {
			createForm.course = options[0].course;
		}
	},
	{ immediate: true }
);

watch(
	() => createForm.course,
	(course, previousCourse) => {
		const nextDefault = defaultTitleForCourse(course);
		const previousDefault = defaultTitleForCourse(previousCourse);
		if (!createForm.title.trim() || createForm.title.trim() === previousDefault) {
			createForm.title = nextDefault;
		}
		if (
			createForm.academic_year &&
			!selectedCourseAcademicYearOptions.value.some(
				option => option.value === createForm.academic_year
			)
		) {
			createForm.academic_year = '';
		}
		createError.value = '';
	}
);

watch(courseOptions, options => {
	if (createForm.course && !options.some(option => option.course === createForm.course)) {
		createForm.course = '';
	}
});

onMounted(() => {
	loadIndex();
});
</script>
