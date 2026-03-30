// Copyright (c) 2024, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed/school_settings/doctype/school/school.js

frappe.provide("ifitwala_ed.school");

/**
 * UX guardrails (NOT the invariant):
 * The server controller enforces:
 * - parent_school must be a group
 * - parent/child must share the same organization
 * - cannot change organization if the school has children
 *
 * This JS only helps users avoid predictable validation errors.
 */

function ensure_parent_is_valid(frm) {
	// If we have a parent, verify:
	// - is_group = 1
	// - parent.organization matches doc.organization (when org is set)
	const parent = frm.doc.parent_school;
	if (!parent) return;

	frappe.db.get_value("School", parent, ["is_group", "organization"], (r) => {
		// Defensive: r can be nullish in odd cases
		const is_group = r && r.is_group;
		const parent_org = r && r.organization;

		if (!is_group) {
			frm.set_value("parent_school", "");
			return;
		}

		// If the doc has an org set, enforce "same org" in the UI.
		if (frm.doc.organization && parent_org && parent_org !== frm.doc.organization) {
			frm.set_value("parent_school", "");
			frappe.msgprint(
				__(
					"Parent School was cleared because it belongs to a different Organization. Parent and child schools must belong to the same Organization."
				)
			);
		}
	});
}

function _is_published(frm) {
	return Boolean(parseInt(frm.doc.is_published || 0, 10));
}

function _store_saved_publish_state(frm) {
	frm._saved_is_published = _is_published(frm);
}

function _open_school_website_page(frm) {
	const slug = (frm.doc.website_slug || "").trim();
	if (!slug) {
		frappe.msgprint(__("Set a Website Slug before opening the school website page."));
		return;
	}

	frappe.db
		.get_value("School Website Page", { school: frm.doc.name, route: "/" }, "name")
		.then((res) => {
			const name = res && res.message ? res.message.name : null;
			if (name) {
				frappe.set_route("Form", "School Website Page", name);
				return;
			}

			frappe.new_doc("School Website Page", {}, (doc) => {
				doc.school = frm.doc.name;
				doc.route = "/";
				doc.page_type = "Standard";
				doc.title = frm.doc.school_name || frm.doc.name;
			});
	});
}

function _ensure_saved_school(frm, actionLabel) {
	if (frm.is_new() || frm.is_dirty()) {
		frappe.msgprint(__("Please save the School before using {0}.", [actionLabel]));
		return false;
	}
	return true;
}

function getOrganizationMediaDialog() {
	return new Promise((resolve) => {
		const existing = window.ifitwalaEd && window.ifitwalaEd.organizationMedia;
		if (existing) {
			resolve(existing);
			return;
		}

		frappe.require("/assets/ifitwala_ed/js/organization_media_dialog.js", () => {
			resolve((window.ifitwalaEd && window.ifitwalaEd.organizationMedia) || null);
		});
	});
}

function setup_governed_school_logo_upload(frm) {
	const fieldname = "school_logo";
	const openUploader = () => {
		if (!_ensure_saved_school(frm, __("Upload School Logo"))) return;

		new frappe.ui.FileUploader({
			method: "ifitwala_ed.utilities.governed_uploads.upload_school_logo",
			args: { school: frm.doc.name },
			doctype: "School",
			docname: frm.doc.name,
			fieldname,
			is_private: 0,
			disable_private: true,
			allow_multiple: false,
			on_success(fileDoc) {
				const payload =
					fileDoc?.message
					|| (Array.isArray(fileDoc) ? fileDoc[0] : fileDoc)
					|| (typeof fileDoc === "string" ? { file_url: fileDoc } : null);
				if (payload?.file_url) {
					frm.set_value("school_logo", payload.file_url);
					frm.set_value("school_logo_file", payload.file);
				}
				const reload = frm.reload_doc();
				if (reload && reload.then) {
					reload.then(() => frm.refresh_field(fieldname));
				}
			},
			on_error() {
				frappe.msgprint(__("School logo upload failed. Please try again."));
			},
		});
	};

	frm.set_df_property(fieldname, "read_only", 1);
	frm.set_df_property(
		fieldname,
		"description",
		__("Use Upload School Logo to attach a governed organization media file.")
	);

	frm.remove_custom_button(__("Upload School Logo"), __("Actions"));
	frm.remove_custom_button(__("Upload School Logo"));
	const $button = frm.add_custom_button(__("Upload School Logo"), openUploader, __("Actions"));
	$button.addClass("btn-primary");
}

function setup_governed_gallery_upload(frm) {
	const grid = frm.get_field("gallery_image")?.grid;
	if (!grid) return;

	grid.update_docfield_property("school_image", "read_only", 1);
	grid.update_docfield_property("governed_file", "read_only", 1);
	grid.update_docfield_property(
		"school_image",
		"description",
		__("Managed by governed organization media uploads.")
	);

	if (grid.__organizationMediaUploadBound) return;
	grid.__organizationMediaUploadBound = true;

	const openUploader = () => {
		if (!_ensure_saved_school(frm, __("Upload Gallery Image"))) return;

		new frappe.ui.FileUploader({
			method: "ifitwala_ed.utilities.governed_uploads.upload_school_gallery_image",
			args: { school: frm.doc.name },
			doctype: "School",
			docname: frm.doc.name,
			fieldname: "gallery_image",
			is_private: 0,
			disable_private: true,
			allow_multiple: false,
			on_success() {
				const reload = frm.reload_doc();
				if (reload && reload.then) {
					reload.then(() => frm.refresh_field("gallery_image"));
				}
			},
			on_error() {
				frappe.msgprint(__("Gallery image upload failed. Please try again."));
			},
		});
	};

	const $button = grid.add_custom_button(__("Upload Gallery Image"), openUploader);
	$button.addClass("btn-primary");
}

