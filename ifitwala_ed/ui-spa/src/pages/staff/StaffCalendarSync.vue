<template>
	<div class="staff-shell space-y-6">
		<header class="page-header">
			<div class="page-header__intro">
				<p class="type-overline text-ink/60">Calendar</p>
				<h1 class="type-h1 text-canopy">Phone Sync</h1>
				<p class="type-meta text-slate-token/80">
					Keep your staff calendar available in Apple Calendar or Google Calendar.
				</p>
			</div>
			<div class="page-header__actions">
				<RouterLink class="if-button if-button--secondary" :to="{ name: 'staff-home' }">
					<FeatherIcon name="arrow-left" class="h-4 w-4" />
					<span>Back to Home</span>
				</RouterLink>
				<button type="button" class="if-button if-button--quiet" :disabled="loading" @click="load">
					<FeatherIcon name="refresh-cw" class="h-4 w-4" />
					<span>Refresh</span>
				</button>
			</div>
		</header>

		<section v-if="loading" class="card-surface p-5">
			<p class="type-body text-ink/70">Loading calendar sync...</p>
		</section>

		<section v-else-if="errorMessage" class="card-surface p-5">
			<p class="type-body-strong text-flame">Calendar sync is not available.</p>
			<p class="mt-1 type-body text-ink/70">{{ errorMessage }}</p>
		</section>

		<template v-else-if="subscription">
			<section class="card-surface p-5 sm:p-6">
				<div class="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
					<div class="min-w-0 space-y-2">
						<p class="type-overline text-slate-token/70">Your link</p>
						<h2 class="type-h2 text-ink">
							{{ subscription.active ? 'Subscription active' : 'No subscription link yet' }}
						</h2>
						<p class="type-body text-ink/70">
							{{ statusCopy }}
						</p>
						<p v-if="subscription.token_hint" class="type-caption text-ink/60">
							Token ending: {{ subscription.token_hint }}
						</p>
					</div>

					<div class="flex shrink-0 flex-wrap gap-2">
						<button
							v-if="!subscription.active"
							type="button"
							class="if-button if-button--primary"
							:disabled="busy"
							@click="createLink"
						>
							<FeatherIcon name="link" class="h-4 w-4" />
							<span>Create Link</span>
						</button>
						<button
							v-else
							type="button"
							class="if-button if-button--secondary"
							:disabled="busy"
							@click="resetLink"
						>
							<FeatherIcon name="rotate-ccw" class="h-4 w-4" />
							<span>Reset Link</span>
						</button>
					</div>
				</div>

				<div v-if="subscription.active" class="mt-6 grid gap-3 lg:grid-cols-3">
					<a
						v-if="subscription.webcal_url"
						:href="subscription.webcal_url"
						class="if-button if-button--primary justify-center"
					>
						<FeatherIcon name="calendar" class="h-4 w-4" />
						<span>Apple Calendar</span>
					</a>
					<button
						type="button"
						class="if-button if-button--secondary justify-center"
						:disabled="!subscription.google_url"
						@click="copyUrl(subscription.google_url, 'Google calendar URL')"
					>
						<FeatherIcon name="copy" class="h-4 w-4" />
						<span>Copy Google URL</span>
					</button>
					<button
						type="button"
						class="if-button if-button--secondary justify-center"
						:disabled="!subscription.feed_url"
						@click="copyUrl(subscription.feed_url, 'Calendar URL')"
					>
						<FeatherIcon name="clipboard" class="h-4 w-4" />
						<span>Copy URL</span>
					</button>
				</div>

				<div
					v-if="subscription.active"
					class="mt-5 rounded-lg border border-line-soft bg-surface-soft px-4 py-3"
				>
					<p class="type-caption text-ink/70">
						Anyone with this link can read this calendar until you reset it. Google Calendar is
						added from Google Calendar on the web, then syncs to the Google Calendar app.
					</p>
				</div>
			</section>

			<section class="card-surface p-5 sm:p-6">
				<div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
					<div>
						<p class="type-overline text-slate-token/70">Included</p>
						<h2 class="type-h2 text-ink">Staff-visible events</h2>
						<p class="mt-1 type-body text-ink/70">
							The feed uses the same permissions and school scope as your staff portal calendar.
						</p>
					</div>
					<p class="type-caption text-ink/60">
						{{ windowCopy }}
					</p>
				</div>
				<div class="mt-5 flex flex-wrap gap-2">
					<span
						v-for="source in sourceLabels"
						:key="source"
						class="rounded-full border border-line-soft bg-surface px-3 py-1 type-caption text-ink/70"
					>
						{{ source }}
					</span>
				</div>
			</section>
		</template>
	</div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { RouterLink } from 'vue-router';
