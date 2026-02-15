<!-- ifitwala_ed/ui-spa/src/pages/guardian/GuardianActivities.vue -->
<template>
	<div class="space-y-6">
		<header class="card-surface p-5 sm:p-6">
			<div class="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
				<div>
					<p class="type-overline text-ink/60">Guardian Activities</p>
					<h1 class="type-h1 text-ink">Family Activity Board</h1>
					<p class="type-body text-ink/70">
						Book for multiple children in one flow with transparent capacity, fairness, and billing.
					</p>
				</div>
				<div class="flex items-center gap-2">
					<RouterLink class="if-action" :to="{ name: 'guardian-home' }">Back to Home</RouterLink>
					<button type="button" class="if-action" :disabled="loading" @click="loadBoard">Refresh</button>
				</div>
			</div>
		</header>

		<section class="grid grid-cols-2 gap-3 sm:grid-cols-4">
			<article class="mini-kpi-card">
				<p class="mini-kpi-label">Children</p>
				<p class="mini-kpi-value">{{ students.length }}</p>
			</article>
			<article class="mini-kpi-card">
				<p class="mini-kpi-label">Open offerings</p>
				<p class="mini-kpi-value">{{ openNowCount }}</p>
			</article>
			<article class="mini-kpi-card">
				<p class="mini-kpi-label">Active bookings</p>
				<p class="mini-kpi-value">{{ activeBookingCount }}</p>
			</article>
			<article class="mini-kpi-card">
				<p class="mini-kpi-label">Waitlist entries</p>
				<p class="mini-kpi-value">{{ waitlistCount }}</p>
			</article>
		</section>

		<section v-if="loading" class="card-surface p-5">
			<p class="type-body text-ink/70">Loading family board...</p>
		</section>
		<section v-else-if="errorMessage" class="card-surface p-5">
			<p class="type-body-strong text-flame">Could not load family activity board.</p>
			<p class="type-body text-ink/70">{{ errorMessage }}</p>
		</section>

		<template v-else>
			<section class="card-surface p-5">
				<div class="mb-3 flex items-center justify-between gap-3">
					<h2 class="type-h3 text-ink">Family Booking Summary</h2>
					<p class="type-caption text-ink/60">One place for all children, low-click flow.</p>
				</div>

				<p v-if="!students.length" class="type-body text-ink/70">
					No linked students found for this guardian account.
				</p>

				<div v-else class="space-y-3">
					<article
						v-for="student in students"
						:key="student.student"
						class="rounded-xl border border-line-soft bg-surface-soft p-4"
					>
						<div class="mb-2 flex flex-wrap items-center justify-between gap-2">
							<p class="type-body-strong text-ink">{{ student.full_name }}</p>
							<span class="type-caption text-ink/60">{{ student.cohort || student.student }}</span>
						</div>
						<p v-if="!student.bookings.length" class="type-caption text-ink/70">
							No bookings yet.
						</p>
						<ul v-else class="space-y-2">
							<li
								v-for="booking in student.bookings"
								:key="booking.name"
								class="rounded-lg border border-line-soft bg-white p-3"
							>
								<div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
									<div>
										<p class="type-body-strong text-ink">{{ offeringTitle(booking.program_offering) }}</p>
										<p class="type-caption text-ink/70">
											Section: {{ booking.allocated_student_group || 'Pending assignment' }}
										</p>
										<p
											v-if="showWaitlistPosition && booking.waitlist_position"
											class="type-caption text-ink/70"
										>
											Waitlist position: {{ booking.waitlist_position }}
										</p>
									</div>
									<div class="flex flex-wrap items-center gap-2">
										<ActivityStatusBadge :status="booking.status" :label="booking.status_label" />
										<a
											v-if="booking.sales_invoice_url && booking.payment_required"
											class="if-action"
											:href="booking.sales_invoice_url"
											target="_blank"
											rel="noopener"
										>
											View invoice
										</a>
										<button
											v-if="booking.status === 'Offered' || booking.status === 'Waitlisted'"
											type="button"
											class="if-action"
											:disabled="actionLoading[booking.name]"
											@click="confirmOffer(booking.name)"
										>
											Accept spot
										</button>
										<button
											v-if="canCancel(booking.status)"
											type="button"
											class="if-action"
											:disabled="actionLoading[booking.name]"
											@click="cancelBooking(booking.name)"
										>
											Cancel
										</button>
									</div>
								</div>
							</li>
						</ul>
					</article>
				</div>
			</section>

			<section class="space-y-4">
				<div class="flex items-center justify-between gap-3">
					<h2 class="type-h3 text-ink">Book New Activities</h2>
					<p class="type-caption text-ink/60">Select children and submit once per offering.</p>
				</div>

				<p v-if="!offerings.length" class="card-surface p-5 type-body text-ink/70">
					No activity offerings are open right now.
				</p>

				<div v-else class="space-y-4">
					<ActivityOfferingCard
						v-for="offering in offerings"
						:key="offering.program_offering"
						:offering="offering"
					>
						<template #actions>
							<div class="space-y-3">
								<div class="flex flex-wrap items-center gap-2">
									<button
										type="button"
										class="if-action"
										@click="toggleEmbeddedComms(offering.program_offering)"
									>
										{{ embeddedCommsOffering === offering.program_offering ? 'Hide updates' : 'Show updates' }}
									</button>
									<p class="type-caption text-ink/70">Max ranked choices: {{ maxChoices }}</p>
								</div>

								<div
									v-if="!canBookOffering(offering)"
									class="rounded-lg border border-line-soft bg-surface-soft p-3 type-caption text-ink/70"
								>
									Booking is not currently open for guardian booking.
								</div>

								<div v-else class="space-y-3">
									<article
										v-for="student in students"
										:key="`${offering.program_offering}-${student.student}`"
										class="rounded-lg border border-line-soft bg-white p-3"
									>
										<div class="mb-2 flex items-center justify-between gap-2">
											<label class="inline-flex items-center gap-2 type-body-strong text-ink">
												<input
													v-model="familySelection[offering.program_offering][student.student].enabled"
													type="checkbox"
													class="rounded border-line-soft"
												/>
												{{ student.full_name }}
											</label>
											<span class="type-caption text-ink/60">{{ student.cohort || student.student }}</span>
										</div>
										<div
											v-if="familySelection[offering.program_offering][student.student].enabled"
											class="grid gap-2 sm:grid-cols-2"
										>
											<label
												v-for="(_, idx) in rankSlots(offering.program_offering, student.student)"
												:key="`${offering.program_offering}-${student.student}-choice-${idx}`"
												class="flex flex-col gap-1"
											>
												<span class="type-label">Choice {{ idx + 1 }}</span>
												<select
													v-model="familySelection[offering.program_offering][student.student].choices[idx]"
													class="rounded-lg border border-line-soft bg-white px-3 py-2 type-caption text-ink"
												>
													<option value="">Select section</option>
													<option
														v-for="section in offering.sections"
														:key="`${offering.program_offering}-${student.student}-${section.student_group}`"
														:value="section.student_group"
													>
														{{ section.label }}
													</option>
												</select>
											</label>
										</div>
									</article>
								</div>

								<p v-if="submitError[offering.program_offering]" class="type-caption text-flame">
									{{ submitError[offering.program_offering] }}
								</p>
								<ul v-if="batchResult[offering.program_offering]?.length" class="space-y-1">
									<li
										v-for="(row, idx) in batchResult[offering.program_offering]"
										:key="`${offering.program_offering}-result-${idx}`"
										class="type-caption"
										:class="row.ok ? 'text-leaf' : 'text-flame'"
									>
										{{ row.student || 'Unknown student' }} · {{ row.ok ? 'Booked' : row.error }}
									</li>
								</ul>

								<button
									type="button"
									class="if-action"
									:disabled="submitLoading[offering.program_offering] || !canBookOffering(offering)"
									@click="submitFamilyBooking(offering.program_offering)"
								>
									Submit for selected children
								</button>

								<ActivityCommunicationPanel
									v-if="embeddedCommsOffering === offering.program_offering"
									:program-offering="offering.program_offering"
								/>
							</div>
						</template>
					</ActivityOfferingCard>
				</div>
			</section>

			<section class="card-surface p-5">
				<div class="mb-3 flex items-center justify-between gap-3">
					<h2 class="type-h3 text-ink">Communication Center</h2>
					<select
						v-model="centerOffering"
						class="rounded-lg border border-line-soft bg-white px-3 py-2 type-caption text-ink"
					>
						<option v-for="offering in offerings" :key="`center-${offering.program_offering}`" :value="offering.program_offering">
							{{ offering.title }}
						</option>
					</select>
				</div>
				<ActivityCommunicationPanel :program-offering="centerOffering || null" />
			</section>
		</template>
	</div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { toast } from 'frappe-ui'

