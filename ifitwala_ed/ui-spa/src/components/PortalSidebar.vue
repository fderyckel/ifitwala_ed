<!-- ifitwala_ed/ui-spa/src/components/PortalSidebar.vue -->
<template>
	<div
		v-if="isMobileOpen"
		class="portal-sidebar__backdrop fixed inset-0 z-30 lg:hidden"
		aria-hidden="true"
		@click="emit('close-mobile')"
	/>

	<aside
		:class="[
			'portal-sidebar fixed inset-y-0 left-0 z-40 transform transition-transform duration-300 ease-in-out lg:static lg:inset-auto lg:translate-x-0',
			isMobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0',
			isRailExpanded ? 'portal-sidebar--expanded' : 'portal-sidebar--collapsed',
		]"
		aria-label="Portal navigation"
	>
		<div class="flex h-full flex-col">
			<div class="portal-sidebar__content">
				<div>
					<h3 class="portal-sidebar__section type-label">Menu</h3>
					<nav class="mt-2 space-y-1" aria-label="Menu">
						<RouterLink
							v-for="item in menuItems"
							:key="item.label"
							:to="item.to"
							class="portal-sidebar__item group"
							active-class="portal-sidebar__item--active"
							:aria-label="item.label"
							@click="handleNavActivate"
						>
							<FeatherIcon :name="item.icon" class="portal-sidebar__icon" />
							<span class="portal-sidebar__label type-body-strong" aria-hidden="true">{{ item.label }}</span>
							<span class="sr-only">{{ item.label }}</span>
							<span class="portal-sidebar__tooltip type-caption" aria-hidden="true">{{ item.label }}</span>
						</RouterLink>
					</nav>
				</div>

				<div v-if="switchItems.length">
					<h3 class="portal-sidebar__section type-label">Switch Portal</h3>
					<nav class="mt-2 space-y-1" aria-label="Switch portal">
						<RouterLink
							v-for="item in switchItems"
							:key="item.label"
							:to="item.to"
							class="portal-sidebar__item group"
							:aria-label="item.label"
							@click="handleNavActivate"
						>
							<FeatherIcon :name="item.icon" class="portal-sidebar__icon" />
							<span class="portal-sidebar__label type-body-strong" aria-hidden="true">{{ item.label }}</span>
							<span class="sr-only">{{ item.label }}</span>
							<span class="portal-sidebar__tooltip type-caption" aria-hidden="true">{{ item.label }}</span>
						</RouterLink>
					</nav>
				</div>

				<div>
					<h3 class="portal-sidebar__section type-label">Account</h3>
					<nav class="mt-2 space-y-1" aria-label="Account">
						<a
							v-for="item in accountItems"
							:key="item.label"
							:href="item.href"
							class="portal-sidebar__item group"
							:aria-label="item.label"
							@click="handleNavActivate"
						>
							<FeatherIcon :name="item.icon" class="portal-sidebar__icon" />
							<span class="portal-sidebar__label type-body-strong" aria-hidden="true">{{ item.label }}</span>
							<span class="sr-only">{{ item.label }}</span>
							<span class="portal-sidebar__tooltip type-caption" aria-hidden="true">{{ item.label }}</span>
						</a>
					</nav>
				</div>
			</div>

			<div class="portal-sidebar__footer">
				<p class="portal-sidebar__meta type-caption">
					<FeatherIcon name="shield" class="h-4 w-4 shrink-0" />
					<span class="portal-sidebar__label" aria-hidden="true">{{ sidebarLabel }}</span>
					<span class="sr-only">{{ sidebarLabel }}</span>
				</p>

				<button
					type="button"
					class="portal-sidebar__toggle type-button-label"
					:aria-expanded="isRailExpanded ? 'true' : 'false'"
					:aria-label="isRailExpanded ? 'Collapse navigation' : 'Expand navigation'"
					@click="emit('toggle-rail')"
				>
					<FeatherIcon name="chevron-right" class="h-4 w-4 transition-transform" :class="{ 'rotate-180': isRailExpanded }" />
					<span class="portal-sidebar__label" aria-hidden="true">{{ isRailExpanded ? 'Collapse' : 'Expand' }}</span>
					<span class="sr-only">{{ isRailExpanded ? 'Collapse navigation' : 'Expand navigation' }}</span>
				</button>
			</div>
		</div>
	</aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { RouteLocationRaw } from 'vue-router'
import { RouterLink } from 'vue-router'
import { FeatherIcon } from 'frappe-ui'

type PortalSection = 'student' | 'guardian'

type MenuItem = {
	label: string
	icon: string
	to: RouteLocationRaw
}

const props = defineProps<{
	isMobileOpen: boolean
	isRailExpanded: boolean
	activeSection: PortalSection
}>()

const emit = defineEmits<{
	(e: 'close-mobile'): void
	(e: 'toggle-rail'): void
}>()

function handleNavActivate() {
	emit('close-mobile')
}

const portalRoles = computed<string[]>(() => {
	const raw = (window as unknown as { portalRoles?: string[] }).portalRoles
	return Array.isArray(raw) ? raw : []
})

const hasStudentPortal = computed(() => portalRoles.value.includes('Student'))
const hasGuardianPortal = computed(() => portalRoles.value.includes('Guardian'))

const studentMenu: MenuItem[] = [
	{ label: 'Dashboard', icon: 'home', to: { name: 'student-home' } },
	{ label: 'Activities', icon: 'star', to: { name: 'student-activities' } },
	{ label: 'Portfolio & Journal', icon: 'layers', to: { name: 'student-portfolio' } },
	{ label: 'Courses', icon: 'book-open', to: { name: 'student-courses' } },
	{ label: 'Student Log', icon: 'file-text', to: { name: 'student-logs' } },
	{ label: 'Profile', icon: 'user', to: { name: 'student-profile' } },
]

const guardianMenu: MenuItem[] = [
	{ label: 'Family Snapshot', icon: 'home', to: { name: 'guardian-home' } },
	{ label: 'Activities', icon: 'star', to: { name: 'guardian-activities' } },
	{ label: 'Showcase Portfolio', icon: 'layers', to: { name: 'guardian-portfolio' } },
]

const menuItems = computed<MenuItem[]>(() => {
	if (props.activeSection === 'guardian' && hasGuardianPortal.value) {
		return guardianMenu
	}
	if (props.activeSection === 'student' && hasStudentPortal.value) {
		return studentMenu
	}
	if (hasStudentPortal.value) return studentMenu
	if (hasGuardianPortal.value) return guardianMenu
	return []
})

const switchItems = computed<MenuItem[]>(() => {
	const items: MenuItem[] = []
	if (props.activeSection !== 'student' && hasStudentPortal.value) {
		items.push({ label: 'Go to Student Portal', icon: 'book-open', to: { name: 'student-home' } })
	}
	if (props.activeSection !== 'guardian' && hasGuardianPortal.value) {
		items.push({ label: 'Go to Guardian Portal', icon: 'users', to: { name: 'guardian-home' } })
	}
	return items
})

const sidebarLabel = computed(() => {
	if (props.activeSection === 'guardian') return 'Guardian Portal'
	return 'Student Portal'
})

const accountItems = [
	{ label: 'Profile', icon: 'user', href: '/app/user-profile' },
	{ label: 'Logout', icon: 'log-out', href: '/?cmd=web_logout' },
]
</script>
