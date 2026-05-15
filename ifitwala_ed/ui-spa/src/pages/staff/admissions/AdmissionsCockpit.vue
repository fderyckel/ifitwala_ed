<!-- ifitwala_ed/ui-spa/src/pages/staff/admissions/AdmissionsCockpit.vue -->
<template>
	<div class="analytics-shell">
		<header class="page-header">
			<div class="page-header__intro">
				<h1 class="type-h1 text-canopy">Admissions Cockpit</h1>
				<p class="type-meta text-slate-token/80">
					Application progression and blockers (applicant-centered)
				</p>
			</div>
			<div class="page-header__actions">
				<a
					v-if="data?.config?.can_create_inquiry"
					href="/desk/inquiry/new-inquiry-1"
					target="_blank"
					rel="noopener noreferrer"
					class="if-button if-button--primary"
				>
					New Inquiry
				</a>
				<button type="button" class="if-button if-button--quiet" @click="refreshNow">
					Refresh
				</button>
			</div>
		</header>

		<FiltersBar class="analytics-filters">
			<div class="flex flex-col gap-1">
				<label class="type-label">Organization</label>
				<select
					v-model="filters.organization"
					class="h-9 min-w-[180px] rounded-md border px-2 text-sm"
				>
					<option value="">All Organizations</option>
					<option v-for="org in organizations" :key="org" :value="org">{{ org }}</option>
				</select>
			</div>

			<div class="flex flex-col gap-1">
				<label class="type-label">School</label>
				<select v-model="filters.school" class="h-9 min-w-[180px] rounded-md border px-2 text-sm">
					<option value="">All Schools</option>
					<option v-for="school in schools" :key="school" :value="school">{{ school }}</option>
				</select>
			</div>

			<div class="flex min-w-[180px] items-end pb-1">
				<label class="inline-flex items-center gap-2 type-label">
					<input v-model="filters.assigned_to_me" type="checkbox" class="h-4 w-4 rounded border" />
					<span>My Assignments Only</span>
				</label>
			</div>
		</FiltersBar>

		<div
			v-if="error"
			class="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
		>
			{{ error }}
		</div>

		<div v-if="loading" class="py-10 text-center text-slate-500">Loading cockpit...</div>

		<template v-else>
			<KpiRow :items="kpiItems" />

			<section class="rounded-xl border border-slate-200 bg-white p-4">
				<h2 class="type-overline mb-3 text-slate-token/70">Top Admission Blockers</h2>
				<div class="flex flex-wrap gap-2">
					<button
						class="rounded-full border px-3 py-1 text-xs font-semibold transition"
						:class="
							activeBlocker
								? 'border-slate-300 text-slate-token hover:border-slate-500'
								: 'border-canopy bg-canopy/10 text-canopy'
						"
						@click="activeBlocker = ''"
					>
						All
					</button>
					<button
						v-for="blocker in blockers"
						:key="blocker.kind"
						class="rounded-full border px-3 py-1 text-xs font-semibold transition"
						:class="
							activeBlocker === blocker.kind
								? 'border-canopy bg-canopy/10 text-canopy'
								: 'border-slate-300 text-slate-token hover:border-slate-500'
						"
						@click="activeBlocker = blocker.kind"
					>
						{{ blocker.label }} · {{ blocker.count }}
					</button>
				</div>
			</section>

			<section class="overflow-x-auto">
				<div class="flex min-w-max gap-4 pb-2">
					<section
						v-for="column in boardColumns"
						:key="column.id"
						class="flex min-h-[360px] w-[360px] min-w-[360px] flex-col rounded-xl border border-slate-200 bg-slate-50"
					>
						<header class="flex items-center justify-between border-b border-slate-200 px-3 py-2">
							<h3 class="type-label text-canopy">{{ column.title }}</h3>
							<span
								class="rounded-full bg-white px-2 py-0.5 text-xs font-semibold text-slate-token"
							>
								{{ filteredItems(column.items).length }}
							</span>
						</header>

						<div class="flex flex-1 flex-col gap-3 p-3">
							<article
								v-for="item in filteredItems(column.items)"
								:key="item.name"
								class="rounded-lg border border-slate-200 bg-white p-3 shadow-sm"
							>
								<div class="mb-2 flex items-start justify-between gap-2">
									<div>
										<button
											type="button"
											class="type-body-strong text-ink text-left hover:underline"
											@click="openApplicantWorkspace(item)"
										>
											{{ item.display_name }}
										</button>
										<p class="type-caption text-slate-token/70">{{ item.name }}</p>
									</div>
									<div class="flex items-center gap-1.5">
										<button
											type="button"
											class="rounded-md border border-slate-200 px-2 py-1 text-xs font-semibold text-canopy hover:border-canopy"
											@click="openScheduleInterview(item)"
										>
											Schedule Interview
										</button>
										<button
											type="button"
											class="rounded-md border border-slate-200 px-2 py-1 text-xs font-semibold text-canopy hover:border-canopy"
											@click="openThread(item)"
										>
											Message
										</button>
										<a
											:href="item.open_url"
											target="_blank"
											rel="noopener noreferrer"
											class="rounded-md border border-slate-200 px-2 py-1 text-xs font-semibold text-canopy hover:border-canopy"
										>
											Open
										</a>
									</div>
								</div>

								<p class="mb-2 type-caption text-slate-token/80">
									{{ item.school }}
									<span v-if="item.program_offering">· {{ item.program_offering }}</span>
								</p>

								<div class="mb-2 flex flex-wrap gap-1">
									<span v-if="column.id === 'review'" :class="reviewStageClass(item)">
										{{ item.ready ? 'Ready for Decision' : 'Needs Review' }}
									</span>
									<span
										class="rounded-full border border-slate-200 bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-token"
									>
										{{ item.application_status }}
									</span>
									<span v-if="item.aep?.has_plan" :class="aepPillClass(item.aep?.status)">
										AEP · {{ item.aep?.status || 'Plan' }}
									</span>
									<span
										v-if="item.aep?.deposit?.deposit_required"
										:class="depositPillClass(item.aep.deposit)"
									>
										{{
											item.aep.deposit.is_paid
												? 'Deposit paid'
												: item.aep.deposit.blocker_label || 'Deposit required'
										}}
									</span>
									<span :class="pillClass(item.readiness.profile_ok)">Profile</span>
									<span :class="pillClass(item.readiness.documents_ok)">Docs</span>
									<span :class="pillClass(item.readiness.recommendations_ok)"
										>Recommendations</span
									>
									<span :class="pillClass(item.readiness.policies_ok)">Policies</span>
									<span :class="pillClass(item.readiness.health_ok)">Health</span>
									<span
										v-if="(item.interviews?.count || 0) > 0"
										class="rounded-full border border-slate-200 bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-token"
									>
										Interviews · {{ item.interviews?.count || 0 }}
									</span>
									<span
										v-if="(item.comms?.unread_count || 0) > 0"
										class="rounded-full border border-blue-300 bg-blue-50 px-2 py-0.5 text-xs font-semibold text-blue-700"
									>
										Comms · {{ item.comms?.unread_count || 0 }}
									</span>
								</div>

								<div
									v-if="item.aep?.has_plan"
									class="mb-2 rounded-md border border-slate-200 bg-slate-50 px-3 py-2"
								>
									<div class="flex items-start justify-between gap-3">
										<div class="min-w-0">
											<p class="text-xs font-semibold text-slate-900">Enrollment Plan</p>
											<p class="text-xs text-slate-token/80">
												{{ item.aep?.name }}
												<span v-if="item.aep?.status">· {{ item.aep?.status }}</span>
											</p>
											<p
												v-if="item.aep?.status === 'Offer Sent' && item.aep?.offer_expires_on"
												class="text-xs text-slate-token/80"
											>
												Offer expires {{ formatDateOnly(item.aep.offer_expires_on) }}
											</p>
										</div>
										<div class="flex flex-wrap justify-end gap-2">
											<button
												v-if="item.aep?.can_send_offer"
												type="button"
												class="rounded-md border border-slate-200 bg-white px-2 py-1 text-xs font-semibold text-canopy hover:border-canopy disabled:cursor-not-allowed disabled:opacity-60"
												:disabled="isAepActionPending(item.aep?.name, 'send_offer')"
												@click="sendEnrollmentOffer(item)"
											>
												{{
													isAepActionPending(item.aep?.name, 'send_offer')
														? 'Sending...'
														: 'Send Offer'
												}}
											</button>
											<button
												v-if="item.aep?.can_hydrate_request"
												type="button"
												class="rounded-md border border-slate-200 bg-white px-2 py-1 text-xs font-semibold text-canopy hover:border-canopy disabled:cursor-not-allowed disabled:opacity-60"
												:disabled="isAepActionPending(item.aep?.name, 'hydrate_request')"
												@click="hydrateEnrollmentRequest(item)"
											>
												{{
													isAepActionPending(item.aep?.name, 'hydrate_request')
														? 'Hydrating...'
														: 'Hydrate Request'
												}}
											</button>
											<a
												v-if="item.aep?.program_enrollment_request_url"
												:href="item.aep.program_enrollment_request_url"
												target="_blank"
												rel="noopener noreferrer"
												class="rounded-md border border-slate-200 bg-white px-2 py-1 text-xs font-semibold text-canopy hover:border-canopy"
											>
												Open Request
											</a>
											<a
												v-if="item.aep?.open_url"
												:href="item.aep.open_url"
												target="_blank"
												rel="noopener noreferrer"
												class="rounded-md border border-slate-200 bg-white px-2 py-1 text-xs font-semibold text-canopy hover:border-canopy"
											>
												Open Plan
											</a>
										</div>
									</div>
								</div>

								<div
									v-if="item.aep?.deposit?.deposit_required"
									class="mb-2 rounded-md border border-slate-200 bg-white px-3 py-2"
								>
									<div class="flex items-start justify-between gap-3">
										<div class="min-w-0">
											<p class="text-xs font-semibold text-slate-900">Deposit</p>
											<p class="text-xs text-slate-token/80">
												{{
													formatAmount(item.aep.deposit.amount || item.aep.deposit.deposit_amount)
												}}
												<span
													v-if="item.aep.deposit.due_date || item.aep.deposit.deposit_due_date"
												>
													· Due
													{{
														formatDateOnly(
															item.aep.deposit.due_date || item.aep.deposit.deposit_due_date
														)
													}}
												</span>
											</p>
											<p class="text-xs text-slate-token/80">
												{{
													item.aep.deposit.invoice
														? `${item.aep.deposit.invoice} · ${item.aep.deposit.invoice_status || 'Draft'}`
														: item.aep.deposit.blocker_label || 'Invoice not generated'
												}}
											</p>
											<p
												v-if="item.aep.deposit.requires_override_approval"
												class="text-xs font-semibold text-amber-800"
											>
												Override approval required
											</p>
										</div>
										<div class="flex flex-wrap justify-end gap-2">
											<button
												v-if="item.aep.deposit.can_generate_invoice"
												type="button"
												class="rounded-md border border-slate-200 bg-white px-2 py-1 text-xs font-semibold text-canopy hover:border-canopy disabled:cursor-not-allowed disabled:opacity-60"
												:disabled="isAepActionPending(item.aep?.name, 'generate_deposit')"
												@click="generateDepositInvoice(item)"
											>
												{{
													isAepActionPending(item.aep?.name, 'generate_deposit')
														? 'Generating...'
														: 'Generate Invoice'
												}}
											</button>
											<a
												v-if="item.aep.deposit.invoice"
												:href="`/desk/sales-invoice/${item.aep.deposit.invoice}`"
												target="_blank"
												rel="noopener noreferrer"
												class="rounded-md border border-slate-200 bg-white px-2 py-1 text-xs font-semibold text-canopy hover:border-canopy"
											>
												Open Invoice
											</a>
										</div>
									</div>
								</div>

								<div
									v-if="(item.recommendations?.pending_review_count || 0) > 0"
									class="mb-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2"
								>
									<div class="flex items-center justify-between gap-3">
										<div>
											<p class="text-xs font-semibold text-amber-900">Recommendation review</p>
											<p class="text-xs text-amber-900/80">
												{{ item.recommendations.pending_review_count }} awaiting review
												<span v-if="item.recommendations.latest_submitted_on">
													· latest {{ formatDate(item.recommendations.latest_submitted_on) }}
												</span>
											</p>
										</div>
										<button
											type="button"
											class="rounded-md border border-amber-300 bg-white px-2 py-1 text-xs font-semibold text-canopy hover:border-canopy"
											@click="openRecommendationReview(item)"
										>
											{{
												item.recommendations.pending_review_count === 1
													? 'Review Recommendation'
													: 'Review Recommendations'
											}}
										</button>
									</div>
								</div>

								<div
									v-if="item.interviews?.latest"
									class="mb-2 rounded-md border border-slate-200 bg-slate-50 px-3 py-2"
								>
									<div class="flex items-start justify-between gap-3">
										<div class="min-w-0">
											<p class="text-xs font-semibold text-slate-900">Latest Interview</p>
											<p class="text-xs text-slate-token/80">
												{{ item.interviews.latest.interview_type || 'Interview' }}
												<span v-if="item.interviews.latest.mode">
													· {{ item.interviews.latest.mode }}
												</span>
											</p>
											<p class="text-xs text-slate-token/80">
												{{ formatInterviewSchedule(item.interviews.latest) }}
											</p>
											<p
												v-if="item.interviews.latest.interviewer_labels?.length"
												class="text-xs text-slate-token/80"
											>
												{{ item.interviews.latest.interviewer_labels.join(', ') }}
											</p>
											<p
												class="text-xs font-semibold"
												:class="
													item.interviews.latest.feedback_complete
														? 'text-emerald-700'
														: 'text-amber-800'
												"
											>
												Feedback · {{ item.interviews.latest.feedback_status_label }}
											</p>
										</div>
										<button
											type="button"
											class="rounded-md border border-slate-200 bg-white px-2 py-1 text-xs font-semibold text-canopy hover:border-canopy"
											@click="openInterviewWorkspace(item.interviews.latest.name)"
										>
											Open Interview
										</button>
									</div>
								</div>

								<div
									v-if="item.comms?.last_message_preview"
									class="mb-2 rounded-md border border-slate-200 bg-slate-50 px-2 py-1"
								>
									<p class="line-clamp-2 text-xs text-slate-token/80">
										{{ item.comms?.last_message_preview }}
									</p>
								</div>

								<div v-if="item.top_blockers.length" class="space-y-1">
									<p class="type-caption text-slate-token/80">Missing / Blocked</p>
									<template
										v-for="issue in item.top_blockers"
										:key="`${item.name}-${issue.kind}-${issue.label}`"
									>
										<button
											v-if="shouldOpenBlockerInWorkspace(issue)"
											type="button"
											class="block text-left text-xs text-red-700 hover:underline"
											@click="openBlockerTarget(item, issue)"
										>
											{{ issue.label }}
										</button>
										<a
											v-else
											:href="issue.target_url || item.open_url"
											target="_blank"
											rel="noopener noreferrer"
											class="block text-xs text-red-700 hover:underline"
										>
											{{ issue.label }}
										</a>
									</template>
								</div>
							</article>

							<div
								v-if="!filteredItems(column.items).length"
								class="flex flex-1 items-center justify-center rounded-lg border border-dashed border-slate-300 bg-white/70 p-4 text-xs text-slate-500"
							>
								No applicants in this stage.
							</div>
						</div>
					</section>
				</div>
			</section>
		</template>

		<div
			v-if="activeThreadCard"
			class="fixed inset-0 z-50 flex items-stretch justify-end bg-slate-900/35"
			@click.self="closeThread"
		>
			<section class="flex h-full w-full max-w-xl flex-col bg-white shadow-2xl">
				<header class="border-b border-slate-200 px-5 py-4">
					<div class="flex items-start justify-between gap-3">
						<div>
							<p class="type-label text-canopy">Case Communication</p>
							<p class="type-body-strong text-ink">{{ activeThreadCard.display_name }}</p>
							<p class="type-caption text-slate-token/70">{{ activeThreadCard.name }}</p>
						</div>
						<button
							type="button"
							class="rounded-full border border-slate-200 px-2 py-1 text-xs font-semibold text-slate-token hover:border-slate-400"
							@click="closeThread"
						>
							Close
						</button>
					</div>
				</header>

				<div class="min-h-0 flex-1 overflow-y-auto px-5 py-4">
					<p v-if="threadLoading" class="text-sm text-slate-500">Loading messages...</p>
					<div
						v-else-if="threadError"
						class="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800"
					>
						{{ threadError }}
					</div>
					<div
						v-else-if="!threadMessages.length"
						class="rounded-md border border-dashed border-slate-300 bg-slate-50 px-3 py-3 text-sm text-slate-600"
					>
						No messages yet.
					</div>
					<div v-else class="space-y-2">
						<article
							v-for="message in threadMessages"
							:key="`${message.name}-${message.created_at}`"
							class="rounded-lg border px-3 py-2"
							:class="messageClass(message.direction)"
						>
							<div class="flex items-center justify-between gap-3">
								<p class="text-xs font-semibold text-slate-700">
									{{ message.full_name || message.user }}
								</p>
								<p class="text-xs text-slate-500">{{ formatDate(message.created_at) }}</p>
							</div>
							<p class="mt-1 whitespace-pre-wrap text-sm text-slate-800">{{ message.body }}</p>
						</article>
					</div>
				</div>

				<footer class="border-t border-slate-200 px-5 py-4">
					<p class="mb-1 text-xs font-semibold text-slate-700">Reply</p>
					<textarea
						v-model="threadDraft"
						rows="4"
						maxlength="300"
						class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-800 focus:border-canopy focus:outline-none focus:ring-2 focus:ring-canopy/20"
						placeholder="Write a message to applicant..."
						@keydown.ctrl.enter.prevent="sendThreadMessage"
						@keydown.meta.enter.prevent="sendThreadMessage"
					/>
					<div class="mt-2 flex flex-wrap items-center justify-between gap-3">
						<label class="inline-flex items-center gap-2 text-xs text-slate-700">
							<input
								v-model="threadInternalNote"
								type="checkbox"
								class="h-4 w-4 rounded border-slate-300"
							/>
							<span>Internal note (not visible to applicant)</span>
						</label>
						<div class="ml-auto flex items-center gap-3">
							<p class="text-xs text-slate-500">{{ threadDraft.length }}/300</p>
							<button
								type="button"
								class="analytics-export-button"
								:disabled="threadSending"
								@click="sendThreadMessage"
							>
								{{ threadSending ? 'Sending...' : 'Send' }}
							</button>
						</div>
					</div>
					<p class="mt-1 text-[11px] text-slate-500">Shortcut: Ctrl/Cmd + Enter</p>
					<p v-if="threadSendError" class="mt-2 text-xs text-rose-700">{{ threadSendError }}</p>
				</footer>
			</section>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';