import ActivityCommunicationPanel from '@/components/activity/ActivityCommunicationPanel.vue'
import ActivityOfferingCard from '@/components/activity/ActivityOfferingCard.vue'
import ActivityStatusBadge from '@/components/activity/ActivityStatusBadge.vue'

import {
	cancelActivityBooking,
	confirmActivityBookingOffer,
	getActivityPortalBoard,
	submitActivityBookingBatch,
} from '@/lib/services/activityBooking/activityBookingService'

import type { ActivityOffering, ActivityStudentBoard } from '@/types/contracts/activity_booking/get_activity_portal_board'

type FamilySelection = Record<
	string,
	Record<
		string,
		{
			enabled: boolean
			choices: string[]
		}
	>
>

const loading = ref<boolean>(true)
const errorMessage = ref<string>('')
const board = ref<{
	settings: { default_max_choices: number; default_show_waitlist_position: 0 | 1 }
	students: ActivityStudentBoard[]
	offerings: ActivityOffering[]
} | null>(null)

const familySelection = ref<FamilySelection>({})
const submitLoading = ref<Record<string, boolean>>({})
const submitError = ref<Record<string, string>>({})
const batchResult = ref<Record<string, Array<{ ok: boolean; student?: string; error?: string | null }>>>({})
const actionLoading = ref<Record<string, boolean>>({})
const embeddedCommsOffering = ref<string>('')
const centerOffering = ref<string>('')

