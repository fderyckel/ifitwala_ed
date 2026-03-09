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
	},
});