import { useOverlayStack } from '@/composables/useOverlayStack';
import FiltersBar from '@/components/filters/FiltersBar.vue';
import KpiRow from '@/components/analytics/KpiRow.vue';
import { SIGNAL_ADMISSIONS_COCKPIT_INVALIDATE, uiSignals } from '@/lib/uiSignals';
import {
	getAdmissionsCaseThread,
	getAdmissionsCockpitData,
	generateAdmissionsCockpitDepositInvoice,
	hydrateAdmissionsCockpitRequest,
	markAdmissionsCaseRead,
	sendAdmissionsCockpitOffer,
	sendAdmissionsCaseMessage,
	type AdmissionsCaseMessage,
} from '@/lib/admission';

type CockpitCounts = {
	active_applications: number;
	blocked_applications: number;
	ready_for_decision: number;
	accepted_pending_promotion: number;
	my_open_assignments: number;
	unread_applicant_replies: number;
};

type CockpitBlocker = {
	kind: string;
	label: string;
	count: number;
};

type CockpitInterviewLatest = {
	name: string;
	open_url: string;
	interview_type?: string | null;
	interview_date?: string | null;
	interview_start?: string | null;
	interview_end?: string | null;
	mode?: string | null;
	interviewer_labels: string[];
	feedback_submitted_count: number;
	feedback_expected_count: number;
	feedback_complete: boolean;
	feedback_status_label: string;
};

