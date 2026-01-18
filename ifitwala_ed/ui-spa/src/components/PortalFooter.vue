<!-- ifitwala_ed/ifitwala_ed/ui-spa/src/components/PortalFooter.vue -->
 
<template>
	<footer
		class="fixed bottom-0 left-0 right-0 z-50 bg-white/95 backdrop-blur border-t border-gray-200 print:hidden"
		role="contentinfo"
	>
		<div class="mx-auto max-w-7xl px-3 py-2">
			<div class="flex flex-col md:flex-row items-center justify-between gap-2">
				<nav aria-label="Footer links">
					<ul class="flex flex-wrap items-center justify-center md:justify-start text-xs sm:text-sm text-gray-600">
						<li v-for="(item, i) in footerItems" :key="item.name" class="flex items-center">
							<!-- Regular links -->
							<RouterLink
								v-if="item.to"
								:to="item.to"
								class="px-1 hover:text-blue-600 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/60 rounded-sm"
							>
								{{ item.name }}
							</RouterLink>
							<a
								v-else-if="item.href"
								:href="item.href"
								class="px-1 hover:text-blue-600 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/60 rounded-sm"
							>
								{{ item.name }}
							</a>

							<!-- Help launcher (opens modal) -->
							<button
								v-else
								type="button"
								class="px-1 hover:text-blue-600 underline-offset-2 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/60 rounded-sm"
								@click="open = true"
							>
								{{ item.name }}
							</button>

							<span v-if="i < footerItems.length - 1" class="mx-2 select-none text-gray-300" aria-hidden="true">•</span>
						</li>
					</ul>
				</nav>

				<p class="text-[11px] sm:text-xs text-gray-500">
					&copy; {{ currentYear }} Ifitwala Ed
				</p>
			</div>
		</div>
	</footer>

	<!-- Help Modal -->
	<Dialog v-model="open" :options="{ title: 'Contact Us / Help', size: 'lg' }">
		<div class="space-y-4">
			<!-- Consent -->
			<label class="flex items-start gap-2 text-sm">
				<input type="checkbox" v-model="form.consent" class="mt-0.5" />
				<span>
					I understand this is not an emergency service and consent to share this information with the counsellor team.
				</span>
			</label>

			<!-- Quick crisis microcopy -->
			<div class="rounded border border-red-200 bg-red-50 p-2 text-xs text-red-700">
				If you or someone else is in immediate danger, contact local emergency services. This form is not monitored 24/7.
			</div>

			<!-- Category & Severity -->
			<div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
				<div class="flex flex-col gap-1">
					<label class="text-xs text-gray-600">Referral Category</label>
					<select v-model="form.referral_category" class="rounded border border-gray-300 px-2 py-1.5">
						<option value="">Select…</option>
						<option v-for="c in CATEGORIES" :key="c" :value="c">{{ c }}</option>
					</select>
				</div>
				<div class="flex flex-col gap-1">
					<label class="text-xs text-gray-600">Severity</label>
					<select v-model="form.severity" class="rounded border border-gray-300 px-2 py-1.5">
						<option value="">Select…</option>
						<option v-for="s in SEVERITY" :key="s" :value="s">{{ s }}</option>
					</select>
				</div>
			</div>

			<!-- Description -->
			<div class="flex flex-col gap-1">
				<label class="text-xs text-gray-600">Describe what you’d like us to know</label>
				<textarea
					v-model="form.referral_description"
					rows="5"
					class="rounded border border-gray-300 px-2 py-1.5"
					placeholder="Write in your own words…"
				/>
				<p class="text-[11px] text-gray-500">Avoid sharing passwords or highly sensitive private information.</p>
			</div>

			<!-- Contact preferences -->
			<div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
				<div class="flex flex-col gap-1">
					<label class="text-xs text-gray-600">Preferred contact method</label>
					<select v-model="form.preferred_contact_method" class="rounded border border-gray-300 px-2 py-1.5">
						<option value="">—</option>
						<option>Email</option>
						<option>In-app</option>
						<option>Phone</option>
					</select>
				</div>
				<label class="flex items-start gap-2 text-sm mt-6 sm:mt-0">
					<input type="checkbox" v-model="form.ok_to_contact_guardians" class="mt-0.5" />
					<span>It’s okay to contact my guardians if necessary</span>
				</label>
			</div>

			<div class="flex flex-col gap-1">
				<label class="text-xs text-gray-600">Safe times to contact (optional)</label>
				<input
					type="text"
					v-model="form.safe_times_to_contact"
					class="rounded border border-gray-300 px-2 py-1.5"
					placeholder="e.g., Lunch, after school, not during Math…"
				/>
			</div>

			<!-- Attachments (images / PDFs) -->
			<div class="flex flex-col gap-1">
				<label class="text-xs text-gray-600">Attachments (optional)</label>
				<input ref="fileInput" type="file" accept=".png,.jpg,.jpeg,.pdf" multiple class="text-sm" />
				<p class="text-[11px] text-gray-500">Images or PDFs only (max 10 MB each).</p>
			</div>

			<!-- Actions -->
			<div class="flex items-center justify-end gap-2 pt-1">
				<Button theme="secondary" @click="open = false">Cancel</Button>
				<Button :loading="submitting" :disabled="!canSubmit" @click="submit">
					Submit
				</Button>
			</div>

			<!-- Confidentiality microcopy -->
			<p class="text-[11px] text-gray-500">
				Confidentiality: by default, your submission will be visible to the counsellor case team only.
			</p>
		</div>
	</Dialog>
