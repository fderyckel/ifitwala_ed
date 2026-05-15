// ifitwala_ed/admission/doctype/recommendation_template/recommendation_template.js

frappe.ui.form.on("Recommendation Template", {
	refresh(frm) {
		frm.set_df_property(
			"target_document_type",
			"description",
			__(
				"Optional. If left empty, the system will auto-link or create a managed Recommendation Letter document type and notify you on save."
			)
		);

		frm.set_query("school", () => {
			if (!frm.doc.organization) {
				return { filters: { name: "" } };
			}
			return {
				query: "ifitwala_ed.admission.doctype.student_applicant.student_applicant.school_by_organization_query",
				filters: { organization: frm.doc.organization },
			};
		});

		frm.remove_custom_button(__("Add Section Header"));
		frm.remove_custom_button(__("Configure Likert Scale"));
		frm.add_custom_button(__("Add Section Header"), () => {
			open_section_header_dialog(frm);
		});
		frm.add_custom_button(__("Configure Likert Scale"), () => {
			open_likert_scale_dialog(frm);
		});
	},
});

function scrub_key(value) {
	return String(value || "")
		.trim()
		.toLowerCase()
		.replace(/[^a-z0-9]+/g, "_")
		.replace(/^_+|_+$/g, "")
		.slice(0, 80);
}

function parse_lines(value) {
	return String(value || "")
		.split("\n")
		.map((line) => line.trim())
		.filter(Boolean);
}

function keyed_entries_from_lines(value) {
	return parse_lines(value).map((label) => ({
		key: scrub_key(label),
		label,
	}));
}

function get_likert_rows(frm) {
	return (frm.doc.template_fields || []).filter((row) => row.field_type === "Likert Scale");
}

function parse_likert_config(row) {
	try {
		const parsed = JSON.parse(row?.options_json || "{}");
		if (parsed && Array.isArray(parsed.columns) && Array.isArray(parsed.rows)) {
			return parsed;
		}
	} catch {
		// Invalid existing config is handled by server validation on save.
	}
	return {
		columns: [
			{ key: "consistently", label: "Consistently" },
			{ key: "usually", label: "Usually" },
			{ key: "sometimes", label: "Sometimes" },
			{ key: "rarely", label: "Rarely" },
			{ key: "n_a", label: "N/A" },
		],
		rows: [],
	};
}

function render_likert_preview(columns, rows) {
	if (!columns.length || !rows.length) {
		return `<div class="text-muted">${frappe.utils.escape_html(
			__("Add scale options and skill rows to preview the matrix.")
		)}</div>`;
	}

	const header = columns
		.map((column) => `<th style="padding:6px 8px;text-align:center;">${frappe.utils.escape_html(column.label)}</th>`)
		.join("");
	const body = rows
		.map(
			(row) => `
				<tr>
					<td style="padding:6px 8px;font-weight:600;">${frappe.utils.escape_html(row.label)}</td>
					${columns
						.map(
							() =>
								`<td style="padding:6px 8px;text-align:center;color:#6b7280;">${frappe.utils.escape_html("[ ]")}</td>`
						)
						.join("")}
				</tr>
			`
		)
		.join("");

	return `
		<div style="overflow:auto;">
			<table class="table table-bordered" style="margin:0;min-width:520px;">
				<thead>
					<tr>
						<th style="padding:6px 8px;">${frappe.utils.escape_html(__("Skill / Attribute"))}</th>
						${header}
					</tr>
				</thead>
				<tbody>${body}</tbody>
			</table>
		</div>
	`;
}

function open_section_header_dialog(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("Add Section Header"),
		fields: [
			{
				fieldname: "label",
				fieldtype: "Data",
				label: __("Section Title"),
				reqd: 1,
			},
			{
				fieldname: "help_text",
				fieldtype: "Small Text",
				label: __("Supporting Text"),
			},
		],
		primary_action_label: __("Add"),
		primary_action(values) {
			const label = String(values.label || "").trim();
			if (!label) {
				frappe.msgprint(__("Section Title is required."));
				return;
			}
			const row = frm.add_child("template_fields");
			row.field_key = scrub_key(label);
			row.label = label;
			row.field_type = "Section Header";
			row.is_required = 0;
			row.help_text = String(values.help_text || "").trim();
			frm.refresh_field("template_fields");
			dialog.hide();
		},
	});
	dialog.show();
}

