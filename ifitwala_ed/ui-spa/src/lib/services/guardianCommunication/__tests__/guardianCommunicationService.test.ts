import { describe, expect, it, vi } from 'vitest'

const { apiMethodMock } = vi.hoisted(() => ({
	apiMethodMock: vi.fn(),
}))

vi.mock('@/resources/frappe', () => ({
	apiMethod: apiMethodMock,
}))

import { getGuardianCommunicationCenter } from '@/lib/services/guardianCommunication/guardianCommunicationService'

describe('guardianCommunicationService', () => {
	it('uses the canonical method and direct payload for the guardian communication center', async () => {
		apiMethodMock.mockResolvedValue({ items: [] })

		await getGuardianCommunicationCenter({
			source: 'course',
			student: 'STU-1',
			start: 0,
			page_length: 24,
		})

		expect(apiMethodMock).toHaveBeenCalledWith(
			'ifitwala_ed.api.guardian_communications.get_guardian_communication_center',
			{
				source: 'course',
				student: 'STU-1',
				start: 0,
				page_length: 24,
			}
		)
	})
})
