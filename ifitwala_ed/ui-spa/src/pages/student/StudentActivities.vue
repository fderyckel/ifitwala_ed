<!-- ifitwala_ed/ui-spa/src/pages/student/StudentActivities.vue -->
<template>
	<div class="space-y-6">
		<header class="card-surface p-5 sm:p-6">
			<div class="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
				<div>
					<p class="type-overline text-ink/60">Student Activities</p>
					<h1 class="type-h1 text-ink">After-School Booking</h1>
					<p class="type-body text-ink/70">
						Choose activities with clear capacity, fairness rules, pricing, and updates.
					</p>
				</div>
				<div class="flex items-center gap-2">
					<RouterLink class="if-action" :to="{ name: 'student-home' }">Back to Home</RouterLink>
					<button type="button" class="if-action" :disabled="loading" @click="loadBoard">Refresh</button>
				</div>
			</div>
		</header>

		<section class="grid grid-cols-2 gap-3 sm:grid-cols-4">
			<article class="mini-kpi-card">
				<p class="mini-kpi-label">Open now</p>
				<p class="mini-kpi-value">{{ openNowCount }}</p>
			</article>
			<article class="mini-kpi-card">
				<p class="mini-kpi-label">My active bookings</p>
				<p class="mini-kpi-value">{{ activeBookingCount }}</p>
			</article>
			<article class="mini-kpi-card">
				<p class="mini-kpi-label">Waitlist spots</p>
				<p class="mini-kpi-value">{{ waitlistCount }}</p>
			</article>
			<article class="mini-kpi-card">
				<p class="mini-kpi-label">Offers expiring soon</p>
				<p class="mini-kpi-value">{{ expiringOfferCount }}</p>
			</article>
		</section>

		<section v-if="loading" class="card-surface p-5">
			<p class="type-body text-ink/70">Loading activity board...</p>
		</section>
		<section v-else-if="errorMessage" class="card-surface p-5">
			<p class="type-body-strong text-flame">Could not load activity board.</p>
			<p class="type-body text-ink/70">{{ errorMessage }}</p>
		</section>

		<template v-else>
			<section class="card-surface p-5">
				<div class="mb-3 flex items-center justify-between gap-3">
					<h2 class="type-h3 text-ink">My Bookings</h2>
					<p class="type-caption text-ink/60">Humanized statuses are shown for clarity.</p>
				</div>
				<p v-if="!studentBookings.length" class="type-body text-ink/70">
					No bookings yet. Choose an activity below.
				</p>
				<ul v-else class="space-y-2">
					<li
						v-for="booking in studentBookings"
						:key="booking.name"
						class="rounded-lg border border-line-soft bg-surface-soft p-3"
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
								<p v-if="offerHint(booking)" class="type-caption text-ink/70">
									{{ offerHint(booking) }}
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
			</section>

			<section class="space-y-4">
				<div class="flex items-center justify-between gap-3">
					<h2 class="type-h3 text-ink">Available Activities</h2>
					<p class="type-caption text-ink/60">Transparent allocation and section capacity are shown.</p>
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
									Booking is not currently open for student self-booking.
								</div>

								<div v-else class="grid gap-3 sm:grid-cols-2">
									<label
										v-for="(_, idx) in rankSlots(offering.program_offering)"
										:key="`${offering.program_offering}-rank-${idx}`"
										class="flex flex-col gap-1"
									>
										<span class="type-label">Choice {{ idx + 1 }}</span>
										<select
											v-model="choiceState[offering.program_offering][idx]"
											class="rounded-lg border border-line-soft bg-white px-3 py-2 type-body text-ink"
										>
											<option value="">Select section</option>
											<option
												v-for="section in offering.sections"
												:key="`${offering.program_offering}-${section.student_group}`"
												:value="section.student_group"
											>
												{{ section.label }}
											</option>
										</select>
									</label>
								</div>

								<div v-if="submitError[offering.program_offering]" class="type-caption text-flame">
									{{ submitError[offering.program_offering] }}
								</div>

								<div class="flex items-center gap-2">
									<button
										type="button"
										class="if-action"
										:disabled="submitLoading[offering.program_offering] || !canBookOffering(offering)"
										@click="submitBooking(offering.program_offering)"
									>
										Submit booking
									</button>
									<p class="type-caption text-ink/70">
										{{ offering.allocation_mode }} · {{ offering.booking_status }}
									</p>
								</div>

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
	submitActivityBooking,
} from '@/lib/services/activityBooking/activityBookingService'

import type { ActivityBookingRow, ActivityOffering, ActivityStudentBoard } from '@/types/contracts/activity_booking/get_activity_portal_board'

