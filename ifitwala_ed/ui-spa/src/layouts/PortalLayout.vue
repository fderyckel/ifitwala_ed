<template>
  <div class="min-h-screen flex flex-col bg-gray-50">
    <PortalNavbar @toggle-sidebar="toggleSidebar" />

    <div class="flex flex-1">
      <PortalSidebar :is-open="isSidebarOpen" @close="isSidebarOpen = false" />

      <div class="flex-1 flex flex-col">
        <main class="flex-1 p-4 sm:p-6 lg:p-8">
          <slot />
        </main>

        <PortalFooter />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import PortalNavbar from '../components/PortalNavbar.vue';
import PortalSidebar from '../components/PortalSidebar.vue';
import PortalFooter from '../components/PortalFooter.vue';

// Reactive state to control the sidebar's visibility on mobile
const isSidebarOpen = ref(false);

// Function to toggle the sidebar state
const toggleSidebar = () => {
  isSidebarOpen.value = !isSidebarOpen.value;
};
</script>