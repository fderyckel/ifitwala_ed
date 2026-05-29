<!-- ifitwala_ed/ui-spa/src/components/activity/ActivityOfferingCard.vue -->
<template>
	<article class="card-surface p-5">
		<div class="mb-3 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
			<div>
				<p class="type-overline text-ink/60">
					{{ offering.school_abbr || offering.school_label }}
				</p>
				<h3 class="type-h3 text-ink">{{ offering.title }}</h3>
				<p class="type-caption text-ink/70">{{ offering.program_label }}</p>
			</div>
			<div class="flex flex-wrap items-center gap-2">
				<span class="chip">{{ offering.allocation_mode }}</span>
				<span v-if="offering.waitlist.enabled" class="chip">{{ __('Waitlist enabled') }}</span>
				<span v-if="offering.payment.required" class="chip">
					{{ currencyLabel(offering.payment.amount) }}
				</span>
			</div>
		</div>

		<p class="type-body text-ink/80">{{ offering.allocation_explanation }}</p>
		<p class="mt-2 type-caption text-ink/70">{{ bookingWindowLabel }}</p>

		<div v-if="offering.activity_context.descriptions" class="mt-3 type-body text-ink/80">
			{{ offering.activity_context.descriptions }}
		</div>

		<div class="mt-4 grid gap-3 md:grid-cols-2">
			<div class="rounded-xl border border-line-soft bg-surface-soft p-3">
				<p class="type-label">{{ __('Logistics') }}</p>
				<p class="mt-1 type-caption text-ink/80">
					{{
						offering.activity_context.logistics_location_label ||
						__('Location shared by school update')
					}}
				</p>
				<p
					v-if="offering.activity_context.logistics_pickup_instructions"
					class="type-caption text-ink/70"
				>
					{{ __('Pickup: {0}', [offering.activity_context.logistics_pickup_instructions]) }}
				</p>
				<p
					v-if="offering.activity_context.logistics_dropoff_instructions"
					class="type-caption text-ink/70"
				>
					{{ __('Drop-off: {0}', [offering.activity_context.logistics_dropoff_instructions]) }}
				</p>
				<a
					v-if="offering.activity_context.logistics_map_url"
					class="mt-1 inline-flex type-caption text-jacaranda hover:underline"
					:href="offering.activity_context.logistics_map_url"
					target="_blank"
					rel="noopener"
				>
					{{ __('Open map') }}
				</a>
			</div>

			<div class="rounded-xl border border-line-soft bg-surface-soft p-3">
				<p class="type-label">{{ __('Policy') }}</p>
				<p class="mt-1 type-caption text-ink/80">{{ __('Age: {0}', [ageLabel]) }}</p>
				<p class="type-caption text-ink/70">
					{{ __('Role access: {0}', [roleAccessLabel]) }}
				</p>
				<a
					v-if="offering.activity_context.media_gallery_link"
					class="mt-1 inline-flex type-caption text-jacaranda hover:underline"
					:href="offering.activity_context.media_gallery_link"
					target="_blank"
					rel="noopener"
				>
					{{ __('View activity media') }}
				</a>
			</div>
		</div>

		<div class="mt-4 space-y-2">
			<p class="type-label">{{ __('Sections') }}</p>
			<ul class="space-y-2">
				<li
					v-for="section in offering.sections"
					:key="section.student_group"
					class="rounded-lg border border-line-soft bg-white p-3"
				>
					<div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
						<div>
							<p class="type-body-strong text-ink">{{ section.label }}</p>
							<p class="type-caption text-ink/70">
								{{ sectionCapacityLabel(section.capacity, section.remaining) }}
							</p>
						</div>
						<p v-if="section.next_slot" class="type-caption text-ink/70">
							{{ __('Next: {0}', [dateTimeLabel(section.next_slot.start)]) }}
						</p>
					</div>
				</li>
			</ul>
		</div>

		<div class="mt-4">
			<slot name="actions" />
		</div>
	</article>
</template>

<script setup lang="ts">
import { computed } from 'vue';

import { __ } from '@/lib/i18n';
import type { ActivityOffering } from '@/types/contracts/activity_booking/get_activity_portal_board';

const props = defineProps<{
	offering: ActivityOffering;
}>();

const bookingWindowLabel = computed(() => {
	const openFrom = props.offering.booking_window.open_from;
	const openTo = props.offering.booking_window.open_to;
	if (!openFrom && !openTo) {
		return props.offering.booking_window.is_open_now
			? __('Booking is currently open.')
			: __('Booking window will be published by the school.');
	}
	const from = openFrom ? dateTimeLabel(openFrom) : __('Now');
	const to = openTo ? dateTimeLabel(openTo) : __('No closing date');
	if (props.offering.booking_window.is_open_now) {
		return __('Open now · {0} to {1}', [from, to]);
	}
	return __('Booking window · {0} to {1}', [from, to]);
});

const ageLabel = computed(() => {
	const min = props.offering.age_limits.min_years;
	const max = props.offering.age_limits.max_years;
	if (min == null && max == null) return __('No age restriction');
	if (min != null && max != null) return __('{0} to {1} years', [min, max]);
	if (min != null) return __('{0}+ years', [min]);
	return __('Up to {0} years', [max]);
});

const roleAccessLabel = computed(() => {
	const parts: string[] = [];
	if (props.offering.booking_roles.allow_student) parts.push(__('Students'));
	if (props.offering.booking_roles.allow_guardian) parts.push(__('Guardians'));
	if (!parts.length) return __('School-managed only');
	return parts.join(', ');
});

function sectionCapacityLabel(capacity?: number | null, remaining?: number | null): string {
	if (capacity == null) return __('Open capacity');
	if (remaining == null) return __('{0} seats', [capacity]);
	return __('{0} of {1} seats remaining', [remaining, capacity]);
}

function currencyLabel(amount: number): string {
	return new Intl.NumberFormat(undefined, { style: 'currency', currency: 'USD' }).format(
		amount || 0
	);
}

function dateTimeLabel(value: string | null | undefined): string {
	if (!value) return __('TBD');
	const date = new Date(value);
	if (Number.isNaN(date.getTime())) return String(value);
	return date.toLocaleString();
}
</script>
