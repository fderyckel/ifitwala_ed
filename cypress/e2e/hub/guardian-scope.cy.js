const users = require("../../fixtures/users/e2e-users.json");

describe("hub guardian scope", () => {
	const guardian = users.hub_guardian_one_child;

	beforeEach(() => {
		cy.loginAs("hub_guardian_one_child");
	});

	it("shows the linked student and blocks out-of-scope student routes", () => {
		cy.visitHub("/guardian");
		cy.getByTestId("guardian-home-page").should("be.visible");

		cy.visitHub(`/guardian/students/${guardian.student_name}`);
		cy.contains(guardian.student_label).should("be.visible");

		cy.visitHub(`/guardian/students/${guardian.out_of_scope_student_name}`);
		cy.getByTestId("guardian-student-scope-error").should("be.visible");
		cy.contains("This student is not available in your guardian scope.").should("be.visible");
	});
});
