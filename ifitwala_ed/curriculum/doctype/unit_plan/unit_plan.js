frappe.ui.form.on("Unit Plan", {
	refresh(frm) {
		if (!frm.custom_buttons[__("Select Learning Standards")]) {
			frm.add_custom_button(__("Select Learning Standards"), () => openLearningStandardsPicker(frm), __("Actions"));
		}
	},
});

function openLearningStandardsPicker(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("Select Learning Standards"),
		size: "extra-large",
		fields: [
			{
				fieldname: "intro_html",
				fieldtype: "HTML",
			},
			{
				fieldname: "framework_name",
				fieldtype: "Select",
				label: __("Framework"),
				options: [""],
			},
			{
				fieldname: "program",
				fieldtype: "Select",
				label: __("Program"),
				options: [""],
			},
			{
				fieldname: "strand",
				fieldtype: "Select",
				label: __("Strand"),
				options: [""],
			},
			{
				fieldname: "substrand",
				fieldtype: "Select",
				label: __("Substrand"),
				options: [""],
			},
			{
				fieldname: "search_text",
				fieldtype: "Data",
				label: __("Search Standards"),
				description: __("Search by standard code or description."),
			},
			{
				fieldname: "selection_html",
				fieldtype: "HTML",
			},
		],
		primary_action_label: __("Add Selected"),
		primary_action: () => addSelectedStandards(frm, dialog),
	});

	const state = {
		loading: false,
		selectedStandards: new Map(),
		currentStandards: [],
		searchTimer: null,
	};
	dialog._learningStandardsState = state;
	dialog._unitPlanForm = frm;

	dialog.fields_dict.intro_html.$wrapper.html(`
		<div class="text-muted small" style="margin-bottom: 0.75rem;">
			${frappe.utils.escape_html(__("Choose standards from the approved catalog. The unit keeps a validated snapshot, so teachers cannot invent standards or create taxonomy typos."))}
		</div>
	`);

	const scheduleRefresh = () => {
		window.clearTimeout(state.searchTimer);
		state.searchTimer = window.setTimeout(() => refreshLearningStandardsPicker(frm, dialog), 180);
	};

	["framework_name", "program", "strand", "substrand"].forEach((fieldname) => {
		dialog.fields_dict[fieldname].df.onchange = () => refreshLearningStandardsPicker(frm, dialog);
	});
	dialog.fields_dict.search_text.$input.on("input", scheduleRefresh);

	dialog.show();
	refreshLearningStandardsPicker(frm, dialog);
}

async function refreshLearningStandardsPicker(frm, dialog) {
	const state = dialog._learningStandardsState;
	if (!state) {
		return;
	}

	const filters = getPickerFilters(dialog);
	state.loading = true;
	renderLearningStandards(dialog, { loading: true, standards: [] });

	try {
		const response = await frappe.call({
			method: "ifitwala_ed.curriculum.doctype.unit_plan.unit_plan.get_learning_standard_picker",
			args: filters,
		});
		const payload = response.message || {};
		const options = payload.options || {};
		const standards = payload.standards || [];

		state.currentStandards = standards;
		syncPickerSelect(dialog, "framework_name", options.frameworks || [], __("Select framework"));
		syncPickerSelect(dialog, "program", options.programs || [], __("Select program"));
		syncPickerSelect(dialog, "strand", options.strands || [], __("Select strand"));
		syncPickerSelect(
			dialog,
			"substrand",
			buildSubstrandOptions(options.substrands || [], options.has_blank_substrand),
			__("Select substrand"),
		);
		if (applyPickerAutoSelect(dialog, options)) {
			return;
		}
		togglePickerField(dialog, "framework_name", (options.frameworks || []).length > 1);
		togglePickerField(dialog, "program", Boolean(getPickerValue(dialog, "framework_name")) || (options.frameworks || []).length <= 1);
		togglePickerField(dialog, "strand", Boolean(getPickerValue(dialog, "program")) || (options.programs || []).length <= 1);
		togglePickerField(
			dialog,
			"substrand",
			Boolean(getPickerValue(dialog, "strand")) && ((options.substrands || []).length > 0 || options.has_blank_substrand),
		);
		renderLearningStandards(dialog, {
			loading: false,
			standards,
			needsStrand: !getPickerValue(dialog, "strand"),
			needsSubstrand:
				Boolean(getPickerValue(dialog, "strand")) &&
				((options.substrands || []).length > 0 || options.has_blank_substrand) &&
				!getPickerValue(dialog, "substrand"),
			substrandOptions: options.substrands || [],
			hasBlankSubstrand: options.has_blank_substrand,
			existingStandards: new Set(
				(frm.doc.standards || [])
					.map((row) => row.learning_standard)
					.filter((value) => Boolean(value)),
			),
			selectedStandards: state.selectedStandards,
		});
	} catch (error) {
		renderLearningStandards(dialog, {
			loading: false,
			error: error?.message || __("Unable to load learning standards."),
			standards: [],
		});
	} finally {
		state.loading = false;
	}
}

