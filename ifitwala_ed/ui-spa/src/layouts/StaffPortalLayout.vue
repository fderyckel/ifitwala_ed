<!-- ifitwala_ed/ui-spa/src/layouts/StaffPortalLayout.vue -->

<template>
  <div
    class="staff-layout flex flex-col font-sans antialiased min-h-screen text-ink"
    style="background: linear-gradient(180deg, var(--sky) 0%, #F1F6F8 40%, var(--sand) 100%);"
  >
    <header class="staff-layout__header">
      <div class="staff-layout__header-inner">
        <h1 class="staff-layout__brand">
          <RouterLink :to="{ name: 'staff-home' }" class="staff-layout__brand-link">
            Staff Portal
          </RouterLink>
        </h1>

        <a href="/app" class="staff-layout__desk-switch">
          <svg class="staff-layout__desk-switch-icon" viewBox="0 0 24 24" aria-hidden="true">
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
      </div>
    </header>

    <main class="staff-layout__main">
      <slot />
    </main>

    <footer class="staff-layout__footer">
      <div class="staff-layout__footer-inner">
        © {{ year }} Staff Portal
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { RouterLink } from 'vue-router';
import { FeatherIcon } from 'frappe-ui';

const year = computed(() => new Date().getFullYear());
</script>
