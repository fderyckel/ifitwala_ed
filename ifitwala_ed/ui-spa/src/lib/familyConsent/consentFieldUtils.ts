import type { ConsentAddressValue, ConsentFieldRow, ConsentFieldValue } from '@/types/contracts/family_consent/shared'

const ADDRESS_KEYS: Array<keyof ConsentAddressValue> = [
	'address_line1',
	'address_line2',
	'city',
	'state',
	'country',
	'pincode',
]

function asText(value: unknown): string {
	return String(value ?? '').trim()
}

export function normalizeConsentFieldValue(fieldType: string, value: ConsentFieldValue): ConsentFieldValue {
	if (fieldType === 'Address') {
		const raw = value && typeof value === 'object' && !Array.isArray(value) ? value : {}
		const normalized: ConsentAddressValue = {}
		for (const key of ADDRESS_KEYS) {
			const cleaned = asText((raw as ConsentAddressValue)?.[key])
			if (cleaned) normalized[key] = cleaned
		}
		return Object.keys(normalized).length ? normalized : null
	}
	if (fieldType === 'Checkbox') {
		return Boolean(value)
	}
	if (fieldType === 'Date') {
		return asText(value) || null
	}
	if (typeof value === 'number') return value
	return asText(value) || null
}

export function formatConsentValue(fieldType: string, value: ConsentFieldValue): string {
	const normalized = normalizeConsentFieldValue(fieldType, value)
	if (fieldType === 'Address') {
		const address = normalized as ConsentAddressValue | null
		if (!address) return 'No address on file'
		const localityParts = [address.city, address.state].filter(Boolean)
		let locality = localityParts.join(', ')
		if (address.pincode) {
			locality = locality ? `${locality} ${address.pincode}` : address.pincode
		}
		return [address.address_line1, address.address_line2, locality, address.country]
			.filter(Boolean)
			.join(', ')
	}
	if (fieldType === 'Checkbox') {
		return normalized ? 'Yes' : 'No'
	}
	return String(normalized || 'Not provided')
}

export function isConsentFieldChanged(field: ConsentFieldRow, value: ConsentFieldValue): boolean {
	return JSON.stringify(normalizeConsentFieldValue(field.field_type, value)) !== JSON.stringify(
		normalizeConsentFieldValue(field.field_type, field.presented_value)
	)
}

export function buildConsentFieldDraftValue(field: ConsentFieldRow): ConsentFieldValue {
	return normalizeConsentFieldValue(field.field_type, field.presented_value)
}

export function emptyAddressValue(): ConsentAddressValue {
	return {
		address_line1: '',
		address_line2: '',
		city: '',
		state: '',
		country: '',
		pincode: '',
	}
}
