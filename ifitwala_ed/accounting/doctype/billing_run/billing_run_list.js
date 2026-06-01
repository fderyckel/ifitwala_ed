// Keep Billing Run List view aligned with Report view.
//
// Frappe v16 adds a title join for Program Offering because that target DocType
// has show_title_field_in_link enabled. The joined title is cosmetic here, while
// the target DocType's scoped permission condition can make List view reference
// the target table by its unaliased name.

const GET_PROGRAM_OFFERING_TITLE_MAP =
	'ifitwala_ed.accounting.doctype.billing_run.billing_run.get_program_offering_title_map_for_billing_runs';
const BILLING_RUN_TITLE_CACHE = Object.create(null);

frappe.listview_settings['Billing Run'] = {
	onload(listview) {
		strip_billing_run_title_joins(listview);
	},
	refresh(listview) {
		strip_billing_run_title_joins(listview);
		hydrate_program_offering_titles(listview);
	},
	formatters: {
		program_offering(value, _df, doc) {
			return format_program_offering_link(value, get_program_offering_title(doc));
		},
	},
};

function strip_billing_run_title_joins(listview) {
	if (!listview || listview.__billing_run_title_joins_stripped) return;

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

	listview.__billing_run_title_joins_stripped = true;
}

function hydrate_program_offering_titles(listview) {
	const rows = Array.isArray(listview?.data) ? listview.data : [];
	const missingRunNames = rows
		.filter(row => {
			const runName = clean_string(row?.name);
			const programOffering = clean_string(row?.program_offering);
			if (!runName || !programOffering) return false;
			const cached = BILLING_RUN_TITLE_CACHE[runName];
			return !cached || cached.program_offering !== programOffering;
		})
		.map(row => row.name);

	if (!missingRunNames.length) return;

	frappe.call({
		method: GET_PROGRAM_OFFERING_TITLE_MAP,
		args: { billing_runs: missingRunNames },
		callback: response => {
			const titleMap = response?.message || {};
			Object.entries(titleMap).forEach(([runName, entry]) => {
				BILLING_RUN_TITLE_CACHE[runName] = {
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
			rerender_billing_run_list(listview);
		},
	});
}

function get_program_offering_title(doc) {
	const runName = clean_string(doc?.name);
	const programOffering = clean_string(doc?.program_offering);
	const cached = runName ? BILLING_RUN_TITLE_CACHE[runName] : null;
	if (cached && cached.program_offering === programOffering) {
		return cached.offering_title;
	}
	return clean_string(doc?.program_offering_offering_title);
}

function rerender_billing_run_list(listview) {
	if (typeof listview?.render === 'function') {
		listview.render();
		return;
	}

	if (typeof listview?.refresh !== 'function' || listview.__billing_run_title_refreshing)
		return;

	listview.__billing_run_title_refreshing = true;
	listview.refresh();
	setTimeout(() => {
		listview.__billing_run_title_refreshing = false;
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