type CockpitInterviewSummary = {
	count: number;
	latest?: CockpitInterviewLatest | null;
};

type CockpitCardTarget = {
	kind: string;
	label?: string;
	target_doctype?: string;
	target_name?: string;
	target_url?: string;
	target_label?: string;
	workspace_mode?: string;
	workspace_student_applicant?: string;
	workspace_document_type?: string | null;
	workspace_applicant_document?: string | null;
	workspace_document_item?: string | null;
};

type CockpitAepSummary = {
	has_plan: boolean;
	name?: string | null;
	status?: string | null;
	open_url?: string | null;
	offer_expires_on?: string | null;
	program_enrollment_request?: string | null;
	program_enrollment_request_url?: string | null;
	can_send_offer: boolean;
	can_hydrate_request: boolean;
	deposit?: CockpitDepositSummary;
};

type CockpitDepositSummary = {
	deposit_required: boolean;
	deposit_amount: number;
	deposit_due_date?: string | null;
	terms_source: string;
	override_status: string;
	requires_override_approval: boolean;
	academic_approved: boolean;
	finance_approved: boolean;
	invoice?: string | null;
	invoice_status?: string | null;
	docstatus?: number | null;
	amount: number;
	paid_amount: number;
	outstanding_amount: number;
	due_date?: string | null;
	is_overdue: boolean;
	is_paid: boolean;
	blocker_label?: string | null;
	can_generate_invoice: boolean;
};

