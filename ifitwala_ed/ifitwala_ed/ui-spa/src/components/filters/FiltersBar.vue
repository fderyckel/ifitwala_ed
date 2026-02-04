<!-- ifitwala_ed/ui-spa/src/components/filters/FiltersBar.vue -->
<!--
  FiltersBar.vue
  A layout container for filter controls (dropdowns, date pickers) in analytics or list pages.

  Used by:
  - EnrollmentAnalytics.vue
  - StudentLogAnalytics.vue
  - RoomUtilization.vue
-->
<template>
  <section
    class="ifit-filters mt-4 flex flex-wrap items-end gap-3 rounded-xl border border-slate-200 bg-white/80 px-3 py-3 shadow-sm"
  >
    <slot />
  </section>
</template>

<script setup lang="ts">
// No logic yet - just a shared layout shell for filters.
</script>
