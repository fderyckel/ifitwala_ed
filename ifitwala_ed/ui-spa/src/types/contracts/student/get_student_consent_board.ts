import type {
	ConsentBoardCounts,
	ConsentBoardGroups,
	ConsentBoardRow,
} from '@/types/contracts/family_consent/shared'

export type Request = {}

export type Response = {
	meta: {
		generated_at: string
		student: { name: string | null }
	}
	identity: {
		student: string
	}
	counts: ConsentBoardCounts
	groups: ConsentBoardGroups
	rows?: ConsentBoardRow[]
}
