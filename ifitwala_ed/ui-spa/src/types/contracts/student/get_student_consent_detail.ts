import type {
	ConsentDetailRequestBlock,
	ConsentDetailSignerBlock,
	ConsentDetailTargetBlock,
	ConsentFieldRow,
	ConsentHistoryRow,
} from '@/types/contracts/family_consent/shared'

export type Request = {
	request_key: string
	student: string
}

export type Response = {
	meta: {
		generated_at: string
	}
	request: ConsentDetailRequestBlock
	target: ConsentDetailTargetBlock
	signer: ConsentDetailSignerBlock
	fields: ConsentFieldRow[]
	history: ConsentHistoryRow[]
}
