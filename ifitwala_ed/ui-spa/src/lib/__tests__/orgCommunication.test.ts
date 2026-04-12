import { describe, expect, it } from 'vitest';

import { getAudienceInteractionCapabilities } from '@/utils/orgCommunication';

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

	it('allows reactions but not shared comments when the shared thread is off', () => {
		expect(
			getAudienceInteractionCapabilities({
				interaction_mode: 'Staff Comments',
				allow_public_thread: 0,
			})
		).toEqual({
			canReact: true,
			canComment: false,
			hasVisibleActions: true,
		});
	});

	it('allows both reactions and shared comments when the shared thread is on', () => {
		expect(
			getAudienceInteractionCapabilities({
				interaction_mode: 'Student Q&A',
				allow_public_thread: '1',
			})
		).toEqual({
			canReact: true,
			canComment: true,
			hasVisibleActions: true,
		});
	});
});
