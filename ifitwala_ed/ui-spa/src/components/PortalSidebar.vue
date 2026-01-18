<template>
<!--
  PortalSidebar.vue
  Responsive sidebar navigation for the Student/Parent portal.
  Handles mobile drawer states and routing to portal sections.

  Used by:
  - PortalLayout.vue (layouts)
-->
  <div
    v-if="isOpen"
    @click="$emit('close')"
    class="fixed inset-0 bg-black bg-opacity-30 z-30 lg:hidden"
    aria-hidden="true"
  ></div>

  <aside
    :class="[
      'fixed inset-y-0 left-0 z-40 w-64 bg-white border-r border-gray-200 transform transition-transform duration-300 ease-in-out',
      isOpen ? 'translate-x-0' : '-translate-x-full',
      'lg:translate-x-0 lg:static lg:inset-auto',
    ]"
  >
    <div class="flex flex-col h-full">
      <div class="flex-1 p-4 space-y-4">
        <div>
          <h3 class="px-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Menu</h3>
          <nav class="mt-2 space-y-1">
            <RouterLink
              v-for="item in menuItems"
              :key="item.label"
              :to="item.to"
              class="flex items-center px-3 py-2 text-sm font-medium rounded-md text-gray-600 hover:bg-gray-100 hover:text-gray-900 group"
              active-class="bg-blue-50 text-blue-700 font-semibold"
            >
              <FeatherIcon :name="item.icon" class="h-5 w-5 mr-3 text-gray-400 group-hover:text-gray-600" />
              <span>{{ item.label }}</span>
            </RouterLink>
          </nav>
        </div>

        <div>
          <h3 class="px-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Account</h3>
          <nav class="mt-2 space-y-1">
            <a
              v-for="item in accountItems"
              :key="item.label"
              :href="item.href"
              class="flex items-center px-3 py-2 text-sm font-medium rounded-md text-gray-600 hover:bg-gray-100 hover:text-gray-900 group"
            >
              <FeatherIcon :name="item.icon" class="h-5 w-5 mr-3 text-gray-400 group-hover:text-gray-600" />
              <span>{{ item.label }}</span>
            </a>
          </nav>
        </div>
      </div>

      <div class="p-4 border-t border-gray-200">
        <p class="text-xs text-gray-500 flex items-center">
          <FeatherIcon name="shield" class="h-4 w-4 mr-2" />
          <span>Student & Parent Portal</span>
        </p>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { FeatherIcon } from 'frappe-ui';
import { RouterLink } from 'vue-router';

// Props to control visibility from the parent component
defineProps({
  isOpen: {
    type: Boolean,
    required: true,
  },
});

// Emits for parent component communication
defineEmits(['close']);

const menuItems = [
	{ label: 'Dashboard', icon: 'home', to: '/student' }, 
  { label: 'Courses', icon: 'book', to: '/student/courses' }, 
  { label: 'Assignments', icon: 'check-square', to: '/student/assignments' },
  { label: 'Grades', icon: 'bar-chart-2', to: '/student/grades' },
  { label: 'Attendance', icon: 'calendar', to: '/student/attendance' },
  { label: 'Messages', icon: 'message-square', to: '/student/messages' },
];

const accountItems = [
  { label: 'Profile', icon: 'user', href: '/app/user-profile' },
  { label: 'Logout', icon: 'log-out', href: '/?cmd=web_logout' },
];
</script>
