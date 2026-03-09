// ifitwala_ed/ui-spa/src/pages/admissions/applicantProfileGuardians.test.ts

import { describe, expect, it } from 'vitest'

import {
	guardianRowsForSubmit,
	haveGuardianRowsChanged,
	normalizeGuardianRow,
} from '@/pages/admissions/applicantProfileGuardians'
import type { ApplicantGuardianProfile } from '@/types/contracts/admissions/types'

describe('applicantProfileGuardians', () => {
	it('treats trimmed but unchanged guardian rows as unchanged', () => {
		const savedRows: ApplicantGuardianProfile[] = [
			{
				name: 'ROW-001',
				contact: 'CONTACT-001',
				guardian_first_name: 'Mina',
				guardian_last_name: 'Portal',
				guardian_email: 'guardian@example.com',
				guardian_mobile_phone: '+14155550101',
				guardian_image: '/private/files/guardian.png',
				can_consent: 1,
				is_primary: 1,
			},
		]
		const currentRows: ApplicantGuardianProfile[] = [
			{
				name: ' ROW-001 ',
				contact: ' CONTACT-001 ',
				guardian_first_name: ' Mina ',
				guardian_last_name: 'Portal',
				guardian_email: 'guardian@example.com ',
				guardian_mobile_phone: '+14155550101',
				guardian_image: ' /private/files/guardian.png ',
				can_consent: true,
				is_primary: true,
			},
		]

		expect(haveGuardianRowsChanged(currentRows, savedRows)).toBe(false)
	})

	it('detects when guardians are removed so the empty list is still submitted', () => {
		const savedRows: ApplicantGuardianProfile[] = [
			{
				name: 'ROW-001',
				guardian_first_name: 'Mina',
				guardian_last_name: 'Portal',
				guardian_email: 'guardian@example.com',
				guardian_mobile_phone: '+14155550101',
				guardian_image: '/private/files/guardian.png',
			},
		]

		expect(haveGuardianRowsChanged([], savedRows)).toBe(true)
	})

	it('filters empty guardian placeholders out of submit payloads', () => {
		const rows = guardianRowsForSubmit([
			normalizeGuardianRow(null),
			normalizeGuardianRow({
				guardian_first_name: 'Mina',
				guardian_last_name: 'Portal',
				guardian_email: 'guardian@example.com',
				guardian_mobile_phone: '+14155550101',
				guardian_image: '/private/files/guardian.png',
			}),
		])

		expect(rows).toHaveLength(1)
		expect(rows[0].guardian_first_name).toBe('Mina')
	})
})