type CockpitCard = {
	name: string;
	display_name: string;
	application_status: string;
	ready: boolean;
	school: string;
	program_offering?: string;
	aep?: CockpitAepSummary;
	interviews?: CockpitInterviewSummary;
	top_blockers: CockpitCardTarget[];
	readiness: {
		profile_ok: boolean;
		documents_ok: boolean;
		policies_ok: boolean;
		health_ok: boolean;
		recommendations_ok: boolean;
	};
	recommendations?: {
		required_total: number;
		received_total: number;
		requested_total: number;
		pending_review_count: number;
		latest_submitted_on?: string | null;
		first_pending_review?: {
			recommendation_request?: string | null;
			recommendation_submission?: string | null;
			applicant_document_item?: string | null;
			recommender_name?: string | null;
			template_name?: string | null;
			submitted_on?: string | null;
		} | null;
	};
	open_url: string;
	blockers: CockpitCardTarget[];
	comms?: {
		thread_name?: string | null;
		unread_count: number;
		last_message_at?: string | null;
		last_message_preview: string;
		last_message_from?: 'applicant' | 'staff' | null;
		needs_reply: boolean;
	};
};

type CockpitColumn = {
	id: string;
	title: string;
	items: CockpitCard[];
};

type CockpitPayload = {
	config?: {
		organizations?: string[];
		schools?: string[];
		can_create_inquiry?: boolean;
	};
	counts?: CockpitCounts;
	blockers?: CockpitBlocker[];
	columns?: CockpitColumn[];
};

