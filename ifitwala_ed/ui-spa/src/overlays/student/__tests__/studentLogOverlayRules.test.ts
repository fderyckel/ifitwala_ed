// ui-spa/src/overlays/student/__tests__/studentLogOverlayRules.test.ts

import { describe, expect, it } from 'vitest'

import {
	hasStudentLogDraftContent,
	normalizeStudentLogOverlayMode,
	shouldPromptStudentLogDiscard,
} from '../studentLogOverlayRules'

describe('studentLogOverlayRules', () => {
	it('normalizes overlay mode to attendance when explicitly requested', () => {
		expect(normalizeStudentLogOverlayMode('attendance')).toBe('attendance')
	})

	it('normalizes unknown overlay mode to home', () => {
		expect(normalizeStudentLogOverlayMode('school')).toBe('home')
		expect(normalizeStudentLogOverlayMode(undefined)).toBe('home')
	})

	it('detects draft content only when mutable form fields are present', () => {
		expect(
			hasStudentLogDraftContent({
				log: '  ',
				log_type: '',
				requires_follow_up: false,
				next_step: '',
				follow_up_person: '',
				visible_to_student: false,
				visible_to_guardians: false,
			})
		).toBe(false)

		expect(
			hasStudentLogDraftContent({
				log: 'Observed new behavior.',
			})
		).toBe(true)

		expect(
			hasStudentLogDraftContent({
				visible_to_guardians: true,
			})
		).toBe(true)
	})

	it('prompts discard only for non-programmatic closes with draft content', () => {
		expect(shouldPromptStudentLogDiscard('programmatic', true)).toBe(false)
		expect(shouldPromptStudentLogDiscard('esc', false)).toBe(false)
		expect(shouldPromptStudentLogDiscard('backdrop', true)).toBe(true)
		expect(shouldPromptStudentLogDiscard('esc', true)).toBe(true)
	})
})