const students = computed<ActivityStudentBoard[]>(() => board.value?.students || [])
const offerings = computed<ActivityOffering[]>(() => board.value?.offerings || [])
const maxChoices = computed<number>(() => Math.max(1, board.value?.settings?.default_max_choices || 3))
const showWaitlistPosition = computed<boolean>(() => Boolean(board.value?.settings?.default_show_waitlist_position))

const openNowCount = computed<number>(() => offerings.value.filter((row) => row.booking_window.is_open_now).length)
const activeBookingCount = computed<number>(() =>
	students.value.reduce(
		(total, student) =>
			total +
			student.bookings.filter((row) => ['Submitted', 'Waitlisted', 'Offered', 'Confirmed'].includes(row.status)).length,
		0
	)
)
const waitlistCount = computed<number>(() =>
	students.value.reduce((total, student) => total + student.bookings.filter((row) => row.status === 'Waitlisted').length, 0)
)

function offeringTitle(programOffering: string): string {
	const found = offerings.value.find((row) => row.program_offering === programOffering)
	return found?.title || programOffering
}

function canCancel(status: string): boolean {
	return ['Submitted', 'Waitlisted', 'Offered', 'Confirmed'].includes(status)
}

function canBookOffering(offering: ActivityOffering): boolean {
	return Boolean(offering.booking_window.is_open_now && offering.booking_roles.allow_guardian)
}

function normalizeChoices(values: string[]): string[] {
	const out: string[] = []
	for (const value of values) {
		const section = (value || '').trim()
		if (!section || out.includes(section)) continue
		out.push(section)
	}
	return out
}

function ensureFamilySelection(offeringKey: string, sectionNames: string[]) {
	if (!familySelection.value[offeringKey]) {
		familySelection.value[offeringKey] = {}
	}
	for (const student of students.value) {
		if (!familySelection.value[offeringKey][student.student]) {
			familySelection.value[offeringKey][student.student] = {
				enabled: false,
				choices: sectionNames.slice(0, maxChoices.value),
			}
		}
	}
}

