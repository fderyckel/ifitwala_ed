<!-- ifitwala_ed/ui-spa/src/layouts/StaffPortalLayout.vue -->

<template>
  <!-- Single, canonical theme wrapper -->
  <div class="ifitwala-theme">
    <header class="staff-layout__header">
      <div class="staff-layout__header-inner">
        <h1 class="staff-layout__brand">
          <RouterLink :to="{ name: 'staff-home' }" class="staff-layout__brand-link">
            Staff Portal
          </RouterLink>
        </h1>

        <div class="flex items-center gap-3">
          <a href="/app" class="staff-layout__desk-switch">
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

          <a href="/?cmd=web_logout" class="staff-layout__desk-switch" title="Logout">
            <FeatherIcon name="log-out" class="h-4 w-4" />
          </a>
        </div>
      </div>
    </header>

    <main class="staff-layout__main">
      <!-- staff-shell handles width + padding; StaffHome already uses it -->
      <slot />
      <PortalNotification />
    </main>

    <!-- ✅ Overlay infra lives INSIDE the staff surface -->
    <div id="overlay-root"></div>
    <OverlayHost />
  </div>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { FeatherIcon } from 'frappe-ui'
import PortalNotification from '../components/PortalNotification.vue'
import OverlayHost from '../components/overlay/OverlayHost.vue'
</script>
