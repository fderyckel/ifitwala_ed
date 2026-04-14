import { afterEach, describe, expect, it, vi } from 'vitest';
import { createApp, defineComponent, h, nextTick, type App } from 'vue';

const {
	getCampaignOptionsMock,
	getDashboardMock,
	getStaffHomeHeaderMock,
	overlayOpenMock,
} = vi.hoisted(() => ({
	getCampaignOptionsMock: vi.fn(),
	getDashboardMock: vi.fn(),
	getStaffHomeHeaderMock: vi.fn(),
	overlayOpenMock: vi.fn(),
}));

vi.mock('@/lib/services/policySignature/policySignatureService', () => ({
	createPolicySignatureService: () => ({
		getCampaignOptions: getCampaignOptionsMock,
		getDashboard: getDashboardMock,
	}),
}));

vi.mock('@/lib/services/staff/staffHomeService', () => ({
	getStaffHomeHeader: getStaffHomeHeaderMock,
}));

vi.mock('@/composables/useOverlayStack', () => ({
	useOverlayStack: () => ({
		open: overlayOpenMock,
	}),
}));

vi.mock('vue-router', () => ({
	useRoute: () => ({
		query: {
			organization: 'ORG-1',
			school: 'SCH-1',
			employee_group: 'GROUP-1',
			policy_version: 'VER-1',
		},
	}),
}));

vi.mock('frappe-ui', () => ({
	FeatherIcon: defineComponent({
		name: 'FeatherIconStub',
		props: { name: { type: String, required: false } },
		setup(props) {
			return () => h('span', { 'data-feather': props.name || '' });
		},
	}),
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

import PolicySignatureAnalytics from '@/pages/staff/analytics/PolicySignatureAnalytics.vue';

const cleanupFns: Array<() => void> = [];

async function flushUi() {
	await Promise.resolve();
	await nextTick();
	await Promise.resolve();
	await nextTick();
}

function mountAnalyticsPage() {
	const host = document.createElement('div');
	document.body.appendChild(host);

	const app: App = createApp(
		defineComponent({
			render() {
				return h(PolicySignatureAnalytics);
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
	getCampaignOptionsMock.mockReset();
	getDashboardMock.mockReset();
	getStaffHomeHeaderMock.mockReset();
	overlayOpenMock.mockReset();
	while (cleanupFns.length) {
		cleanupFns.pop()?.();
	}
	document.body.innerHTML = '';
});

describe('PolicySignatureAnalytics', () => {
	it('renders mixed-audience acknowledgement sections and preserves context for campaign setup', async () => {
		getStaffHomeHeaderMock.mockResolvedValue({
			user: 'admin@example.com',
			capabilities: { manage_policy_signatures: true },
		});
		getCampaignOptionsMock.mockResolvedValue({
			options: {
				organizations: ['ORG-1'],
				schools: ['SCH-1'],
				employee_groups: ['GROUP-1'],
				policies: [
					{
						policy_version: 'VER-1',
						policy_title: 'Community Handbook',
						version_label: 'v1',
						applies_to_tokens: ['Staff', 'Guardian', 'Student'],
					},
				],
			},
			preview: {
				target_employee_rows: 2,
				eligible_users: 2,
				already_signed: 1,
				already_open: 0,
				to_create: 1,
				skipped_scope: 0,
				policy_audiences: ['Staff', 'Guardian', 'Student'],
				audience_previews: [],
			},
		});
		getDashboardMock.mockResolvedValue({
			summary: {
				policy_version: 'VER-1',
				policy_title: 'Community Handbook',
				version_label: 'v1',
				organization: 'ORG-1',
				school: 'SCH-1',
				employee_group: 'GROUP-1',
				applies_to_tokens: ['Staff', 'Guardian', 'Student'],
				eligible_targets: 6,
				signed: 3,
				pending: 3,
				completion_pct: 50,
				skipped_scope: 0,
			},
			audiences: [
				{
					audience: 'Staff',
					audience_label: 'Staff',
					workflow_description: 'Staff campaigns create internal signature tasks for eligible employees.',
					supports_campaign_launch: true,
					summary: {
						target_rows: 2,
						eligible_targets: 2,
						signed: 1,
						pending: 1,
						completion_pct: 50,
						skipped_scope: 0,
						already_open: 0,
						to_create: 1,
					},
					breakdowns: {
						by_organization: [],
						by_school: [],
						by_context: [],
						context_label: 'Employee Group',
					},
					rows: {
						pending: [],
						signed: [],
					},
				},
				{
					audience: 'Guardian',
					audience_label: 'Guardians',
					workflow_description: 'Guardians acknowledge this policy in Guardian Portal; no staff tasks are created.',
					supports_campaign_launch: false,
					summary: {
						target_rows: 2,
						eligible_targets: 2,
						signed: 1,
						pending: 1,
						completion_pct: 50,
						skipped_scope: 0,
						already_open: 0,
						to_create: 0,
					},
					breakdowns: {
						by_organization: [],
						by_school: [],
						by_context: [],
						context_label: 'Guardian Email',
					},
					rows: {
						pending: [
							{
								record_id: 'GRD-2',
								subject_name: 'Guardian Two',
								subject_subtitle: 'guardian-two@example.com',
								context_label: 'Linked students: Student Two',
								organization: 'ORG-1',
								school: 'SCH-1',
								is_signed: false,
							},
						],
						signed: [],
					},
				},
				{
					audience: 'Student',
					audience_label: 'Students',
					workflow_description: 'Students acknowledge this policy in Student Hub; no staff tasks are created.',
					supports_campaign_launch: false,
					summary: {
						target_rows: 2,
						eligible_targets: 2,
						signed: 1,
						pending: 1,
						completion_pct: 50,
						skipped_scope: 0,
						already_open: 0,
						to_create: 0,
					},
					breakdowns: {
						by_organization: [],
						by_school: [],
						by_context: [],
						context_label: 'Portal Email',
					},
					rows: {
						pending: [],
						signed: [],
					},
				},
			],
		});

		mountAnalyticsPage();
		await flushUi();
		await flushUi();

		const text = document.body.textContent || '';
		expect(text).toContain('Policy Signatures');
		expect(text).toContain('Community Handbook');
		expect(text).toContain('Guardians');
		expect(text).toContain('Students');
		expect(text).toContain('Portal tracking only');
		expect(text).toContain('Employee Group filtering narrows staff results only.');

		const setupButton = Array.from(document.querySelectorAll('button')).find(button =>
			(button.textContent || '').includes('Set up campaign')
		);
		setupButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
		await flushUi();

		expect(overlayOpenMock).toHaveBeenCalledWith('staff-policy-signature-campaign', {
			organization: 'ORG-1',
			school: 'SCH-1',
			employee_group: 'GROUP-1',
			policy_version: 'VER-1',
		});
	});
});
