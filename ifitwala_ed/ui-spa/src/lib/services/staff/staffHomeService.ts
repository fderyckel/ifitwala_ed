// ui-spa/src/lib/services/staff/staffHomeService.ts

import { createResource } from 'frappe-ui'
import type { FocusItem } from '@/types/focusItem'

export type StaffHomeHeader = {
	user: string
	first_name?: string | null
	full_name?: string | null
}

export type ListFocusItemsPayload = {
	open_only: number
	limit: number
	offset: number
}

/**
 * A+ Transport Contract (LOCKED)
 * ------------------------------------------------------------
 * Services must NEVER unwrap transport responses.
 * The resourceFetcher (configured in ui-spa/src/resources/frappe.ts)
 * returns domain payloads only.
 */

const staffHomeHeaderResource = createResource<StaffHomeHeader>({
	url: 'ifitwala_ed.api.portal.get_staff_home_header',
	method: 'POST',
	auto: false,
})

const focusItemsResource = createResource<FocusItem[]>({
	url: 'ifitwala_ed.api.focus.list_focus_items',
	method: 'POST',
	auto: false,
})

export async function getStaffHomeHeader(): Promise<StaffHomeHeader> {
	return staffHomeHeaderResource.submit({})
}

export async function listFocusItems(payload: ListFocusItemsPayload): Promise<FocusItem[]> {
	return focusItemsResource.submit(payload)
}
