// ui-spa/src/lib/services/staff/staffHomeService.ts

import { createResource } from 'frappe-ui'
import type { FocusItem } from '@/types/focusItem'

export type StaffHomeHeader = {
	user: string
	first_name?: string | null
	full_name?: string | null
}

export type ListFocusItemsPayload = {
	open_only: 1
	limit: number
	offset: 0
}

/**
 * Transport normalization (A+)
 * - Accept unknown at the boundary.
 * - Normalize once.
 * - Return ONLY the contract type downstream (no union types).
 *
 * Handles:
 * - { message: T }
 * - Axios-ish: { data: { message: T } } / { data: T }
 * - Raw T
 */
function unwrapMessage<T>(res: unknown): T {
	const root =
		res && typeof res === 'object' && 'data' in (res as any) ? (res as any).data : res

	if (root && typeof root === 'object' && 'message' in (root as any)) {
		return (root as any).message as T
	}
	return root as T
}

const staffHomeHeaderResource = createResource<StaffHomeHeader>({
	url: 'ifitwala_ed.api.portal.get_staff_home_header',
	method: 'POST',
	auto: false,
	transform: (res: unknown) => unwrapMessage<StaffHomeHeader>(res),
})

const focusItemsResource = createResource<FocusItem[]>({
	url: 'ifitwala_ed.api.focus.list_focus_items',
	method: 'POST',
	auto: false,
	transform: (res: unknown) => unwrapMessage<FocusItem[]>(res),
})

export async function getStaffHomeHeader(): Promise<StaffHomeHeader> {
	return staffHomeHeaderResource.submit({})
}

export async function listFocusItems(payload: ListFocusItemsPayload): Promise<FocusItem[]> {
	return focusItemsResource.submit(payload)
}
