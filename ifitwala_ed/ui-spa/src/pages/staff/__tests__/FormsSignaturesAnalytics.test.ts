import { afterEach, describe, expect, it, vi } from 'vitest'
import { createApp, defineComponent, h, nextTick, type App } from 'vue'

const { getDashboardContextMock, getDashboardMock, routeQueryMock } = vi.hoisted(() => ({
	getDashboardContextMock: vi.fn(),
	getDashboardMock: vi.fn(),
	routeQueryMock: {
		organization: 'ORG-1',
		school: 'SCH-1',
		request_type: 'One-off Permission Request',
		status: 'Published',
		audience_mode: 'Guardian',
		completion_channel_mode: 'Paper Only',
	},
}))

vi.mock('@/lib/services/familyConsent/familyConsentService', () => ({
	createFamilyConsentService: () => ({
		getDashboardContext: getDashboardContextMock,
		getDashboard: getDashboardMock,
	}),
}))

vi.mock('vue-router', () => ({
	useRoute: () => ({
		query: routeQueryMock,
	}),
}))

vi.mock('frappe-ui', () => ({
	FeatherIcon: defineComponent({
		name: 'FeatherIconStub',
		props: { name: { type: String, required: false } },
		setup(props) {
			return () => h('span', { 'data-feather': props.name || '' })
		},
	}),
}))

vi.mock('@/components/filters/FiltersBar.vue', () => ({
	default: defineComponent({
		name: 'FiltersBarStub',
		setup(_props, { slots }) {
			return () => h('div', { 'data-testid': 'filters-bar' }, slots.default?.())
		},
	}),
}))

vi.mock('@/components/analytics/KpiRow.vue', () => ({
	default: defineComponent({
		name: 'KpiRowStub',
		props: { items: { type: Array, required: false, default: () => [] } },
		setup(props) {
			return () =>
				h(
					'div',
					{ 'data-testid': 'kpi-row' },
					(Array.isArray(props.items) ? props.items : []).map((item: any) =>
						h('span', { class: 'kpi-item' }, String(item?.label || ''))
					)
				)
		},
	}),
}))

import FormsSignaturesAnalytics from '@/pages/staff/analytics/FormsSignaturesAnalytics.vue'

const cleanupFns: Array<() => void> = []

async function flushUi() {
	await Promise.resolve()
	await nextTick()
	await Promise.resolve()
	await nextTick()
}

function mountAnalyticsPage() {
	const host = document.createElement('div')
	document.body.appendChild(host)

	const app: App = createApp(
		defineComponent({
			render() {
				return h(FormsSignaturesAnalytics)
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
	getDashboardContextMock.mockReset()
	getDashboardMock.mockReset()
	Object.assign(routeQueryMock, {
		organization: 'ORG-1',
		school: 'SCH-1',
		request_type: 'One-off Permission Request',
		status: 'Published',
		audience_mode: 'Guardian',
		completion_channel_mode: 'Paper Only',
	})
	while (cleanupFns.length) {
		cleanupFns.pop()?.()
	}
	document.body.innerHTML = ''
})

describe('FormsSignaturesAnalytics', () => {
	it('loads scoped filter context and renders request monitoring rows including paper-only tracking', async () => {
		getDashboardContextMock.mockResolvedValue({
			filters: { organization: 'ORG-1' },
			options: {
				organizations: ['ORG-1'],
				schools: ['SCH-1'],
				request_types: ['One-off Permission Request', 'Mutable Consent'],
				statuses: ['Draft', 'Published', 'Closed', 'Archived'],
				audience_modes: ['Guardian', 'Student', 'Guardian + Student'],
				completion_channel_modes: ['Portal Only', 'Portal Or Paper', 'Paper Only'],
			},
		})
		getDashboardMock.mockResolvedValue({
			meta: { generated_at: '2026-04-22T09:30:00Z' },
			filters: {
				organization: 'ORG-1',
				school: 'SCH-1',
				request_type: 'One-off Permission Request',
				status: 'Published',
				audience_mode: 'Guardian',
				completion_channel_mode: 'Paper Only',
			},
			counts: {
				requests: 1,
				pending: 1,
				completed: 0,
				declined: 0,
				withdrawn: 0,
				expired: 0,
				overdue: 0,
			},
			rows: [
				{
					family_consent_request: 'FCR-0001',
					request_key: 'FCR-KEY-1',
					request_title: 'Field Trip Permission',
					request_type: 'One-off Permission Request',
					audience_mode: 'Guardian',
					signer_rule: 'Any Authorized Guardian',
					completion_channel_mode: 'Paper Only',
					status: 'Published',
					organization: 'ORG-1',
					school: 'SCH-1',
					due_on: '2026-05-10',
					target_count: 1,
					pending_count: 1,
					completed_count: 0,
					declined_count: 0,
					withdrawn_count: 0,
					expired_count: 0,
					overdue_count: 0,
				},
			],
		})

		mountAnalyticsPage()
		await flushUi()

		expect(getDashboardContextMock).toHaveBeenCalledWith({ organization: 'ORG-1' })
		expect(getDashboardMock).toHaveBeenCalledWith({
			organization: 'ORG-1',
			school: 'SCH-1',
			request_type: 'One-off Permission Request',
			status: 'Published',
			audience_mode: 'Guardian',
			completion_channel_mode: 'Paper Only',
		})

		expect(document.body.textContent || '').toContain('Forms & Signatures')
		expect(document.body.textContent || '').toContain('Desk builds. Portal completes. Analytics stay here.')
		expect(document.body.textContent || '').toContain('Field Trip Permission')
		expect(document.body.textContent || '').toContain('Paper Only')
		expect(document.body.textContent || '').toContain('requests stay visible for monitoring here')

		const deskLink = document.querySelector('a[href="/app/family-consent-request"]')
		expect(deskLink).toBeTruthy()
	})
})
