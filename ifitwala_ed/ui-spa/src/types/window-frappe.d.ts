// ifitwala_ed/ui-spa/src/types/window-frappe.d.ts

export {}

declare global {
	interface FrappeSessionUserInfo {
		fullname?: string | null
		email?: string | null
		[key: string]: unknown
	}

	interface FrappeSessionState {
		user?: string | null
		user_info?: FrappeSessionUserInfo | null
		[key: string]: unknown
	}

	interface FrappeBrowserGlobal {
		session?: FrappeSessionState | null
		[key: string]: unknown
	}

	interface Window {
		frappe?: FrappeBrowserGlobal
		csrf_token?: string
	}
}
