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
			'portal-sidebar fixed left-0 z-40 lg:z-20',
			isMobileOpen ? 'portal-sidebar--mobile-open' : 'portal-sidebar--mobile-closed',
			isRailExpanded ? 'portal-sidebar--expanded' : 'portal-sidebar--collapsed',
		]"
		:aria-label="__('Portal navigation')"
	>
		<div class="flex h-full flex-col">
			<div class="portal-sidebar__brand">
				<RouterLink
					:to="homeLink"
					class="portal-sidebar__item"
					:aria-label="homeLabel"
					@click="handleNavActivate"
				>
					<FeatherIcon name="book-open" class="portal-sidebar__icon" />
					<span class="portal-sidebar__label type-body-strong" aria-hidden="true">{{
						homeLabel
					}}</span>
					<span class="sr-only">{{ homeLabel }}</span>
				</RouterLink>
			</div>

			<div class="portal-sidebar__content">
				<div>
					<h3 class="portal-sidebar__section type-label">{{ __('Menu') }}</h3>
					<nav class="mt-2 space-y-1" :aria-label="__('Menu')">
						<RouterLink
							v-for="item in menuItems"
							:key="item.label"
							:to="item.to"
							class="portal-sidebar__item group"
							active-class="portal-sidebar__item--active"
							:aria-label="itemAriaLabel(item)"
							@click="handleNavActivate"
						>
							<FeatherIcon :name="item.icon" class="portal-sidebar__icon" />
							<span class="portal-sidebar__label type-body-strong" aria-hidden="true">{{
								item.label
							}}</span>
							<span class="sr-only">{{ item.label }}</span>
							<span
								v-if="badgeCount(item)"
								class="portal-sidebar__badge type-caption"
								aria-hidden="true"
							>
								{{ badgeLabel(badgeCount(item)) }}
							</span>
							<span v-if="badgeCount(item)" class="sr-only">
								{{ __('{0} unread communications', [badgeCount(item)]) }}
							</span>
							<span class="portal-sidebar__tooltip type-caption" aria-hidden="true">{{
								item.label
							}}</span>
						</RouterLink>
					</nav>
				</div>

				<div v-if="switchItems.length">
					<h3 class="portal-sidebar__section type-label">{{ __('Switch Portal') }}</h3>
					<nav class="mt-2 space-y-1" :aria-label="__('Switch portal')">
						<RouterLink
							v-for="item in switchItems"
							:key="item.label"
							:to="item.to"
							class="portal-sidebar__item group"
							:aria-label="item.label"
							@click="handleNavActivate"
						>
							<FeatherIcon :name="item.icon" class="portal-sidebar__icon" />
							<span class="portal-sidebar__label type-body-strong" aria-hidden="true">{{
								item.label
							}}</span>
							<span class="sr-only">{{ item.label }}</span>
							<span class="portal-sidebar__tooltip type-caption" aria-hidden="true">{{
								item.label
							}}</span>
						</RouterLink>
					</nav>
				</div>

				<div>
					<h3 class="portal-sidebar__section type-label">{{ __('Account') }}</h3>
					<nav class="mt-2 space-y-1" :aria-label="__('Account')">
						<a
							v-for="item in accountItems"
							:key="item.label"
							:href="item.href"
							class="portal-sidebar__item group"
							:aria-label="item.label"
							@click="handleNavActivate"
						>
							<FeatherIcon :name="item.icon" class="portal-sidebar__icon" />
							<span class="portal-sidebar__label type-body-strong" aria-hidden="true">{{
								item.label
							}}</span>
							<span class="sr-only">{{ item.label }}</span>
							<span class="portal-sidebar__tooltip type-caption" aria-hidden="true">{{
								item.label
							}}</span>
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
					:aria-label="isRailExpanded ? __('Collapse navigation') : __('Expand navigation')"
					@click="emit('toggle-rail')"
				>
					<FeatherIcon
						name="chevron-right"
						class="h-4 w-4 transition-transform"
						:class="{ 'rotate-180': isRailExpanded }"
					/>
					<span class="portal-sidebar__label" aria-hidden="true">{{
						isRailExpanded ? __('Collapse') : __('Expand')
					}}</span>
					<span class="sr-only">{{
						isRailExpanded ? __('Collapse navigation') : __('Expand navigation')
					}}</span>
				</button>
			</div>
		</div>
	</aside>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { RouteLocationRaw } from 'vue-router';
import { RouterLink } from 'vue-router';
import { FeatherIcon } from 'frappe-ui';

import { __ } from '@/lib/i18n';

type PortalSection = 'student' | 'guardian';