const loading = ref(false);
const error = ref('');
const data = ref<CockpitPayload | null>(null);
const overlay = useOverlayStack();
const activeBlocker = ref('');
const activeThreadCard = ref<CockpitCard | null>(null);
const threadLoading = ref(false);
const threadError = ref('');
const threadMessages = ref<AdmissionsCaseMessage[]>([]);
const threadDraft = ref('');
const threadInternalNote = ref(false);
const threadSending = ref(false);
const threadSendError = ref('');
const pendingAepActionKey = ref('');

const filters = ref({
	organization: '',
	school: '',
	assigned_to_me: true,
});

let refreshTimer: ReturnType<typeof setTimeout> | null = null;
let requestToken = 0;
let unsubscribeCockpitInvalidate: (() => void) | null = null;

const organizations = computed(() => data.value?.config?.organizations || []);
const schools = computed(() => data.value?.config?.schools || []);
const blockers = computed(() => data.value?.blockers || []);
const columns = computed(() => data.value?.columns || []);
const boardColumns = computed<CockpitColumn[]>(() => {
	const incoming = columns.value || [];
	if (!incoming.length) {
		return [];
	}

	const byId = new Map<string, CockpitCard[]>(
		incoming.map(column => [column.id, (column.items || []) as CockpitCard[]])
	);

	return [
		{
			id: 'preparation',
			title: 'Preparation',
			items: [...(byId.get('in_progress') || []), ...(byId.get('draft') || [])],
		},
		{
			id: 'submitted',
			title: 'Submitted',
			items: [...(byId.get('submitted') || [])],
		},
		{
			id: 'review',
			title: 'Review',
			items: [...(byId.get('awaiting_decision') || []), ...(byId.get('under_review') || [])],
		},
		{
			id: 'accepted',
			title: 'Accepted',
			items: [...(byId.get('accepted_pending_promotion') || [])],
		},
	];
});

