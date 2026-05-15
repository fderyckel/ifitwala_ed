const users = require("../../fixtures/users/e2e-users.json");

describe("admissions profile save", () => {
	const applicant = users.admissions_profile_edit;
	const preferredName = "Cypress Profile Save";

	beforeEach(() => {
		cy.loginAs("admissions_profile_edit");
	});

	it("persists a profile edit through the real admissions form", () => {
		cy.intercept("POST", "**/api/method/ifitwala_ed.api.admissions_portal.update_applicant_profile").as(
			"updateProfile"
		);

		cy.visitAdmissions(`/profile?student_applicant=${applicant.applicant_name}`);

		cy.getByTestId("admissions-profile-page").should("be.visible");
		cy.contains("label", "Preferred name").find("input").clear().type(preferredName);
		cy.getByTestId("admissions-profile-save").click();

		cy.wait("@updateProfile").its("response.statusCode").should("eq", 200);

		cy.reload();
		cy.getByTestId("admissions-profile-page").should("be.visible");
		cy.contains("label", "Preferred name").find("input").should("have.value", preferredName);
	});
});
