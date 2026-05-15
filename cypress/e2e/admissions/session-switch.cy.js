const users = require("../../fixtures/users/e2e-users.json");

describe("admissions family workspace", () => {
	const family = users.admissions_family_workspace;

	beforeEach(() => {
		cy.loginAs("admissions_family_workspace");
	});

	it("switches applicants while preserving the admissions route contract", () => {
		cy.visitAdmissions(`/overview?student_applicant=${family.first_applicant_name}`);

		cy.getByTestId("admissions-layout").should("be.visible");
		cy.getByTestId("admissions-family-switcher").should("be.visible");
		cy.contains(family.first_applicant_label).should("be.visible");

		cy.getByTestId("admissions-family-switcher")
			.contains("button", family.second_applicant_label)
			.click();

		cy.location("search").should("include", `student_applicant=${family.second_applicant_name}`);
		cy.contains(family.second_applicant_label).should("be.visible");
	});
});
