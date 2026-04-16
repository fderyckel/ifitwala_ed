describe("hub route resolution", () => {
	beforeEach(() => {
		cy.logout();
	});

	it("redirects guests to login for protected hub routes", () => {
		cy.visitHub("/staff");

		cy.expectPath("/login");
		cy.location("search").should("include", "redirect-to=%2Fhub%2Fstaff");
	});

	it("loads the requested staff route after authenticated login", () => {
		cy.visitHub("/staff");
		cy.expectPath("/login");

		cy.loginAs("hub_staff_basic");
		cy.visitHub("/staff");

		cy.getByTestId("staff-home-page").should("be.visible");
	});
});