import { FeatherIcon, toast } from 'frappe-ui';

import {
	createOrGetStaffCalendarSubscription,
	getStaffCalendarSubscription,
	resetStaffCalendarSubscription,
} from '@/lib/services/calendar/staffCalendarSubscriptionService';
import type { Response as StaffCalendarSubscription } from '@/types/contracts/calendar/staff_calendar_subscription';

const loading = ref(true);
const busy = ref(false);
const errorMessage = ref('');
const subscription = ref<StaffCalendarSubscription | null>(null);

const SOURCE_LABELS: Record<string, string> = {
	student_group: 'Classes',
	meeting: 'Meetings',
	school_event: 'School Events',
	staff_holiday: 'School & Staff Holidays',
};

const sourceLabels = computed(() =>
	(subscription.value?.feed.sources || []).map(source => SOURCE_LABELS[source] || source)
);

const statusCopy = computed(() => {
	if (!subscription.value?.active) {
		return 'Create a private subscription link for your phone calendar.';
	}
	if (!subscription.value.feed_url) {
		return 'Reset this link to generate a new calendar URL.';
	}
	return 'Calendar apps refresh this link automatically. Updates are not instant.';
});

const windowCopy = computed(() => {
	const feed = subscription.value?.feed;
	if (!feed) return '';
	return `${feed.past_window_days} days back, ${feed.future_window_days} days ahead. Weekly offs are hidden.`;
});

function errorToMessage(error: unknown): string {
	if (!error || typeof error !== 'object') return String(error || 'Request failed.');
	return String((error as any)?.message || (error as any)?.response?.message || 'Request failed.');
}

async function load() {
	loading.value = true;
	errorMessage.value = '';
	try {
		subscription.value = await getStaffCalendarSubscription();
	} catch (error) {
		subscription.value = null;
		errorMessage.value = errorToMessage(error);
	} finally {
		loading.value = false;
	}
}

async function createLink() {
	busy.value = true;
	errorMessage.value = '';
	try {
		subscription.value = await createOrGetStaffCalendarSubscription();
		toast.success('Calendar link created.');
	} catch (error) {
		errorMessage.value = errorToMessage(error);
		toast.error(errorMessage.value);
	} finally {
		busy.value = false;
	}
}

async function resetLink() {
	if (
		typeof window !== 'undefined' &&
		!window.confirm(
			'Reset this calendar link? Existing subscriptions using the old link will stop updating.'
		)
	) {
		return;
	}

	busy.value = true;
	errorMessage.value = '';
	try {
		subscription.value = await resetStaffCalendarSubscription();
		toast.success('Calendar link reset.');
	} catch (error) {
		errorMessage.value = errorToMessage(error);
		toast.error(errorMessage.value);
	} finally {
		busy.value = false;
	}
}

async function copyUrl(value: string | null, label: string) {
	if (!value) {
		toast.error(`${label} is not available.`);
		return;
	}
	try {
		await navigator.clipboard.writeText(value);
		toast.success(`${label} copied.`);
	} catch (error) {
		toast.error(errorToMessage(error));
	}
}

onMounted(load);
</script>
