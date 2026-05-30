// Keep Program Billing Plan List view aligned with Report view.
//
// Frappe v16 adds a title join for Program Offering because that target DocType
// has show_title_field_in_link enabled. The joined title is cosmetic here, while
// the target DocType's scoped permission condition can make List view reference
// the target table by its unaliased name.

const GET_PROGRAM_OFFERING_TITLE_MAP =
	'ifitwala_ed.accounting.doctype.program_billing_plan.program_billing_plan.get_program_offering_title_map_for_billing_plans';
const PROGRAM_BILLING_PLAN_TITLE_CACHE = Object.create(null);

frappe.listview_settings['Program Billing Plan'] = {
	onload(listview) {
		strip_program_billing_plan_title_joins(listview);
	},
	refresh(listview) {
		strip_program_billing_plan_title_joins(listview);
		hydrate_program_offering_titles(listview);
	},
	formatters: {
		program_offering(value, _df, doc) {
			return format_program_offering_link(value, get_program_offering_title(doc));
		},
	},
};

function strip_program_billing_plan_title_joins(listview) {
	if (!listview || listview.__program_billing_plan_title_joins_stripped) return;

	const blocked_fields = new Set([
		'program_offering.offering_title as program_offering_offering_title',
	]);
	const original_get_fields = listview.get_fields.bind(listview);
	listview.get_fields = function () {
		return original_get_fields().filter(field => !blocked_fields.has(field));
	};

	if (listview.link_field_title_fields) {
		delete listview.link_field_title_fields.program_offering;
	}

	listview.__program_billing_plan_title_joins_stripped = true;
}

function hydrate_program_offering_titles(listview) {
	const rows = Array.isArray(listview?.data) ? listview.data : [];
	const missingPlanNames = rows
		.filter(row => {
			const planName = clean_string(row?.name);
			const programOffering = clean_string(row?.program_offering);
			if (!planName || !programOffering) return false;
			const cached = PROGRAM_BILLING_PLAN_TITLE_CACHE[planName];
			return !cached || cached.program_offering !== programOffering;
		})
		.map(row => row.name);

	if (!missingPlanNames.length) return;

	frappe.call({
		method: GET_PROGRAM_OFFERING_TITLE_MAP,
		args: { program_billing_plans: missingPlanNames },
		callback: response => {
			const titleMap = response?.message || {};
			Object.entries(titleMap).forEach(([planName, entry]) => {
				PROGRAM_BILLING_PLAN_TITLE_CACHE[planName] = {
					program_offering: clean_string(entry?.program_offering),
					offering_title: clean_string(entry?.offering_title),
				};
			});

			rows.forEach(row => {
				const title = get_program_offering_title(row);
				if (title) {
					row.program_offering_offering_title = title;
				}
			});
			rerender_program_billing_plan_list(listview);
		},
	});
}

function get_program_offering_title(doc) {
	const planName = clean_string(doc?.name);
	const programOffering = clean_string(doc?.program_offering);
	const cached = planName ? PROGRAM_BILLING_PLAN_TITLE_CACHE[planName] : null;
	if (cached && cached.program_offering === programOffering) {
		return cached.offering_title;
	}
	return clean_string(doc?.program_offering_offering_title);
}

function rerender_program_billing_plan_list(listview) {
	if (typeof listview?.render === 'function') {
		listview.render();
		return;
	}

	if (typeof listview?.refresh !== 'function' || listview.__program_billing_plan_title_refreshing)
		return;

	listview.__program_billing_plan_title_refreshing = true;
	listview.refresh();
	setTimeout(() => {
		listview.__program_billing_plan_title_refreshing = false;
	}, 0);
}

function format_program_offering_link(value, title) {
	const programOffering = clean_string(value);
	if (!programOffering) return '';

	const label = clean_string(title) || programOffering;
	const escapedLabel = frappe.utils.escape_html(label);
	const escapedTitle = frappe.utils.escape_html(programOffering);
	const route = `/app/program-offering/${encodeURIComponent(programOffering)}`;
	return `<a href="${route}" title="${escapedTitle}">${escapedLabel}</a>`;
}

function clean_string(value) {
	return String(value || '').trim();
}
