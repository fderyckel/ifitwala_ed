<template>
  <footer class="bg-white border-t border-gray-200">
    <div class="container mx-auto px-6 py-8">
      <div class="grid grid-cols-2 md:grid-cols-4 gap-8">
        <div v-for="section in footerLinks" :key="section.title" class="space-y-4">
          <h3 class="text-sm font-semibold text-gray-800 tracking-wider uppercase">
            {{ section.title }}
          </h3>
          <ul class="space-y-2">
            <li v-for="link in section.links" :key="link.name">
              <a :href="link.href" class="text-sm text-gray-600 hover:text-blue-600 hover:underline">
                {{ link.name }}
              </a>
            </li>
          </ul>
        </div>
      </div>

      <div class="mt-8 pt-8 border-t border-gray-200 flex flex-col md:flex-row items-center justify-between">
        <p class="text-sm text-gray-500">
          &copy; {{ currentYear }} Ifitwala Ed. All rights reserved.
        </p>
        <div class="flex items-center space-x-4 mt-4 md:mt-0">
          </div>
      </div>
    </div>
  </footer>
</template>

<script setup>
import { computed } from 'vue';
// Uncomment if you decide to add social icons
// import { FeatherIcon } from 'frappe-ui';

const currentYear = computed(() => new Date().getFullYear());

const footerLinks = [
  {
    title: 'Academics',
    links: [
      { name: 'My Courses', href: '/portal/courses' },
      { name: 'Assignments', href: '/portal/assignments' },
      { name: 'Grades', href: '/portal/grades' },
      { name: 'Calendar', href: '/portal/attendance' },
    ],
  },
  {
    title: 'Support',
    links: [
      { name: 'Help Center', href: '/help' },
      { name: 'Contact Us', href: '/contact' },
      { name: 'Technical Support', href: '#' },
      { name: 'FAQs', href: '/faq' },
    ],
  },
  {
    title: 'Resources',
    links: [
      { name: 'School Website', href: '/' },
      { name: 'Library', href: '#' },
      { name: 'Wellbeing', href: '/portal/wellbeing' },
      { name: 'Student Handbook', href: '#' },
    ],
  },
  {
    title: 'Legal',
    links: [
      { name: 'Privacy Policy', href: '/privacy' },
      { name: 'Terms of Service', href: '/terms' },
      { name: 'Acceptable Use', href: '#' },
    ],
  },
];
</script>