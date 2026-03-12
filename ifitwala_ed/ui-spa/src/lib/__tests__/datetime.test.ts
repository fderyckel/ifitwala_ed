// ifitwala_ed/ui-spa/src/lib/__tests__/datetime.test.ts

import { afterEach, describe, expect, it, vi } from 'vitest'

import { formatHumanDateTimeFields } from '@/lib/datetime'

describe('lib/datetime human field formatting', () => {
	afterEach(() => {
		vi.unstubAllGlobals()
		document.documentElement.lang = ''
	})

	it('formats a date and time field into a human-readable English label', () => {
		vi.stubGlobal('window', {
			frappe: {
				boot: {
					lang: 'en',
					sysdefaults: { time_zone: 'Asia/Bangkok' },
				},
			},
		})

		expect(formatHumanDateTimeFields('2026-04-01', '10:15:00')).toBe('Wednesday 1st April, 10:15')
	})

	it('formats a date-only field without inventing a time', () => {
		vi.stubGlobal('window', {
			frappe: {
				boot: {
					lang: 'en',
					sysdefaults: { time_zone: 'Asia/Bangkok' },
				},
			},
		})

		expect(formatHumanDateTimeFields('2026-11-27', null)).toBe('Friday 27th November')
	})
})
