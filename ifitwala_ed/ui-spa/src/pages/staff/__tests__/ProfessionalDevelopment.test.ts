import { afterEach, describe, expect, it, vi } from 'vitest'
import { createApp, defineComponent, h, nextTick, type App } from 'vue'

const {
	getBoardMock,
	getHeaderMock,
	overlayOpenMock,
	cancelRequestMock,
	decideRequestMock,
	liquidateRecordMock,
} = vi.hoisted(() => ({
	getBoardMock: vi.fn(),
	getHeaderMock: vi.fn(),
	overlayOpenMock: vi.fn(),
	cancelRequestMock: vi.fn(),
	decideRequestMock: vi.fn(),
	liquidateRecordMock: vi.fn(),
}))

vi.mock('@/lib/services/professionalDevelopment/professionalDevelopmentService', () => ({
	getProfessionalDevelopmentBoard: getBoardMock,
	cancelProfessionalDevelopmentRequest: cancelRequestMock,
	decideProfessionalDevelopmentRequest: decideRequestMock,
	liquidateProfessionalDevelopmentRecord: liquidateRecordMock,
}))

vi.mock('@/lib/services/staff/staffHomeService', () => ({
	getStaffHomeHeader: getHeaderMock,
}))

vi.mock('@/composables/useOverlayStack', () => ({
	useOverlayStack: () => ({
		open: overlayOpenMock,
	}),
}))

vi.mock('vue-router', () => ({
	RouterLink: defineComponent({
		name: 'RouterLinkStub',
		props: ['to'],
		setup(_props, { slots }) {
			return () => h('a', {}, slots.default?.())
		},
	}),
}))

import ProfessionalDevelopment from '@/pages/staff/ProfessionalDevelopment.vue'

const cleanupFns: Array<() => void> = []

async function flushUi() {
	await Promise.resolve()
	await nextTick()
	await Promise.resolve()
	await nextTick()
}

function mountPage() {
	const host = document.createElement('div')
	document.body.appendChild(host)

	const app: App = createApp(
		defineComponent({
			render() {
				return h(ProfessionalDevelopment)
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
	getBoardMock.mockReset()
	getHeaderMock.mockReset()
	overlayOpenMock.mockReset()
	cancelRequestMock.mockReset()
	decideRequestMock.mockReset()
	liquidateRecordMock.mockReset()
	while (cleanupFns.length) cleanupFns.pop()?.()
	document.body.innerHTML = ''
})

describe('ProfessionalDevelopment page', () => {
	it('renders board data and opens the request overlay', async () => {
		getHeaderMock.mockResolvedValue({
			user: 'staff@example.com',
			capabilities: {
				professional_development_decide: true,
				professional_development_liquidate: true,
			},
		})
		getBoardMock.mockResolvedValue({
			generated_at: '2026-03-20T10:00:00',
			viewer: {
				user: 'staff@example.com',
				employee: 'HR-EMP-0001',
				employee_name: 'Ada Staff',
				organization: 'ORG-1',
				school: 'SCH-1',
				academic_year: 'AY-1',
			},
			settings: {
				budget_mode: 'Hybrid',
				require_completion_evidence: 1,
				require_liquidation_reflection: 1,
			},
			summary: {
				open_requests: 1,
				upcoming_records: 1,
				completion_backlog: 0,
				available_budget_total: 1500,
			},
			request_options: { themes: [], budgets: [], pgp_plans: [], types: [] },
			requests: [
				{
					name: 'PDRQ-1',
					title: 'Assessment for learning workshop',
					professional_development_type: 'Workshop',
					status: 'Submitted',
					start_datetime: '2026-04-02 09:00:00',
					end_datetime: '2026-04-02 15:00:00',
					estimated_total: 200,
					validation_status: 'Valid',
					requires_override: 0,
				},
			],
			records: [
				{
					name: 'PDR-1',
					title: 'Assessment for learning workshop',
					professional_development_type: 'Workshop',
					status: 'Planned',
					start_datetime: '2026-04-02 09:00:00',
					end_datetime: '2026-04-02 15:00:00',
					estimated_total: 200,
					actual_total: 0,
				},
			],
			completion_backlog: [],
			budget_rows: [
				{
					value: 'PDB-1',
					label: 'Whole School PD (School Pool)',
					budget_mode: 'School Pool',
					available_amount: 1200,
				},
			],
			expiring_items: [],
		})

		mountPage()
		await flushUi()

		const text = document.body.textContent || ''
		expect(text).toContain('Professional Development')
		expect(text).toContain('Assessment for learning workshop')
		expect(text).toContain('Whole School PD')

		const newRequestButton = Array.from(document.querySelectorAll('button')).find((button) =>
			(button.textContent || '').includes('New request')
		)
		newRequestButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }))
		await flushUi()

		expect(overlayOpenMock).toHaveBeenCalledWith('staff-professional-development-request', {
			budgetName: null,
		})
	})
})
