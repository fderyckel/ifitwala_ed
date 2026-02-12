<template>
<!--
  PortalNavbar.vue
  Main top navigation bar for the Staff/Student portal layout. Handles user profile and mobile menu toggle.

  Used by:
  - PortalLayout.vue (layouts)
-->
  <nav class="bg-white border-b border-gray-200 shadow-sm sticky top-0 z-30">
    <div class="container mx-auto px-4">
      <div class="flex items-center justify-between h-16">
        <div class="flex items-center space-x-4">
          <button
            @click="$emit('toggle-sidebar')"
            class="p-2 rounded-md text-gray-600 hover:bg-gray-100 hover:text-gray-800 lg:hidden"
            aria-label="Toggle sidebar"
          >
            <FeatherIcon name="menu" class="h-6 w-6" />
          </button>

          <a href="/portal" class="flex items-center space-x-2 text-gray-800">
            <FeatherIcon name="book-open" class="h-6 w-6 text-blue-600" />
            <span class="font-semibold text-xl">Ifitwala</span>
          </a>
        </div>

        <div class="flex items-center">
          <div class="relative">
            <button
              @click="isUserMenuOpen = !isUserMenuOpen"
              class="flex items-center space-x-2 p-2 rounded-full hover:bg-gray-100 focus:outline-none"
            >
              <span class="text-sm font-medium text-gray-700 hidden sm:block">{{ user.fullname }}</span>
              <img
                v-if="user.avatarImage"
                :src="user.avatarImage"
                :alt="`${user.fullname} avatar`"
                class="h-8 w-8 rounded-full object-cover border border-gray-200"
              />
              <div v-else class="h-8 w-8 rounded-full bg-blue-500 flex items-center justify-center text-white font-bold">
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
              <div
                v-if="isUserMenuOpen"
                class="absolute right-0 mt-2 w-56 origin-top-right bg-white rounded-md shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none"
              >
                <div class="py-1">
                  <div class="px-4 py-2 border-b">
                    <p class="text-sm text-gray-700">Signed in as</p>
                    <p class="text-sm font-medium text-gray-900 truncate">{{ user.email }}</p>
                  </div>
                  <a href="/app/user-profile" class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">
                    My Profile
                  </a>
                  <a href="/update-password" class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">
                    Security Settings
                  </a>
                  <div class="border-t border-gray-100"></div>
                  <a href="/?cmd=web_logout" class="block px-4 py-2 text-sm text-red-600 hover:bg-red-50">
                    Logout
                  </a>
                </div>
              </div>
            </transition>
          </div>
        </div>
      </div>
    </div>
  </nav>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { useRoute } from 'vue-router';
import { FeatherIcon } from 'frappe-ui';
import { getStudentPortalIdentity } from '@/lib/services/student/studentHomeService';

// Reactive state for user menu visibility
const isUserMenuOpen = ref(false);
const route = useRoute();
const studentIdentity = ref(null);

const isStudentPortal = computed(() => String(route.path || '').startsWith('/student'));

watch(
  isStudentPortal,
  async (active) => {
    if (!active) {
      studentIdentity.value = null;
      return;
    }

    try {
      studentIdentity.value = await getStudentPortalIdentity();
    } catch {
      studentIdentity.value = null;
    }
  },
  { immediate: true }
);

// Get user info from Frappe's session object
const user = computed(() => {
  const userInfo = window.frappe?.session?.user_info || { fullname: 'Guest', email: 'guest@example.com' };
  const resolvedFullName = (
    (isStudentPortal.value && studentIdentity.value?.display_name) ||
    userInfo.fullname ||
    'Guest'
  ).trim();
  const nameParts = resolvedFullName.split(' ').filter(Boolean);
  const initials = nameParts.length > 1
    ? `${nameParts[0][0]}${nameParts[nameParts.length - 1][0]}`
    : resolvedFullName.substring(0, 2);
  
  return {
    fullname: resolvedFullName,
    email: userInfo.email,
    initials: initials.toUpperCase(),
    avatarImage: isStudentPortal.value ? (studentIdentity.value?.image_url || null) : null,
  };
});

// Define emits for parent component communication
const emit = defineEmits(['toggle-sidebar']);
</script>