function rankSlots(offeringKey: string, student: string): string[] {
	const sectionNames =
		offerings.value.find((row) => row.program_offering === offeringKey)?.sections.map((row) => row.student_group) || []
	ensureFamilySelection(offeringKey, sectionNames)
	const row = familySelection.value[offeringKey][student]
	const total = Math.min(maxChoices.value, Math.max(sectionNames.length, 1))
	while (row.choices.length < total) row.choices.push('')
	row.choices = row.choices.slice(0, total)
	return row.choices
}

async function loadBoard() {
	loading.value = true
	errorMessage.value = ''
	try {
		const payload = await getActivityPortalBoard({})
		board.value = {
			settings: payload.settings,
			students: payload.students,
			offerings: payload.offerings,
		}
		for (const offering of payload.offerings) {
			ensureFamilySelection(
				offering.program_offering,
				offering.sections.map((section) => section.student_group)
			)
		}
		if (!centerOffering.value && payload.offerings.length) {
			centerOffering.value = payload.offerings[0].program_offering
		}
	} catch (error) {
		const message = error instanceof Error ? error.message : String(error || '')
		errorMessage.value = message || 'Could not load activities.'
	} finally {
		loading.value = false
	}
}

function makeIdempotencyKey(student: string, programOffering: string): string {
	const randomPart = Math.random().toString(36).slice(2, 9)
	return `${student}:${programOffering}:${Date.now()}:${randomPart}`
}

async function submitFamilyBooking(programOffering: string) {
	const selection = familySelection.value[programOffering]
	if (!selection) {
		submitError.value[programOffering] = 'Family selection context missing.'
		return
	}
	const requests = Object.entries(selection)
		.filter(([, row]) => row.enabled)
		.map(([student, row]) => ({
			student,
			choices: normalizeChoices(row.choices),
			idempotency_key: makeIdempotencyKey(student, programOffering),
			request_surface: 'Guardian Portal',
		}))
		.filter((row) => row.choices.length > 0)

	if (!requests.length) {
		submitError.value[programOffering] =
			'Select at least one child and one section choice before submitting.'
		return
	}

	submitLoading.value[programOffering] = true
	submitError.value[programOffering] = ''
	batchResult.value[programOffering] = []
	try {
		const response = await submitActivityBookingBatch({
			program_offering: programOffering,
			requests,
			request_surface: 'Guardian Portal',
		})
		batchResult.value[programOffering] = (response.results || []).map((row) => ({
			ok: Boolean(row.ok),
			student: row.student || undefined,
			error: row.error || null,
		}))
		if (response.ok) {
			toast.success('Bookings submitted for selected children.')
		} else {
			toast.error('Some bookings could not be submitted. Review results below.')
		}
		await loadBoard()
	} catch (error) {
		const message = error instanceof Error ? error.message : String(error || '')
		submitError.value[programOffering] = message || 'Could not submit family booking.'
	} finally {
		submitLoading.value[programOffering] = false
	}
}

async function confirmOffer(bookingName: string) {
	actionLoading.value[bookingName] = true
	try {
		await confirmActivityBookingOffer({ activity_booking: bookingName })
		toast.success('Spot accepted.')
		await loadBoard()
	} catch (error) {
		const message = error instanceof Error ? error.message : String(error || '')
		toast.error(message || 'Could not accept this offer.')
	} finally {
		actionLoading.value[bookingName] = false
	}
}

async function cancelBooking(bookingName: string) {
	actionLoading.value[bookingName] = true
	try {
		await cancelActivityBooking({ activity_booking: bookingName })
		toast.success('Booking cancelled.')
		await loadBoard()
	} catch (error) {
		const message = error instanceof Error ? error.message : String(error || '')
		toast.error(message || 'Could not cancel booking.')
	} finally {
		actionLoading.value[bookingName] = false
	}
}

function toggleEmbeddedComms(offeringName: string) {
	embeddedCommsOffering.value = embeddedCommsOffering.value === offeringName ? '' : offeringName
}

void loadBoard()
</script>
