<!-- ifitwala_ed/ui-spa/src/components/PortalSidebar.vue -->
<template>
	<div
		v-if="isOpen"
		class="fixed inset-0 z-30 bg-black bg-opacity-30 lg:hidden"
		aria-hidden="true"
		@click="$emit('close')"
	/>

	<aside
		:class="[
			'fixed inset-y-0 left-0 z-40 w-64 transform border-r border-gray-200 bg-white transition-transform duration-300 ease-in-out',
			isOpen ? 'translate-x-0' : '-translate-x-full',
			'lg:static lg:inset-auto lg:translate-x-0',
		]"
	>
		<div class="flex h-full flex-col">
			<div class="flex-1 space-y-4 p-4">
				<div>
					<h3 class="px-3 text-xs font-semibold uppercase tracking-wider text-gray-500">Menu</h3>
					<nav class="mt-2 space-y-1">
						<RouterLink
							v-for="item in menuItems"
							:key="item.label"
							:to="item.to"
							class="group flex items-center rounded-md px-3 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 hover:text-gray-900"
							active-class="bg-blue-50 font-semibold text-blue-700"
							@click="$emit('close')"
						>
							<FeatherIcon :name="item.icon" class="mr-3 h-5 w-5 text-gray-400 group-hover:text-gray-600" />
							<span>{{ item.label }}</span>
						</RouterLink>
					</nav>
				</div>

				<div v-if="switchItems.length">
					<h3 class="px-3 text-xs font-semibold uppercase tracking-wider text-gray-500">Switch Portal</h3>
					<nav class="mt-2 space-y-1">
						<RouterLink
							v-for="item in switchItems"
							:key="item.label"
							:to="item.to"
							class="group flex items-center rounded-md px-3 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 hover:text-gray-900"
							@click="$emit('close')"
						>
							<FeatherIcon :name="item.icon" class="mr-3 h-5 w-5 text-gray-400 group-hover:text-gray-600" />
							<span>{{ item.label }}</span>
						</RouterLink>
					</nav>
				</div>

				<div>
					<h3 class="px-3 text-xs font-semibold uppercase tracking-wider text-gray-500">Account</h3>
					<nav class="mt-2 space-y-1">
						<a
							v-for="item in accountItems"
							:key="item.label"
							:href="item.href"
							class="group flex items-center rounded-md px-3 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 hover:text-gray-900"
						>
							<FeatherIcon :name="item.icon" class="mr-3 h-5 w-5 text-gray-400 group-hover:text-gray-600" />
							<span>{{ item.label }}</span>
						</a>
					</nav>
				</div>
			</div>

			<div class="border-t border-gray-200 p-4">
				<p class="flex items-center text-xs text-gray-500">
					<FeatherIcon name="shield" class="mr-2 h-4 w-4" />
					<span>{{ sidebarLabel }}</span>
				</p>
			</div>
		</div>
	</aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import type { RouteLocationRaw } from 'vue-router'
import { FeatherIcon } from 'frappe-ui'

defineProps<{
	isOpen: boolean
}>()

defineEmits<{
	(e: 'close'): void
}>()

type MenuItem = {
	label: string
	icon: string
	to: RouteLocationRaw
}

const route = useRoute()
const portalRoles = computed<string[]>(() => {
	const raw = (window as unknown as { portalRoles?: string[] }).portalRoles
	return Array.isArray(raw) ? raw : []
})

const activeSection = computed<'student' | 'guardian'>(() => {
	if (String(route.path || '').startsWith('/guardian')) return 'guardian'
	return 'student'
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
	if (activeSection.value === 'guardian' && hasGuardianPortal.value) {
		return guardianMenu
	}
	if (activeSection.value === 'student' && hasStudentPortal.value) {
		return studentMenu
	}
	if (hasStudentPortal.value) return studentMenu
	if (hasGuardianPortal.value) return guardianMenu
	return []
})

const switchItems = computed<MenuItem[]>(() => {
	const items: MenuItem[] = []
	if (activeSection.value !== 'student' && hasStudentPortal.value) {
		items.push({ label: 'Go to Student Portal', icon: 'book-open', to: { name: 'student-home' } })
	}
	if (activeSection.value !== 'guardian' && hasGuardianPortal.value) {
		items.push({ label: 'Go to Guardian Portal', icon: 'users', to: { name: 'guardian-home' } })
	}
	return items
})

const sidebarLabel = computed(() => {
	if (activeSection.value === 'guardian') return 'Guardian Portal'
	return 'Student Portal'
})

const accountItems = [
	{ label: 'Profile', icon: 'user', href: '/app/user-profile' },
	{ label: 'Logout', icon: 'log-out', href: '/?cmd=web_logout' },
]
</script>
