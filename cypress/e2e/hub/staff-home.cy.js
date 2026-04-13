const users = require("../../fixtures/users/e2e-users.json");

describe("hub staff home", () => {
	beforeEach(() => {
		cy.loginAs("hub_staff_basic");
	});

	it("boots the staff shell for a seeded employee", () => {
		cy.visitHub("/staff");

		cy.getByTestId("staff-home-page").should("be.visible");
		cy.contains(users.hub_staff_basic.first_name).should("be.visible");
		cy.contains("Morning Brief").should("be.visible");
		cy.getByTestId("staff-home-quick-actions").should("be.visible");
	});
});
