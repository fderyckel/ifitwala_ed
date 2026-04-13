const users = require("../../fixtures/users/e2e-users.json");

describe("admissions submit", () => {
	it("keeps submission blocked when required steps are incomplete", () => {
		cy.loginAs("admissions_submit_blocked");
		cy.visitAdmissions(
			`/submit?student_applicant=${users.admissions_submit_blocked.applicant_name}`
		);

		cy.getByTestId("admissions-submit-page").should("be.visible");
		cy.getByTestId("admissions-submit-blocked").should("be.visible");
		cy.getByTestId("admissions-submit-open").should("be.disabled");
		cy.contains("Action required").should("be.visible");
	});

	it("submits a ready application and exposes the read-only state", () => {
		cy.loginAs("admissions_submit_ready");
		cy.intercept("POST", "**/api/method/ifitwala_ed.api.admissions_portal.submit_application").as(
			"submitApplication"
		);

		cy.visitAdmissions(`/submit?student_applicant=${users.admissions_submit_ready.applicant_name}`);

		cy.getByTestId("admissions-submit-page").should("be.visible");
		cy.getByTestId("admissions-submit-open").should("not.be.disabled").click();
		cy.getByTestId("admissions-submit-overlay").should("be.visible");
		cy.getByTestId("admissions-submit-confirm").click();

		cy.wait("@submitApplication").its("response.statusCode").should("eq", 200);
		cy.getByTestId("admissions-read-only-banner", { timeout: 10000 }).should("be.visible");
		cy.contains("Read-only mode").should("be.visible");
	});
});
