import { afterEach, describe, expect, it, vi } from 'vitest'
import { createApp, defineComponent, h, nextTick, type App } from 'vue'

const { getGuardianPortalIdentityMock, getStudentPortalIdentityMock, routeState } = vi.hoisted(() => ({
	getGuardianPortalIdentityMock: vi.fn(),
	getStudentPortalIdentityMock: vi.fn(),
	routeState: { path: '/guardian' },
}))

vi.mock('frappe-ui', async () => {
	const { defineComponent, h } = await import('vue')

	return {
		FeatherIcon: defineComponent({
			name: 'FeatherIconStub',
			props: {
				name: {
					type: String,
					default: '',
				},
			},
			setup(props) {
				return () => h('span', { 'data-feather-icon': props.name })
			},
		}),
	}
})

vi.mock('vue-router', async () => {
	const { defineComponent, h } = await import('vue')

	return {
		RouterLink: defineComponent({
			name: 'RouterLinkStub',
			props: {
				to: {
					type: [String, Object],
					required: false,
					default: '',
				},
			},
			setup(_, { slots }) {
				return () => h('a', {}, slots.default?.())
			},
		}),
		useRoute: () => routeState,
	}
})

vi.mock('@/lib/services/guardian/guardianPortalService', () => ({
	getGuardianPortalIdentity: getGuardianPortalIdentityMock,
}))

vi.mock('@/lib/services/student/studentHomeService', () => ({
	getStudentPortalIdentity: getStudentPortalIdentityMock,
}))

import PortalNavbar from '@/components/PortalNavbar.vue'

const cleanupFns: Array<() => void> = []

async function flushUi() {
	await Promise.resolve()
	await nextTick()
	await Promise.resolve()
	await nextTick()
}

function mountPortalNavbar() {
	const host = document.createElement('div')
	document.body.appendChild(host)

	const app: App = createApp(
		defineComponent({
			render() {
				return h(PortalNavbar)
			},
		})
	)

	app.mount(host)
	cleanupFns.push(() => {
		app.unmount()
		host.remove()
	})
}

afterEach(() => {
	getGuardianPortalIdentityMock.mockReset()
	getStudentPortalIdentityMock.mockReset()
	routeState.path = '/guardian'
	delete (window as Window & { defaultPortal?: string }).defaultPortal
	delete (window as Window & { frappe?: unknown }).frappe
	while (cleanupFns.length) {
		cleanupFns.pop()?.()
	}
	document.body.innerHTML = ''
})

describe('PortalNavbar', () => {
	it('renders guardian identity and governed image on guardian routes', async () => {
		routeState.path = '/guardian'
		;(window as Window & { defaultPortal?: string }).defaultPortal = 'guardian'
		;(window as Window & { frappe?: unknown }).frappe = {
			session: { user: 'guardian@example.com' },
		}
		getGuardianPortalIdentityMock.mockResolvedValue({
			user: 'guardian@example.com',
			guardian: 'GRD-0001',
			display_name: 'Mina Dar',
			full_name: 'Mina Dar',
			email: 'guardian@example.com',
			image_url: '/files/guardian-thumb.webp',
		})

		mountPortalNavbar()
		await flushUi()

		expect(getGuardianPortalIdentityMock).toHaveBeenCalledTimes(1)
		expect(getStudentPortalIdentityMock).not.toHaveBeenCalled()
		expect(document.body.textContent || '').toContain('Mina Dar')
		expect(document.body.textContent || '').not.toContain('Guest')
		expect(document.querySelector('img[src="/files/guardian-thumb.webp"]')).not.toBeNull()

		const buttons = Array.from(document.querySelectorAll('button'))
		buttons[buttons.length - 1]?.dispatchEvent(new MouseEvent('click', { bubbles: true }))
		await flushUi()

		expect(document.body.textContent || '').toContain('guardian@example.com')
		expect(document.body.textContent || '').not.toContain('guest@example.com')
	})

	it('keeps student identity rendering on student routes', async () => {
		routeState.path = '/student'
		;(window as Window & { defaultPortal?: string }).defaultPortal = 'student'
		;(window as Window & { frappe?: unknown }).frappe = {
			session: { user: 'student@example.com' },
		}
		getStudentPortalIdentityMock.mockResolvedValue({
			user: 'student@example.com',
			display_name: 'Amina',
			full_name: 'Amina Example',
			image_url: '/files/student-thumb.webp',
		})

		mountPortalNavbar()
		await flushUi()

		expect(getStudentPortalIdentityMock).toHaveBeenCalledTimes(1)
		expect(getGuardianPortalIdentityMock).not.toHaveBeenCalled()
		expect(document.body.textContent || '').toContain('Amina Example')
		expect(document.querySelector('img[src="/files/student-thumb.webp"]')).not.toBeNull()

		const buttons = Array.from(document.querySelectorAll('button'))
		buttons[buttons.length - 1]?.dispatchEvent(new MouseEvent('click', { bubbles: true }))
		await flushUi()

		expect(document.body.textContent || '').toContain('student@example.com')
		expect(document.body.textContent || '').not.toContain('guest@example.com')
	})
})
