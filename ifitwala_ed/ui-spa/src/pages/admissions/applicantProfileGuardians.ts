// ifitwala_ed/ui-spa/src/pages/admissions/applicantProfileGuardians.ts

import type { ApplicantGuardianProfile } from '@/types/contracts/admissions/types'

export function createEmptyGuardian(): ApplicantGuardianProfile {
	return {
		name: '',
		guardian: '',
		contact: '',
		use_applicant_contact: false,
		relationship: 'Other',
		is_primary: false,
		can_consent: true,
		salutation: '',
		guardian_full_name: '',
		guardian_first_name: '',
		guardian_last_name: '',
		guardian_gender: '',
		guardian_mobile_phone: '',
		guardian_email: '',
		guardian_work_email: '',
		guardian_work_phone: '',
		guardian_image: '',
		guardian_image_open_url: '',
		user: '',
		is_primary_guardian: false,
		is_financial_guardian: false,
		employment_sector: '',
		work_place: '',
		guardian_designation: '',
	}
}

function normalizeBoolean(value: unknown, fallback = false): boolean {
	if (typeof value === 'boolean') return value
	if (typeof value === 'number') return value !== 0
	const normalized = String(value || '')
		.trim()
		.toLowerCase()
	if (!normalized) return fallback
	return ['1', 'true', 'yes', 'on'].includes(normalized)
}

export function normalizeGuardianRow(
	input: ApplicantGuardianProfile | null | undefined
): ApplicantGuardianProfile {
	const row = input || {}
	return {
		...createEmptyGuardian(),
		...row,
		name: String(row.name || '').trim(),
		guardian: String(row.guardian || '').trim(),
		contact: String(row.contact || '').trim(),
		relationship: String(row.relationship || '').trim() || 'Other',
		salutation: String(row.salutation || '').trim(),
		guardian_full_name: String(row.guardian_full_name || '').trim(),
		guardian_first_name: String(row.guardian_first_name || '').trim(),
		guardian_last_name: String(row.guardian_last_name || '').trim(),
		guardian_gender: String(row.guardian_gender || '').trim(),
		guardian_mobile_phone: String(row.guardian_mobile_phone || '').trim(),
		guardian_email: String(row.guardian_email || '').trim(),
		guardian_work_email: String(row.guardian_work_email || '').trim(),
		guardian_work_phone: String(row.guardian_work_phone || '').trim(),
		guardian_image: String(row.guardian_image || '').trim(),
		guardian_image_open_url: String(row.guardian_image_open_url || '').trim(),
		user: String(row.user || '').trim(),
		employment_sector: String(row.employment_sector || '').trim(),
		work_place: String(row.work_place || '').trim(),
		guardian_designation: String(row.guardian_designation || '').trim(),
		use_applicant_contact: normalizeBoolean(row.use_applicant_contact, false),
		is_primary: normalizeBoolean(row.is_primary, false),
		can_consent: normalizeBoolean(row.can_consent, true),
		is_primary_guardian: normalizeBoolean(row.is_primary_guardian, false),
		is_financial_guardian: normalizeBoolean(row.is_financial_guardian, false),
	}
}

export function guardianRowIsEmpty(row: ApplicantGuardianProfile): boolean {
	return !(
		String(row.guardian || '').trim() ||
		String(row.guardian_first_name || '').trim() ||
		String(row.guardian_last_name || '').trim() ||
		String(row.guardian_email || '').trim() ||
		String(row.guardian_mobile_phone || '').trim() ||
		String(row.salutation || '').trim() ||
		String(row.guardian_work_email || '').trim() ||
		String(row.guardian_work_phone || '').trim() ||
		String(row.employment_sector || '').trim() ||
		String(row.work_place || '').trim() ||
		String(row.guardian_designation || '').trim() ||
		String(row.guardian_image || '').trim()
	)
}

export function guardianRowsForSubmit(rows: ApplicantGuardianProfile[]): ApplicantGuardianProfile[] {
	return rows
		.map(row => normalizeGuardianRow(row))
		.filter(row => !guardianRowIsEmpty(row))
}

function serializeGuardianRows(rows: ApplicantGuardianProfile[]): string {
	return JSON.stringify(
		guardianRowsForSubmit(rows).map(row => ({
			name: String(row.name || ''),
			guardian: String(row.guardian || ''),
			contact: String(row.contact || ''),
			use_applicant_contact: Boolean(row.use_applicant_contact),
			relationship: String(row.relationship || ''),
			is_primary: Boolean(row.is_primary),
			can_consent: Boolean(row.can_consent),
			salutation: String(row.salutation || ''),
			guardian_full_name: String(row.guardian_full_name || ''),
			guardian_first_name: String(row.guardian_first_name || ''),
			guardian_last_name: String(row.guardian_last_name || ''),
			guardian_gender: String(row.guardian_gender || ''),
			guardian_mobile_phone: String(row.guardian_mobile_phone || ''),
			guardian_email: String(row.guardian_email || ''),
			guardian_work_email: String(row.guardian_work_email || ''),
			guardian_work_phone: String(row.guardian_work_phone || ''),
			guardian_image: String(row.guardian_image || ''),
			user: String(row.user || ''),
			is_primary_guardian: Boolean(row.is_primary_guardian),
			is_financial_guardian: Boolean(row.is_financial_guardian),
			employment_sector: String(row.employment_sector || ''),
			work_place: String(row.work_place || ''),
			guardian_designation: String(row.guardian_designation || ''),
		}))
	)
}

export function haveGuardianRowsChanged(
	currentRows: ApplicantGuardianProfile[],
	savedRows: ApplicantGuardianProfile[]
): boolean {
	return serializeGuardianRows(currentRows) !== serializeGuardianRows(savedRows)
}
