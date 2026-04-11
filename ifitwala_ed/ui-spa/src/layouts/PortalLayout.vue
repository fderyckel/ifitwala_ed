<!-- ifitwala_ed/ui-spa/src/layouts/PortalLayout.vue -->
<template>
	<!-- Student/Guardian surface (Portal) -->
	<div
		class="ifitwala-theme portal-layout text-ink"
		:class="
			isDesktopRailExpanded ? 'portal-layout--rail-expanded' : 'portal-layout--rail-collapsed'
		"
	>
		<PortalNavbar @toggle-sidebar="toggleSidebar" />

		<div class="portal-layout__body">
			<PortalSidebar
				:is-mobile-open="isMobileSidebarOpen"
				:is-rail-expanded="isDesktopRailExpanded"
				:active-section="activeSection"
				@close-mobile="isMobileSidebarOpen = false"
				@toggle-rail="toggleRail"
			/>

			<div class="portal-layout__workspace">
				<div class="portal-layout__frame xl:items-start">
					<main class="portal-shell">
						<slot />
					</main>

					<StudentContextSidebar v-if="showStudentContextSidebar" />
				</div>

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
import StudentContextSidebar from '@/components/StudentContextSidebar.vue';
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

const showStudentContextSidebar = computed(() => {
	if (activeSection.value !== 'student') return false;
	const routeName = String(route.name || '').trim();
	if (!routeName.startsWith('student-')) return false;
	if (routeName === 'student-course-detail' || routeName === 'student-quiz') return false;
	return true;
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
