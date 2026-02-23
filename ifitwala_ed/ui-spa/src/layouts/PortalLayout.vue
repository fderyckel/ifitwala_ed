<!-- ifitwala_ed/ui-spa/src/layouts/PortalLayout.vue -->
<template>
	<!-- Student/Guardian surface (Portal) -->
	<div
		class="min-h-screen flex flex-col text-ink bg-gradient-to-b from-sky/95 via-sand/95 to-white bg-[radial-gradient(circle_at_0_0,rgb(var(--jacaranda-rgb)/0.18),transparent_55%)] sm:bg-[radial-gradient(circle_at_0_0,rgb(var(--jacaranda-rgb)/0.18),transparent_55%),radial-gradient(circle_at_100%_0,rgb(var(--leaf-rgb)/0.14),transparent_55%),linear-gradient(to_bottom,rgb(var(--sky-rgb)/0.98),rgb(var(--sand-rgb)/0.98))]"
	>
		<PortalNavbar @toggle-sidebar="toggleSidebar" />

		<div class="flex flex-1">
			<PortalSidebar
				:is-mobile-open="isMobileSidebarOpen"
				:is-rail-expanded="isDesktopRailExpanded"
				:active-section="activeSection"
				@close-mobile="isMobileSidebarOpen = false"
				@toggle-rail="toggleRail"
			/>

			<div class="flex min-w-0 flex-1 flex-col">
				<main
					class="flex-1 px-4 py-4 sm:px-6 sm:py-6 lg:px-8 lg:py-8 pb-[var(--footer-h)] bg-surface-soft/75 backdrop-blur-sm shadow-strong sm:m-4 sm:rounded-3xl sm:border sm:border-sand"
				>
					<slot />
				</main>

				<PortalFooter />
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import PortalNavbar from '@/components/PortalNavbar.vue';
import PortalSidebar from '@/components/PortalSidebar.vue';
import PortalFooter from '@/components/PortalFooter.vue';

type PortalSection = 'student' | 'guardian';

const STORAGE_KEYS: Record<PortalSection, string> = {
	student: 'ifw.portal.rail.expanded.student.v1',
	guardian: 'ifw.portal.rail.expanded.guardian.v1',
};

const route = useRoute();
const isMobileSidebarOpen = ref(false);
const isDesktopRailExpanded = ref(false);

const activeSection = computed<PortalSection>(() => {
	if (String(route.path || '').startsWith('/guardian')) return 'guardian';
	return 'student';
});

function readRailPreference(section: PortalSection) {
	if (typeof window === 'undefined') return false;
	try {
		return window.localStorage.getItem(STORAGE_KEYS[section]) === '1';
	} catch {
		return false;
	}
}

function writeRailPreference(section: PortalSection, expanded: boolean) {
	if (typeof window === 'undefined') return;
	try {
		window.localStorage.setItem(STORAGE_KEYS[section], expanded ? '1' : '0');
	} catch {
		// Best effort only; layout still functions without persistence.
	}
}

watch(
	activeSection,
	section => {
		isDesktopRailExpanded.value = readRailPreference(section);
		isMobileSidebarOpen.value = false;
	},
	{ immediate: true }
);

watch(isDesktopRailExpanded, expanded => {
	writeRailPreference(activeSection.value, expanded);
});

watch(
	() => route.fullPath,
	() => {
		isMobileSidebarOpen.value = false;
	}
);

function toggleSidebar() {
	isMobileSidebarOpen.value = !isMobileSidebarOpen.value;
}

function toggleRail() {
	isDesktopRailExpanded.value = !isDesktopRailExpanded.value;
}
</script>
