// ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianFinance.test.ts

import { afterEach, describe, expect, it, vi } from 'vitest'
import { createApp, defineComponent, h, nextTick, type App } from 'vue'

const { getGuardianFinanceSnapshotMock } = vi.hoisted(() => ({
	getGuardianFinanceSnapshotMock: vi.fn(),
}))

vi.mock('@/lib/services/guardianFinance/guardianFinanceService', () => ({
	getGuardianFinanceSnapshot: getGuardianFinanceSnapshotMock,
}))

import GuardianFinance from '@/pages/guardian/GuardianFinance.vue'

const cleanupFns: Array<() => void> = []

async function flushUi() {
	await Promise.resolve()
	await nextTick()
	await Promise.resolve()
	await nextTick()
}

function mountGuardianFinance() {
	const host = document.createElement('div')
	document.body.appendChild(host)

	const app: App = createApp(
		defineComponent({
			render() {
				return h(GuardianFinance)
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
	getGuardianFinanceSnapshotMock.mockReset()
	while (cleanupFns.length) {
		cleanupFns.pop()?.()
	}
	document.body.innerHTML = ''
})

describe('GuardianFinance', () => {
	it('renders finance summaries, invoices, and payment history from the canonical payload', async () => {
		getGuardianFinanceSnapshotMock.mockResolvedValue({
			meta: {
				generated_at: '2026-03-13T09:00:00',
				guardian: { name: 'GRD-0001' },
				finance_access: true,
				access_reason: '',
			},
			family: {
				children: [
					{
						student: 'STU-1',
						full_name: 'Amina Example',
						school: 'School One',
						account_holder: 'AH-1',
					},
				],
			},
			account_holders: [
				{
					account_holder: 'AH-1',
					label: 'Example Family',
					organization: 'ORG-1',
					status: 'Active',
					primary_email: 'guardian@example.com',
					primary_phone: '',
					students: [{ student: 'STU-1', full_name: 'Amina Example', school: 'School One' }],
				},
			],
			invoices: [
				{
					sales_invoice: 'INV-1',
					account_holder: 'AH-1',
					organization: 'ORG-1',
					school: 'School One',
					program: 'Program A',
					posting_date: '2026-03-01',
					due_date: '2026-03-15',
					grand_total: 1200,
					paid_amount: 200,
					outstanding_amount: 1000,
					status: 'Overdue',
					remarks: 'Tuition March',
					students: [{ student: 'STU-1', full_name: 'Amina Example' }],
				},
			],
			payments: [
				{
					payment_entry: 'PAY-1',
					account_holder: 'AH-1',
					organization: 'ORG-1',
					school: 'School One',
					program: 'Program A',
					posting_date: '2026-03-10',
					paid_amount: 200,
					unallocated_amount: 0,
					remarks: 'Card payment',
					references: [{ sales_invoice: 'INV-1', allocated_amount: 200 }],
				},
			],
			counts: {
				total_invoices: 1,
				open_invoices: 1,
				overdue_invoices: 1,
				payment_history_count: 1,
				total_outstanding: 1000,
				total_paid: 200,
			},
		})

		mountGuardianFinance()
		await flushUi()

		const text = document.body.textContent || ''
		expect(getGuardianFinanceSnapshotMock).toHaveBeenCalledTimes(1)
		expect(text).toContain('Family Finance')
		expect(text).toContain('Example Family')
		expect(text).toContain('INV-1')
		expect(text).toContain('Amina Example')
		expect(text).toContain('PAY-1')
		expect(text).toContain('Card payment')
	})

	it('renders an explicit access-limited state when no account holder is authorized', async () => {
		getGuardianFinanceSnapshotMock.mockResolvedValue({
			meta: {
				generated_at: '2026-03-13T09:00:00',
				guardian: { name: 'GRD-0001' },
				finance_access: false,
				access_reason: 'no_authorized_account_holders',
			},
			family: { children: [] },
			account_holders: [],
			invoices: [],
			payments: [],
			counts: {
				total_invoices: 0,
				open_invoices: 0,
				overdue_invoices: 0,
				payment_history_count: 0,
				total_outstanding: 0,
				total_paid: 0,
			},
		})

		mountGuardianFinance()
		await flushUi()

		expect(document.body.textContent || '').toContain('Finance access is limited for this guardian account.')
	})
})
