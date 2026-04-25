<!-- ifitwala_ed/ifitwala_ed/ui-spa/src/pages/students/StudentLogs.vue -->

<template>
	<div class="portal-page">
		<header class="page-header">
			<div class="page-header__intro">
				<h1 class="type-h1 text-ink">Student Logs</h1>
				<p class="type-meta text-ink/70">Notes shared with you by staff.</p>
			</div>
		</header>

		<!-- Initial loading -->
		<div v-if="initialLoading" class="card-panel py-10 text-center type-meta text-ink/70">
			Loading logs…
		</div>

		<!-- Empty state -->
		<div
			v-else-if="!logs.length"
			class="card-panel rounded-2xl border-dashed py-10 text-center type-meta text-ink/68"
		>
			No logs yet.
		</div>

		<!-- List -->
		<div v-else class="space-y-3">
			<button
				v-for="log in logs"
				:key="log.name"
				type="button"
				class="if-feed-card if-feed-card--interactive group w-full border-l-4 text-left"
				:style="{ borderLeftColor: colorFor(log.log_type) }"
				@click="openLogDetail(log)"
			>
				<div class="flex items-start justify-between">
					<div>
						<p class="type-meta">
							<span class="inline-flex items-center gap-2 type-body-strong text-ink">
								<span
									class="inline-block w-2.5 h-2.5 rounded-full"
									:style="{ backgroundColor: colorFor(log.log_type) }"
								/>
								{{ log.log_type }}
							</span>
							<span class="mx-2 text-ink/30">•</span>
							<span>{{ formatDate(log.date) }}</span>
							<span
								v-if="formatTime(log.time)"
								class="ml-2 align-[0.5px] type-caption text-ink/70 bg-surface-soft border border-line-soft rounded px-1.5 py-0.5 tabular-nums"
							>
								{{ formatTime(log.time) }}
							</span>
						</p>
						<p class="type-meta">By {{ log.author_name }}</p>

						<p v-if="log.preview" class="mt-2 type-body text-ink/80 break-words">
							{{ log.preview }}
						</p>
					</div>

					<div class="ml-3">
						<span v-if="log.is_unread" class="chip chip-focus">New</span>
					</div>
				</div>

				<div v-if="log.follow_up_status" class="mt-2">
					<span class="chip" :class="statusClass(log.follow_up_status)">
						Follow-up: {{ log.follow_up_status }}
					</span>
					<span v-if="log.attachment_count" class="chip ml-2">
						Evidence: {{ log.attachment_count }}
					</span>
				</div>
			</button>
		</div>

		<!-- Load more -->
		<div v-if="hasMore" class="mt-4">
			<button :disabled="moreLoading" @click="loadMoreLogs" class="if-button if-button--primary">
				<span v-if="!moreLoading">Load more</span>
				<span v-else>Loading…</span>
			</button>
		</div>

		<!-- Modal -->
		<TransitionRoot as="template" :show="isModalOpen">
			<Dialog
				as="div"
				class="if-overlay"
				:initialFocus="initialFocus"
				@close="isModalOpen = false"
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
					<div class="if-overlay__backdrop" />
				</TransitionChild>

				<div class="if-overlay__wrap">
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
								@click="isModalOpen = false"
							>
								Close
							</button>
							<div class="if-overlay__body">
								<div v-if="selectedLog">
									<DialogTitle as="h3" class="type-h3">
										{{ selectedLog.log_type }}
									</DialogTitle>

									<div class="mt-2">
										<div class="type-meta space-x-4">
											<span>{{ formatDate(selectedLog.date) }}</span>
											<span>By: {{ selectedLog.author_name }}</span>
										</div>
										<hr class="my-4 border-[rgb(var(--border-rgb)/0.7)]" />

										<div v-if="modalLoading" class="text-center py-8">
											<p class="type-body text-ink/70">Loading details...</p>
										</div>
										<div
											v-else
											class="prose prose-sm max-w-none text-ink/80"
											v-html="selectedLog.log"
										/>
										<div
											v-if="
												Array.isArray(selectedLog.attachments) && selectedLog.attachments.length
											"
											class="mt-5 space-y-3"
										>
											<p class="type-body-strong text-ink">Evidence</p>
											<template
												v-for="attachment in selectedLog.attachments"
												:key="attachment.row_name"
											>
												<AttachmentPreviewCard
													v-if="attachment.attachment_preview"
													:attachment="attachment.attachment_preview"
													:title="attachment.title"
													:description="attachment.description"
													variant="evidence"
												/>
											</template>
										</div>
									</div>
								</div>
							</div>

							<div class="if-overlay__footer">
								<button
									type="button"
									class="if-button if-button--primary w-full justify-center"
									@click="isModalOpen = false"
								>
									Close
								</button>
							</div>
						</DialogPanel>
					</TransitionChild>
				</div>
			</Dialog>
		</TransitionRoot>
	</div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { toast } from 'frappe-ui';
