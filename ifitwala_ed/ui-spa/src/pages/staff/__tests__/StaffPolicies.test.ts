// ifitwala_ed/ui-spa/src/pages/staff/__tests__/StaffPolicies.test.ts

import { afterEach, describe, expect, it, vi } from 'vitest';
import { createApp, defineComponent, h, nextTick, type App } from 'vue';

const { getPolicyLibraryMock, overlayOpenMock, getStaffHomeHeaderMock, routerPushMock } =
	vi.hoisted(() => ({
		getPolicyLibraryMock: vi.fn(),
		overlayOpenMock: vi.fn(),
		getStaffHomeHeaderMock: vi.fn(),
		routerPushMock: vi.fn(),
	}));

vi.mock('@/lib/services/policySignature/policySignatureService', () => ({
	createPolicySignatureService: () => ({
		getPolicyLibrary: getPolicyLibraryMock,
	}),
}));

vi.mock('@/composables/useOverlayStack', () => ({
	useOverlayStack: () => ({
		open: overlayOpenMock,
	}),
}));

vi.mock('vue-router', () => ({
	useRouter: () => ({
		push: routerPushMock,
	}),
}));

vi.mock('@/lib/services/staff/staffHomeService', () => ({
	getStaffHomeHeader: getStaffHomeHeaderMock,
}));

vi.mock('@/components/filters/FiltersBar.vue', () => ({
	default: defineComponent({
		name: 'FiltersBarStub',
		setup(_props, { slots }) {
			return () => h('div', { 'data-testid': 'filters-bar' }, slots.default?.());
		},
	}),
}));

vi.mock('@/components/analytics/KpiRow.vue', () => ({
	default: defineComponent({
		name: 'KpiRowStub',
		props: { items: { type: Array, required: false, default: () => [] } },
		setup(props) {
			return () =>
				h(
					'div',
					{ 'data-testid': 'kpi-row' },
					(Array.isArray(props.items) ? props.items : []).map((item: any) =>
						h('span', { class: 'kpi-item' }, String(item?.label || ''))
					)
				);
		},
	}),
}));

import StaffPolicies from '@/pages/staff/StaffPolicies.vue';

const cleanupFns: Array<() => void> = [];

function makeCounts(overrides: Record<string, number> = {}) {
	return {
		total_policies: 0,
		staff_policies: 0,
		guardian_policies: 0,
		student_policies: 0,
		organization_scoped: 0,
		school_scoped: 0,
		multi_audience: 0,
		signature_required: 0,
		informational: 0,
		signed: 0,
		pending: 0,
		new_version: 0,
		...overrides,
	};
}

async function flushUi() {
	await Promise.resolve();
	await nextTick();
	await Promise.resolve();
	await nextTick();
}

function mountStaffPolicies() {
	const host = document.createElement('div');
	document.body.appendChild(host);

	const app: App = createApp(
		defineComponent({
			render() {
				return h(StaffPolicies);
			},
		})
	);

	app.mount(host);
	cleanupFns.push(() => {
		app.unmount();
		host.remove();
	});
}

afterEach(() => {
	getPolicyLibraryMock.mockReset();
	overlayOpenMock.mockReset();
	getStaffHomeHeaderMock.mockReset();
	routerPushMock.mockReset();
	while (cleanupFns.length) {
		cleanupFns.pop()?.();
	}
	document.body.innerHTML = '';
});