</template>

<script setup>
import { computed, reactive, ref } from 'vue';
import { Dialog, Button, toast } from 'frappe-ui';
import { RouterLink } from 'vue-router';

const currentYear = computed(() => new Date().getFullYear());
const open = ref(false);
const submitting = ref(false);
const fileInput = ref(null);

// Footer links (Help triggers modal)
const footerItems = [
	{ name: 'Privacy Policy', href: '/privacy' },
	{ name: 'School Website', href: '/' },
	{ name: 'Contact Us / Help', help: true }, // modal launcher
	{ name: 'Calendar', to: '/calendar' },
	{ name: 'Student Handbook', to: '/handbook' },
];

const CATEGORIES = ['Social', 'Emotional', 'Pastoral', 'Academic', 'Behavior', 'Attendance'];
const SEVERITY = ['Low', 'Moderate', 'High', 'Critical'];

const form = reactive({
	consent: false,
	referral_category: '',
	severity: '',
	referral_description: '',
	preferred_contact_method: '',
	ok_to_contact_guardians: false,
	safe_times_to_contact: '',
});

const canSubmit = computed(() => {
	return (
		form.consent &&
		form.referral_category.trim().length > 0 &&
		form.severity.trim().length > 0 &&
		(form.referral_description.trim().length >= 10)
	);
});

function captureContext() {
	try {
		const d = new Date();
		return [
			'',
			'---',
			'Context (auto-captured):',
			`Route: ${location.pathname}${location.search}${location.hash}`,
			`UA: ${navigator.userAgent}`,
			`Viewport: ${window.innerWidth}x${window.innerHeight}`,
			`TZ Offset: ${new Date().getTimezoneOffset()} min`,
			`Local Time: ${d.toISOString()}`,
			'---',
			'',
		].join('\n');
	} catch {
		return '';
	}
}

async function submit() {
	if (!canSubmit.value || submitting.value) return;
	submitting.value = true;

	// Append context to the description (server safely ignores extra text)
	const payload = {
		referral_category: form.referral_category,
		severity: form.severity,
		referral_description: `${form.referral_description}\n${captureContext()}`,
		preferred_contact_method: form.preferred_contact_method || '',
		ok_to_contact_guardians: form.ok_to_contact_guardians ? 1 : 0,
		safe_times_to_contact: form.safe_times_to_contact || '',
	};

	try {
		const { message } = await frappe.call({
			method: 'ifitwala_ed.utilities.portal_utils.create_self_referral',
			type: 'POST',
			args: payload,
		});

		const name = message?.name;
		// Upload attachments sequentially
		const files = fileInput.value?.files ? Array.from(fileInput.value.files) : [];
		for (const file of files) {
			const fd = new FormData();
			fd.append('referral_name', name);
			fd.append('file', file, file.name);

			const resp = await fetch('/api/method/ifitwala_ed.utilities.portal_utils.upload_self_referral_file', {
				method: 'POST',
				body: fd,
				headers: { 'X-Frappe-CSRF-Token': frappe.csrf_token },
			});
			if (!resp.ok) {
				// Non-blocking: show a warning but keep success for the referral itself
				console.warn('Upload failed:', file.name, await resp.text());
				toast({
					title: 'Some files failed to upload',
					text: 'You can add attachments later with a counselor.',
					icon: 'alert',
					theme: 'orange',
				});
			}
		}

		toast({
			title: 'Submitted',
			text: name
				? `Thank you. Your message has been sent to the counsellor team. Reference: ${name}`
				: 'Thank you. Your message has been sent to the counsellor team.',
			icon: 'check',
			theme: 'green',
		});

		// Reset and close
		resetForm();
		open.value = false;
	} catch (err) {
		console.error(err);
		toast({
			title: 'Could not submit',
			text: 'Please review your entries and try again. If the problem persists, contact the school counsellor.',
			icon: 'x',
			theme: 'red',
		});
	} finally {
		submitting.value = false;
	}
}

function resetForm() {
	form.consent = false;
	form.referral_category = '';
	form.severity = '';
	form.referral_description = '';
	form.preferred_contact_method = '';
	form.ok_to_contact_guardians = false;
	form.safe_times_to_contact = '';
	if (fileInput.value) fileInput.value.value = '';
}
</script>
