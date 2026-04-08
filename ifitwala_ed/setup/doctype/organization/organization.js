// Copyright (c) 2024, fdR and contributors
// For license information, please see license.txt

// ifitwala_ed/setup/doctype/organization/organization.js

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

function ensure_saved_organization(frm, actionLabel) {
	if (frm.is_new() || frm.is_dirty()) {
		frappe.msgprint(__("Please save the Organization before using {0}.", [actionLabel]));
		return false;
	}
	return true;
}

function setup_governed_organization_logo_upload(frm) {
	const fieldname = "organization_logo";
	const openUploader = () => {
		if (!ensure_saved_organization(frm, __("Upload Organization Logo"))) return;

		new frappe.ui.FileUploader({
			method: "ifitwala_ed.utilities.governed_uploads.upload_organization_logo",
			args: { organization: frm.doc.name },
			doctype: "Organization",
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
					frm.set_value("organization_logo", payload.file_url);
					frm.set_value("organization_logo_file", payload.file);
				}
				const reload = frm.reload_doc();
				if (reload && reload.then) {
					reload.then(() => frm.refresh_field(fieldname));
				}
			},
			on_error() {
				frappe.msgprint(__("Organization logo upload failed. Please try again."));
			},
		});
	};

	frm.set_df_property(fieldname, "read_only", 1);
	frm.set_df_property(
		fieldname,
		"description",
		__("Use Upload Organization Logo or Manage Organization Media for governed public assets.")
	);

	frm.remove_custom_button(__("Upload Organization Logo"), __("Actions"));
	frm.remove_custom_button(__("Upload Organization Logo"));
	const $button = frm.add_custom_button(__("Upload Organization Logo"), openUploader, __("Actions"));
	$button.addClass("btn-primary");
}

function setup_organization_media_manager(frm) {
	if (frm.is_new()) return;

	const openManager = async () => {
		if (!ensure_saved_organization(frm, __("Manage Organization Media"))) return;

		const dialogApi = await getOrganizationMediaDialog();
		if (!dialogApi || typeof dialogApi.openManager !== "function") {
			frappe.msgprint(__("Organization Media is not available. Please refresh the page."));
			return;
		}

		dialogApi.openManager({
			frm,
			organization: frm.doc.name,
			school: frm.doc.default_website_school || null,
		});
	};

	frm.remove_custom_button(__("Manage Organization Media"), __("Actions"));
	frm.remove_custom_button(__("Manage Organization Media"));
	frm.add_custom_button(__("Manage Organization Media"), openManager, __("Actions"));
}

function setup_governed_drive_link(frm) {
	const drive = window.ifitwala_ed && window.ifitwala_ed.drive;
	if (!drive || typeof drive.addOpenContextButton !== "function" || frm.is_new()) {
		return;
	}

	drive.addOpenContextButton(frm, {
		doctype: "Organization",
		name: frm.doc.name,
		label: __("Open in Drive"),
		group: __("Actions"),
	});
}

function clear_invalid_default_school(frm, school, school_org) {
	frappe.msgprint(
		__(
			"Default Website School must belong to this Organization. " +
			"School '{0}' belongs to '{1}', not '{2}'.",
			[school, school_org || __("Unknown"), frm.doc.name || __("this Organization")]
		)
	);
	frm.set_value("default_website_school", null);
}

frappe.ui.form.on("Organization", {
	setup(frm) {
		frm.set_query("default_website_school", () => {
			const filters = {};
			if (frm.doc.name && !frm.is_new()) {
				filters.organization = frm.doc.name;
			}
			return { filters };
		});
	},

	refresh(frm) {
		setup_governed_organization_logo_upload(frm);
		setup_organization_media_manager(frm);
		setup_governed_drive_link(frm);
	},

	default_website_school(frm) {
		const school = frm.doc.default_website_school;
		if (!school || !frm.doc.name || frm.is_new()) {
			return;
		}

		frappe.db.get_value("School", school, "organization", (r) => {
			const school_org = r && r.organization;
			if (!school_org || school_org !== frm.doc.name) {
				clear_invalid_default_school(frm, school, school_org);
			}
		});
	},
});
