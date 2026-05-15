// Copyright (c) 2026, François de Ryckel and contributors
// For license information, please see license.txt

frappe.listview_settings["Unit Plan"] = {
	onload(listview) {
		install_program_subtree_filter(listview);
	},

	refresh(listview) {
		prime_selected_program_scope(listview);
	},
};

function install_program_subtree_filter(listview) {
	if (listview.__program_subtree_filter_installed) return;

	listview.__program_scope_cache = Object.create(null);
	listview.__program_scope_pending = Object.create(null);

	if (typeof listview.get_args === "function") {
		const originalGetArgs = listview.get_args.bind(listview);
		listview.get_args = function () {
			const args = originalGetArgs();
			args.filters = rewrite_program_filters(args.filters || [], this);
			return args;
		};
	}

	listview.__program_subtree_filter_installed = true;
}

function rewrite_program_filters(filters, listview) {
	if (!Array.isArray(filters)) return filters;

	return filters.map((filter) => {
		const parsed = parse_program_filter(filter);
		if (!parsed) return filter;

		const scope = listview.__program_scope_cache?.[parsed.value];
		if (!Array.isArray(scope) || !scope.length) return filter;

		if (Array.isArray(filter)) {
			if (filter.length >= 4) {
				return [filter[0], filter[1], "in", scope];
			}
			return ["program", "in", scope];
		}

		if (filter && typeof filter === "object") {
			return { ...filter, operator: "in", value: scope };
		}

		return filter;
	});
}

function parse_program_filter(filter) {
	if (Array.isArray(filter)) {
		if (filter.length >= 4) {
			const fieldname = filter[1];
			const operator = filter[2];
			const value = filter[3];
			if (fieldname === "program" && operator === "=" && typeof value === "string" && value.trim()) {
				return { value: value.trim() };
			}
		}

		if (filter.length === 3) {
			const fieldname = filter[0];
			const operator = filter[1];
			const value = filter[2];
			if (fieldname === "program" && operator === "=" && typeof value === "string" && value.trim()) {
				return { value: value.trim() };
			}
		}
	}

	if (filter && typeof filter === "object") {
		const fieldname = filter.fieldname || filter.field || filter[1];
		const operator = filter.operator || filter.condition;
		const value = filter.value;
		if (fieldname === "program" && operator === "=" && typeof value === "string" && value.trim()) {
			return { value: value.trim() };
		}
	}

	return null;
}

function prime_selected_program_scope(listview) {
	const selectedPrograms = get_selected_exact_program_filters(listview);
	selectedPrograms.forEach((program) => ensure_program_scope(listview, program));
}

function get_selected_exact_program_filters(listview) {
	const filters = listview.filter_area && typeof listview.filter_area.get === "function"
		? listview.filter_area.get()
		: [];

	const programs = [];
	for (const filter of filters || []) {
		const parsed = parse_program_filter(filter);
		if (parsed?.value) {
			programs.push(parsed.value);
		}
	}
	return programs;
}

function ensure_program_scope(listview, program) {
	if (!program) return;
	if (Array.isArray(listview.__program_scope_cache?.[program])) return;
	if (listview.__program_scope_pending?.[program]) return;

	listview.__program_scope_pending[program] = true;

	frappe.call({
		method: "ifitwala_ed.curriculum.doctype.unit_plan.unit_plan.get_program_subtree_scope",
		args: { program },
		callback: (response) => {
			const scope = Array.isArray(response.message) && response.message.length ? response.message : [program];
			listview.__program_scope_cache[program] = scope;
			delete listview.__program_scope_pending[program];

			if (get_selected_exact_program_filters(listview).includes(program)) {
				listview.refresh();
			}
		},
		error: () => {
			delete listview.__program_scope_pending[program];
		},
	});
}