function getPickerFilters(dialog) {
	return {
		framework_name: getPickerValue(dialog, "framework_name"),
		program: getPickerValue(dialog, "program"),
		strand: getPickerValue(dialog, "strand"),
		substrand: getPickerValue(dialog, "substrand"),
		search_text: getPickerValue(dialog, "search_text"),
	};
}

function getPickerValue(dialog, fieldname) {
	return (dialog.get_value(fieldname) || "").trim();
}

function syncPickerSelect(dialog, fieldname, values, placeholder) {
	const field = dialog.fields_dict[fieldname];
	if (!field) {
		return;
	}
	const currentValue = getPickerValue(dialog, fieldname);
	const options = [""].concat(values || []);
	field.df.description = placeholder;
	field.df.options = options.join("\n");
	field.refresh();
	if (currentValue && !options.includes(currentValue)) {
		dialog.set_value(fieldname, "");
	}
}

function buildSubstrandOptions(values, hasBlankSubstrand) {
	const options = [...values];
	if (hasBlankSubstrand) {
		options.unshift("[No Substrand]");
	}
	return options;
}

function togglePickerField(dialog, fieldname, shouldShow) {
	dialog.set_df_property(fieldname, "hidden", shouldShow ? 0 : 1);
}

function applyPickerAutoSelect(dialog, options) {
	if ((options.frameworks || []).length === 1 && !getPickerValue(dialog, "framework_name")) {
		dialog.set_value("framework_name", options.frameworks[0]);
		refreshLearningStandardsPicker(dialog._unitPlanForm, dialog);
		return true;
	}
	if ((options.programs || []).length === 1 && !getPickerValue(dialog, "program")) {
		dialog.set_value("program", options.programs[0]);
		refreshLearningStandardsPicker(dialog._unitPlanForm, dialog);
		return true;
	}
	if ((options.strands || []).length === 1 && !getPickerValue(dialog, "strand")) {
		dialog.set_value("strand", options.strands[0]);
		refreshLearningStandardsPicker(dialog._unitPlanForm, dialog);
		return true;
	}
	if (
		(options.substrands || []).length === 1 &&
		!options.has_blank_substrand &&
		!getPickerValue(dialog, "substrand")
	) {
		dialog.set_value("substrand", options.substrands[0]);
		refreshLearningStandardsPicker(dialog._unitPlanForm, dialog);
		return true;
	}
	return false;
}

