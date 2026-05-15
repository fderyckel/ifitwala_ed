// ui-spa/src/overlays/planning/__tests__/quickClassSessionRules.test.ts

import { describe, expect, it } from 'vitest'

import type { StaffPlanningUnit } from '@/types/contracts/staff_teaching/get_staff_class_planning_surface'

import {
	findSessionForDate,
	sessionBelongsToUnit,
	suggestedSessionTitle,
	suggestSessionSequence,
	suggestUnitPlan,
} from '../quickClassSessionRules'

function buildUnit(overrides: Partial<StaffPlanningUnit>): StaffPlanningUnit {
	return {
		unit_plan: overrides.unit_plan || 'UP-001',
		title: overrides.title || 'Argument Writing',
		standards: [],
		shared_resources: [],
		assigned_work: [],
		governed_required: 1,
		sessions: [],
		...overrides,
	}
}

describe('quickClassSessionRules', () => {
	it('finds an existing session for the clicked calendar date', () => {
		const units = [
			buildUnit({
				unit_plan: 'UP-001',
				sessions: [
					{
						class_session: 'CLASS-SESSION-00001',
						title: 'Claim warm-up',
						unit_plan: 'UP-001',
						session_date: '2026-04-07',
						activities: [],
						resources: [],
						assigned_work: [],
					},
				],
			}),
		]

		expect(findSessionForDate(units, '2026-04-07')).toEqual({
			unit_plan: 'UP-001',
			class_session: 'CLASS-SESSION-00001',
		})
		expect(findSessionForDate(units, '2026-04-08')).toBeNull()
	})

	it('prefers the in-progress unit before other suggestions', () => {
		const units = [
			buildUnit({
				unit_plan: 'UP-001',
				unit_order: 1,
				pacing_status: 'Completed',
				sessions: [
					{
						class_session: 'CLASS-SESSION-00001',
						title: 'Launch',
						unit_plan: 'UP-001',
						session_status: 'Taught',
						session_date: '2026-03-01',
						activities: [],
						resources: [],
						assigned_work: [],
					},
				],
			}),
			buildUnit({
				unit_plan: 'UP-002',
				unit_order: 2,
				pacing_status: 'In Progress',
			}),
		]

		expect(suggestUnitPlan(units)).toBe('UP-002')
	})

	it('falls back to the next untaught unit when none are in progress', () => {
		const units = [
			buildUnit({
				unit_plan: 'UP-001',
				unit_order: 1,
				pacing_status: 'Completed',
				sessions: [
					{
						class_session: 'CLASS-SESSION-00001',
						title: 'Launch',
						unit_plan: 'UP-001',
						session_status: 'Taught',
						session_date: '2026-03-01',
						activities: [],
						resources: [],
						assigned_work: [],
					},
				],
			}),
			buildUnit({
				unit_plan: 'UP-002',
				unit_order: 2,
				pacing_status: 'Not Started',
				sessions: [],
			}),
		]

		expect(suggestUnitPlan(units)).toBe('UP-002')
	})

	it('uses the most recently active unit when all units have taught sessions', () => {
		const units = [
			buildUnit({
				unit_plan: 'UP-001',
				unit_order: 1,
				sessions: [
					{
						class_session: 'CLASS-SESSION-00001',
						title: 'Earlier',
						unit_plan: 'UP-001',
						session_status: 'Taught',
						session_date: '2026-03-01',
						activities: [],
						resources: [],
						assigned_work: [],
					},
				],
			}),
			buildUnit({
				unit_plan: 'UP-002',
				unit_order: 2,
				sessions: [
					{
						class_session: 'CLASS-SESSION-00002',
						title: 'Later',
						unit_plan: 'UP-002',
						session_status: 'Taught',
						session_date: '2026-03-14',
						activities: [],
						resources: [],
						assigned_work: [],
					},
				],
			}),
		]

		expect(suggestUnitPlan(units)).toBe('UP-002')
	})

	it('suggests the next session sequence with room for insertion', () => {
		const unitWithExplicitSequence = buildUnit({
			sessions: [
				{
					class_session: 'CLASS-SESSION-00001',
					title: 'One',
					unit_plan: 'UP-001',
					sequence_index: 10,
					activities: [],
					resources: [],
					assigned_work: [],
				},
				{
					class_session: 'CLASS-SESSION-00002',
					title: 'Two',
					unit_plan: 'UP-001',
					sequence_index: 30,
					activities: [],
					resources: [],
					assigned_work: [],
				},
			],
		})
		const unitWithoutExplicitSequence = buildUnit({
			sessions: [
				{
					class_session: 'CLASS-SESSION-00003',
					title: 'Only',
					unit_plan: 'UP-001',
					activities: [],
					resources: [],
					assigned_work: [],
				},
			],
		})

		expect(suggestSessionSequence(unitWithExplicitSequence)).toBe(40)
		expect(suggestSessionSequence(unitWithoutExplicitSequence)).toBe(20)
		expect(suggestSessionSequence(buildUnit({ sessions: [] }))).toBe(10)
	})

	it('returns the current unit title as the quick-session title seed', () => {
		expect(suggestedSessionTitle(buildUnit({ title: 'Evidence and Reasoning' }))).toBe(
			'Evidence and Reasoning'
		)
		expect(suggestedSessionTitle(null)).toBe('')
	})

	it('resolves a selected session only when it belongs to the chosen unit', () => {
		const unit = buildUnit({
			sessions: [
				{
					class_session: 'CLASS-SESSION-00001',
					title: 'Opening',
					unit_plan: 'UP-001',
					activities: [],
					resources: [],
					assigned_work: [],
				},
			],
		})

		expect(sessionBelongsToUnit(unit, 'CLASS-SESSION-00001')?.title).toBe('Opening')
		expect(sessionBelongsToUnit(unit, 'CLASS-SESSION-99999')).toBeNull()
		expect(sessionBelongsToUnit(null, 'CLASS-SESSION-00001')).toBeNull()
	})
})