const loading = ref<boolean>(true)
const errorMessage = ref<string>('')
const board = ref<{
	settings: { default_max_choices: number; default_show_waitlist_position: 0 | 1; default_offer_banner_hours: number }
	students: ActivityStudentBoard[]
	offerings: ActivityOffering[]
} | null>(null)

const choiceState = ref<Record<string, string[]>>({})
const submitLoading = ref<Record<string, boolean>>({})
const submitError = ref<Record<string, string>>({})
const actionLoading = ref<Record<string, boolean>>({})
const embeddedCommsOffering = ref<string>('')
const centerOffering = ref<string>('')

const studentRecord = computed<ActivityStudentBoard | null>(() => board.value?.students?.[0] || null)
const studentBookings = computed<ActivityBookingRow[]>(() => studentRecord.value?.bookings || [])
const offerings = computed<ActivityOffering[]>(() => board.value?.offerings || [])
const maxChoices = computed<number>(() => Math.max(1, board.value?.settings?.default_max_choices || 3))
const showWaitlistPosition = computed<boolean>(() => Boolean(board.value?.settings?.default_show_waitlist_position))
const offerBannerHours = computed<number>(() => Math.max(1, board.value?.settings?.default_offer_banner_hours || 24))

const openNowCount = computed<number>(() => offerings.value.filter((row) => row.booking_window.is_open_now).length)
const activeBookingCount = computed<number>(() =>
	studentBookings.value.filter((row) => ['Submitted', 'Waitlisted', 'Offered', 'Confirmed'].includes(row.status)).length
)
const waitlistCount = computed<number>(() => studentBookings.value.filter((row) => row.status === 'Waitlisted').length)
const expiringOfferCount = computed<number>(() =>
	studentBookings.value.filter((row) => row.status === 'Offered' && offerHint(row)).length
)

function normalizeChoices(values: string[]): string[] {
	const out: string[] = []
	for (const value of values) {
		const section = (value || '').trim()
		if (!section || out.includes(section)) continue
		out.push(section)
	}
	return out
}

function ensureChoiceState(offeringKey: string, sectionNames: string[]) {
	if (!choiceState.value[offeringKey]) {
		choiceState.value[offeringKey] = sectionNames.slice(0, maxChoices.value)
		return
	}
	if (!choiceState.value[offeringKey].length) {
		choiceState.value[offeringKey] = sectionNames.slice(0, maxChoices.value)
	}
}

function rankSlots(offeringKey: string): string[] {
	const rows = offerings.value.find((row) => row.program_offering === offeringKey)?.sections || []
	const sectionNames = rows.map((row) => row.student_group)
	ensureChoiceState(offeringKey, sectionNames)
	const total = Math.min(maxChoices.value, Math.max(sectionNames.length, 1))
	const values = choiceState.value[offeringKey] || []
	while (values.length < total) values.push('')
	choiceState.value[offeringKey] = values.slice(0, total)
	return choiceState.value[offeringKey]
}

function offeringTitle(programOffering: string): string {
	const found = offerings.value.find((row) => row.program_offering === programOffering)
	return found?.title || programOffering
}

function canCancel(status: string): boolean {
	return ['Submitted', 'Waitlisted', 'Offered', 'Confirmed'].includes(status)
}

function canBookOffering(offering: ActivityOffering): boolean {
	return Boolean(offering.booking_window.is_open_now && offering.booking_roles.allow_student)
}

function offerHint(booking: ActivityBookingRow): string {
	if (booking.status !== 'Offered' || !booking.offer_expires_on) return ''
	const expiry = new Date(booking.offer_expires_on)
	if (Number.isNaN(expiry.getTime())) return ''
	const hours = Math.floor((expiry.getTime() - Date.now()) / (1000 * 60 * 60))
	if (hours < 0) return 'Offer expired; refresh for latest status.'
	if (hours <= offerBannerHours.value) {
		return `Offer expires in about ${hours}h.`
	}
	return `Offer valid until ${expiry.toLocaleString()}.`
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

async function submitBooking(programOffering: string) {
	const student = studentRecord.value?.student
	if (!student) {
		submitError.value[programOffering] = 'Student context is missing.'
		return
	}
	const choices = normalizeChoices(choiceState.value[programOffering] || [])
	if (!choices.length) {
		submitError.value[programOffering] = 'Select at least one section choice before submitting.'
		return
	}
	submitLoading.value[programOffering] = true
	submitError.value[programOffering] = ''
	try {
		await submitActivityBooking({
			program_offering: programOffering,
			student,
			choices,
			idempotency_key: makeIdempotencyKey(student, programOffering),
			request_surface: 'Student Portal',
		})
		toast.success('Activity booking submitted.')
		await loadBoard()
	} catch (error) {
		const message = error instanceof Error ? error.message : String(error || '')
		submitError.value[programOffering] = message || 'Could not submit booking.'
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
