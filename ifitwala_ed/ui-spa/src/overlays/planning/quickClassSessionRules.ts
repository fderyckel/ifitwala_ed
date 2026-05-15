// ui-spa/src/overlays/planning/quickClassSessionRules.ts

import type {
	StaffPlanningSession,
	StaffPlanningUnit,
} from '@/types/contracts/staff_teaching/get_staff_class_planning_surface'

export type QuickClassSessionMatch = {
	unit_plan: string
	class_session: string
}

function normalizeDate(value?: string | null): string {
	return String(value || '').trim()
}

function parseSessionDate(value?: string | null): number | null {
	const normalized = normalizeDate(value)
	if (!normalized) return null
	const parsed = Date.parse(normalized)
	return Number.isNaN(parsed) ? null : parsed
}

export function findSessionForDate(
	units: StaffPlanningUnit[],
	sessionDate?: string | null
): QuickClassSessionMatch | null {
	const targetDate = normalizeDate(sessionDate)
	if (!targetDate) return null

	for (const unit of units || []) {
		for (const session of unit.sessions || []) {
			if (normalizeDate(session.session_date) === targetDate) {
				return {
					unit_plan: unit.unit_plan,
					class_session: session.class_session,
				}
			}
		}
	}

	return null
}

function isInProgressUnit(unit: StaffPlanningUnit): boolean {
	return normalizeDate(unit.pacing_status).toLowerCase() === 'in progress'
}

function hasTaughtSession(unit: StaffPlanningUnit): boolean {
	return (unit.sessions || []).some(
		session => normalizeDate(session.session_status).toLowerCase() === 'taught'
	)
}

function latestSessionTimestamp(unit: StaffPlanningUnit): number {
	let latest = -1
	for (const session of unit.sessions || []) {
		const parsed = parseSessionDate(session.session_date)
		if (parsed !== null) {
			latest = Math.max(latest, parsed)
			continue
		}
		const fallback = Number(session.sequence_index || 0)
		latest = Math.max(latest, fallback)
	}
	return latest
}

export function suggestUnitPlan(units: StaffPlanningUnit[]): string | null {
	if (!units.length) return null

	const inProgress = units.find(isInProgressUnit)
	if (inProgress?.unit_plan) return inProgress.unit_plan

	const nextUntaught = units.find(unit => !hasTaughtSession(unit))
	if (nextUntaught?.unit_plan) return nextUntaught.unit_plan

	const ranked = [...units].sort((left, right) => {
		const rightTimestamp = latestSessionTimestamp(right)
		const leftTimestamp = latestSessionTimestamp(left)
		if (rightTimestamp !== leftTimestamp) return rightTimestamp - leftTimestamp

		const rightOrder = Number(right.unit_order || 0)
		const leftOrder = Number(left.unit_order || 0)
		return rightOrder - leftOrder
	})

	return ranked[0]?.unit_plan || units[0]?.unit_plan || null
}

export function suggestSessionSequence(unit: StaffPlanningUnit | null): number | null {
	if (!unit) return null

	const explicitIndexes = (unit.sessions || [])
		.map(session => Number(session.sequence_index))
		.filter(value => Number.isFinite(value) && value > 0)

	if (explicitIndexes.length) {
		return Math.max(...explicitIndexes) + 10
	}

	const count = (unit.sessions || []).length
	return count > 0 ? (count + 1) * 10 : 10
}

export function suggestedSessionTitle(unit: StaffPlanningUnit | null): string {
	return (unit?.title || '').trim()
}

export function sessionBelongsToUnit(
	unit: StaffPlanningUnit | null,
	classSession?: string | null
): StaffPlanningSession | null {
	const target = normalizeDate(classSession)
	if (!unit || !target) return null
	return (unit.sessions || []).find(session => session.class_session === target) || null
}
