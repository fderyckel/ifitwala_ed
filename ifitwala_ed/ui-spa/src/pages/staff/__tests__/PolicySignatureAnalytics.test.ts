import { afterEach, describe, expect, it, vi } from 'vitest';
import { createApp, defineComponent, h, nextTick, type App } from 'vue';

const {
	getCampaignOptionsMock,
	getDashboardMock,
	getAudienceRowsMock,
	getStaffHomeHeaderMock,
	overlayOpenMock,
	routeQueryMock,
} = vi.hoisted(() => ({
	getCampaignOptionsMock: vi.fn(),
	getDashboardMock: vi.fn(),
	getAudienceRowsMock: vi.fn(),
	getStaffHomeHeaderMock: vi.fn(),
	overlayOpenMock: vi.fn(),
	routeQueryMock: {
		organization: 'ORG-1',
		school: 'SCH-1',
		employee_group: 'GROUP-1',
		policy_version: 'VER-1',
	},
}));

vi.mock('@/lib/services/policySignature/policySignatureService', () => ({
	createPolicySignatureService: () => ({
		getCampaignOptions: getCampaignOptionsMock,
		getDashboard: getDashboardMock,
		getAudienceRows: getAudienceRowsMock,
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
		query: routeQueryMock,
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
	getAudienceRowsMock.mockReset();
	getStaffHomeHeaderMock.mockReset();
	overlayOpenMock.mockReset();
	Object.assign(routeQueryMock, {
		organization: 'ORG-1',
		school: 'SCH-1',
		employee_group: 'GROUP-1',
		policy_version: 'VER-1',
	});
	vi.useRealTimers();
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

	it('reloads dependent school and policy options when organization and school change', async () => {
		vi.useFakeTimers();

		getStaffHomeHeaderMock.mockResolvedValue({
			user: 'admin@example.com',
			capabilities: { manage_policy_signatures: true },
		});
		getCampaignOptionsMock.mockImplementation(async (payload?: Record<string, unknown>) => {
			const organization = String(payload?.organization || '');
			const school = String(payload?.school || '');

			if (organization === 'ORG-1') {
				return {
					options: {
						organizations: ['ORG-1', 'ORG-2'],
						schools: ['SCH-1'],
						employee_groups: ['GROUP-1'],
						policies: [
							{
								policy_version: 'VER-1',
								policy_title: 'Community Handbook',
								version_label: 'v1',
								applies_to_tokens: ['Staff'],
							},
						],
					},
					preview: {
						target_employee_rows: 0,
						eligible_users: 0,
						already_signed: 0,
						already_open: 0,
						to_create: 0,
						skipped_scope: 0,
						policy_audiences: ['Staff'],
						audience_previews: [],
					},
				};
			}

			if (organization === 'ORG-2' && !school) {
				return {
					options: {
						organizations: ['ORG-1', 'ORG-2'],
						schools: ['SCH-2A', 'SCH-2B'],
						employee_groups: ['GROUP-2'],
						policies: [
							{
								policy_version: 'VER-2-ORG',
								policy_title: 'Org Two Handbook',
								version_label: 'v4',
								applies_to_tokens: ['Staff'],
							},
						],
					},
					preview: {
						target_employee_rows: 0,
						eligible_users: 0,
						already_signed: 0,
						already_open: 0,
						to_create: 0,
						skipped_scope: 0,
						policy_audiences: ['Staff'],
						audience_previews: [],
					},
				};
			}

			if (organization === 'ORG-2' && school === 'SCH-2A') {
				return {
					options: {
						organizations: ['ORG-1', 'ORG-2'],
						schools: ['SCH-2A', 'SCH-2B'],
						employee_groups: ['GROUP-2A'],
						policies: [
							{
								policy_version: 'VER-2-ORG',
								policy_title: 'Org Two Handbook',
								version_label: 'v4',
								applies_to_tokens: ['Staff'],
							},
							{
								policy_version: 'VER-2A',
								policy_title: 'School Two A Safeguarding',
								version_label: 'v1',
								applies_to_tokens: ['Staff'],
							},
						],
					},
					preview: {
						target_employee_rows: 0,
						eligible_users: 0,
						already_signed: 0,
						already_open: 0,
						to_create: 0,
						skipped_scope: 0,
						policy_audiences: ['Staff'],
						audience_previews: [],
					},
				};
			}

			throw new Error(`Unexpected campaign options payload: ${JSON.stringify(payload)}`);
		});
		getDashboardMock.mockResolvedValue({
			summary: {
				policy_version: 'VER-1',
				policy_title: 'Community Handbook',
				version_label: 'v1',
				organization: 'ORG-1',
				school: 'SCH-1',
				employee_group: 'GROUP-1',
				applies_to_tokens: ['Staff'],
				eligible_targets: 0,
				signed: 0,
				pending: 0,
				completion_pct: 0,
				skipped_scope: 0,
			},
			audiences: [],
		});

		mountAnalyticsPage();
		await flushUi();
		await flushUi();

		const selects = Array.from(document.querySelectorAll('select')) as HTMLSelectElement[];
		const [organizationSelect, schoolSelect, _groupSelect, policySelect] = selects;

		organizationSelect.value = 'ORG-2';
		organizationSelect.dispatchEvent(new Event('change', { bubbles: true }));
		await flushUi();
		await vi.advanceTimersByTimeAsync(250);
		await flushUi();
		await flushUi();

		expect(getCampaignOptionsMock).toHaveBeenLastCalledWith({
			organization: 'ORG-2',
			school: null,
			employee_group: null,
			policy_version: 'VER-1',
		});
		expect(Array.from(schoolSelect.options).map(option => option.value)).toEqual(['', 'SCH-2A', 'SCH-2B']);
		expect(Array.from(policySelect.options).map(option => option.value)).toEqual(['', 'VER-2-ORG']);
		expect(policySelect.value).toBe('');

		schoolSelect.value = 'SCH-2A';
		schoolSelect.dispatchEvent(new Event('change', { bubbles: true }));
		await flushUi();
		await vi.advanceTimersByTimeAsync(250);
		await flushUi();
		await flushUi();

		expect(getCampaignOptionsMock).toHaveBeenLastCalledWith({
			organization: 'ORG-2',
			school: 'SCH-2A',
			employee_group: null,
			policy_version: null,
		});
		expect(Array.from(policySelect.options).map(option => option.value)).toEqual([
			'',
			'VER-2-ORG',
			'VER-2A',
		]);
	});

	it('opens the searchable audience register and fetches paginated guardian rows on demand', async () => {
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
						applies_to_tokens: ['Guardian'],
					},
				],
			},
			preview: {
				target_employee_rows: 0,
				eligible_users: 0,
				already_signed: 0,
				already_open: 0,
				to_create: 0,
				skipped_scope: 0,
				policy_audiences: ['Guardian'],
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
				applies_to_tokens: ['Guardian'],
				eligible_targets: 42,
				signed: 21,
				pending: 21,
				completion_pct: 50,
				skipped_scope: 0,
			},
			audiences: [
				{
					audience: 'Guardian',
					audience_label: 'Guardians',
					workflow_description: 'Guardians acknowledge this policy in Guardian Portal; no staff tasks are created.',
					supports_campaign_launch: false,
					summary: {
						target_rows: 42,
						eligible_targets: 42,
						signed: 21,
						pending: 21,
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
						pending: [],
						signed: [],
					},
				},
			],
		});
		getAudienceRowsMock
			.mockResolvedValueOnce({
				audience: 'Guardian',
				audience_label: 'Guardians',
				workflow_description:
					'Guardians acknowledge this policy in Guardian Portal; no staff tasks are created.',
				supports_campaign_launch: false,
				status: 'all',
				query: null,
				rows: [
					{
						record_id: 'GRD-1',
						subject_name: 'Guardian One',
						subject_subtitle: 'guardian-one@example.com',
						context_label: 'Linked students: Student One',
						organization: 'ORG-1',
						school: 'SCH-1',
						is_signed: true,
						acknowledged_at: '2026-04-15 08:30:00',
						acknowledged_by: 'guardian1@example.com',
					},
				],
				pagination: {
					page: 1,
					limit: 25,
					total_rows: 42,
					total_pages: 2,
				},
			})
			.mockResolvedValueOnce({
				audience: 'Guardian',
				audience_label: 'Guardians',
				workflow_description:
					'Guardians acknowledge this policy in Guardian Portal; no staff tasks are created.',
				supports_campaign_launch: false,
				status: 'all',
				query: 'guardian two',
				rows: [
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
				pagination: {
					page: 1,
					limit: 25,
					total_rows: 1,
					total_pages: 1,
				},
			})
			.mockResolvedValueOnce({
				audience: 'Guardian',
				audience_label: 'Guardians',
				workflow_description:
					'Guardians acknowledge this policy in Guardian Portal; no staff tasks are created.',
				supports_campaign_launch: false,
				status: 'signed',
				query: 'guardian two',
				rows: [],
				pagination: {
					page: 1,
					limit: 25,
					total_rows: 0,
					total_pages: 1,
				},
			});

		mountAnalyticsPage();
		await flushUi();
		await flushUi();

		const openRegisterButton = Array.from(document.querySelectorAll('button')).find(button =>
			(button.textContent || '').includes('Open searchable register')
		);
		openRegisterButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
		await flushUi();
		await flushUi();

		expect(getAudienceRowsMock).toHaveBeenCalledWith({
			policy_version: 'VER-1',
			audience: 'Guardian',
			organization: 'ORG-1',
			school: 'SCH-1',
			employee_group: 'GROUP-1',
			status: 'all',
			query: null,
			page: 1,
			limit: 25,
		});

		const searchInput = document.querySelector('input[type="search"]') as HTMLInputElement;
		searchInput.value = 'guardian two';
		searchInput.dispatchEvent(new Event('input', { bubbles: true }));
		searchInput.dispatchEvent(new KeyboardEvent('keyup', { key: 'Enter', bubbles: true }));
		await flushUi();
		await flushUi();

		expect(getAudienceRowsMock).toHaveBeenLastCalledWith({
			policy_version: 'VER-1',
			audience: 'Guardian',
			organization: 'ORG-1',
			school: 'SCH-1',
			employee_group: 'GROUP-1',
			status: 'all',
			query: 'guardian two',
			page: 1,
			limit: 25,
		});

		const signedButton = Array.from(document.querySelectorAll('button')).find(button =>
			(button.textContent || '').trim() === 'Signed'
		);
		signedButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
		await flushUi();
		await flushUi();

		expect(getAudienceRowsMock).toHaveBeenLastCalledWith({
			policy_version: 'VER-1',
			audience: 'Guardian',
			organization: 'ORG-1',
			school: 'SCH-1',
			employee_group: 'GROUP-1',
			status: 'signed',
			query: 'guardian two',
			page: 1,
			limit: 25,
		});
		expect(document.body.textContent || '').toContain('No people matched this search');
	});
});