describe('StaffPolicies', () => {
	it('renders staff-mode status labels in the policy library', async () => {
		getStaffHomeHeaderMock.mockResolvedValue({
			user: 'staff@example.com',
			capabilities: { analytics_policy_signatures: false },
		});
		getPolicyLibraryMock.mockResolvedValue({
			meta: {
				generated_at: '2026-03-14T10:00:00',
				user: 'staff@example.com',
				employee: null,
				can_manage_audiences: false,
			},
			filters: { organization: 'ORG-1', school: 'SCH-1', audience: 'Staff' },
			options: {
				organizations: ['ORG-1'],
				schools: ['SCH-1'],
				audiences: ['Staff'],
			},
			counts: makeCounts({
				total_policies: 2,
				staff_policies: 2,
				school_scoped: 2,
				signature_required: 1,
				informational: 1,
				pending: 1,
			}),
			rows: [
				{
					institutional_policy: 'POL-INFO',
					policy_version: 'VER-INFO',
					policy_title: 'Campus Conduct Handbook',
					policy_category: 'Handbooks',
					version_label: 'v1',
					description: 'Informational policy',
					policy_organization: 'ORG-1',
					policy_school: 'SCH-1',
					applies_to_tokens: ['Staff'],
					signature_required: false,
					acknowledgement_status: 'informational',
				},
				{
					institutional_policy: 'POL-SIGN',
					policy_version: 'VER-SIGN',
					policy_title: 'Staff Data Handling',
					policy_category: 'Employment',
					version_label: 'v3',
					description: 'Signature policy',
					policy_organization: 'ORG-1',
					policy_school: 'SCH-1',
					applies_to_tokens: ['Staff'],
					signature_required: true,
					acknowledgement_status: 'pending',
				},
			],
		});

		mountStaffPolicies();
		await flushUi();

		const text = document.body.textContent || '';
		expect(getPolicyLibraryMock).toHaveBeenCalledTimes(1);
		expect(text).toContain('Policy Library');
		expect(text).toContain('Campus Conduct Handbook');
		expect(text).toContain('Informational');
		expect(text).toContain('Staff Data Handling');
		expect(text).toContain('Signature pending');
		expect(text).not.toContain('Open acknowledgement tracking');
		expect(text).not.toContain('All schools');
	});

	it('renders cross-audience browsing controls for admin scope', async () => {
		getStaffHomeHeaderMock.mockResolvedValue({
			user: 'admin@example.com',
			capabilities: { analytics_policy_signatures: false },
		});
		getPolicyLibraryMock.mockResolvedValue({
			meta: {
				generated_at: '2026-03-14T10:00:00',
				user: 'admin@example.com',
				employee: null,
				can_manage_audiences: true,
			},
			filters: { organization: 'ORG-1', school: '', audience: 'All' },
			options: {
				organizations: ['ORG-1'],
				schools: ['SCH-1'],
				audiences: ['All', 'Staff', 'Guardian', 'Student'],
			},
			counts: makeCounts({
				total_policies: 1,
				guardian_policies: 1,
				organization_scoped: 1,
			}),
			rows: [
				{
					institutional_policy: 'POL-GRD',
					policy_version: 'VER-GRD',
					policy_title: 'Guardian Handbook',
					policy_category: 'Handbooks',
					description: 'Guardian policy',
					policy_organization: 'ORG-1',
					applies_to_tokens: ['Guardian'],
					signature_required: null,
					acknowledgement_status: null,
				},
			],
		});

		mountStaffPolicies();
		await flushUi();

		const text = document.body.textContent || '';
		expect(text).toContain('Policy Library');
		expect(text).toContain('All schools');
		expect(text).toContain('All audiences');
		expect(text).toContain('Guardian Handbook');
		expect(text).toContain('Guardians');
		expect(text).toContain('Guardian Portal');
	});

	it('opens the policy inform overlay when a row action is clicked', async () => {
		getStaffHomeHeaderMock.mockResolvedValue({
			user: 'staff@example.com',
			capabilities: { analytics_policy_signatures: false },
		});
		getPolicyLibraryMock.mockResolvedValue({
			meta: {
				generated_at: '2026-03-14T10:00:00',
				user: 'staff@example.com',
				employee: null,
				can_manage_audiences: false,
			},
			filters: { organization: 'ORG-1', school: 'SCH-1', audience: 'Staff' },
			options: {
				organizations: ['ORG-1'],
				schools: ['SCH-1'],
				audiences: ['Staff'],
			},
			counts: makeCounts({ total_policies: 1, staff_policies: 1, school_scoped: 1, informational: 1 }),
			rows: [
				{
					institutional_policy: 'POL-INFO',
					policy_version: 'VER-INFO',
					policy_title: 'Campus Conduct Handbook',
					policy_category: 'Handbooks',
					description: 'Informational policy',
					applies_to_tokens: ['Staff'],
					signature_required: false,
					acknowledgement_status: 'informational',
				},
			],
		});

		mountStaffPolicies();
		await flushUi();

		const openButton = Array.from(document.querySelectorAll('button')).find(button =>
			(button.textContent || '').includes('Open policy')
		);
		openButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
		await flushUi();

		expect(overlayOpenMock).toHaveBeenCalledWith('staff-policy-inform', { policyVersion: 'VER-INFO' });
	});

	it('opens acknowledgement tracking with the current library scope', async () => {
		getStaffHomeHeaderMock.mockResolvedValue({
			user: 'staff@example.com',
			capabilities: { analytics_policy_signatures: true },
		});
		getPolicyLibraryMock.mockResolvedValue({
			meta: {
				generated_at: '2026-03-14T10:00:00',
				user: 'staff@example.com',
				employee: null,
				can_manage_audiences: false,
			},
			filters: { organization: 'ORG-1', school: 'SCH-1', audience: 'Staff' },
			options: {
				organizations: ['ORG-1'],
				schools: ['SCH-1'],
				audiences: ['Staff'],
			},
			counts: makeCounts({
				total_policies: 1,
				staff_policies: 1,
				school_scoped: 1,
				signature_required: 1,
				pending: 1,
			}),
			rows: [
				{
					institutional_policy: 'POL-SIGN',
					policy_version: 'VER-SIGN',
					policy_title: 'Staff Data Handling',
					policy_category: 'Employment',
					version_label: 'v3',
					description: 'Signature policy',
					policy_organization: 'ORG-1',
					policy_school: 'SCH-1',
					applies_to_tokens: ['Staff'],
					signature_required: true,
					acknowledgement_status: 'pending',
				},
			],
		});

		mountStaffPolicies();
		await flushUi();

		const trackingButton = Array.from(document.querySelectorAll('button')).find(button =>
			(button.textContent || '').includes('Open acknowledgement tracking')
		);
		trackingButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
		await flushUi();

		expect(routerPushMock).toHaveBeenCalledWith({
			name: 'staff-policy-signature-analytics',
			query: {
				policy_version: 'VER-SIGN',
				organization: 'ORG-1',
				school: 'SCH-1',
			},
		});
	});
});