import {
	Dialog,
	DialogPanel,
	DialogTitle,
	TransitionChild,
	TransitionRoot,
} from '@headlessui/vue';
import { apiMethod } from '@/resources/frappe';
import AttachmentPreviewCard from '@/components/attachments/AttachmentPreviewCard.vue';

const PAGE_LENGTH = 20;

const logs = ref([]);
const selectedLog = ref(null);
const isModalOpen = ref(false);
const hasMore = ref(true);
const start = ref(0);

const initialLoading = ref(true);
const moreLoading = ref(false);
const modalLoading = ref(false);
const initialFocus = ref(null);

// --- Color helpers (elegant, consistent with tokens) ---------------------------------
const PALETTE = [
	'var(--sky)', // sky
	'var(--leaf)', // leaf
	'var(--moss)', // moss
	'var(--jacaranda)', // jacaranda
	'var(--slate)', // slate
	'var(--sand)', // sand
	'var(--flame)', // flame
	'var(--clay)', // clay
	'var(--canopy)', // canopy
];

function hashStr(s) {
	let h = 5381;
	for (let i = 0; i < s.length; i++) h = ((h << 5) + h) ^ s.charCodeAt(i);
	return Math.abs(h);
}
function colorFor(key) {
	const idx = hashStr(String(key || '')) % PALETTE.length;
	return PALETTE[idx];
}
function statusClass(status) {
	const s = String(status || '').toLowerCase();
	if (s.includes('overdue') || s.includes('escalated')) return 'chip-alert';
	if (s.includes('pending') || s.includes('open')) return 'chip-warm';
	return 'chip-success';
}

// --- Formatting ---------------------------------------------------------------
function formatDate(d) {
	try {
		return new Date(d).toDateString();
	} catch {
		return d;
	}
}
function formatTime(t) {
	// Accepts 'HH:MM:SS' or 'HH:MM' (returns 'HH:MM')
	if (!t) return '';
	const [hh = '', mm = ''] = String(t).split(':');
	const H = hh.toString().padStart(2, '0');
	const M = mm.toString().padStart(2, '0');
	return `${H}:${M}`;
}

// --- Data fetching ------------------------------------------------------------
async function fetchLogs() {
	try {
		const rows = await apiMethod('ifitwala_ed.api.student_log.get_student_logs', {
			start: start.value,
			page_length: PAGE_LENGTH,
		});
		if (!Array.isArray(rows)) throw new Error('Unexpected logs response');

		logs.value.push(...rows);
		if (rows.length < PAGE_LENGTH) hasMore.value = false;
		start.value += PAGE_LENGTH;
	} catch (err) {
		console.error('Failed to fetch student logs:', err);
		hasMore.value = false;
	}
}

async function openLogDetail(log) {
	selectedLog.value = log;
	isModalOpen.value = true;
	modalLoading.value = true;
	try {
		const full = await apiMethod('ifitwala_ed.api.student_log.get_student_log_detail', {
			log_name: log.name,
		});
		if (full && typeof full === 'object') {
			selectedLog.value = full;
			try {
				await apiMethod('ifitwala_ed.api.student_log.mark_student_log_read', {
					log_name: log.name,
				});
				const row = logs.value.find(l => l.name === log.name);
				if (row) row.is_unread = false;
			} catch (markErr) {
				const message = markErr instanceof Error ? markErr.message : String(markErr || '');
				toast.error(message || 'Could not update read status.');
			}
		}
	} catch (err) {
		console.error('Failed to fetch log detail:', err);
		toast.error('Could not load this log.');
		isModalOpen.value = false;
	} finally {
		modalLoading.value = false;
	}
}

async function loadMoreLogs() {
	moreLoading.value = true;
	await fetchLogs();
	moreLoading.value = false;
}

onMounted(async () => {
	await fetchLogs();
	initialLoading.value = false;
});
</script>