function renderLearningStandards(dialog, context) {
	const wrapper = dialog.fields_dict.selection_html?.$wrapper;
	if (!wrapper) {
		return;
	}
	if (context.loading) {
		wrapper.html(`<div class="text-muted small">${frappe.utils.escape_html(__("Loading learning standards..."))}</div>`);
		return;
	}
	if (context.error) {
		wrapper.html(`<div class="text-danger small">${frappe.utils.escape_html(context.error)}</div>`);
		return;
	}
	if (context.needsStrand) {
		wrapper.html(`<div class="text-muted small">${frappe.utils.escape_html(__("Choose a strand to see matching standards."))}</div>`);
		return;
	}
	if (context.needsSubstrand) {
		wrapper.html(`<div class="text-muted small">${frappe.utils.escape_html(__("Choose a substrand to narrow the standards list."))}</div>`);
		return;
	}
	if (!(context.standards || []).length) {
		wrapper.html(`<div class="text-muted small">${frappe.utils.escape_html(__("No learning standards match this selection."))}</div>`);
		return;
	}

	const existingStandards = context.existingStandards || new Set();
	const selectedStandards = context.selectedStandards || new Map();
	const cards = context.standards
		.map((standard) => {
			const learningStandard = standard.learning_standard;
			const isExisting = existingStandards.has(learningStandard);
			const isSelected = selectedStandards.has(learningStandard);
			const meta = [
				standard.framework_name,
				standard.program,
				standard.strand,
				standard.substrand || (context.hasBlankSubstrand ? __("No Substrand") : ""),
			]
				.filter(Boolean)
				.join(" • ");
			return `
				<label class="learning-standard-card" style="display:block;border:1px solid var(--border-color);border-radius:16px;padding:12px 14px;margin-bottom:10px;background:${isExisting ? "#f7f7f7" : "white"};opacity:${isExisting ? "0.72" : "1"};">
					<div style="display:flex;gap:12px;align-items:flex-start;">
						<input type="checkbox" data-learning-standard="${frappe.utils.escape_html(learningStandard || "")}" ${isExisting ? "disabled" : ""} ${isSelected ? "checked" : ""} style="margin-top:4px;" />
						<div style="min-width:0;">
							<div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
								<strong>${frappe.utils.escape_html(standard.standard_code || __("Standard"))}</strong>
								${standard.alignment_type ? `<span class="text-muted small">${frappe.utils.escape_html(standard.alignment_type)}</span>` : ""}
								${isExisting ? `<span class="text-success small">${frappe.utils.escape_html(__("Already added"))}</span>` : ""}
							</div>
							<div class="text-muted small" style="margin-top:4px;">${frappe.utils.escape_html(standard.standard_description || __("No description"))}</div>
							${meta ? `<div class="text-muted small" style="margin-top:6px;">${frappe.utils.escape_html(meta)}</div>` : ""}
						</div>
					</div>
				</label>
			`;
		})
		.join("");

	wrapper.html(`
		<div class="small text-muted" style="margin-bottom:10px;">
			${frappe.utils.escape_html(__("Tick the standards that apply to this unit. The system will copy the approved catalog metadata into the alignment rows and keep only unit-specific judgment fields editable."))}
		</div>
		<div style="max-height:28rem;overflow:auto;padding-right:4px;">
			${cards}
		</div>
	`);

	wrapper.find("input[type='checkbox']").on("change", function () {
		const learningStandard = this.dataset.learningStandard;
		if (!learningStandard) {
			return;
		}
		const standard = (context.standards || []).find((row) => row.learning_standard === learningStandard);
		if (!standard) {
			return;
		}
		if (this.checked) {
			selectedStandards.set(learningStandard, standard);
		} else {
			selectedStandards.delete(learningStandard);
		}
	});
}

function addSelectedStandards(frm, dialog) {
	const state = dialog._learningStandardsState;
	if (!state) {
		return;
	}
	const selectedRows = Array.from(state.selectedStandards.values());
	if (!selectedRows.length) {
		frappe.show_alert({ message: __("Choose at least one learning standard."), indicator: "orange" });
		return;
	}

	const existingStandards = new Set(
		(frm.doc.standards || [])
			.map((row) => row.learning_standard)
			.filter((value) => Boolean(value)),
	);
	let addedCount = 0;
	selectedRows.forEach((standard) => {
		if (!standard.learning_standard || existingStandards.has(standard.learning_standard)) {
			return;
		}
		const row = frm.add_child("standards");
		row.learning_standard = standard.learning_standard;
		row.framework_name = standard.framework_name || "";
		row.framework_version = standard.framework_version || "";
		row.subject_area = standard.subject_area || "";
		row.program = standard.program || "";
		row.strand = standard.strand || "";
		row.substrand = standard.substrand || "";
		row.standard_code = standard.standard_code || "";
		row.standard_description = standard.standard_description || "";
		row.alignment_type = standard.alignment_type || "";
		existingStandards.add(standard.learning_standard);
		addedCount += 1;
	});

	frm.refresh_field("standards");
	if (addedCount) {
		frm.dirty();
		frappe.show_alert({
			message: __("{0} learning standards added.", [addedCount]),
			indicator: "green",
		});
		dialog.hide();
		return;
	}

	frappe.show_alert({ message: __("All selected standards are already on this unit."), indicator: "blue" });
}
