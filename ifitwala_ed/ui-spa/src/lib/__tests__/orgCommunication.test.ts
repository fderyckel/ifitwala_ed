import { describe, expect, it } from 'vitest';

import {
	getAudienceInteractionCapabilities,
	getInteractionCommentUi,
	ORG_COMMUNICATION_COMMENT_MODES,
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
			commentMode: ORG_COMMUNICATION_COMMENT_MODES.NONE,
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
			commentMode: ORG_COMMUNICATION_COMMENT_MODES.STAFF_THREAD,
		});
	});

	it('keeps structured feedback reaction-only on recipient-facing surfaces', () => {
		expect(
			getAudienceInteractionCapabilities({
				interaction_mode: 'Structured Feedback',
				allow_public_thread: 1,
			})
		).toEqual({
			canReact: true,
			canComment: false,
			hasVisibleActions: true,
			commentMode: ORG_COMMUNICATION_COMMENT_MODES.NONE,
		});
	});

	it('hides staff-only staff-comments interactions on recipient-facing surfaces', () => {
		expect(
			getAudienceInteractionCapabilities({
				interaction_mode: 'Staff Comments',
				allow_public_thread: 1,
			})
		).toEqual({
			canReact: false,
			canComment: false,
			hasVisibleActions: false,
			commentMode: ORG_COMMUNICATION_COMMENT_MODES.NONE,
		});
	});

	it('allows shared student q-and-a threads on recipient-facing surfaces when shared thread is on', () => {
		expect(
			getAudienceInteractionCapabilities({
				interaction_mode: 'Student Q&A',
				allow_public_thread: '1',
			})
		).toEqual({
			canReact: false,
			canComment: true,
			hasVisibleActions: true,
			commentMode: ORG_COMMUNICATION_COMMENT_MODES.SHARED_THREAD,
		});
	});

	it('keeps private student q-and-a notes available on recipient-facing surfaces when shared thread is off', () => {
		expect(
			getAudienceInteractionCapabilities({
				interaction_mode: 'Student Q&A',
				allow_public_thread: 'false',
			})
		).toEqual({
			canReact: false,
			canComment: true,
			hasVisibleActions: true,
			commentMode: ORG_COMMUNICATION_COMMENT_MODES.PRIVATE_NOTE,
		});
	});

	it('returns ask-school copy for private recipient notes', () => {
		expect(getInteractionCommentUi(ORG_COMMUNICATION_COMMENT_MODES.PRIVATE_NOTE)).toMatchObject({
			actionLabel: 'Ask School',
			submitLabel: 'Send to School',
		});
	});
});