const kpiItems = computed(() => {
	const counts = data.value?.counts || {
		active_applications: 0,
		blocked_applications: 0,
		ready_for_decision: 0,
		accepted_pending_promotion: 0,
		my_open_assignments: 0,
		unread_applicant_replies: 0,
	};
	return [
		{ id: 'active', label: 'Active Applications', value: counts.active_applications },
		{ id: 'blocked', label: 'Blocked', value: counts.blocked_applications, hint: 'Action Needed' },
		{ id: 'decision', label: 'Ready for Decision', value: counts.ready_for_decision },
		{
			id: 'promotion',
			label: 'Accepted Pending Promotion',
			value: counts.accepted_pending_promotion,
		},
		{ id: 'assignments', label: 'My Open Assignments', value: counts.my_open_assignments },
		{
			id: 'unread-replies',
			label: 'Unread Applicant Replies',
			value: counts.unread_applicant_replies,
			hint: 'Comms Queue',
		},
	];
});

function pillClass(ok: boolean) {
	return ok
		? 'rounded-full border border-emerald-300 bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-700'
		: 'rounded-full border border-[rgb(var(--flame-rgb)/0.35)] bg-[rgb(var(--flame-rgb)/0.10)] px-2 py-0.5 text-xs font-semibold text-flame';
}

function reviewStageClass(item: CockpitCard) {
	return item.ready
		? 'rounded-full border border-emerald-300 bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-700'
		: 'rounded-full border border-amber-300 bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-800';
}

function aepPillClass(status?: string | null) {
	const resolvedStatus = String(status || '').trim();
	if (resolvedStatus === 'Hydrated') {
		return 'rounded-full border border-emerald-300 bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-700';
	}
	if (resolvedStatus === 'Offer Sent' || resolvedStatus === 'Offer Accepted') {
		return 'rounded-full border border-blue-300 bg-blue-50 px-2 py-0.5 text-xs font-semibold text-blue-700';
	}
	if (resolvedStatus === 'Committee Approved' || resolvedStatus === 'Ready for Committee') {
		return 'rounded-full border border-amber-300 bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-800';
	}
	return 'rounded-full border border-slate-200 bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-token';
}

function depositPillClass(deposit?: CockpitDepositSummary | null) {
	if (deposit?.is_paid) {
		return 'rounded-full border border-emerald-300 bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-700';
	}
	if (deposit?.is_overdue || deposit?.requires_override_approval) {
		return 'rounded-full border border-red-300 bg-red-50 px-2 py-0.5 text-xs font-semibold text-red-700';
	}
	return 'rounded-full border border-amber-300 bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-800';
}

function filteredItems(items: CockpitCard[]) {
	if (!activeBlocker.value) {
		return items;
	}
	return (items || []).filter(item =>
		(item.blockers || []).some(row => row.kind === activeBlocker.value)
	);
}

function queueRefresh() {
	if (refreshTimer) {
		clearTimeout(refreshTimer);
	}
	refreshTimer = setTimeout(() => {
		void refreshNow();
	}, 300);
}

function messageClass(direction: AdmissionsCaseMessage['direction']) {
	if (direction === 'ApplicantToStaff') {
		return 'border-blue-300 bg-blue-50';
	}
	if (direction === 'Internal') {
		return 'border-amber-300 bg-amber-50';
	}
	return 'border-emerald-300 bg-emerald-50';
}

function formatDate(value?: string | null) {
	if (!value) {
		return '—';
	}
	const date = new Date(value);
	if (Number.isNaN(date.getTime())) {
		return value;
	}
	return date.toLocaleString();
}

