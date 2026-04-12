<!-- ifitwala_ed/ui-spa/src/components/PortalNavbar.vue -->
<template>
	<!--
  PortalNavbar.vue
  Main top navigation bar for the Staff/Student portal layout. Handles user profile and mobile menu toggle.

  Used by:
  - PortalLayout.vue (layouts)
-->
	<nav class="portal-navbar">
		<div class="portal-navbar__inner">
			<div class="portal-navbar__start">
				<button
					@click="$emit('toggle-sidebar')"
					class="portal-navbar__menu-button"
					aria-label="Toggle sidebar"
				>
					<FeatherIcon name="menu" class="h-5 w-5" />
				</button>

				<RouterLink :to="{ name: `${defaultPortal}-home` }" class="portal-navbar__brand">
					<span class="portal-navbar__brand-mark">
						<FeatherIcon name="book-open" class="h-5 w-5" />
					</span>
					<span class="portal-navbar__brand-label">Ifitwala</span>
				</RouterLink>
			</div>

			<div class="flex items-center">
				<div class="relative">
					<button @click="isUserMenuOpen = !isUserMenuOpen" class="portal-navbar__profile-trigger">
						<span class="portal-navbar__profile-name">{{ user.fullname }}</span>
						<img
							v-if="user.avatarImage"
							:src="user.avatarImage"
							:alt="`${user.fullname} avatar`"
							class="portal-navbar__avatar"
						/>
						<div v-else class="portal-navbar__avatar-fallback">
							{{ user.initials }}
						</div>
					</button>

					<transition
						enter-active-class="transition ease-out duration-100"
						enter-from-class="transform opacity-0 scale-95"
						enter-to-class="transform opacity-100 scale-100"
						leave-active-class="transition ease-in duration-75"
						leave-from-class="transform opacity-100 scale-100"
						leave-to-class="transform opacity-0 scale-95"
					>
						<div v-if="isUserMenuOpen" class="portal-navbar__menu">
							<div class="py-1">
								<div class="portal-navbar__menu-header">
									<p class="portal-navbar__menu-label">Signed in as</p>
									<p class="portal-navbar__menu-email">{{ user.email }}</p>
								</div>
								<a href="/desk/user-profile" class="portal-navbar__menu-link"> My Profile </a>
								<a href="/update-password" class="portal-navbar__menu-link"> Security Settings </a>
								<div class="portal-navbar__menu-separator"></div>
								<a
									href="/logout?redirect-to=%2F"
									class="portal-navbar__menu-link portal-navbar__menu-link--danger"
								>
									Logout
								</a>
							</div>
						</div>
					</transition>
				</div>
			</div>
		</div>
	</nav>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { RouterLink, useRoute } from 'vue-router';
import { FeatherIcon } from 'frappe-ui';
import { getGuardianPortalIdentity } from '@/lib/services/guardian/guardianPortalService';
import { getStudentPortalIdentity } from '@/lib/services/student/studentHomeService';

// Reactive state for user menu visibility
const isUserMenuOpen = ref(false);
const route = useRoute();
const studentIdentity = ref(null);
const guardianIdentity = ref(null);
const defaultPortal = computed(() => {
	const raw = window.defaultPortal || 'student';
	const normalized = String(raw || 'student')
		.trim()
		.toLowerCase();
	return ['staff', 'student', 'guardian'].includes(normalized) ? normalized : 'student';
});

const portalSection = computed(() => {
	const path = String(route.path || '')
		.trim()
		.toLowerCase();

	if (path.startsWith('/staff')) {
		return 'staff';
	}
	if (path.startsWith('/guardian')) {
		return 'guardian';
	}
	if (path.startsWith('/student')) {
		return 'student';
	}

	return defaultPortal.value;
});

let identityRequestId = 0;

watch(
	portalSection,
	async section => {
		const requestId = ++identityRequestId;
		studentIdentity.value = null;
		guardianIdentity.value = null;

		if (section === 'student') {
			try {
				const identity = await getStudentPortalIdentity();
				if (requestId === identityRequestId) {
					studentIdentity.value = identity;
				}
			} catch {
				if (requestId === identityRequestId) {
					studentIdentity.value = null;
				}
			}
			return;
		}

		if (section === 'guardian') {
			try {
				const identity = await getGuardianPortalIdentity();
				if (requestId === identityRequestId) {
					guardianIdentity.value = identity;
				}
			} catch {
				if (requestId === identityRequestId) {
					guardianIdentity.value = null;
				}
			}
		}
	},
	{ immediate: true }
);

// Get user info from Frappe's session object
function getSessionUserInfo() {
	const session = window?.frappe?.session || {};
	const userInfo = session.user_info || {};
	const email = String(userInfo.email || userInfo.name || session.user || '').trim();
	const fullname = String(
		userInfo.fullname || userInfo.full_name || userInfo.name || session.full_name || ''
	).trim();
	const userId = String(session.user || userInfo.name || '').trim();

	return {
		fullname,
		email,
		userId,
	};
}

const user = computed(() => {
	const userInfo = getSessionUserInfo();
	const resolvedFullName = (
		(portalSection.value === 'student' &&
			(studentIdentity.value?.full_name || studentIdentity.value?.display_name)) ||
		(portalSection.value === 'guardian' &&
			(guardianIdentity.value?.display_name || guardianIdentity.value?.full_name)) ||
		userInfo.fullname ||
		userInfo.email ||
		'Guest'
	).trim();
	const nameParts = resolvedFullName.split(' ').filter(Boolean);
	const initials =
		nameParts.length > 1
			? `${nameParts[0][0]}${nameParts[nameParts.length - 1][0]}`
			: resolvedFullName.substring(0, 2);

	return {
		fullname: resolvedFullName,
		email:
			(portalSection.value === 'student'
				? studentIdentity.value?.user
				: portalSection.value === 'guardian'
					? guardianIdentity.value?.email || guardianIdentity.value?.user
					: null) ||
			userInfo.userId ||
			userInfo.email ||
			'guest@example.com',
		initials: initials.toUpperCase(),
		avatarImage:
			portalSection.value === 'student'
				? studentIdentity.value?.image_url || null
				: portalSection.value === 'guardian'
					? guardianIdentity.value?.image_url || null
					: null,
	};
});

// Define emits for parent component communication
const emit = defineEmits(['toggle-sidebar']);
</script>
