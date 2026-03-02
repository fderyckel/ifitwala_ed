<!-- ifitwala_ed/ui-spa/src/layouts/StaffPortalLayout.vue -->
<template>
	<!-- Staff surface -->
	<div class="ifitwala-theme">
		<header class="staff-layout__header">
			<div class="staff-layout__header-inner">
				<h1 class="staff-layout__brand type-overline">
					<RouterLink :to="{ name: 'staff-home' }" class="staff-layout__brand-link">
						Staff Portal
					</RouterLink>
				</h1>

				<div class="flex items-center gap-3">
					<!-- Leaving SPA intentionally -->
					<a href="/desk" class="staff-layout__desk-switch type-button-label">
						<svg class="h-4 w-4" viewBox="0 0 24 24" aria-hidden="true">
							<path
								d="M4 4h16v10H4zm4 14h8m-4-4v4"
								fill="none"
								stroke="currentColor"
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="1.7"
							/>
						</svg>
						<span>Switch to Desk</span>
					</a>

					<!-- Leaving SPA intentionally -->
					<a
						href="/logout?redirect-to=%2F"
						class="staff-layout__desk-switch type-button-label"
						title="Logout"
					>
						<FeatherIcon name="log-out" class="h-4 w-4" />
					</a>
				</div>
			</div>
		</header>

		<main class="staff-layout__main">
			<slot />
			<PortalNotification />
		</main>
	</div>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router';
import { FeatherIcon } from 'frappe-ui';
import PortalNotification from '@/components/PortalNotification.vue';
</script>
