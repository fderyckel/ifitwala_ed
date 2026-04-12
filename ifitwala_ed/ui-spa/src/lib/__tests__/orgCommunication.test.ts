import { describe, expect, it } from 'vitest';

import {
	getAudienceInteractionCapabilities,
	ORG_COMMUNICATION_VIEWERS,
} from '@/utils/orgCommunication';

describe('getAudienceInteractionCapabilities', () => {
	it('disables all actions when interaction mode is None', () => {
		expect(
			getAudienceInteractionCapabilities({
				interaction_mode: 'None',
				allow_public_thread: 1,
			})
		).toEqual({
			canReact: false,
			canComment: false,
			hasVisibleActions: false,
		});
	});

	it('keeps staff comments available on staff-facing surfaces even when the shared-thread flag is off', () => {
		expect(
			getAudienceInteractionCapabilities({
				interaction_mode: 'Staff Comments',
				allow_public_thread: 0,
			}, {
				viewer: ORG_COMMUNICATION_VIEWERS.STAFF,
			})
		).toEqual({
			canReact: true,
			canComment: true,
			hasVisibleActions: true,
		});
	});

	it('hides staff-only interactions on recipient-facing surfaces', () => {
		expect(
			getAudienceInteractionCapabilities({
				interaction_mode: 'Staff Comments',
				allow_public_thread: 1,
			})
		).toEqual({
			canReact: false,
			canComment: false,
			hasVisibleActions: false,
		});
	});

	it('allows shared-thread comments on recipient-facing surfaces when the mode supports them', () => {
		expect(
			getAudienceInteractionCapabilities({
				interaction_mode: 'Student Q&A',
				allow_public_thread: '1',
			})
		).toEqual({
			canReact: false,
			canComment: true,
			hasVisibleActions: true,
		});
	});

	it('keeps structured-feedback reactions available on recipient-facing surfaces', () => {
		expect(
			getAudienceInteractionCapabilities({
				interaction_mode: 'Structured Feedback',
				allow_public_thread: 'false',
			})
		).toEqual({
			canReact: true,
			canComment: false,
			hasVisibleActions: true,
		});
	});
});