type MenuItem = {
	label: string;
	icon: string;
	to: RouteLocationRaw;
	badge?: 'unread-communications';
};

const props = defineProps<{
	isMobileOpen: boolean;
	isRailExpanded: boolean;
	activeSection: PortalSection;
	communicationUnreadCount?: number;
}>();

const emit = defineEmits<{
	(e: 'close-mobile'): void;
	(e: 'toggle-rail'): void;
}>();

function handleNavActivate() {
	emit('close-mobile');
}

const portalRoles = computed<string[]>(() => {
	const raw = (window as unknown as { portalRoles?: string[] }).portalRoles;
	if (!Array.isArray(raw)) return [];
	return raw
		.map(role =>
			String(role || '')
				.trim()
				.toLowerCase()
		)
		.filter(Boolean);
});

const hasStudentPortal = computed(() => portalRoles.value.includes('student'));
const hasGuardianPortal = computed(() => portalRoles.value.includes('guardian'));

const studentMenu: MenuItem[] = [
	{ label: __('Courses'), icon: 'book-open', to: { name: 'student-courses' } },
	{ label: __('Policies'), icon: 'shield', to: { name: 'student-policies' } },
	{ label: __('Forms & Signatures'), icon: 'edit-3', to: { name: 'student-consents' } },
	{ label: __('Portfolio & Journal'), icon: 'layers', to: { name: 'student-portfolio' } },
	{
		label: __('Communications'),
		icon: 'message-square',
		to: { name: 'student-communications' },
		badge: 'unread-communications',
	},
	{ label: __('Activities'), icon: 'star', to: { name: 'student-activities' } },
	{ label: __('Student Log'), icon: 'file-text', to: { name: 'student-logs' } },
];

const guardianMenu: MenuItem[] = [
	{
		label: __('Communications'),
		icon: 'message-square',
		to: { name: 'guardian-communications' },
		badge: 'unread-communications',
	},
	{ label: __('Attendance'), icon: 'calendar', to: { name: 'guardian-attendance' } },
	{ label: __('Activities'), icon: 'star', to: { name: 'guardian-activities' } },
	{ label: __('Monitoring'), icon: 'file-text', to: { name: 'guardian-monitoring' } },
	{ label: __('Finance'), icon: 'credit-card', to: { name: 'guardian-finance' } },
	{ label: __('Policies'), icon: 'shield', to: { name: 'guardian-policies' } },
	{ label: __('Forms & Signatures'), icon: 'edit-3', to: { name: 'guardian-consents' } },
	{ label: __('Showcase Portfolio'), icon: 'layers', to: { name: 'guardian-portfolio' } },
];

const menuItems = computed<MenuItem[]>(() => {
	if (props.activeSection === 'guardian' && hasGuardianPortal.value) {
		return guardianMenu;
	}
	if (props.activeSection === 'student' && hasStudentPortal.value) {
		return studentMenu;
	}
	if (hasStudentPortal.value) return studentMenu;
	if (hasGuardianPortal.value) return guardianMenu;
	return [];
});

const switchItems = computed<MenuItem[]>(() => {
	const items: MenuItem[] = [];
	if (props.activeSection !== 'student' && hasStudentPortal.value) {
		items.push({
			label: __('Go to Student Portal'),
			icon: 'book-open',
			to: { name: 'student-home' },
		});
	}
	if (props.activeSection !== 'guardian' && hasGuardianPortal.value) {
		items.push({
			label: __('Go to Guardian Portal'),
			icon: 'users',
			to: { name: 'guardian-home' },
		});
	}
	return items;
});

const sidebarLabel = computed(() => {
	if (props.activeSection === 'guardian') return __('Guardian Portal');
	return __('Student Portal');
});

const homeLabel = computed(() => {
	if (props.activeSection === 'guardian') return __('Family Snapshot');
	return __('Student Home');
});

const homeLink = computed<RouteLocationRaw>(() => {
	if (props.activeSection === 'guardian') return { name: 'guardian-home' };
	return { name: 'student-home' };
});

const accountItems = [
	{ label: __('Profile'), icon: 'user', href: '/desk/user-profile' },
	{ label: __('Logout'), icon: 'log-out', href: '/logout?redirect-to=%2F' },
];

function badgeCount(item: MenuItem) {
	if (item.badge !== 'unread-communications') return 0;
	return Math.max(0, Number(props.communicationUnreadCount || 0));
}

function badgeLabel(count: number) {
	return count > 9 ? '9+' : String(count);
}

function itemAriaLabel(item: MenuItem) {
	const count = badgeCount(item);
	if (!count) return item.label;
	return __('{0}, {1} unread communications', [item.label, count]);
}
</script>
