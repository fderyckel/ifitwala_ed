<template>
  <div class="space-y-8">
    <header class="border-b border-gray-200 pb-4">
      <h1 class="text-3xl font-bold text-gray-800">Welcome back, {{ user.fullname }}!</h1>
      <p class="mt-1 text-md text-gray-600">Here's a quick overview of your day.</p>
    </header>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
      <div class="lg:col-span-2 space-y-8">
        <section aria-labelledby="courses-heading">
          <div class="flex items-center justify-between mb-4">
            <h2 id="courses-heading" class="text-xl font-semibold text-gray-700">My Courses</h2>
            <RouterLink to="/portal/courses" class="text-sm font-medium text-blue-600 hover:underline">
              View All
            </RouterLink>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div v-for="course in courses" :key="course.title" class="bg-white border border-gray-200 rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow">
              <div class="flex items-start justify-between">
                <div>
                  <h3 class="font-semibold text-gray-800">{{ course.title }}</h3>
                  <p class="text-sm text-gray-500">{{ course.instructor }}</p>
                </div>
                <FeatherIcon :name="course.icon" class="w-6 h-6 text-gray-400" />
              </div>
            </div>
          </div>
        </section>

        <section class="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div class="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
            <h2 class="font-semibold text-gray-700 mb-2">My Tasks</h2>
            <div class="h-64 bg-gray-50 rounded-md flex flex-col items-center justify-center text-center text-gray-500">
              <FeatherIcon name="calendar" class="w-10 h-10 mb-2 text-gray-400" />
              <span class="text-sm">Task calendar coming soon</span>
            </div>
          </div>
          <div class="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
            <h2 class="font-semibold text-gray-700 mb-2">My Schedule</h2>
            <div class="h-64 bg-gray-50 rounded-md flex flex-col items-center justify-center text-center text-gray-500">
              <FeatherIcon name="clock" class="w-10 h-10 mb-2 text-gray-400" />
              <span class="text-sm">Schedule coming soon</span>
            </div>
          </div>
        </section>
      </div>

      <div class="lg:col-span-1 space-y-6">
        <section aria-labelledby="more-heading">
          <h2 id="more-heading" class="text-xl font-semibold text-gray-700 mb-4">Quick Links</h2>
          <div class="space-y-4">
            <RouterLink v-for="item in moreLinks" :key="item.title" :to="item.to" class="group flex items-center bg-white p-4 border border-gray-200 rounded-lg shadow-sm hover:border-blue-500 hover:shadow-lg transition-all">
              <div class="mr-4 bg-blue-50 text-blue-600 rounded-lg p-2">
                <FeatherIcon :name="item.icon" class="w-6 h-6" />
              </div>
              <div>
                <h3 class="font-semibold text-gray-800">{{ item.title }}</h3>
                <p class="text-sm text-gray-500">{{ item.description }}</p>
              </div>
              <FeatherIcon name="chevron-right" class="w-5 h-5 text-gray-400 ml-auto group-hover:text-blue-600" />
            </RouterLink>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { RouterLink } from 'vue-router';
import { FeatherIcon } from 'frappe-ui';

// Get user info from Frappe's session object for the welcome message
const user = computed(() => {
  return window.frappe?.session?.user_info || { fullname: 'Student' };
});

// Placeholder data for "My Courses"
const courses = [
  { title: 'Introduction to Physics', instructor: 'Dr. Evelyn Reed', icon: 'cpu' },
  { title: 'History of Ancient Civilizations', instructor: 'Prof. Marcus Chen', icon: 'book-open' },
  { title: 'Calculus I', instructor: 'Dr. Alan Grant', icon: 'percent' },
  { title: 'Creative Writing Workshop', instructor: 'Ms. Alice Martin', icon: 'edit-3' },
];

// Data for the "More" section cards
const moreLinks = [
  { 
    title: 'Student Log',
    description: 'View socio-emotional notes.',
    icon: 'file-text',
    to: '/portal/student/logs' 
  },
  { 
    title: 'Wellbeing',
    description: 'Access resources and check-ins.',
    icon: 'heart',
    to: '/portal/wellbeing'
  },
  { 
    title: 'Demographics',
    description: 'Manage your profile and details.',
    icon: 'user',
    to: '/portal/student/profile'
  },
];
</script>