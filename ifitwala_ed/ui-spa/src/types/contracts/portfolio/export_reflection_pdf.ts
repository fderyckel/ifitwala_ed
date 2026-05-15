// ifitwala_ed/ui-spa/src/types/contracts/portfolio/export_reflection_pdf.ts

import type { Request as ListReflectionEntriesRequest } from './list_reflection_entries'

export type Request = ListReflectionEntriesRequest

export type Response = {
	file_url: string
	file_name: string
	student: string
}
