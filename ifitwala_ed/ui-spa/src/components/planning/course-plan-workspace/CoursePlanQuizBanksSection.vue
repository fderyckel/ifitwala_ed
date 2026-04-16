<template>
	<section
		:id="SECTION_IDS.quizBanks"
		class="scroll-mt-40 rounded-[2rem] border border-line-soft bg-white p-6 shadow-soft"
	>
		<button
			type="button"
			class="flex w-full flex-col gap-4 text-left lg:flex-row lg:items-start lg:justify-between"
			:aria-expanded="!collapsed"
			@click="emit('toggle')"
		>
			<div>
				<p class="type-overline text-ink/60">Course Quiz Banks</p>
				<h2 class="mt-2 type-h2 text-ink">Shared quiz authoring</h2>
				<p class="mt-2 type-body text-ink/80">
					{{
						collapsed
							? 'Open the course-level question banks when you need to author, revise, or assign a reusable quiz.'
							: 'Build question banks once, then assign them through the class task flow without rewriting the quiz each time.'
					}}
				</p>
			</div>
			<div class="flex flex-wrap items-center gap-2 lg:justify-end">
				<span class="chip">{{ quizQuestionBanks.length }} banks</span>
				<span v-if="selectedQuizBankLabel" class="chip">{{ selectedQuizBankLabel }}</span>
				<span class="chip">{{ collapsed ? 'Show' : 'Hide' }}</span>
			</div>
		</button>

		<div v-if="!collapsed" class="mt-6 grid gap-6 xl:grid-cols-[minmax(0,20rem),minmax(0,1fr)]">
			<aside class="space-y-4 xl:self-start">
				<section class="rounded-[1.75rem] border border-line-soft bg-surface-soft/55 p-5">
					<div class="mb-4 flex items-center justify-between gap-3">
						<div>
							<p class="type-overline text-ink/60">Course Quiz Banks</p>
							<h2 class="mt-1 type-h3 text-ink">Shared quiz authoring</h2>
						</div>
						<span class="chip">{{ quizQuestionBanks.length }}</span>
					</div>

					<p class="mb-4 type-caption text-ink/70">
						Quiz banks are shared at the course level so teachers can assign them later from the
						class task flow.
					</p>

					<div class="space-y-3">
						<button
							v-for="bank in quizQuestionBanks"
							:key="bank.quiz_question_bank"
							type="button"
							class="w-full rounded-2xl border p-4 text-left transition"
							:class="
								selectedQuizQuestionBank?.quiz_question_bank === bank.quiz_question_bank &&
								!creatingQuizQuestionBank
									? 'border-jacaranda bg-jacaranda/10 shadow-soft'
									: 'border-line-soft bg-surface-soft hover:border-jacaranda/40'
							"
							@click="emit('select-bank', bank.quiz_question_bank)"
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
							v-if="!quizQuestionBanks.length"
							class="rounded-2xl border border-dashed border-line-soft p-4"
						>
							<p class="type-caption text-ink/70">No course quiz banks yet.</p>
						</div>
					</div>

					<div v-if="canManagePlan" class="mt-4">
						<button type="button" class="if-action w-full" @click="emit('start-new-bank')">
							{{ creatingQuizQuestionBank ? 'Editing New Quiz Bank' : 'New Quiz Bank' }}
						</button>
					</div>
				</section>
			</aside>

			<section class="rounded-[1.75rem] border border-line-soft bg-surface-soft/40 p-6">
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
							class="if-action"
							:disabled="!selectedQuizQuestionBank.is_published"
							@click="emit('assign-quiz', selectedQuizQuestionBank)"
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
								data-quick-focus="quiz-bank-title"
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
								class="if-action"
								@click="emit('add-question')"
							>
								Add Question
							</button>
						</div>

						<div
							v-if="!quizBankForm.questions.length"
							class="rounded-2xl border border-dashed border-line-soft p-4"
						>
							<p class="type-caption text-ink/70">
								No questions yet. Add reusable questions teachers can pull into quiz-backed tasks.
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
											@change="emit('question-type-change', question)"
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
										<PlanningRichTextField
											v-model="question.prompt"
											:editable="canManagePlan"
											min-height-class="min-h-[8rem]"
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
											class="if-action"
											@click="emit('add-option', question)"
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
												class="if-action"
												@click="emit('remove-option', question, option.local_id)"
											>
												Remove
											</button>
										</div>
									</div>
								</section>

								<label class="mt-4 block space-y-2">
									<span class="type-caption text-ink/70">Explanation</span>
									<PlanningRichTextField
										v-model="question.explanation"
										placeholder="Optional feedback or explanation shown when allowed."
										:editable="canManagePlan"
										min-height-class="min-h-[6rem]"
									/>
								</label>

								<div v-if="canManagePlan" class="mt-4 flex justify-end">
									<button
										type="button"
										class="if-action"
										@click="emit('remove-question', question.local_id)"
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
							class="if-action"
							@click="emit('cancel-new-bank')"
						>
							Cancel New Quiz Bank
						</button>
						<button
							type="button"
							class="if-action"
							:disabled="quizBankPending"
							@click="emit('save-bank')"
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
		</div>
	</section>
</template>

<script setup lang="ts">
import PlanningRichTextField from '@/components/planning/PlanningRichTextField.vue';
import {
	SECTION_IDS,
	isChoiceQuestion,
	quizQuestionTypeOptions,
	type EditableQuizQuestion,
	type QuizBankFormState,
} from '@/lib/planning/coursePlanWorkspace';
import type { StaffCoursePlanQuizQuestionBank } from '@/types/contracts/staff_teaching/get_staff_course_plan_surface';

defineProps<{
	collapsed: boolean;
	canManagePlan: boolean;
	creatingQuizQuestionBank: boolean;
	showQuizBankEditor: boolean;
	quizQuestionBanks: StaffCoursePlanQuizQuestionBank[];
	selectedQuizQuestionBank: StaffCoursePlanQuizQuestionBank | null;
	selectedQuizBankLabel: string;
	quizBankForm: QuizBankFormState;
	quizBankPending: boolean;
}>();

const emit = defineEmits<{
	(e: 'toggle'): void;
	(e: 'select-bank', quizQuestionBank: string): void;
	(e: 'start-new-bank'): void;
	(e: 'assign-quiz', bank: StaffCoursePlanQuizQuestionBank): void;
	(e: 'add-question'): void;
	(e: 'remove-question', localId: number): void;
	(e: 'add-option', question: EditableQuizQuestion): void;
	(e: 'remove-option', question: EditableQuizQuestion, localId: number): void;
	(e: 'question-type-change', question: EditableQuizQuestion): void;
	(e: 'cancel-new-bank'): void;
	(e: 'save-bank'): void;
}>();
</script>
