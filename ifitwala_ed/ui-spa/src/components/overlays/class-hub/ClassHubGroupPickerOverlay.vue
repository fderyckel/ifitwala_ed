<!-- ifitwala_ed/ui-spa/src/components/overlays/class-hub/ClassHubGroupPickerOverlay.vue -->
<template>
	<TransitionRoot as="template" :show="open" @after-leave="$emit('after-leave')">
		<Dialog
			as="div"
			class="if-overlay if-overlay--class-hub"
			:style="overlayStyle"
			:initialFocus="initialFocus"
			@close="onDialogClose"
		>
			<TransitionChild
				as="template"
				enter="if-overlay__fade-enter"
				enter-from="if-overlay__fade-from"
				enter-to="if-overlay__fade-to"
				leave="if-overlay__fade-leave"
				leave-from="if-overlay__fade-to"
				leave-to="if-overlay__fade-from"
			>
				<div class="if-overlay__backdrop" @click="emitClose('backdrop')" />
			</TransitionChild>

			<div class="if-overlay__wrap" @click.self="emitClose('backdrop')">
				<TransitionChild
					as="template"
					enter="if-overlay__panel-enter"
					enter-from="if-overlay__panel-from"
					enter-to="if-overlay__panel-to"
					leave="if-overlay__panel-leave"
					leave-from="if-overlay__panel-to"
					leave-to="if-overlay__panel-from"
				>
					<DialogPanel class="if-overlay__panel if-overlay__panel--compact">
						<button
							ref="initialFocus"
							type="button"
							class="sr-only"
							aria-hidden="true"
							tabindex="0"
							@click="emitClose('programmatic')"
						>
							Close
						</button>

						<div class="if-overlay__header px-6 pt-6">
							<div class="flex items-start justify-between gap-4">
								<div>
									<p class="type-overline text-slate-token/70">{{ sourceLabel }}</p>
									<DialogTitle as="h2" class="type-h2 text-ink">Open Class Hub</DialogTitle>
									<p class="mt-2 type-body text-slate-token/70">
										Choose the class workspace you want to open.
									</p>
								</div>
								<button
									type="button"
									class="if-overlay__icon-button"
									aria-label="Close class hub chooser"
									@click="emitClose('programmatic')"
								>
									<span aria-hidden="true">x</span>
								</button>
							</div>
						</div>

						<div class="if-overlay__body space-y-4">
							<section
								v-if="!groupOptions.length"
								class="rounded-2xl border border-dashed border-slate-200 bg-slate-50/70 px-4 py-5"
							>
								<p class="type-body-strong text-ink">
									{{ emptyMessage }}
								</p>
								<p class="mt-2 type-caption text-slate-token/70">
									Ask an academic admin to add you as an instructor on a student group, then try
									again here.
								</p>
							</section>

							<template v-else>
								<label v-if="groupOptions.length > 6" class="block space-y-2">
									<span class="type-label text-slate-token/70">Search your classes</span>
									<input
										v-model.trim="searchQuery"
										type="text"
										class="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-ink outline-none transition focus:border-jacaranda"
										placeholder="Find a course or student group"
									/>
								</label>

								<div
									v-if="filteredGroups.length"
									class="max-h-[24rem] space-y-2 overflow-y-auto pr-1"
								>
									<button
										v-for="group in filteredGroups"
										:key="group.student_group"
										type="button"
										class="flex w-full items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-white px-4 py-4 text-left transition hover:-translate-y-0.5 hover:border-jacaranda/60 hover:shadow-soft"
										@click="openGroup(group)"
									>
										<div class="min-w-0">
											<p class="type-body-strong text-ink">
												{{ group.title }}
											</p>
											<p class="mt-1 truncate type-caption text-slate-token/70">
												{{ formatSubtitle(group) }}
											</p>
										</div>
										<FeatherIcon name="arrow-right" class="h-4 w-4 shrink-0 text-slate-token/40" />
									</button>
								</div>

								<p
									v-else
									class="rounded-2xl border border-dashed border-slate-200 bg-slate-50/70 px-4 py-5 type-body text-slate-token/70"
								>
									No classes match that search yet.
								</p>
							</template>
						</div>

						<div class="if-overlay__footer">
							<button
								type="button"
								class="rounded-full border border-slate-200 bg-white px-4 py-2 type-button-label text-ink"
								@click="emitClose('programmatic')"
							>
								Close
							</button>
						</div>
					</DialogPanel>
				</TransitionChild>
			</div>
		</Dialog>
	</TransitionRoot>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { FeatherIcon } from 'frappe-ui';
import {
	Dialog,
	DialogPanel,
	DialogTitle,
	TransitionChild,
	TransitionRoot,
} from '@headlessui/vue';

import type { ClassHubHomeEntryGroup } from '@/types/classHub';

type CloseReason = 'backdrop' | 'esc' | 'programmatic';

const props = defineProps<{
	open: boolean;
	zIndex?: number;
	overlayId?: string | null;
	source_label?: string | null;
	message?: string | null;
	groups?: ClassHubHomeEntryGroup[];
}>();

const emit = defineEmits<{
	(e: 'close', reason: CloseReason): void;
	(e: 'after-leave'): void;
}>();

const router = useRouter();
const initialFocus = ref<HTMLElement | null>(null);
const searchQuery = ref('');

const overlayStyle = computed(() => ({ zIndex: props.zIndex ?? 60 }));
const sourceLabel = computed(() => props.source_label || 'Staff Home');
const groupOptions = computed(() => props.groups || []);
const emptyMessage = computed(
	() => props.message || 'You are not assigned to any student groups yet.'
);
const filteredGroups = computed(() => {
	const query = searchQuery.value.trim().toLowerCase();
	if (!query) return groupOptions.value;

	return groupOptions.value.filter(group =>
		[group.title, group.student_group_name, group.course, group.academic_year, group.student_group]
			.filter(Boolean)
			.some(value => String(value).toLowerCase().includes(query))
	);
});

function emitClose(reason: CloseReason) {
	emit('close', reason);
}

function onDialogClose(_payload: unknown) {
	// OverlayHost owns close enforcement.
}

function formatSubtitle(group: ClassHubHomeEntryGroup) {
	return [group.student_group_name, group.academic_year].filter(Boolean).join(' | ');
}

function openGroup(group: ClassHubHomeEntryGroup) {
	emitClose('programmatic');
	void router.push({
		name: 'ClassHub',
		params: { studentGroup: group.student_group },
	});
}

function onKeydown(event: KeyboardEvent) {
	if (!props.open) return;
	if (event.key === 'Escape') emitClose('esc');
}

watch(
	() => props.open,
	value => {
		if (value) document.addEventListener('keydown', onKeydown, true);
		else document.removeEventListener('keydown', onKeydown, true);
	},
	{ immediate: true }
);

onBeforeUnmount(() => {
	document.removeEventListener('keydown', onKeydown, true);
});
</script>