function formatDateOnly(value?: string | null) {
	if (!value) {
		return '—';
	}
	const date = new Date(value);
	if (Number.isNaN(date.getTime())) {
		return value;
	}
	return date.toLocaleDateString();
}

type AepAction = 'send_offer' | 'hydrate_request' | 'generate_deposit';

function aepActionKey(planName?: string | null, action: AepAction = 'send_offer') {
	return `${String(planName || '').trim()}:${action}`;
}

function isAepActionPending(planName?: string | null, action: AepAction = 'send_offer') {
	return pendingAepActionKey.value === aepActionKey(planName, action);
}

function formatAmount(value?: number | string | null) {
	const amount = Number(value || 0);
	if (Number.isNaN(amount)) {
		return '0.00';
	}
	return amount.toLocaleString(undefined, {
		minimumFractionDigits: 2,
		maximumFractionDigits: 2,
	});
}

function formatInterviewSchedule(interview?: CockpitInterviewLatest | null) {
	if (!interview) {
		return '—';
	}
	if (interview.interview_start && interview.interview_end) {
		return `${formatDate(interview.interview_start)} → ${formatDate(interview.interview_end)}`;
	}
	if (interview.interview_start) {
		return formatDate(interview.interview_start);
	}
	if (interview.interview_date) {
		return interview.interview_date;
	}
	return '—';
}

function openApplicantWorkspace(
	card: CockpitCard,
	anchor: {
		documentType?: string | null;
		applicantDocument?: string | null;
		documentItem?: string | null;
	} = {}
) {
	const applicantName = String(card?.name || '').trim();
	if (!applicantName) {
		error.value = 'Applicant reference is missing for workspace open.';
		return;
	}

	overlay.open('admissions-workspace', {
		mode: 'applicant',
		studentApplicant: applicantName,
		documentType: String(anchor.documentType || '').trim() || null,
		applicantDocument: String(anchor.applicantDocument || '').trim() || null,
		documentItem: String(anchor.documentItem || '').trim() || null,
	});
}

function openInterviewWorkspace(interviewName?: string | null) {
	const resolvedInterview = String(interviewName || '').trim();
	if (!resolvedInterview) {
		error.value = 'Interview reference is missing for workspace open.';
		return;
	}

	overlay.open('admissions-workspace', {
		mode: 'interview',
		interview: resolvedInterview,
	});
}

function openRecommendationReview(card: CockpitCard) {
	const applicantName = String(card?.name || '').trim();
	if (!applicantName) {
		error.value = 'Applicant reference is missing for recommendation review.';
		return;
	}

	const pendingReview = card.recommendations?.first_pending_review;
	const pendingCount = Number(card.recommendations?.pending_review_count || 0);
	const shouldPrefill = pendingCount === 1 && pendingReview;

	overlay.open('admissions-workspace', {
		mode: 'applicant',
		studentApplicant: applicantName,
		recommendationRequest: shouldPrefill
			? String(pendingReview?.recommendation_request || '').trim() || null
			: null,
		recommendationSubmission: null,
		applicantDocumentItem: null,
	});
}

function shouldOpenBlockerInWorkspace(issue: CockpitCardTarget) {
	return (
		String(issue?.workspace_mode || '').trim() === 'applicant' &&
		Boolean(String(issue?.workspace_student_applicant || '').trim())
	);
}

function openBlockerTarget(card: CockpitCard, issue: CockpitCardTarget) {
	if (shouldOpenBlockerInWorkspace(issue)) {
		openApplicantWorkspace(card, {
			documentType: issue.workspace_document_type || null,
			applicantDocument: issue.workspace_applicant_document || null,
			documentItem: issue.workspace_document_item || null,
		});
		return;
	}

	const targetUrl = String(issue?.target_url || card?.open_url || '').trim();
	if (!targetUrl) {
		error.value = 'Action target is missing for this blocker.';
		return;
	}
	window.open(targetUrl, '_blank', 'noopener,noreferrer');
}

function openScheduleInterview(card: CockpitCard) {
	const applicantName = String(card?.name || '').trim();
	if (!applicantName) {
		error.value = 'Applicant reference is missing for interview scheduling.';
		return;
	}

	overlay.open('admissions-interview-schedule', {
		studentApplicant: applicantName,
		applicantName: String(card?.display_name || '').trim() || applicantName,
		school: String(card?.school || '').trim() || null,
	});
}

async function sendEnrollmentOffer(card: CockpitCard) {
	const planName = String(card?.aep?.name || '').trim();
	if (!planName) {
		error.value = 'Enrollment plan reference is missing for offer send.';
		return;
	}

	const key = aepActionKey(planName, 'send_offer');
	pendingAepActionKey.value = key;
	error.value = '';

	try {
		await sendAdmissionsCockpitOffer({ applicant_enrollment_plan: planName });
		await refreshNow();
	} catch (err: any) {
		error.value = err?.message || 'Could not send the enrollment offer.';
	} finally {
		if (pendingAepActionKey.value === key) {
			pendingAepActionKey.value = '';
		}
	}
}

