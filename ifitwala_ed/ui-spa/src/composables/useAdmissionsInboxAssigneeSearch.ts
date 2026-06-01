import { computed, ref } from 'vue';

import { searchAdmissionsInboxAssignees } from '@/lib/services/admissions/admissionsInboxService';
import type {
	AdmissionsInboxAssigneeOption,
	SearchAdmissionsInboxAssigneesRequest,
} from '@/types/contracts/admissions_inbox/get_admissions_inbox_context';

type AssigneeSearchOptions = {
	getPayload: (query: string) => SearchAdmissionsInboxAssigneesRequest | null;
	getQuery: () => string;
	onError: (message: string) => void;
	errorMessage: string;
};

export function useAdmissionsInboxAssigneeSearch(options: AssigneeSearchOptions) {
	const candidates = ref<AdmissionsInboxAssigneeOption[]>([]);
	const loading = ref(false);
	let sequence = 0;

	const showNoMatches = computed(() => {
		const query = options.getQuery().trim();
		return query.length >= 2 && !loading.value && candidates.value.length === 0;
	});

	function reset() {
		sequence += 1;
		candidates.value = [];
		loading.value = false;
	}

	async function load(query: string) {
		const payload = options.getPayload(query);
		if (!payload) {
			reset();
			return;
		}

		const currentSequence = ++sequence;
		loading.value = true;

		try {
			const rows = await searchAdmissionsInboxAssignees(payload);
			if (currentSequence !== sequence) return;
			candidates.value = rows || [];
		} catch (err) {
			if (currentSequence !== sequence) return;
			candidates.value = [];
			options.onError(err instanceof Error ? err.message : String(err || options.errorMessage));
		} finally {
			if (currentSequence === sequence) {
				loading.value = false;
			}
		}
	}

	function handleInput(query = options.getQuery()) {
		const text = String(query || '').trim();
		if (text && text.length < 2) {
			reset();
			return;
		}
		void load(text);
	}

	function selectCandidate(candidate: AdmissionsInboxAssigneeOption) {
		candidates.value = [];
		return String(candidate.value || '').trim();
	}

	return {
		candidates,
		loading,
		showNoMatches,
		reset,
		load,
		handleInput,
		selectCandidate,
	};
}
