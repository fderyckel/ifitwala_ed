frappe.ui.form.on("Admission Acknowledgement Profile", {
	setup(frm) {
		set_school_query(frm);
	},
	refresh(frm) {
		set_school_query(frm);
	},
	organization(frm) {
		if (frm.doc.school) {
			frm.set_value("school", null);
		}
		set_school_query(frm);
	},
});

function set_school_query(frm) {
	frm.set_query("school", () => ({
		query:
			"ifitwala_ed.admission.doctype.admission_acknowledgement_profile.admission_acknowledgement_profile.acknowledgement_school_link_query",
		filters: {
			organization: frm.doc.organization || "",
		},
	}));
}