async function hydrateEnrollmentRequest(card: CockpitCard) {
	const planName = String(card?.aep?.name || '').trim();
	if (!planName) {
		error.value = 'Enrollment plan reference is missing for request hydration.';
		return;
	}

	const key = aepActionKey(planName, 'hydrate_request');
	pendingAepActionKey.value = key;
	error.value = '';

	try {
		await hydrateAdmissionsCockpitRequest({ applicant_enrollment_plan: planName });
		await refreshNow();
	} catch (err: any) {
		error.value = err?.message || 'Could not hydrate the enrollment request.';
	} finally {
		if (pendingAepActionKey.value === key) {
			pendingAepActionKey.value = '';
		}
	}
}

async function generateDepositInvoice(card: CockpitCard) {
	const planName = String(card?.aep?.name || '').trim();
	if (!planName) {
		error.value = 'Enrollment plan reference is missing for deposit invoicing.';
		return;
	}

	const key = aepActionKey(planName, 'generate_deposit');
	pendingAepActionKey.value = key;
	error.value = '';

	try {
		await generateAdmissionsCockpitDepositInvoice({ applicant_enrollment_plan: planName });
		await refreshNow();
	} catch (err: any) {
		error.value = err?.message || 'Could not generate the deposit invoice.';
	} finally {
		if (pendingAepActionKey.value === key) {
			pendingAepActionKey.value = '';
		}
	}
}

async function loadThread(card: CockpitCard, markRead: boolean = true) {
	threadLoading.value = true;
	threadError.value = '';
	try {
		const payload = await getAdmissionsCaseThread({
			context_doctype: 'Student Applicant',
			context_name: card.name,
			limit_start: 0,
			limit: 200,
		});
		threadMessages.value = payload.messages || [];
		if (markRead) {
			await markAdmissionsCaseRead({
				context_doctype: 'Student Applicant',
				context_name: card.name,
			});
			queueRefresh();
		}
	} catch (err: any) {
		threadError.value = err?.message || 'Could not load case communication.';
	} finally {
		threadLoading.value = false;
	}
}

function openThread(card: CockpitCard) {
	activeThreadCard.value = card;
	threadDraft.value = '';
	threadInternalNote.value = false;
	threadSendError.value = '';
	void loadThread(card, true);
}

function closeThread() {
	activeThreadCard.value = null;
	threadMessages.value = [];
	threadDraft.value = '';
	threadInternalNote.value = false;
	threadSendError.value = '';
}

async function sendThreadMessage() {
	const card = activeThreadCard.value;
	if (!card) {
		threadSendError.value = 'No applicant selected.';
		return;
	}
	const body = threadDraft.value.trim();
	if (!body) {
		threadSendError.value = 'Please write a message before sending.';
		return;
	}

	threadSendError.value = '';
	threadSending.value = true;
	try {
		await sendAdmissionsCaseMessage({
			context_doctype: 'Student Applicant',
			context_name: card.name,
			body,
			applicant_visible: threadInternalNote.value ? 0 : 1,
			client_request_id: `admissions_case_message_${Date.now()}_${Math.random().toString(16).slice(2)}`,
		});
		threadDraft.value = '';
		threadInternalNote.value = false;
		await loadThread(card, false);
		queueRefresh();
	} catch (err: any) {
		threadSendError.value = err?.message || 'Could not send message.';
	} finally {
		threadSending.value = false;
	}
}

async function refreshNow() {
	const token = ++requestToken;
	loading.value = true;
	error.value = '';
	try {
		const payload = await getAdmissionsCockpitData({
			organization: filters.value.organization || undefined,
			school: filters.value.school || undefined,
			assigned_to_me: filters.value.assigned_to_me ? 1 : 0,
			limit: 120,
		});
		if (token !== requestToken) {
			return;
		}
		data.value = payload;

		if (filters.value.school && !schools.value.includes(filters.value.school)) {
			filters.value.school = '';
		}
	} catch (err: any) {
		if (token !== requestToken) {
			return;
		}
		error.value = err?.message || 'Could not load admissions cockpit.';
	} finally {
		if (token === requestToken) {
			loading.value = false;
		}
	}
}

watch(
	() => [filters.value.organization, filters.value.school, filters.value.assigned_to_me],
	() => {
		queueRefresh();
	}
);

onMounted(() => {
	unsubscribeCockpitInvalidate = uiSignals.subscribe(SIGNAL_ADMISSIONS_COCKPIT_INVALIDATE, () => {
		queueRefresh();
	});
	void refreshNow();
});

onUnmounted(() => {
	if (refreshTimer) {
		clearTimeout(refreshTimer);
		refreshTimer = null;
	}
	unsubscribeCockpitInvalidate?.();
	unsubscribeCockpitInvalidate = null;
});
</script>