function open_likert_scale_dialog(frm) {
	const likertRows = get_likert_rows(frm);
	const rowOptions = [__("Create New Likert Scale")]
		.concat(likertRows.map((row) => `${row.field_key} - ${row.label}`))
		.join("\n");

	const dialog = new frappe.ui.Dialog({
		title: __("Configure Likert Scale"),
		fields: [
			{
				fieldname: "target",
				fieldtype: "Select",
				label: __("Likert Scale Field"),
				options: rowOptions,
				default: __("Create New Likert Scale"),
				change() {
					load_selected_likert_row();
				},
			},
			{
				fieldname: "label",
				fieldtype: "Data",
				label: __("Scale Title"),
				reqd: 1,
				default: __("Academic Skills"),
				change() {
					update_preview();
				},
			},
			{
				fieldname: "is_required",
				fieldtype: "Check",
				label: __("Require a response for every row"),
				default: 1,
			},
			{
				fieldname: "scale_options",
				fieldtype: "Small Text",
				label: __("Scale Options"),
				description: __("Enter one option per line. These become clickable columns for the recommender."),
				default: "Consistently\nUsually\nSometimes\nRarely\nN/A",
				reqd: 1,
				change() {
					update_preview();
				},
			},
			{
				fieldname: "attribute_rows",
				fieldtype: "Long Text",
				label: __("Skills / Attributes"),
				description: __("Enter one skill or attribute per line."),
				reqd: 1,
				change() {
					update_preview();
				},
			},
			{
				fieldname: "preview",
				fieldtype: "HTML",
				label: __("Preview"),
			},
		],
		primary_action_label: __("Apply"),
		primary_action(values) {
			const label = String(values.label || "").trim();
			const columns = keyed_entries_from_lines(values.scale_options);
			const rows = keyed_entries_from_lines(values.attribute_rows);

			if (!label) {
				frappe.msgprint(__("Scale Title is required."));
				return;
			}
			if (columns.length < 2) {
				frappe.msgprint(__("Add at least two scale options."));
				return;
			}
			if (!rows.length) {
				frappe.msgprint(__("Add at least one skill or attribute."));
				return;
			}

			const duplicateColumn = find_duplicate_key(columns);
			if (duplicateColumn) {
				frappe.msgprint(__("Scale option labels must be unique after normalization."));
				return;
			}
			const duplicateRow = find_duplicate_key(rows);
			if (duplicateRow) {
				frappe.msgprint(__("Skill / Attribute labels must be unique after normalization."));
				return;
			}

			let row = get_selected_likert_row();
			if (!row) {
				row = frm.add_child("template_fields");
			}

			row.field_key = row.field_key || scrub_key(label);
			row.label = label;
			row.field_type = "Likert Scale";
			row.is_required = values.is_required ? 1 : 0;
			row.options_json = JSON.stringify({ version: 1, columns, rows }, null, 2);
			frm.refresh_field("template_fields");
			dialog.hide();
		},
	});

	function get_selected_likert_row() {
		const target = String(dialog.get_value("target") || "").trim();
		return likertRows.find((row) => target.startsWith(`${row.field_key} - `));
	}

	function load_selected_likert_row() {
		const row = get_selected_likert_row();
		if (!row) {
			dialog.set_value("label", __("Academic Skills"));
			dialog.set_value("is_required", 1);
			dialog.set_value("scale_options", "Consistently\nUsually\nSometimes\nRarely\nN/A");
			dialog.set_value("attribute_rows", "");
			update_preview();
			return;
		}

		const config = parse_likert_config(row);
		dialog.set_value("label", row.label || "");
		dialog.set_value("is_required", row.is_required ? 1 : 0);
		dialog.set_value("scale_options", (config.columns || []).map((column) => column.label).join("\n"));
		dialog.set_value("attribute_rows", (config.rows || []).map((entry) => entry.label).join("\n"));
		update_preview();
	}

	function update_preview() {
		const columns = keyed_entries_from_lines(dialog.get_value("scale_options"));
		const rows = keyed_entries_from_lines(dialog.get_value("attribute_rows"));
		dialog.fields_dict.preview.$wrapper.html(render_likert_preview(columns, rows));
	}

	dialog.show();
	update_preview();
}

function find_duplicate_key(entries) {
	const seen = new Set();
	for (const entry of entries) {
		if (seen.has(entry.key)) {
			return entry.key;
		}
		seen.add(entry.key);
	}
	return null;
}
