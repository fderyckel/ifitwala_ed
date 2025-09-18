<!-- ifitwala_ed/ifitwala_ed/ui-spa/src/components/PortalFooter.vue -->
 
<template>
	<footer
		class="fixed bottom-0 left-0 right-0 z-50 bg-white/95 backdrop-blur border-t border-gray-200 print:hidden"
		role="contentinfo"
	>
		<div class="mx-auto max-w-7xl px-3 py-2">
			<div class="flex flex-col md:flex-row items-center justify-between gap-2">
				<nav aria-label="Footer links">
					<ul class="flex flex-wrap items-center justify-center md:justify-start text-xs sm:text-sm text-gray-600">
						<li v-for="(item, i) in footerItems" :key="item.name" class="flex items-center">
							<a
								:href="item.href"
								class="px-1 hover:text-blue-600 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/60 rounded-sm"
							>
								{{ item.name }}
							</a>
							<span v-if="i < footerItems.length - 1" class="mx-2 select-none text-gray-300" aria-hidden="true">•</span>
						</li>
					</ul>
				</nav>

				<p class="text-[11px] sm:text-xs text-gray-500">
					&copy; {{ currentYear }} Ifitwala Ed
				</p>
			</div>
		</div>
	</footer>
</template>

<script setup>
import { computed } from 'vue';

const currentYear = computed(() => new Date().getFullYear());

// Routes can be adjusted later if needed
const footerItems = [
	{ name: 'Privacy Policy', href: '/privacy' },
	{ name: 'School Website', href: '/' },
	{ name: 'Contact Us / Help', href: '/portal/help' }, // will open modal later
	{ name: 'Calendar', href: '/portal/calendar' },
	{ name: 'Student Handbook', href: '/portal/handbook' },
];
</script>