function setup_organization_media_manager(frm) {
	if (!frm.doc.organization || frm.is_new()) return;

	const openManager = async () => {
		if (!_ensure_saved_school(frm, __("Manage Organization Media"))) return;

		const dialogApi = await getOrganizationMediaDialog();
		if (!dialogApi || typeof dialogApi.openManager !== "function") {
			frappe.msgprint(__("Organization Media is not available. Please refresh the page."));
			return;
		}

		dialogApi.openManager({
			organization: frm.doc.organization,
			school: frm.doc.name,
		});
	};

	frm.remove_custom_button(__("Manage Organization Media"), __("Actions"));
	frm.remove_custom_button(__("Manage Organization Media"));
	frm.add_custom_button(__("Manage Organization Media"), openManager, __("Actions"));
}

frappe.ui.form.on("School", {
	onload: function (frm) {
		_store_saved_publish_state(frm);

		// On new docs, if a parent is preset, ensure it's valid.
		if (frm.doc.__islocal && frm.doc.parent_school) {
			ensure_parent_is_valid(frm);
		}
	},

	setup: function (frm) {
		frm.set_query("parent_school", function () {
			// UX guardrail: only allow group schools, and (when set) restrict to same organization.
			// Server enforces the real invariant.
			const filters = { is_group: 1 };

			if (frm.doc.organization) {
				filters.organization = frm.doc.organization;
			}

			return { filters };
		});
	},

	refresh: function (frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__("Create Academic Year"), () => {
				frappe.new_doc("Academic Year", {}, (ay) => {
					ay.school = frm.doc.name;
				});
			});

			frm.add_custom_button(__("Create School Calendar"), () => {
				frappe.new_doc("School Calendar", {}, (sc) => {
					sc.school = frm.doc.name;
				});
			});
		}

		if (!frm.doc.__islocal) {
			frm.doc.abbr && frm.set_df_property("abbr", "read_only", 1);
		}

		frm.toggle_display("address_html", !frm.doc.__islocal);
		if (!frm.doc.__islocal) {
			frappe.contacts.render_address_and_contact(frm);
		}
		setup_governed_school_logo_upload(frm);
		setup_governed_gallery_upload(frm);
		setup_organization_media_manager(frm);

		frm.set_query("current_school_calendar", function () {
			return {
				filters: { school: frm.doc.name },
			};
		});

		_store_saved_publish_state(frm);
	},

	before_save: function (frm) {
		frm._pre_save_is_published = frm._saved_is_published;
	},

	after_save: function (frm) {
		const was_published = Boolean(parseInt(frm._pre_save_is_published || 0, 10));
		const now_published = _is_published(frm);
		if (!was_published && now_published) {
			_open_school_website_page(frm);
		}
	},

	is_published: function (frm) {
		if (_is_published(frm) && !(frm.doc.website_slug || "").trim()) {
			frappe.msgprint(__("Website Slug is required before publishing a School."));
		}
	},

	school_name: function (frm) {
		if (frm.doc.__islocal) {
			let parts = frm.doc.school_name.split();
			let abbr = $.map(parts, function (p) {
				return p ? p.substr(0, 1) : null;
			}).join("");
			frm.set_value("abbr", abbr);
		}
	},

	organization: function (frm) {
		// If organization changes, the current parent may now be invalid under the "same org" rule.
		// Clear parent early to avoid predictable server-side validation errors.
		if (frm.doc.parent_school) {
			ensure_parent_is_valid(frm);
		}
	},

	parent_school: function (frm) {
		// Keep existing behavior
		var bool = frm.doc.parent_school ? true : false;
		frm.set_value("existing_school", bool ? frm.doc.parent_school : "");

		// UX guardrail: validate parent immediately (group + same org).
		if (frm.doc.parent_school) {
			ensure_parent_is_valid(frm);
		}
	},
});

cur_frm.cscript.change_abbr = function () {
	var dialog = new frappe.ui.Dialog({
		title: __("Replace Abbr"),
		fields: [
			{
				fieldtype: "Data",
				label: __("New Abbreviation"),
				fieldname: "new_abbr",
				reqd: 1,
			},
			{ fieldtype: "Button", label: __("Update"), fieldname: "update" },
		],
	});

	dialog.fields_dict.update.$input.click(function () {
		var args = dialog.get_values();
		if (!args) return;
		frappe.show_alert(__("Update in progress. It might take a while."));
		return frappe.call({
			method: "ifitwala_ed.school_settings.doctype.school.school.enqueue_replace_abbr",
			args: {
				school: cur_frm.doc.name,
				old: cur_frm.doc.abbr,
				new: args.new_abbr,
			},
			callback: function (r) {
				if (r.exc) {
					frappe.msgprint(__("There were errors."));
					return;
				} else {
					cur_frm.set_value("abbr", args.new_abbr);
				}
				dialog.hide();
				cur_frm.refresh();
			},
			btn: this,
		});
	});
	dialog.show();
};

ifitwala_ed.school.set_custom_query = function (frm, v) {
	var filters = {
		school: frm.doc.name,
		is_group: 0,
	};

	for (var key in v[1]) {
		filters[key] = v[1][key];
	}

	frm.set_query(v[0], function () {
		return {
			filters: filters,
		};
	});
};
