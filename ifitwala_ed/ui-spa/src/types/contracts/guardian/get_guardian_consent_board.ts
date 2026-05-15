import type {
	ConsentBoardCounts,
	ConsentBoardGroups,
	ConsentBoardRow,
} from '@/types/contracts/family_consent/shared'

export type Request = {}

export type Response = {
	meta: {
		generated_at: string
		guardian: { name: string | null }
	}
	family: {
		children: Array<{
			student: string
			full_name: string
			school: string
			student_image_url?: string | null
		}>
	}
	counts: ConsentBoardCounts
	groups: ConsentBoardGroups
	rows?: ConsentBoardRow[]
}
